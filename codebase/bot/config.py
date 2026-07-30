"""Cấu hình bot — đọc từ biến môi trường (.env). Không commit token thật (xem .env.example + luật an toàn
trong 02-guide.md §3.4: không commit API key/.env)."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
# CHÚ Ý: os.getenv(key, default) chỉ dùng default khi biến KHÔNG TỒN TẠI, không phải khi nó rỗng —
# .env.example để "BOT_DB_PATH=" trống nghĩa là biến tồn tại với giá trị "" (bug thật đã bắt được khi
# chạy thử: Path("") -> thư mục hiện tại -> sqlite mở file lỗi). Dùng `or` để coi rỗng như chưa set.
DB_PATH = Path(os.getenv("BOT_DB_PATH") or (BASE_DIR / "bot.sqlite3"))

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID") or "0") or None  # set để sync slash command tức thời (test server)

# URL Web UI (Hải) — /hub gửi link này
WEB_UI_URL = os.getenv("WEB_UI_URL", "http://localhost:5173")

# Backend API (Nghĩa) — decision.py sẽ gọi endpoint này khi RAG Core thật sẵn sàng.
# Hiện chưa dùng (mock rule-based) — để sẵn config cho lúc swap, tránh phải sửa lan man nhiều file.
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# ---------- Mapping tên kênh Discord thật -> channel_group (MASTERPLAN.md §3) ----------
# Tên kênh thật trên server BTC giữ dấu tiếng Việt và có thể có icon/emoji trước tên
# (vd "🔔-thông-báo", "thông-báo-chung", "🙋-hỏi-đáp") — _normalize() bỏ dấu + bỏ icon trước khi so khớp.
#
# CỐ Ý dùng khớp CHÍNH XÁC (không phải substring): "thông-báo" là cụm rất phổ biến — kênh riêng của
# từng nhóm cũng thường đặt tên kiểu "thông-báo-nhóm" (vd server thật có kênh "G-17 > thông-báo-nhóm").
# Substring sẽ vô tình ingest cả kênh nội bộ nhóm khác vào KB chung — chỉ liệt kê đúng tên kênh chính thức
# quan sát được; thấy kênh chính thức nào chưa có trong danh sách thì thêm exact name vào đây.
CHANNEL_EXACT_NAMES: dict[str, list[str]] = {
    "chat_lop": ["ly-thuyet", "thuc-hanh-lab"],  # + mọi kênh "Lab-*"/"Lec-*" khớp qua prefix, xem _class_room_prefix()
    "forum": ["hoi-dap", "bai-hoc", "chia-se"],
    "tai_nguyen": ["tai-nguyen"],
    "thong_bao": ["thong-bao", "thong-bao-chung"],
}

_ROOM_PREFIXES = ("lab-", "lec-")  # phòng lớp cụ thể, nằm trong category "lý thuyết"/"thực hành lab"


def _normalize(name: str) -> str:
    """Bỏ dấu tiếng Việt + icon/emoji + ký tự thừa, chỉ giữ chữ-số-gạch ngang, viết thường.

    'đ'/'Đ' không tự bỏ dấu được qua NFD (không phải ký tự có dấu kết hợp) nên xử lý tay trước.
    """
    name = name.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", name)
    no_accents = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    ascii_only = "".join(c for c in no_accents if c.isascii() and (c.isalnum() or c == "-"))
    return ascii_only.lower().strip("-")


def _class_room_prefix(name_norm: str) -> str | None:
    for prefix in _ROOM_PREFIXES:
        if name_norm.startswith(prefix):
            return prefix
    return None


def classify_channel(channel_name: str) -> str | None:
    """Trả về channel_group cho một tên kênh, hoặc None nếu kênh không thuộc phạm vi ingest.

    Phòng lớp cụ thể (`Lab-D305`, `Lec-D302`...) được coi là kênh chat lớp dù không nằm trong
    danh sách tĩnh — mỗi khoá/mỗi lớp có tên phòng khác nhau, không liệt kê hết được.
    """
    name_norm = _normalize(channel_name)
    if _class_room_prefix(name_norm):
        return "chat_lop"
    for group, names in CHANNEL_EXACT_NAMES.items():
        if name_norm in names:
            return group
    return None


def cohort_from_category(category_name: str | None) -> str | None:
    """Suy ra mã khoá ('K3', 'K4'...) từ tên category cha (vd 'LỚP HỌC - KHOÁ 3').

    Server thật dùng CHUNG số phòng giữa các khoá (vd cả Khoá 3 và Khoá 4 đều có phòng 'Lab-D305' —
    2 thread khác nhau, cùng tên) — không tách theo khoá thì escalation của 2 khoá sẽ bị gộp nhầm
    vào một mã lớp khi route cho TA qua /ta-digest.
    """
    if not category_name:
        return None
    match = re.search(r"khoa(\d+)", _normalize(category_name))
    return f"K{match.group(1)}" if match else None


def class_code_for_channel(channel_name: str, cohort: str | None = None) -> str | None:
    """Suy ra mã lớp (vd 'K3-Lab-D305') từ tên phòng lớp cụ thể + khoá (nếu xác định được);
    None cho kênh chung (vd ly-thuyet-chung).

    `cohort` nên là kết quả của `cohort_from_category()` trên category chứa forum lý-thuyết/thực-hành-lab —
    xem lý do tách khoá ở docstring của hàm đó. Không có cohort thì trả về mã lớp trần (không tiền tố).
    """
    name_norm = _normalize(channel_name)
    prefix = _class_room_prefix(name_norm)
    if not prefix:
        return None
    label = "Lab" if prefix == "lab-" else "Lec"
    room = name_norm[len(prefix):].upper()
    code = f"{label}-{room}"
    return f"{cohort}-{code}" if cohort else code