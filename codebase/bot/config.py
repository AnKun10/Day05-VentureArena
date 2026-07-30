"""Cấu hình bot — đọc từ biến môi trường (.env). Không commit token thật (xem .env.example + luật an toàn
trong 02-guide.md §3.4: không commit API key/.env)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.getenv("BOT_DB_PATH", BASE_DIR / "bot.sqlite3"))

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0")) or None  # set để sync slash command tức thời (test server)

# URL Web UI (Hải) — /hub gửi link này
WEB_UI_URL = os.getenv("WEB_UI_URL", "http://localhost:5173")

# Backend API (Nghĩa) — decision.py sẽ gọi endpoint này khi RAG Core thật sẵn sàng.
# Hiện chưa dùng (mock rule-based) — để sẵn config cho lúc swap, tránh phải sửa lan man nhiều file.
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# ---------- Mapping tên kênh Discord thật -> channel_group (MASTERPLAN.md §3) ----------
# Sửa theo đúng tên kênh của server thật/server test khi dựng xong (xem MASTERPLAN.md §9 rủi ro #1).
CHANNEL_GROUPS: dict[str, list[str]] = {
    "chat_lop": ["ly-thuyet", "ly-thuyet-chung"],  # + mọi kênh "Lab-*" khớp qua prefix, xem is_lab_channel()
    "forum": ["hoi-dap", "bai-hoc", "chia-se"],
    "tai_nguyen": ["tai-nguyen"],
    "thong_bao": ["thong-bao"],
}


def is_lab_channel(channel_name: str) -> bool:
    return channel_name.lower().startswith("lab-")


def classify_channel(channel_name: str) -> str | None:
    """Trả về channel_group cho một tên kênh, hoặc None nếu kênh không thuộc phạm vi ingest.

    Kênh `lab-*` (vd `lab-d305`) được coi là kênh chat lớp dù không nằm trong danh sách tĩnh —
    vì mỗi khoá có số lớp Lab khác nhau, không liệt kê hết được.
    """
    name = channel_name.lower()
    if is_lab_channel(name):
        return "chat_lop"
    for group, names in CHANNEL_GROUPS.items():
        if name in names:
            return group
    return None


def class_code_for_channel(channel_name: str) -> str | None:
    """Suy ra mã lớp (vd 'Lab-D305') từ tên kênh chat lớp; None cho kênh không phải lớp cụ thể (vd ly-thuyet-chung)."""
    if is_lab_channel(channel_name):
        return "Lab-" + channel_name.split("-", 1)[1].upper()
    return None