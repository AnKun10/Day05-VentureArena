"""Safely dry-run or rebuild only Bot-managed Discord demo resources."""

import argparse
import asyncio
from copy import deepcopy
import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

import discord
from dotenv import load_dotenv

from .replication import ConfigError, ReplicaConfig, build_rebuild_plan, load_replica_config


BOT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BOT_ROOT.parents[1]
load_dotenv(BOT_ROOT / ".env")
LOGGER = logging.getLogger(__name__)
MENTIONS = discord.AllowedMentions.none()
DESTINATION_PERMISSIONS = {
    "manage_channels": "create, update, or delete managed categories and channels",
    "manage_threads": "manage forum threads and private-thread access",
    "send_messages": "replay text-channel messages",
    "send_messages_in_threads": "replay forum-post messages",
    "create_public_threads": "create public threads where needed",
    "read_message_history": "resolve already-replayed messages for replies and resume",
    "embed_links": "recreate compatible source embeds",
}


def _read_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        temporary = Path(file.name)
    temporary.replace(path)


def _manifest(path: Path, destination_guild_id: str) -> dict:
    data = _read_json(path, {})
    source_guild_id = str(data.get("source_guild", {}).get("id", ""))
    if not source_guild_id.isdigit():
        raise ConfigError("manifest must identify its source guild from configured channel URLs")
    if source_guild_id == destination_guild_id:
        raise ConfigError("manifest source guild and DESTINATION_GUILD_ID must be different")
    return data


def _select_manifest(manifest: dict, source_names: set[str], message_limit: int | None) -> dict:
    """Restrict a dry-run/apply to named source channels and their latest messages."""
    if not source_names and message_limit is None:
        return manifest
    selected = [deepcopy(channel) for channel in manifest.get("channels", []) if not source_names or channel.get("source_name") in source_names]
    missing = source_names - {channel.get("source_name") for channel in selected}
    if missing:
        raise ConfigError(f"unknown source channel name(s): {', '.join(sorted(missing))}")
    if message_limit is not None:
        if message_limit < 1:
            raise ConfigError("--message-limit must be positive")
        for channel in selected:
            channel["messages"] = channel.get("messages", [])[-message_limit:]
            for post in channel.get("forum_posts", []):
                post["messages"] = post.get("messages", [])[-message_limit:]
    result = dict(manifest)
    result["channels"] = selected
    return result


def _snapshot(guild: discord.Guild, channels: list[discord.abc.GuildChannel]) -> dict:
    protected = {
        getattr(getattr(guild, name, None), "id", None)
        for name in ("system_channel", "rules_channel", "public_updates_channel", "safety_alerts_channel")
    }
    return {
        "categories": [{"id": str(channel.id), "name": channel.name} for channel in channels if isinstance(channel, discord.CategoryChannel)],
        "channels": [{"id": str(channel.id), "name": channel.name, "type": str(channel.type), "category_id": str(channel.category_id) if channel.category_id else None} for channel in channels if not isinstance(channel, discord.CategoryChannel)],
        "protected_channel_ids": [str(channel_id) for channel_id in protected if channel_id],
    }


def _permission_report(member: discord.Member, required: dict[str, str]) -> dict:
    permissions = member.guild_permissions
    return {
        name: {"granted": bool(getattr(permissions, name)), "required_for": purpose}
        for name, purpose in required.items()
    }


def _missing(report: dict) -> list[str]:
    return [name for name, value in report.items() if value.get("required", True) and not value["granted"]]


def _chunks(value: str, limit: int = 1_900) -> list[str]:
    """Split on whitespace where possible, so URLs are not split between messages."""
    if not value:
        return ["(empty message)"]
    payload_limit = limit - 24  # Reserve room for a [Part n/n] prefix.
    result, remaining = [], value
    while len(remaining) > payload_limit:
        boundary = remaining.rfind(" ", 0, payload_limit + 1)
        if boundary <= 0:
            boundary = remaining.find(" ", payload_limit)
        if boundary <= 0:
            result.append(remaining)  # A single URL/token is reported as a failed replay rather than corrupted.
            return result
        result.append(remaining[:boundary].rstrip())
        remaining = remaining[boundary:].lstrip()
    result.append(remaining)
    count = len(result)
    return [f"[Part {index}/{count}]\n{chunk}" if count > 1 else chunk for index, chunk in enumerate(result, 1)]


