import json
from ingest.config import Config
from ingest.agents import enrich_post
from ingest.tools import pick_image
from ingest.models import NewsEnrichment


def test_pick_image_filters_bad_urls():
    assert pick_image(["http://x/a.png", "https://x/logo.svg",
                       "https://x/photo.jpg"]) == "https://x/photo.jpg"
    assert pick_image([]) is None


def test_enrich_post_with_injected_runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # trace ghi vào cwd/eval/traces/ingest/
    fake = NewsEnrichment(summary_vi="Tóm tắt.", tags=["survey"],
                          image_query="q", image_url="https://x/p.jpg")
    post = {"message_id": "1009", "title": "Khảo sát", "content": "...",
            "channel": "bai-hoc"}
    e, image_source, trace_id = enrich_post(post, Config(), runner=lambda text: fake)
    assert e.tags == ["survey"] and image_source == "tavily"
    trace = json.loads(
        (tmp_path / "eval/traces/ingest/1009.json").read_text(encoding="utf-8"))
    assert trace["prompt_version"] == "v1" and trace["output"]["tags"] == ["survey"]


def test_enrich_post_placeholder_when_no_image(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake = NewsEnrichment(summary_vi="x", tags=["other"], image_query="q",
                          image_url=None)
    post = {"message_id": "1010", "title": "t", "content": "c", "channel": "chia-se"}
    _, image_source, _ = enrich_post(post, Config(), runner=lambda text: fake)
    assert image_source == "placeholder"
