# RecSys Personalized Recommendations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed tóm tắt news vào Qdrant embedded; suy luận sở thích user từ bio + bookmarks bằng agent; API gợi ý cá nhân hoá (similarity + engagement + recency, MMR đa dạng); UI section "Dành cho bạn" gọi API thật với fallback mock.

**Architecture:** Package `recsys/` (embedder · vectorstore · profile · recommend · prompts · seeds); hook embed vào `run_once` (embed-once qua cột `embedded_at`); API users/bookmarks/recommendations với lazy profile re-infer theo `bio_hash`. Spec: `docs/superpowers/specs/2026-07-31-recsys-personalized-recommendations-design.md`.

**Tech Stack:** qdrant-client (embedded local), openai (embeddings), openai-agents (profile inferencer), FastAPI, pytest; UI React hiện có.

## Global Constraints

- Backend cwd: `codebase/backend`; python = `.venv/Scripts/python.exe`. UI cwd: `codebase/ui`.
- `.env` thật đã có key — bước nào gọi API thật sẽ ghi rõ; unit tests KHÔNG gọi API ngoài (injectable runner/embedder/client).
- Embedding model env `EMBED_MODEL` default `text-embedding-3-small` (1536d); Qdrant path env `QDRANT_PATH` default `qdrant_data` (thư mục, gitignore).
- Công thức điểm: có user_vec → `0.5·sim + 0.25·eng + 0.25·rec`; không user_vec → `0.5·eng + 0.5·rec`. `eng = log1p(hearts+comment_count)/log1p(max_engagement_trong_tập)` (max=0 → eng=0). `rec = exp(−age_hours/72)`. MMR λ=0.7.
- Bài user đã bookmark bị loại khỏi gợi ý. k mặc định 6.
- Profile cache: `bio_hash = sha256(f"{bio}|{','.join(sorted(bookmark_ids))}")`; lazy re-infer trong endpoint recommendations.
- Qdrant embedded chỉ cho MỘT process mở path — code phải bắt lỗi mở client và trả 503/skip có thông điệp rõ (spec §6). API dùng singleton module-level, không mở per-request.
- Trace inference: `eval/traces/recsys/<user_id>.json`.
- Commit trên dev/An, message tiếng Anh, kết thúc bằng:

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

- Package layout: `recsys/__init__.py` re-export public API: `from recsys import VectorStore, embed_texts, news_text, hybrid_scores, mmr_select, recommend, ensure_profile, InterestProfile`.

---

### Task 1: Scaffold recsys + config + deps

**Files:**
- Modify: `codebase/backend/requirements.txt` (thêm `qdrant-client>=1.9` và `openai>=1.40`)
- Modify: `codebase/backend/ingest/config.py`
- Modify: `codebase/backend/tests/test_config.py`
- Create: `codebase/backend/recsys/__init__.py` (tạm rỗng, điền dần)
- Modify: `codebase/backend/.env.example`
- Modify: root `.gitignore` (thêm `qdrant_data/`)

**Interfaces:**
- Produces: `Config` thêm fields `embed_model: str = "text-embedding-3-small"`, `qdrant_path: str = "qdrant_data"`; `from_env` đọc `EMBED_MODEL`, `QDRANT_PATH`.

- [ ] **Step 1: Failing test** — thêm vào `tests/test_config.py`:

```python
def test_recsys_config_defaults(monkeypatch):
    monkeypatch.delenv("EMBED_MODEL", raising=False)
    monkeypatch.delenv("QDRANT_PATH", raising=False)
    cfg = Config.from_env()
    assert cfg.embed_model == "text-embedding-3-small"
    assert cfg.qdrant_path == "qdrant_data"


def test_recsys_config_reads_env(monkeypatch):
    monkeypatch.setenv("EMBED_MODEL", "text-embedding-3-large")
    monkeypatch.setenv("QDRANT_PATH", "x_data")
    cfg = Config.from_env()
    assert cfg.embed_model == "text-embedding-3-large"
    assert cfg.qdrant_path == "x_data"
```

- [ ] **Step 2: Chạy → FAIL.**
- [ ] **Step 3: Implement** — thêm 2 field vào dataclass `Config` (sau `guild_id`):

```python
    embed_model: str = "text-embedding-3-small"
    qdrant_path: str = "qdrant_data"
```

và trong `from_env(...)`:

```python
            embed_model=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
            qdrant_path=os.getenv("QDRANT_PATH", "qdrant_data"),
```

Thêm vào `requirements.txt` hai dòng `qdrant-client>=1.9` và `openai>=1.40`; chạy `.venv/Scripts/python.exe -m pip install -r requirements.txt`. Tạo `recsys/__init__.py` rỗng. `.env.example` thêm dưới mục Model:

```
EMBED_MODEL=text-embedding-3-small
QDRANT_PATH=qdrant_data
```

Root `.gitignore`: thêm dòng `qdrant_data/`.

- [ ] **Step 4: `pytest tests/test_config.py -v` → PASS** (4 test).
- [ ] **Step 5: Commit** — `feat(recsys): scaffold package, config and deps`.

---

### Task 2: Store mở rộng (users, bookmarks, embedded_at)

**Files:**
- Modify: `codebase/backend/ingest/store.py`
- Create: `codebase/backend/tests/test_store_recsys.py`

**Interfaces:**
- Consumes: `Store` hiện có.
- Produces (methods mới trên `Store`):
  - Migration: cột `posts.embedded_at TEXT` (PRAGMA table_info check + ALTER TABLE nếu thiếu — DB cũ vẫn mở được).
  - `upsert_user(user_id, name, bio="", bio_source="manual") -> None` (INSERT OR IGNORE; không ghi đè bio đã có).
  - `list_users() -> list[dict]`, `get_user(user_id) -> dict | None` (dict có keys user_id,name,bio,bio_source,bio_hash,interest_summary,interest_tags — interest_tags parse JSON list).
  - `set_bio(user_id, bio, source="manual") -> None`.
  - `toggle_bookmark(user_id, message_id) -> bool` (True = giờ ĐANG bookmark), `list_bookmarks(user_id) -> list[str]` (mới nhất trước), `bookmarked_news(user_id, limit=10) -> list[dict]` (join posts: message_id,title,summary,tags).
  - `save_profile(user_id, bio_hash, interest_summary, interest_tags: list[str]) -> None`.
  - `pending_embedding(limit=100, force=False) -> list[dict]` (keys message_id,title,summary,tags,created_at,hearts,comment_count; điều kiện `enriched_at IS NOT NULL AND embedded_at IS NULL`, force bỏ điều kiện embedded).
  - `set_embedded(message_id) -> None`; `embedded_news_meta() -> list[dict]` (message_id,hearts,comment_count của bài đã embedded).

