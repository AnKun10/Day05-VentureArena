"""Companion's four Discord slash commands (luồng TA đã bỏ theo MASTERPLAN)."""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
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
    if data.get("footer"):
        embed.set_footer(text=data["footer"])
    return embed


_RETRIES = 2                 # tổng 3 lần thử
_BACKOFF = (0.5, 1.5)        # giãn cách giữa các lần retry (giây)


class ApiError(Exception):
    """Lỗi gọi API. status=None: lỗi mạng/timeout (đã retry). status 4xx: lỗi
    client (vd nội dung bị guardrail chặn) — không retry, reason là lý do."""
    def __init__(self, reason: str, status: int | None = None):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def _request_json(url: str, payload: dict | None = None, method: str | None = None,
                  timeout: int = 10) -> dict:
    """GET/PUT/POST JSON với retry cho lỗi TẠM THỜI (mạng/timeout/5xx). Lỗi 4xx
    không retry — ném ApiError kèm `detail` từ server để hiển thị cho user."""
    data = json.dumps(payload).encode("utf-8") if payload else None
    method = method or ("POST" if payload else "GET")
    last: ApiError | None = None
    for attempt in range(_RETRIES + 1):
        try:
            request = Request(url, data=data,
                              headers={"Content-Type": "application/json"}, method=method)
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = ""
            try:
                detail = json.loads(exc.read().decode("utf-8", "ignore")).get("detail", "")
            except Exception:
                pass
            if 400 <= exc.code < 500:
                raise ApiError(detail or f"HTTP {exc.code}", status=exc.code)
            last = ApiError(detail or f"HTTP {exc.code}", status=exc.code)   # 5xx → retry
        except (URLError, TimeoutError, OSError) as exc:
            last = ApiError(str(exc))                                         # mạng/timeout → retry
        if attempt < _RETRIES:
            time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)])
    raise last or ApiError("unknown error")


def _fail_message(err: Exception) -> str:
    """Thông điệp lỗi thân thiện, phân biệt guardrail (4xx) vs mạng/timeout."""
    if isinstance(err, ApiError) and err.status and 400 <= err.status < 500:
        return f"⚠️ {err.reason}"
    return "⚠️ Companion tạm thời không phản hồi (mạng hoặc quá tải). Hãy thử lại sau."


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
            if result.get("action") == "blocked":     # guardrail chặn nội dung
                await interaction.followup.send(f"⚠️ {result.get('answer')}", ephemeral=True)
                return
            citations = "\n".join(f"• {citation}" for citation in result.get("citations", []))
            await interaction.followup.send(_text(result["answer"] + (f"\n\nNguồn:\n{citations}" if citations else "")), ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(_fail_message(exc), ephemeral=True)

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
                try:
                    items = await asyncio.to_thread(_request_json, f"{api_url}/api/recommendations?user_id={user}&k=10")
                    embed = digest_embed(items, personalized=True)
                except ApiError:
                    # Hạ cấp: personalize hỏng → tin mới nhất kèm ghi chú
                    items = await asyncio.to_thread(_request_json, f"{api_url}/api/news")
                    embed = digest_embed(items[:10], personalized=False)
                    embed["footer"] = "⚠️ Chưa cá nhân hoá được — đang hiển thị tin mới nhất."
            else:
                items = await asyncio.to_thread(_request_json, f"{api_url}/api/news")
                embed = digest_embed(items[:10], personalized=False)
            await interaction.followup.send(embed=_embed_from(embed), ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(_fail_message(exc), ephemeral=True)

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
        except Exception as exc:
            await interaction.followup.send(_fail_message(exc), ephemeral=True)

    @bot.tree.command(name="bio", description="Xem hoặc cập nhật bio — Companion dùng bio để gợi ý bản tin cho bạn")
    @app_commands.describe(text="Bio mới (bỏ trống để xem bio hiện tại). Gợi ý: copy About Me trên profile Discord của bạn")
    async def bio(interaction: discord.Interaction, text: str | None = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        user = quote(interaction.user.name)
        try:
            # GET settings trước để đảm bảo user đã tồn tại trong DB (auto-create)
            await asyncio.to_thread(_request_json, f"{api_url}/api/users/{user}/settings")
            if text:
                # PUT bio: server chạy guardrail; 4xx (bị chặn) → ApiError kèm lý do
                await asyncio.to_thread(_request_json, f"{api_url}/api/users/{user}/bio",
                                        {"bio": text}, "PUT")
                await interaction.followup.send(
                    "✅ Đã lưu bio! Chạy `/digest personalize` để nhận gợi ý theo sở thích mới.",
                    ephemeral=True)
            else:
                users = await asyncio.to_thread(_request_json, f"{api_url}/api/users")
                me = next((u for u in users if u.get("user_id") == interaction.user.name), None)
                current = (me or {}).get("bio") or "_(chưa có — dùng `/bio text:...` để thêm)_"
                await interaction.followup.send(f"📝 Bio hiện tại của bạn:\n> {current}", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(_fail_message(exc), ephemeral=True)

    @bot.tree.command(name="hub", description="Mở Companion Web UI")
    async def hub(interaction: discord.Interaction):
        ui_url = os.environ.get("COMPANION_UI_URL", "http://localhost:5173")
        await interaction.response.send_message(ui_url + "?user=" + quote(interaction.user.name), ephemeral=True)

    return bot
