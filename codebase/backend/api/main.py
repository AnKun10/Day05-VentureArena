import os
from datetime import datetime, timedelta
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ingest.config import Config
from ingest.schedule import build_schedule
from ingest.store import Store
from guardrails import check_bio, check_question

app = FastAPI(title="Companion API")
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins,
                   allow_origin_regex=r"https://.*\.vercel\.app",
                   allow_methods=["*"], allow_headers=["*"])


def get_store() -> Store:
    return Store(Config.from_env().db_path)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)


class AskResponse(BaseModel):
    action: str                       # answer | no_info | clarify | refuse | blocked
    answer: str
    citations: list[str] = []
    confidence: float = 0.0
    meta: dict = {}                   # {latency_ms, output_tokens, input_tokens, tool_calls}


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest, store: Store = Depends(get_store)) -> AskResponse:
    """Agent hỏi-đáp có tool (giờ + hỏi-đáp/bản tin + tài nguyên/lịch). Guardrail
    chặn nội dung không phù hợp / injection TRƯỚC khi vào agent. Trả kèm `meta`
    (latency, token, số lần gọi tool) để bot log quan sát."""
    verdict = check_question(request.question)
    if not verdict.ok:
        return AskResponse(action="blocked", answer=verdict.reason)
    from ask import answer_question
    t0 = datetime.now()
    try:
        result, meta = answer_question(store, verdict.text, Config.from_env())
    except Exception as exc:
        print(f"[ask] agent failed: {exc}")
        return AskResponse(action="no_info",
                           answer="Companion tạm thời chưa trả lời được. Bạn thử lại sau nhé.")
    meta = {**meta, "latency_ms": int((datetime.now() - t0).total_seconds() * 1000)}
    return AskResponse(
        action=result.action,          # answer | no_info | clarify | refuse
        answer=result.answer_vi,
        citations=list(dict.fromkeys(result.citations)),   # bỏ trùng, giữ thứ tự
        confidence=1.0 if result.action == "answer" else 0.0,
        meta=meta)


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


@app.get("/api/news")
def list_news(tag: str | None = None, store: Store = Depends(get_store)):
    return store.list_news(tag=tag)


@app.get("/api/news/search")
def news_search(q: str, k: int = 20, store: Store = Depends(get_store)):
    """Hybrid search (lexical + semantic RRF rerank) trên bản tin — chỉ theo
    heading + tóm tắt, KHÔNG dùng comment."""
    from ask.retrieval import search_news
    from recsys.embedder import embed_texts
    cfg = Config.from_env()

    def _embed(text):
        return embed_texts([text], cfg)[0]

    if not (q or "").strip():
        return []
    return search_news(store.list_news(), store.get_ask_embeddings(), q, _embed, k)


@app.get("/api/news/{message_id}")
def news_detail(message_id: str, store: Store = Depends(get_store)):
    news = store.get_news(message_id)
    if news is None or news.get("enriched_at") is None:
        raise HTTPException(404)
    return news


@app.get("/api/resources")
def resources(store: Store = Depends(get_store)):
    return store.list_resources()


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
    verdict = check_bio(body.bio)
    if not verdict.ok:
        raise HTTPException(422, detail=verdict.reason)
    store.set_bio(user_id, verdict.text)
    # Suy hồ sơ sở thích NGAY khi lưu bio (thay vì lúc đọc recommendations) để
    # /api/recommendations luôn nhanh (<1s) — non-fatal nếu OpenAI/Qdrant lỗi.
    try:
        from recsys import ensure_profile
        ensure_profile(store, get_vectors(), Config.from_env(), user_id)
    except Exception as exc:
        print(f"[recsys] ensure_profile on bio-write failed: {exc}")
    return {"ok": True}