- [ ] **Step 1: Failing tests** — `tests/test_store_recsys.py`:

```python
from ingest.models import NewsEnrichment
from ingest.store import Store
from tests.test_store import make_post


def enriched_store(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.upsert_post(make_post(mid="1"))
    s.save_enrichment("1", NewsEnrichment(summary_vi="Tóm tắt.", tags=["ai-model"],
                                          image_query="q"), "placeholder", "v1", "t")
    return s


def test_users_crud(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.upsert_user("u1", "An", bio="Thích CV")
    s.upsert_user("u1", "An", bio="GHI ĐÈ?")          # IGNORE — không ghi đè
    assert s.get_user("u1")["bio"] == "Thích CV"
    s.set_bio("u1", "Mê xe tự hành")
    assert s.get_user("u1")["bio"] == "Mê xe tự hành"
    assert s.get_user("u1")["interest_tags"] == []
    assert len(s.list_users()) == 1 and s.get_user("zz") is None


def test_bookmarks_toggle_and_join(tmp_path):
    s = enriched_store(tmp_path)
    s.upsert_user("u1", "An")
    assert s.toggle_bookmark("u1", "1") is True
    assert s.list_bookmarks("u1") == ["1"]
    rows = s.bookmarked_news("u1")
    assert rows[0]["title"].startswith("Bài") and rows[0]["tags"] == ["ai-model"]
    assert s.toggle_bookmark("u1", "1") is False
    assert s.list_bookmarks("u1") == []


def test_save_profile_roundtrip(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.upsert_user("u1", "An")
    s.save_profile("u1", "h123", "Mê CV", ["ai-model", "dataset"])
    u = s.get_user("u1")
    assert u["bio_hash"] == "h123" and u["interest_tags"] == ["ai-model", "dataset"]


def test_pending_embedding_and_flag(tmp_path):
    s = enriched_store(tmp_path)
    s.upsert_post(make_post(mid="2"))                  # chưa enrich → không pending embed
    rows = s.pending_embedding()
    assert [r["message_id"] for r in rows] == ["1"]
    s.set_embedded("1")
    assert s.pending_embedding() == []
    assert len(s.pending_embedding(force=True)) == 1
    assert s.embedded_news_meta()[0]["message_id"] == "1"


def test_embedded_at_migration_on_old_db(tmp_path):
    # DB tạo bởi schema cũ (không có embedded_at) vẫn mở được
    import sqlite3
    p = str(tmp_path / "old.db")
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE posts(message_id TEXT PRIMARY KEY, channel TEXT, title TEXT,"
                 " content TEXT, author TEXT, author_role TEXT, jump_url TEXT, created_at TEXT,"
                 " hearts INTEGER DEFAULT 0, comment_count INTEGER DEFAULT 0, summary TEXT,"
                 " tags TEXT, image_url TEXT, image_source TEXT, enriched_at TEXT,"
                 " enrich_failed INTEGER DEFAULT 0, prompt_version TEXT, trace_id TEXT)")
    conn.commit(); conn.close()
    s = Store(p)
    assert s.pending_embedding() == []                 # không nổ ALTER/SELECT
```

- [ ] **Step 2: Chạy → FAIL.**
- [ ] **Step 3: Implement trong `ingest/store.py`** — thêm vào `SCHEMA`:

```sql
CREATE TABLE IF NOT EXISTS users(
  user_id TEXT PRIMARY KEY, name TEXT, bio TEXT DEFAULT '', bio_source TEXT DEFAULT 'manual',
  bio_hash TEXT, interest_summary TEXT, interest_tags TEXT
);
CREATE TABLE IF NOT EXISTS bookmarks(
  user_id TEXT, message_id TEXT, created_at TEXT,
  PRIMARY KEY(user_id, message_id)
);
```

Trong `__init__` sau `executescript(SCHEMA)`:

```python
        cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(posts)")]
        if "embedded_at" not in cols:
            self.conn.execute("ALTER TABLE posts ADD COLUMN embedded_at TEXT")
        self.conn.commit()
```

Methods (đặt cuối class):

```python
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
```

- [ ] **Step 4: `pytest tests/test_store_recsys.py -v` → PASS; full suite PASS.**
- [ ] **Step 5: Commit** — `feat(recsys): store users/bookmarks tables and embedding flags`.

---

### Task 3: Embedder + VectorStore (Qdrant embedded)

**Files:**
- Create: `codebase/backend/recsys/embedder.py`
- Create: `codebase/backend/recsys/vectorstore.py`
- Modify: `codebase/backend/recsys/__init__.py`
- Test: `codebase/backend/tests/test_vectorstore.py`

**Interfaces:**
- Produces:
  - `embed_texts(texts: list[str], cfg, client=None) -> list[list[float]]` — client injectable (mặc định `OpenAI(api_key=cfg.openai_api_key)`), 1 call batch `client.embeddings.create(model=cfg.embed_model, input=texts)`.
  - `news_text(row: dict) -> str` = `f"{row['title']}\n{row['summary']}\nTags: {', '.join(row['tags'])}"` (summary None → "").
  - `class VectorStore(path: str, dim: int = 1536)`: `_ensure(name)` dùng `collection_exists`/`create_collection(VectorParams(size=dim, distance=Distance.COSINE))`; `upsert_news(message_id: str, vector, payload: dict)` (Qdrant id = `int(message_id)`, payload PHẢI chứa `message_id` gốc + tags/created_at/hearts/comment_count); `update_news_payload(message_id, hearts, comment_count)` (`set_payload`); `all_news() -> list[tuple[str, list[float], dict]]` (scroll `with_vectors=True`, limit 1000, trả (payload["message_id"], vector, payload)); `upsert_user(user_id: str, vector)` (id = `int.from_bytes(hashlib.sha256(user_id.encode()).digest()[:8], "big")`); `get_user(user_id) -> list[float] | None` (`retrieve` with_vectors).
- Lỗi mở path (process khác giữ lock) → để exception nổ lên tự nhiên; caller xử lý (Task 6/7).

- [ ] **Step 1: Failing tests** — `tests/test_vectorstore.py` (Qdrant embedded trên tmp_path — KHÔNG gọi API ngoài; embed_texts test bằng fake client):

