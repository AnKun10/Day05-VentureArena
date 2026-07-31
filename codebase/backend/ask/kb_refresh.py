"""Làm mới news + schedule từ gói KB (discord_kb) — nhất quán với chính sách access.

3 việc:
  1) GOVERNANCE: gỡ khỏi news mọi post mà KB gắn nhạy cảm (personal_data/
     internal_only/...) — để feed học viên tuân thủ như /ask.
  2) SCHEDULE: re-extract sự kiện tối từ announcements KB (messages_clean,
     sensitivity=none) thay cho bản trích từ crawl thô.
  3) NEWS: re-enrich (force) — làm mới tóm tắt/tag/ảnh, GIỮ nguyên engagement
     (hearts/comment) và author vốn có (KB không có count reaction đáng tin).

Dùng:  python -m ask.kb_refresh <kb_dir>
"""

import json
import sys
from collections import Counter
from pathlib import Path

from ingest.agents import enrich_post, extract_schedule
from ingest.config import Config
from ingest.store import Store

_ANN_CHANNELS = {
    "announcements": "thong-bao:all",
    "cohort_3_common_announcements": "thong-bao:3",
    "cohort_4_common_announcements": "thong-bao:4",
}


def _messages(kb_dir: Path):
    for ln in (kb_dir / "data" / "messages_clean.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            yield json.loads(ln)


def governance_prune(store: Store, kb_dir: Path) -> int:
    """Gỡ post trong DB mà KB đánh dấu nhạy cảm (theo message_id)."""
    sensitive = {m["message_id"] for m in _messages(kb_dir)
                 if m.get("sensitivity_category") not in (None, "none")}
    have = {p["message_id"] for p in store.list_news()}
    removed = 0
    for mid in have & sensitive:
        store.delete_post(mid)
        removed += 1
    return removed


def reextract_schedule(store: Store, cfg, kb_dir: Path) -> int:
    """Xoá schedule cũ, trích lại từ announcements KB (chỉ sensitivity=none)."""
    store.clear_schedule_events()
    events = 0
    for m in _messages(kb_dir):
        ch = _ANN_CHANNELS.get(m.get("channel_name"))
        if not ch or m.get("sensitivity_category") != "none":
            continue
        text = (m.get("text_clean") or "").strip()
        if len(text) < 15:
            continue
        refs = m.get("source_reference_or_reference") or m.get("source_url_or_reference") or ""
        post = {"message_id": m["message_id"], "title": text[:60], "content": text,
                "channel": ch, "created_at": m.get("timestamp") or "",
                "jump_url": refs if isinstance(refs, str) else ""}
        if store.is_schedule_extracted(m["message_id"]):
            continue
        try:
            extraction, trace_id = extract_schedule(post, cfg)
            events += store.save_schedule_extraction(
                m["message_id"], [e.model_dump() for e in extraction.events], trace_id)
        except Exception as exc:
            print(f"[kb-schedule-fail] {m['message_id']}: {exc}")
    return events


def reenrich_news(store: Store, cfg) -> dict:
    """Re-enrich (force) toàn bộ news — giữ content/engagement, làm mới summary/tag/ảnh."""
    stats = Counter()
    for row in store.pending_enrichment(limit=1000, force=True):
        try:
            e, image_source, trace_id = enrich_post(row, cfg)
            store.save_enrichment(row["message_id"], e, image_source, "v1", trace_id)
            stats["enriched"] += 1
        except Exception as exc:
            print(f"[kb-enrich-fail] {row['message_id']}: {exc}")
            stats["failed"] += 1
    return dict(stats)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m ask.kb_refresh <kb_dir>")
        raise SystemExit(2)
    kb_dir = Path(sys.argv[1])
    cfg = Config.from_env()
    store = Store(cfg.db_path)
    removed = governance_prune(store, kb_dir)
    print(f"[kb-refresh] governance: gỡ {removed} post nhạy cảm khỏi news")
    sched = reextract_schedule(store, cfg, kb_dir)
    print(f"[kb-refresh] schedule: re-extract {sched} sự kiện từ announcements KB")
    news = reenrich_news(store, cfg)
    print(f"[kb-refresh] news re-enrich (force): {news}")
    store.close()


if __name__ == "__main__":
    main()