class AvatarBody(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


@app.put("/api/users/{user_id}/avatar")
def put_avatar(user_id: str, body: AvatarBody, store: Store = Depends(get_store)):
    """Bot đồng bộ tên + avatar Discord của user (để UI hiển thị đúng người)."""
    store.set_avatar(user_id, body.name, body.avatar_url)
    return {"ok": True}


@app.get("/api/users/{user_id}/bookmarks")
def bookmarks(user_id: str, store: Store = Depends(get_store)):
    return store.list_bookmarks(user_id)


@app.get("/api/users/{user_id}/bookmarks/news")
def bookmarks_news(user_id: str, store: Store = Depends(get_store)):
    """Full bản tin đã bookmark của user — cho trang Bookmark."""
    return store.list_bookmarked_news(user_id)


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


class SettingsBody(BaseModel):
    cohort: Literal["3", "4"]
    lt_room: str
    lab_room: str


@app.get("/api/users/{user_id}/settings")
def get_user_settings(user_id: str, store: Store = Depends(get_store)):
    store.ensure_user(user_id)
    return store.get_settings(user_id)


@app.put("/api/users/{user_id}/settings")
def put_user_settings(user_id: str, body: SettingsBody, store: Store = Depends(get_store)):
    store.ensure_user(user_id)
    store.set_settings(user_id, body.cohort, body.lt_room, body.lab_room)
    return store.get_settings(user_id)


@app.get("/api/schedule")
def get_schedule(user_id: str | None = None, cohort: str | None = None,
                 from_: str | None = Query(None, alias="from"),
                 to: str | None = Query(None),
                 store: Store = Depends(get_store)):
    if not from_ or not to:
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        saturday = monday + timedelta(days=5)
        from_ = from_ or monday.strftime("%Y-%m-%d")
        to = to or saturday.strftime("%Y-%m-%d")
    if user_id:
        store.ensure_user(user_id)
        settings = store.get_settings(user_id)
    else:
        settings = {"cohort": cohort or "4", "lt_room": "D302", "lab_room": "D305"}
    events = store.list_schedule_events(settings["cohort"], from_, to)
    resources = store.list_resources()
    items = build_schedule(settings, events, resources, from_, to)
    if user_id:                       # áp chỉnh sửa cá nhân (chỉ của user này)
        from ingest.schedule import apply_user_overrides
        items = apply_user_overrides(items, store.get_schedule_overrides(user_id), from_, to)
    return items


class ScheduleOverrideBody(BaseModel):
    block_key: str
    hidden: bool = False
    patch: dict | None = None         # {title?, start?, end?, location?, format?, host?, zoom_url?}
    custom: dict | None = None        # buổi tự thêm: {date, type, title, start, end, location, format...}


@app.put("/api/users/{user_id}/schedule/override")
def put_schedule_override(user_id: str, body: ScheduleOverrideBody,
                          store: Store = Depends(get_store)):
    """Lưu chỉnh sửa lịch của RIÊNG user: ẩn buổi / sửa field / thêm buổi tự tạo."""
    store.ensure_user(user_id)
    store.set_schedule_override(user_id, body.block_key, body.hidden, body.patch, body.custom)
    return {"ok": True}


@app.delete("/api/users/{user_id}/schedule/override/{block_key:path}")
def delete_schedule_override(user_id: str, block_key: str, store: Store = Depends(get_store)):
    """Bỏ chỉnh sửa (khôi phục về bản do hệ thống/Agent dựng)."""
    store.delete_schedule_override(user_id, block_key)
    return {"ok": True}


@app.get("/api/ai-news")
def ai_news(user_id: str, k: int = 5, store: Store = Depends(get_store)):
    """Daily AI News ca nhan hoa - cache theo (user, ngay). Lan dau trong ngay
    chay agent (Tavily crawl + verify source); cac lan sau lay cache."""
    store.ensure_user(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    cached = store.get_ai_news(user_id, today)
    if cached:
        return {"date": today, "items": cached[:k], "cached": True}
    from ai_news import generate_daily_news
    try:
        items = generate_daily_news(store, user_id, Config.from_env())
    except Exception as exc:
        print(f"[ai-news] generate failed: {exc}")
        return {"date": today, "items": [], "cached": False}
    if items:
        store.save_ai_news(user_id, today, items)
    return {"date": today, "items": items[:k], "cached": False}


@app.get("/api/recommendations")
def recommendations(user_id: str, k: int = 6, store: Store = Depends(get_store)):
    """Không bao giờ 503. Chuỗi hạ cấp:
      1) Qdrant + vector (hồ sơ đã suy lúc lưu bio) — tốt nhất.
      2) Qdrant chết / user chưa có vector → xếp hạng bằng keyword (SQLite thuần).
      3) Không có bio → keyword degenerate về hot ranking (tương tác + mới).
    """
    from recsys import ensure_profile, recommend, recommend_keyword
    _seed_users(store)
    store.ensure_user(user_id)
    try:
        vs = get_vectors()
    except Exception as exc:                    # Qdrant không sẵn sàng → keyword fallback
        print(f"[recsys] vector store unavailable, keyword fallback: {exc}")
        return recommend_keyword(store, user_id, k=k)
    try:
        # top-up hồ sơ nếu lỡ chưa suy (vd bio set qua đường khác); no-op nếu đã có
        ensure_profile(store, vs, Config.from_env(), user_id)
    except Exception as exc:
        print(f"[recsys] ensure_profile failed, dùng profile cũ/fallback: {exc}")
    try:
        results = recommend(store, vs, user_id, k=k)
        return results if results else recommend_keyword(store, user_id, k=k)
    except Exception as exc:                    # lỗi vector search bất ngờ → keyword fallback
        print(f"[recsys] vector recommend failed, keyword fallback: {exc}")
        return recommend_keyword(store, user_id, k=k)