```python
from ingest.config import Config
from recsys.embedder import embed_texts, news_text
from recsys.vectorstore import VectorStore


class FakeEmbeddings:
    def create(self, model, input):
        class D:  # noqa: N801
            def __init__(self, v): self.embedding = v
        class R:
            data = [D([float(len(t))] * 4) for t in input]
        return R()


class FakeOpenAI:
    embeddings = FakeEmbeddings()


def test_embed_texts_uses_injected_client():
    vecs = embed_texts(["ab", "abcd"], Config(), client=FakeOpenAI())
    assert vecs == [[2.0] * 4, [4.0] * 4]


def test_news_text_format():
    t = news_text({"title": "T", "summary": "S", "tags": ["uiux", "other"]})
    assert t == "T\nS\nTags: uiux, other"
    assert news_text({"title": "T", "summary": None, "tags": []}) == "T\n\nTags: "


def test_vectorstore_news_roundtrip(tmp_path):
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    vs.upsert_news("1001", [1, 0, 0, 0],
                   {"message_id": "1001", "tags": ["ai-model"], "created_at": "2026-07-30T09:00:00",
                    "hearts": 5, "comment_count": 1})
    vs.update_news_payload("1001", hearts=9, comment_count=2)
    items = vs.all_news()
    assert len(items) == 1
    mid, vec, payload = items[0]
    assert mid == "1001" and payload["hearts"] == 9 and list(vec)[:1] == [1.0]


def test_vectorstore_user_roundtrip(tmp_path):
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    assert vs.get_user("u1") is None
    vs.upsert_user("u1", [0, 1, 0, 0])
    assert list(vs.get_user("u1")) == [0.0, 1.0, 0.0, 0.0]
```

- [ ] **Step 2: Chạy → FAIL.**
- [ ] **Step 3: Implement.** `recsys/embedder.py`:

```python
def embed_texts(texts, cfg, client=None):
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=cfg.openai_api_key)
    resp = client.embeddings.create(model=cfg.embed_model, input=texts)
    return [d.embedding for d in resp.data]


def news_text(row: dict) -> str:
    return f"{row['title']}\n{row.get('summary') or ''}\nTags: {', '.join(row.get('tags') or [])}"
```

`recsys/vectorstore.py`:

```python
import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

NEWS = "news"
USERS = "user_profiles"


def _user_point_id(user_id: str) -> int:
    return int.from_bytes(hashlib.sha256(user_id.encode()).digest()[:8], "big")


class VectorStore:
    def __init__(self, path: str, dim: int = 1536):
        self.client = QdrantClient(path=path)
        self.dim = dim
        for name in (NEWS, USERS):
            if not self.client.collection_exists(name):
                self.client.create_collection(
                    name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))

    def upsert_news(self, message_id: str, vector, payload: dict) -> None:
        payload = {**payload, "message_id": message_id}
        self.client.upsert(NEWS, points=[
            PointStruct(id=int(message_id), vector=list(vector), payload=payload)])

    def update_news_payload(self, message_id: str, hearts: int, comment_count: int) -> None:
        self.client.set_payload(NEWS, payload={"hearts": hearts, "comment_count": comment_count},
                                points=[int(message_id)])

    def all_news(self):
        points, _ = self.client.scroll(NEWS, limit=1000, with_vectors=True, with_payload=True)
        return [(p.payload["message_id"], p.vector, p.payload) for p in points]

    def upsert_user(self, user_id: str, vector) -> None:
        self.client.upsert(USERS, points=[
            PointStruct(id=_user_point_id(user_id), vector=list(vector),
                        payload={"user_id": user_id})])

    def get_user(self, user_id: str):
        pts = self.client.retrieve(USERS, ids=[_user_point_id(user_id)], with_vectors=True)
        return pts[0].vector if pts else None
```

`recsys/__init__.py`:

```python
from .embedder import embed_texts, news_text
from .vectorstore import VectorStore

__all__ = ["embed_texts", "news_text", "VectorStore"]
```

- [ ] **Step 4: `pytest tests/test_vectorstore.py -v` → PASS; full suite PASS.**
- [ ] **Step 5: Commit** — `feat(recsys): openai embedder and qdrant embedded vector store`.

---

### Task 4: Scoring + MMR + recommend

**Files:**
- Create: `codebase/backend/recsys/recommend.py`
- Modify: `codebase/backend/recsys/__init__.py` (re-export)
- Test: `codebase/backend/tests/test_recommend.py`

**Interfaces:**
- Consumes: `Store` (get_news, list_bookmarks), `VectorStore.all_news/get_user`.
- Produces:
  - `cosine(a, b) -> float`.
  - `hybrid_scores(user_vec, items, now) -> list[dict]` — items = list[(mid, vec, payload)]; trả `[{message_id, vector, score, parts:{sim,eng,rec}}]` theo Global Constraints (payload thiếu hearts → 0; created_at parse `datetime.fromisoformat`, bỏ tzinfo nếu có; age âm → 0).
  - `mmr_select(scored: list[dict], k: int, lam: float = 0.7) -> list[dict]` — greedy MMR trên `score` và cosine giữa `vector`.
  - `recommend(store, vs, user_id: str, k: int = 6) -> list[dict]` — user_vec = vs.get_user; loại message_id ∈ store.list_bookmarks(user_id); mmr_select; join `store.get_news(mid)` (chỉ giữ bài tồn tại) → mỗi phần tử = news dict + `score` + `parts`.

- [ ] **Step 1: Failing tests** — `tests/test_recommend.py`:

```python
from datetime import datetime

from recsys.recommend import cosine, hybrid_scores, mmr_select

NOW = datetime(2026, 7, 31, 12, 0, 0)


def item(mid, vec, hearts=0, comments=0, hours_ago=0):
    from datetime import timedelta
    return (mid, vec, {"message_id": mid, "hearts": hearts, "comment_count": comments,
                       "created_at": (NOW - timedelta(hours=hours_ago)).isoformat()})


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0


def test_scores_without_user_vec_is_eng_plus_rec():
    scored = hybrid_scores(None, [item("1", [1, 0], hearts=10, hours_ago=0),
                                  item("2", [0, 1], hearts=0, hours_ago=200)], NOW)
    by = {s["message_id"]: s for s in scored}
    assert by["1"]["parts"]["sim"] == 0.0
    assert by["1"]["score"] > by["2"]["score"]          # nhiều tim + mới hơn thắng
    assert by["1"]["parts"]["eng"] == 1.0               # log-chuẩn hoá theo max


def test_scores_with_user_vec_prefers_similar():
    scored = hybrid_scores([1, 0], [item("sim", [1, 0]), item("far", [0, 1])], NOW)
    by = {s["message_id"]: s for s in scored}
    assert by["sim"]["parts"]["sim"] == 1.0 and by["far"]["parts"]["sim"] == 0.0
    assert by["sim"]["score"] > by["far"]["score"]


def test_recency_decay():
    scored = hybrid_scores(None, [item("new", [1, 0], hours_ago=0),
                                  item("old", [1, 0], hours_ago=72)], NOW)
    by = {s["message_id"]: s for s in scored}
    assert by["new"]["parts"]["rec"] == 1.0
    assert 0.35 < by["old"]["parts"]["rec"] < 0.38      # e^-1 ≈ 0.3679


def test_mmr_diversifies():
    # 2 bài gần trùng vector, 1 bài khác hẳn: top-2 phải chứa bài khác hẳn
    scored = hybrid_scores([1, 0, 0], [item("a1", [1, 0, 0], hearts=10),
                                       item("a2", [0.999, 0.04, 0], hearts=9),
                                       item("b", [0, 1, 0], hearts=8)], NOW)
    picked = [s["message_id"] for s in mmr_select(scored, k=2, lam=0.7)]
    assert picked[0] == "a1" and picked[1] == "b"
```

