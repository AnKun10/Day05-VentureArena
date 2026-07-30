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
