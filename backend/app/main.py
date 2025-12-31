import asyncio
import json
import os
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db
from .pipeline import process_session
from .qwen_client import QwenClient

DEFAULT_AUDIO_MODEL = "qwen3-asr-flash-filetrans"
DEFAULT_TEXT_MODEL = "qwen-max-latest"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigIn(BaseModel):
    api_key: str = Field(..., min_length=10)


class SessionIn(BaseModel):
    url: str
    style: str | None = None
    remark: str | None = None
    include_joke: bool = True


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


@app.get("/api/config")
def get_config() -> dict:
    config = db.get_config()
    if not config:
        return {"has_key": False}

    api_key = config["api_key"]
    masked = f"{api_key[:4]}****{api_key[-4:]}" if len(api_key) >= 8 else "****"
    return {
        "has_key": True,
        "api_key_masked": masked,
    }


@app.post("/api/config")
def save_config(payload: ConfigIn) -> dict:
    client = QwenClient(payload.api_key)
    try:
        client.validate_text_model(DEFAULT_TEXT_MODEL)
        client.validate_audio_model(DEFAULT_AUDIO_MODEL)
    except Exception as exc:
        message = str(exc)
        if "Throttling.AllocationQuota" in message:
            raise HTTPException(status_code=400, detail="quota exceeded")
        raise HTTPException(status_code=400, detail="invalid api key")

    db.upsert_config(payload.api_key, DEFAULT_AUDIO_MODEL, DEFAULT_TEXT_MODEL)
    return {"ok": True}


@app.post("/api/sessions")
def create_session(payload: SessionIn, background_tasks: BackgroundTasks) -> dict:
    config = db.get_config()
    if not config:
        raise HTTPException(status_code=400, detail="missing api key")

    session_id = db.create_session(payload.url, payload.style, payload.remark)
    background_tasks.add_task(process_session, session_id, payload.include_joke)
    return {"id": session_id}


@app.get("/api/sessions")
def list_sessions() -> dict:
    return {"items": db.list_sessions()}


@app.get("/api/sessions/stream")
async def stream_sessions(request: Request) -> StreamingResponse:
    async def event_generator():
        last_payload = None
        while True:
            if await request.is_disconnected():
                break
            payload = {"items": db.list_sessions()}
            data = json.dumps(payload, ensure_ascii=False)
            if data != last_payload:
                last_payload = data
                yield f"event: sessions\ndata: {data}\n\n"
            await asyncio.sleep(2)

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: int) -> dict:
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="not found")
    steps = db.list_session_steps(session_id)
    return {"session": session, "steps": steps}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int) -> dict:
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="not found")
    _delete_audio_assets(session_id)
    db.delete_session(session_id)
    return {"ok": True}


def _delete_audio_assets(session_id: int) -> None:
    audio_dir = Path(os.path.join(db.DATA_DIR, "audio"))
    if not audio_dir.exists():
        return
    for path in audio_dir.glob(f"{session_id}.*"):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    chunk_dir = audio_dir / f"{session_id}_chunks"
    if chunk_dir.exists():
        shutil.rmtree(chunk_dir, ignore_errors=True)


@app.get("/api/sessions/{session_id}/stream")
async def stream_session(session_id: int, request: Request) -> StreamingResponse:
    async def event_generator():
        last_payload = None
        while True:
            if await request.is_disconnected():
                break
            session = db.get_session(session_id)
            steps = db.list_session_steps(session_id) if session else []
            payload = {"session": session, "steps": steps}
            data = json.dumps(payload, ensure_ascii=False)
            if data != last_payload:
                last_payload = data
                yield f"event: session\ndata: {data}\n\n"
            await asyncio.sleep(2)

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
