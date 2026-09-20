"""DB接続とスキーマ。

フィードバックだけでなく、ユーザーと認証もこの1つの SQLite に持つ。
将来ユーザー登録や課金（Stripe）を足すときも、同じDBに表を増やして扱う。
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("FEEDBACK_DB", BASE_DIR / "data" / "feedback.sqlite3"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_slug TEXT NOT NULL,
    page_title TEXT NOT NULL,
    feedback TEXT NOT NULL CHECK (feedback IN ('helpful', 'needs_more')),
    comment TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_page ON feedback(page_slug);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);

-- role で権限と課金区分を表す。有料プランを足すときは 'paid' を使い、
-- プラン詳細や Stripe の情報は別表（subscriptions など）に持たせる。
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'free' CHECK (role IN ('admin', 'free', 'paid')),
    created_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- 外部APIへの問い合わせ結果などを保持する汎用の置き場。
-- 今は MathJax の最新版チェック結果のキャッシュに使う。
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def get_state(key: str) -> tuple[str, str] | None:
    """(value, updated_at) を返す。無ければ None。"""
    with connect() as conn:
        row = conn.execute(
            "SELECT value, updated_at FROM app_state WHERE key = ?", (key,)
        ).fetchone()
    return (row["value"], row["updated_at"]) if row else None


def set_state(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO app_state (key, value, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                              updated_at = excluded.updated_at""",
            (key, value, now()),
        )
