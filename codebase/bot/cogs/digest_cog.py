"""`/digest` — bản tin tổng hợp cộng đồng (News Digest, MASTERPLAN.md §2 mục 1).

Ưu tiên đọc post đã ingest thật trong SQLite; nếu DB rỗng (server mới dựng, chưa chạy ingestion
lần nào) thì fallback qua `data/news_seed.yaml` để lệnh vẫn demo được — khai rõ là seed, không phải
dữ liệu thật, để tránh nhầm với evidence mining (đó là việc của Bình, dùng data ingest thật).
"""

from __future__ import annotations

import yaml
import discord
from discord import app_commands
from discord.ext import commands

import config
import db
from knowledge import CATEGORIES


class DigestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="digest", description="Bản tin hôm nay từ các kênh cộng đồng của khoá")
    async def digest(self, interaction: discord.Interaction) -> None:
        rows = db.recent_posts(config.DB_PATH, limit=10)
        items = [dict(r) for r in rows] if rows else self._seed_items()

        if not items:
            await interaction.response.send_message("Chưa có bản tin nào — ingestion chưa chạy lần nào.")
            return

        grouped: dict[str, list[dict]] = {}
        for item in items:
            cat = item.get("category") or "chưa phân loại"
            grouped.setdefault(cat, []).append(item)

        blocks = []
        for cat, group_items in grouped.items():
            label = CATEGORIES.get(cat, cat)
            lines = "\n".join(
                f"- {it['title']} ({it.get('channel', '')}, {it.get('author', '')})" for it in group_items[:5]
            )
            blocks.append(f"**{label}**\n{lines}")

        source_note = "" if rows else "\n\n_(seed demo — chưa ingest dữ liệu thật)_"
        await interaction.response.send_message("\n\n".join(blocks) + source_note)

    @staticmethod
    def _seed_items() -> list[dict]:
        seed_path = config.DATA_DIR / "news_seed.yaml"
        return yaml.safe_load(seed_path.read_text(encoding="utf-8")) or []


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DigestCog(bot))