"""Input safety guardrails cho nội dung do người dùng nhập (bio, câu hỏi /ask).

Thuần, không phụ thuộc — chặn 2 lớp TRƯỚC khi nội dung tới model/retrieval:
  1. Nội dung tục tĩu / xúc phạm / bị cấm (khớp từ khoá có ranh giới từ).
  2. Prompt injection (câu lệnh nhằm điều khiển AI thay vì mô tả/hỏi thật).
Kèm chuẩn hoá (bỏ ký tự điều khiển, ký tự ẩn zero-width, gộp khoảng trắng).

Đây là phòng thủ lớp ngoài (regex/keyword) — kết hợp với việc prompt luôn coi
nội dung người dùng là DỮ LIỆU, không phải chỉ thị (defense-in-depth).
"""

import re
import unicodedata
from dataclasses import dataclass

MAX_BIO_LEN = 500
MAX_QUESTION_LEN = 2000

# Ký tự ẩn hay dùng để né bộ lọc (zero-width, joiner, BOM...).
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)

# --- Lớp 1: tục tĩu / xúc phạm / slur (VI + EN). Khớp theo ranh giới từ. ---
# Danh sách có chủ đích chứa từ thô để LỌC; giữ gọn, dễ mở rộng.
_PROFANITY = [
    # Tiếng Việt (tình dục / chửi tục / viết tắt toxic phổ biến)
    "địt", "đụ", "lồn", "cặc", "buồi", "đĩ", "điếm", "đéo", "vãi lồn", "vãi l",
    "đầu buồi", "óc chó", "súc vật", "đm", "đmm", "dmm", "dcm", "dkm", "vcl",
    "vkl", "clm", "cmm", "đmcm", "đcm", "cức",
    # Tiếng Anh (profanity / slur)
    "fuck", "shit", "bitch", "asshole", "cunt", "motherfucker", "bastard",
    "nigger", "faggot", "retard", "whore", "slut",
]
_PROFANITY_RE = [
    re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.IGNORECASE)
    for w in _PROFANITY
]

# --- Lớp 2: dấu hiệu prompt injection (VI + EN). ---
_INJECTION_RE = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all|the|any|previous|above|prior)?\s*(instruction|prompt|rule|direction|command)",
        r"disregard\s+(all|the|any|previous|above)?\s*(instruction|prompt|rule)",
        r"forget\s+(all|the|any|previous|above|everything)",
        r"bỏ\s*qua\s+(mọi|các|những|tất\s*cả)?\s*(chỉ\s*dẫn|hướng\s*dẫn|chỉ\s*thị|quy\s*tắc|câu\s*lệnh|lệnh)",
        r"(quên|phớt\s*lờ)\s+(đi\s+)?(mọi|các|những|tất\s*cả)?\s*(chỉ\s*dẫn|hướng\s*dẫn|chỉ\s*thị|quy\s*tắc)",
        r"(system|assistant|developer)\s+(prompt|message|instruction)",
        r"(reveal|show|print|leak|tiết\s*lộ|in\s+ra|đọc\s+ra)\s+.{0,25}(prompt|instruction|system|chỉ\s*thị)",
        r"you\s+are\s+now\b",
        r"from\s+now\s+on\s+you\b",
        r"(pretend|act)\s+(to\s+be|as\s+if|as\s+though)",
        r"(bạn\s+(bây\s*giờ|giờ)\s+là|từ\s+(giờ|nay)\s+(trở\s+đi\s+)?bạn)",
        r"đóng\s+vai\b",
        r"jailbreak|\bDAN\b|do\s+anything\s+now",
        r"</?\s*(system|instruction|prompt|assistant)\s*>",
        r"(?im)^\s*(system|assistant|developer|user)\s*:",
    ]
]


@dataclass
class Guard:
    ok: bool
    reason: str      # rỗng khi ok; ngược lại: thông điệp ngắn giải thích
    text: str        # nội dung đã chuẩn hoá (an toàn để lưu / dùng tiếp)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").translate(_ZERO_WIDTH)
    # bỏ ký tự điều khiển (trừ \n\t), gộp khoảng trắng thừa
    text = "".join(c for c in text if c == "\n" or c == "\t" or ord(c) >= 0x20)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_profanity(text: str) -> str | None:
    for rx in _PROFANITY_RE:
        if rx.search(text):
            return rx.pattern
    return None


def _find_injection(text: str) -> str | None:
    for rx in _INJECTION_RE:
        if rx.search(text):
            return rx.pattern
    return None


def _check(text: str, *, max_len: int) -> Guard:
    clean = normalize(text)
    if len(clean) > max_len:
        return Guard(False, f"Nội dung quá dài (tối đa {max_len} ký tự).", clean)
    if _find_profanity(clean):
        return Guard(False, "Nội dung chứa từ ngữ không phù hợp.", clean)
    if _find_injection(clean):
        return Guard(False, "Nội dung có dấu hiệu thao túng hệ thống (prompt injection) nên bị từ chối.", clean)
    return Guard(True, "", clean)


def check_bio(text: str) -> Guard:
    """Bio là mô tả bản thân. Rỗng được phép (xoá bio)."""
    clean = normalize(text)
    if not clean:
        return Guard(True, "", "")
    return _check(clean, max_len=MAX_BIO_LEN)


def check_question(text: str) -> Guard:
    """Câu hỏi /ask. Cần tối thiểu 2 ký tự (khớp AskRequest)."""
    clean = normalize(text)
    if len(clean) < 2:
        return Guard(False, "Câu hỏi quá ngắn.", clean)
    return _check(clean, max_len=MAX_QUESTION_LEN)
