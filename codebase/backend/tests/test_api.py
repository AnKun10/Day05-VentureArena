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
