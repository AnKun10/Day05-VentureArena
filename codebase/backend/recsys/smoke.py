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
