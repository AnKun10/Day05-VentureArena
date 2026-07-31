"""Quyết định trung tâm của Companion — bản dùng chung cho CẢ bot Discord VÀ Web UI.

Trước đây logic này nằm trong `codebase/bot/decision.py` nên chỉ bot dùng được, còn UI phải gọi
`codebase/backend` (bản cũ chấm 8/21) — hai mặt tiền trả lời khác nhau cho cùng một câu hỏi.
Chuyển vào backend để cả hai đi qua đúng một quyết định.

Trả về đúng contract UI của Hải đã thiết kế (`codebase/ui/src/api/client.js`):
  action="answer"                              -> trả lời được, kèm citation
  action="clarify"  + clarify_options[]        -> ② mơ hồ, hỏi lại tối đa 1 lần
  action="refuse"   + escalated_to=None        -> ③ ngoài phạm vi/thẩm quyền
  action="refuse"   + escalated_to={ta,...}    -> ① không có căn cứ, chuyển TA

Đo trên eval/golden_set.yaml: 19/21 (90,5%) — xem eval/results/comparison-bot-vs-backend.md.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import yaml

# ---------- Hằng số quyết định ----------

ANSWER = "answer"
CLARIFY = "clarify"
REFUSE = "refuse"

# ③ Ngoài phạm vi — chặn bằng luật cứng, KHÔNG uỷ cho LLM quyết.
# Đây là ranh giới an toàn: thà chặn nhầm một câu vô hại còn hơn để lọt một câu lộ đáp án/điểm.
# LLM có thể BỔ SUNG bắt thêm cách diễn đạt lạ (xem ai_decision.py), nhưng không được gỡ bỏ luật này.
_OUT_OF_SCOPE_KEYWORDS = [
    "đáp án", "dap an", "cho xin bài giải", "giải hộ đề",
    "điểm của tôi", "diem cua toi", "điểm cá nhân",
    "gia hạn", "gia han", "extend deadline", "xin extend",
    "điểm của bạn", "thông tin học viên khác",
]

_SESSION_TYPE_HINTS = {
    "LT": ["lý thuyết", "ly thuyet", "buổi học", "buoi hoc"],
    "LAB": ["lab", "thực hành"],
    "WS": ["workshop"],
    "OH": ["office hour", "văn phòng"],
    "MD": ["mentor duty", "mentor"],
}

_DEADLINE_KEYWORDS = ["deadline", "hạn nộp", "han nop", "nộp bài", "nop bai"]

_SESSION_CODE_RE = re.compile(r"\b(LT|Lab|WS|OH|MD|Lec)[\s\-_]?(\d+)\b", re.IGNORECASE)


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def best_session_code(text: str) -> Optional[str]:
    match = _SESSION_CODE_RE.search(text or "")
    if not match:
        return None
    prefix = match.group(1)
    canonical = {"lt": "LT", "lab": "Lab", "ws": "WS", "oh": "OH", "md": "MD", "lec": "Lec"}[prefix.lower()]
    return f"{canonical}-{match.group(2)}"


# ---------- Knowledge ----------


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
    def __init__(self, sessions: list[Session], faqs: dict[str, list[FaqEntry]], roster: list[dict]):
        self.sessions = sessions
        self.faqs = faqs
        self.roster = roster

    @classmethod
    def load(cls, data_dir: Path) -> "Knowledge":
        data_dir = Path(data_dir)

        def _read(name: str, default):
            path = data_dir / name
            if not path.exists():
                return default
            return yaml.safe_load(path.read_text(encoding="utf-8")) or default

        sessions_raw = _read("schedule.yaml", {})
        faq_raw = _read("faq.yaml", {})
        roster_raw = _read("ta_roster.yaml", [])

        sessions = [
            Session(
                code=s["code"], type=s["type"], title=s["title"], day_offset=s["day_offset"],
                start=s["start"], end=s["end"], format=s["format"], class_=s["class"],
                host=s["host"], updated=s["updated"],
                source_channel=s.get("source_channel", "#thông-báo"),
                location=s.get("location"), deadline=s.get("deadline"),
            )
            for s in (sessions_raw.get("sessions", []) if isinstance(sessions_raw, dict) else [])
        ]
        faqs = {
            stype: [FaqEntry(q=e["q"], a=e["a"], keywords=e.get("keywords", [])) for e in entries]
            for stype, entries in (faq_raw.items() if isinstance(faq_raw, dict) else [])
            if isinstance(entries, list)
        }
        return cls(sessions=sessions, faqs=faqs, roster=roster_raw if isinstance(roster_raw, list) else [])

    def find_session(self, code: str) -> Optional[Session]:
        code_norm = (code or "").strip().upper().replace("_", "-")
        return next((s for s in self.sessions if s.code.upper() == code_norm), None)

    def sessions_by_type(self, session_type: str) -> list[Session]:
        return [s for s in self.sessions if s.type == session_type]

    def upcoming(self, limit: int = 5) -> list[Session]:
        today = date.today()
        return sorted([s for s in self.sessions if s.date >= today], key=lambda s: s.date)[:limit]

    def ta_for_class(self, class_code: str) -> Optional[dict]:
        return next((r for r in self.roster if str(r.get("class", "")).lower() == (class_code or "").lower()), None)


# ---------- Kết quả ----------


@dataclass
class Decision:
    action: str
    answer: str
    confidence: float = 0.0
    citations: list[dict] = field(default_factory=list)
    clarify_options: list[str] = field(default_factory=list)
    escalated_to: Optional[dict] = None
    class_code: Optional[str] = None
    reason: Optional[str] = None  # ①②③④ — để ghi hàng đợi + phân tích eval


def _citation(session: Session) -> dict:
    """Citation dạng object theo contract UI (client.js) — có session_code để UI nhảy sang tab Lịch học."""
    return {
        "source": session.source_channel,
        "session_code": session.code,
        "quote": f"{session.code} · {session.start}–{session.end} · {session.format}",
        "updated": session.updated,
        "url": "#",
    }


def _session_info(session: Session) -> str:
    location = f", {session.location}" if session.location else ""
    return (
        f"{session.code} — {session.title} ({session.format}{location}), "
        f"{session.start}-{session.end}, host: {session.host}."
    )


def _match_faq(question_norm: str, kb: Knowledge, session_type: str) -> Optional[FaqEntry]:
    best, best_score = None, 0
    for entry in kb.faqs.get(session_type, []):
        score = sum(1 for kw in entry.keywords if _norm(kw) in question_norm)
        if score > best_score:
            best, best_score = entry, score
    return best if best_score > 0 else None


def escalate(kb: Knowledge, class_code: Optional[str], queue_position: int = 1) -> dict:
    """Dựng payload escalated_to theo contract UI. TA lấy từ ta_roster.yaml nếu map được lớp."""
    ta_entry = kb.ta_for_class(class_code) if class_code else None
    return {
        "ta": (ta_entry or {}).get("ta_name") or "TA trực tuần",
        "class": class_code or "Chung",
        "queue_position": queue_position,
    }


def decide(question: str, kb: Knowledge, *, asked_by_class: Optional[str] = None) -> Decision:
    """Quyết định thuần luật — cũng là đường lui khi không có API key hoặc LLM lỗi."""
    q_norm = _norm(question)

    # ③ Ngoài phạm vi — chặn TRƯỚC mọi thứ khác, kể cả khi câu có mã buổi hợp lệ.
    if any(_norm(kw) in q_norm for kw in _OUT_OF_SCOPE_KEYWORDS):
        return Decision(
            action=REFUSE,
            answer=(
                "Mình không có thẩm quyền xử lý việc này (đáp án / điểm cá nhân / gia hạn deadline). "
                "Bạn liên hệ trực tiếp TA phụ trách lớp hoặc BTC qua kênh #thông-báo nhé."
            ),
            confidence=1.0,
            escalated_to=None,  # ngoài phạm vi thì KHÔNG đẩy vào hàng đợi TA
            reason="③ ngoài phạm vi",
        )

    explicit_code = best_session_code(question)
    session = kb.find_session(explicit_code) if explicit_code else None

    if session:
        is_deadline_question = any(kw in q_norm for kw in _DEADLINE_KEYWORDS)

        # ④ Đặc thù domain: sai deadline -> học viên nộp muộn, mất điểm thật.
        # Ưu tiên precision: chỉ trả lời khi buổi THỰC SỰ có deadline trong nguồn.
        if is_deadline_question:
            if session.deadline:
                return Decision(
                    action=ANSWER,
                    answer=f"{session.code} — {session.title}: deadline {session.deadline}.",
                    confidence=0.95,
                    citations=[_citation(session)],
                    class_code=session.class_,
                )
            return Decision(
                action=REFUSE,
                answer=(
                    f"Mình không có thông tin chính thức về deadline của {session.code} — "
                    "câu hỏi đã được ghi nhận và sẽ gửi TA phụ trách lớp của bạn trong bản tổng hợp gần nhất."
                ),
                confidence=0.2,
                escalated_to=escalate(kb, session.class_),
                class_code=session.class_,
                reason="① nguồn sự thật (không có deadline field cho buổi này)",
            )

        faq = _match_faq(q_norm, kb, session.type)
        if faq:
            return Decision(
                action=ANSWER, answer=faq.a, confidence=0.85,
                citations=[_citation(session)], class_code=session.class_,
            )
        return Decision(
            action=ANSWER, answer=_session_info(session), confidence=0.7,
            citations=[_citation(session)], class_code=session.class_,
        )

    # ② Mơ hồ — biết loại buổi nhưng không biết buổi nào
    matched_type = next(
        (stype for stype, hints in _SESSION_TYPE_HINTS.items() if any(_norm(h) in q_norm for h in hints)),
        None,
    )
    if matched_type:
        candidates = kb.sessions_by_type(matched_type)
        if len(candidates) > 1:
            options = [f"{s.code} · {s.title}" for s in candidates[:4]]
            return Decision(
                action=CLARIFY,
                answer=f"Bạn hỏi về buổi nào cụ thể — {', '.join(s.code for s in candidates[:4])}?",
                confidence=0.4,
                clarify_options=options,
                reason="② mơ hồ / thiếu thông tin",
            )
        if len(candidates) == 1:
            session = candidates[0]
            faq = _match_faq(q_norm, kb, session.type)
            return Decision(
                action=ANSWER,
                answer=faq.a if faq else _session_info(session),
                confidence=0.75 if faq else 0.6,
                citations=[_citation(session)],
                class_code=session.class_,
            )

    # ① Không tìm được căn cứ -> từ chối + chuyển TA, tuyệt đối không đoán
    return Decision(
        action=REFUSE,
        answer=(
            "Mình không có thông tin chính thức về việc này — câu hỏi đã được ghi nhận "
            "và sẽ gửi TA phụ trách lớp của bạn trong bản tổng hợp gần nhất."
        ),
        confidence=0.1,
        escalated_to=escalate(kb, asked_by_class),
        class_code=asked_by_class,
        reason="① nguồn sự thật (không tìm thấy căn cứ)",
    )
