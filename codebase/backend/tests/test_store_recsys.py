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
