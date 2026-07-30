"""SQLite layer cho Companion bot — posts (ingestion), escalations (hàng đợi TA), ask_logs (trace AI call).

Một file DB duy nhất (mặc định bot.sqlite3, đổi qua config.DB_PATH). Không dùng ORM — hackathon scope,
schema nhỏ và truy vấn đơn giản không cần thêm lớp trừu tượng.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    channel_name TEXT NOT NULL,
    channel_group TEXT NOT NULL,   -- chat_lop | forum | tai_nguyen | thong_bao
    class_code TEXT,               -- vd. Lab-D305, null nếu không thuộc kênh lớp
    author TEXT,
    author_role TEXT,
    tags TEXT,                     -- JSON list, vd forum tag Open/Solved/Tip...
    reactions INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    content_snippet TEXT,
    session_code TEXT,             -- gắn bởi Session Linker (kênh #tài-nguyên), null nếu không match
    category TEXT,                 -- gắn bởi agent phân loại taxonomy (An), null nếu chưa phân loại
    jump_link TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    asked_by TEXT,
    class_code TEXT,               -- dùng để map sang ta_roster khi build TA digest
    reason TEXT NOT NULL,          -- no_source (①) | out_of_scope (③) | unresolved_clarify (②)
    status TEXT NOT NULL DEFAULT 'open',   -- open | notified | resolved
    created_at TEXT NOT NULL,
    notified_at TEXT,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS ask_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    action TEXT NOT NULL,          -- answer | clarify | refuse_escalate | refuse_scope
    answer TEXT,
    citations TEXT,                -- JSON list
    confidence REAL,
    asked_by TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


# ---------- posts (ingestion worker) ----------

def upsert_post(
    db_path: Path,
    *,
    message_id: str,
    channel_name: str,
    channel_group: str,
    jump_link: str,
    class_code: Optional[str] = None,
    author: Optional[str] = None,
    author_role: Optional[str] = None,
    tags: Optional[list[str]] = None,
    reactions: int = 0,
    comments: int = 0,
    content_snippet: Optional[str] = None,
    session_code: Optional[str] = None,
    category: Optional[str] = None,
    created_at: Optional[str] = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO posts (
                message_id, channel_name, channel_group, class_code, author, author_role,
                tags, reactions, comments, content_snippet, session_code, category,
                jump_link, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(message_id) DO UPDATE SET
                reactions=excluded.reactions,
                comments=excluded.comments,
                tags=excluded.tags,
                session_code=COALESCE(excluded.session_code, posts.session_code),
                category=COALESCE(excluded.category, posts.category)
            """,
            (
                message_id,
                channel_name,
                channel_group,
                class_code,
                author,
                author_role,
                json.dumps(tags or [], ensure_ascii=False),
                reactions,
                comments,
                content_snippet,
                session_code,
                category,
                jump_link,
                created_at or _now(),
            ),
        )


def recent_posts(db_path: Path, *, channel_group: Optional[str] = None, limit: int = 20) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        if channel_group:
            rows = conn.execute(
                "SELECT * FROM posts WHERE channel_group=? ORDER BY created_at DESC LIMIT ?",
                (channel_group, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return rows


def posts_for_session(db_path: Path, session_code: str) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM posts WHERE session_code=? ORDER BY created_at DESC", (session_code,)
        ).fetchall()


# ---------- escalations (hàng đợi TA) ----------

def add_escalation(
    db_path: Path, *, question: str, reason: str, asked_by: Optional[str] = None, class_code: Optional[str] = None
) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO escalations (question, asked_by, class_code, reason, status, created_at) "
            "VALUES (?,?,?,?, 'open', ?)",
            (question, asked_by, class_code, reason, _now()),
        )
        return cur.lastrowid


def open_escalations(db_path: Path, *, class_code: Optional[str] = None) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        if class_code:
            return conn.execute(
                "SELECT * FROM escalations WHERE status='open' AND class_code=? ORDER BY created_at",
                (class_code,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM escalations WHERE status='open' ORDER BY class_code, created_at"
        ).fetchall()


def mark_notified(db_path: Path, escalation_ids: list[int]) -> None:
    if not escalation_ids:
        return
    with connect(db_path) as conn:
        conn.executemany(
            "UPDATE escalations SET status='notified', notified_at=? WHERE id=?",
            [(_now(), eid) for eid in escalation_ids],
        )


def resolve_escalation(db_path: Path, escalation_id: int) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE escalations SET status='resolved', resolved_at=? WHERE id=?",
            (_now(), escalation_id),
        )


# ---------- ask_logs (trace — R5 yêu cầu log lời gọi AI thật; hiện log cả quyết định mock) ----------

def log_ask(
    db_path: Path,
    *,
    question: str,
    action: str,
    answer: Optional[str],
    citations: list[str],
    confidence: float,
    asked_by: Optional[str] = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO ask_logs (question, action, answer, citations, confidence, asked_by, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (question, action, answer, json.dumps(citations, ensure_ascii=False), confidence, asked_by, _now()),
        )