- [ ] **Step 2: Chạy → FAIL.**
- [ ] **Step 3: Implement `recsys/recommend.py`:**

```python
import math
from datetime import datetime

W_SIM, W_ENG, W_REC = 0.5, 0.25, 0.25
TAU_HOURS = 72.0


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _age_hours(created_at: str, now: datetime) -> float:
    dt = datetime.fromisoformat(created_at)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return max(0.0, (now - dt).total_seconds() / 3600)


def hybrid_scores(user_vec, items, now: datetime) -> list[dict]:
    engs = [math.log1p((p.get("hearts") or 0) + (p.get("comment_count") or 0))
            for _, _, p in items]
    max_eng = max(engs) if engs else 0.0
    out = []
    for (mid, vec, payload), raw_eng in zip(items, engs):
        sim = cosine(user_vec, vec) if user_vec is not None else 0.0
        eng = raw_eng / max_eng if max_eng else 0.0
        rec = math.exp(-_age_hours(payload["created_at"], now) / TAU_HOURS)
        if user_vec is not None:
            score = W_SIM * sim + W_ENG * eng + W_REC * rec
        else:
            score = 0.5 * eng + 0.5 * rec
        out.append({"message_id": mid, "vector": vec, "score": score,
                    "parts": {"sim": sim, "eng": eng, "rec": rec}})
    return out


def mmr_select(scored: list[dict], k: int, lam: float = 0.7) -> list[dict]:
    remaining = list(scored)
    picked: list[dict] = []
    while remaining and len(picked) < k:
        def mmr(c):
            penalty = max((cosine(c["vector"], p["vector"]) for p in picked), default=0.0)
            return lam * c["score"] - (1 - lam) * penalty
        best = max(remaining, key=mmr)
        picked.append(best)
        remaining.remove(best)
    return picked


def recommend(store, vs, user_id: str, k: int = 6) -> list[dict]:
    user_vec = vs.get_user(user_id)
    bookmarked = set(store.list_bookmarks(user_id))
    items = [(m, v, p) for m, v, p in vs.all_news() if m not in bookmarked]
    scored = hybrid_scores(user_vec, items, datetime.utcnow())
    results = []
    for s in mmr_select(scored, k=k):
        news = store.get_news(s["message_id"])
        if news is None:
            continue
        news.pop("comments", None)
        results.append({**news, "score": round(s["score"], 4),
                        "parts": {kk: round(vv, 4) for kk, vv in s["parts"].items()}})
    return results
```

`recsys/__init__.py` thêm: `from .recommend import cosine, hybrid_scores, mmr_select, recommend`.

- [ ] **Step 4: `pytest tests/test_recommend.py -v` → PASS; full suite PASS.**
- [ ] **Step 5: Commit** — `feat(recsys): hybrid scoring with MMR diversity selection`.

---

### Task 5: Interest prompt + profile inferencer (lazy, hash cache)

**Files:**
- Create: `codebase/backend/recsys/prompts/__init__.py` + `codebase/backend/recsys/prompts/interest_v1.py`
- Create: `codebase/backend/recsys/profile.py`
- Modify: `codebase/backend/recsys/__init__.py` (re-export `ensure_profile`, `InterestProfile`, `compute_hash`)
- Test: `codebase/backend/tests/test_profile.py`

**Interfaces:**
- Consumes: `Store` (get_user, list_bookmarks, bookmarked_news, save_profile), `VectorStore` (get_user, upsert_user), `embed_texts`, `TagId`.
- Produces:
  - `InterestProfile(BaseModel)`: `interest_summary_vi: str`, `interest_tags: list[TagId]` min 1 max 4.
  - `compute_hash(bio: str, bookmark_ids: list[str]) -> str` = sha256 của `f"{bio}|{','.join(sorted(bookmark_ids))}"`.
  - `ensure_profile(store, vs, cfg, user_id, runner=None, embedder=None) -> bool` — True nếu vừa re-infer. Flow: user không tồn tại → `KeyError`. hash trùng `bio_hash` VÀ (`vs.get_user` có vector HOẶC user trắng thông tin) → return False. User trắng (bio rỗng + 0 bookmark) → `save_profile(user_id, hash, "", [])`, KHÔNG upsert vector, return False. Ngược lại: gọi agent (runner injectable nhận input_text trả InterestProfile; mặc định Agents SDK `Runner.run_sync` với agent `profile_inferencer` — model `cfg.enrich_model`, instructions `INTEREST_V1`, output_type InterestProfile, không tool) → vector = `(embedder or embed_texts)([profile.interest_summary_vi], cfg)[0]` → `vs.upsert_user` → `store.save_profile` → ghi trace `eval/traces/recsys/<user_id>.json` (ensure_ascii=False; keys: user_id, bio_hash, input, output, model) → True.
  - Input text: `f"Bio: {bio or '(trống)'}\nCác bài đã bookmark:\n" + "\n".join(f"- {r['title']} [tags: {', '.join(r['tags'])}] {(r['summary'] or '')[:150]}" for r in bookmarked_rows)` (rows từ `bookmarked_news(user_id, 10)`; rỗng → dòng `- (chưa có)`).

- [ ] **Step 1: Viết `recsys/prompts/interest_v1.py`:**

```python
INTEREST_V1 = """Bạn là bộ phân tích sở thích học viên của khoá AI Thực Chiến.
Đầu vào: bio tự giới thiệu của học viên + danh sách bài viết họ đã bookmark
(tiêu đề, tags, trích tóm tắt).

Nhiệm vụ: suy luận HỌ QUAN TÂM GÌ và trả về đúng schema:
- interest_summary_vi: MỘT đoạn 2-4 câu tiếng Việt mô tả chủ đề kỹ thuật họ
  quan tâm, viết như mô tả nội dung muốn đọc (đoạn này sẽ được embedding để
  tìm bài tương tự — hãy giàu từ khoá chủ đề, không viết về tính cách).
- interest_tags: 1-4 tag từ đúng bộ: ai-model, ai-skill, ai-tools, api-mcp,
  system-design, uiux, dataset, soft-skills, survey, other.

Quy tắc: bookmark là tín hiệu MẠNH hơn bio khi hai bên lệch nhau; không suy
diễn chủ đề không có căn cứ; bio trống thì dựa hoàn toàn vào bookmark.

VÍ DỤ — bio "Mê computer vision và xe tự hành", bookmark có bài BEV + dataset
CV → interest_summary_vi: "Quan tâm thị giác máy tính cho xe tự hành: kiến
trúc perception như BEV, lựa chọn dataset (nuScenes, KITTI), pipeline
detection và đánh giá mô hình." · interest_tags: ["ai-model", "dataset"]
"""
```

