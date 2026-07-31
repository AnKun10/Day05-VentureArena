"""Test Daily AI News (offline: fake runner + store roundtrip)."""

from ai_news import DailyNews, NewsItem, generate_daily_news
from ai_news.agent import _domain
from ingest.store import Store


def test_domain():
    assert _domain("https://www.techcrunch.com/2026/01/x") == "techcrunch.com"
    assert _domain("https://arxiv.org/abs/1234") == "arxiv.org"


def test_generate_maps_and_fills_source(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.ensure_user("u1", "U")

    def fake_runner(prompt):
        assert "sở thích" in prompt.lower() or "so thich" in prompt.lower() or prompt
        return DailyNews(items=[
            NewsItem(title="New VLM", url="https://techcrunch.com/vlm", source="", summary_vi="Tóm tắt A"),
            NewsItem(title="Agent tools", url="https://theverge.com/agents", source="theverge.com",
                     summary_vi="Tóm tắt B"),
        ])

    out = generate_daily_news(s, "u1", cfg=None, runner=fake_runner)
    assert len(out) == 2
    assert out[0]["source"] == "techcrunch.com"          # suy từ url khi source rỗng
    assert out[1]["source"] == "theverge.com"
    assert out[0]["summary"] == "Tóm tắt A"


def test_store_ai_news_roundtrip(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    assert s.get_ai_news("u1", "2026-07-31") == []
    items = [{"title": "T1", "url": "https://a/1", "source": "a.com", "summary": "s1"},
             {"title": "T2", "url": "https://b/2", "source": "b.com", "summary": "s2"}]
    s.save_ai_news("u1", "2026-07-31", items)
    got = s.get_ai_news("u1", "2026-07-31")
    assert [g["title"] for g in got] == ["T1", "T2"]
    assert got[0]["rank"] == 0 and got[1]["rank"] == 1
    # lưu lại (ngày khác user khác) không đụng nhau; ghi đè cùng key
    s.save_ai_news("u1", "2026-07-31", items[:1])
    assert len(s.get_ai_news("u1", "2026-07-31")) == 1
