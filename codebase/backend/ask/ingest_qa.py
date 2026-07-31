"""Ingest kênh hỏi-đáp (forum threads) vào bảng qa_threads — nguồn cho /ask.

Mỗi file questions/<thread_id>.json là 1 thread: nhiều message có chung
`post_title` (câu hỏi mở thread) + `text_content` (thảo luận/trả lời). Ta gộp
các message thành body, giữ title làm câu hỏi. Ingest-once (INSERT OR REPLACE
theo thread_id), chạy lại an toàn.

Dùng:
  python -m ask.ingest_qa <đường_dẫn_thư_mục_questions>
"""

import json
import sys
from pathlib import Path

from ingest.config import Config
from ingest.store import Store


def _thread_jump_url(guild_id: str, thread_id: str) -> str:
    return f"https://discord.com/channels/{guild_id}/{thread_id}" if guild_id else ""


def ingest_qa(store: Store, questions_dir: str | Path, guild_id: str = "") -> int:
    root = Path(questions_dir)
    count = 0
    for path in sorted(root.glob("*.json")):
        if path.name == "posts.json":
            continue
        msgs = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(msgs, list) or not msgs:
            continue
        title = next((m.get("post_title") for m in msgs if m.get("post_title")), None) \
            or "(thảo luận)"
        texts = [m.get("text_content", "").strip() for m in msgs if m.get("text_content")]
        body = "\n".join(texts)
        if not body.strip():
            continue
        thread_id = path.stem
        created = next((m.get("timestamp") for m in msgs if m.get("timestamp")), "") or ""
        store.upsert_qa_thread(thread_id, title, body, len(texts),
                               _thread_jump_url(guild_id, thread_id), created)
        count += 1
    return count


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m ask.ingest_qa <questions_dir>")
        raise SystemExit(2)
    cfg = Config.from_env()
    store = Store(cfg.db_path)
    n = ingest_qa(store, sys.argv[1], cfg.guild_id)
    store.close()
    print(f"[ask] ingested {n} qa threads into {cfg.db_path}")


if __name__ == "__main__":
    main()
