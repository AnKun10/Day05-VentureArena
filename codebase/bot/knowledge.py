"""Load schedule.yaml / faq.yaml / ta_roster.yaml / news_seed.yaml vào bộ nhớ.

Đây là bản MOCK knowledge base phía bot — khi Nghĩa dựng xong RAG Core + Chroma thật (MASTERPLAN.md §3),
/ask sẽ gọi API backend thay vì đọc trực tiếp các file này. Giữ file rời để việc thay thế không đụng
vào cogs (chỉ đổi decision.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import yaml

# ⚠️ PLACEHOLDER — taxonomy loại tin chính thức do An thiết kế (MASTERPLAN.md §3).
# Sửa danh sách này khi taxonomy chốt; mọi nơi dùng "category" tự động theo bộ mới.
CATEGORIES = {
    "announce": "Thông báo",
    "survey": "Khảo sát / Form",
    "qa": "Hỏi đáp",
    "share": "Chia sẻ kiến thức",
    "resource": "Tài liệu",
}


@dataclass
class Session:
    code: str
    type: str
    title: str
    day_offset: int
    start: str
    end: str
    format: str
    class_: str
    host: str
    updated: str
    source_channel: str
    location: Optional[str] = None
    deadline: Optional[str] = None

    @property
    def date(self) -> date:
        return date.today() + timedelta(days=self.day_offset)


@dataclass
class FaqEntry:
    q: str
    a: str
    keywords: list[str]


class Knowledge:
    """Snapshot in-memory của schedule/faq/roster — load một lần khi bot khởi động.

    Gọi lại `Knowledge.load(...)` để refresh nếu Bình cập nhật file trong lúc bot đang chạy
    (hackathon scope: chưa cần watch file / hot-reload tự động).
    """

    def __init__(self, sessions: list[Session], faqs: dict[str, list[FaqEntry]], roster: list[dict]):
        self.sessions = sessions
        self.faqs = faqs
        self.roster = roster

    @classmethod
    def load(cls, data_dir: Path) -> "Knowledge":
        sessions_raw = yaml.safe_load((data_dir / "schedule.yaml").read_text(encoding="utf-8")) or {}
        faq_raw = yaml.safe_load((data_dir / "faq.yaml").read_text(encoding="utf-8")) or {}
        roster_raw = yaml.safe_load((data_dir / "ta_roster.yaml").read_text(encoding="utf-8")) or []

        sessions = [
            Session(
                code=s["code"],
                type=s["type"],
                title=s["title"],
                day_offset=s["day_offset"],
                start=s["start"],
                end=s["end"],
                format=s["format"],
                class_=s["class"],
                host=s["host"],
                updated=s["updated"],
                source_channel=s.get("source_channel", "#thông-báo"),
                location=s.get("location"),
                deadline=s.get("deadline"),
            )
            for s in sessions_raw.get("sessions", [])
        ]

        faqs = {
            session_type: [FaqEntry(q=e["q"], a=e["a"], keywords=e.get("keywords", [])) for e in entries]
            for session_type, entries in faq_raw.items()
        }

        return cls(sessions=sessions, faqs=faqs, roster=roster_raw)

    def find_session(self, code: str) -> Optional[Session]:
        code_norm = code.strip().upper().replace("_", "-")
        for s in self.sessions:
            if s.code.upper() == code_norm:
                return s
        return None

    def sessions_by_type(self, session_type: str) -> list[Session]:
        return [s for s in self.sessions if s.type == session_type]

    def upcoming(self, limit: int = 5) -> list[Session]:
        today = date.today()
        future = [s for s in self.sessions if s.date >= today]
        return sorted(future, key=lambda s: s.date)[:limit]

    def ta_for_class(self, class_code: str) -> Optional[dict]:
        for row in self.roster:
            if row["class"].lower() == (class_code or "").lower():
                return row
        return None