# News Ingestion Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Worker batch đọc bài từ Discord (hoặc seed JSON), enrich mỗi bài đúng một lần bằng agent OpenAI Agents SDK (tóm tắt tiếng Việt + 1-3 tag taxonomy + ảnh qua Tavily), lưu vĩnh viễn vào SQLite, và expose 3 API read-only cho UI.

**Architecture:** CLI `python -m ingest` → `Source.fetch(since=checkpoint)` → upsert raw vào SQLite → enrich các bài chưa có `enriched_at` (enrich-once, `--force` để chạy lại) → SessionLinker cho `#tài-nguyên` → checkpoint. FastAPI router chỉ đọc DB. Spec: `docs/superpowers/specs/2026-07-31-news-ingestion-pipeline-design.md`.

**Tech Stack:** Python 3.11+, openai-agents (Agents SDK), pydantic v2, sqlite3 (stdlib), httpx, discord.py, python-dotenv, FastAPI + uvicorn, pytest.

## Global Constraints

- Thư mục làm việc của MỌI lệnh: `codebase/backend/` (tạo venv tại đây).
- Model từ env `ENRICH_MODEL`, mặc định `gpt-5-mini`. Secrets qua `.env` (template `codebase/backend/.env.example` đã có sẵn — không sửa, không commit `.env`).
- Taxonomy tag CHÍNH XÁC 10 id: `ai-model ai-skill ai-tools api-mcp system-design uiux dataset soft-skills survey other` (khớp `codebase/ui/src/data/mock.js`).
- `summary_vi` 1-3 câu tiếng Việt; tags 1-3 phần tử.
- Enrich-once: bài có `enriched_at` không bao giờ được enrich lại trừ khi `--force`. `enrich_failed >= 3` → thôi retry.
- Không commit `companion.db`, `.env`, `eval/traces/` output (đã gitignore `*.db` thì thêm; kiểm tra `.gitignore` gốc repo có `.env` rồi).
- Trace mỗi lần enrich: `eval/traces/ingest/<message_id>.json`.
- Commit trên branch hiện tại (`dev/An` hoặc branch của người thực hiện), message tiếng Anh, kèm `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Scaffold backend + config

**Files:**
- Create: `codebase/backend/requirements.txt`
- Create: `codebase/backend/ingest/__init__.py` (rỗng)
- Create: `codebase/backend/ingest/config.py`
- Create: `codebase/backend/tests/__init__.py` (rỗng)
- Test: `codebase/backend/tests/test_config.py`

**Interfaces:**
- Produces: `Config` dataclass với fields `db_path: str`, `enrich_model: str`, `openai_api_key: str`, `tavily_api_key: str`, `discord_token: str`, `channel_ids: dict[str, str]` (keys: `chia-se`, `bai-hoc`, `tai-nguyen`); classmethod `Config.from_env() -> Config`.

- [ ] **Step 1: Tạo venv + requirements**

```bash
cd codebase/backend
python -m venv .venv
.venv\Scripts\activate
```

`requirements.txt`:

```
openai-agents>=0.2
pydantic>=2.7
httpx>=0.27
discord.py>=2.4
python-dotenv>=1.0
fastapi>=0.111
uvicorn>=0.30
pytest>=8.2
```

```bash
pip install -r requirements.txt
```

- [ ] **Step 2: Viết failing test**

`tests/test_config.py`:

```python
import os
from ingest.config import Config


def test_from_env_defaults(monkeypatch):
    for k in ["COMPANION_DB", "ENRICH_MODEL", "OPENAI_API_KEY", "TAVILY_API_KEY",
              "DISCORD_TOKEN", "DISCORD_CHANNEL_CHIA_SE", "DISCORD_CHANNEL_BAI_HOC",
              "DISCORD_CHANNEL_TAI_NGUYEN"]:
        monkeypatch.delenv(k, raising=False)
    cfg = Config.from_env()
    assert cfg.db_path == "companion.db"
    assert cfg.enrich_model == "gpt-5-mini"
    assert cfg.channel_ids == {"chia-se": "", "bai-hoc": "", "tai-nguyen": ""}


def test_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("COMPANION_DB", "x.db")
    monkeypatch.setenv("ENRICH_MODEL", "gpt-5")
    monkeypatch.setenv("DISCORD_CHANNEL_CHIA_SE", "111")
    cfg = Config.from_env()
    assert cfg.db_path == "x.db"
    assert cfg.enrich_model == "gpt-5"
    assert cfg.channel_ids["chia-se"] == "111"
```

- [ ] **Step 3: Chạy test, xác nhận FAIL** — `pytest tests/test_config.py -v` → `ModuleNotFoundError` hoặc `ImportError`.

- [ ] **Step 4: Implement `ingest/config.py`**

```python
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    db_path: str = "companion.db"
    enrich_model: str = "gpt-5-mini"
    openai_api_key: str = ""
    tavily_api_key: str = ""
    discord_token: str = ""
    channel_ids: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            db_path=os.getenv("COMPANION_DB", "companion.db"),
            enrich_model=os.getenv("ENRICH_MODEL", "gpt-5-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            channel_ids={
                "chia-se": os.getenv("DISCORD_CHANNEL_CHIA_SE", ""),
                "bai-hoc": os.getenv("DISCORD_CHANNEL_BAI_HOC", ""),
                "tai-nguyen": os.getenv("DISCORD_CHANNEL_TAI_NGUYEN", ""),
            },
        )
```

- [ ] **Step 5: `pytest tests/test_config.py -v` → PASS.** Lưu ý: nếu máy có `.env` thật, `load_dotenv` có thể làm test defaults fail — test đã `delenv` nên vẫn pass.

- [ ] **Step 6: Commit** — `git add codebase/backend` + `git commit -m "feat(ingest): scaffold backend package with config"`.

---

### Task 2: Models (RawPost / NewsEnrichment)

**Files:**
- Create: `codebase/backend/ingest/models.py`
- Test: `codebase/backend/tests/test_models.py`

**Interfaces:**
- Produces:
  - `TAG_IDS: list[str]` (10 id đúng thứ tự Global Constraints), `TagId` = `Literal[...]`.
  - `RawComment(BaseModel)`: `id: str, author: str, author_role: str = "Học viên", content: str, created_at: str`.
  - `RawPost(BaseModel)`: `message_id: str, channel: str, title: str, content: str, author: str, author_role: str = "Học viên", jump_url: str = "", created_at: str, hearts: int = 0, comments: list[RawComment] = []`.
  - `NewsEnrichment(BaseModel)`: `summary_vi: str`, `tags: list[TagId]` (min 1 max 3), `image_query: str`, `image_url: str | None = None`.

- [ ] **Step 1: Failing test** — `tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError
from ingest.models import NewsEnrichment, RawPost, TAG_IDS


