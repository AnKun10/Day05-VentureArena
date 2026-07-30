import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from ingest.models import TagId
from .embedder import embed_texts
from .prompts import INTEREST_V1, INTEREST_VERSION

TRACE_DIR = Path("eval/traces/recsys")


class InterestProfile(BaseModel):
    interest_summary_vi: str
    interest_tags: list[TagId] = Field(min_length=1, max_length=4)


def compute_hash(bio: str, bookmark_ids: list[str]) -> str:
    raw = f"{bio}|{','.join(sorted(bookmark_ids))}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_input(bio: str, rows: list[dict]) -> str:
    lines = [f"- {r['title']} [tags: {', '.join(r['tags'])}] {(r['summary'] or '')[:150]}"
             for r in rows] or ["- (chưa có)"]
    return f"Bio: {bio or '(trống)'}\nCác bài đã bookmark:\n" + "\n".join(lines)


def _run_agent(input_text: str, cfg) -> InterestProfile:
    from agents import Agent, Runner
    agent = Agent(name="profile_inferencer", instructions=INTEREST_V1,
                  model=cfg.enrich_model, output_type=InterestProfile)
    return Runner.run_sync(agent, input_text).final_output


def ensure_profile(store, vs, cfg, user_id: str, runner=None, embedder=None) -> bool:
    user = store.get_user(user_id)
    if user is None:
        raise KeyError(user_id)
    bio = user["bio"] or ""
    ids = store.list_bookmarks(user_id)
    h = compute_hash(bio, ids)
    blank = not bio.strip() and not ids
    if h == user["bio_hash"] and (blank or vs.get_user(user_id) is not None):
        return False
    if blank:
        store.save_profile(user_id, h, "", [])
        return False
    input_text = _build_input(bio, store.bookmarked_news(user_id, 10))
    profile = (runner or (lambda t: _run_agent(t, cfg)))(input_text)
    vector = (embedder or embed_texts)([profile.interest_summary_vi], cfg)[0]
    vs.upsert_user(user_id, vector)
    store.save_profile(user_id, h, profile.interest_summary_vi, list(profile.interest_tags))
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    (TRACE_DIR / f"{user_id}.json").write_text(json.dumps({
        "user_id": user_id, "bio_hash": h, "prompt_version": INTEREST_VERSION,
        "model": cfg.enrich_model, "input": input_text[:500],
        "output": profile.model_dump(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
