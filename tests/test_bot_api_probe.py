from types import SimpleNamespace

from companion_discord.api_probe import message_payload


def test_message_payload_keeps_plaintext_newlines_and_separate_discord_metadata():
    attachment = SimpleNamespace(filename="notes.pdf", url="https://cdn.example/notes.pdf", content_type="application/pdf", size=12)
    embed = SimpleNamespace(title="Preview", description="Description", url="https://example.test", fields=[SimpleNamespace(name="Field", value="Value", inline=False)], image=SimpleNamespace(url=None), thumbnail=SimpleNamespace(url=None), type="link")
    reaction = SimpleNamespace(emoji="👍", count=2, me=False)
    message = SimpleNamespace(
        id=3,
        channel=SimpleNamespace(id=2),
        content="1. First line\n2. https://example.test",
        author=SimpleNamespace(id=1, display_name="Teacher"),
        created_at=SimpleNamespace(isoformat=lambda: "2026-07-31T00:00:00+00:00"),
        edited_at=None,
        jump_url="https://discord.com/channels/1/2/3",
        attachments=[attachment],
        embeds=[embed],
        reference=None,
        pinned=True,
        reactions=[reaction],
    )

    result = message_payload(message)

    assert result["content"] == "1. First line\n2. https://example.test"
    assert result["content_urls"] == ["https://example.test"]
    assert result["author"] == {"id": "1", "display_name": "Teacher", "roles": [], "role_snapshot_status": "not_resolved"}
    assert result["attachments"] == [{"name": "notes.pdf", "url": "https://cdn.example/notes.pdf", "content_type": "application/pdf", "size": 12}]
    assert result["embeds"][0]["title"] == "Preview"
    assert result["reactions"] == [{"emoji": "👍", "count": 2, "me": False}]


def test_message_payload_accepts_a_resolved_author_and_location():
    message = SimpleNamespace(
        id=3,
        channel=SimpleNamespace(id=2),
        content="Line one\nLine two",
        author=SimpleNamespace(id=1, display_name="Teacher"),
        created_at=SimpleNamespace(isoformat=lambda: "2026-07-31T00:00:00+00:00"),
        edited_at=None,
        jump_url="https://discord.com/channels/1/2/3",
        attachments=[], embeds=[], reference=None, pinned=False, reactions=[],
    )

    result = message_payload(
        message,
        author={"id": "1", "display_name": "Teacher", "roles": [{"id": "9", "name": "Moderator"}], "role_snapshot_status": "resolved"},
        location={"channel": {"id": "2", "name": "chung"}, "message_url": message.jump_url},
    )

    assert result["content"] == "Line one\nLine two"
    assert result["author"]["roles"] == [{"id": "9", "name": "Moderator"}]
    assert result["location"]["channel"]["name"] == "chung"