def test_tag_ids_complete():
    assert TAG_IDS == ["ai-model", "ai-skill", "ai-tools", "api-mcp", "system-design",
                       "uiux", "dataset", "soft-skills", "survey", "other"]


def test_enrichment_rejects_unknown_tag():
    with pytest.raises(ValidationError):
        NewsEnrichment(summary_vi="x", tags=["blockchain"], image_query="q")


def test_enrichment_rejects_empty_and_too_many_tags():
    with pytest.raises(ValidationError):
        NewsEnrichment(summary_vi="x", tags=[], image_query="q")
    with pytest.raises(ValidationError):
        NewsEnrichment(summary_vi="x", tags=["other"] * 4, image_query="q")


def test_rawpost_defaults():
    p = RawPost(message_id="1", channel="bai-hoc", title="t", content="c",
                author="A", created_at="2026-07-31T10:00:00")
    assert p.author_role == "Học viên" and p.comments == [] and p.hearts == 0
```

- [ ] **Step 2: Chạy → FAIL** (`ModuleNotFoundError: ingest.models`).

- [ ] **Step 3: Implement `ingest/models.py`**

```python
from typing import Literal

from pydantic import BaseModel, Field

TAG_IDS = ["ai-model", "ai-skill", "ai-tools", "api-mcp", "system-design",
           "uiux", "dataset", "soft-skills", "survey", "other"]

TagId = Literal["ai-model", "ai-skill", "ai-tools", "api-mcp", "system-design",
                "uiux", "dataset", "soft-skills", "survey", "other"]


class RawComment(BaseModel):
    id: str
    author: str
    author_role: str = "Học viên"
    content: str
    created_at: str


class RawPost(BaseModel):
    message_id: str
    channel: str
    title: str
    content: str
    author: str
    author_role: str = "Học viên"
    jump_url: str = ""
    created_at: str
    hearts: int = 0
    comments: list[RawComment] = Field(default_factory=list)


class NewsEnrichment(BaseModel):
    summary_vi: str
    tags: list[TagId] = Field(min_length=1, max_length=3)
    image_query: str
    image_url: str | None = None
```

- [ ] **Step 4: `pytest tests/test_models.py -v` → PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(ingest): pydantic models with 10-tag taxonomy validation"`.

---

### Task 3: Store (SQLite, enrich-once, checkpoint)

**Files:**
- Create: `codebase/backend/ingest/store.py`
- Test: `codebase/backend/tests/test_store.py`

**Interfaces:**
- Consumes: `RawPost`, `NewsEnrichment` từ Task 2.
- Produces: class `Store`:
  - `__init__(db_path: str)` — tự tạo schema.
  - `upsert_post(p: RawPost) -> None` — bài mới: insert đủ; bài cũ: CHỈ update `hearts`, `comment_count` và insert comment mới (không đụng các cột enrich).
  - `pending_enrichment(limit: int = 20, force: bool = False) -> list[dict]` — dict có keys `message_id,title,content,channel`; mặc định lọc `enriched_at IS NULL AND enrich_failed < 3`; `force=True` trả mọi bài (vẫn theo limit, mới nhất trước).
  - `save_enrichment(message_id: str, e: NewsEnrichment, image_source: str, prompt_version: str, trace_id: str) -> None` — set `enriched_at` = now ISO, reset `enrich_failed = 0`.
  - `mark_enrich_failed(message_id: str, fallback_summary: str) -> None` — `enrich_failed += 1`, set `summary` fallback + `tags='["other"]'` nhưng KHÔNG set `enriched_at`.
  - `get_checkpoint(channel: str) -> int` (0 nếu chưa có), `set_checkpoint(channel: str, message_id: str) -> None` (chỉ tăng, không giảm).
  - `add_resource(message_id: str, kind: str, title: str, session_code: str | None, author: str, url: str, created_at: str) -> None`.
  - `list_news(tag: str | None = None) -> list[dict]` (chỉ bài `enriched_at IS NOT NULL`, sort `created_at` DESC, thêm key `hot: bool` = hearts+comment_count ≥ 20, `tags` đã parse thành list), `get_news(message_id: str) -> dict | None` (kèm `comments: list[dict]`), `list_resources() -> list[dict]`.

- [ ] **Step 1: Failing tests** — `tests/test_store.py`:

