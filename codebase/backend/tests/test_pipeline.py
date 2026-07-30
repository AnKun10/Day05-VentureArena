from pathlib import Path

from ingest.__main__ import run_once
from ingest.config import Config
from ingest.models import NewsEnrichment
from ingest.sources import SeedSource
from ingest.store import Store

SEED = str(Path(__file__).resolve().parent.parent / "ingest" / "seeds" / "posts.json")


def fake_runner(text):
    return NewsEnrichment(summary_vi="Tóm tắt giả.", tags=["other"],
                          image_query="q", image_url=None)


def failing_runner(text):
    raise RuntimeError("api down")


def test_run_once_then_enrich_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # tránh ghi đè trace thật ở eval/traces/ingest
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    stats1 = run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    assert stats1["fetched"] == 10 and stats1["enriched"] == 10
    stats2 = run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    assert stats2["fetched"] == 0 and stats2["enriched"] == 0  # checkpoint + enrich-once


def test_run_once_force_reenriches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    stats = run_once(store, SeedSource(SEED), cfg, force=True, runner=fake_runner)
    assert stats["enriched"] == 10


def test_run_once_failure_marks_and_continues(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    stats = run_once(store, SeedSource(SEED), cfg, runner=failing_runner)
    assert stats["failed"] == 10 and stats["enriched"] == 0
    row = store.get_news("1001")
    assert row["enrich_failed"] == 1 and row["tags"] == ["other"]


class TaiNguyenSource:
    def fetch(self, since):
        from ingest.models import RawPost
        return [RawPost(message_id="2001", channel="tai-nguyen",
                        title="Slide Workshop WS2: Problem -> MVP Canvas",
                        content="", author="BTC", created_at="2026-07-31T08:00:00",
                        jump_url="https://discord.com/x/2001")]


def test_run_once_routes_tai_nguyen_to_resources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(str(tmp_path / "t.db"))
    stats = run_once(store, TaiNguyenSource(), Config(), runner=fake_runner)
    assert stats["fetched"] == 1 and stats["enriched"] == 0
    res = store.list_resources()
    assert len(res) == 1
    assert res[0]["session_code"] == "WS-2" and res[0]["kind"] == "slide"
    assert store.get_checkpoint("tai-nguyen") == 2001


class FakeVectors:
    def __init__(self):
        self.news, self.payloads = {}, {}
    def upsert_news(self, mid, vec, payload):
        self.news[mid] = (list(vec), payload)
    def update_news_payload(self, mid, hearts, comment_count):
        self.payloads[mid] = (hearts, comment_count)


def fake_embed(texts, cfg):
    return [[float(len(t)), 0.0] for t in texts]


def test_run_once_embeds_after_enrich(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(str(tmp_path / "t.db"))
    fv = FakeVectors()
    stats = run_once(store, SeedSource(SEED), Config(), runner=fake_runner,
                     vectors=fv, embed_fn=fake_embed)
    assert stats["embedded"] == 10 and len(fv.news) == 10
    stats2 = run_once(store, SeedSource(SEED), Config(), runner=fake_runner,
                      vectors=fv, embed_fn=fake_embed)
    assert stats2["embedded"] == 0                     # embed-once
    assert len(fv.payloads) == 10                      # payload refresh vẫn chạy


def test_run_once_without_vectors_keeps_old_behavior(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(str(tmp_path / "t.db"))
    stats = run_once(store, SeedSource(SEED), Config(), runner=fake_runner)
    assert stats["embedded"] == 0
