import json
import sqlite3
from datetime import datetime, timezone

from .models import NewsEnrichment, RawPost

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts(
  message_id TEXT PRIMARY KEY, channel TEXT, title TEXT, content TEXT,
  author TEXT, author_role TEXT, jump_url TEXT, created_at TEXT,
  hearts INTEGER DEFAULT 0, comment_count INTEGER DEFAULT 0,
  summary TEXT, tags TEXT, image_url TEXT, image_source TEXT,
  enriched_at TEXT, enrich_failed INTEGER DEFAULT 0,
  prompt_version TEXT, trace_id TEXT
);
CREATE TABLE IF NOT EXISTS comments(
  id TEXT PRIMARY KEY, post_id TEXT, author TEXT, author_role TEXT,
  content TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS resources(
  message_id TEXT PRIMARY KEY, kind TEXT, title TEXT, session_code TEXT,
  author TEXT, url TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS ingest_state(key TEXT PRIMARY KEY, value TEXT);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert_post(self, p: RawPost) -> None:
        cur = self.conn.execute(
            "SELECT 1 FROM posts WHERE message_id=?", (p.message_id,))
        if cur.fetchone():
            self.conn.execute(
                "UPDATE posts SET hearts=?, comment_count=? WHERE message_id=?",
                (p.hearts, len(p.comments), p.message_id))
        else:
            self.conn.execute(
                "INSERT INTO posts(message_id, channel, title, content, author, "
                "author_role, jump_url, created_at, hearts, comment_count) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (p.message_id, p.channel, p.title, p.content, p.author,
                 p.author_role, p.jump_url, p.created_at, p.hearts, len(p.comments)))
        for c in p.comments:
            self.conn.execute(
                "INSERT OR IGNORE INTO comments(id, post_id, author, author_role, "
                "content, created_at) VALUES(?,?,?,?,?,?)",
                (c.id, p.message_id, c.author, c.author_role, c.content, c.created_at))
        self.conn.commit()

    def pending_enrichment(self, limit: int = 20, force: bool = False) -> list[dict]:
        where = "" if force else "WHERE enriched_at IS NULL AND enrich_failed < 3"
        rows = self.conn.execute(
            f"SELECT message_id, title, content, channel FROM posts {where} "
            "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def save_enrichment(self, message_id: str, e: NewsEnrichment, image_source: str,
                        prompt_version: str, trace_id: str) -> None:
        self.conn.execute(
            "UPDATE posts SET summary=?, tags=?, image_url=?, image_source=?, "
            "enriched_at=?, enrich_failed=0, prompt_version=?, trace_id=? "
            "WHERE message_id=?",
            (e.summary_vi, json.dumps(e.tags), e.image_url, image_source,
             _now(), prompt_version, trace_id, message_id))
        self.conn.commit()

    def mark_enrich_failed(self, message_id: str, fallback_summary: str) -> None:
        self.conn.execute(
            "UPDATE posts SET enrich_failed = enrich_failed + 1, summary=?, "
            "tags=? WHERE message_id=?",
            (fallback_summary, json.dumps(["other"]), message_id))
        self.conn.commit()

    def get_checkpoint(self, channel: str) -> int:
        row = self.conn.execute(
            "SELECT value FROM ingest_state WHERE key=?", (f"ckpt:{channel}",)).fetchone()
        return int(row["value"]) if row else 0

    def set_checkpoint(self, channel: str, message_id: str) -> None:
        new = max(int(message_id), self.get_checkpoint(channel))
        self.conn.execute(
            "INSERT INTO ingest_state(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (f"ckpt:{channel}", str(new)))
        self.conn.commit()

    def add_resource(self, message_id: str, kind: str, title: str,
                     session_code: str | None, author: str, url: str,
                     created_at: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO resources VALUES(?,?,?,?,?,?,?)",
            (message_id, kind, title, session_code, author, url, created_at))
        self.conn.commit()

    def _post_dict(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        d["hot"] = (d["hearts"] or 0) + (d["comment_count"] or 0) >= 20
        return d

    def list_news(self, tag: str | None = None) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM posts WHERE enriched_at IS NOT NULL "
            "ORDER BY created_at DESC").fetchall()
        news = [self._post_dict(r) for r in rows]
        if tag:
            news = [n for n in news if tag in n["tags"]]
        return news

    def get_news(self, message_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM posts WHERE message_id=?", (message_id,)).fetchone()
        if not row:
            return None
        d = self._post_dict(row)
        d["comments"] = [dict(c) for c in self.conn.execute(
            "SELECT * FROM comments WHERE post_id=? ORDER BY created_at",
            (message_id,)).fetchall()]
        return d

    def list_resources(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM resources ORDER BY created_at DESC").fetchall()]
