"""Build the Bot API rebuild manifest from the read-only browser collector output."""

from collections import defaultdict
import re
from typing import Any

from .storage import atomic_write_json, read_records


URL = re.compile(r"https?://[^\s<>]+")


def _message(record: dict, channel_id: str, guild_id: str, *, channel_name: str | None, channel_type: str, channel_url: str, forum_channel: dict | None = None) -> dict:
    message_id = str(record["message_id"])
    attachments = [
        {
            "name": item.get("filename") or item.get("name"),
            "url": item.get("url"),
            "content_type": item.get("content_type"),
            "size": item.get("size"),
        }
        for item in record.get("attachments", [])
    ]
    content = record.get("text_content") or ""
    author = record.get("author_display_name")
    reply_id = record.get("reply_to_message_id")
    jump_url = record.get("jump_url") or f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
    if forum_channel and f"/{channel_id}/" not in jump_url:
        jump_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
    location = {
        "guild": {"id": guild_id, "name": None},
        "channel": {"id": channel_id, "name": channel_name, "type": channel_type, "url": channel_url},
        "message_url": jump_url,
    }
    if forum_channel:
        location["forum_channel"] = forum_channel
    return {
        "id": message_id,
        "channel_id": channel_id,
        "content": content,
        "content_urls": record.get("content_urls") or URL.findall(content),
        "author": {"id": str(record["author_id"]) if record.get("author_id") else None, "name": author, "display_name": author, "roles": None, "role_snapshot_status": "not_collected_by_selenium"},
        "created_at": record.get("timestamp"),
        "edited_at": record.get("edited_at"),
        "jump_url": jump_url,
        "embeds": record.get("embeds") or None,
        "attachments": attachments,
        "reference": {"message_id": str(reply_id), "channel_id": channel_id} if reply_id else None,
        "reactions": record.get("reactions") or None,
        "pinned": None,
        "location": location,
        "data_availability": {"roles": "not_collected_by_selenium", "embeds": "not_collected_by_selenium", "reactions": "not_collected_by_selenium", "pinned": "not_collected_by_selenium"},
    }


def _ordered(records: list[dict], channel_id: str, guild_id: str, **kwargs) -> list[dict]:
    unique = {str(record.get("message_id")): record for record in records if record.get("message_id")}
    return sorted((_message(record, channel_id, guild_id, **kwargs) for record in unique.values()), key=lambda item: (item.get("created_at") or "", item["id"]))


def build_manifest(config) -> dict:
    """Merge old/new per-channel JSON files into one non-destructive manifest."""
    guild_ids = {channel.guild_id for channel in config.channels}
    if len(guild_ids) != 1:
        raise ValueError("configured browser-source URLs must belong to exactly one source guild")
    guild_id = guild_ids.pop()
    channels: list[dict[str, Any]] = []
    for channel in config.channels:
        entry = {
            "source_name": channel.name,
            "id": channel.channel_id,
            "name": channel.name,
            "display_name": None,
            "name_source": "configured_alias",
            "type": "forum" if channel.type == "forum" else "text",
            "url": channel.url,
            "category_id": None,
            "category_name": None,
            "topic": None,
            "position": None,
            "nsfw": False,
            "slowmode_delay": 0,
            "overwrites": [],
            "messages": [],
            "threads": [],
            "available_tags": None if channel.type == "forum" else [],
        }
        if channel.type == "text":
            entry["messages"] = _ordered(read_records(config.output_directory / f"{channel.name}.json"), channel.channel_id, guild_id, channel_name=None, channel_type="text", channel_url=channel.url)
        else:
            posts = defaultdict(list)
            titles = {}
            post_urls = {}
            catalog_ids = set()
            directory = config.output_directory / channel.name
            entry["forum_scan"] = read_records(directory / "scan-report.json") if (directory / "scan-report.json").exists() else None
            for post in read_records(directory / "posts.json"):
                thread_id = str(post.get("thread_id") or "")
                if thread_id:
                    catalog_ids.add(thread_id)
                    titles[thread_id] = post.get("title") or thread_id
                    post_urls[thread_id] = post.get("url")
            for path in directory.glob("*.json") if directory.exists() else []:
                if path.name in {"posts.json", "scan-report.json"}:
                    continue
                for record in read_records(path):
                    thread_id = str(record.get("post_thread_id") or path.stem)
                    posts[thread_id].append(record)
                    titles[thread_id] = record.get("post_title") or titles.get(thread_id) or thread_id
                    post_urls[thread_id] = record.get("post_url") or post_urls.get(thread_id)
            forum_location = {"id": channel.channel_id, "name": None, "type": "forum", "url": channel.url}
            entry["forum_posts"] = []
            for thread_id in sorted(set(posts) | set(titles)):
                records = posts[thread_id]
                post_url = post_urls.get(thread_id) or f"https://discord.com/channels/{guild_id}/{channel.channel_id}/{thread_id}"
                messages = _ordered(records, thread_id, guild_id, channel_name=titles[thread_id], channel_type="public_thread", channel_url=post_url, forum_channel=forum_location)
                starter = messages[0] if messages else None
                entry["forum_posts"].append({
                    "id": thread_id,
                    "catalog_status": "visible_in_latest_forum_catalog" if thread_id in catalog_ids else "retained_from_prior_crawl",
                    "parent_channel_id": channel.channel_id,
                    "name": titles[thread_id],
                    "title": titles[thread_id],
                    "url": post_url,
                    "applied_tag_names": None,
                    "applied_tags": None,
                    "author": starter["author"] if starter else None,
                    "created_at": starter["created_at"] if starter else None,
                    "edited_at": starter["edited_at"] if starter else None,
                    "content": starter["content"] if starter else None,
                    "reactions": starter["reactions"] if starter else None,
                    "starter_message": starter,
                    "comments": messages[1:],
                    "messages": messages,
                })
        channels.append(entry)
    manifest = {"schema_version": 3, "crawl_method": "selenium_browser_session", "source_guild": {"id": guild_id, "name": None}, "categories": [], "channels": channels}
    atomic_write_json(config.manifest_file, manifest)
    return manifest


def counts(manifest: dict) -> dict[str, int]:
    channels = manifest.get("channels", [])
    return {
        "categories": len(manifest.get("categories", [])),
        "channels": len(channels),
        "forum_posts": sum(len(item.get("forum_posts", [])) for item in channels),
        "threads": sum(len(item.get("threads", [])) for item in channels) + sum(len(item.get("forum_posts", [])) for item in channels),
        "messages": sum(len(item.get("messages", [])) + sum(len(post.get("messages", [])) for post in item.get("forum_posts", [])) for item in channels),
    }