`recsys/prompts/__init__.py`:

```python
from .interest_v1 import INTEREST_V1

INTEREST_VERSION = "v1"
INTEREST_PROMPTS = {"v1": INTEREST_V1}
```

- [ ] **Step 2: Failing tests** — `tests/test_profile.py` (không gọi API — runner + embedder giả):

```python
from ingest.config import Config
from ingest.models import NewsEnrichment
from ingest.store import Store
from recsys.profile import InterestProfile, compute_hash, ensure_profile
from recsys.vectorstore import VectorStore
from tests.test_store import make_post

FAKE = InterestProfile(interest_summary_vi="Mê CV.", interest_tags=["ai-model"])


def setup(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    s.upsert_user("u1", "An", bio="Thích xe tự hành")
    return s, vs


def test_hash_changes_with_bio_and_bookmarks():
    h1 = compute_hash("bio", [])
    assert h1 != compute_hash("bio2", [])
    assert h1 != compute_hash("bio", ["9"])
    assert compute_hash("bio", ["2", "1"]) == compute_hash("bio", ["1", "2"])


def test_infer_once_then_cached(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s, vs = setup(tmp_path)
    calls = []
    runner = lambda text: (calls.append(text) or FAKE)
    embedder = lambda texts, cfg: [[0.0, 1.0, 0.0, 0.0]]
    assert ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder) is True
    assert ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder) is False
    assert len(calls) == 1                       # cache hash
    assert list(vs.get_user("u1")) == [0.0, 1.0, 0.0, 0.0]
    assert s.get_user("u1")["interest_tags"] == ["ai-model"]
    assert "Thích xe tự hành" in calls[0]


def test_bookmark_change_triggers_reinfer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s, vs = setup(tmp_path)
    s.upsert_post(make_post(mid="1"))
    s.save_enrichment("1", NewsEnrichment(summary_vi="Tóm tắt.", tags=["dataset"],
                                          image_query="q"), "placeholder", "v1", "t")
    runner = lambda text: FAKE
    embedder = lambda texts, cfg: [[1.0, 0.0, 0.0, 0.0]]
    ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder)
    s.toggle_bookmark("u1", "1")
    assert ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder) is True


def test_blank_user_no_infer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s, vs = setup(tmp_path)
    s.upsert_user("u2", "Trắng")                  # bio rỗng, không bookmark
    boom = lambda text: (_ for _ in ()).throw(AssertionError("không được gọi"))
    assert ensure_profile(s, vs, Config(), "u2", runner=boom, embedder=None) is False
    assert vs.get_user("u2") is None


def test_unknown_user_raises(tmp_path):
    s, vs = setup(tmp_path)
    import pytest
    with pytest.raises(KeyError):
        ensure_profile(s, vs, Config(), "zzz", runner=lambda t: FAKE,
                       embedder=lambda t, c: [[0, 0, 0, 0]])
```

- [ ] **Step 3: Chạy → FAIL. Step 4: Implement `recsys/profile.py`:**

```python
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from ingest.models import TagId
from .embedder import embed_texts
from .prompts import INTEREST_V1, INTEREST_VERSION

TRACE_DIR = Path("eval/traces/recsys")


class InterestProfile(BaseModel):
    interest_summary_vi: str
    interest_tags: list[TagId] = Field(min_length=1, max_length=4)


def compute_hash(bio: str, bookmark_ids: list[str]) -> str:
    raw = f"{bio}|{','.join(sorted(bookmark_ids))}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_input(bio: str, rows: list[dict]) -> str:
    lines = [f"- {r['title']} [tags: {', '.join(r['tags'])}] {(r['summary'] or '')[:150]}"
             for r in rows] or ["- (chưa có)"]
    return f"Bio: {bio or '(trống)'}\nCác bài đã bookmark:\n" + "\n".join(lines)


def _run_agent(input_text: str, cfg) -> InterestProfile:
    from agents import Agent, Runner
    agent = Agent(name="profile_inferencer", instructions=INTEREST_V1,
                  model=cfg.enrich_model, output_type=InterestProfile)
    return Runner.run_sync(agent, input_text).final_output


def ensure_profile(store, vs, cfg, user_id: str, runner=None, embedder=None) -> bool:
    user = store.get_user(user_id)
    if user is None:
        raise KeyError(user_id)
    bio = user["bio"] or ""
    ids = store.list_bookmarks(user_id)
    h = compute_hash(bio, ids)
    blank = not bio.strip() and not ids
    if h == user["bio_hash"] and (blank or vs.get_user(user_id) is not None):
        return False
    if blank:
        store.save_profile(user_id, h, "", [])
        return False
    input_text = _build_input(bio, store.bookmarked_news(user_id, 10))
    profile = (runner or (lambda t: _run_agent(t, cfg)))(input_text)
    vector = (embedder or embed_texts)([profile.interest_summary_vi], cfg)[0]
    vs.upsert_user(user_id, vector)
    store.save_profile(user_id, h, profile.interest_summary_vi, list(profile.interest_tags))
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    (TRACE_DIR / f"{user_id}.json").write_text(json.dumps({
        "user_id": user_id, "bio_hash": h, "prompt_version": INTEREST_VERSION,
        "model": cfg.enrich_model, "input": input_text[:500],
        "output": profile.model_dump(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
```

`recsys/__init__.py` thêm: `from .profile import InterestProfile, compute_hash, ensure_profile`.

- [ ] **Step 5: `pytest tests/test_profile.py -v` → PASS; full suite PASS.**
- [ ] **Step 6: Commit** — `feat(recsys): interest profile inferencer with lazy hash cache`.

---

### Task 6: Hook embed vào pipeline

**Files:**
- Modify: `codebase/backend/ingest/__main__.py`
- Test: thêm vào `codebase/backend/tests/test_pipeline.py`

