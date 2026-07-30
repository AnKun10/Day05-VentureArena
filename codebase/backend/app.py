"""FastAPI boundary for source-backed Companion Q&A."""

import os
from pathlib import Path
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

app = FastAPI(title="Companion API")


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)


class AskResponse(BaseModel):
    action: str
    answer: str
    citations: list[str]
    confidence: float


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    result = answer(request.question, load_sources(DATA_DIRECTORY))
    provider = None
    if result.action == "answer":
        excerpt, provider = model_excerpt(request.question, result.answer)
        if excerpt:
            result = replace(result, answer=excerpt)
    log_trace(TRACE_DIRECTORY, request.question, result, provider)
    return AskResponse(**result.__dict__)