```python
from ingest.models import NewsEnrichment, RawComment, RawPost
from ingest.store import Store


def make_post(mid="100", hearts=5, n_comments=1):
    return RawPost(
        message_id=mid, channel="bai-hoc", title=f"Bài {mid}", content="Nội dung.",
        author="T001", created_at="2026-07-31T10:00:00", hearts=hearts,
        comments=[RawComment(id=f"{mid}-c{i}", author="T002", content="hay",
                             created_at="2026-07-31T11:00:00") for i in range(n_comments)],
    )


def test_upsert_insert_then_update(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.upsert_post(make_post(hearts=5, n_comments=1))
    s.upsert_post(make_post(hearts=9, n_comments=2))  # chạy lại: update, không nhân đôi
    rows = s.pending_enrichment()
    assert len(rows) == 1
    detail_pending = s.get_news("100")  # chưa enrich → get_news vẫn trả raw để debug
    assert detail_pending["hearts"] == 9
    assert len(detail_pending["comments"]) == 2


def test_enrich_once(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.upsert_post(make_post())
    e = NewsEnrichment(summary_vi="Tóm tắt.", tags=["ai-model"], image_query="q",
                       image_url="https://img/x.png")
    s.save_enrichment("100", e, image_source="tavily", prompt_version="v1", trace_id="tr1")
    assert s.pending_enrichment() == []                    # enrich-once
    assert len(s.pending_enrichment(force=True)) == 1      # --force thấy lại
    news = s.list_news()
    assert news[0]["tags"] == ["ai-model"] and news[0]["hot"] is False


def test_failed_counter_stops_at_3(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.upsert_post(make_post())
    for _ in range(3):
        assert len(s.pending_enrichment()) == 1
        s.mark_enrich_failed("100", "fallback")
    assert s.pending_enrichment() == []                    # đạt 3 lần → dừng retry


def test_checkpoint_monotonic(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    assert s.get_checkpoint("bai-hoc") == 0
    s.set_checkpoint("bai-hoc", "200")
    s.set_checkpoint("bai-hoc", "150")                     # không được tụt
    assert s.get_checkpoint("bai-hoc") == 200


def test_list_news_filter_tag_and_hot(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.upsert_post(make_post(mid="1", hearts=30, n_comments=0))
    s.upsert_post(make_post(mid="2", hearts=1, n_comments=0))
    e1 = NewsEnrichment(summary_vi="a", tags=["dataset"], image_query="q")
    e2 = NewsEnrichment(summary_vi="b", tags=["uiux"], image_query="q")
    s.save_enrichment("1", e1, "placeholder", "v1", "t1")
    s.save_enrichment("2", e2, "placeholder", "v1", "t2")
    assert [n["message_id"] for n in s.list_news(tag="dataset")] == ["1"]
    assert s.list_news()[0]["hot"] in (True, False)
    assert next(n for n in s.list_news() if n["message_id"] == "1")["hot"] is True
```

- [ ] **Step 2: Chạy → FAIL.**

- [ ] **Step 3: Implement `ingest/store.py`**

```python
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
        self.conn = sqlite3.connect(db_path)
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
```

- [ ] **Step 4: `pytest tests/test_store.py -v` → PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(ingest): sqlite store with enrich-once and checkpoints"`.

---

### Task 4: SeedSource + seed data

**Files:**
- Create: `codebase/backend/ingest/sources.py` (phần Source + SeedSource; DiscordSource ở Task 8)
- Create: `codebase/backend/ingest/seeds/posts.json`
- Test: `codebase/backend/tests/test_sources_seed.py`

**Interfaces:**
- Produces: `class Source(Protocol): fetch(since: dict[str, int]) -> list[RawPost]` (since = checkpoint theo channel); `SeedSource(path: str)` implement `fetch`.

- [ ] **Step 1: Tạo `ingest/seeds/posts.json`** — 10 bài giả tiếng Việt (data TỰ TẠO, không copy nguyên văn từ Discord thật). Cấu trúc mỗi phần tử = RawPost. Nội dung: 4 bài `bai-hoc` kỹ thuật (BEV/dataset CV, tool eval, MCP, folder-as-architecture), 2 bài `chia-se` (prompt caching, shadcn UI), 2 khảo sát (`survey`), 1 meme recap (`other`), 1 bài soft-skill "làm chủ AI". message_id tăng dần "1001".."1010", mỗi bài 0-2 comments. Ví dụ 2 phần tử đầu (viết đủ 10 theo mẫu):

```json
[
  {
    "message_id": "1001",
    "channel": "bai-hoc",
    "title": "[Deep-dive] BEV — góc nhìn từ trên xuống của xe tự hành",
    "content": "BEV đưa dữ liệu camera/LiDAR về một mặt phẳng nhìn từ trên xuống để hợp nhất cảm biến. Bài giải thích pipeline BEVFormer và demo trên nuScenes.",
    "author": "GR16 — T112",
    "author_role": "Học viên",
    "jump_url": "https://discord.com/channels/1/2/1001",
    "created_at": "2026-07-30T09:00:00",
    "hearts": 23,
    "comments": [
      {"id": "1001-c1", "author": "T057 — A.Minh", "author_role": "Học viên",
       "content": "Phần chiếu multi-camera dễ hiểu quá!", "created_at": "2026-07-30T10:00:00"}
    ]
  },
  {
    "message_id": "1002",
    "channel": "chia-se",
    "title": "Prompt caching giảm 80% chi phí gọi API",
    "content": "Cố định phần context tĩnh lên đầu request để cache hit khi chạy eval lặp lại. Kèm số liệu trước/sau và các lỗi gây cache miss.",
    "author": "T093 — D.Phúc",
    "author_role": "Học viên",
    "jump_url": "https://discord.com/channels/1/2/1002",
    "created_at": "2026-07-30T11:00:00",
    "hearts": 27,
    "comments": []
  }
]
```

- [ ] **Step 2: Failing test** — `tests/test_sources_seed.py`:

```python
from ingest.sources import SeedSource

SEED = "ingest/seeds/posts.json"


def test_seed_loads_all_posts():
    posts = SeedSource(SEED).fetch(since={})
    assert len(posts) == 10
    assert posts[0].message_id and posts[0].channel in ("bai-hoc", "chia-se")


def test_seed_respects_checkpoint():
    src = SeedSource(SEED)
    all_posts = src.fetch(since={})
    max_id = max(int(p.message_id) for p in all_posts)
    assert src.fetch(since={"bai-hoc": max_id, "chia-se": max_id}) == []
```

- [ ] **Step 3: Chạy → FAIL.**

- [ ] **Step 4: Implement phần SeedSource trong `ingest/sources.py`**

```python
import json
from pathlib import Path
from typing import Protocol

from .models import RawPost


class Source(Protocol):
    def fetch(self, since: dict[str, int]) -> list[RawPost]: ...


class SeedSource:
    def __init__(self, path: str):
        self.path = Path(path)

    def fetch(self, since: dict[str, int]) -> list[RawPost]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        posts = [RawPost(**item) for item in data]
        return [p for p in posts
                if int(p.message_id) > since.get(p.channel, 0)]
```

- [ ] **Step 5: `pytest tests/test_sources_seed.py -v` → PASS.**
- [ ] **Step 6: Commit** — `git commit -m "feat(ingest): seed source with 10 fabricated posts"`.

---

### Task 5: SessionLinker (tầng regex/alias)

**Files:**
- Create: `codebase/backend/ingest/linker.py`
- Test: `codebase/backend/tests/test_linker.py`