**Interfaces:**
- `run_once(store, source, cfg, limit=20, force=False, runner=None, vectors=None, embed_fn=None) -> dict` — thêm 2 param mặc định None; `vectors is None` → bỏ qua bước embed (test cũ giữ nguyên pass, stats["embedded"]=0). `embed_fn(texts, cfg) -> vectors` (mặc định `embed_texts`).
- Sau vòng enrich: `rows = store.pending_embedding(force=force)`; nếu rows và vectors: texts = [news_text(r)], vecs = embed_fn(texts, cfg); từng row → `vectors.upsert_news(mid, vec, payload={tags, created_at, hearts, comment_count})` + `store.set_embedded(mid)`; lỗi embed → print, KHÔNG set_embedded (lượt sau thử lại), không chặn run. Sau đó payload refresh: `for m in store.embedded_news_meta(): vectors.update_news_payload(...)`. Stats: `{"fetched", "enriched", "failed", "embedded"}`.
- CLI `main()`: tạo `VectorStore(cfg.qdrant_path)` trong try/except — lỗi (path bị process khác giữ) → print cảnh báo `[recsys] qdrant busy/unavailable: ... (bỏ qua embed)` và `vectors=None`.

- [ ] **Step 1: Failing tests** — thêm vào `tests/test_pipeline.py`:

```python
class FakeVectors:
    def __init__(self):
        self.news, self.payloads = {}, {}
    def upsert_news(self, mid, vec, payload):
        self.news[mid] = (list(vec), payload)
    def update_news_payload(self, mid, hearts, comment_count):
        self.payloads[mid] = (hearts, comment_count)


def fake_embed(texts, cfg):
    return [[float(len(t)), 0.0] for t in texts]


def test_run_once_embeds_after_enrich(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(str(tmp_path / "t.db"))
    fv = FakeVectors()
    stats = run_once(store, SeedSource(SEED), Config(), runner=fake_runner,
                     vectors=fv, embed_fn=fake_embed)
    assert stats["embedded"] == 10 and len(fv.news) == 10
    stats2 = run_once(store, SeedSource(SEED), Config(), runner=fake_runner,
                      vectors=fv, embed_fn=fake_embed)
    assert stats2["embedded"] == 0                     # embed-once
    assert len(fv.payloads) == 10                      # payload refresh vẫn chạy


def test_run_once_without_vectors_keeps_old_behavior(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(str(tmp_path / "t.db"))
    stats = run_once(store, SeedSource(SEED), Config(), runner=fake_runner)
    assert stats["embedded"] == 0
```

- [ ] **Step 2: FAIL → Step 3: Implement** trong `ingest/__main__.py` (import `from recsys import VectorStore, embed_texts, news_text` — import `VectorStore` lazily trong `main()` để tránh phụ thuộc khi chỉ chạy test cũ; `embed_texts`, `news_text` import lazily trong `run_once` khi cần):

```python
def run_once(store, source, cfg, limit=20, force=False, runner=None,
             vectors=None, embed_fn=None) -> dict:
    ...  # phần fetch + enrich giữ nguyên
    embedded = 0
    if vectors is not None:
        from recsys import embed_texts as _default_embed, news_text
        embed = embed_fn or _default_embed
        rows = store.pending_embedding(force=force)
        if rows:
            try:
                vecs = embed([news_text(r) for r in rows], cfg)
                for r, vec in zip(rows, vecs):
                    vectors.upsert_news(r["message_id"], vec, {
                        "tags": r["tags"], "created_at": r["created_at"],
                        "hearts": r["hearts"], "comment_count": r["comment_count"]})
                    store.set_embedded(r["message_id"])
                    embedded += 1
            except Exception as exc:
                print(f"[embed-fail] {exc}")
        for m in store.embedded_news_meta():
            vectors.update_news_payload(m["message_id"], m["hearts"], m["comment_count"])
    return {"fetched": len(posts), "enriched": enriched, "failed": failed,
            "embedded": embedded}
```

Trong `main()` sau khi tạo store:

```python
    try:
        from recsys import VectorStore
        vectors = VectorStore(cfg.qdrant_path)
    except Exception as exc:
        print(f"[recsys] qdrant busy/unavailable: {exc} (bỏ qua embed)")
        vectors = None
```

và truyền `vectors=vectors` vào `run_once`.

- [ ] **Step 4: `pytest tests/test_pipeline.py -v` → PASS (6 test); full suite PASS.**
- [ ] **Step 5: Commit** — `feat(recsys): embed news into qdrant during ingest run`.

---

### Task 7: API users / bookmarks / recommendations + seeds

**Files:**
- Modify: `codebase/backend/api/main.py`
- Create: `codebase/backend/recsys/seeds/users.json`
- Test: `codebase/backend/tests/test_api_recsys.py`

**Interfaces:**
- Produces endpoints (Global Constraints áp dụng; VectorStore singleton):

```python
# api/main.py additions
_VS = None
def get_vectors():
    global _VS
    if _VS is None:
        from recsys import VectorStore
        _VS = VectorStore(Config.from_env().qdrant_path)
    return _VS


def _seed_users(store: Store) -> None:
    if store.list_users():
        return
    import json as _json
    from pathlib import Path
    seed = Path(__file__).resolve().parent.parent / "recsys" / "seeds" / "users.json"
    for u in _json.loads(seed.read_text(encoding="utf-8")):
        store.upsert_user(u["user_id"], u["name"], bio=u.get("bio", ""))


@app.get("/api/users")
def users(store: Store = Depends(get_store)):
    _seed_users(store)
    return store.list_users()


class BioBody(BaseModel):
    bio: str


@app.put("/api/users/{user_id}/bio")
def put_bio(user_id: str, body: BioBody, store: Store = Depends(get_store)):
    if store.get_user(user_id) is None:
        raise HTTPException(404)
    store.set_bio(user_id, body.bio)
    return {"ok": True}


@app.get("/api/users/{user_id}/bookmarks")
def bookmarks(user_id: str, store: Store = Depends(get_store)):
    return store.list_bookmarks(user_id)


@app.put("/api/users/{user_id}/bookmarks/{message_id}")
def add_bookmark(user_id: str, message_id: str, store: Store = Depends(get_store)):
    if message_id not in store.list_bookmarks(user_id):
        store.toggle_bookmark(user_id, message_id)
    return {"bookmarked": True}


@app.delete("/api/users/{user_id}/bookmarks/{message_id}")
def del_bookmark(user_id: str, message_id: str, store: Store = Depends(get_store)):
    if message_id in store.list_bookmarks(user_id):
        store.toggle_bookmark(user_id, message_id)
    return {"bookmarked": False}


@app.get("/api/recommendations")
def recommendations(user_id: str, k: int = 6, store: Store = Depends(get_store)):
    from recsys import ensure_profile, recommend
    try:
        vs = get_vectors()
    except Exception as exc:
        raise HTTPException(503, detail=f"vector store unavailable: {exc}")
    _seed_users(store)
    if store.get_user(user_id) is None:
        raise HTTPException(404)
    try:
        ensure_profile(store, vs, Config.from_env(), user_id)
    except Exception as exc:                    # inference lỗi → dùng profile cũ/fallback
        print(f"[recsys] ensure_profile failed: {exc}")
    return recommend(store, vs, user_id, k=k)
```