def _replay_text(message: dict, config: ReplicaConfig) -> str:
    author = message.get("author", {})
    parts = []
    if config.include_source_metadata_in_content and not config.visual_fidelity:
        parts.append(f"[Original author: {author.get('display_name', 'Unknown')} | Original time: {message.get('created_at', 'unknown')}]")
    if message.get("content"):
        parts.append(message["content"])
    for item in message.get("attachments") or []:
        parts.append(f"Attachment: {item.get('filename', 'file')}\nOriginal URL: {item.get('url', '')}")
    return "\n\n".join(parts) or "(empty message)"


def _custom_embeds(message: dict) -> list[discord.Embed]:
    """Build only embeds that are not Discord's native previews of plaintext URLs."""
    plaintext_urls = set(message.get("content_urls", []))
    results = []
    for source in message.get("embeds") or []:
        if source.get("url") and source["url"] in plaintext_urls:
            continue
        try:
            result = discord.Embed(title=source.get("title") or None, description=source.get("description") or None, url=source.get("url") or None)
            for field in source.get("fields", [])[:25]:
                result.add_field(name=str(field.get("name") or "-"), value=str(field.get("value") or "-"), inline=bool(field.get("inline")))
            if source.get("image_url"):
                result.set_image(url=source["image_url"])
            if source.get("thumbnail_url"):
                result.set_thumbnail(url=source["thumbnail_url"])
            results.append(result)
        except (TypeError, ValueError):
            continue
    return results[:10]


def _state(value: dict) -> dict:
    value.setdefault("categories", value.pop("source_to_destination_category_ids", {}))
    value.setdefault("channels", value.pop("source_to_destination_channel_ids", {}))
    value.setdefault("threads", {})
    value.setdefault("messages", value.pop("source_to_destination_message_ids", {}))
    value.setdefault("created_category_ids", [])
    value.setdefault("created_channel_ids", [])
    value.setdefault("failed", [])
    return value


def _pending_messages(messages: list[dict], state: dict) -> list[dict]:
    return [message for message in messages if message["id"] not in state["messages"]]


def _overwrites(config: ReplicaConfig, guild: discord.Guild, source_guild_id: str, items: list[dict], roles: dict[str, discord.Role]) -> dict:
    result = {}
    for item in items:
        source_id = str(item["target_id"])
        if item["target_type"] == "role" and source_id == source_guild_id:
            target = guild.default_role
        elif item["target_type"] == "role" and source_id in config.role_mapping:
            target = roles.get(config.role_mapping[source_id])
        else:
            target = None
        if target:
            result[target] = discord.PermissionOverwrite.from_pair(
                discord.Permissions(item["allow"]), discord.Permissions(item["deny"])
            )
    return result


async def _retry(action, *, attempts: int = 3):
    for attempt in range(attempts):
        try:
            return await action()
        except discord.HTTPException:
            if attempt + 1 == attempts:
                raise
            await asyncio.sleep(2 ** attempt)


