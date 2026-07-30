"""FastAPI boundary for source-backed Companion Q&A."""

import os
from pathlib import Path
import sqlite3
from dataclasses import replace

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from companion_rag import answer, load_sources, log_trace
from providers import model_excerpt


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(Path(__file__).with_name(".env"))
DATA_DIRECTORY = Path(os.environ.get("COMPANION_DATA_DIR", ROOT / "codebase" / "data"))
TRACE_DIRECTORY = Path(os.environ.get("COMPANION_TRACE_DIR", ROOT / "eval" / "traces"))
QUEUE_PATH = Path(os.environ.get("COMPANION_QUEUE_PATH", ROOT / "data" / "companion.sqlite3"))

app = FastAPI(title="Companion API")


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)
    class_name: str | None = Field(default=None, max_length=100)


class AskResponse(BaseModel):
    action: str
    answer: str
    citations: list[str]
    confidence: float


def _queue_refusal(question: str, class_name: str | None) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(QUEUE_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS unanswered_questions (question TEXT NOT NULL, class_name TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute("INSERT INTO unanswered_questions (question, class_name) VALUES (?, ?)", (question, class_name))


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    result = answer(request.question, load_sources(DATA_DIRECTORY))
    provider = None
    if result.action == "answer":
        excerpt, provider = model_excerpt(request.question, result.answer)
        if excerpt:
            result = replace(result, answer=excerpt)
    if result.action == "refuse":
        _queue_refusal(request.question, request.class_name)
    log_trace(TRACE_DIRECTORY, request.question, result, provider)
    return AskResponse(**result.__dict__)
