from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("FEEDBACK_DB", BASE_DIR / "data" / "feedback.sqlite3"))

app = FastAPI(title="Calculation Power Feedback API", docs_url=None, redoc_url=None)

class FeedbackIn(BaseModel):
    page_slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9_./-]+$")
    page_title: str = Field(min_length=1, max_length=200)
    feedback: Literal["helpful", "needs_more"]
    comment: str | None = Field(default=None, max_length=1000)

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def init_db() -> None:
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_slug TEXT NOT NULL,
                page_title TEXT NOT NULL,
                feedback TEXT NOT NULL CHECK (feedback IN ('helpful', 'needs_more')),
                comment TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_page ON feedback(page_slug)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")

@app.on_event("startup")
def startup() -> None:
    init_db()

@app.post("/api/feedback", status_code=201)
def create_feedback(item: FeedbackIn) -> dict[str, bool]:
    comment = item.comment.strip() if item.comment else None
    if comment == "":
        comment = None

    try:
        with connect() as conn:
            conn.execute(
                """INSERT INTO feedback
                   (page_slug, page_title, feedback, comment, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    item.page_slug,
                    item.page_title,
                    item.feedback,
                    comment,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Could not save feedback") from exc

    return {"ok": True}

@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}
