from datetime import datetime, timedelta
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest.config import Config
from ingest.schedule import build_schedule
from ingest.store import Store

import app as qa  # Q&A core POST /api/ask (Nghĩa) — mount vào cùng một server

app = FastAPI(title="Companion API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.add_api_route("/api/ask", qa.ask, methods=["POST"], response_model=qa.AskResponse)


def get_store() -> Store:
    return Store(Config.from_env().db_path)


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
    return build_schedule(settings, events, resources, from_, to)


@app.get("/api/recommendations")
def recommendations(user_id: str, k: int = 6, store: Store = Depends(get_store)):
    from recsys import ensure_profile, recommend
    try:
        vs = get_vectors()
    except Exception as exc:
        raise HTTPException(503, detail=f"vector store unavailable: {exc}")
    _seed_users(store)
    store.ensure_user(user_id)
    try:
        ensure_profile(store, vs, Config.from_env(), user_id)
    except Exception as exc:                    # inference lỗi → dùng profile cũ/fallback
        print(f"[recsys] ensure_profile failed: {exc}")
    return recommend(store, vs, user_id, k=k)
