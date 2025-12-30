import os
import shutil
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL

from . import db
from .qwen_client import QwenClient

AUDIO_DIR = os.path.join(db.DATA_DIR, "audio")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCAL_FFMPEG = os.path.join(REPO_ROOT, "tools", "ffmpeg", "bin", "ffmpeg.exe")
SAFE_DATA_URI_BYTES = 7_000_000
CHUNK_SECONDS = 120


def process_session(session_id: int) -> None:
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


def transcribe_with_chunks(
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


def build_note_prompt(transcript: str, style: str | None, remark: str | None) -> str:
    style_text = style or "default"
    remark_text = remark or "none"
    return (
        "You are a note-taking assistant."
        " Create concise and structured notes in Simplified Chinese."
        f"\n\nStyle: {style_text}"
        f"\nUser remark: {remark_text}"
        "\n\nTranscript:"
        f"\n{transcript}"
    )