**Interfaces:**
- Produces: `detect_session(title: str) -> str | None` (trả mã chuẩn `WS-3`/`LT-11`/`Lab-10`/`OH-5`), `detect_kind(title: str) -> str` (`slide|record|doc|link`). (Tầng 2 agent-fallback KHÔNG làm ở vòng này — ghi chú TODO có chủ đích trong docstring, spec cho phép vì tầng 1 phủ hầu hết bài `#tài-nguyên` thực tế.)

- [ ] **Step 1: Failing test** — `tests/test_linker.py`:

```python
import pytest
from ingest.linker import detect_kind, detect_session


@pytest.mark.parametrize("title,expected", [
    ("Slide Workshop WS2: Problem → MVP Canvas", "WS-2"),
    ("Video Recording WS1: Kick off", "WS-1"),
    ("Record LT-10: Eval & Golden set", "LT-10"),
    ("Slide buổi lý thuyết 11 — Agent & tool use", "LT-11"),
    ("Đề bài + hướng dẫn Lab 10 (Discord bot)", "Lab-10"),
    ("Thông tin Workshop 3 tối nay", "WS-3"),
    ("Ngân hàng đề chính thức Build Phase", None),
    ("Tổng quan chương trình 6 tuần", None),
])
def test_detect_session(title, expected):
    assert detect_session(title) == expected


@pytest.mark.parametrize("title,expected", [
    ("Slide Workshop WS2", "slide"),
    ("Video Recording WS1", "record"),
    ("Record LT-10: Eval", "record"),
    ("Đề bài + hướng dẫn Lab 10", "doc"),
    ("Worksheet JTBD bản dịch", "link"),
])
def test_detect_kind(title, expected):
    assert detect_kind(title) == expected
```

- [ ] **Step 2: Chạy → FAIL.**

- [ ] **Step 3: Implement `ingest/linker.py`**

```python
"""SessionLinker tầng 1 — regex/alias. Tầng 2 (agent fallback cho case mơ hồ)
để vòng sau, theo spec §4."""
import re

_PATTERNS = [
    (re.compile(r"\bWS[\s-]?(\d+)\b", re.I), "WS"),
    (re.compile(r"\bworkshop\s*(\d+)\b", re.I), "WS"),
    (re.compile(r"\bLT[\s-]?(\d+)\b", re.I), "LT"),
    (re.compile(r"lý thuyết\s*(\d+)", re.I), "LT"),
    (re.compile(r"\bLab[\s-]?(\d+)\b", re.I), "Lab"),
    (re.compile(r"\bOH[\s-]?(\d+)\b", re.I), "OH"),
    (re.compile(r"office hour\s*(\d+)", re.I), "OH"),
]

_KIND_KEYWORDS = [
    ("record", ["record", "recording", "video"]),
    ("slide", ["slide"]),
    ("doc", ["đề bài", "hướng dẫn", "đề ", "tài liệu", "ngân hàng"]),
]


def detect_session(title: str) -> str | None:
    for pattern, prefix in _PATTERNS:
        m = pattern.search(title)
        if m:
            return f"{prefix}-{int(m.group(1))}"
    return None


def detect_kind(title: str) -> str:
    low = title.lower()
    for kind, words in _KIND_KEYWORDS:
        if any(w in low for w in words):
            return kind
    return "link"
```

Lưu ý thứ tự `_KIND_KEYWORDS`: "Video Recording" phải ra `record` trước khi khớp gì khác — record đứng đầu danh sách.

- [ ] **Step 4: `pytest tests/test_linker.py -v` → PASS.** Nếu case "Slide buổi lý thuyết 11" fail: regex `lý thuyết\s*(\d+)` cần khớp sau chữ "buổi" — đã cover vì search toàn chuỗi.
- [ ] **Step 5: Commit** — `git commit -m "feat(ingest): session linker tier-1 regex/alias"`.

---

### Task 6: Prompts + NewsEnricher (Agents SDK + Tavily tool)

**Files:**
- Create: `codebase/backend/ingest/prompts.py`
- Create: `codebase/backend/ingest/enrich.py`
- Test: `codebase/backend/tests/test_enrich.py`

**Interfaces:**
- Consumes: `NewsEnrichment`, `TAG_IDS` (Task 2); `Config` (Task 1).
- Produces:
  - `prompts.PROMPT_VERSION = "v1"`, `prompts.ENRICH_V1: str`.
  - `enrich.pick_image(images: list[str]) -> str | None` — lọc URL hợp lệ.
  - `enrich.enrich_post(post: dict, cfg: Config, runner=None) -> tuple[NewsEnrichment, str, str]` — trả `(enrichment, image_source, trace_id)`; `runner` injectable (callable nhận `input_text` trả `NewsEnrichment`) để test không gọi API; mặc định dùng `Runner.run_sync` với agent thật. Ghi trace JSON vào `eval/traces/ingest/<message_id>.json` (đường dẫn gốc repo, tạo thư mục nếu chưa có).

- [ ] **Step 1: Viết `ingest/prompts.py`** (không cần test riêng — hằng số):

