from ingest.sources import map_role, normalize_channel_name, resolve_forum_channels, thread_to_rawpost


def test_normalize_channel_name():
    assert normalize_channel_name("📖-bài-học") == "-bai-hoc"
    assert normalize_channel_name("🎨︱chia-sẻ") == "chia-se"
    assert normalize_channel_name("tài-nguyên") == "tai-nguyen"


def test_resolve_forum_channels_by_name():
    channels = [(1, "🙋-hỏi-đáp"), (2, "📖-bài-học"), (3, "🎨︱chia-sẻ"),
                (4, "🗂-tài-nguyên"), (5, "general")]
    assert resolve_forum_channels(channels) == {
        "bai-hoc": "2", "chia-se": "3", "tai-nguyen": "4"}


def test_map_role():
    assert map_role(["Lab Coach", "Member"]) == "Lab Coach"
    assert map_role(["BTC"]) == "BTC"
    assert map_role(["Admin"]) == "BTC"
    assert map_role(["Mentor 2026"]) == "Mentor"
    assert map_role(["Member"]) == "Học viên"
    assert map_role([]) == "Học viên"


def test_thread_to_rawpost_maps_fields():
    p = thread_to_rawpost(
        thread_id="555", channel_key="bai-hoc", title="Bài chia sẻ",
        starter_content="Nội dung", author_name="T001", role_names=["Member"],
        jump_url="https://discord.com/x", created_at_iso="2026-07-31T09:00:00",
        hearts=7,
        comment_tuples=[("556", "T002", ["Lab Coach"], "hay", "2026-07-31T10:00:00")],
    )
    assert p.message_id == "555" and p.channel == "bai-hoc"
    assert p.comments[0].author_role == "Lab Coach" and p.hearts == 7
