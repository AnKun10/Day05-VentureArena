from ingest.config import Config
from recsys.embedder import embed_texts, news_text
from recsys.vectorstore import VectorStore


class FakeEmbeddings:
    def create(self, model, input):
        class D:  # noqa: N801
            def __init__(self, v): self.embedding = v
        class R:
            data = [D([float(len(t))] * 4) for t in input]
        return R()


class FakeOpenAI:
    embeddings = FakeEmbeddings()


def test_embed_texts_uses_injected_client():
    vecs = embed_texts(["ab", "abcd"], Config(), client=FakeOpenAI())
    assert vecs == [[2.0] * 4, [4.0] * 4]


def test_news_text_format():
    t = news_text({"title": "T", "summary": "S", "tags": ["uiux", "other"]})
    assert t == "T\nS\nTags: uiux, other"
    assert news_text({"title": "T", "summary": None, "tags": []}) == "T\n\nTags: "


def test_vectorstore_news_roundtrip(tmp_path):
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    vs.upsert_news("1001", [1, 0, 0, 0],
                   {"message_id": "1001", "tags": ["ai-model"], "created_at": "2026-07-30T09:00:00",
                    "hearts": 5, "comment_count": 1})
    vs.update_news_payload("1001", hearts=9, comment_count=2)
    items = vs.all_news()
    assert len(items) == 1
    mid, vec, payload = items[0]
    assert mid == "1001" and payload["hearts"] == 9 and list(vec)[:1] == [1.0]


def test_vectorstore_user_roundtrip(tmp_path):
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    assert vs.get_user("u1") is None
    vs.upsert_user("u1", [0, 1, 0, 0])
    assert list(vs.get_user("u1")) == [0.0, 1.0, 0.0, 0.0]