```python
PROMPT_VERSION = "v1"

ENRICH_V1 = """Bạn là biên tập viên bản tin nội bộ của khoá học AI Thực Chiến.
Nhiệm vụ: đọc MỘT bài đăng Discord và trả về đúng schema yêu cầu.

QUY TẮC TÓM TẮT (summary_vi):
- 1 đến 3 câu tiếng Việt, trung thực với nội dung bài — TUYỆT ĐỐI không thêm
  thông tin không có trong bài.
- Giữ nguyên thuật ngữ kỹ thuật (RAG, BEV, prompt caching...).

QUY TẮC GẮN TAG (tags — chọn 1 đến 3):
- ai-model: kiến trúc/mô hình AI (BEV, transformer, LLM nội bộ...)
- ai-skill: kỹ năng dùng AI hiệu quả (prompt, review output, học với AI)
- ai-tools: công cụ AI cụ thể (Claude Code, Copilot, shadcn generator...)
- api-mcp: gọi API model, MCP, tool calling, chi phí/caching API
- system-design: kiến trúc hệ thống, tổ chức code, pipeline
- uiux: thiết kế giao diện, trải nghiệm người dùng
- dataset: bộ dữ liệu, thu thập/chọn dữ liệu
- soft-skills: kỹ năng mềm, teamwork, quản lý thời gian, suy ngẫm
- survey: bài xin điền khảo sát/form thu thập ý kiến
- other: không khớp tag nào ở trên
- Không chắc thì chọn ÍT tag lại. Không khớp gì → ["other"].

QUY TẮC ẢNH:
- Tạo image_query TIẾNG ANH ngắn mô tả chủ đề trực quan của bài
  (vd "bird's eye view autonomous driving perception").
- Gọi tool search_image ĐÚNG MỘT LẦN với image_query đó, điền kết quả vào
  image_url. Tool trả chuỗi rỗng → để image_url = null.

VÍ DỤ 1 — bài: "Prompt caching giảm 80% chi phí… cố định context tĩnh…"
→ summary_vi: "Cố định phần context tĩnh lên đầu request giúp cache hit khi
chạy eval lặp lại, giảm khoảng 80% chi phí. Bài kèm số liệu trước/sau và các
lỗi thường gây cache miss." · tags: ["api-mcp","ai-skill"]
· image_query: "api cost optimization caching diagram"

VÍ DỤ 2 — bài: "Nhóm mình cần khảo sát khó khăn khi làm Lab demo, 1 phút thôi…"
→ summary_vi: "Nhóm cần dữ liệu về khó khăn của học viên trong buổi thực hành
để làm evidence. Form 1 phút, nhận khảo sát chéo qua DM."
· tags: ["survey"] · image_query: "student survey form clipboard"
"""
```

- [ ] **Step 2: Failing test** — `tests/test_enrich.py` (không gọi API thật):

```python
import json
from ingest.config import Config
from ingest.enrich import enrich_post, pick_image
from ingest.models import NewsEnrichment


def test_pick_image_filters_bad_urls():
    assert pick_image(["http://x/a.png", "https://x/logo.svg",
                       "https://x/photo.jpg"]) == "https://x/photo.jpg"
    assert pick_image([]) is None


def test_enrich_post_with_injected_runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # trace ghi vào cwd/eval/traces/ingest/
    fake = NewsEnrichment(summary_vi="Tóm tắt.", tags=["survey"],
                          image_query="q", image_url="https://x/p.jpg")
    post = {"message_id": "1009", "title": "Khảo sát", "content": "...",
            "channel": "bai-hoc"}
    e, image_source, trace_id = enrich_post(post, Config(), runner=lambda text: fake)
    assert e.tags == ["survey"] and image_source == "tavily"
    trace = json.loads(
        (tmp_path / "eval/traces/ingest/1009.json").read_text(encoding="utf-8"))
    assert trace["prompt_version"] == "v1" and trace["output"]["tags"] == ["survey"]


def test_enrich_post_placeholder_when_no_image(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake = NewsEnrichment(summary_vi="x", tags=["other"], image_query="q",
                          image_url=None)
    post = {"message_id": "1010", "title": "t", "content": "c", "channel": "chia-se"}
    _, image_source, _ = enrich_post(post, Config(), runner=lambda text: fake)
    assert image_source == "placeholder"
```

- [ ] **Step 3: Chạy → FAIL.**

- [ ] **Step 4: Implement `ingest/enrich.py`**

```python
import json
import uuid
from pathlib import Path

import httpx
from agents import Agent, Runner, function_tool

from .config import Config
from .models import NewsEnrichment
from .prompts import ENRICH_V1, PROMPT_VERSION

TRACE_DIR = Path("eval/traces/ingest")
_BAD_SUFFIXES = (".svg", ".ico", ".gif")


def pick_image(images: list[str]) -> str | None:
    for url in images:
        low = url.lower()
        if low.startswith("https://") and not low.endswith(_BAD_SUFFIXES) \
                and "logo" not in low and "favicon" not in low:
            return url
    return None


def _tavily_images(query: str, api_key: str) -> list[str]:
    if not api_key:
        return []
    try:
        resp = httpx.post("https://api.tavily.com/search", timeout=10.0, json={
            "api_key": api_key, "query": query,
            "include_images": True, "max_results": 3,
        })
        resp.raise_for_status()
        return resp.json().get("images", [])
    except httpx.HTTPError:
        return []


def build_agent(cfg: Config) -> Agent:
    @function_tool
    def search_image(query: str) -> str:
        """Tìm 1 ảnh minh hoạ theo query tiếng Anh. Trả URL, hoặc chuỗi rỗng."""
        return pick_image(_tavily_images(query, cfg.tavily_api_key)) or ""

    return Agent(
        name="news_enricher",
        instructions=ENRICH_V1,
        model=cfg.enrich_model,
        output_type=NewsEnrichment,
        tools=[search_image],
    )


def enrich_post(post: dict, cfg: Config, runner=None) -> tuple[NewsEnrichment, str, str]:
    """runner: callable(input_text) -> NewsEnrichment; None = agent thật."""
    input_text = (f"Kênh: #{post['channel']}\nTiêu đề: {post['title']}\n"
                  f"Nội dung:\n{post['content']}")
    usage = None
    if runner is None:
        agent = build_agent(cfg)
        result = Runner.run_sync(agent, input_text)
        enrichment: NewsEnrichment = result.final_output
        u = result.context_wrapper.usage
        usage = {"requests": u.requests, "input_tokens": u.input_tokens,
                 "output_tokens": u.output_tokens}
    else:
        enrichment = runner(input_text)

    if enrichment.image_url:
        image_source = "tavily"
    else:
        image_source = "placeholder"

    trace_id = uuid.uuid4().hex[:12]
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    (TRACE_DIR / f"{post['message_id']}.json").write_text(json.dumps({
        "trace_id": trace_id,
        "message_id": post["message_id"],
        "prompt_version": PROMPT_VERSION,
        "model": cfg.enrich_model,
        "input": input_text[:500],
        "output": enrichment.model_dump(),
        "image_source": image_source,
        "usage": usage,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return enrichment, image_source, trace_id
```

