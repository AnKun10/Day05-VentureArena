"""SessionLinker tầng 1 — regex/alias. Tầng 2 (agent fallback cho case mơ hồ)
để vòng sau, theo spec §4."""
import re

_PATTERNS = [
    (re.compile(r"\bWS[\s-]?(\d+)\b", re.I), "WS"),
    (re.compile(r"\bworkshop\s*(\d+)\b", re.I), "WS"),
    (re.compile(r"\bLT[\s-]?(\d+)\b", re.I), "LT"),
    (re.compile(r"lý thuyết\s*(\d+)", re.I), "LT"),
    (re.compile(r"\bLab[\s-]?(\d+)\b", re.I), "Lab"),
    (re.compile(r"\bOH[\s-]?(\d+)\b", re.I), "OH"),
    (re.compile(r"office hour\s*(\d+)", re.I), "OH"),
]

_KIND_KEYWORDS = [
    ("record", ["record", "recording", "video"]),
    ("slide", ["slide"]),
    ("doc", ["đề bài", "hướng dẫn", "đề ", "tài liệu", "ngân hàng"]),
]


def detect_session(title: str) -> str | None:
    for pattern, prefix in _PATTERNS:
        m = pattern.search(title)
        if m:
            return f"{prefix}-{int(m.group(1))}"
    return None


def detect_kind(title: str) -> str:
    low = title.lower()
    for kind, words in _KIND_KEYWORDS:
        if any(w in low for w in words):
            return kind
    return "link"
