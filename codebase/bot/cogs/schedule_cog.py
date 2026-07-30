"""`/schedule` — buổi sắp tới, đọc từ knowledge.py (schedule.yaml của Bình khi có bản chính thức)."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import config
from knowledge import Knowledge


class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot, kb: Knowledge):
        self.bot = bot
        self.kb = kb

    @app_commands.command(name="schedule", description="Xem các buổi học sắp tới")
    async def schedule(self, interaction: discord.Interaction) -> None:
        upcoming = self.kb.upcoming(limit=5)
        if not upcoming:
            await interaction.response.send_message("Chưa có buổi nào sắp tới trong lịch.", ephemeral=True)
            return

        lines = [
            f"**{s.code}** · {s.title}\n"
            f"{s.date.strftime('%d/%m')} {s.start}-{s.end} · {s.format}"
            f"{(' · ' + s.location) if s.location else ''} · host: {s.host}"
            for s in upcoming
        ]
        await interaction.response.send_message("\n\n".join(lines))


async def setup(bot: commands.Bot) -> None:
    kb = Knowledge.load(config.DATA_DIR)
    await bot.add_cog(ScheduleCog(bot, kb))