- [ ] **Step 5: `pytest tests/test_enrich.py -v` → PASS.**
- [ ] **Step 6: Commit** — `git commit -m "feat(ingest): agents-sdk news enricher with tavily image tool"`.

---

### Task 7: Pipeline `run_once` + CLI

**Files:**
- Create: `codebase/backend/ingest/__main__.py`
- Test: `codebase/backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `Store` (Task 3), `SeedSource` (Task 4), `detect_session/detect_kind` (Task 5), `enrich_post` (Task 6).
- Produces: `run_once(store: Store, source, cfg: Config, limit: int = 20, force: bool = False, runner=None) -> dict` trả `{"fetched": int, "enriched": int, "failed": int}`. CLI: `python -m ingest [--source seed|discord] [--loop MIN] [--force] [--limit N] [--db PATH] [--seed PATH]`.

- [ ] **Step 1: Failing test** — `tests/test_pipeline.py`:

```python
from ingest.__main__ import run_once
from ingest.config import Config
from ingest.models import NewsEnrichment
from ingest.sources import SeedSource
from ingest.store import Store

SEED = "ingest/seeds/posts.json"


def fake_runner(text):
    return NewsEnrichment(summary_vi="Tóm tắt giả.", tags=["other"],
                          image_query="q", image_url=None)


def failing_runner(text):
    raise RuntimeError("api down")


def test_run_once_then_enrich_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path.parent if False else ".")  # giữ cwd backend
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    stats1 = run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    assert stats1["fetched"] == 10 and stats1["enriched"] == 10
    stats2 = run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    assert stats2["fetched"] == 0 and stats2["enriched"] == 0  # checkpoint + enrich-once


