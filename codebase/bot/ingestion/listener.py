"""Ingestion Worker (MASTERPLAN.md §3) — đọc 4 nhóm kênh, lưu metadata vào SQLite.

Chạy như một Cog lắng nghe `on_message` (near-realtime) — đủ cho hackathon, không cần job định kỳ riêng.

**Cấu trúc thật trên server BTC (quan trọng, khác giả định ban đầu):** `lý-thuyết` VÀ `thực-hành-lab`
CŨNG là kênh Forum, không phải kênh chat thường — mỗi phòng lớp (`Lab-D305`, `Lec-D302`...) là 1 THREAD
riêng bên trong forum đó, y hệt cách `hỏi-đáp`/`chia-sẻ`/`bài-học` vận hành (1 post = 1 thread, nhiều
comment). Vì vậy mã lớp (`class_code`) phải soi trên TÊN THREAD, không phải tên forum cha — xem
`_store()` (`leaf_name`) và test tái hiện bug này ở `tests/test_ingestion.py`.
Ta chỉ lưu 1 row/thread (dùng thread.id làm message_id) và cập nhật reaction/comment count mỗi khi có
message mới trong thread đó.

**Chưa làm ở bản này** (khai rõ, không phải quyết định trung tâm nên để sau taxonomy chốt — MASTERPLAN.md §3):
  - Phân loại tin theo taxonomy (category) — An đang thiết kế; cột `category` để NULL, agent phân loại
    cắm vào qua `apply_category()` khi taxonomy chốt.
  - Đẩy nội dung `#thông-báo` sang Knowledge Base (Chroma) của Nghĩa — hiện chỉ lưu SQLite;
    export riêng cho backend ingest xem `export_announcements()`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

import config
import db
from ingestion.session_linker import best_session_code


class IngestionCog(commands.Cog):
    """Lắng nghe message ở 4 nhóm kênh đã cấu hình trong config.CHANNEL_GROUPS và ghi vào SQLite."""

    def __init__(self, bot: commands.Bot, db_path: Path = config.DB_PATH):
        self.bot = bot
        self.db_path = db_path

    def _channel_name(self, channel: discord.abc.GuildChannel) -> str:
        # Thread forum trả về tên qua parent; message thường lấy trực tiếp channel.name
        parent = getattr(channel, "parent", None)
        return (parent.name if parent is not None else getattr(channel, "name", "")) or ""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        channel_name = self._channel_name(message.channel)
        group = config.classify_channel(channel_name)
        if group is None:
            return  # kênh ngoài phạm vi ingest (vd kênh riêng tư, kênh giải trí)

        self._store(message, channel_name, group)

    def _store(self, message: discord.Message, channel_name: str, group: str) -> None:
        is_thread = isinstance(message.channel, discord.Thread)
        # 1 thread forum = 1 "post" logic; dùng thread id làm khoá thay vì id của từng reply
        message_id = str(message.channel.id) if is_thread else str(message.id)

        tags: list[str] = []
        if is_thread:
            applied = getattr(message.channel, "applied_tags", None) or []
            tags = [t.name for t in applied]

        reactions = sum(r.count for r in message.reactions) if not is_thread else self._thread_reaction_total(message.channel)
        comments = self._thread_message_count(message.channel) - 1 if is_thread else 0

        session_code = best_session_code(message.content) if group == "tai_nguyen" else None

        # Mã lớp: dùng chung config.class_code_for_discord_channel() với ask_cog.py (soi trên tên THREAD
        # + cohort từ category cha, không phải tên forum cha) — 2 nơi từng lặp logic này và LỆCH nhau
        # (bug thật đã bắt được), xem docstring của hàm đó.
        class_code = config.class_code_for_discord_channel(message.channel)

        db.upsert_post(
            self.db_path,
            message_id=message_id,
            channel_name=channel_name,
            channel_group=group,
            jump_link=message.jump_url,
            class_code=class_code,
            author=str(message.author.display_name),
            author_role=self._author_role(message),
            tags=tags,
            reactions=reactions,
            comments=max(comments, 0),
            content_snippet=(message.content or "")[:280],
            session_code=session_code,
            category=None,  # taxonomy chưa chốt — agent phân loại cắm sau qua apply_category()
            created_at=message.created_at.isoformat(),
        )

    @staticmethod
    def _author_role(message: discord.Message) -> str:
        roles = [r.name for r in getattr(message.author, "roles", []) if r.name != "@everyone"]
        return roles[0] if roles else "Học viên"

    @staticmethod
    def _thread_message_count(thread: "discord.Thread") -> int:
        return getattr(thread, "message_count", 1) or 1

    @staticmethod
    def _thread_reaction_total(thread: "discord.Thread") -> int:
        # discord.py không expose tổng reaction cấp thread trực tiếp; xấp xỉ bằng message_count
        # cho tới khi có nhu cầu chính xác hơn (đủ cho ranking "Hot" ở mức demo).
        return getattr(thread, "message_count", 0) or 0


def apply_category(db_path: Path, message_id: str, category: str) -> None:
    """Gắn category cho 1 post — gọi từ agent phân loại (An/Minh cắm sau khi taxonomy chốt).

    Tách riêng khỏi IngestionCog để agent phân loại (chạy batch, có thể ngoài event loop của bot)
    gọi thẳng mà không cần khởi tạo Cog.
    """
    with db.connect(db_path) as conn:
        conn.execute("UPDATE posts SET category=? WHERE message_id=?", (category, message_id))


def export_announcements(db_path: Path, out_path: Path) -> int:
    """Xuất toàn bộ post nhóm `thong_bao` ra JSON cho Nghĩa ingest vào Knowledge Base (Chroma).

    Kiến trúc trong MASTERPLAN.md §3 vẽ 1 mũi tên riêng "ING -> thông báo chính thức -> KB" —
    đây là điểm nối cụ thể cho mũi tên đó ở giai đoạn chưa có API nội bộ giữa 2 service.
    """
    rows = db.recent_posts(db_path, channel_group="thong_bao", limit=1000)
    payload = [dict(row) for row in rows]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(payload)