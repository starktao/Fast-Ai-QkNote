import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                api_key TEXT NOT NULL,
                audio_model TEXT NOT NULL,
                text_model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                style TEXT,
                remark TEXT,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                error TEXT,
                transcript TEXT,
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                step TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            """
        )


def get_config() -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM config WHERE id = 1").fetchone()
        return dict(row) if row else None


def upsert_config(api_key: str, audio_model: str, text_model: str) -> None:
    now = _utc_now()
    existing = get_config()
    created_at = existing["created_at"] if existing else now
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO config (id, api_key, audio_model, text_model, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                api_key = excluded.api_key,
                audio_model = excluded.audio_model,
                text_model = excluded.text_model,
                updated_at = excluded.updated_at
            """,
            (api_key, audio_model, text_model, created_at, now),
        )


def create_session(url: str, style: str | None, remark: str | None) -> int:
    now = _utc_now()
    with _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO sessions (url, style, remark, status, stage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (url, style, remark, "pending", "download", now, now),
        )
        session_id = int(cur.lastrowid)
        steps = [
            (session_id, "download", "pending", None, now, now),
            (session_id, "transcribe", "pending", None, now, now),
            (session_id, "note", "pending", None, now, now),
        ]
        conn.executemany(
            """
            INSERT INTO session_steps (session_id, step, status, message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            steps,
        )
        return session_id


def list_sessions() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, url, style, remark, status, stage, created_at, updated_at
            FROM sessions
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_session(session_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def list_session_steps(session_id: int) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT step, status, message, created_at, updated_at
            FROM session_steps
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def update_session(session_id: int, **fields: str | None) -> None:
    if not fields:
        return
    fields["updated_at"] = _utc_now()
    keys = list(fields.keys())
    assignments = ", ".join([f"{key} = ?" for key in keys])
    values = [fields[key] for key in keys]
    values.append(session_id)
    with _get_conn() as conn:
        conn.execute(
            f"UPDATE sessions SET {assignments} WHERE id = ?",
            values,
        )


def update_step(session_id: int, step: str, status: str, message: str | None = None) -> None:
    now = _utc_now()
    with _get_conn() as conn:
        conn.execute(
            """
            UPDATE session_steps
            SET status = ?, message = ?, updated_at = ?
            WHERE session_id = ? AND step = ?
            """,
            (status, message, now, session_id, step),
        )