(`from pydantic import BaseModel` thêm đầu file.)

- `recsys/seeds/users.json` — 3 user demo:

```json
[
  {"user_id": "an", "name": "An (demo)", "bio": "Mê computer vision và xe tự hành, đang tìm hiểu BEV, chọn dataset cho bài toán detection."},
  {"user_id": "vy", "name": "Vy (demo)", "bio": "Thích thiết kế sản phẩm và UI/UX, hay đọc về design system, shadcn, cách làm demo đẹp nhanh."},
  {"user_id": "long", "name": "Long (demo)", "bio": "Quan tâm backend và hạ tầng agent: tool calling, MCP, tối ưu chi phí gọi API, prompt caching."}
]
```

- [ ] **Step 1: Failing tests** — `tests/test_api_recsys.py` (monkeypatch `api.main.get_vectors` trả VectorStore tmp; monkeypatch `recsys.profile.embed_texts`?? — KHÔNG: recommendations gọi `ensure_profile` mặc định (runner thật) → tests seed profile TRỰC TIẾP thay vì qua ensure_profile: upsert_user vector thẳng vào vs + save_profile với đúng hash để ensure_profile thấy cache hit và KHÔNG gọi API):

```python
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app, get_store
from ingest.config import Config
from ingest.models import NewsEnrichment
from ingest.store import Store
from recsys.profile import compute_hash
from recsys.vectorstore import VectorStore
from tests.test_store import make_post


def make_env(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "t.db"))
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    monkeypatch.setattr(api_main, "get_vectors", lambda: vs)
    app.dependency_overrides[get_store] = lambda: store
    for i, tags in [("1", ["ai-model"]), ("2", ["uiux"]), ("3", ["api-mcp"])]:
        store.upsert_post(make_post(mid=i, hearts=int(i) * 5))
        store.save_enrichment(i, NewsEnrichment(summary_vi=f"Bài {i}.", tags=tags,
                                                image_query="q"), "placeholder", "v1", "t")
        vs.upsert_news(i, [1.0 if i == "1" else 0.0, 1.0 if i == "2" else 0.0,
                           1.0 if i == "3" else 0.0, 0.0],
                       {"message_id": i, "tags": tags,
                        "created_at": "2026-07-31T08:00:00", "hearts": int(i) * 5,
                        "comment_count": 0})
    return TestClient(app), store, vs


def test_users_seeded_and_bio_update(tmp_path, monkeypatch):
    client, store, _ = make_env(tmp_path, monkeypatch)
    users = client.get("/api/users").json()
    assert {u["user_id"] for u in users} == {"an", "vy", "long"}
    assert client.put("/api/users/an/bio", json={"bio": "bio mới"}).json() == {"ok": True}
    assert store.get_user("an")["bio"] == "bio mới"
    assert client.put("/api/users/zzz/bio", json={"bio": "x"}).status_code == 404


def test_bookmark_put_delete_idempotent(tmp_path, monkeypatch):
    client, store, _ = make_env(tmp_path, monkeypatch)
    client.get("/api/users")
    client.put("/api/users/an/bookmarks/1")
    client.put("/api/users/an/bookmarks/1")            # idempotent
    assert client.get("/api/users/an/bookmarks").json() == ["1"]
    client.delete("/api/users/an/bookmarks/1")
    assert client.get("/api/users/an/bookmarks").json() == []


def test_recommendations_personalized_and_excludes_bookmarked(tmp_path, monkeypatch):
    client, store, vs = make_env(tmp_path, monkeypatch)
    client.get("/api/users")
    # seed profile trực tiếp với hash khớp → ensure_profile cache-hit, không gọi API
    bio = store.get_user("an")["bio"]
    store.save_profile("an", compute_hash(bio, []), "Mê CV", ["ai-model"])
    vs.upsert_user("an", [1.0, 0.0, 0.0, 0.0])
    recs = client.get("/api/recommendations", params={"user_id": "an", "k": 2}).json()
    assert recs[0]["message_id"] == "1"                # giống vector user nhất
    assert "parts" in recs[0] and recs[0]["parts"]["sim"] == 1.0
    # bookmark bài 1 → hash đổi; cập nhật profile hash mới rồi gọi lại: bài 1 biến mất
    client.put("/api/users/an/bookmarks/1")
    store.save_profile("an", compute_hash(bio, ["1"]), "Mê CV", ["ai-model"])
    recs2 = client.get("/api/recommendations", params={"user_id": "an", "k": 3}).json()
    assert all(r["message_id"] != "1" for r in recs2)
    assert client.get("/api/recommendations", params={"user_id": "zzz"}).status_code == 404
```

- [ ] **Step 2: FAIL → Step 3: Implement như Interfaces + tạo seeds/users.json.**
- [ ] **Step 4: `pytest tests/test_api_recsys.py -v` → PASS; full suite PASS.**
- [ ] **Step 5: Commit** — `feat(api): users, bookmarks and personalized recommendations endpoints`.

---

### Task 8: UI — section "Dành cho bạn"

**Files:**
- Create: `codebase/ui/src/lib/api.js`
- Modify: `codebase/ui/src/pages/NewsPage.jsx`

**Interfaces:**
- `src/lib/api.js`:

```javascript
const API_BASE = "http://localhost:8000";

async function j(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export const api = {
  users: () => j(`${API_BASE}/api/users`),
  setBio: (id, bio) =>
    j(`${API_BASE}/api/users/${id}/bio`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bio }),
    }),
  bookmarks: (id) => j(`${API_BASE}/api/users/${id}/bookmarks`),
  setBookmark: (id, mid, on) =>
    j(`${API_BASE}/api/users/${id}/bookmarks/${mid}`, { method: on ? "PUT" : "DELETE" }),
  recommendations: (id, k = 6) =>
    j(`${API_BASE}/api/recommendations?user_id=${id}&k=${k}`),
};
```

