from ingest.sources import SeedSource

SEED = "ingest/seeds/posts.json"


def test_seed_loads_all_posts():
    posts = SeedSource(SEED).fetch(since={})
    assert len(posts) == 10
    assert posts[0].message_id and posts[0].channel in ("bai-hoc", "chia-se")


def test_seed_respects_checkpoint():
    src = SeedSource(SEED)
    all_posts = src.fetch(since={})
    max_id = max(int(p.message_id) for p in all_posts)
    assert src.fetch(since={"bai-hoc": max_id, "chia-se": max_id}) == []
