import os
import shutil
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL

from . import db
from .qwen_client import QwenClient, is_no_valid_fragment_error

AUDIO_DIR = os.path.join(db.DATA_DIR, "audio")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCAL_FFMPEG = os.path.join(REPO_ROOT, "tools", "ffmpeg", "bin", "ffmpeg.exe")
SAFE_DATA_URI_BYTES = 7_000_000
CHUNK_SECONDS = 120
FALLBACK_AUDIO_MODEL = "qwen-audio-turbo-latest"


def process_session(session_id: int, include_joke: bool) -> None:
    config = db.get_config()
    if not config:
        db.update_session(session_id, status="failed", stage="download", error="missing api key")
        db.update_step(session_id, "download", "failed", "missing api key")
        return

    api_key = config["api_key"]
    audio_model = config["audio_model"]
    text_model = config["text_model"]
    session = db.get_session(session_id)
    if not session:
        return

    client = QwenClient(api_key)

    try:
        db.update_session(session_id, status="running", stage="download")
        db.update_step(session_id, "download", "running")
        audio_path = download_audio(session_id, session["url"])
        db.update_step(session_id, "download", "completed")
    except Exception as exc:
        message = f"download failed: {exc}"
        db.update_session(session_id, status="failed", stage="download", error=message)
        db.update_step(session_id, "download", "failed", message)
        return

    try:
        db.update_session(session_id, stage="transcribe")
        db.update_step(session_id, "transcribe", "running")
        transcript_prompt = "Transcribe the audio to Simplified Chinese. Output plain text only."
        transcript = transcribe_with_chunks(
            client=client,
            session_id=session_id,
            audio_model=audio_model,
            audio_path=audio_path,
            prompt=transcript_prompt,
        )
        if not transcript.strip():
            raise RuntimeError("empty transcript")
        db.update_session(session_id, transcript=transcript)
        db.update_step(session_id, "transcribe", "completed")
    except Exception as exc:
        message = f"transcribe failed: {exc}"
        db.update_session(session_id, status="failed", stage="transcribe", error=message)
        db.update_step(session_id, "transcribe", "failed", message)
        return

    try:
        db.update_session(session_id, stage="note")
        db.update_step(session_id, "note", "running")
        note_prompt = build_note_prompt(
            transcript=transcript,
            style=session.get("style"),
            remark=session.get("remark"),
            include_joke=include_joke,
        )
        note = client.generate_note(text_model, note_prompt)
        db.update_session(session_id, note=note, status="completed")
        db.update_step(session_id, "note", "completed")
    except Exception as exc:
        message = f"note failed: {exc}"
        db.update_session(session_id, status="failed", stage="note", error=message)
        db.update_step(session_id, "note", "failed", message)


def download_audio(session_id: int, url: str) -> str:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    cached = find_cached_audio(url)
    if cached:
        cached_session_id, cached_path = cached
        target_path = Path(AUDIO_DIR) / f"{session_id}{cached_path.suffix}"
        try:
            shutil.copy2(cached_path, target_path)
        except FileNotFoundError:
            pass
        else:
            cached_session = db.get_session(cached_session_id)
            if cached_session and cached_session.get("title"):
                db.update_session(session_id, title=cached_session["title"])
            return str(target_path)
    output_template = os.path.join(AUDIO_DIR, f"{session_id}.%(ext)s")

    ffmpeg_location = resolve_ffmpeg_location()
    if not ffmpeg_location:
        raise RuntimeError("ffmpeg not found. Run scripts/setup.ps1 first.")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": ffmpeg_location,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if isinstance(info, dict):
        title = info.get("title")
        if title:
            db.update_session(session_id, title=title)

    candidates = sorted(Path(AUDIO_DIR).glob(f"{session_id}.*"), key=os.path.getmtime, reverse=True)
    if not candidates:
        raise RuntimeError("audio file not found")
    return str(candidates[0])


def resolve_ffmpeg_location() -> str | None:
    env = os.getenv("FFMPEG_LOCATION")
    if env:
        return env
    if os.path.exists(LOCAL_FFMPEG):
        return LOCAL_FFMPEG
    return shutil.which("ffmpeg")


def find_cached_audio(url: str) -> tuple[int, Path] | None:
    cached_session_id = db.find_latest_downloaded_session(url)
    if not cached_session_id:
        return None
    candidates = sorted(Path(AUDIO_DIR).glob(f"{cached_session_id}.*"), key=os.path.getmtime, reverse=True)
    if not candidates:
        return None
    return cached_session_id, candidates[0]


def transcribe_with_chunks(
    client: QwenClient,
    session_id: int,
    audio_model: str,
    audio_path: str,
    prompt: str,
) -> str:
    try:
        return _transcribe_with_model(client, session_id, audio_model, audio_path, prompt)
    except Exception as exc:
        if client.is_filetrans_model(audio_model) and is_no_valid_fragment_error(exc):
            print(f"[transcribe] filetrans no valid fragment; fallback to {FALLBACK_AUDIO_MODEL}")
            db.update_step(session_id, "transcribe", "running", f"fallback {FALLBACK_AUDIO_MODEL}")
            return _transcribe_with_model(client, session_id, FALLBACK_AUDIO_MODEL, audio_path, prompt)
        print(f"[transcribe] failed: {exc}")
        raise


