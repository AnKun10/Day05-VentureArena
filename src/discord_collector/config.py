from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

import yaml

CHANNEL_URL = re.compile(r"^https://discord\.com/channels/(\d+)/(\d+)$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Channel:
    name: str
    type: str
    url: str
    mode: str
    limit: int | None = None
    post_limit: int | None = None
    collect_all_replies: bool = False

    @property
    def channel_id(self):
        return CHANNEL_URL.match(self.url).group(2)  # validated by load_config

    @property
    def guild_id(self):
        return CHANNEL_URL.match(self.url).group(1)  # validated by load_config


@dataclass(frozen=True)
class Config:
    cdp_url: str
    channels: list[Channel]
    scroll_pause_seconds: float
    max_empty_scrolls: int
    output_directory: Path
    checkpoint_file: Path
    manifest_file: Path


def _positive(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{field} must be a positive number")
    return value


def load_config(path: str | Path) -> Config:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read config: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config must be a mapping")
    browser, collection, output = (raw.get(key) for key in ("browser", "collection", "output"))
    if not all(isinstance(part, dict) for part in (browser, collection, output)):
        raise ConfigError("browser, collection, and output mappings are required")
    cdp_url = browser.get("cdp_url")
    parsed = urlparse(cdp_url) if isinstance(cdp_url, str) else None
    if not parsed or parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
        raise ConfigError("browser.cdp_url must be a local http URL with a port")
    configured_channels = raw.get("channels")
    if not isinstance(configured_channels, list) or not configured_channels:
        raise ConfigError("channels must be a non-empty list")
    items = list(configured_channels)
    sources = raw.get("sources", {})
    if not isinstance(sources, dict):
        raise ConfigError("sources must be a mapping when provided")
    for name, item in sources.items():
        if not isinstance(item, dict) or item.get("type") != "text_channel":
            raise ConfigError(f"sources.{name} must be a text_channel mapping")
        url = item.get("url")
        if isinstance(url, str) and url.startswith("PASTE_"):
            continue  # Explicit placeholder: do not discover or substitute another channel.
        items.append({"name": name, "type": "text", "url": url, "mode": "all"})
    channels = []
    names = set()
    for item in items:
        if not isinstance(item, dict): raise ConfigError("each channel must be a mapping")
        name, kind, url, mode = (item.get(key) for key in ("name", "type", "url", "mode"))
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name) or name in names:
            raise ConfigError("channel names must be unique and filesystem-safe")
        if kind not in {"text", "forum"} or not isinstance(url, str) or not CHANNEL_URL.fullmatch(url):
            raise ConfigError(f"{name}: type or Discord channel URL is invalid")
        if (kind == "text" and mode not in {"all", "latest_messages"}) or (kind == "forum" and mode not in {"latest_posts", "all_posts"}):
            raise ConfigError(f"{name}: mode is incompatible with channel type")
        limit = item.get("limit")
        post_limit = item.get("post_limit")
        if mode == "latest_messages": _positive(limit, f"{name}.limit")
        if mode == "latest_posts": _positive(post_limit, f"{name}.post_limit")
        if mode == "all_posts" and post_limit is not None:
            raise ConfigError(f"{name}: all_posts must not set post_limit")
        if kind == "forum" and item.get("collect_all_replies") is not True:
            raise ConfigError(f"{name}: forum channels require collect_all_replies: true")
        names.add(name)
        channels.append(Channel(name, kind, url, mode, int(limit) if limit else None, int(post_limit) if post_limit else None, bool(item.get("collect_all_replies"))))
    directory = Path(output.get("directory", ""))
    checkpoint = Path(output.get("checkpoint_file", ""))
    if not str(directory) or not str(checkpoint): raise ConfigError("output.directory and output.checkpoint_file are required")
    manifest = Path(output.get("manifest_file", directory / "manifest.json"))
    return Config(cdp_url, channels, float(_positive(collection.get("scroll_pause_seconds"), "collection.scroll_pause_seconds")), int(_positive(collection.get("max_empty_scrolls"), "collection.max_empty_scrolls")), directory, checkpoint, manifest)
