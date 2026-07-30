"""`/ta-digest` — bản tổng hợp câu hỏi tồn (escalation queue) gửi DM cho TA phụ trách đúng lớp
(MASTERPLAN.md §2 "cơ chế escalation" · §3 "TA Digest"). Đây chính là tính năng "bản tin cuối ngày
cho TA" mà đề bài gợi ý.

Quyền chạy lệnh: giới hạn cho role TA/Lab Coach/Mentor/BTC/Admin — học viên gõ lệnh này sẽ bị từ chối,
vì digest chứa câu hỏi + tên người hỏi (ranh giới ③ ngoài phạm vi/thẩm quyền áp theo hướng ngược lại:
bảo vệ dữ liệu học viên khác, không phải chỉ chặn AI trả lời sai phạm vi).
"""

from __future__ import annotations

from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands

import config
import db
from knowledge import Knowledge

_TA_ROLE_NAMES = {"ta", "lab coach", "mentor", "btc", "admin"}


def _is_ta(interaction: discord.Interaction) -> bool:
    member = interaction.user
    roles = getattr(member, "roles", [])
    return any(r.name.lower() in _TA_ROLE_NAMES for r in roles)


class TaDigestCog(commands.Cog):
    def __init__(self, bot: commands.Bot, kb: Knowledge):
        self.bot = bot
        self.kb = kb

    @app_commands.command(name="ta-digest", description="[TA] Bản tổng hợp câu hỏi tồn theo lớp phụ trách")
    async def ta_digest(self, interaction: discord.Interaction) -> None:
        if not _is_ta(interaction):
            await interaction.response.send_message(
                "Lệnh này dành cho TA/Lab Coach/Mentor phụ trách lớp — bạn không có quyền chạy.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        open_rows = db.open_escalations(config.DB_PATH)
        if not open_rows:
            await interaction.followup.send("Không có câu hỏi tồn nào — hàng đợi trống.", ephemeral=True)
            return

        by_class: dict[str, list] = defaultdict(list)
        for row in open_rows:
            by_class[row["class_code"] or "(chưa xác định lớp)"].append(row)

        sent_summaries = []
        notified_ids = []
        for class_code, rows in by_class.items():
            summary_lines = "\n".join(f"- {r['question']} _(lý do: {r['reason']})_" for r in rows)
            summary = f"**Bản tổng hợp câu hỏi tồn — {class_code}** ({len(rows)} câu)\n{summary_lines}"

            ta_entry = self.kb.ta_for_class(class_code)
            discord_id = (ta_entry or {}).get("discord_id")

            if discord_id:
                try:
                    member = await interaction.guild.fetch_member(int(discord_id))
                    await member.send(summary)
                    sent_summaries.append(f"✅ Đã gửi DM cho {ta_entry['ta_name']} ({class_code})")
                    notified_ids.extend(r["id"] for r in rows)
                except (discord.NotFound, discord.Forbidden, ValueError):
                    sent_summaries.append(f"⚠️ Không gửi được DM cho {class_code} (member/DM lỗi) — xem log dưới:\n{summary}")
            else:
                sent_summaries.append(
                    f"⚠️ Chưa gán discord_id cho TA lớp {class_code} trong ta_roster.yaml — nội dung:\n{summary}"
                )

        db.mark_notified(config.DB_PATH, notified_ids)
        await interaction.followup.send("\n\n".join(sent_summaries), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    kb = Knowledge.load(config.DATA_DIR)
    await bot.add_cog(TaDigestCog(bot, kb))