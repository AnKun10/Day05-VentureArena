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
    assert client.get("/api/recommendations", params={"user_id": "zzz"}).status_code == 200
