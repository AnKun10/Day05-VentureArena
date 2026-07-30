from companion_discord.ingestion import latest_posts, save_posts


def test_ingestion_persists_each_discord_message_once_with_its_jump_link(tmp_path):
    database = tmp_path / "companion.sqlite3"
    post = {
        "message_id": "42",
        "channel_id": "123",
        "source_group": "announcements",
        "author_id": "7",
        "author_name": "BTC",
        "author_roles": ["Admin"],
        "content": "Deadline nộp spec: 23:59 ngày 1.",
        "attachments": [],
        "jump_url": "https://discord.com/channels/1/123/42",
        "created_at": "2026-07-30T10:00:00+00:00",
    }

    save_posts(database, [post, post])

    assert latest_posts(database, "announcements", 5) == [post]
