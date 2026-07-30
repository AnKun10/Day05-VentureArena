"""`/hub` — gửi link Web UI thống nhất (Hải), nơi hiển thị 3 tab Lịch/Tài nguyên/Bản tin."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import config


class HubCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hub", description="Mở Session Hub — lịch học, tài liệu, bản tin")
    async def hub(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"📎 Session Hub của bạn: {config.WEB_UI_URL}", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HubCog(bot))