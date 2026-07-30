import pytest
from pydantic import ValidationError
from ingest.models import NewsEnrichment, RawPost, TAG_IDS


def test_tag_ids_complete():
    assert TAG_IDS == ["ai-model", "ai-skill", "ai-tools", "api-mcp", "system-design",
                       "uiux", "dataset", "soft-skills", "survey", "other"]


def test_enrichment_rejects_unknown_tag():
    with pytest.raises(ValidationError):
        NewsEnrichment(summary_vi="x", tags=["blockchain"], image_query="q")


def test_enrichment_rejects_empty_and_too_many_tags():
    with pytest.raises(ValidationError):
        NewsEnrichment(summary_vi="x", tags=[], image_query="q")
    with pytest.raises(ValidationError):
        NewsEnrichment(summary_vi="x", tags=["other"] * 4, image_query="q")


def test_rawpost_defaults():
    p = RawPost(message_id="1", channel="bai-hoc", title="t", content="c",
                author="A", created_at="2026-07-31T10:00:00")
    assert p.author_role == "Học viên" and p.comments == [] and p.hearts == 0
