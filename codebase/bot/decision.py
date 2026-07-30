"""Quyết định AI trung tâm của Companion (MASTERPLAN.md §2): answer-with-citation / clarify / refuse-and-escalate.

⚠️ Đây là bản MOCK rule-based cho CP2/CP3 sớm — đủ để demo đúng 4 đường trải nghiệm (happy / low-confidence /
failure / out-of-scope) và có golden set chấm được. Khi Nghĩa xong RAG Core thật (retrieval + LLM), hàm `decide()`
sẽ được thay bằng 1 lời gọi HTTP tới `/api/ask` của backend — **giữ nguyên chữ ký hàm và shape kết quả**
để cogs/ask_cog.py không phải sửa gì khi swap.

4 lớp chỗ khó (đề bài) map vào action:
  ① Nguồn sự thật   -> REFUSE_ESCALATE khi không tìm được câu trả lời có căn cứ
  ② Mơ hồ           -> CLARIFY khi hỏi đúng loại buổi nhưng thiếu mã buổi cụ thể
  ③ Ngoài phạm vi   -> REFUSE_SCOPE khi hỏi đáp án / điểm cá nhân / gia hạn deadline
  ④ Đặc thù domain  -> mọi câu có chữ "deadline" ưu tiên precision: confidence thấp thì refuse, không đoán
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from knowledge import Knowledge, Session

ANSWER = "answer"
CLARIFY = "clarify"
REFUSE_ESCALATE = "refuse_escalate"
REFUSE_SCOPE = "refuse_scope"

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


def _strip_accents(text: str) -> str:
    norm = unicodedata.normalize("NFD", text)
    return "".join(c for c in norm if unicodedata.category(c) != "Mn")


def _norm(text: str) -> str:
    return _strip_accents(text.lower())


@dataclass
class Decision:
    action: str
    message: str
    citations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    class_code: str | None = None  # dùng để route escalation vào đúng lớp cho TA digest
    reason: str | None = None  # ①/②/③/④ — dùng khi ghi escalation


def _session_citation(session: Session) -> str:
    return f"{session.source_channel} — {session.code} (cập nhật {session.updated})"


def _match_faq(question_norm: str, kb: Knowledge, session_type: str) -> tuple | None:
    """Trả (faq_entry, score) khớp nhất trong loại buổi, hoặc None nếu không case nào đủ tin cậy."""
    best = None
    best_score = 0
    for entry in kb.faqs.get(session_type, []):
        score = sum(1 for kw in entry.keywords if _norm(kw) in question_norm)
        if score > best_score:
            best, best_score = entry, score
    if best and best_score > 0:
        return best, best_score
    return None


def decide(question: str, kb: Knowledge, *, asked_by_class: str | None = None) -> Decision:
    q_norm = _norm(question)

    # ③ Ngoài phạm vi — chặn trước tiên, không để lọt vào answer/escalate
    if any(_norm(kw) in q_norm for kw in _OUT_OF_SCOPE_KEYWORDS):
        return Decision(
            action=REFUSE_SCOPE,
            message=(
                "Mình không có thẩm quyền xử lý việc này (đáp án / điểm cá nhân / gia hạn deadline). "
                "Bạn liên hệ trực tiếp TA phụ trách lớp hoặc BTC qua kênh #thông-báo nhé."
            ),
            confidence=1.0,
            reason="③ ngoài phạm vi",
        )

    # Tìm mã buổi tường minh trong câu hỏi (vd "Lab-10 deadline khi nào?")
    from ingestion.session_linker import best_session_code

    explicit_code = best_session_code(question)
    session = kb.find_session(explicit_code) if explicit_code else None

    if session:
        faq_match = _match_faq(q_norm, kb, session.type)
        is_deadline_question = any(kw in q_norm for kw in _DEADLINE_KEYWORDS)

        # ④ Đặc thù domain: câu hỏi deadline ưu tiên precision — chỉ trả lời khi buổi thật sự có deadline field
        if is_deadline_question:
            if session.deadline:
                return Decision(
                    action=ANSWER,
                    message=f"{session.code} — {session.title}: deadline {session.deadline}.",
                    citations=[_session_citation(session)],
                    confidence=0.95,
                    class_code=session.class_,
                )
            return Decision(
                action=REFUSE_ESCALATE,
                message=(
                    f"Mình không có thông tin chính thức về deadline của {session.code} — "
                    "câu hỏi đã được ghi nhận và sẽ gửi TA phụ trách lớp của bạn trong bản tổng hợp gần nhất."
                ),
                confidence=0.2,
                class_code=session.class_,
                reason="① nguồn sự thật (không có deadline field cho buổi này)",
            )

        if faq_match:
            entry, _score = faq_match
            return Decision(
                action=ANSWER,
                message=entry.a,
                citations=[_session_citation(session)],
                confidence=0.85,
                class_code=session.class_,
            )

        # Có mã buổi nhưng câu hỏi không khớp FAQ nào -> vẫn trả thông tin buổi cơ bản (an toàn, có căn cứ)
        return Decision(
            action=ANSWER,
            message=(
                f"{session.code} — {session.title} ({session.format}"
                f"{', ' + session.location if session.location else ''}), "
                f"{session.start}-{session.end}, host: {session.host}."
            ),
            citations=[_session_citation(session)],
            confidence=0.7,
            class_code=session.class_,
        )

    # Không có mã buổi tường minh — thử suy ra LOẠI buổi từ từ khoá (② mơ hồ, thiếu thông tin)
    matched_type = None
    for stype, hints in _SESSION_TYPE_HINTS.items():
        if any(_norm(h) in q_norm for h in hints):
            matched_type = stype
            break

    if matched_type:
        candidates = kb.sessions_by_type(matched_type)
        if len(candidates) > 1:
            options = ", ".join(s.code for s in candidates[:4])
            return Decision(
                action=CLARIFY,
                message=f"Bạn hỏi về buổi nào cụ thể — {options}?",
                confidence=0.4,
                reason="② mơ hồ / thiếu thông tin",
            )
        if len(candidates) == 1:
            session = candidates[0]
            faq_match = _match_faq(q_norm, kb, session.type)
            if faq_match:
                entry, _ = faq_match
                return Decision(
                    action=ANSWER,
                    message=entry.a,
                    citations=[_session_citation(session)],
                    confidence=0.75,
                    class_code=session.class_,
                )
            # Không khớp FAQ cụ thể nhưng chỉ có đúng 1 buổi loại này -> vẫn có căn cứ để trả info cơ bản
            return Decision(
                action=ANSWER,
                message=(
                    f"{session.code} — {session.title} ({session.format}"
                    f"{', ' + session.location if session.location else ''}), "
                    f"{session.start}-{session.end}, host: {session.host}."
                ),
                citations=[_session_citation(session)],
                confidence=0.6,
                class_code=session.class_,
            )

    # Không tìm được căn cứ nào -> ① nguồn sự thật: từ chối + escalate, không đoán
    return Decision(
        action=REFUSE_ESCALATE,
        message=(
            "Mình không có thông tin chính thức về việc này — câu hỏi đã được ghi nhận "
            "và sẽ gửi TA phụ trách lớp của bạn trong bản tổng hợp gần nhất."
        ),
        confidence=0.1,
        class_code=asked_by_class,
        reason="① nguồn sự thật (không tìm thấy căn cứ)",
    )