"""Test retrieval /ask: lexical, RRF fuse, hybrid, và search_resources (offline)."""

from ask.retrieval import cosine, rank, rrf_fuse, search_qa, search_resources, tokens


class FakeStore:
    def __init__(self, qa=(), news=(), resources=(), events=(), embeddings=None):
        self._qa, self._news = list(qa), list(news)
        self._res, self._ev = list(resources), list(events)
        self._emb = dict(embeddings or {})

    def list_qa_threads(self):
        return self._qa

    def list_news(self):
        return self._news

    def list_resources(self):
        return self._res

    def all_schedule_events(self):
        return self._ev

    def get_ask_embeddings(self):
        return self._emb


# ---------- lexical ----------

def test_tokens_strips_accent_and_stopwords():
    t = tokens("Khi nào có buổi Workshop về RAG?")
    assert "workshop" in t and "rag" in t
    assert "khi" not in t and "co" not in t


def test_rank_requires_overlap_and_orders_by_count():
    docs = [{"t": "workshop nâng cao"}, {"t": "lịch nghỉ lễ"},
            {"t": "rag workshop slide record"}]
    out = rank("workshop rag slide", docs, lambda d: d["t"], k=5)
    assert out[0]["t"] == "rag workshop slide record"
    assert {"t": "lịch nghỉ lễ"} not in out


# ---------- RRF ----------

def test_rrf_rewards_agreement_of_two_signals():
    lex = ["a", "b", "c"]      # a hạng 1 lexical
    sem = ["b", "a", "d"]      # b hạng 1 semantic, a hạng 2
    fused = rrf_fuse([lex, sem])
    # a và b đều xuất hiện ở cả 2 danh sách → cao hơn c (chỉ lexical) và d (chỉ semantic)
    order = sorted(fused, key=lambda i: fused[i], reverse=True)
    assert set(order[:2]) == {"a", "b"}
    assert fused["a"] > fused["c"] and fused["b"] > fused["d"]


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0
    assert cosine([], [1]) == 0.0


# ---------- hybrid: semantic tìm được bài lexical bỏ lỡ ----------

def test_hybrid_surfaces_semantic_only_match():
    store = FakeStore(
        qa=[{"thread_id": "1", "title": "autonomous vehicle perception", "body": "bev lidar",
             "jump_url": "u1"},
            {"thread_id": "2", "title": "xyz foo", "body": "xyz foo", "jump_url": "u2"}],
        embeddings={"qa:1": [1.0, 0.0], "qa:2": [0.0, 1.0]})
    fake_embed = lambda text: [1.0, 0.0]        # câu hỏi gần qa:1 về semantic
    out = search_qa(store, "xyz", embed=fake_embed)
    titles = {r["title"] for r in out}
    # qa:2 khớp lexical ("xyz"); qa:1 khớp semantic (cosine=1.0) dù không trùng từ
    assert "autonomous vehicle perception" in titles and "xyz foo" in titles


def test_search_qa_lexical_fallback_when_no_embedder():
    store = FakeStore(
        qa=[{"thread_id": "1", "title": "Tải slide ở đâu", "body": "vào vlearn tải slide",
             "jump_url": "https://d/qa1"}],
        news=[{"message_id": "n1", "title": "Cách tải slide trên Vlearn",
               "summary": "hướng dẫn tải slide", "tags": ["ai-tools"], "jump_url": "https://d/n1"}])
    out = search_qa(store, "tải slide")        # embed=None → lexical thuần
    assert {r["source"] for r in out} == {"hỏi-đáp", "bản tin"}


# ---------- resources (keyword) ----------

def test_search_resources_includes_zoom_from_schedule():
    store = FakeStore(
        resources=[{"kind": "record", "title": "Recording WS1", "session_code": "WS-1",
                    "url": "https://d/rec1"}],
        events=[{"title": "Workshop 1", "type": "WS", "date": "2026-07-24",
                 "start": "20:00", "zoom_url": "https://zoom.us/j/1"},
                {"title": "Buổi Lab", "type": "LAB", "zoom_url": None}])
    out = search_resources(store, "workshop recording zoom")
    kinds = {r["kind"] for r in out}
    assert "record" in kinds and "zoom" in kinds
    zoom = next(r for r in out if r["kind"] == "zoom")
    assert zoom["url"] == "https://zoom.us/j/1" and zoom["when"] == "2026-07-24 20:00"


def test_search_resources_no_match_returns_empty():
    store = FakeStore(resources=[{"kind": "doc", "title": "abc", "url": "u"}])
    assert search_resources(store, "xyz không liên quan gì") == []


def test_search_news_uses_title_summary_not_comment():
    from ask.retrieval import search_news
    news = [
        {"message_id": "1", "title": "Prompt Injection phòng chống",
         "summary": "cách chống injection", "content": "ZZKEYWORD trong body", "tags": ["ai-model"]},
        {"message_id": "2", "title": "UI/UX design", "summary": "thiết kế giao diện",
         "content": "x", "tags": ["ui-ux"]},
    ]
    out = search_news(news, {}, "prompt injection", embed=None, k=5)
    assert out and out[0]["message_id"] == "1"
    # từ khoá chỉ có trong content/comment (không phải title/summary) → KHÔNG match
    assert search_news(news, {}, "ZZKEYWORD", embed=None, k=5) == []
    # helper keys _id/_emb/_text bị loại khỏi kết quả trả về
    assert all(not str(k).startswith("_") for k in out[0])
