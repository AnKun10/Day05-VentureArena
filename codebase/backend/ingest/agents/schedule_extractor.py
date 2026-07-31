import json
import re
import uuid
from pathlib import Path
from typing import Literal

from agents import Agent, Runner
from pydantic import BaseModel, Field, field_validator

from ..config import Config
from ..prompts import SCHEDULE_V1, SCHEDULE_VERSION

TRACE_DIR = Path("eval/traces/schedule")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _normalize_time(value: str | None) -> str | None:
    """'H:MM' hoặc 'HH:MM' hợp lệ -> 'HH:MM' đã zero-pad; sai định dạng -> None."""
    if value is None:
        return None
    m = _TIME_RE.match(value.strip())
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


class ScheduleEvent(BaseModel):
    type: Literal["LAB", "LT", "WS", "OH", "MD", "OTHER"]
    title: str
    date: str                      # YYYY-MM-DD
    start: str | None = None       # HH:MM
    end: str | None = None
    cohort: Literal["3", "4", "all"] = "all"
    format: Literal["Zoom", "Offline"] = "Zoom"
    zoom_url: str | None = None
    host: str | None = None
    location: str | None = None

    @field_validator("date")
    @classmethod
    def _validate_date(cls, v: str) -> str:
        if not _DATE_RE.match(v):
            raise ValueError(f"date phải đúng định dạng YYYY-MM-DD, nhận được: {v!r}")
        return v

    @field_validator("start", "end")
    @classmethod
    def _normalize_start_end(cls, v: str | None) -> str | None:
        return _normalize_time(v)


class ScheduleExtraction(BaseModel):
    events: list[ScheduleEvent] = Field(default_factory=list)


def build_agent(cfg: Config) -> Agent:
    return Agent(
        name="schedule_extractor",
        instructions=SCHEDULE_V1,
        model=cfg.enrich_model,
        output_type=ScheduleExtraction,
    )


def _cohort_hint(channel: str) -> str:
    if ":" in channel:
        _, suffix = channel.rsplit(":", 1)
        if suffix in ("3", "4"):
            return f"kênh riêng — cohort {suffix}"
    return "kênh thông báo chung — cohort all trừ khi bài nêu rõ cohort khác"


def extract_schedule(post: dict, cfg: Config, runner=None) -> tuple[ScheduleExtraction, str]:
    """runner: callable(input_text) -> ScheduleExtraction; None = agent thật."""
    posting_date = post["created_at"][:10]
    input_text = (
        f"Kênh: {post['channel']} ({_cohort_hint(post['channel'])})\n"
        f"Ngày đăng: {posting_date}\n"
        f"Tiêu đề: {post['title']}\n"
        f"Nội dung:\n{post['content']}"
    )

    if runner is None:
        agent = build_agent(cfg)
        result = Runner.run_sync(agent, input_text)
        extraction: ScheduleExtraction = result.final_output
    else:
        extraction = runner(input_text)

    trace_id = uuid.uuid4().hex[:12]
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    (TRACE_DIR / f"{post['message_id']}.json").write_text(json.dumps({
        "message_id": post["message_id"],
        "prompt_version": SCHEDULE_VERSION,
        "model": cfg.enrich_model,
        "input": input_text[:500],
        "output": extraction.model_dump(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return extraction, trace_id
