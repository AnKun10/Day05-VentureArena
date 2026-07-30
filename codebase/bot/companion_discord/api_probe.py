"""Read-only Discord Bot API format probe for channels the bot can access."""

import argparse
import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
import re

import discord
from dotenv import load_dotenv


BOT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BOT_ROOT.parents[1]
URL = re.compile(r"https?://[^\s<>()]+")


def _embed_payload(embed) -> dict:
    return {
        "type": getattr(embed, "type", None),
        "title": getattr(embed, "title", None),
        "description": getattr(embed, "description", None),
        "url": getattr(embed, "url", None),
        "fields": [{"name": field.name, "value": field.value, "inline": field.inline} for field in getattr(embed, "fields", [])],
        "image_url": getattr(getattr(embed, "image", None), "url", None),
        "thumbnail_url": getattr(getattr(embed, "thumbnail", None), "url", None),
    }


def message_payload(message, *, author: dict | None = None, location: dict | None = None, reactions: list[dict] | None = None) -> dict:
    """Serialize Discord-native fields without changing plaintext formatting."""
    content = message.content or ""
    reference = getattr(message, "reference", None)
    return {
        "id": str(message.id),
        "channel_id": str(message.channel.id),
        "content": content,
        "content_urls": URL.findall(content),
        "author": author or {"id": str(message.author.id), "display_name": getattr(message.author, "display_name", str(message.author)), "roles": [], "role_snapshot_status": "not_resolved"},
        "created_at": message.created_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "jump_url": message.jump_url,
        "attachments": [{"name": item.filename, "url": item.url, "content_type": item.content_type, "size": item.size} for item in message.attachments],
        "embeds": [_embed_payload(embed) for embed in message.embeds],
        "reference": None if reference is None else {"message_id": str(reference.message_id) if reference.message_id else None, "channel_id": str(reference.channel_id) if reference.channel_id else None},
        "pinned": message.pinned,
        "reactions": reactions if reactions is not None else [{"emoji": str(item.emoji), "count": item.count, "me": item.me} for item in message.reactions],
        "location": location,
    }


def _channel_payload(channel) -> dict:
    category = getattr(channel, "category", None)
    return {
        "id": str(channel.id),
        "name": channel.name,
        "type": str(channel.type),
        "category_id": str(category.id) if category else None,
        "category_name": category.name if category else None,
        "topic": getattr(channel, "topic", None),
        "position": getattr(channel, "position", None),
        "nsfw": channel.is_nsfw() if hasattr(channel, "is_nsfw") else False,
        "slowmode_delay": getattr(channel, "slowmode_delay", 0),
    }


