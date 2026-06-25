"""SQLite-backed user store + per-day query counter.

Kept intentionally dependency-light (stdlib ``sqlite3``) so the backend runs with
zero external services. Stores users, hashed passwords, tier, and a daily query
ledger used for free-tier rate limiting.
"""
from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    tier          TEXT NOT NULL DEFAULT 'free',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS query_log (
    user_id TEXT NOT NULL,
    day     TEXT NOT NULL,
    count   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(settings.user_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def create_user(name: str, email: str, password_hash: str, tier: str = "free") -> dict:
    user_id = "usr_" + secrets.token_hex(8)
    created = _now_iso()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, tier, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, email.lower(), password_hash, tier, created),
        )
    return {
        "id": user_id,
        "name": name,
        "email": email.lower(),
        "tier": tier,
        "created_at": created,
    }


def get_user_by_email(email: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def queries_today(user_id: str) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT count FROM query_log WHERE user_id = ? AND day = ?",
            (user_id, _today()),
        ).fetchone()
    return row["count"] if row else 0


def increment_queries(user_id: str) -> int:
    day = _today()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO query_log (user_id, day, count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, day) DO UPDATE SET count = count + 1",
            (user_id, day),
        )
        row = conn.execute(
            "SELECT count FROM query_log WHERE user_id = ? AND day = ?",
            (user_id, day),
        ).fetchone()
    return row["count"] if row else 1
