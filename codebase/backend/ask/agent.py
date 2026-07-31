"""Agent /ask: OpenAI Agents SDK + 2 function tool tra cứu (token-overlap).

Agent chỉ trả lời dựa trên kết quả tool (chống bịa). Với runner=None sẽ gọi
OpenAI thật; test truyền runner giả để chạy offline.
"""

from typing import Literal

from pydantic import BaseModel

from .prompts import ASK_V1
from .retrieval import search_qa as _search_qa, search_resources as _search_resources


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


def _build_agent(store, cfg):
    from agents import Agent, function_tool
    from recsys.embedder import embed_texts

    def _embed(text: str):
        return embed_texts([text], cfg)[0]

    @function_tool
    def search_qa(query: str) -> str:
        """Tra kênh hỏi-đáp và bản tin để tìm thông tin về AI, kiến thức kỹ
        thuật, chương trình học, logistics của khoá. `query` là từ khoá chính."""
        return _format_qa(_search_qa(store, query, embed=_embed))

    @function_tool
    def search_resources(query: str) -> str:
        """Tra tài nguyên (slide, record/recording) và lịch (link Zoom, giờ,
        buổi) của khoá. `query` là từ khoá về tài liệu/buổi cần tìm."""
        return _format_resources(_search_resources(store, query))

    return Agent(name="companion_ask", instructions=ASK_V1, model=cfg.enrich_model,
                 tools=[search_qa, search_resources], output_type=AskResult)


def answer_question(store, question: str, cfg, runner=None) -> AskResult:
    if runner is not None:
        return runner(store, question)
    from agents import Runner
    agent = _build_agent(store, cfg)
    return Runner.run_sync(agent, question).final_output
