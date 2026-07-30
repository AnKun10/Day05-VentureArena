from ingest.__main__ import run_once
from ingest.config import Config
from ingest.models import NewsEnrichment
from ingest.sources import SeedSource
from ingest.store import Store

SEED = "ingest/seeds/posts.json"


def fake_runner(text):
    return NewsEnrichment(summary_vi="Tóm tắt giả.", tags=["other"],
                          image_query="q", image_url=None)


def failing_runner(text):
    raise RuntimeError("api down")


def test_run_once_then_enrich_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path.parent if False else ".")  # giữ cwd backend
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    stats1 = run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    assert stats1["fetched"] == 10 and stats1["enriched"] == 10
    stats2 = run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    assert stats2["fetched"] == 0 and stats2["enriched"] == 0  # checkpoint + enrich-once


def test_run_once_force_reenriches(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    run_once(store, SeedSource(SEED), cfg, runner=fake_runner)
    stats = run_once(store, SeedSource(SEED), cfg, force=True, runner=fake_runner)
    assert stats["enriched"] == 10


def test_run_once_failure_marks_and_continues(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    cfg = Config()
    stats = run_once(store, SeedSource(SEED), cfg, runner=failing_runner)
    assert stats["failed"] == 10 and stats["enriched"] == 0
    row = store.get_news("1001")
    assert row["enrich_failed"] == 1 and row["tags"] == ["other"]
