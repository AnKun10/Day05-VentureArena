import json
import uuid
from pathlib import Path

from agents import Agent, Runner, function_tool

from ..config import Config
from ..models import NewsEnrichment
from ..prompts import ENRICH_V1, PROMPT_VERSION
from ..tools import pick_image, tavily_images

TRACE_DIR = Path("eval/traces/ingest")


def build_agent(cfg: Config) -> Agent:
    @function_tool
    def search_image(query: str) -> str:
        """Tìm 1 ảnh minh hoạ theo query tiếng Anh. Trả URL, hoặc chuỗi rỗng."""
        return pick_image(tavily_images(query, cfg.tavily_api_key)) or ""

    return Agent(
        name="news_enricher",
        instructions=ENRICH_V1,
        model=cfg.enrich_model,
        output_type=NewsEnrichment,
        tools=[search_image],
    )


def enrich_post(post: dict, cfg: Config, runner=None) -> tuple[NewsEnrichment, str, str]:
    """runner: callable(input_text) -> NewsEnrichment; None = agent thật."""
    input_text = (f"Kênh: #{post['channel']}\nTiêu đề: {post['title']}\n"
                  f"Nội dung:\n{post['content']}")
    usage = None
    if runner is None:
        agent = build_agent(cfg)
        result = Runner.run_sync(agent, input_text)
        enrichment: NewsEnrichment = result.final_output
        u = result.context_wrapper.usage
        usage = {"requests": u.requests, "input_tokens": u.input_tokens,
                 "output_tokens": u.output_tokens}
    else:
        enrichment = runner(input_text)

    if enrichment.image_url:
        image_source = "tavily"
    else:
        image_source = "placeholder"

    trace_id = uuid.uuid4().hex[:12]
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    (TRACE_DIR / f"{post['message_id']}.json").write_text(json.dumps({
        "trace_id": trace_id,
        "message_id": post["message_id"],
        "prompt_version": PROMPT_VERSION,
        "model": cfg.enrich_model,
        "input": input_text[:500],
        "output": enrichment.model_dump(),
        "image_source": image_source,
        "usage": usage,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return enrichment, image_source, trace_id