def _transcribe_with_model(
    client: QwenClient,
    session_id: int,
    audio_model: str,
    audio_path: str,
    prompt: str,
) -> str:
    if client.is_filetrans_model(audio_model):
        return client.transcribe_audio(audio_model, audio_path, prompt)
    if os.path.getsize(audio_path) <= SAFE_DATA_URI_BYTES:
        return client.transcribe_audio(audio_model, audio_path, prompt)

    ffmpeg_location = resolve_ffmpeg_location()
    if not ffmpeg_location:
        raise RuntimeError("ffmpeg not found. Run scripts/setup.ps1 first.")

    chunks = split_audio(audio_path, session_id, ffmpeg_location)
    transcripts: list[str] = []
    total = len(chunks)
    for index, chunk_path in enumerate(chunks, start=1):
        db.update_step(session_id, "transcribe", "running", f"chunk {index}/{total}")
        transcripts.append(client.transcribe_audio(audio_model, chunk_path, prompt))
    return "\n".join([part.strip() for part in transcripts if part.strip()])


def split_audio(audio_path: str, session_id: int, ffmpeg_location: str) -> list[str]:
    chunk_dir = os.path.join(AUDIO_DIR, f"{session_id}_chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    output_template = os.path.join(chunk_dir, "chunk_%03d.mp3")
    cmd = [
        ffmpeg_location,
        "-y",
        "-i",
        audio_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        "-f",
        "segment",
        "-segment_time",
        str(CHUNK_SECONDS),
        "-reset_timestamps",
        "1",
        output_template,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chunks = sorted(Path(chunk_dir).glob("chunk_*.mp3"))
    if not chunks:
        raise RuntimeError("audio split failed")
    return [str(path) for path in chunks]


def build_note_prompt(
    transcript: str,
    style: str | None,
    remark: str | None,
    include_joke: bool = False,
) -> str:
    style_key = style or "video_faithful"
    remark_text = remark or "无"
    joke_line = "- 在笔记末尾加一个和视频相关的笑话便于理解记忆。\n" if include_joke else ""
    prompts = {
        "video_faithful": (
            "你是笔记助手。请将转写整理为“贴近视频风格”的笔记，强调还原度与顺序。\n"
            "要求：\n"
            "- 如用户备注存在，优先遵循。\n"
            "- 按视频讲述顺序组织内容，尽量保持原始结构与叙述节奏。\n"
            "- 保留关键细节、术语与结论，不要过度概括。\n"
            "- 可对口语或语病做轻微整理，但不改变原意。\n"
            "- 不编造内容，未提及的写“未提及”。\n"
            f"{joke_line}"
            f"\n用户备注（如无请忽略）：{remark_text}\n"
            "\n转写：\n"
            f"{transcript}\n"
            "\n输出格式：\n"
            "【内容顺序笔记】...\n"
        ),
        "understand_memory": (
            "你是笔记助手。请根据下方转写生成“理解记忆风格”的笔记，使用简体中文，目标是帮助理解与记忆。\n"
            "要求：\n"
            "- 如用户备注存在，优先遵循。\n"
            "- 先给出清晰的主题概述。\n"
            "- 分点整理核心概念与步骤，突出逻辑关系。\n"
            "- 提供贴近生活或工作场景的例子或类比，帮助理解。\n"
            "- 给出多种记忆辅助方法，例如横向对比、知识延展、口诀、故事或幽默联想。\n"
            "- 如有易混概念，请进行对比；若无写“无”。\n"
            "- 不编造内容，未提及的写“未提及”。\n"
            f"{joke_line}"
            f"\n用户备注（如无请忽略）：{remark_text}\n"
            "\n转写：\n"
            f"{transcript}\n"
            "\n输出格式：\n"
            "【主题概述】...\n"
            "【要点】...\n"
            "【例子/类比】...\n"
            "【记忆辅助】...\n"
            "【易混点对比】...\n"
        ),
        "concise": (
            "你是笔记助手。请将转写整理为“简明扼要风格”的中文笔记。\n"
            "要求：\n"
            "- 如用户备注存在，优先遵循。\n"
            "- 仅保留关键信息，分点输出，表达清晰。\n"
            "- 每条尽量简短，避免重复与赘述。\n"
            "- 不写解释、背景、例子或推测。\n"
            "- 不编造内容，未提及的写“未提及”。\n"
            f"{joke_line}"
            f"\n用户备注（如无请忽略）：{remark_text}\n"
            "\n转写：\n"
            f"{transcript}\n"
            "\n输出格式：\n"
            "【要点】...\n"
        ),
        "moments": (
            "你是笔记助手。请将转写整理成适合朋友圈分享的中文笔记：吸引注意但准确、不过度夸张。\n"
            "要求：\n"
            "- 如用户备注存在，优先遵循。\n"
            "- 标题简短有吸引力，但不标题党。\n"
            "- 输出易传播的要点或金句，表达清晰、有感染力。\n"
            "- 给出简短总结。\n"
            "- 允许轻度口语化，但必须忠于原文，不编造。\n"
            "- 有数据或结论则保留，未提及则不补写。\n"
            f"{joke_line}"
            f"\n用户备注（如无请忽略）：{remark_text}\n"
            "\n转写：\n"
            f"{transcript}\n"
            "\n输出格式：\n"
            "【标题】...\n"
            "【要点】...\n"
            "【总结】...\n"
        ),
    }
    return prompts.get(style_key, prompts["video_faithful"])
