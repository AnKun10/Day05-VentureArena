import json

import pytest

from companion_discord.replication import ConfigError, build_rebuild_plan, load_replica_config
from companion_discord.rebuild import MENTIONS, _apply_allowed, _chunks, _custom_embeds, _manifest, _pending_messages, _replay_text, _select_manifest, _state


def _config(tmp_path, *, source="100", destination="200", allowlist=None, preserve=None, destination_mapping=None):
    path = tmp_path / "replica.yaml"
    path.write_text(
        "discord_bot:\n"
        f"  source_guild_id: '{source}'\n"
        f"  destination_guild_id: '{destination}'\n"
        "  destination_guild_allowlist:\n"
        + "".join(f"    - '{item}'\n" for item in (allowlist or [destination]))
        + "  manifest_path: data/discord_bot_crawl/manifest.json\n"
        + "  state_path: data/discord_bot_crawl/rebuild-state.json\n"
        + "  managed_categories: ['900']\n"
        + "  managed_channels: ['901']\n"
        + ("  preserve_channels: []\n" if not preserve else "  preserve_channels:\n" + "".join(f"    - '{item}'\n" for item in preserve))
        + ("  destination_channel_mappings: {}\n" if not destination_mapping else "  destination_channel_mappings:\n" + "".join(f"    {name}:\n      destination_channel_id: '{channel_id}'\n" for name, channel_id in destination_mapping.items()))
        + "  sources:\n"
        + "    cohort_4_common_announcements:\n"
        + "      guild_id: '100'\n"
        + "      channel_id: '400'\n",
        encoding="utf-8",
    )
    return path


def test_rebuild_rejects_a_manifest_from_the_destination_guild(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"source_guild": {"id": "100"}}', encoding="utf-8")
    with pytest.raises(ConfigError, match="different"):
        _manifest(manifest, "100")


def test_replica_config_rejects_destination_outside_allowlist(tmp_path):
    with pytest.raises(ConfigError, match="allowlist"):
        load_replica_config(_config(tmp_path, allowlist=["999"]))


def test_dry_run_deletes_only_configured_or_recorded_resources(tmp_path):
    config = load_replica_config(_config(tmp_path))
    manifest = {
        "source_guild": {"id": "100", "name": "Source"},
        "categories": [{"id": "10", "name": "Course"}],
        "channels": [{"id": "20", "name": "announcements", "type": "text", "category_id": "10", "messages": [{"id": "30"}]}],
    }
    state = {"created_category_ids": ["902"], "created_channel_ids": ["903"]}
    destination = {
        "categories": [{"id": "900"}, {"id": "902"}, {"id": "unmanaged-category"}],
        "channels": [{"id": "901"}, {"id": "903"}, {"id": "unmanaged-channel"}],
    }

    plan = build_rebuild_plan(config, manifest, state, destination)

    assert plan["delete_categories"] == ["900", "902"]
    assert plan["delete_channels"] == ["901", "903"]
    assert plan["create_categories"] == ["Course"]
    assert plan["message_count"] == 1
    assert json.loads(json.dumps(plan))["forum_post_count"] == 0


def test_preserved_or_system_resources_are_never_in_a_delete_plan(tmp_path):
    config = load_replica_config(_config(tmp_path, preserve=["901"]))
    plan = build_rebuild_plan(
        config, {"categories": [], "channels": []}, {},
        {"categories": [], "channels": [{"id": "901"}, {"id": "902"}], "protected_channel_ids": ["902"]},
        replace_all=True,
    )
    assert plan["delete_channels"] == []


def test_existing_mapping_resumes_without_creating_a_duplicate_channel(tmp_path):
    config = load_replica_config(_config(tmp_path))
    plan = build_rebuild_plan(
        config,
        {"categories": [], "channels": [{"id": "20", "name": "announcements", "type": "text", "messages": []}]},
        {"channels": {"20": "903"}},
        {"categories": [], "channels": [{"id": "903"}]},
    )
    assert plan["create_channels"] == []


def test_message_mapping_skips_replay_after_an_interruption():
    state = _state({"source_to_destination_message_ids": {"30": "930"}})
    pending = _pending_messages([{"id": "30"}, {"id": "31"}], state)
    assert state["messages"] == {"30": "930"}
    assert pending == [{"id": "31"}]