def _channel_url(guild_id: int, channel_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{channel_id}"


class ProbeClient(discord.Client):
    def __init__(self, *, guild_id: int, text_id: int, forum_id: int, output: Path, message_limit: int, forum_post_limit: int, reaction_user_limit: int, **kwargs):
        super().__init__(**kwargs)
        self.guild_id, self.text_id, self.forum_id = guild_id, text_id, forum_id
        self.output, self.message_limit, self.forum_post_limit, self.reaction_user_limit = output, message_limit, forum_post_limit, reaction_user_limit
        self.member_cache: dict[int, dict] = {}

    async def _author(self, guild: discord.Guild, user) -> dict:
        if user.id in self.member_cache:
            return self.member_cache[user.id]
        member = user if isinstance(user, discord.Member) else None
        if member is None:
            try:
                member = await guild.fetch_member(user.id)
            except discord.HTTPException:
                result = {"id": str(user.id), "display_name": getattr(user, "display_name", str(user)), "roles": [], "role_snapshot_status": "unavailable"}
                self.member_cache[user.id] = result
                return result
        result = {
            "id": str(member.id),
            "display_name": member.display_name,
            "roles": [{"id": str(role.id), "name": role.name} for role in member.roles if not role.is_default()],
            "role_snapshot_status": "resolved",
        }
        self.member_cache[user.id] = result
        return result

    async def _reactions(self, message) -> list[dict]:
        result = []
        for reaction in message.reactions:
            users = []
            try:
                async for user in reaction.users(limit=self.reaction_user_limit):
                    users.append({"id": str(user.id), "display_name": getattr(user, "display_name", str(user))})
            except discord.HTTPException:
                pass
            result.append({"emoji": str(reaction.emoji), "count": reaction.count, "me": reaction.me, "users": users, "users_truncated": len(users) < reaction.count})
        return result

    async def _message(self, message, *, channel: dict, forum_channel: dict | None = None) -> dict:
        location = {"guild": {"id": str(self.guild_id)}, "channel": channel, "message_url": message.jump_url}
        if forum_channel:
            location["forum_channel"] = forum_channel
        return message_payload(message, author=await self._author(message.guild, message.author), location=location, reactions=await self._reactions(message))

    async def _text(self, channel: discord.TextChannel) -> dict:
        details = {**_channel_payload(channel), "url": _channel_url(channel.guild.id, channel.id)}
        return {"channel": details, "messages": [await self._message(item, channel=details) async for item in channel.history(limit=self.message_limit, oldest_first=True)]}

    async def _forum(self, forum: discord.ForumChannel) -> dict:
        threads = {thread.id: thread for thread in forum.threads}
        async for thread in forum.archived_threads(limit=self.forum_post_limit):
            threads.setdefault(thread.id, thread)
        forum_details = {**_channel_payload(forum), "url": _channel_url(forum.guild.id, forum.id)}
        posts = []
        for thread in list(threads.values())[:self.forum_post_limit]:
            post_url = f"https://discord.com/channels/{forum.guild.id}/{forum.id}/{thread.id}"
            thread_details = {"id": str(thread.id), "name": thread.name, "type": str(thread.type), "url": post_url}
            messages = [await self._message(item, channel=thread_details, forum_channel=forum_details) async for item in thread.history(limit=self.message_limit, oldest_first=True)]
            starter = messages[0] if messages else None
            posts.append({
                "id": str(thread.id),
                "title": thread.name,
                "url": post_url,
                "parent_channel_id": str(forum.id),
                "archived": thread.archived,
                "locked": thread.locked,
                "applied_tags": [{"id": str(tag.id), "name": tag.name} for tag in getattr(thread, "applied_tags", [])],
                "author": starter["author"] if starter else None,
                "created_at": starter["created_at"] if starter else None,
                "edited_at": starter["edited_at"] if starter else None,
                "content": starter["content"] if starter else None,
                "reactions": starter["reactions"] if starter else [],
                "starter_message": starter,
                "comments": messages[1:],
            })
        result = forum_details
        result["available_tags"] = [{"id": str(tag.id), "name": tag.name, "moderated": tag.moderated, "emoji": str(tag.emoji) if tag.emoji else None} for tag in forum.available_tags]
        return {"forum": result, "posts": posts}

    async def on_ready(self):
        try:
            text = await self.fetch_channel(self.text_id)
            forum = await self.fetch_channel(self.forum_id)
            if not isinstance(text, discord.TextChannel) or not isinstance(forum, discord.ForumChannel):
                raise RuntimeError("Configured IDs must be a text channel and a forum channel.")
            if text.guild.id != self.guild_id or forum.guild.id != self.guild_id:
                raise RuntimeError("Configured channels must belong to the expected guild.")
            snapshot = {
                "schema_version": "discord_bot_api_probe.v1",
                "generated_at": datetime.now(UTC).isoformat(),
                "read_only": True,
                "guild": {"id": str(text.guild.id), "name": text.guild.name},
                "text_channel": await self._text(text),
                "forum_channel": await self._forum(forum),
                "comparison_with_selenium": {
                    "bot_api": "Discord returns plaintext, attachments, embeds, references, pins, and reactions as separate fields; content is not DOM-normalized.",
                    "selenium": "Browser collection needs DOM parsing and can lose layout if block and break elements are not preserved.",
                },
            }
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(self.output), "text_messages": len(snapshot["text_channel"]["messages"]), "forum_posts": len(snapshot["forum_channel"]["posts"]), "forum_messages": sum(len(post["comments"]) + bool(post["starter_message"]) for post in snapshot["forum_channel"]["posts"])}, ensure_ascii=False))
        finally:
            await self.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only Bot API format probe; no Discord writes.")
    parser.add_argument("--guild-id", type=int, required=True)
    parser.add_argument("--text-channel-id", type=int, required=True)
    parser.add_argument("--forum-channel-id", type=int, required=True)
    parser.add_argument("--message-limit", type=int, default=100)
    parser.add_argument("--forum-post-limit", type=int, default=25)
    parser.add_argument("--reaction-user-limit", type=int, default=100)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output" / "bot_api_probe" / "destination-format.json")
    args = parser.parse_args(argv)
    if args.message_limit < 1 or args.forum_post_limit < 1 or args.reaction_user_limit < 1:
        raise SystemExit("Limits must be positive.")
    load_dotenv(BOT_ROOT / ".env")
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_TOKEN in codebase/bot/.env first.")
    logging.getLogger("discord").setLevel(logging.WARNING)
    intents = discord.Intents.default()
    intents.message_content = True
    ProbeClient(guild_id=args.guild_id, text_id=args.text_channel_id, forum_id=args.forum_channel_id, output=args.output, message_limit=args.message_limit, forum_post_limit=args.forum_post_limit, reaction_user_limit=args.reaction_user_limit, intents=intents).run(token)


if __name__ == "__main__":
    main()
