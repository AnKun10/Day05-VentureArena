"""Smoke check prompt enrich: python -m ingest.smoke (cần OPENAI_API_KEY).
Pass khi mỗi bài có >=1 tag trùng expected_tags và summary <= 3 câu."""
import json
import sys
from pathlib import Path

from .agents import enrich_post
from .config import Config


def main():
    cfg = Config.from_env()
    if not cfg.openai_api_key:
        print("SKIP: thiếu OPENAI_API_KEY")
        return
    cases = json.loads(Path("tests/smoke_posts.json").read_text(encoding="utf-8"))
    failures = 0
    for c in cases:
        e, _, _ = enrich_post(
            {"message_id": f"smoke-{c['message_id']}", "title": c["title"],
             "content": c["content"], "channel": c["channel"]}, cfg)
        tag_ok = bool(set(e.tags) & set(c["expected_tags"]))
        sent_ok = e.summary_vi.count(".") <= 3
        status = "OK " if (tag_ok and sent_ok) else "FAIL"
        failures += 0 if (tag_ok and sent_ok) else 1
        print(f"[{status}] {c['message_id']} tags={e.tags} "
              f"expected={c['expected_tags']}")
    print(f"=> {len(cases) - failures}/{len(cases)} pass")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
