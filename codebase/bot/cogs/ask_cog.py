"""`/ask` — quyết định AI trung tâm của Companion (MASTERPLAN.md §2), chấm điểm bằng golden set.

CP2: decision.py trả lời bằng rule-based mock (KHÔNG hardcode câu trả lời cứng — vẫn có logic
answer/clarify/refuse thật, chỉ chưa gọi LLM). CP3: thay lệnh gọi `decide()` bằng HTTP call tới
`/api/ask` của Nghĩa (backend RAG Core) — giữ nguyên phần log + escalation bên dưới.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import config
import db
from decision import ANSWER, CLARIFY, REFUSE_ESCALATE, REFUSE_SCOPE, Decision, decide
from knowledge import Knowledge


class AskCog(commands.Cog):
    def __init__(self, bot: commands.Bot, kb: Knowledge):
        self.bot = bot
        self.kb = kb

    @app_commands.command(name="ask", description="Hỏi về lịch học / tài liệu / logistics của khoá")
    @app_commands.describe(question="Câu hỏi của bạn")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        class_code = config.class_code_for_discord_channel(interaction.channel)
        result: Decision = decide(question, self.kb, asked_by_class=class_code)

        asked_by = str(interaction.user)
        db.log_ask(
            config.DB_PATH,
            question=question,
            action=result.action,
            answer=result.message,
            citations=result.citations,
            confidence=result.confidence,
            asked_by=asked_by,
        )

        if result.action in (REFUSE_ESCALATE,):
            db.add_escalation(
                config.DB_PATH,
                question=question,
                reason=result.reason or "① nguồn sự thật",
                asked_by=asked_by,
                class_code=result.class_code or class_code,
            )

        await interaction.response.send_message(self._format(result), ephemeral=False)

    @staticmethod
    def _format(result: Decision) -> str:
        if result.action == ANSWER:
            cites = "\n".join(f"> 📎 {c}" for c in result.citations)
            return f"{result.message}\n{cites}" if cites else result.message
        if result.action == CLARIFY:
            return f"❓ {result.message}"
        if result.action == REFUSE_SCOPE:
            return f"🚫 {result.message}"
        # REFUSE_ESCALATE
        return f"🙏 {result.message}"


async def setup(bot: commands.Bot) -> None:
    kb = Knowledge.load(config.DATA_DIR)
    await bot.add_cog(AskCog(bot, kb))