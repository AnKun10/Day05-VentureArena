"""Companion's five Discord slash commands."""

import asyncio
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import yaml

from .digest import unanswered_for_classes
from .ingestion import latest_posts


BOT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BOT_ROOT.parents[1]
load_dotenv(BOT_ROOT / ".env")


def _path(name: str, default: Path) -> Path:
    path = Path(os.environ.get(name, default))
    return path if path.is_absolute() else BOT_ROOT / path


def _request_json(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload else None
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST" if payload else "GET")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _text(value: str) -> str:
    return value[:1_900] + ("…" if len(value) > 1_900 else "")


def _roster(path: Path, user_id: int) -> list[str]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return []
    return next((entry.get("classes", []) for entry in data.get("tas", []) if str(entry.get("user_id")) == str(user_id)), [])


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
    database = _path("COMPANION_DB_PATH", PROJECT_ROOT / "data" / "companion.sqlite3")

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

    @bot.tree.command(name="digest", description="Xem các tin mới đã ingest")
    async def digest(interaction: discord.Interaction):
        posts = latest_posts(database, "announcements", 5) + latest_posts(database, "resources", 5)
        if not posts:
            await interaction.response.send_message("Chưa có bản tin đã ingest.", ephemeral=True)
            return
        lines = [f"• {post['content'][:180]}\n  {post['jump_url']}" for post in posts]
        await interaction.response.send_message(_text("\n".join(lines)), ephemeral=True)

    @bot.tree.command(name="schedule", description="Mở lịch học và tài liệu trong Companion")
    async def schedule(interaction: discord.Interaction):
        await interaction.response.send_message(f"Lịch học: {os.environ['COMPANION_UI_URL']}", ephemeral=True)

    @bot.tree.command(name="hub", description="Mở Companion Web UI")
    async def hub(interaction: discord.Interaction):
        await interaction.response.send_message(os.environ["COMPANION_UI_URL"], ephemeral=True)

    @bot.tree.command(name="ta-digest", description="Nhận DM các câu hỏi tồn cho lớp bạn phụ trách")
    async def ta_digest(interaction: discord.Interaction):
        classes = _roster(_path("TA_ROSTER_PATH", PROJECT_ROOT / "codebase" / "data" / "ta_roster.yaml"), interaction.user.id)
        questions = unanswered_for_classes(database, classes)
        if not classes:
            await interaction.response.send_message("Tài khoản này chưa có lớp được gán trong ta_roster.yaml.", ephemeral=True)
            return
        text = "Không có câu hỏi tồn." if not questions else "Câu hỏi tồn:\n" + "\n".join(f"• {question}" for question in questions)
        try:
            await interaction.user.send(_text(text))
        except discord.Forbidden:
            await interaction.response.send_message("Không thể gửi DM; hãy bật nhận DM từ server này.", ephemeral=True)
            return
        await interaction.response.send_message("Đã gửi bản tổng hợp qua DM.", ephemeral=True)

    return bot
