"""Source-bounded Q&A decisions for Companion."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata

import yaml


_STOP_WORDS = {"la", "khi", "nao", "buoi", "tuan", "nay", "hoc", "gi", "co", "duoc", "khong", "ve", "cho", "toi"}


@dataclass(frozen=True)
class Source:
    citation: str
    text: str


@dataclass(frozen=True)
class Answer:
    action: str
    answer: str
    citations: list[str]
    confidence: float


def _normalized(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFD", value.lower()) if not unicodedata.combining(character)
    )


def _words(value: str) -> set[str]:
    normalized = _normalized(value)
    return {word for word in re.findall(r"\w+", normalized) if len(word) > 1 and word not in _STOP_WORDS}


def _is_ambiguous_session(question: str) -> bool:
    normalized = _normalized(question)
    return "lab" in normalized and "tuan" in normalized and not re.search(r"lab\s*[- ]?\d+", normalized)


def answer(question: str, sources: list[Source]) -> Answer:
    if _is_ambiguous_session(question):
        return Answer("clarify", "Bạn muốn hỏi Lab nào? Ví dụ: Lab-3.", [], 0.0)
    query = _words(question)
    if not query:
        return Answer("clarify", "Bạn có thể nêu rõ buổi học hoặc thông tin cần hỏi không?", [], 0.0)
    best = max(sources, key=lambda source: len(query & _words(source.text)), default=None)
    score = len(query & _words(best.text)) / len(query) if best else 0.0
    if score <= 0.5:
        return Answer(
            "refuse",
            "Mình chưa có nguồn chính thức để trả lời việc này. Câu hỏi sẽ được chuyển tới TA phụ trách.",
            [],
            round(score, 2),
        )
    return Answer("answer", _excerpt(best.text, query), [best.citation], round(score, 2))


def _excerpt(text: str, query: set[str]) -> str:
    lines = [line.strip(" -\t") for line in re.split(r"[\r\n]+", text) if line.strip()]
    return max(lines or [text], key=lambda line: len(query & _words(line)))


def load_sources(data_directory: str | Path) -> list[Source]:
    root = Path(data_directory)
    sources = []
    for path in sorted(root.rglob("*")) if root.exists() else []:
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            text = yaml.safe_dump(yaml.safe_load(text), allow_unicode=True, default_flow_style=False, sort_keys=False)
        if text.strip():
            sources.append(Source(path.relative_to(root).as_posix(), text))
    return sources


def log_trace(trace_directory: str | Path, question: str, result: Answer, provider: str | None = None) -> Path:
    trace_directory = Path(trace_directory)
    trace_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    path = trace_directory / f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    path.write_text(
        json.dumps(
            {"timestamp": timestamp.isoformat(), "question": question, "action": result.action, "provider": provider,
             "answer": result.answer, "citations": result.citations, "confidence": result.confidence},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
