import base64
import io
import os
import re
import tempfile
import wave
from typing import Any

import dashscope
try:  # dashscope>=1.15 uses File, older versions expose Files
    from dashscope import Files as DashscopeFile
except ImportError:  # pragma: no cover - depends on installed dashscope
    from dashscope import File as DashscopeFile
try:  # dashscope newer versions use audio.asr.transcription.Transcription
    from dashscope.audio.qwen_asr import QwenTranscription as DashscopeTranscription
except ImportError:  # pragma: no cover - depends on installed dashscope
    from dashscope.audio.asr.transcription import Transcription as DashscopeTranscription
import requests

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
TEXT_ENDPOINT = "services/aigc/text-generation/generation"
MULTIMODAL_ENDPOINT = "services/aigc/multimodal-generation/generation"


class QwenClient:
    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = (base_url or os.getenv("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        dashscope.base_http_api_url = self.base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{path}"
        response = requests.post(url, headers=self._headers(), json=payload, timeout=120)
        if response.status_code != 200:
            try:
                detail = response.json()
            except Exception:
                detail = {"message": response.text}
            raise RuntimeError(f"DashScope error {response.status_code}: {detail}")
        return response.json()

    @staticmethod
    def _extract_message_text(data: dict[str, Any]) -> str:
        output = data.get("output") or {}
        choices = output.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
            return "".join(parts)
        return str(content or "")

    def validate_text_model(self, model: str) -> None:
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {"role": "user", "content": "ping"},
                ]
            },
            "parameters": {"result_format": "message"},
        }
        self._post(TEXT_ENDPOINT, payload)

    def validate_audio_model(self, model: str) -> None:
        if _is_filetrans_model(model):
            temp_path = _write_silence_wav()
            try:
                _ = self._transcribe_filetrans(model, temp_path)
            except Exception as exc:
                if is_no_valid_fragment_error(exc):
                    return
                raise
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            return

        data_url, fmt = _silence_wav_data_url()
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {"data": data_url, "format": fmt},
                            },
                            {"type": "text", "text": "transcribe"},
                        ],
                    }
                ]
            },
            "parameters": {"result_format": "message"},
        }
        self._post(MULTIMODAL_ENDPOINT, payload)

    def transcribe_audio(self, model: str, audio_path: str, prompt: str) -> str:
        if _is_filetrans_model(model):
            return self._transcribe_filetrans(model, audio_path)

        data_url, fmt = _audio_to_data_url(audio_path)
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {"data": data_url, "format": fmt},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {"result_format": "message"},
        }
        data = self._post(MULTIMODAL_ENDPOINT, payload)
        return self._extract_message_text(data)

    def generate_note(self, model: str, prompt: str) -> str:
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {"role": "user", "content": prompt},
                ]
            },
            "parameters": {"result_format": "message"},
        }
        data = self._post(TEXT_ENDPOINT, payload)
        return self._extract_message_text(data)

    @staticmethod
    def is_filetrans_model(model: str) -> bool:
        return _is_filetrans_model(model)

    def _transcribe_filetrans(self, model: str, audio_path: str) -> str:
        upload = DashscopeFile.upload(file_path=audio_path, purpose="assistants", api_key=self.api_key)
        upload_output = upload.get("output") or {}
        file_id = _extract_file_id(upload_output)
        if not file_id:
            raise RuntimeError(f"file upload missing file_id: {upload_output}")
        try:
            info = DashscopeFile.get(file_id, api_key=self.api_key)
            info_output = info.get("output") or {}
            file_url = (
                _extract_file_url(upload_output)
                or info_output.get("url")
                or info_output.get("file_url")
                or info_output.get("download_url")
            )
            if not file_url:
                raise RuntimeError(f"missing file url for file_id {file_id}")
            response = _call_transcription(model=model, file_url=file_url, api_key=self.api_key)
            output = response.get("output") or {}
            if output.get("task_status") != "SUCCEEDED":
                raise RuntimeError(f"filetrans failed: {output}")
            result = output.get("result") or {}
            transcription_url = result.get("transcription_url")
            if transcription_url:
                transcription = requests.get(transcription_url, timeout=120).json()
                text = _extract_filetrans_text(transcription)
            else:
                text = _extract_filetrans_text(output)
            if not text:
                raise RuntimeError("empty transcript")
            return text
        finally:
            try:
                DashscopeFile.delete(file_id, api_key=self.api_key)
            except Exception:
                pass


