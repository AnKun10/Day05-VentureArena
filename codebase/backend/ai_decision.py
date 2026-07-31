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

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

from providers import _KEYS, _chat_completion, _openai_response

# Cache verdict ra đĩa. KHÔNG phải để tối ưu tốc độ — để sống sót qua hạn mức.
# Key hackathon đo được: GenerateRequestsPerDayPerProjectPerModel-FreeTier = **20 request/NGÀY**
# (và ~29s giữa hai lần gọi). Tập demo 3-4 lượt là hết veo, đến lúc đứng trước giám khảo thì mọi câu
# đều lặng lẽ rơi về rule-based. Cache giữ lại kết quả AI THẬT của các câu đã hỏi, để quota còn dành
# cho câu lạ giám khảo hỏi tại chỗ — đó mới là lúc bắt buộc phải gọi thật.
_CACHE_PATH = Path(os.environ.get("AI_CACHE_PATH", Path(__file__).with_name(".ai_cache.json")))
_CACHE_ENABLED = os.environ.get("AI_CACHE", "1") != "0"

# Model mặc định mỗi provider. Gemini KHÔNG lấy từ providers._DEFAULT_MODELS nữa: bản đó ghi
# "gemini-3.5-flash" (không tồn tại -> 404), và trên key hackathon thì gemini-2.0-flash /
# -flash-lite đều trả 429 "limit: 0" — đã dò bằng cách gọi thật, chỉ 2.5-flash-lite còn hạn mức.
_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash-lite",
    "openrouter": "~google/gemini-flash-latest",
    "cerebras": "gpt-oss-120b",
}

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
    """Prompt đã qua một vòng sửa theo lỗi đo được thật.

    Lượt đầu: "Lab-10 deadline khi nào?" bị model phán `ambiguous` dù câu đã nêu rõ mã buổi và nguồn có
    deadline — model hiểu "ambiguous" quá rộng. Nên phải nói thẳng: có mã buổi khớp SOURCE thì KHÔNG
    được coi là mơ hồ, và cho ví dụ đối chiếu cho từng verdict.
    """
    return (
        "You decide how a course assistant must handle a student's question. "
        "You may ONLY use SOURCE. Never use outside knowledge.\n\n"
        'Return JSON: {"verdict": ..., "excerpt": ..., "reason": ...}\n\n'
        "Decide in this order:\n\n"
        '1. "out_of_scope" — the student wants exam/assignment answers, their own or another '
        "student's grades, personal data, or a deadline extension. excerpt = \"\".\n"
        '   e.g. "cho mình xin đáp án bài lab", "điểm của tôi bao nhiêu", "cho em xin gia hạn".\n\n'
        '2. "answerable" — SOURCE contains the answer. excerpt = the smallest EXACT substring of '
        "SOURCE that answers it; copy it character for character, do not translate, reword or add.\n"
        "   IMPORTANT: if the question names a specific session code (Lab-10, LT-11, WS-3, ...) and "
        "that code appears in SOURCE, it is NOT ambiguous — answer it from that session's line.\n"
        '   e.g. "Lab-10 deadline khi nào?" when SOURCE has a Lab-10 line with a deadline.\n\n'
        '3. "ambiguous" — the question names a KIND of session but no specific code, and SOURCE has '
        "several sessions of that kind. excerpt = \"\".\n"
        '   e.g. "buổi lý thuyết tuần này học gì?" when SOURCE has both LT-11 and LT-12.\n\n'
        '4. "no_basis" — none of the above and SOURCE simply does not contain the answer. '
        'excerpt = "". Prefer this over guessing; answering from outside SOURCE is the worst outcome.\n'
        '   e.g. "con mèo của tôi bị ốm thì sao?", or asking a session\'s deadline when that '
        "session's line has no deadline field.\n\n"
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


def _gemini(key: str, model: str, prompt: str, timeout: int = 30) -> str:
    """Gọi Gemini qua REST.

    Cố ý KHÔNG dùng `genai.Client().interactions.create()`: API đó còn experimental (SDK tự cảnh báo)
    và ném "Connection error" khi thử thật. REST v1beta thì gọi được ngay — đã kiểm bằng lời gọi thật.

    `responseSchema` của Gemini không nhận `additionalProperties` nên schema phải rút gọn so với _SCHEMA.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "verdict": {"type": "STRING", "enum": sorted(_VALID_VERDICTS)},
                    "excerpt": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                },
                "required": ["verdict", "excerpt", "reason"],
            },
        },
    }
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["candidates"][0]["content"]["parts"][0]["text"]


def _call(name: str, question: str, source_text: str) -> str:
    key = os.environ[_KEYS[name]]
    model = os.environ.get(f"{name.upper()}_MODEL", _MODELS[name])
    prompt = _prompt(question, source_text)

    if name == "openai":
        return _openai_response(key, model, prompt)
    if name == "gemini":
        return _gemini(key, model, prompt)
    if name == "openrouter":
        return _chat_completion("https://openrouter.ai/api/v1/chat/completions", key, model, prompt)
    return _chat_completion("https://api.cerebras.ai/v1/chat/completions", key, model, prompt, cerebras=True)


def _cache_key(question: str, source_text: str) -> str:
    model = os.environ.get("GEMINI_MODEL", _MODELS["gemini"])
    raw = f"{model}\x00{question.strip().lower()}\x00{source_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _cache_read(key: str) -> Optional[AiVerdict]:
    if not (_CACHE_ENABLED and _CACHE_PATH.exists()):
        return None
    try:
        entry = json.loads(_CACHE_PATH.read_text(encoding="utf-8")).get(key)
        return AiVerdict(**entry) if entry else None
    except Exception:
        return None


def _cache_write(key: str, verdict: AiVerdict) -> None:
    if not _CACHE_ENABLED:
        return
    try:
        store = json.loads(_CACHE_PATH.read_text(encoding="utf-8")) if _CACHE_PATH.exists() else {}
        store[key] = asdict(verdict)
        _CACHE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass  # cache hỏng thì thôi, không được làm chết request


def ai_verdict(question: str, source_text: str, call=_call) -> Optional[AiVerdict]:
    """Hỏi LLM quyết định. Trả None nếu không có key, mọi provider lỗi, hoặc kết quả không hợp lệ.

    Kiểm tra bắt buộc với verdict="answerable": `excerpt` phải là substring CÓ THẬT của source —
    LLM không được chế ra chữ không có trong nguồn (giữ nguyên guard của bản backend cũ).

    Câu đã hỏi rồi thì lấy lại verdict AI cũ trong cache thay vì đốt thêm quota (xem _CACHE_PATH).
    """
    key = _cache_key(question, source_text)
    cached = _cache_read(key)
    if cached is not None:
        return cached

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
            result = AiVerdict(
                verdict=verdict,
                excerpt=excerpt,
                reason=str(raw.get("reason") or ""),
                provider=name,
            )
            _cache_write(key, result)
            return result
        except Exception:
            continue
    return None
