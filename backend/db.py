"""SQLite-backed user store + per-day query counter.

Kept intentionally dependency-light (stdlib ``sqlite3``) so the backend runs with
zero external services. Stores users, hashed passwords, tier, and a daily query
ledger used for free-tier rate limiting.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from config import settings

# Use Postgres when DATABASE_URL is set (Render), else local SQLite.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
if USE_PG:
    _PG_DSN = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # Render's external Postgres host requires SSL; add it if missing.
    if "render.com" in _PG_DSN and "sslmode=" not in _PG_DSN:
        _PG_DSN += ("&" if "?" in _PG_DSN else "?") + "sslmode=require"


class _ConnProxy:
    """Uniform connection: functions use ``?`` placeholders + ``conn.execute``;
    for Postgres we translate ``?`` -> ``%s`` and split multi-statement scripts."""

    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql: str, params: tuple = ()):
        if USE_PG:
            sql = sql.replace("?", "%s")
        return self.raw.execute(sql, params)

    def executescript(self, script: str):
        if USE_PG:
            for stmt in script.split(";"):
                if stmt.strip():
                    self.raw.execute(stmt)
        else:
            self.raw.executescript(script)

    def commit(self):
        self.raw.commit()

    def close(self):
        self.raw.close()

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

CREATE TABLE IF NOT EXISTS bookmarks (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    book_id    TEXT NOT NULL,
    title      TEXT NOT NULL,
    author     TEXT NOT NULL,
    excerpt    TEXT NOT NULL,
    note       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS query_history (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    query      TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    query      TEXT NOT NULL DEFAULT '',
    rating     INTEGER NOT NULL,
    comment    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    amount     INTEGER NOT NULL,
    plan       TEXT NOT NULL DEFAULT 'pro',
    status     TEXT NOT NULL DEFAULT 'pending',  -- pending | paid | rejected
    txn_ref    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@contextmanager
def _conn():
    global USE_PG
    raw = None
    if USE_PG:
        try:
            import psycopg
            from psycopg.rows import dict_row

            raw = psycopg.connect(_PG_DSN, row_factory=dict_row)
        except Exception as exc:
            # Never crash the app on a bad/unreachable DB URL: fall back to SQLite
            # so the service stays up. Postgres activates once the URL is valid.
            print(f"[db] Postgres unavailable ({exc}); falling back to SQLite.")
            USE_PG = False
    if raw is None:
        raw = sqlite3.connect(settings.user_db_path)
        raw.row_factory = sqlite3.Row
    conn = _ConnProxy(raw)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        # Migration: add pro_until to existing users tables (dialect-aware).
        if USE_PG:
            conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS pro_until TEXT")
        else:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "pro_until" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN pro_until TEXT")


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


# --- Tier / Pro -------------------------------------------------------------
def set_pro(user_id: str, until_iso: str, tier: str = "premium") -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET tier = ?, pro_until = ? WHERE id = ?",
            (tier, until_iso, user_id),
        )


def pro_active(user: dict) -> bool:
    until = user.get("pro_until")
    if not until:
        return False
    try:
        return datetime.fromisoformat(until) > datetime.now(timezone.utc)
    except Exception:
        return False


# --- Bookmarks --------------------------------------------------------------
def add_bookmark(user_id, book_id, title, author, excerpt, note="") -> dict:
    bid = "bm_" + secrets.token_hex(8)
    created = _now_iso()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO bookmarks (id, user_id, book_id, title, author, excerpt, note, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (bid, user_id, book_id, title, author, excerpt, note, created),
        )
    return {"id": bid, "book_id": book_id, "title": title, "author": author,
            "excerpt": excerpt, "note": note, "created_at": created}


def list_bookmarks(user_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def remove_bookmark(user_id: str, bookmark_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM bookmarks WHERE id = ? AND user_id = ?", (bookmark_id, user_id)
        )
    return cur.rowcount > 0


# --- Query history ----------------------------------------------------------
def log_history(user_id: str, query: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO query_history (id, user_id, query, created_at) VALUES (?,?,?,?)",
            ("qh_" + secrets.token_hex(8), user_id, query[:2000], _now_iso()),
        )


def list_history(user_id: str, limit: int = 50) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT query, created_at FROM query_history WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?", (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def popular_queries(limit: int = 10) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT query, COUNT(*) c FROM query_history GROUP BY lower(query) "
            "ORDER BY c DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{"query": r["query"], "count": r["c"]} for r in rows]


# --- Feedback ---------------------------------------------------------------
def add_feedback(user_id: str, query: str, rating: int, comment: str = "") -> dict:
    fid = "fb_" + secrets.token_hex(8)
    created = _now_iso()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO feedback (id, user_id, query, rating, comment, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (fid, user_id, query[:2000], rating, comment[:1000], created),
        )
    return {"id": fid, "rating": rating, "created_at": created}


# --- Payments ---------------------------------------------------------------
def create_payment(user_id: str, amount: int, plan: str = "pro") -> dict:
    pid = "pay_" + secrets.token_hex(8)
    now = _now_iso()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO payments (id, user_id, amount, plan, status, created_at, updated_at) "
            "VALUES (?,?,?,?, 'pending', ?, ?)",
            (pid, user_id, amount, plan, now, now),
        )
    return {"id": pid, "user_id": user_id, "amount": amount, "plan": plan,
            "status": "pending", "created_at": now}


def submit_payment_ref(user_id: str, payment_id: str, txn_ref: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE payments SET txn_ref = ?, status = 'pending', updated_at = ? "
            "WHERE id = ? AND user_id = ?",
            (txn_ref[:120], _now_iso(), payment_id, user_id),
        )
    return cur.rowcount > 0


def get_payment(payment_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    return dict(row) if row else None


def list_payments(status: Optional[str] = None) -> list[dict]:
    with _conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM payments WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM payments ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
    return [dict(r) for r in rows]


def set_payment_status(payment_id: str, status: str) -> Optional[dict]:
    with _conn() as conn:
        conn.execute(
            "UPDATE payments SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now_iso(), payment_id),
        )
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    return dict(row) if row else None


# --- Admin stats ------------------------------------------------------------
def counts() -> dict:
    with _conn() as conn:
        users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        pro = conn.execute(
            "SELECT COUNT(*) c FROM users WHERE pro_until IS NOT NULL"
        ).fetchone()["c"]
        paid = conn.execute(
            "SELECT COUNT(*) c FROM payments WHERE status = 'paid'"
        ).fetchone()["c"]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(amount),0) s FROM payments WHERE status = 'paid'"
        ).fetchone()["s"]
        queries = conn.execute("SELECT COUNT(*) c FROM query_history").fetchone()["c"]
    return {"users": users, "pro_users": pro, "paid_payments": paid,
            "revenue_inr": revenue, "total_queries": queries}