def _audio_to_data_url(audio_path: str) -> tuple[str, str]:
    ext = os.path.splitext(audio_path)[1].lstrip(".").lower() or "mp3"
    with open(audio_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    data_url = f"data:audio/{ext};base64,{encoded}"
    return data_url, ext


def _silence_wav_data_url(duration_seconds: float = 0.5, sample_rate: int = 16000) -> tuple[str, str]:
    frame_count = int(duration_seconds * sample_rate)
    pcm_data = b"\x00\x00" * frame_count
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    data_url = f"data:audio/wav;base64,{encoded}"
    return data_url, "wav"


def _write_silence_wav(duration_seconds: float = 0.5, sample_rate: int = 16000) -> str:
    frame_count = int(duration_seconds * sample_rate)
    pcm_data = b"\x00\x00" * frame_count
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as handle:
        handle.write(buffer.getvalue())
        return handle.name


def _is_filetrans_model(model: str) -> bool:
    return "filetrans" in model or model.startswith("qwen3-asr-")


def is_no_valid_fragment_error(exc: Exception) -> bool:
    return "SUCCESS_WITH_NO_VALID_FRAGMENT" in str(exc)


def _call_transcription(model: str, file_url: str, api_key: str):
    try:
        return DashscopeTranscription.call(model=model, file_url=file_url, api_key=api_key)
    except TypeError:
        return DashscopeTranscription.call(model=model, file_urls=[file_url], api_key=api_key)


def _extract_file_id(output: dict) -> str | None:
    uploaded_files = output.get("uploaded_files") or []
    if uploaded_files and isinstance(uploaded_files, list):
        entry = uploaded_files[0] if uploaded_files else None
        if isinstance(entry, dict):
            return entry.get("file_id") or entry.get("id")
    return output.get("file_id") or output.get("id")


def _extract_file_url(output: dict) -> str | None:
    uploaded_files = output.get("uploaded_files") or []
    if uploaded_files and isinstance(uploaded_files, list):
        entry = uploaded_files[0] if uploaded_files else None
        if isinstance(entry, dict):
            return entry.get("url") or entry.get("file_url") or entry.get("download_url")
    return output.get("url") or output.get("file_url") or output.get("download_url")


def _extract_asr_text(response: dict[str, Any]) -> str:
    output = response.get("output") if isinstance(response, dict) else None
    text = _extract_asr_from_output(output)
    if text:
        return text
    return _extract_text_recursive(output or response)


def _extract_text_recursive(node: Any, key_hint: str | None = None) -> str:
    ignored = {"task_id", "task_status", "status", "code", "message", "request_id"}
    if node is None:
        return ""
    if isinstance(node, str):
        if key_hint in ignored:
            return ""
        return node.strip()
    if isinstance(node, list):
        parts = []
        for item in node:
            text = _extract_text_recursive(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    if isinstance(node, dict):
        for key in ("text", "transcript", "transcription", "content"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("results", "sentences", "paragraphs", "segments", "transcriptions"):
            if key in node:
                text = _extract_text_recursive(node.get(key), key_hint=key)
                if text:
                    return text
        for key, value in node.items():
            text = _extract_text_recursive(value, key_hint=key)
            if text:
                return text
    return ""


def _extract_filetrans_text(data: Any) -> str:
    if isinstance(data, dict):
        transcripts = data.get("transcripts")
        if isinstance(transcripts, list):
            texts = []
            for item in transcripts:
                if isinstance(item, dict):
                    value = item.get("text")
                    if isinstance(value, str) and value.strip():
                        texts.append(value.strip())
            if texts:
                return "\n".join(texts).strip()
    return _extract_text_recursive(data)


def _extract_asr_from_output(output: Any) -> str:
    if not isinstance(output, dict):
        return ""

    direct = _pick_text_value(output)
    if direct:
        return direct

    results = output.get("results") or output.get("result") or output.get("files") or output.get("file") or output.get("transcriptions")
    items = results if isinstance(results, list) else ([results] if results else [])
    if items:
        texts: list[str] = []
        for item in items:
            item_text = _pick_text_value(item)
            if item_text:
                texts.append(item_text)
                continue
            for key in ("sentences", "sentence_list", "segments", "paragraphs"):
                if isinstance(item, dict) and isinstance(item.get(key), list):
                    for entry in item[key]:
                        entry_text = _pick_text_value(entry)
                        if entry_text:
                            texts.append(entry_text)
            if not texts:
                texts.extend(_collect_texts(item))
        if texts:
            return "\n".join(texts).strip()

    collected = _collect_texts(output)
    if collected:
        return "\n".join(collected).strip()
    return ""


def _pick_text_value(node: Any) -> str:
    if isinstance(node, str):
        return "" if _looks_like_timestamp(node) else node.strip()
    if isinstance(node, dict):
        for key in ("transcription", "transcript", "text", "content"):
            value = node.get(key)
            if isinstance(value, str) and value.strip() and not _looks_like_timestamp(value):
                return value.strip()
    return ""


def _collect_texts(node: Any, key_hint: str | None = None) -> list[str]:
    if node is None:
        return []
    if isinstance(node, str):
        if key_hint and _should_ignore_key(key_hint):
            return []
        value = node.strip()
        if not value or _looks_like_timestamp(value):
            return []
        return [value]
    if isinstance(node, list):
        results: list[str] = []
        for item in node:
            results.extend(_collect_texts(item))
        return results
    if isinstance(node, dict):
        results: list[str] = []
        for key, value in node.items():
            if key in ("transcription", "transcript", "text", "content"):
                if isinstance(value, str) and value.strip() and not _looks_like_timestamp(value):
                    results.append(value.strip())
                    continue
            if _should_ignore_key(key):
                continue
            results.extend(_collect_texts(value, key_hint=key))
        return results
    return []


def _looks_like_timestamp(value: str) -> bool:
    return bool(re.match(r"^\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?$", value))


def _should_ignore_key(key: str) -> bool:
    key_lower = key.lower()
    ignored = {
        "task_id",
        "task_status",
        "status",
        "code",
        "message",
        "request_id",
    }
    if key_lower in ignored:
        return True
    if key_lower.endswith(("_time", "_timestamp", "_url", "_id", "_status")):
        return True
    if key_lower.startswith(("start_", "end_", "begin_", "finish_", "create_", "update_")):
        return True
    return False
