"""Ingest gói KB `discord_kb_v0.1-provisional` vào nguồn tri thức /ask.

CHÍNH SÁCH ACCESS (quan trọng): gói đặt MỌI chunk là access_scope=review_required
(ingestion_eligible=false) vì chưa có chủ quyền duyệt. Team AI Thực Chiến LÀ chủ
dữ liệu Discord của khoá → duyệt subset AN TOÀN để dùng cho bot học viên:
  - CHỈ nhận chunk `sensitivity_category == 'none'`.
  - LOẠI toàn bộ personal_data / internal_only / restricted / suspected_secret.
  - Bỏ chunk rỗng text.
Quyết định này được ghi log rõ ràng mỗi lần chạy (auditable). Chỉ embed
`chunk_text`; giữ provenance (thread_id, url nguồn) để trích dẫn.

Dùng:  python -m ask.ingest_kb <đường_dẫn_gói_kb>   (thư mục chứa data/kb_chunks.jsonl)
"""

import json
import sys
from collections import Counter
from pathlib import Path

from ingest.config import Config
from ingest.store import Store
from recsys.embedder import embed_texts

APPROVED_SENSITIVITY = {"none"}       # team duyệt: chỉ nội dung không nhạy cảm

_CHANNEL_LABEL = {
    "questions": "hỏi-đáp", "sharing": "chia sẻ", "lessons": "bài học",
    "resources": "tài nguyên", "announcements": "thông báo",
    "cohort_3_common_announcements": "thông báo K3",
    "cohort_4_common_announcements": "thông báo K4",
}


def _eligible(chunk: dict) -> bool:
    return (chunk.get("sensitivity_category") in APPROVED_SENSITIVITY
            and (chunk.get("chunk_text") or "").strip())


def ingest_kb(store: Store, cfg, kb_dir: str | Path, embedder=embed_texts, batch: int = 64) -> dict:
    path = Path(kb_dir) / "data" / "kb_chunks.jsonl"
    stats = Counter()
    excluded_sens = Counter()
    approved = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        c = json.loads(ln)
        stats["total"] += 1
        if not _eligible(c):
            stats["excluded"] += 1
            excluded_sens[c.get("sensitivity_category")] += 1
            continue
        refs = c.get("source_reference") or []
        store.upsert_kb_chunk(
            c["chunk_id"],
            _CHANNEL_LABEL.get(c.get("channel_name"), c.get("channel_name") or "khoá"),
            c.get("title") or "(không tiêu đề)",
            c.get("chunk_text") or "",
            c.get("thread_id"),
            refs[0] if refs else None)
        approved.append(c["chunk_id"])
        stats["ingested"] += 1

    # Embed những chunk chưa có embedding (key kb:<chunk_id>)
    have = set(store.get_ask_embeddings())
    by_id = {c["chunk_id"]: c["chunk_text"] for c in store.list_kb_chunks()}
    todo = [(cid, by_id[cid]) for cid in approved if f"kb:{cid}" not in have]
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        vecs = embedder([txt for _, txt in chunk], cfg)
        for (cid, _), vec in zip(chunk, vecs):
            store.save_ask_embedding(f"kb:{cid}", vec)
    stats["embedded"] = len(todo)
    return {"stats": dict(stats), "excluded_by_sensitivity": dict(excluded_sens)}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m ask.ingest_kb <kb_dir>")
        raise SystemExit(2)
    cfg = Config.from_env()
    store = Store(cfg.db_path)
    result = ingest_kb(store, cfg, sys.argv[1])
    store.close()
    print(f"[kb] policy: chỉ nhận sensitivity=none (team-approved). {result['stats']}")
    print(f"[kb] loại theo nhạy cảm: {result['excluded_by_sensitivity']}")


if __name__ == "__main__":
    main()
