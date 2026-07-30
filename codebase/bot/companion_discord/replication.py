"""Validated configuration and dry-run planning for Discord source replication."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a replication configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class ReplicaConfig:
    destination_guild_id: str
    destination_guild_allowlist: frozenset[str]
    manifest_path: Path
    state_path: Path
    managed_categories: frozenset[str]
    managed_channels: frozenset[str]
    preserve_channels: frozenset[str]
    role_mapping: dict[str, str]
    destination_channel_mappings: dict[str, str]
    visual_fidelity: bool
    include_source_metadata_in_content: bool
    allow_native_link_previews: bool


def _snowflake(value: Any, field: str) -> str:
    if isinstance(value, str):
        value = os.path.expandvars(value)
    if not isinstance(value, (str, int)) or not str(value).isdigit():
        raise ConfigError(f"{field} must be a Discord ID")
    return str(value)


def _ids(value: Any, field: str) -> frozenset[str]:
    if not isinstance(value, list):
        raise ConfigError(f"{field} must be a list")
    return frozenset(_snowflake(item, field) for item in value)


def _role_mapping(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError("role_mapping must be a mapping of source IDs to destination IDs")
    return {_snowflake(key, "role_mapping key"): _snowflake(item, "role_mapping value") for key, item in value.items()}


def _destination_channel_mappings(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError("destination_channel_mappings must be a mapping")
    result = {}
    for name, item in value.items():
        if not isinstance(name, str) or not isinstance(item, dict):
            raise ConfigError("each destination channel mapping must be a named mapping")
        result[name] = _snowflake(item.get("destination_channel_id"), f"destination_channel_mappings.{name}.destination_channel_id")
    return result


def _bools(value: Any) -> tuple[bool, bool, bool]:
    if value is None:
        return True, False, True
    if not isinstance(value, dict) or any(not isinstance(value.get(key, default), bool) for key, default in (("visual_fidelity", True), ("include_source_metadata_in_content", False), ("allow_native_link_previews", True))):
        raise ConfigError("replay settings must be booleans")
    return value.get("visual_fidelity", True), value.get("include_source_metadata_in_content", False), value.get("allow_native_link_previews", True)


def load_replica_config(path: str | Path) -> ReplicaConfig:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read config: {exc}") from exc
    section = raw.get("discord_bot")
    if not isinstance(section, dict):
        raise ConfigError("discord_bot mapping is required")
    destination = _snowflake(section.get("destination_guild_id"), "destination_guild_id")
    allowlist = _ids(section.get("destination_guild_allowlist"), "destination_guild_allowlist")
    if destination not in allowlist:
        raise ConfigError("destination guild is not in destination allowlist")
    manifest_path = section.get("manifest_path")
    state_path = section.get("state_path")
    if not isinstance(manifest_path, str) or not isinstance(state_path, str):
        raise ConfigError("manifest_path and state_path are required")
    visual_fidelity, include_metadata, native_previews = _bools(raw.get("replay"))
    return ReplicaConfig(
        destination,
        allowlist,
        Path(manifest_path),
        Path(state_path),
        _ids(section.get("managed_categories", []), "managed_categories"),
        _ids(section.get("managed_channels", []), "managed_channels"),
        _ids(section.get("preserve_channels", []), "preserve_channels"),
        _role_mapping(section.get("role_mapping")),
        _destination_channel_mappings(section.get("destination_channel_mappings")),
        visual_fidelity,
        include_metadata,
        native_previews,
    )


def build_rebuild_plan(config: ReplicaConfig, manifest: dict, state: dict, destination: dict, *, replace_all: bool = False, remove_superseded_created_channels: bool = False) -> dict:
    """Return an inspectable plan; this function never calls Discord."""
    mappings = state.get("categories", {}), state.get("channels", {})
    managed_categories = config.managed_categories | set(state.get("created_category_ids", []))
    managed_channels = config.managed_channels | set(state.get("created_channel_ids", []))
    protected = config.preserve_channels | set(destination.get("protected_channel_ids", []))
    configured_reuse = destination.get("configured_reuse", {})
    superseded_created = {
        mappings[1][str(item.get("id"))]
        for item in manifest.get("channels", [])
        if item.get("source_name") in configured_reuse
        and mappings[1].get(str(item.get("id")))
        and mappings[1][str(item.get("id"))] != configured_reuse[item.get("source_name")]["id"]
    }
    if not remove_superseded_created_channels:
        protected |= superseded_created
    protected_categories = set(destination.get("protected_category_ids", []))
    existing_categories = {str(item["id"]) for item in destination.get("categories", [])}
    existing_channels = {str(item["id"]) for item in destination.get("channels", [])}
    for channel in destination.get("channels", []):
        if str(channel.get("id")) in protected and channel.get("category_id"):
            protected_categories.add(str(channel["category_id"]))
    category_pool = {str(item["id"]) for item in destination.get("categories", [])} if replace_all else managed_categories
    channel_pool = {str(item["id"]) for item in destination.get("channels", [])} if replace_all else managed_channels
    delete_categories = [str(item["id"]) for item in destination.get("categories", []) if str(item.get("id")) in category_pool - protected - protected_categories]
    delete_channels = [str(item["id"]) for item in destination.get("channels", []) if str(item.get("id")) in channel_pool - protected]
    existing_categories -= set(delete_categories)
    existing_channels -= set(delete_channels)
    categories = manifest.get("categories", [])
    channels = manifest.get("channels", [])
    def create_channel(item: dict) -> bool:
        return item.get("source_name") not in configured_reuse and mappings[1].get(str(item.get("id"))) not in existing_channels
    reuse_details = [
        {"source_name": item.get("source_name"), **configured_reuse[item.get("source_name")]}
        for item in channels if item.get("source_name") in configured_reuse
    ]
    migrations = [
        {
            "source_name": item.get("source_name"),
            "source_channel_id": str(item.get("id")),
            "old_destination_channel_id": mappings[1][str(item.get("id"))],
            "new_destination_channel_id": configured_reuse[item.get("source_name")]["id"],
            "reset_message_mappings": True,
        }
        for item in channels
        if item.get("source_name") in configured_reuse
        and mappings[1].get(str(item.get("id")))
        and mappings[1][str(item.get("id"))] != configured_reuse[item.get("source_name")]["id"]
    ]
    return {
        "delete_categories": delete_categories,
        "delete_channels": delete_channels,
        "delete_category_details": [item for item in destination.get("categories", []) if str(item.get("id")) in delete_categories],
        "delete_channel_details": [item for item in destination.get("channels", []) if str(item.get("id")) in delete_channels],
        "create_categories": [item.get("name", "Unnamed category") for item in categories if mappings[0].get(str(item.get("id"))) not in existing_categories],
        "create_channels": [item.get("name", "Unnamed channel") for item in channels if create_channel(item)],
        "create_category_details": [{"source_id": str(item.get("id")), "name": item.get("name", "Unnamed category")} for item in categories if mappings[0].get(str(item.get("id"))) not in existing_categories],
        "create_channel_details": [{"source_id": str(item.get("id")), "name": item.get("name", "Unnamed channel"), "type": item.get("type")} for item in channels if create_channel(item)],
        "reuse_existing_channels": reuse_details,
        "mapping_migrations": migrations,
        "retained_superseded_created_channel_ids": [] if remove_superseded_created_channels else sorted(superseded_created),
        "message_count": sum(len(item.get("messages", [])) for item in channels if item.get("type") != "forum"),
        "forum_post_count": sum(len(item.get("forum_posts", [])) for item in channels if item.get("type") == "forum"),
        "text_channel_count": sum(item.get("type") not in {"forum"} for item in channels),
        "forum_channel_count": sum(item.get("type") == "forum" for item in channels),
        "thread_count": sum(len(item.get("threads", [])) for item in channels) + sum(len(item.get("forum_posts", [])) for item in channels if item.get("type") == "forum"),
        "preserved_channel_ids": sorted(protected),
        "limitations": [
            "Discord assigns new message IDs and timestamps.",
            "Original authors cannot be impersonated.",
            "Attachment URLs may expire; files are not uploaded.",
        ],
    }