class RebuildClient(discord.Client):
    def __init__(self, config: ReplicaConfig, manifest: dict, state: dict, *, apply: bool, replace_all: bool, remove_superseded: bool, **kwargs):
        super().__init__(**kwargs)
        self.config, self.manifest, self.state = config, manifest, _state(state)
        self.apply, self.replace_all, self.remove_superseded = apply, replace_all, remove_superseded

    def _save(self) -> None:
        _write_json(self.config.state_path, self.state)

    def _failure(self, kind: str, source_id: str, exc: Exception) -> None:
        self.state["failed"].append({"kind": kind, "source_id": str(source_id), "error": str(exc)})
        self._save()

    async def _reuse_channels(self, destination: discord.Guild, member: discord.Member) -> dict[str, discord.TextChannel]:
        result = {}
        for source_name, destination_id in self.config.destination_channel_mappings.items():
            try:
                channel = await self.fetch_channel(int(destination_id))
            except discord.HTTPException as exc:
                raise ConfigError(f"destination mapping {source_name} does not exist: {destination_id}") from exc
            if not isinstance(channel, discord.TextChannel) or channel.guild.id != destination.id:
                raise ConfigError(f"destination mapping {source_name} must be a text/announcement channel in DESTINATION_GUILD_ID")
            if not channel.permissions_for(member).send_messages:
                raise ConfigError(f"destination mapping {source_name} is not sendable by the bot")
            result[source_name] = channel
        return result

    async def on_ready(self):
        try:
            destination = self.get_guild(int(self.config.destination_guild_id))
            if destination is None:
                raise ConfigError("bot cannot access DESTINATION_GUILD_ID through the Discord Gateway")
            destination_member = await destination.fetch_member(self.user.id)
            destination_report = _permission_report(destination_member, DESTINATION_PERMISSIONS)
            if self.config.role_mapping:
                destination_report["manage_roles"] = {
                    "granted": destination_member.guild_permissions.manage_roles,
                    "required_for": "apply configured role_mapping permission overwrites",
                }
            report = {
                "source": {"id": self.manifest["source_guild"]["id"], "name": self.manifest["source_guild"].get("name"), "access": "read by configured browser-session URLs; Bot API is not used"},
                "destination": destination_report,
            }
            print(json.dumps(report, indent=2))
            missing = [f"destination.{permission}" for permission in _missing(destination_report)]
            if missing:
                print("Stopped safely; grant the listed Discord permissions, then rerun.")
                return
            destination_channels = list(await destination.fetch_channels())
            reused = await self._reuse_channels(destination, destination_member)
            snapshot = _snapshot(destination, destination_channels)
            snapshot["configured_reuse"] = {name: {"id": str(channel.id), "name": channel.name, "type": str(channel.type)} for name, channel in reused.items()}
            plan = build_rebuild_plan(self.config, self.manifest, self.state, snapshot, replace_all=self.replace_all, remove_superseded_created_channels=self.remove_superseded)
            for item in plan["reuse_existing_channels"]:
                print(f"REUSE EXISTING CHANNEL: {item['name']} ({item['id']})")
            print(json.dumps({"mode": "apply" if self.apply else "dry-run", "source_guild": self.manifest["source_guild"], "destination_guild": {"id": self.config.destination_guild_id, "name": destination.name}, "plan": plan}, indent=2))
            if self.apply:
                await self._apply(destination, destination_channels, plan, reused)
        finally:
            await self.close()

    async def _apply(self, guild: discord.Guild, existing: list[discord.abc.GuildChannel], plan: dict, reused: dict[str, discord.TextChannel]) -> None:
        by_id = {str(channel.id): channel for channel in existing}
        for source in self.manifest.get("channels", []):
            target = reused.get(source.get("source_name"))
            if not target:
                continue
            previous = self.state["channels"].get(source["id"])
            if previous and previous != str(target.id):
                stale_messages = [message["id"] for message in source.get("messages", [])]
                self.state.setdefault("mapping_migrations", []).append({"source_name": source["source_name"], "source_channel_id": source["id"], "old_destination_channel_id": previous, "new_destination_channel_id": str(target.id), "superseded_message_ids": stale_messages})
                self.state.setdefault("superseded_message_mappings", {}).update({message_id: self.state["messages"].pop(message_id) for message_id in stale_messages if message_id in self.state["messages"]})
            self.state["channels"][source["id"]] = str(target.id)
        self._save()
        deleted = set(plan["delete_channels"]) | set(plan["delete_categories"])
        if deleted:
            self.state["categories"] = {key: value for key, value in self.state["categories"].items() if value not in deleted}
            self.state["channels"] = {key: value for key, value in self.state["channels"].items() if value not in deleted}
            self.state["threads"], self.state["messages"] = {}, {}
            self._save()
        for channel_id in plan["delete_channels"]:
            channel = by_id.get(channel_id)
            if channel:
                try:
                    await _retry(lambda channel=channel: channel.delete(reason="Companion managed demo rebuild"))
                except discord.HTTPException as exc:
                    self._failure("delete_channel", channel_id, exc)
        for category_id in plan["delete_categories"]:
            category = by_id.get(category_id)
            if category:
                try:
                    await _retry(lambda category=category: category.delete(reason="Companion managed demo rebuild"))
                except discord.HTTPException as exc:
                    self._failure("delete_category", category_id, exc)
        roles = {str(role.id): role for role in await guild.fetch_roles()}
        categories = {}
        for source in self.manifest.get("categories", []):
            mapped = by_id.get(self.state["categories"].get(source["id"], ""))
            category = mapped if isinstance(mapped, discord.CategoryChannel) else None
            if category is None:
                try:
                    category = await _retry(lambda source=source: guild.create_category(
                        source["name"], position=source.get("position", 0),
                        overwrites=_overwrites(self.config, guild, self.manifest["source_guild"]["id"], source.get("overwrites", []), roles),
                        reason="Companion managed demo rebuild",
                    ))
                except discord.HTTPException as exc:
                    self._failure("create_category", source["id"], exc)
                    continue
            categories[source["id"]] = category
            self.state["categories"][source["id"]] = str(category.id)
            if str(category.id) not in self.state["created_category_ids"]:
                self.state["created_category_ids"].append(str(category.id))
            self._save()
        for source in self.manifest.get("channels", []):
            target = reused.get(source.get("source_name"))
            mapped = by_id.get(self.state["channels"].get(source["id"], ""))
            target = target or (mapped if isinstance(mapped, (discord.TextChannel, discord.ForumChannel)) else None)
            category = categories.get(source.get("category_id"))
            options = {
                "category": category,
                "position": source.get("position", 0),
                "topic": source.get("topic") or "",
                "slowmode_delay": source.get("slowmode_delay", 0),
                "nsfw": source.get("nsfw", False),
                "overwrites": _overwrites(self.config, guild, self.manifest["source_guild"]["id"], source.get("overwrites", []), roles),
                "reason": "Companion managed demo rebuild",
            }
            if target is None:
                try:
                    if source.get("type") == "forum":
                        options["available_tags"] = [discord.ForumTag(name=item["name"], moderated=item.get("moderated", False)) for item in source.get("available_tags", [])]
                        try:
                            target = await _retry(lambda: guild.create_forum(source["name"], **options))
                        except discord.HTTPException:
                            target = await _retry(lambda: guild.create_text_channel(source["name"], **{key: value for key, value in options.items() if key != "available_tags"}))
                            self.state.setdefault("fallbacks", []).append({"source_channel_id": source["id"], "fallback": "forum_to_text"})
                    else:
                        try:
                            target = await _retry(lambda: guild.create_text_channel(source["name"], news=source.get("type") == "news", **options))
                        except discord.HTTPException:
                            if source.get("type") != "news":
                                raise
                            target = await _retry(lambda: guild.create_text_channel(source["name"], **options))
                            self.state.setdefault("fallbacks", []).append({"source_channel_id": source["id"], "fallback": "announcement_to_text"})
                except discord.HTTPException as exc:
                    self._failure("create_channel", source["id"], exc)
                    continue
            self.state["channels"][source["id"]] = str(target.id)
            if str(target.id) not in self.state["created_channel_ids"]:
                self.state["created_channel_ids"].append(str(target.id))
            self._save()
            if isinstance(target, discord.ForumChannel):
                await self._replay_forum(target, source)
            else:
                if source.get("type") == "forum":
                    await self._replay_text_threads(target, source.get("forum_posts", []))
                else:
                    await self._replay_messages(target, source.get("messages", []))
                    await self._replay_text_threads(target, source.get("threads", []))

    async def _reference(self, target: Any, source: dict):
        reference = source.get("reference") or {}
        destination_id = self.state["messages"].get(str(reference.get("message_id", "")))
        if not destination_id:
            return None
        try:
            return await target.fetch_message(int(destination_id))
        except discord.HTTPException:
            return None

    async def _replay_messages(self, target: Any, messages: list[dict]) -> None:
        for source in _pending_messages(messages, self.state):
            first = None
            reference = await self._reference(target, source)
            text = _replay_text(source, self.config)
            if source.get("reference") and reference is None:
                text = f"[Reply to original message: {source['reference'].get('message_id') or source['reference'].get('channel_id')}]\n{text}"
            try:
                for index, chunk in enumerate(_chunks(text)):
                    options = {"allowed_mentions": MENTIONS, "reference": reference if index == 0 else None}
                    if index == 0:
                        embeds = _custom_embeds(source)
                        if embeds:
                            options["embeds"] = embeds
                    if not self.config.allow_native_link_previews:
                        options["suppress_embeds"] = True
                    sent = await _retry(lambda chunk=chunk, options=options: target.send(chunk, **options))
                    first = first or sent
                self.state["messages"][source["id"]] = str(first.id)
                self._save()
            except discord.HTTPException as exc:
                self._failure("replay_message", source["id"], exc)

    async def _replay_forum(self, target: discord.ForumChannel, source: dict) -> None:
        tags = {tag.name: tag for tag in target.available_tags}
        for post in source.get("forum_posts", []):
            messages = post.get("messages", [])
            thread = None
            mapped = self.state["threads"].get(post["id"])
            if mapped:
                try:
                    thread = await self.fetch_channel(int(mapped))
                except discord.HTTPException:
                    thread = None
            if thread is None:
                first = messages[0] if messages else {"id": post["id"], "content": "(empty forum post)"}
                chunks = _chunks(_replay_text(first, self.config))
                try:
                    options = {"name": post["name"], "content": chunks[0], "applied_tags": [tags[name] for name in post.get("applied_tag_names", []) if name in tags], "allowed_mentions": MENTIONS}
                    embeds = _custom_embeds(first)
                    if embeds:
                        options["embeds"] = embeds
                    if not self.config.allow_native_link_previews:
                        options["suppress_embeds"] = True
                    created = await _retry(lambda options=options: target.create_thread(**options))
                except discord.HTTPException as exc:
                    self._failure("create_forum_post", post["id"], exc)
                    continue
                thread = created.thread
                self.state["threads"][post["id"]] = str(thread.id)
                self.state["messages"][first["id"]] = str(created.message.id)
                self._save()
                for chunk in chunks[1:]:
                    try:
                        await _retry(lambda chunk=chunk: thread.send(chunk, allowed_mentions=MENTIONS))
                    except discord.HTTPException as exc:
                        self._failure("replay_forum_post_part", post["id"], exc)
            await self._replay_messages(thread, messages)

    async def _replay_text_threads(self, target: discord.TextChannel, threads: list[dict]) -> None:
        for source in threads:
            messages = source.get("messages", [])
            if not messages:
                continue
            mapped = self.state["threads"].get(source["id"])
            thread = None
            if mapped:
                try:
                    thread = await self.fetch_channel(int(mapped))
                except discord.HTTPException:
                    thread = None
            if thread is None:
                try:
                    thread = await _retry(lambda: target.create_thread(name=source["name"], type=discord.ChannelType.public_thread, reason="Companion managed demo rebuild"))
                except discord.HTTPException as exc:
                    self._failure("create_thread", source["id"], exc)
                    continue
                self.state["threads"][source["id"]] = str(thread.id)
                self._save()
            await self._replay_messages(thread, messages)


