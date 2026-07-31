"""FastAPI — một cửa duy nhất cho quyết định của Companion, dùng chung bởi Discord bot và Web UI.

Contract trả về đúng thiết kế của UI (`codebase/ui/src/api/client.js` + `codebase/ui/README.md`):

    { action, answer, confidence, citations[{source,session_code,quote,updated,url}],
      clarify_options[], escalated_to{ta,class,queue_position}|null, trace_id }

Thứ tự quyết định:
  1. Luật chặn ③ ngoài phạm vi (đáp án/điểm/gia hạn) — chặn cứng, KHÔNG hỏi LLM, không cho ghi đè.
  2. LLM quyết định phần còn lại (answerable / ambiguous / out_of_scope / no_basis) — ai_decision.py.
  3. Không có API key hoặc LLM lỗi -> lui về quyết định thuần luật của decision_core.decide().

Chạy: uvicorn app:app --port 8000   (từ thư mục codebase/backend)
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import decision_core
from ai_decision import (
    VERDICT_AMBIGUOUS,
    VERDICT_ANSWERABLE,
    VERDICT_NO_BASIS,
    VERDICT_OUT_OF_SCOPE,
    ai_verdict,
    available_providers,
)
from companion_rag import log_trace

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(Path(__file__).with_name(".env"))

# Mặc định trỏ vào data của bot — đây mới là chỗ có schedule/faq/ta_roster thật.
# (Bản trước mặc định `codebase/data` không tồn tại nên load_sources trả rỗng và mọi câu đều bị refuse.)
DATA_DIRECTORY = Path(os.environ.get("COMPANION_DATA_DIR", ROOT / "codebase" / "bot" / "data"))
TRACE_DIRECTORY = Path(os.environ.get("COMPANION_TRACE_DIR", ROOT / "eval" / "traces"))
QUEUE_PATH = Path(os.environ.get("COMPANION_QUEUE_PATH", ROOT / "data" / "companion.sqlite3"))

app = FastAPI(title="Companion API")

# UI chạy ở cổng khác (5173) nên trình duyệt coi là cross-origin — thiếu CORS thì fetch bị chặn
# và UI không bao giờ gọi được backend, dù backend chạy đúng.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "COMPANION_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)
    clarify_context: str | None = Field(default=None, max_length=2_000)
    class_name: str | None = Field(default=None, max_length=100)


class Citation(BaseModel):
    source: str
    session_code: str | None = None
    quote: str = ""
    updated: str = ""
    url: str = "#"


class AskResponse(BaseModel):
    action: str
    answer: str
    confidence: float
    citations: list[Citation] = []
    clarify_options: list[str] = []
    escalated_to: dict | None = None
    trace_id: str


class FeedbackRequest(BaseModel):
    trace_id: str | None = None
    question: str = Field(min_length=1, max_length=2_000)
    answer: str = ""
    verdict: str = "wrong"


class _TraceView:
    """log_trace() của bản cũ nhận object có .action/.answer/.citations/.confidence — giữ nguyên
    hàm đó (đang được test của Nghĩa phủ) và bọc kết quả mới cho khớp."""

    def __init__(self, result: "decision_core.Decision"):
        self.action = result.action
        self.answer = result.answer
        self.citations = [c.get("source", "") for c in result.citations]
        self.confidence = result.confidence


def _knowledge() -> decision_core.Knowledge:
    # Load mỗi request: file YAML nhỏ, và Bình còn sửa liên tục — đọc lại thì không phải restart server.
    return decision_core.Knowledge.load(DATA_DIRECTORY)


def _source_text(kb: decision_core.Knowledge) -> str:
    """Gom toàn bộ knowledge thành một khối text cho LLM soi.

    Corpus nhỏ (vài buổi + vài chục FAQ) nên đưa hết là đúng và rẻ hơn dựng vector store —
    quan trọng hơn: LLM thấy trọn nguồn thì mới phán "không có căn cứ" một cách đáng tin.
    """
    lines = []
    for s in kb.sessions:
        deadline = f" · deadline: {s.deadline}" if s.deadline else ""
        location = f" · {s.location}" if s.location else ""
        lines.append(
            f"[BUỔI {s.code}] {s.title} · {s.type} · {s.start}-{s.end} · {s.format}{location}"
            f" · lớp: {s.class_} · host: {s.host}{deadline} · cập nhật {s.updated}"
        )
    for stype, entries in kb.faqs.items():
        for e in entries:
            lines.append(f"[FAQ {stype}] Hỏi: {e.q} Đáp: {e.a}")
    return "\n".join(lines)


def _queue_refusal(question: str, class_name: str | None) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(QUEUE_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS unanswered_questions ("
            "question TEXT NOT NULL, class_name TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "INSERT INTO unanswered_questions (question, class_name) VALUES (?, ?)", (question, class_name)
        )


def _apply_ai(
    result: decision_core.Decision, question: str, kb: decision_core.Knowledge, class_name: str | None
) -> tuple[decision_core.Decision, str | None]:
    """Cho LLM quyết định. Trả (decision, provider); provider=None nghĩa là đã lui về luật."""
    verdict = ai_verdict(question, _source_text(kb))
    if verdict is None:
        return result, None

    if verdict.verdict == VERDICT_OUT_OF_SCOPE:
        return replace(
            result,
            action=decision_core.REFUSE,
            answer="Mình không có thẩm quyền xử lý việc này. Bạn liên hệ TA phụ trách lớp hoặc BTC nhé.",
            confidence=0.9, citations=[], clarify_options=[], escalated_to=None,
            reason="③ ngoài phạm vi (LLM)",
        ), verdict.provider

    if verdict.verdict == VERDICT_NO_BASIS:
        return replace(
            result,
            action=decision_core.REFUSE,
            answer=("Mình không có thông tin chính thức về việc này — câu hỏi đã được ghi nhận "
                    "và sẽ gửi TA phụ trách lớp của bạn trong bản tổng hợp gần nhất."),
            confidence=0.2, citations=[], clarify_options=[],
            escalated_to=decision_core.escalate(kb, class_name or result.class_code),
            reason="① nguồn sự thật (LLM)",
        ), verdict.provider

    if verdict.verdict == VERDICT_AMBIGUOUS:
        # Giữ clarify_options mà luật đã dựng được — LLM không biết danh sách buổi để tự liệt kê.
        return replace(
            result,
            action=decision_core.CLARIFY,
            answer=(result.answer if result.action == decision_core.CLARIFY else "Bạn hỏi về buổi nào cụ thể ạ?"),
            confidence=0.5, citations=[], escalated_to=None, reason="② mơ hồ (LLM)",
        ), verdict.provider

    if verdict.verdict == VERDICT_ANSWERABLE:
        # excerpt đã được ai_decision kiểm là substring CÓ THẬT của nguồn.
        return replace(
            result,
            action=decision_core.ANSWER, answer=verdict.excerpt,
            confidence=max(result.confidence, 0.8),
            citations=result.citations or [{
                "source": "schedule.yaml + faq.yaml", "session_code": None,
                "quote": verdict.excerpt[:120], "updated": "", "url": "#",
            }],
            clarify_options=[], escalated_to=None, reason=None,
        ), verdict.provider

    return result, verdict.provider


@app.get("/api/health")
def health() -> dict:
    """Để biết AI có đang bật thật không — dùng lúc demo, khỏi phải đoán."""
    providers = available_providers()
    return {
        "ok": True,
        "ai_enabled": bool(providers),
        "providers": providers,
        "data_dir": str(DATA_DIRECTORY),
        "sessions_loaded": len(_knowledge().sessions),
    }


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    kb = _knowledge()
    question = request.question
    if request.clarify_context:
        question = f"{request.clarify_context} — {question}"

    result = decision_core.decide(question, kb, asked_by_class=request.class_name)

    # ③ đã bị luật chặn -> chốt luôn, không hỏi LLM. Ranh giới an toàn không uỷ quyền cho model.
    provider = None
    if result.reason != "③ ngoài phạm vi":
        result, provider = _apply_ai(result, question, kb, request.class_name)

    if result.action == decision_core.REFUSE and result.escalated_to is not None:
        _queue_refusal(question, request.class_name or result.class_code)

    log_trace(TRACE_DIRECTORY, question, _TraceView(result), provider)

    return AskResponse(
        action=result.action,
        answer=result.answer,
        confidence=result.confidence,
        citations=[Citation(**c) for c in result.citations],
        clarify_options=result.clarify_options,
        escalated_to=result.escalated_to,
        trace_id=f"tr_{uuid.uuid4().hex[:8]}",
    )


@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict:
    """Nút "Báo sai" trên UI — đẩy vào hàng đợi để TA xác nhận (HAX: sửa dễ dàng)."""
    _queue_refusal(f"[BÁO SAI] {request.question} | bot đã trả lời: {request.answer[:200]}", None)
    return {"ok": True, "queued_for_ta": True, "trace_id": request.trace_id}
