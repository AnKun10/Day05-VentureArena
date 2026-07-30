"""Session Linker — nhận diện mã buổi (LT-x / Lab-x / WS-x / OH-x / MD-x) trong nội dung bài đăng #tài-nguyên
để gắn tài liệu vào đúng block buổi trên UI (MASTERPLAN.md §3 "Session Hub").

Xử lý 2 dạng viết trong post thật:
  - Mã chuẩn liền/có gạch ngang: "WS2", "WS-2", "Lab-10", "LT12"
  - Viết chữ đầy đủ kèm số:      "Workshop 3", "Lab 10", "Workshop2" (không dấu cách)

Case mơ hồ (ví dụ nhắc tới nhiều mã trong 1 bài, hoặc số không khớp buổi nào đã curate)
được trả về nguyên danh sách match — ingestion worker tự quyết định gắn vào buổi đầu tiên
hay để agent xử lý thêm (khai rõ trong spec, đây không phải quyết định AI trung tâm).
"""

from __future__ import annotations

import re

# Giá trị = dạng hiển thị chuẩn dùng trong schedule.yaml (Lab viết hoa chữ đầu, không phải LAB).
_PREFIX_ALIASES = {
    "LT": ["LT", "LY THUYET", "LÝ THUYẾT"],
    "Lab": ["LAB"],
    "WS": ["WS", "WORKSHOP"],
    "OH": ["OH", "OFFICE HOUR"],
    "MD": ["MD", "MENTOR DUTY"],
}

# canonical code luôn dạng PREFIX-N, N là số nguyên. Key ở đây là alias viết hoa để match ổn định.
_CANONICAL_PREFIX = {alias: canon for canon, aliases in _PREFIX_ALIASES.items() for alias in aliases}

_ALTERNATION = "|".join(sorted(_CANONICAL_PREFIX, key=len, reverse=True))
_PATTERN = re.compile(
    rf"\b({_ALTERNATION})\s*-?\s*(\d+)\b",
    flags=re.IGNORECASE,
)


def find_session_codes(text: str) -> list[str]:
    """Trả về danh sách mã buổi chuẩn hoá (vd 'WS-2') tìm thấy trong text, giữ thứ tự xuất hiện, không trùng lặp."""
    if not text:
        return []
    seen: list[str] = []
    for match in _PATTERN.finditer(text.upper()):
        alias, number = match.group(1), match.group(2)
        canon_prefix = _CANONICAL_PREFIX.get(alias.upper())
        if not canon_prefix:
            continue
        code = f"{canon_prefix}-{int(number)}"
        if code not in seen:
            seen.append(code)
    return seen


def best_session_code(text: str) -> str | None:
    """Case thường gặp nhất: 1 bài #tài-nguyên gắn đúng 1 buổi -> lấy match đầu tiên.

    Trả None nếu không tìm thấy mã nào (đẩy bài vào mục "Tài nguyên chung" theo MASTERPLAN.md §3).
    """
    codes = find_session_codes(text)
    return codes[0] if codes else None