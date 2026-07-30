"""Manual ingestion worker for only the configured course channels."""

import asyncio
import os
from pathlib import Path

import discord
from dotenv import load_dotenv
import yaml

from .ingestion import ingest_history, save_posts


BOT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BOT_ROOT.parents[1]
load_dotenv(BOT_ROOT / ".env")


def _config() -> dict:
    path = Path(os.environ.get("COMPANION_SOURCES_PATH", BOT_ROOT / "sources.yaml"))
    if not path.is_absolute():
        path = BOT_ROOT / path
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class IngestClient(discord.Client):
    async def on_ready(self):
        config = _config()
        database = Path(os.environ.get("COMPANION_DB_PATH", PROJECT_ROOT / "data" / "companion.sqlite3"))
        if not database.is_absolute():
            database = BOT_ROOT / database
        limit = int(config.get("message_limit", 100))
        for source in config.get("sources", []):
            for channel_id in source.get("channel_ids", []):
                channel = await self.fetch_channel(int(channel_id))
                targets = [channel]
                if isinstance(channel, discord.ForumChannel):
                    targets = list(channel.threads)
                    async for thread in channel.archived_threads(limit=limit):
                        targets.append(thread)
                for target in targets:
                    save_posts(database, await ingest_history(target, source["group"], limit))
        await self.close()


def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_TOKEN in codebase/bot/.env first.")
    client = IngestClient(intents=discord.Intents.none())
    client.run(token)


if __name__ == "__main__":
    main()
