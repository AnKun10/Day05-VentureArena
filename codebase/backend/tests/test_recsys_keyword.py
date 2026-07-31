"""Test keyword fallback (recommend_keyword) — thuần, dùng fake store, không Qdrant."""

from datetime import datetime

from recsys import recommend_keyword

NOW_ISO = datetime.utcnow().isoformat()


class FakeStore:
    def __init__(self, user, news, bookmarks=()):
        self._user = user
        self._news = news
        self._bm = list(bookmarks)

    def get_user(self, uid):
        return self._user

    def list_bookmarks(self, uid):
        return self._bm

    def list_news(self):
        return self._news


def _n(mid, title, summary="", tags=(), hearts=0, comments=0):
    return {"message_id": mid, "title": title, "summary": summary,
            "tags": list(tags), "hearts": hearts, "comment_count": comments,
            "created_at": NOW_ISO}


def test_keyword_ranks_by_bio_overlap():
    store = FakeStore(
        user={"bio": "AI Engineer interested in VLM and multimodal retrieval",
              "interest_summary": ""},
        news=[
            _n("1", "Bài về multimodal retrieval và VLM", tags=["ai-model"]),
            _n("2", "Hướng dẫn UI/UX cho web", tags=["ui-ux"]),
            _n("3", "Dataset cho xe tự hành", tags=["dataset"]),
        ])
    out = recommend_keyword(store, "u", k=3)
    assert out[0]["message_id"] == "1"                 # trùng nhiều từ khoá nhất
    assert out[0]["parts"]["sim"] > out[1]["parts"]["sim"]


def test_keyword_excludes_bookmarked():
    store = FakeStore(
        user={"bio": "VLM", "interest_summary": ""},
        news=[_n("1", "VLM paper"), _n("2", "VLM tutorial")],
        bookmarks=["1"])
    out = recommend_keyword(store, "u", k=5)
    assert [o["message_id"] for o in out] == ["2"]


def test_keyword_no_bio_falls_back_to_hot_ranking():
    store = FakeStore(
        user={"bio": "", "interest_summary": ""},
        news=[
            _n("low", "Bài ít tương tác", hearts=0, comments=0),
            _n("hot", "Bài nhiều tương tác", hearts=50, comments=20),
        ])
    out = recommend_keyword(store, "u", k=2)
    assert out[0]["message_id"] == "hot"               # không bio → tương tác + mới
    assert all(o["parts"]["sim"] == 0.0 for o in out)


def test_keyword_missing_user_is_safe():
    store = FakeStore(user=None, news=[_n("1", "abc")])
    out = recommend_keyword(store, "ghost", k=1)
    assert len(out) == 1 and out[0]["message_id"] == "1"
