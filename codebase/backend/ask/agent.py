"""Agent /ask: OpenAI Agents SDK + 2 function tool tra cứu (token-overlap).

Agent chỉ trả lời dựa trên kết quả tool (chống bịa). Với runner=None sẽ gọi
OpenAI thật; test truyền runner giả để chạy offline.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel

from .prompts import ASK_V1
from .retrieval import search_qa as _search_qa, search_resources as _search_resources

_VN_TZ = timezone(timedelta(hours=7))       # Asia/Ho_Chi_Minh (UTC+7)
_VN_DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


class AskResult(BaseModel):
    # reasoning ĐỨNG TRƯỚC để ép Chain-of-Thought: model suy luận ngắn (hỏi gì →
    # tool nào → tool có nguồn khớp không → chọn action) rồi mới quyết. Không trả
    # cho user (API bỏ qua). answer: có căn cứ | no_info: hợp lệ nhưng không nguồn
    # | clarify: mơ hồ | refuse: ngoài phạm vi/quyền hạn.
    reasoning: str = ""
    action: Literal["answer", "no_info", "clarify", "refuse"]
    answer_vi: str
    citations: list[str] = []


def _format_qa(results: list[dict]) -> str:
    if not results:
        return "Không tìm thấy kết quả liên quan trong hỏi-đáp/bản tin."
    return "\n".join(
        f"[{i}] ({r['source']}) {r['title']}: {r['snippet']} — nguồn: {r['url']}"
        for i, r in enumerate(results, 1))


def _format_resources(results: list[dict]) -> str:
    if not results:
        return "Không tìm thấy tài nguyên hoặc link zoom nào phù hợp."
    lines = []
    for i, r in enumerate(results, 1):
        when = f" ({r['when']})" if r.get("when") else ""
        lines.append(f"[{i}] ({r['source']}/{r['kind']}) {r['title']}{when} — {r['url']}")
    return "\n".join(lines)


def now_vn() -> str:
    now = datetime.now(_VN_TZ)
    return f"{_VN_DAYS[now.weekday()]}, {now.strftime('%Y-%m-%d %H:%M')} (giờ VN, UTC+7)"


def _build_agent(store, cfg, surfaced: list):
    """surfaced: list tích luỹ URL mà tool đã trả cho agent (để guardrail sau
    này back-fill citation / phát hiện answer không có nguồn)."""
    from agents import Agent, function_tool
    from recsys.embedder import embed_texts

    def _embed(text: str):
        return embed_texts([text], cfg)[0]

    @function_tool
    def current_datetime() -> str:
        """Ngày giờ HIỆN TẠI (giờ Việt Nam). Gọi khi cần hiểu 'hôm nay', 'tuần
        này', 'sắp tới', 'gần đây' hoặc để biết đâu là thông tin/buổi mới nhất."""
        return now_vn()

    @function_tool
    def search_qa(query: str) -> str:
        """Tra kênh hỏi-đáp và bản tin để tìm thông tin về AI, kiến thức kỹ
        thuật, chương trình học, logistics của khoá. `query` là từ khoá chính."""
        results = _search_qa(store, query, embed=_embed)
        surfaced.extend(r["url"] for r in results if r.get("url"))
        return _format_qa(results)

    @function_tool
    def search_resources(query: str) -> str:
        """Tra tài nguyên (slide, record/recording) và lịch (link Zoom, giờ,
        buổi) của khoá. `query` là từ khoá về tài liệu/buổi cần tìm."""
        results = _search_resources(store, query)
        surfaced.extend(r["url"] for r in results if r.get("url"))
        return _format_resources(results)

    return Agent(name="companion_ask", instructions=ASK_V1, model=cfg.enrich_model,
                 tools=[current_datetime, search_qa, search_resources], output_type=AskResult)


_NO_INFO = "Mình chưa có thông tin về việc này. Bạn thử hỏi trực tiếp ở kênh #hỏi-đáp nhé."


def enforce_citations(result: AskResult, surfaced: list) -> AskResult:
    """Guardrail HẬU-XỬ-LÝ chống bịa: một 'answer' phải có nguồn.
    - answer đã có citation → giữ nguyên.
    - answer thiếu citation NHƯNG tool có trả URL → back-fill (agent quên trích).
    - answer thiếu citation VÀ không có URL nào từ tool → agent trả lời không
      nguồn (nghi bịa) → hạ xuống no_info an toàn."""
    if result.action != "answer" or result.citations:
        return result
    urls = list(dict.fromkeys(u for u in surfaced if isinstance(u, str) and u.startswith("http")))
    if urls:
        return result.model_copy(update={"citations": urls[:3]})
    return result.model_copy(update={"action": "no_info", "answer_vi": _NO_INFO, "citations": []})


def _extract_meta(result) -> dict:
    """Rút số liệu quan sát từ RunResult: số lần gọi tool + token (best-effort)."""
    meta = {"tool_calls": 0, "output_tokens": 0, "input_tokens": 0}
    try:
        for it in getattr(result, "new_items", []) or []:
            if type(it).__name__ == "ToolCallItem" or getattr(it, "type", "") == "tool_call_item":
                meta["tool_calls"] += 1
    except Exception:
        pass
    try:
        for resp in getattr(result, "raw_responses", []) or []:
            usage = getattr(resp, "usage", None)
            if usage:
                meta["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
                meta["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
    except Exception:
        pass
    return meta


def answer_question(store, question: str, cfg, runner=None) -> tuple[AskResult, dict]:
    """Trả (AskResult, meta). meta = {tool_calls, output_tokens, input_tokens}.
    Áp guardrail hậu-xử-lý enforce_citations trước khi trả."""
    if runner is not None:
        r = runner(store, question)
        result, meta = r if isinstance(r, tuple) else (r, {})
        return enforce_citations(result, []), meta
    from agents import Runner
    surfaced: list = []
    agent = _build_agent(store, cfg, surfaced)
    result = Runner.run_sync(agent, question)
    return enforce_citations(result.final_output, surfaced), _extract_meta(result)
