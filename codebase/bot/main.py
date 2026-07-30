"""Entrypoint Discord bot Companion (Minh — MASTERPLAN.md §6 "Discord Bot & Ingestion").

Chạy: `python main.py` (cần DISCORD_TOKEN trong .env — xem .env.example).
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("companion.bot")

INTENTS = discord.Intents.default()
INTENTS.message_content = True  # cần để ingestion đọc nội dung message ở kênh chat lớp/forum
INTENTS.members = True  # cần để /ta-digest fetch_member và gửi DM

bot = commands.Bot(command_prefix="!", intents=INTENTS)


@bot.event
async def on_ready() -> None:
    log.info("Đăng nhập với tên %s (id=%s)", bot.user, bot.user.id if bot.user else "?")
    guild = discord.Object(id=config.GUILD_ID) if config.GUILD_ID else None
    if guild:
        synced = await bot.tree.sync(guild=guild)
        log.info("Đã sync %d slash command vào guild test %s", len(synced), config.GUILD_ID)
    else:
        synced = await bot.tree.sync()
        log.info("Đã sync %d slash command global (có thể mất tới 1h để hiện)", len(synced))


async def _load_extensions() -> None:
    for name in ("cogs.ask_cog", "cogs.schedule_cog", "cogs.digest_cog", "cogs.hub_cog", "cogs.ta_digest_cog"):
        await bot.load_extension(name)
        log.info("Loaded %s", name)

    # IngestionCog không nhận data qua Knowledge.load() nên add trực tiếp, không qua load_extension
    from ingestion.listener import IngestionCog

    await bot.add_cog(IngestionCog(bot))
    log.info("Loaded ingestion.listener.IngestionCog")


async def main() -> None:
    db.init_db(config.DB_PATH)
    log.info("DB sẵn sàng tại %s", config.DB_PATH)

    if not config.DISCORD_TOKEN:
        raise SystemExit(
            "Thiếu DISCORD_TOKEN — copy .env.example thành .env và điền token bot (xem README.md)."
        )

    async with bot:
        await _load_extensions()
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())