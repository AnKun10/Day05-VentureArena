import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from discord_collector.config import ConfigError, load_config
from discord_collector.parsing import parse_forum_posts, parse_text_messages
from discord_collector.storage import Checkpoint, atomic_write_json, merge_records
from discord_collector.manifest import build_manifest


FIXTURES = Path(__file__).parent / "fixtures"


def test_config_rejects_non_channel_url(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("browser: {cdp_url: http://127.0.0.1:9222}\nchannels: [{name: x, type: text, url: https://discord.com/channels/1, mode: all}]\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_config_accepts_expected_shape(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("browser: {cdp_url: http://127.0.0.1:9222}\ncollection: {scroll_pause_seconds: 1, max_empty_scrolls: 1}\noutput: {directory: output, checkpoint_file: output/checkpoint.json}\nchannels: [{name: general, type: text, url: https://discord.com/channels/123/456, mode: latest_messages, limit: 100}]\n")
    assert load_config(path).channels[0].channel_id == "456"


def test_config_accepts_all_forum_posts_without_a_post_limit(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("browser: {cdp_url: http://127.0.0.1:9222}\ncollection: {scroll_pause_seconds: 1, max_empty_scrolls: 1}\noutput: {directory: output, checkpoint_file: output/checkpoint.json}\nchannels: [{name: questions, type: forum, url: https://discord.com/channels/123/456, mode: all_posts, collect_all_replies: true}]\n")
    channel = load_config(path).channels[0]
    assert channel.mode == "all_posts" and channel.post_limit is None


def test_text_parser_handles_grouped_messages_and_attachments():
    records = parse_text_messages((FIXTURES / "messages.html").read_text(), "general", "456")
    assert [record["message_id"] for record in records] == ["1", "2"]
    assert records[1]["author_display_name"] == "Ada"
    assert records[1]["attachments"][0]["filename"] == "notes.pdf"


def test_text_parser_uses_the_message_part_of_current_discord_compound_ids():
    records = parse_text_messages('<div data-list-item-id="chat-messages-123-456"><div class="message-content">Message</div></div>', "general", "123")
    assert records[0]["message_id"] == "456"


def test_text_parser_preserves_line_breaks_lists_and_anchor_urls():
    html = '<div data-list-item-id="chat-messages-1"><div class="message-content">1. Slide <a href="https://example.test/slide">details</a><br><br><div>2. Checkpoints:</div><ol><li>CP1: https://example.test/cp1</li><li>CP2: https://example.test/cp2</li></ol></div></div>'
    content = parse_text_messages(html, "announcements", "456", "123")[0]["text_content"]
    assert "1. Slide details https://example.test/slide\n\n2. Checkpoints:" in content
    assert "CP1: https://example.test/cp1" in content
    assert "CP2: https://example.test/cp2" in content


def test_forum_parser_selects_newest_posts_by_visible_time():
    posts = parse_forum_posts((FIXTURES / "forum.html").read_text(), 2)
    assert [post["thread_id"] for post in posts] == ["999", "new"]


def test_forum_parser_returns_every_visible_post_when_limit_is_none():
    posts = parse_forum_posts((FIXTURES / "forum.html").read_text(), None)
    assert [post["thread_id"] for post in posts] == ["999", "new", "middle", "old"]


def test_forum_parser_uses_the_visible_card_label_as_a_title_fallback():
    html = '<div data-list-item-id="forum-channel-list-456___789" aria-label="Bài đăng Useful title, 6 tin nhắn"></div>'
    assert parse_forum_posts(html, None)[0]["title"] == "Useful title"


def test_forum_parser_recognizes_current_discord_forum_list_items():
    posts = parse_forum_posts((FIXTURES / "forum.html").read_text(), 1)
    assert posts[0]["thread_id"] == "999"


def test_forum_post_without_an_href_uses_only_the_configured_guild_and_thread_id():
    from discord_collector.collector import _post_url
    assert _post_url(SimpleNamespace(guild_id="123", channel_id="456"), {"thread_id": "789", "url": ""}) == "https://discord.com/channels/123/456/789"


def test_forum_collection_excludes_the_parent_forum_channel_from_post_candidates():
    from discord_collector.collector import _usable_forum_posts
    channel = SimpleNamespace(channel_id="456")
    posts = [{"thread_id": "456"}, {"thread_id": "789"}]
    assert _usable_forum_posts(channel, posts) == [{"thread_id": "789"}]


def test_forum_scroll_targets_only_the_configured_forum_list():
    from discord_collector.collector import _scroll_forum

    class Driver:
        def execute_script(self, script, *args):
            self.script, self.args = script, args
            return True

    driver = Driver()
    assert _scroll_forum(driver, "456") is True
    assert driver.args == ("forum-channel-list-456",)


def test_forum_scroll_dispatches_events_for_discord_lazy_loading():
    from discord_collector.collector import _scroll_forum

    class Driver:
        def execute_script(self, script, *args):
            self.script = script
            return True

    driver = Driver()
    _scroll_forum(driver, "456")
    assert "WheelEvent" in driver.script
    assert "dispatchEvent" in driver.script


def test_message_history_scroll_uses_the_scrollable_ancestor_not_the_message_list():
    from discord_collector.collector import _scroll_up

    class Driver:
        def execute_script(self, script, *args):
            self.script, self.args = script, args
            return True

    driver = Driver()
    assert _scroll_up(driver) is True
    assert "parentElement" in driver.script
    assert "scrollBy" in driver.script
    assert driver.args == ("[data-list-id=\"chat-messages\"], ol[aria-label*=\"Messages\"]",)


def test_forum_scroll_top_dispatches_scroll_event_to_restore_virtualized_header():
    from discord_collector.collector import _scroll_forum_top

    class Driver:
        def execute_script(self, script, *args):
            self.script, self.args = script, args

    driver = Driver()
    _scroll_forum_top(driver, "456")
    assert "dispatchEvent" in driver.script
    assert driver.args == ("forum-channel-list-456",)


def test_forum_scan_requires_a_stable_second_pass_before_it_is_complete():
    from discord_collector.collector import _scan_report
    assert _scan_report([22])["converged"] is False
    assert _scan_report([22, 0]) == {"passes": 2, "new_post_counts": [22, 0], "converged": True}


def test_forum_all_posts_scans_only_the_recent_activity_catalog():
    from discord_collector import selectors
    assert selectors.FORUM_SORT_IDS == ("sort-and-view-sort-by-recent-activity",)


def test_forum_post_keeps_the_sort_that_exposed_it():
    post = {"thread_id": "789"} | {"_sort_id": "sort-and-view-sort-by-date-posted"}
    assert post["_sort_id"] == "sort-and-view-sort-by-date-posted"


def test_cli_can_refresh_only_forum_catalogs(tmp_path, monkeypatch):
    import discord_collector.__main__ as cli
    config = tmp_path / "config.yaml"
    config.write_text("browser: {cdp_url: http://127.0.0.1:9222}\ncollection: {scroll_pause_seconds: 1, max_empty_scrolls: 1}\noutput: {directory: output, checkpoint_file: output/checkpoint.json}\nchannels: [{name: questions, type: forum, url: https://discord.com/channels/123/456, mode: all_posts, collect_all_replies: true}]\n")
    captured = {}
    monkeypatch.setattr(cli, "collect", lambda config, refresh, catalog_refresh: captured.update(refresh=refresh, catalog_refresh=catalog_refresh))
    monkeypatch.setattr("sys.argv", ["collector", "collect", "--config", str(config), "--refresh-forum-catalogs", "questions"])
    assert cli.main() == 0
    assert captured == {"refresh": set(), "catalog_refresh": {"questions"}}


def test_deduplication_and_limit():
    records = [{"channel_id": "1", "message_id": "a"}, {"channel_id": "1", "message_id": "a"}, {"channel_id": "1", "message_id": "b"}]
    assert merge_records([], records, limit=1) == [records[0]]


def test_refresh_replaces_existing_message_by_id_without_creating_a_duplicate():
    existing = [{"channel_id": "1", "message_id": "a", "text_content": "flattened"}]
    refreshed = [{"channel_id": "1", "message_id": "a", "text_content": "line 1\nline 2"}]
    assert merge_records(existing, refreshed, replace_existing=True) == refreshed


def test_checkpoint_round_trip_and_atomic_write(tmp_path):
    output = tmp_path / "x.json"
    atomic_write_json(output, [{"ok": True}])
    assert json.loads(output.read_text()) == [{"ok": True}]
    checkpoint = Checkpoint(tmp_path / "checkpoint.json")
    checkpoint.add("1", "m1").add("1", "m1").complete("general").save()
    loaded = Checkpoint.load(tmp_path / "checkpoint.json")
    assert loaded.has("1", "m1") and "general" in loaded.completed
    assert loaded.data["collected_message_ids"]["1"] == ["m1"]
    assert "general" not in loaded.reopen("general").completed


def test_stop_condition_detects_no_growth():
    from discord_collector.collector import should_stop
    assert should_stop(empty_scrolls=10, max_empty_scrolls=10, reached_limit=False)
    assert should_stop(empty_scrolls=0, max_empty_scrolls=10, reached_limit=True)


def test_browser_output_merges_into_a_rebuild_manifest_without_touching_source_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "config.yaml"
    path.write_text(
        "browser: {cdp_url: http://127.0.0.1:9222}\n"
        "collection: {scroll_pause_seconds: 1, max_empty_scrolls: 1}\n"
        "output: {directory: output, checkpoint_file: output/checkpoint.json, manifest_file: output/manifest.json}\n"
        "channels: [{name: general, type: text, url: https://discord.com/channels/123/456, mode: all}]\n"
        "sources: {cohort_4_common_announcements: {type: text_channel, url: https://discord.com/channels/123/789}}\n",
        encoding="utf-8",
    )
    config = load_config(path)
    atomic_write_json(tmp_path / "output" / "general.json", [{"message_id": "2", "channel_id": "456", "text_content": "later", "timestamp": "2026-07-30T11:00:00Z"}])
    atomic_write_json(tmp_path / "output" / "cohort_4_common_announcements.json", [{"message_id": "1", "channel_id": "789", "text_content": "https://example.test", "timestamp": "2026-07-30T10:00:00Z", "attachments": [{"filename": "a.pdf", "url": "https://cdn.discordapp.com/a.pdf"}]}])

    manifest = build_manifest(config)

    assert manifest["source_guild"]["id"] == "123"
    assert [channel["id"] for channel in manifest["channels"]] == ["456", "789"]
    announcement = manifest["channels"][1]["messages"][0]
    assert announcement["content_urls"] == ["https://example.test"]
    assert announcement["attachments"][0]["url"] == "https://cdn.discordapp.com/a.pdf"
    assert announcement["author"]["roles"] is None
    assert announcement["embeds"] is None
    assert announcement["reactions"] is None
    assert manifest["channels"][1]["url"] == "https://discord.com/channels/123/789"


def test_browser_manifest_exposes_forum_starter_and_comments_in_the_api_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "config.yaml"
    path.write_text(
        "browser: {cdp_url: http://127.0.0.1:9222}\n"
        "collection: {scroll_pause_seconds: 1, max_empty_scrolls: 1}\n"
        "output: {directory: output, checkpoint_file: output/checkpoint.json, manifest_file: output/manifest.json}\n"
        "channels: [{name: lessons, type: forum, url: https://discord.com/channels/123/456, mode: latest_posts, post_limit: 1, collect_all_replies: true}]\n",
        encoding="utf-8",
    )
    config = load_config(path)
    atomic_write_json(tmp_path / "output" / "lessons" / "789.json", [
        {"message_id": "2", "channel_id": "789", "post_thread_id": "789", "post_title": "A lesson", "text_content": "Comment", "timestamp": "2026-07-31T10:01:00Z"},
        {"message_id": "1", "channel_id": "789", "post_thread_id": "789", "post_title": "A lesson", "text_content": "Starter", "timestamp": "2026-07-31T10:00:00Z"},
    ])
    atomic_write_json(tmp_path / "output" / "lessons" / "posts.json", [{"thread_id": "999", "title": "Empty post", "url": "https://discord.com/channels/123/456/999"}])

    forum_posts = build_manifest(config)["channels"][0]["forum_posts"]
    post = next(item for item in forum_posts if item["id"] == "789")
    empty = next(item for item in forum_posts if item["id"] == "999")

    assert build_manifest(config)["channels"][0]["available_tags"] is None
    assert post["url"] == "https://discord.com/channels/123/456/789"
    assert post["applied_tags"] is None
    assert post["starter_message"]["content"] == "Starter"
    assert post["comments"][0]["content"] == "Comment"
    assert [message["id"] for message in post["messages"]] == ["1", "2"]
    assert empty["title"] == "Empty post" and empty["starter_message"] is None and empty["comments"] == []
    assert empty["catalog_status"] == "visible_in_latest_forum_catalog"
    assert post["catalog_status"] == "retained_from_prior_crawl"
