from ingest.config import Config
from ingest.models import NewsEnrichment
from ingest.store import Store
from recsys.profile import InterestProfile, compute_hash, ensure_profile
from recsys.vectorstore import VectorStore
from tests.test_store import make_post

FAKE = InterestProfile(interest_summary_vi="Mê CV.", interest_tags=["ai-model"])


def setup(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    s.upsert_user("u1", "An", bio="Thích xe tự hành")
    return s, vs


def test_hash_changes_with_bio_and_bookmarks():
    h1 = compute_hash("bio", [])
    assert h1 != compute_hash("bio2", [])
    assert h1 != compute_hash("bio", ["9"])
    assert compute_hash("bio", ["2", "1"]) == compute_hash("bio", ["1", "2"])


def test_infer_once_then_cached(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s, vs = setup(tmp_path)
    calls = []
    runner = lambda text: (calls.append(text) or FAKE)
    embedder = lambda texts, cfg: [[0.0, 1.0, 0.0, 0.0]]
    assert ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder) is True
    assert ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder) is False
    assert len(calls) == 1                       # cache hash
    assert list(vs.get_user("u1")) == [0.0, 1.0, 0.0, 0.0]
    assert s.get_user("u1")["interest_tags"] == ["ai-model"]
    assert "Thích xe tự hành" in calls[0]


def test_bookmark_change_triggers_reinfer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s, vs = setup(tmp_path)
    s.upsert_post(make_post(mid="1"))
    s.save_enrichment("1", NewsEnrichment(summary_vi="Tóm tắt.", tags=["dataset"],
                                          image_query="q"), "placeholder", "v1", "t")
    runner = lambda text: FAKE
    embedder = lambda texts, cfg: [[1.0, 0.0, 0.0, 0.0]]
    ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder)
    s.toggle_bookmark("u1", "1")
    assert ensure_profile(s, vs, Config(), "u1", runner=runner, embedder=embedder) is True


def test_blank_user_no_infer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s, vs = setup(tmp_path)
    s.upsert_user("u2", "Trắng")                  # bio rỗng, không bookmark
    boom = lambda text: (_ for _ in ()).throw(AssertionError("không được gọi"))
    assert ensure_profile(s, vs, Config(), "u2", runner=boom, embedder=None) is False
    assert vs.get_user("u2") is None


def test_unknown_user_raises(tmp_path):
    s, vs = setup(tmp_path)
    import pytest
    with pytest.raises(KeyError):
        ensure_profile(s, vs, Config(), "zzz", runner=lambda t: FAKE,
                       embedder=lambda t, c: [[0, 0, 0, 0]])