- `NewsPage.jsx` — hành vi (giữ toàn bộ phần feed/tags mock như cũ):
  1. State mới: `users` (list|null), `selectedUser` (id|null), `recs` (list|null), `bioDraft`, `bioOpen`. Mount: `api.users()` → set users, chọn user đầu; lỗi → users=null (offline).
  2. Khi selectedUser đổi hoặc sau khi đổi bio/bookmark: gọi `api.recommendations(selectedUser, 6)` → recs (lỗi → recs=null).
  3. Section đầu trang đổi tiêu đề: online → `✨ Dành cho bạn` + `<select>` user (className: `h-8 rounded-lg border bg-background px-2 text-sm`) + Button outline sm "Sửa bio" mở Dialog (textarea `className="min-h-28 w-full rounded-lg border bg-background p-2 text-sm"`, nút Lưu → `api.setBio` → đóng + refetch recommendations). Offline (users null) → giữ nguyên header "Hot trend" + hot mock như hiện tại.
  4. Card gợi ý: render tối đa 3 phần tử đầu của recs bằng layout hot-card hiện có (TagBadge tag đầu, title, author chip, meta) + dòng lý do: `✨ {Math.round(parts.sim*100)}% match · 🔥 {hearts + comment_count} · 🕐 {Math.round(parts.rec*100)}% mới` (text-[10px] text-muted-foreground). Field names từ API: `message_id`, `title`, `tags` (list), `author`, `author_role`, `hearts`, `comment_count`, `image_url`, `parts`. Card click: item từ API không có `comments`/`content` đầy đủ → mở modal bằng cách tìm bài mock cùng title nếu có, còn không thì bỏ click (đơn giản: `onClick` chỉ gắn khi tìm thấy trong NEWS mock theo title).
  5. Bookmark: khi online + selectedUser → nút bookmark trên cả rec card lẫn feed card gọi `api.setBookmark(selectedUser, id, !bookmarked)` (feed card dùng mock id — chỉ đồng bộ local state như cũ nếu id không tồn tại backend; đơn giản: rec cards sync API, feed cards giữ local như cũ) rồi refetch recommendations. Sau toggle trên rec card → bài biến khỏi gợi ý (backend loại bài đã bookmark) — đúng hành vi mong muốn.
- Gate kiểm tra: `cd codebase/ui && npm run build` PASS (không cần backend chạy); không sửa file UI nào khác.

- [ ] **Step 1: Viết `src/lib/api.js` như trên.**
- [ ] **Step 2: Sửa `NewsPage.jsx`** theo hành vi 1-5 (dùng `useEffect`; import `api` từ `@/lib/api`; import `Dialog, DialogContent, DialogHeader, DialogTitle` + `Button` sẵn có).
- [ ] **Step 3: `npm run build` → PASS.** Nếu backend đang chạy sẵn thì mở dev server kiểm tra nhanh bằng mắt là bonus, không bắt buộc trong task này (controller sẽ verify browser sau).
- [ ] **Step 4: Commit** — `feat(ui): personalized "Danh cho ban" section with bio editor and bookmark sync`.

---

### Task 9: Smoke recsys + README

**Files:**
- Create: `codebase/backend/recsys/smoke.py`
- Modify: `codebase/backend/README.md`

**Interfaces:**
- `python -m recsys.smoke` (API thật): dùng DB `smoke-rec.db` MỚI trong cwd: (1) chạy `run_once` seed với enrich thật + embed thật (10 bài — enrich tốn ~10 call gpt-5-mini); (2) `_seed_users` từ seeds/users.json; (3) với mỗi user: `ensure_profile` thật + `recommend(k=3)` → in bảng: user, interest_tags suy luận được, top-3 (message_id · title cắt 40 · score · parts). (4) Cleanup: xoá `smoke-rec.db` và thư mục Qdrant tạm `smoke_qdrant/`. Thiếu OPENAI_API_KEY → in SKIP, exit 0. Kỳ vọng: 3 user ra top-3 khác nhau (an→bài CV/dataset, vy→bài UI, long→bài MCP/caching); nếu giống hệt nhau → in cảnh báo (không exit 1 — chất lượng đánh giá tay).

- [ ] **Step 1: Implement `recsys/smoke.py`:**

```python
"""Smoke recsys: python -m recsys.smoke (cần OPENAI_API_KEY; ~13 call nhỏ)."""
import shutil
from pathlib import Path

from ingest.__main__ import run_once
from ingest.config import Config
from ingest.sources import SeedSource
from ingest.store import Store
from api.main import _seed_users
from recsys import VectorStore, ensure_profile, recommend


def main():
    cfg = Config.from_env()
    if not cfg.openai_api_key:
        print("SKIP: thiếu OPENAI_API_KEY")
        return
    db, qpath = "smoke-rec.db", "smoke_qdrant"
    try:
        store = Store(db)
        vs = VectorStore(qpath)
        stats = run_once(store, SeedSource("ingest/seeds/posts.json"), cfg, vectors=vs)
        print(f"[ingest] {stats}")
        _seed_users(store)
        for u in store.list_users():
            ensure_profile(store, vs, cfg, u["user_id"])
            recs = recommend(store, vs, u["user_id"], k=3)
            tags = store.get_user(u["user_id"])["interest_tags"]
            print(f"\n== {u['name']} (tags suy luận: {tags})")
            for r in recs:
                print(f"  {r['message_id']} · {r['title'][:40]:40} · score={r['score']}"
                      f" · sim={r['parts']['sim']} eng={r['parts']['eng']} rec={r['parts']['rec']}")
    finally:
        try:
            vs.client.close()
        except Exception:
            pass
        Path(db).unlink(missing_ok=True)
        shutil.rmtree(qpath, ignore_errors=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: CHẠY THẬT** — `.venv/Scripts/python.exe -m recsys.smoke` từ `codebase/backend`; dán toàn bộ output vào report. Kỳ vọng 3 user ra top-3 khác nhau; nếu top-3 của 2 user trùng hệt → chạy lại 1 lần; vẫn trùng → báo trung thực (không sửa prompt trong task này).
- [ ] **Step 3: Cập nhật `codebase/backend/README.md`** — thêm mục "## Recommendations (recsys)": lệnh smoke, 3 endpoint mới + users/bookmarks, giải thích 1 dòng công thức điểm + MMR, ghi chú Qdrant embedded 1-process (chạy ingest khi API tắt hoặc chấp nhận skip-embed), `qdrant_data/` không commit.
- [ ] **Step 4: Full suite `pytest -q` → PASS.**
- [ ] **Step 5: Commit** — `feat(recsys): smoke runner and README for recommendations`.

---

## Self-review đã chạy

- **Spec coverage:** §1 quyết định (Tasks 1-9) · §2 package (T3-5) · §3 hook (T6) · §4 API (T7) · §5 UI (T8) · §6 lỗi/Qdrant lock (T6 main try/except, T7 503, T8 fallback) · §7 test/smoke (mỗi task + T9).
- **Type consistency:** `pending_embedding` trả keys mà `news_text`/payload dùng — khớp; `ensure_profile(store, vs, cfg, user_id, runner, embedder)` thống nhất T5/T7/T9; `recommend(store, vs, user_id, k)` T4/T7/T9; FakeVectors T6 đủ 2 method được gọi; test API seed profile qua `compute_hash` để tránh gọi API thật — cache-hit yêu cầu vector tồn tại (`vs.upsert_user` trong test) đúng điều kiện `ensure_profile`.
- **Placeholder:** không còn; điểm hoãn có chủ đích: bio default từ Discord (best-effort) không nằm trong vòng này — ghi ở spec, không phải plan gap.
