"""Retrieval cho /ask.

- search_qa: HYBRID — trộn 2 tín hiệu bằng RRF (Reciprocal Rank Fusion):
    (1) lexical: token-overlap (từ khoá trùng),
    (2) semantic: cosine giữa embedding câu hỏi và embedding tài liệu.
  Nếu không có embedder/embedding (offline hoặc chưa build index) → tự hạ cấp
  về lexical thuần. Trả ROW thật kèm nguồn để agent chỉ trả lời dựa trên đó.
- search_resources: keyword thuần (tài nguyên/lịch là dữ liệu có cấu trúc).
"""

import math
import re
import unicodedata

RRF_K = 60             # hằng số RRF chuẩn
SEM_FLOOR = 0.30       # ngưỡng cosine tối thiểu để tính là "liên quan"
_POOL = 10             # số ứng viên mỗi tín hiệu trước khi fuse

_STOP = {
    "la", "khi", "nao", "buoi", "tuan", "nay", "hoc", "gi", "co", "duoc",
    "khong", "ve", "cho", "toi", "minh", "ban", "cac", "mot", "va", "the",
    "o", "a", "cua", "voi", "trong", "de", "lam", "sao", "hoi",
}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", _norm(text))
            if len(w) >= 2 and w not in _STOP}


def cosine(a, b) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _snippet(body: str, query: set[str], limit: int = 500) -> str:
    """Trả đoạn khớp nhất, nhưng ĐỦ DÀI (500) để chứa trọn cách làm/dữ kiện —
    tránh cắt cụt khiến agent phải tự chế thông tin generic ngoài nguồn."""
    parts = [p.strip() for p in re.split(r"[\r\n]+|(?<=[.!?])\s+", body or "") if p.strip()]
    if not parts:
        return (body or "")[:limit]
    return max(parts, key=lambda p: len(query & tokens(p)))[:limit]


def rank(query: str, docs: list[dict], text_of, k: int = 5, min_overlap: int = 1) -> list[dict]:
    """Lexical: xếp docs theo số từ khoá trùng; loại doc 0 trùng."""
    q = tokens(query)
    if not q:
        return []
    scored = [(len(q & tokens(text_of(d))), d) for d in docs]
    scored = [(o, d) for o, d in scored if o >= min_overlap]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:k]]


def rrf_fuse(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """RRF: mỗi id nhận Σ 1/(k + hạng) qua từng danh sách xếp hạng."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for pos, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + pos)
    return scores


def hybrid_ids(query: str, qvec, cands: list[dict], k: int) -> list[str]:
    """Fuse lexical + semantic (RRF) → danh sách id theo thứ hạng."""
    lex = [c["_id"] for c in rank(query, cands, lambda c: c["_text"], k=_POOL)]
    sims = [(cosine(qvec, c["_emb"]), c["_id"]) for c in cands if c.get("_emb")]
    sims = [(s, i) for s, i in sims if s >= SEM_FLOOR]
    sims.sort(reverse=True)
    sem = [i for _, i in sims[:_POOL]]
    fused = rrf_fuse([lex, sem])
    return sorted(fused, key=lambda i: fused[i], reverse=True)[:k]


def _retrieve(query: str, cands: list[dict], embed, k: int) -> list[dict]:
    """Hybrid nếu có embedder chạy được; ngược lại hạ cấp lexical thuần."""
    qvec = None
    if embed is not None:
        try:
            qvec = embed(query)
        except Exception as exc:
            print(f"[ask] embed query failed, dùng lexical: {exc}")
    if qvec:
        by_id = {c["_id"]: c for c in cands}
        return [by_id[i] for i in hybrid_ids(query, qvec, cands, k) if i in by_id]
    return rank(query, cands, lambda c: c["_text"], k=k)


def search_qa(store, query: str, embed=None, k: int = 5) -> list[dict]:
    """Hybrid (lexical + semantic RRF) trên hỏi-đáp + bản tin."""
    emb_map = store.get_ask_embeddings() if embed is not None else {}
    cands = []
    for t in store.list_qa_threads():
        key = "qa:" + t["thread_id"]
        cands.append({"_id": key, "_emb": emb_map.get(key),
                      "_text": f"{t.get('title','')} {t.get('body','')}",
                      "source": "hỏi-đáp", "title": t.get("title") or "(thảo luận)",
                      "body": t.get("body", ""), "url": t.get("jump_url") or ""})
    for n in store.list_news():
        key = "news:" + n["message_id"]
        cands.append({"_id": key, "_emb": emb_map.get(key),
                      "_text": f"{n.get('title','')} {n.get('summary','')} {' '.join(n.get('tags') or [])}",
                      "source": "bản tin", "title": n.get("title") or "",
                      "body": n.get("summary") or n.get("content") or "", "url": n.get("jump_url") or ""})
    q = tokens(query)
    return [{"source": c["source"], "title": c["title"],
             "snippet": _snippet(c["body"], q), "url": c["url"]}
            for c in _retrieve(query, cands, embed, k)]


def search_resources(store, query: str, k: int = 6) -> list[dict]:
    """Keyword trên tài nguyên (record/slide/doc) + sự kiện lịch có link zoom."""
    out = []
    for r in rank(query, store.list_resources(),
                  lambda r: f"{r.get('title','')} {r.get('kind','')} {r.get('session_code','')}", k=k):
        out.append({"source": "tài nguyên", "kind": r.get("kind") or "doc",
                    "title": r.get("title") or "", "url": r.get("url") or "", "when": ""})
    for e in rank(query, [e for e in store.all_schedule_events() if e.get("zoom_url")],
                  lambda e: f"{e.get('title','')} {e.get('type','')} zoom", k=k):
        when = f"{e.get('date','')} {e.get('start') or ''}".strip()
        out.append({"source": "lịch", "kind": "zoom", "title": e.get("title") or "",
                    "url": e.get("zoom_url") or "", "when": when})
    return out[: k + k]


def search_news(news_items, emb_map, query, embed=None, k=20):
    """Hybrid search (lexical token-overlap + semantic cosine, RRF rerank) trên
    bản tin cộng đồng. CHỈ dùng heading (title) + tóm tắt (summary) — KHÔNG dùng
    comment hay nội dung body. Không có embedder → hạ cấp lexical."""
    cands = []
    for n in news_items:
        key = "news:" + n["message_id"]
        cands.append({**n, "_id": key, "_emb": emb_map.get(key),
                      "_text": f"{n.get('title', '')} {n.get('summary', '')}"})
    hits = _retrieve(query, cands, embed, k)
    return [{kk: vv for kk, vv in c.items() if not str(kk).startswith("_")} for c in hits]
