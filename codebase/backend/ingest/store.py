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
CREATE TABLE IF NOT EXISTS users(
  user_id TEXT PRIMARY KEY, name TEXT, bio TEXT DEFAULT '', bio_source TEXT DEFAULT 'manual',
  bio_hash TEXT, interest_summary TEXT, interest_tags TEXT
);
CREATE TABLE IF NOT EXISTS bookmarks(
  user_id TEXT, message_id TEXT, created_at TEXT,
  PRIMARY KEY(user_id, message_id)
);
CREATE TABLE IF NOT EXISTS schedule_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT, type TEXT, title TEXT, date TEXT, start TEXT, end TEXT,
  cohort TEXT, format TEXT, zoom_url TEXT, host TEXT, location TEXT,
  session_code TEXT, jump_url TEXT
);
CREATE TABLE IF NOT EXISTS schedule_extracted(
  message_id TEXT PRIMARY KEY, extracted_at TEXT, trace_id TEXT,
  event_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS qa_threads(
  thread_id TEXT PRIMARY KEY, title TEXT, body TEXT,
  reply_count INTEGER DEFAULT 0, jump_url TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS ask_embeddings(
  doc_key TEXT PRIMARY KEY, embedding TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(posts)")]
        if "embedded_at" not in cols:
            self.conn.execute("ALTER TABLE posts ADD COLUMN embedded_at TEXT")
        user_cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(users)")]
        if "cohort" not in user_cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN cohort TEXT DEFAULT '4'")
        if "lt_room" not in user_cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN lt_room TEXT DEFAULT 'D302'")
        if "lab_room" not in user_cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN lab_room TEXT DEFAULT 'D305'")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

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
        self.conn.execute(
            "UPDATE posts SET enriched_at=?, image_source='placeholder' "
            "WHERE message_id=? AND enrich_failed >= 3",
            (_now(), message_id))
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

    # ---------- Q&A (kênh hỏi-đáp) — nguồn cho /ask ----------

    def upsert_qa_thread(self, thread_id: str, title: str, body: str,
                         reply_count: int, jump_url: str, created_at: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO qa_threads"
            "(thread_id, title, body, reply_count, jump_url, created_at) VALUES(?,?,?,?,?,?)",
            (thread_id, title, body, reply_count, jump_url, created_at))
        self.conn.commit()

    def list_qa_threads(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM qa_threads ORDER BY created_at DESC").fetchall()]

    def all_schedule_events(self) -> list[dict]:
        """Mọi sự kiện lịch (không lọc cohort) — cho tool tra cứu link zoom /ask."""
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM schedule_events ORDER BY date, COALESCE(start,'99:99')").fetchall()]

    def save_ask_embedding(self, doc_key: str, embedding: list[float]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO ask_embeddings(doc_key, embedding) VALUES(?,?)",
            (doc_key, json.dumps(embedding)))
        self.conn.commit()

    def get_ask_embeddings(self) -> dict[str, list[float]]:
        return {r["doc_key"]: json.loads(r["embedding"])
                for r in self.conn.execute("SELECT doc_key, embedding FROM ask_embeddings")}

    # ---------- recsys: users / bookmarks / embedding flags ----------

    def upsert_user(self, user_id: str, name: str, bio: str = "",
                    bio_source: str = "manual") -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users(user_id, name, bio, bio_source) VALUES(?,?,?,?)",
            (user_id, name, bio, bio_source))
        self.conn.commit()

    def _user_dict(self, r) -> dict:
        d = dict(r)
        d["interest_tags"] = json.loads(d["interest_tags"]) if d["interest_tags"] else []
        return d

    def list_users(self) -> list[dict]:
        return [self._user_dict(r) for r in
                self.conn.execute("SELECT * FROM users ORDER BY user_id")]

    def get_user(self, user_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return self._user_dict(r) if r else None

    def set_bio(self, user_id: str, bio: str, source: str = "manual") -> None:
        self.conn.execute("UPDATE users SET bio=?, bio_source=? WHERE user_id=?",
                          (bio, source, user_id))
        self.conn.commit()

    def toggle_bookmark(self, user_id: str, message_id: str) -> bool:
        cur = self.conn.execute(
            "DELETE FROM bookmarks WHERE user_id=? AND message_id=?", (user_id, message_id))
        if cur.rowcount == 0:
            self.conn.execute(
                "INSERT INTO bookmarks(user_id, message_id, created_at) VALUES(?,?,?)",
                (user_id, message_id, _now()))
            self.conn.commit()
            return True
        self.conn.commit()
        return False

    def list_bookmarks(self, user_id: str) -> list[str]:
        return [r["message_id"] for r in self.conn.execute(
            "SELECT message_id FROM bookmarks WHERE user_id=? ORDER BY created_at DESC",
            (user_id,))]

    def bookmarked_news(self, user_id: str, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT p.message_id, p.title, p.summary, p.tags FROM bookmarks b "
            "JOIN posts p ON p.message_id = b.message_id WHERE b.user_id=? "
            "ORDER BY b.created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d["tags"]) if d["tags"] else []
            out.append(d)
        return out

    def save_profile(self, user_id: str, bio_hash: str, interest_summary: str,
                     interest_tags: list[str]) -> None:
        self.conn.execute(
            "UPDATE users SET bio_hash=?, interest_summary=?, interest_tags=? WHERE user_id=?",
            (bio_hash, interest_summary, json.dumps(interest_tags), user_id))
        self.conn.commit()

    def pending_embedding(self, limit: int = 100, force: bool = False) -> list[dict]:
        where = ("WHERE enriched_at IS NOT NULL" if force
                 else "WHERE enriched_at IS NOT NULL AND embedded_at IS NULL")
        rows = self.conn.execute(
            f"SELECT message_id, title, summary, tags, created_at, hearts, comment_count "
            f"FROM posts {where} ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d["tags"]) if d["tags"] else []
            out.append(d)
        return out

    def set_embedded(self, message_id: str) -> None:
        self.conn.execute("UPDATE posts SET embedded_at=? WHERE message_id=?",
                          (_now(), message_id))
        self.conn.commit()

    def embedded_news_meta(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT message_id, hearts, comment_count FROM posts "
            "WHERE embedded_at IS NOT NULL")]

    # ---------- schedule / settings ----------

    def ensure_user(self, user_id: str, name: str | None = None) -> dict:
        self.conn.execute(
            "INSERT OR IGNORE INTO users(user_id, name) VALUES(?,?)",
            (user_id, name or user_id))
        self.conn.commit()
        return self.get_user(user_id)

    def get_settings(self, user_id: str) -> dict:
        r = self.conn.execute(
            "SELECT cohort, lt_room, lab_room FROM users WHERE user_id=?",
            (user_id,)).fetchone()
        if not r:
            return {"cohort": "4", "lt_room": "D302", "lab_room": "D305"}
        return dict(r)

    def set_settings(self, user_id: str, cohort: str, lt_room: str, lab_room: str) -> None:
        self.conn.execute(
            "UPDATE users SET cohort=?, lt_room=?, lab_room=? WHERE user_id=?",
            (cohort, lt_room, lab_room, user_id))
        self.conn.commit()

    def is_schedule_extracted(self, message_id: str) -> bool:
        r = self.conn.execute(
            "SELECT 1 FROM schedule_extracted WHERE message_id=?", (message_id,)).fetchone()
        return r is not None

    def save_schedule_extraction(self, message_id: str, events: list[dict], trace_id: str) -> int:
        if self.is_schedule_extracted(message_id):
            return 0
        for e in events:
            self.conn.execute(
                "INSERT INTO schedule_events(message_id, type, title, date, start, end, "
                "cohort, format, zoom_url, host, location, session_code, jump_url) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (message_id, e.get("type"), e.get("title"), e.get("date"), e.get("start"),
                 e.get("end"), e.get("cohort"), e.get("format"), e.get("zoom_url"),
                 e.get("host"), e.get("location"), e.get("session_code"), e.get("jump_url")))
        self.conn.execute(
            "INSERT INTO schedule_extracted(message_id, extracted_at, trace_id, event_count) "
            "VALUES(?,?,?,?)",
            (message_id, _now(), trace_id, len(events)))
        self.conn.commit()
        return len(events)

    def list_schedule_events(self, cohort: str, date_from: str, date_to: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM schedule_events WHERE date BETWEEN ? AND ? "
            "AND cohort IN (?, 'all') ORDER BY date, COALESCE(start,'99:99')",
            (date_from, date_to, cohort)).fetchall()
        return [dict(r) for r in rows]
