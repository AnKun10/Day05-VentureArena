"""Lời gọi AI ĐẶT ĐÚNG CHỖ QUYẾT ĐỊNH — LLM tự phán câu hỏi này trả lời được / mơ hồ / ngoài phạm vi /
không có căn cứ, chứ không chỉ gọt câu chữ sau khi luật đã quyết xong.

Vì sao viết lại thay vì dùng `providers.model_excerpt()`: bản đó chỉ chạy KHI action đã là "answer" và
chỉ thay đoạn text, nên không bao giờ đổi được "answer" -> "refuse". Đo trên golden set cho thấy toàn bộ
case fail của backend cũ là lỗi QUYẾT ĐỊNH, xảy ra trước khi LLM được gọi — thêm API key cũng không sửa
được case nào (xem eval/results/comparison-bot-vs-backend.md). Rubric R5 đòi "AI thật ở quyết định
trung tâm", nên lời gọi phải nằm ở đây.

Giữ nguyên 2 thiết kế tốt của bản cũ: chuỗi fallback nhiều provider, và bắt buộc `excerpt` phải là
substring có thật của nguồn (LLM không chế ra chữ không tồn tại).

Không có API key -> trả None, caller tự lui về luật. Sản phẩm vẫn chạy, chỉ mất phần AI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from providers import _KEYS, _DEFAULT_MODELS, _chat_completion, _openai_response

VERDICT_ANSWERABLE = "answerable"
VERDICT_AMBIGUOUS = "ambiguous"
VERDICT_OUT_OF_SCOPE = "out_of_scope"
VERDICT_NO_BASIS = "no_basis"

_VALID_VERDICTS = {VERDICT_ANSWERABLE, VERDICT_AMBIGUOUS, VERDICT_OUT_OF_SCOPE, VERDICT_NO_BASIS}

_SYSTEM = "You are a decision component. Return valid JSON only, no prose."

_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": sorted(_VALID_VERDICTS)},
        "excerpt": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "excerpt", "reason"],
    "additionalProperties": False,
}


def _prompt(question: str, source_text: str) -> str:
    return (
        "You decide how a course assistant must handle a student's question. "
        "You may ONLY use SOURCE. Never use outside knowledge.\n\n"
        "Return JSON: {\"verdict\": ..., \"excerpt\": ..., \"reason\": ...}\n\n"
        "verdict must be exactly one of:\n"
        '- "answerable": SOURCE directly answers it. Set excerpt to the smallest exact substring of '
        "SOURCE that answers it. Do not translate, reword, summarise or add anything.\n"
        '- "ambiguous": the question is about a real topic but does not say WHICH session/class, and '
        "SOURCE has several candidates. Set excerpt to \"\".\n"
        '- "out_of_scope": the student is asking for exam/assignment answers, their own or another '
        "student's grades, personal data, or a deadline extension. Set excerpt to \"\".\n"
        '- "no_basis": SOURCE does not contain the answer. Set excerpt to "". Choose this rather than '
        "guessing. Answering from outside SOURCE is the worst possible outcome.\n\n"
        "reason: one short sentence, Vietnamese.\n\n"
        f"QUESTION:\n{question}\n\nSOURCE:\n{source_text}"
    )


@dataclass
class AiVerdict:
    verdict: str
    excerpt: str
    reason: str
    provider: str


def available_providers() -> list[str]:
    """Provider có key thật trong env, theo thứ tự AI_PROVIDER_ORDER. Rỗng = AI đang tắt."""
    order = os.environ.get("AI_PROVIDER_ORDER", "openai,gemini,openrouter,cerebras").split(",")
    return [name.strip() for name in order if name.strip() in _KEYS and os.environ.get(_KEYS[name.strip()])]


def _call(name: str, question: str, source_text: str) -> str:
    key = os.environ[_KEYS[name]]
    model = os.environ.get(f"{name.upper()}_MODEL", _DEFAULT_MODELS[name])
    prompt = _prompt(question, source_text)

    if name == "openai":
        return _openai_response(key, model, prompt)
    if name == "gemini":
        from google import genai

        response = genai.Client(api_key=key).interactions.create(
            model=model,
            input=prompt,
            store=False,
            response_format={"type": "text", "mime_type": "application/json", "schema": _SCHEMA},
        )
        return response.output_text
    if name == "openrouter":
        return _chat_completion("https://openrouter.ai/api/v1/chat/completions", key, model, prompt)
    return _chat_completion("https://api.cerebras.ai/v1/chat/completions", key, model, prompt, cerebras=True)


def ai_verdict(question: str, source_text: str, call=_call) -> Optional[AiVerdict]:
    """Hỏi LLM quyết định. Trả None nếu không có key, mọi provider lỗi, hoặc kết quả không hợp lệ.

    Kiểm tra bắt buộc với verdict="answerable": `excerpt` phải là substring CÓ THẬT của source —
    LLM không được chế ra chữ không có trong nguồn (giữ nguyên guard của bản backend cũ).
    """
    for name in available_providers():
        try:
            raw = json.loads(call(name, question, source_text))
            verdict = raw.get("verdict")
            excerpt = raw.get("excerpt") or ""
            if verdict not in _VALID_VERDICTS:
                continue
            if verdict == VERDICT_ANSWERABLE:
                if not excerpt or excerpt not in source_text:
                    # LLM bịa đoạn không có trong nguồn -> coi như không trả lời được, KHÔNG dùng kết quả này.
                    continue
            return AiVerdict(
                verdict=verdict,
                excerpt=excerpt,
                reason=str(raw.get("reason") or ""),
                provider=name,
            )
        except Exception:
            continue
    return None
