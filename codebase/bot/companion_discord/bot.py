"""Companion's four Discord slash commands (luồng TA đã bỏ theo MASTERPLAN)."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from .formatting import digest_embed, schedule_embed


BOT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BOT_ROOT / ".env")

_VN_DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


def _date_label(iso_date: str) -> str:
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d")
        return f"{_VN_DAYS[d.weekday()]} · {d.strftime('%d/%m/%Y')}"
    except ValueError:
        return iso_date


def _embed_from(data: dict) -> discord.Embed:
    embed = discord.Embed(title=data["title"], color=data["color"],
                          description=data.get("description"))
    for field in data.get("fields", []):
        embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
    return embed


def _request_json(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload else None
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST" if payload else "GET")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _text(value: str) -> str:
    return value[:1_900] + ("…" if len(value) > 1_900 else "")


class CompanionBot(commands.Bot):
    async def setup_hook(self):
        guild_id = os.environ.get("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


def create_bot() -> commands.Bot:
    bot = CompanionBot(command_prefix="/", intents=discord.Intents.none())
    api_url = os.environ["COMPANION_API_URL"].rstrip("/")

    @bot.tree.command(name="ask", description="Hỏi về lịch, tài liệu, hoặc logistics của khoá")
    @app_commands.describe(question="Câu hỏi của bạn")
    async def ask(interaction: discord.Interaction, question: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            result = await asyncio.to_thread(_request_json, f"{api_url}/api/ask", {"question": question})
            citations = "\n".join(f"• {citation}" for citation in result.get("citations", []))
            await interaction.followup.send(_text(result["answer"] + (f"\n\nNguồn:\n{citations}" if citations else "")), ephemeral=True)
        except Exception:
            await interaction.followup.send("Chưa kết nối được Companion. Hãy thử lại sau.", ephemeral=True)

    @bot.tree.command(name="digest", description="Xem bản tin: mới nhất hoặc gợi ý riêng cho bạn")
    @app_commands.describe(option="latest (mới nhất) hoặc personalize (gợi ý riêng)")
    @app_commands.choices(option=[
        app_commands.Choice(name="latest", value="latest"),
        app_commands.Choice(name="personalize", value="personalize"),
    ])
    async def digest(interaction: discord.Interaction, option: app_commands.Choice[str] | None = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        choice = option.value if option else "latest"
        user = quote(interaction.user.name)
        try:
            if choice == "personalize":
                items = await asyncio.to_thread(_request_json, f"{api_url}/api/recommendations?user_id={user}&k=10")
                embed = digest_embed(items, personalized=True)
            else:
                items = await asyncio.to_thread(_request_json, f"{api_url}/api/news")
                embed = digest_embed(items[:10], personalized=False)
            await interaction.followup.send(embed=_embed_from(embed), ephemeral=True)
        except Exception:
            await interaction.followup.send("Chưa kết nối được Companion. Hãy thử lại sau.", ephemeral=True)

    @bot.tree.command(name="schedule", description="Xem lịch học trong ngày")
    @app_commands.describe(date="Ngày xem lịch, dạng YYYY-MM-DD (mặc định hôm nay)")
    async def schedule(interaction: discord.Interaction, date: str | None = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        user = quote(interaction.user.name)
        d = date or datetime.now().strftime("%Y-%m-%d")
        try:
            items = await asyncio.to_thread(_request_json, f"{api_url}/api/schedule?user_id={user}&from={d}&to={d}")
            settings = await asyncio.to_thread(_request_json, f"{api_url}/api/users/{user}/settings")
            embed = schedule_embed(items, _date_label(d), settings["cohort"])
            await interaction.followup.send(embed=_embed_from(embed), ephemeral=True)
        except Exception:
            await interaction.followup.send("Chưa kết nối được Companion. Hãy thử lại sau.", ephemeral=True)

    @bot.tree.command(name="hub", description="Mở Companion Web UI")
    async def hub(interaction: discord.Interaction):
        ui_url = os.environ.get("COMPANION_UI_URL", "http://localhost:5173")
        await interaction.response.send_message(ui_url + "?user=" + quote(interaction.user.name), ephemeral=True)

    return bot