def test_selected_manifest_replays_only_the_latest_message_per_named_channel():
    manifest = {"channels": [
        {"source_name": "cohort_3_common_announcements", "messages": [{"id": "1"}, {"id": "2"}]},
        {"source_name": "cohort_4_common_announcements", "messages": [{"id": "3"}, {"id": "4"}]},
        {"source_name": "general", "messages": [{"id": "5"}]},
    ]}
    selected = _select_manifest(manifest, {"cohort_3_common_announcements", "cohort_4_common_announcements"}, 1)
    assert [channel["source_name"] for channel in selected["channels"]] == ["cohort_3_common_announcements", "cohort_4_common_announcements"]
    assert [[message["id"] for message in channel["messages"]] for channel in selected["channels"]] == [["2"], ["4"]]


def test_destination_mapping_reuses_existing_channel_instead_of_creating_one(tmp_path):
    config = load_replica_config(_config(tmp_path, destination_mapping={"cohort_3_common_announcements": "777"}))
    manifest = {"channels": [{"id": "20", "source_name": "cohort_3_common_announcements", "name": "source-name", "type": "text", "messages": []}]}
    plan = build_rebuild_plan(config, manifest, {}, {"categories": [], "channels": [{"id": "777"}], "configured_reuse": {"cohort_3_common_announcements": {"id": "777", "name": "thông-báo-chung", "type": "text"}}})
    assert plan["create_channels"] == []
    assert plan["reuse_existing_channels"] == [{"source_name": "cohort_3_common_announcements", "id": "777", "name": "thông-báo-chung", "type": "text"}]


def test_destination_mapping_keeps_the_superseded_bot_created_channel_by_default(tmp_path):
    config = load_replica_config(_config(tmp_path, destination_mapping={"cohort_3_common_announcements": "777"}))
    manifest = {"channels": [{"id": "20", "source_name": "cohort_3_common_announcements", "name": "source-name", "type": "text", "messages": []}]}
    state = {"channels": {"20": "901"}, "created_channel_ids": ["901"]}
    destination = {
        "categories": [],
        "channels": [{"id": "901"}, {"id": "777"}],
        "configured_reuse": {"cohort_3_common_announcements": {"id": "777", "name": "thông-báo-chung", "type": "text"}},
    }

    plan = build_rebuild_plan(config, manifest, state, destination)

    assert plan["delete_channels"] == []
    assert plan["retained_superseded_created_channel_ids"] == ["901"]


def test_visual_replay_preserves_newlines_urls_and_avoids_native_preview_embed_duplication(tmp_path):
    config = load_replica_config(_config(tmp_path))
    url = "https://example.test/slide"
    message = {"content": f"1. Slide\n\n2. Link: {url}", "content_urls": [url], "author": {"display_name": "Teacher"}, "created_at": "old", "attachments": [], "embeds": [{"title": "Native preview", "url": url, "fields": []}]}
    assert _replay_text(message, config) == f"1. Slide\n\n2. Link: {url}"
    assert _custom_embeds(message) == []


def test_chunks_keep_urls_together_and_mentions_are_disabled():
    url = "https://example.test/" + "a" * 100
    parts = _chunks(("intro " * 400) + url)
    assert url in parts[-1]
    assert all(len(part) <= 1_900 for part in parts)
    assert not MENTIONS.everyone and not MENTIONS.users and not MENTIONS.roles


def test_apply_requires_two_exact_destination_confirmations(tmp_path):
    config = load_replica_config(_config(tmp_path))
    args = type("Args", (), {"apply": True, "destination_guild_id": "200", "confirm_destination_guild_id": "200"})()
    assert _apply_allowed(config, args) is True

    wrong = type("Args", (), {"apply": True, "destination_guild_id": "200", "confirm_destination_guild_id": "201"})()
    with pytest.raises(ConfigError, match="exactly match"):
        _apply_allowed(config, wrong)


def test_replace_all_requires_its_own_confirmation(tmp_path):
    config = load_replica_config(_config(tmp_path))
    args = type("Args", (), {
        "apply": True, "destination_guild_id": "200", "confirm_destination_guild_id": "200",
        "replace_all_destination_channels": True, "confirm_replace_all": False,
    })()
    with pytest.raises(ConfigError, match="confirm-replace-all"):
        _apply_allowed(config, args)
