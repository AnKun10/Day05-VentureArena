"""Embed-once index cho semantic search của /ask.

Nhúng qa_threads + news vào bảng ask_embeddings (bỏ qua doc đã có → chạy lại
an toàn, chỉ nhúng phần mới). Semantic của search_qa đọc từ bảng này.

Dùng:  python -m ask.embed_index
"""

from ingest.config import Config
from ingest.store import Store
from recsys.embedder import embed_texts


def _candidates(store: Store) -> list[tuple[str, str]]:
    cands = []
    for t in store.list_qa_threads():
        cands.append(("qa:" + t["thread_id"],
                      f"{t.get('title','')}\n{(t.get('body') or '')[:800]}"))
    for n in store.list_news():
        cands.append(("news:" + n["message_id"],
                      f"{n.get('title','')}\n{n.get('summary') or ''}\n"
                      f"Tags: {', '.join(n.get('tags') or [])}"))
    return cands


def build_index(store: Store, cfg, embedder=embed_texts, batch: int = 64) -> int:
    have = set(store.get_ask_embeddings())
    todo = [(key, text) for key, text in _candidates(store) if key not in have]
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        vecs = embedder([text for _, text in chunk], cfg)
        for (key, _), vec in zip(chunk, vecs):
            store.save_ask_embedding(key, vec)
    return len(todo)


def main() -> None:
    cfg = Config.from_env()
    store = Store(cfg.db_path)
    n = build_index(store, cfg)
    store.close()
    print(f"[ask] embedded {n} new docs into ask_embeddings ({cfg.db_path})")


if __name__ == "__main__":
    main()