def test_run_once_force_reenriches(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    stats = run_once(store, SeedSource(SEED), cfg, force=True, runner=fake_runner)
    assert stats["enriched"] == 10


def test_run_once_failure_marks_and_continues(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    stats = run_once(store, SeedSource(SEED), cfg, runner=failing_runner)
    assert stats["failed"] == 10 and stats["enriched"] == 0
    row = store.get_news("1001")
    assert row["enrich_failed"] == 1 and row["tags"] == ["other"]
```

Lưu ý: test chạy từ `codebase/backend` nên trace ghi vào `eval/traces/ingest/` tương đối — chấp nhận được (gitignore), hoặc chạy pytest với `--basetemp`.

- [ ] **Step 2: Chạy → FAIL.**

- [ ] **Step 3: Implement `ingest/__main__.py`**

```python
import argparse
import time

from .config import Config
from .enrich import enrich_post
from .linker import detect_kind, detect_session
from .sources import SeedSource
from .store import Store


def _fallback_summary(content: str) -> str:
    sentences = content.replace("\n", " ").split(". ")
    return (". ".join(sentences[:2]))[:200]


def run_once(store: Store, source, cfg: Config, limit: int = 20,
             force: bool = False, runner=None) -> dict:
    since = {ch: store.get_checkpoint(ch)
             for ch in ("chia-se", "bai-hoc", "tai-nguyen")}
    posts = source.fetch(since=since)
    for p in posts:
        if p.channel == "tai-nguyen":
            store.add_resource(p.message_id, detect_kind(p.title), p.title,
                               detect_session(p.title), p.author, p.jump_url,
                               p.created_at)
        else:
            store.upsert_post(p)
        store.set_checkpoint(p.channel, p.message_id)

    enriched = failed = 0
    for row in store.pending_enrichment(limit=limit, force=force):
        try:
            e, image_source, trace_id = enrich_post(row, cfg, runner=runner)
            store.save_enrichment(row["message_id"], e, image_source,
                                  prompt_version="v1", trace_id=trace_id)
            enriched += 1
        except Exception as exc:  # enrich lỗi: fallback, không dừng lượt chạy
            print(f"[enrich-fail] {row['message_id']}: {exc}")
            store.mark_enrich_failed(row["message_id"],
                                     _fallback_summary(row["content"]))
            failed += 1
    return {"fetched": len(posts), "enriched": enriched, "failed": failed}


def main():
    ap = argparse.ArgumentParser(prog="ingest")
    ap.add_argument("--source", choices=["seed", "discord"], default="seed")
    ap.add_argument("--loop", type=int, default=0, help="phút giữa các lượt; 0 = 1 lượt")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--db", default=None)
    ap.add_argument("--seed", default="ingest/seeds/posts.json")
    args = ap.parse_args()

    cfg = Config.from_env()
    store = Store(args.db or cfg.db_path)
    if args.source == "seed":
        source = SeedSource(args.seed)
    else:
        from .sources import DiscordSource  # Task 8
        source = DiscordSource(cfg.discord_token, cfg.channel_ids)

    while True:
        stats = run_once(store, source, cfg, limit=args.limit, force=args.force)
        print(f"[ingest] {stats}")
        if not args.loop:
            break
        args.force = False  # force chỉ áp dụng lượt đầu
        time.sleep(args.loop * 60)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: `pytest tests/test_pipeline.py -v` → PASS.**
- [ ] **Step 5: Chạy tay end-to-end (không cần API key):** tạm thời chưa chạy được enrich thật — chạy `python -m ingest --source seed --db demo.db` với `OPENAI_API_KEY` trong `.env`; nếu chưa có key thì bỏ qua bước này (test đã phủ). Xoá `demo.db` sau khi thử.
- [ ] **Step 6: Commit** — `git commit -m "feat(ingest): run_once pipeline and CLI with loop/force flags"`.

---

### Task 8: DiscordSource

**Files:**
- Modify: `codebase/backend/ingest/sources.py` (thêm mapping + DiscordSource)
- Test: `codebase/backend/tests/test_sources_discord.py` (chỉ test mapping — không gọi Discord thật)

**Interfaces:**
- Produces: `map_role(role_names: list[str]) -> str` ("Lab Coach"|"BTC"|"Mentor"|"Học viên"); `thread_to_rawpost(thread_id, channel_key, title, starter_content, author_name, role_names, jump_url, created_at_iso, hearts, comment_tuples) -> RawPost` với `comment_tuples: list[tuple[id, author, role_names, content, created_at_iso]]`; `DiscordSource(token, channel_ids).fetch(since)` dùng discord.py.

- [ ] **Step 1: Failing test** — `tests/test_sources_discord.py`:

```python
from ingest.sources import map_role, thread_to_rawpost


def test_map_role():
    assert map_role(["Lab Coach", "Member"]) == "Lab Coach"
    assert map_role(["BTC"]) == "BTC"
    assert map_role(["Admin"]) == "BTC"
    assert map_role(["Mentor 2026"]) == "Mentor"
    assert map_role(["Member"]) == "Học viên"
    assert map_role([]) == "Học viên"


def test_thread_to_rawpost_maps_fields():
    p = thread_to_rawpost(
        thread_id="555", channel_key="bai-hoc", title="Bài chia sẻ",
        starter_content="Nội dung", author_name="T001", role_names=["Member"],
        jump_url="https://discord.com/x", created_at_iso="2026-07-31T09:00:00",
        hearts=7,
        comment_tuples=[("556", "T002", ["Lab Coach"], "hay", "2026-07-31T10:00:00")],
    )
    assert p.message_id == "555" and p.channel == "bai-hoc"
    assert p.comments[0].author_role == "Lab Coach" and p.hearts == 7
```

- [ ] **Step 2: Chạy → FAIL.**

- [ ] **Step 3: Implement — thêm vào `ingest/sources.py`**

```python
def map_role(role_names: list[str]) -> str:
    joined = " ".join(role_names).lower()
    if "coach" in joined:
        return "Lab Coach"
    if "btc" in joined or "admin" in joined:
        return "BTC"
    if "mentor" in joined:
        return "Mentor"
    return "Học viên"


def thread_to_rawpost(thread_id, channel_key, title, starter_content, author_name,
                      role_names, jump_url, created_at_iso, hearts,
                      comment_tuples) -> RawPost:
    from .models import RawComment
    return RawPost(
        message_id=str(thread_id), channel=channel_key, title=title,
        content=starter_content, author=author_name,
        author_role=map_role(role_names), jump_url=jump_url,
        created_at=created_at_iso, hearts=hearts,
        comments=[RawComment(id=str(cid), author=a, author_role=map_role(r),
                             content=c, created_at=t)
                  for cid, a, r, c, t in comment_tuples],
    )


class DiscordSource:
    """Đọc forum channels qua discord.py: connect ngắn, fetch, rồi thoát.
    Cần bật MESSAGE CONTENT INTENT trong Discord Developer Portal."""

    def __init__(self, token: str, channel_ids: dict[str, str]):
        self.token = token
        self.channel_ids = {k: v for k, v in channel_ids.items() if v}

    def fetch(self, since: dict[str, int]) -> list[RawPost]:
        import asyncio
        import discord

        results: list[RawPost] = []
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            try:
                for key, cid in self.channel_ids.items():
                    channel = client.get_channel(int(cid)) or \
                        await client.fetch_channel(int(cid))
                    threads = list(channel.threads)
                    async for t in channel.archived_threads(limit=50):
                        threads.append(t)
                    for thread in threads:
                        if thread.id <= since.get(key, 0):
                            continue
                        try:
                            starter = await thread.fetch_message(thread.id)
                        except discord.NotFound:
                            continue
                        comments = []
                        async for m in thread.history(limit=50, oldest_first=True):
                            if m.id == thread.id or m.author.bot:
                                continue
                            roles = [r.name for r in getattr(m.author, "roles", [])]
                            comments.append((m.id, m.author.display_name, roles,
                                             m.content, m.created_at.isoformat()))
                        roles = [r.name for r in getattr(starter.author, "roles", [])]
                        hearts = sum(r.count for r in starter.reactions)
                        results.append(thread_to_rawpost(
                            thread.id, key, thread.name, starter.content,
                            starter.author.display_name, roles, starter.jump_url,
                            thread.created_at.isoformat(), hearts, comments))
            finally:
                await client.close()

        asyncio.run(client.start(self.token))
        return results
```

- [ ] **Step 4: `pytest tests/test_sources_discord.py -v` → PASS** (mapping tests; `fetch` không chạy trong CI).
- [ ] **Step 5: Manual verify (khi có server test + token):** điền `.env` → `python -m ingest --source discord --db demo.db --limit 3` → mở DB xem 3 bài có summary/tags. Ghi kết quả (số bài, 1 ví dụ tags) vào PR description. Chưa có server test thì đánh dấu bước này pending — không chặn các task sau.
- [ ] **Step 6: Commit** — `git commit -m "feat(ingest): discord forum source with role mapping"`.

---

### Task 9: API read-only cho UI

**Files:**
- Create: `codebase/backend/api/__init__.py` (rỗng)
- Create: `codebase/backend/api/main.py`
- Test: `codebase/backend/tests/test_api.py`

**Interfaces:**
- Consumes: `Store` (Task 3).
- Produces: FastAPI app `api.main:app` với `GET /api/news?tag=`, `GET /api/news/{message_id}` (404 nếu không có), `GET /api/resources`. App đọc DB path từ `Config.from_env()`; test override qua `app.state.store`.

- [ ] **Step 1: Failing test** — `tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from api.main import app, get_store
from ingest.models import NewsEnrichment
from ingest.store import Store
from tests.test_store import make_post


def make_client(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    store.upsert_post(make_post(mid="1", hearts=30))
    store.save_enrichment("1", NewsEnrichment(
        summary_vi="Tóm tắt.", tags=["dataset"], image_query="q",
        image_url=None), "placeholder", "v1", "t1")
    store.add_resource("9", "slide", "Slide WS2", "WS-2", "BTC",
                       "https://x", "2026-07-30T09:00:00")
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_list_news_and_tag_filter(tmp_path):
    client = make_client(tmp_path)
    body = client.get("/api/news").json()
    assert body[0]["message_id"] == "1" and body[0]["hot"] is True
    assert client.get("/api/news?tag=uiux").json() == []


def test_news_detail_with_comments_and_404(tmp_path):
    client = make_client(tmp_path)
    detail = client.get("/api/news/1").json()
    assert detail["summary"] == "Tóm tắt." and len(detail["comments"]) == 1
    assert client.get("/api/news/999").status_code == 404


def test_resources(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/resources").json()[0]["session_code"] == "WS-2"
```

- [ ] **Step 2: Chạy → FAIL.**

- [ ] **Step 3: Implement `api/main.py`**

```python
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ingest.config import Config
from ingest.store import Store

app = FastAPI(title="Companion API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


def get_store() -> Store:
    return Store(Config.from_env().db_path)


@app.get("/api/news")
def list_news(tag: str | None = None, store: Store = Depends(get_store)):
    return store.list_news(tag=tag)


@app.get("/api/news/{message_id}")
def news_detail(message_id: str, store: Store = Depends(get_store)):
    news = store.get_news(message_id)
    if news is None or news.get("enriched_at") is None:
        raise HTTPException(404)
    return news


@app.get("/api/resources")
def resources(store: Store = Depends(get_store)):
    return store.list_resources()
```

- [ ] **Step 4: `pytest tests/test_api.py -v` → PASS.**
- [ ] **Step 5: Chạy tay:** `uvicorn api.main:app --port 8000` → mở `http://localhost:8000/api/news` thấy JSON (sau khi đã chạy `python -m ingest --source seed`).
- [ ] **Step 6: Commit** — `git commit -m "feat(api): read-only news/resources endpoints for UI"`.

---

### Task 10: Smoke set + README backend

**Files:**
- Create: `codebase/backend/ingest/smoke.py`
- Create: `codebase/backend/tests/smoke_posts.json`
- Create: `codebase/backend/README.md`

**Interfaces:**
- Consumes: `enrich_post` (Task 6), `Config` (Task 1).
- Produces: `python -m ingest.smoke` — chạy enrich THẬT trên ~10 bài, in bảng kết quả, exit code 1 nếu fail. Không chạy trong pytest CI (cần API key).

- [ ] **Step 1: Tạo `tests/smoke_posts.json`** — copy 10 bài từ `ingest/seeds/posts.json`, mỗi phần tử thêm `"expected_tags": [...]` (1-2 tag hợp lý; bài 1001 → `["ai-model"]`, 1002 → `["api-mcp"]`, khảo sát → `["survey"]`, meme → `["other"]`…).

- [ ] **Step 2: Implement `ingest/smoke.py`**

```python
"""Smoke check prompt enrich: python -m ingest.smoke (cần OPENAI_API_KEY).
Pass khi mỗi bài có >=1 tag trùng expected_tags và summary <= 3 câu."""
import json
import sys
from pathlib import Path

from .config import Config
from .enrich import enrich_post


def main():
    cfg = Config.from_env()
    if not cfg.openai_api_key:
        print("SKIP: thiếu OPENAI_API_KEY")
        return
    cases = json.loads(Path("tests/smoke_posts.json").read_text(encoding="utf-8"))
    failures = 0
    for c in cases:
        e, _, _ = enrich_post(
            {"message_id": f"smoke-{c['message_id']}", "title": c["title"],
             "content": c["content"], "channel": c["channel"]}, cfg)
        tag_ok = bool(set(e.tags) & set(c["expected_tags"]))
        sent_ok = e.summary_vi.count(".") <= 3
        status = "OK " if (tag_ok and sent_ok) else "FAIL"
        failures += 0 if (tag_ok and sent_ok) else 1
        print(f"[{status}] {c['message_id']} tags={e.tags} "
              f"expected={c['expected_tags']}")
    print(f"=> {len(cases) - failures}/{len(cases)} pass")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Chạy tay khi có key:** `python -m ingest.smoke` → kỳ vọng ≥8/10 pass; nếu thấp hơn, chỉnh mô tả tag trong `prompts.py` (nâng `PROMPT_VERSION` lên `v2`) rồi chạy lại — ghi kết quả 2 lượt vào commit message.

- [ ] **Step 4: Viết `codebase/backend/README.md`**

````markdown
# Companion backend — ingestion + API

## Setup
```bash
cd codebase/backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # điền OPENAI_API_KEY (+ TAVILY, DISCORD nếu có)
```

## Chạy
```bash
python -m ingest --source seed          # ingest + enrich seed (enrich-once)
python -m ingest --source discord       # đọc forum thật (cần token + channel id)
python -m ingest --loop 30              # lặp mỗi 30 phút
python -m ingest --force                # enrich lại (khi đổi prompt version)
uvicorn api.main:app --port 8000        # API cho UI (CORS localhost:5173)
pytest                                  # unit tests (không gọi API ngoài)
python -m ingest.smoke                  # smoke prompt (cần OPENAI_API_KEY)
```

Enrich-once: bài đã có `enriched_at` trong `companion.db` không bao giờ bị
enrich lại (không tốn phí) trừ khi `--force`. Trace từng lời gọi AI nằm ở
`eval/traces/ingest/`. Spec: `docs/superpowers/specs/2026-07-31-news-ingestion-pipeline-design.md`.
````

- [ ] **Step 5: Thêm gitignore backend** — kiểm tra `.gitignore` gốc repo đã có `.env`, thêm nếu thiếu: `*.db`, `.venv/`, `__pycache__/`, `eval/traces/`.

- [ ] **Step 6: Chạy toàn bộ test lần cuối** — `pytest -v` từ `codebase/backend` → tất cả PASS.

- [ ] **Step 7: Commit** — `git commit -m "feat(ingest): smoke runner, backend README and gitignore"`.

---

## Self-review đã chạy

- **Spec coverage:** §2 flow (Task 7) · §3 enricher/prompt/trace (Task 6) · §4 linker tầng 1 (Task 5; tầng 2 agent-fallback hoãn có chủ đích, ghi trong docstring) · §5 schema (Task 3) · §6 API (Task 9) · §7 error/env (Task 6, 7, 10; `.env.example` đã tồn tại) · §8 smoke + unit (Task 3, 5, 7, 10).
- **Type consistency:** `Store.pending_enrichment` trả `list[dict]` với keys mà `enrich_post(post: dict)` đọc (`message_id,title,content,channel`) — khớp; `run_once(runner=...)` truyền xuyên xuống `enrich_post(runner=...)` — khớp; `since: dict[str,int]` thống nhất Task 4/7/8.
- **Placeholder:** không còn TBD; điểm hoãn duy nhất (linker tầng 2) là quyết định phạm vi có ghi chú, không phải placeholder.
