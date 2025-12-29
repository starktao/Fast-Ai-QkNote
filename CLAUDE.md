# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Bilibili video note-taking application that downloads audio, transcribes it with Qwen Audio models, and generates structured notes using Qwen text models. The app consists of:

- **Backend**: FastAPI application ([`backend/app/main.py`](backend/app/main.py)) serving REST API with SQLite database
- **Frontend**: Vue 3 + Vite application ([`frontend/src/App.vue`](frontend/src/App.vue)) with session management UI
- **Processing Pipeline**: Background task system ([`backend/app/pipeline.py`](backend/app/pipeline.py)) for multi-stage audio processing

## Development Commands

### Setup (one-time)
```powershell
./scripts/setup.ps1      # Install Python, Node.js, ffmpeg, and dependencies
```

### Running the application
```powershell
./scripts/start.ps1      # Start both backend (port 8000) and frontend (port 5173)
```

### Backend
```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload    # Start dev server on http://localhost:8000
```

### Frontend
```powershell
cd frontend
npm run dev      # Start dev server on http://localhost:5173
npm run build    # Production build
npm run preview  # Preview production build
```

## Architecture

### Processing Pipeline Flow
When a user creates a session via `POST /api/sessions`, the backend runs a background task ([`pipeline.py:process_session()`](backend/app/pipeline.py#L18)) with three stages:

1. **Download**: Uses `yt-dlp` with bundled ffmpeg to extract MP3 audio from Bilibili URL
2. **Transcribe**: Calls Qwen Audio API (supports both filetrans and data-URI models with automatic chunking for large files)
3. **Note Generation**: Sends transcript to Qwen text model with configurable style prompts

Each stage updates the SQLite database with status and error messages. The frontend polls sessions every 5 seconds to display progress.

### Key Components

| File | Purpose |
|------|---------|
| [`backend/app/qwen_client.py`](backend/app/qwen_client.py) | DashScope API client with dual-mode transcription (file upload vs base64) |
| [`backend/app/db.py`](backend/app/db.py) | SQLite schema with `config`, `sessions`, and `session_steps` tables |
| [`backend/app/pipeline.py`](backend/app/pipeline.py) | Background task orchestration, audio downloading, and chunking logic |
| [`frontend/src/api.js`](frontend/src/api.js) | REST API client for config/sessions |
| [`frontend/vite.config.js`](frontend/vite.config.js) | Proxy `/api` requests to backend port 8000 |

### Model Configuration
Two model categories are configured via `/api/config`:
- **Audio models**: `qwen3-asr-flash-filetrans`, `qwen-audio-turbo-latest`
- **Text models**: `qwen-max-latest`

The filetrans models require uploading audio files to DashScope's file API, while other models use base64-encoded data URIs with size limits (~7MB threshold for chunking).

## Environment Variables

- `FFMPEG_LOCATION`: Path to ffmpeg executable (defaults to `tools/ffmpeg/bin/ffmpeg.exe` if not set)
- `DASHSCOPE_BASE_URL`: Override DashScope API base URL (default: `https://dashscope.aliyuncs.com/api/v1`)

## Data Persistence

- **Database**: `backend/data/app.db` (SQLite)
- **Audio files**: `backend/data/audio/` (downloaded MP3s and chunks)