def _apply_allowed(config: ReplicaConfig, args) -> bool:
    if getattr(args, "replace_all_destination_channels", False) and not args.apply:
        raise ConfigError("--replace-all-destination-channels requires --apply")
    if not args.apply:
        return False
    if args.destination_guild_id != config.destination_guild_id or args.confirm_destination_guild_id != config.destination_guild_id:
        raise ConfigError("--apply requires both destination IDs to exactly match DESTINATION_GUILD_ID")
    if getattr(args, "replace_all_destination_channels", False) and not getattr(args, "confirm_replace_all", False):
        raise ConfigError("--replace-all-destination-channels requires --confirm-replace-all")
    if getattr(args, "remove_superseded_created_channels", False) and not getattr(args, "confirm_remove_superseded_created_channels", False):
        raise ConfigError("--remove-superseded-created-channels requires --confirm-remove-superseded-created-channels")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run a safe Discord demo rebuild by default.")
    parser.add_argument("--config", default=PROJECT_ROOT / "config.yaml")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="default; never changes Discord")
    mode.add_argument("--apply", action="store_true", help="requires two matching destination confirmations")
    parser.add_argument("--replace-all-destination-channels", action="store_true", help="only with --apply and --confirm-replace-all")
    parser.add_argument("--confirm-replace-all", action="store_true", help="required acknowledgement for replace-all")
    parser.add_argument("--remove-superseded-created-channels", action="store_true", help="requires explicit confirmation; otherwise migrated test channels are retained")
    parser.add_argument("--confirm-remove-superseded-created-channels", action="store_true")
    parser.add_argument("--resume", action="store_true", help="explicitly document the default incremental state resume")
    parser.add_argument("--source-names", help="comma-separated source_name values to replay; defaults to every manifest channel")
    parser.add_argument("--message-limit", type=int, help="replay only the latest N messages per selected text channel")
    parser.add_argument("--destination-guild-id")
    parser.add_argument("--confirm-destination-guild-id")
    args = parser.parse_args()
    try:
        config = load_replica_config(args.config)
        apply = _apply_allowed(config, args)
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            raise ConfigError("DISCORD_TOKEN is required in codebase/bot/.env")
        manifest = _select_manifest(
            _manifest(config.manifest_path, config.destination_guild_id),
            {name.strip() for name in (args.source_names or "").split(",") if name.strip()},
            args.message_limit,
        )
        intents = discord.Intents.none()
        intents.guilds = True
        RebuildClient(config, manifest, _read_json(config.state_path, {}), apply=apply, replace_all=args.replace_all_destination_channels, remove_superseded=args.remove_superseded_created_channels, intents=intents).run(token)
    except ConfigError as exc:
        print(f"Stopped safely: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
