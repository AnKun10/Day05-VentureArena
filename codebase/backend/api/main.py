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
