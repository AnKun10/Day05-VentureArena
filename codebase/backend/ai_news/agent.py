"""Agent Daily AI News: Agents SDK + 2 tool (search_ai_news, verify_source).

Chọn 3 bài AI mới đã xác minh nguồn, tóm tắt tiếng Việt. runner=None → gọi
OpenAI thật; test truyền runner giả (chạy offline).
"""

from urllib.parse import urlparse

from pydantic import BaseModel, Field

from .prompts import AINEWS_V1
from .tools import tavily_news_search, verify_url


class NewsItem(BaseModel):
    title: str
    url: str
    source: str = ""
    summary_vi: str


class DailyNews(BaseModel):
    items: list[NewsItem] = Field(default_factory=list, max_length=3)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _build_agent(cfg):
    from agents import Agent, function_tool

    @function_tool
    def search_ai_news(query: str) -> str:
        """Tìm bài báo/tin AI mới theo từ khoá (tiếng Anh sát chủ đề user).
        Trả danh sách ứng viên {title, url, trích nội dung}."""
        results = tavily_news_search(query, cfg.tavily_api_key)
        if not results:
            return "Không tìm thấy tin nào — thử từ khoá khác."
        return "\n".join(f"[{i + 1}] {r['title']} — {r['url']}\n    {r['content']}"
                         for i, r in enumerate(results))

    @function_tool
    def verify_source(url: str) -> str:
        """Xác minh 1 URL: truy cập được không + trích nội dung để kiểm tra đúng
        chủ đề AI. CHỈ dùng nguồn trả về OK."""
        ok, status, text = verify_url(url)
        if not ok:
            return f"FAIL: không truy cập được (status {status}). KHÔNG dùng nguồn này."
        return f"OK: truy cập được (status {status}). Trích nội dung: {text[:600]}"

    return Agent(name="daily_ai_news", instructions=AINEWS_V1, model=cfg.enrich_model,
                 tools=[search_ai_news, verify_source], output_type=DailyNews)


def generate_daily_news(store, user_id: str, cfg, runner=None) -> list[dict]:
    user = store.get_user(user_id) or {}
    interest = (user.get("interest_summary") or "").strip()
    tags = user.get("interest_tags") or []
    focus = interest or "trí tuệ nhân tạo, LLM, AI agents, công cụ AI mới"
    prompt = (f"Sở thích/chủ đề user quan tâm: {focus}\n"
              f"Tags: {', '.join(tags) if tags else '(chưa có)'}\n"
              "Tìm và chọn tối đa 3 bài báo/tin AI MỚI, đã xác minh nguồn, sát sở thích trên.")
    if runner is not None:
        result = runner(prompt)
    else:
        from agents import Runner
        result = Runner.run_sync(_build_agent(cfg), prompt).final_output
    out = []
    for it in result.items[:3]:
        if not it.url:
            continue
        out.append({"title": it.title, "url": it.url,
                    "source": it.source or _domain(it.url), "summary": it.summary_vi})
    return out
