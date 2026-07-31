import math
import re
import unicodedata
from datetime import datetime

W_SIM, W_ENG, W_REC = 0.5, 0.25, 0.25
# Trọng số nhánh keyword fallback (khi không có vector): ưu tiên từ khoá trùng,
# vẫn tính tương tác + độ mới. Không có bio → phần kw = 0 → hot ranking.
W_KW, W_KW_ENG, W_KW_REC = 0.5, 0.25, 0.25
TAU_HOURS = 72.0
_STOPWORDS = {
    "va", "la", "cua", "cho", "voi", "trong", "mot", "cac", "nhung", "khi",
    "the", "and", "the", "for", "with", "that", "this", "ban", "toi", "minh",
    "quan", "tam", "den", "ve", "hoc", "bai", "nao", "gi", "co", "duoc",
}
# Mức ép đa dạng của MMR (biến thể nhân): 0 = tắt, 1 = tối đa.
# 0.15 = thấp — gợi ý bám sát relevance, chỉ nén nhẹ bài gần trùng hẳn.
MMR_LAMBDA = 0.15


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _age_hours(created_at: str, now: datetime) -> float:
    dt = datetime.fromisoformat(created_at)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return max(0.0, (now - dt).total_seconds() / 3600)


def hybrid_scores(user_vec, items, now: datetime) -> list[dict]:
    engs = [math.log1p((p.get("hearts") or 0) + (p.get("comment_count") or 0))
            for _, _, p in items]
    max_eng = max(engs) if engs else 0.0
    out = []
    for (mid, vec, payload), raw_eng in zip(items, engs):
        sim = cosine(user_vec, vec) if user_vec is not None else 0.0
        eng = raw_eng / max_eng if max_eng else 0.0
        rec = math.exp(-_age_hours(payload["created_at"], now) / TAU_HOURS)
        if user_vec is not None:
            score = W_SIM * sim + W_ENG * eng + W_REC * rec
        else:
            score = 0.5 * eng + 0.5 * rec
        score = max(0.0, score)
        out.append({"message_id": mid, "vector": vec, "score": score,
                    "parts": {"sim": sim, "eng": eng, "rec": rec}})
    return out


def mmr_select(scored: list[dict], k: int, lam: float = MMR_LAMBDA) -> list[dict]:
    remaining = list(scored)
    picked: list[dict] = []
    while remaining and len(picked) < k:
        def mmr(c):
            penalty = max((cosine(c["vector"], p["vector"]) for p in picked), default=0.0)
            return c["score"] * (1 - lam * penalty)
        best = max(remaining, key=mmr)
        picked.append(best)
        remaining.remove(best)
    return picked


def _tokens(text: str) -> set[str]:
    # bỏ dấu để so khớp rộng hơn (VLM ~ vlm; "thị giác" khớp cả có/không dấu)
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_text.lower())
    return {w for w in words if len(w) >= 2 and w not in _STOPWORDS}


def recommend_keyword(store, user_id: str, k: int = 6) -> list[dict]:
    """Fallback thuần SQLite khi KHÔNG có vector store (Qdrant chết) hoặc user
    chưa có vector. Xếp hạng bằng từ khoá trùng giữa hồ sơ người dùng (bio +
    interest_summary) và (title + summary + tags) của bài, trộn tương tác + độ
    mới. Không bio → phần keyword = 0 → về hot ranking (tương tác + mới)."""
    user = store.get_user(user_id) or {}
    profile_text = f"{user.get('bio') or ''} {user.get('interest_summary') or ''}"
    query = _tokens(profile_text)
    bookmarked = set(store.list_bookmarks(user_id))
    now = datetime.utcnow()

    rows = [n for n in store.list_news() if n["message_id"] not in bookmarked]
    engs = [math.log1p((n.get("hearts") or 0) + (n.get("comment_count") or 0)) for n in rows]
    max_eng = max(engs) if engs else 0.0

    scored = []
    for n, raw_eng in zip(rows, engs):
        doc = _tokens(f"{n.get('title') or ''} {n.get('summary') or ''} "
                      f"{' '.join(n.get('tags') or [])}")
        overlap = len(query & doc)
        kw = overlap / len(query) if query else 0.0        # tỉ lệ từ khoá hồ sơ được đáp ứng
        eng = raw_eng / max_eng if max_eng else 0.0
        rec = math.exp(-_age_hours(n["created_at"], now) / TAU_HOURS)
        if query:
            score = W_KW * kw + W_KW_ENG * eng + W_KW_REC * rec
        else:
            score = 0.5 * eng + 0.5 * rec
        n = {kk: vv for kk, vv in n.items() if kk != "comments"}
        scored.append({**n, "score": round(max(0.0, score), 4),
                       "parts": {"sim": round(kw, 4), "eng": round(eng, 4), "rec": round(rec, 4)}})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]


def recommend(store, vs, user_id: str, k: int = 6) -> list[dict]:
    user = store.get_user(user_id)
    interest = (user.get("interest_summary") or "").strip() if user else ""
    user_vec = vs.get_user(user_id) if interest else None
    bookmarked = set(store.list_bookmarks(user_id))
    items = [(m, v, p) for m, v, p in vs.all_news() if m not in bookmarked]
    scored = hybrid_scores(user_vec, items, datetime.utcnow())
    results = []
    for s in mmr_select(scored, k=k):
        news = store.get_news(s["message_id"])
        if news is None:
            continue
        news.pop("comments", None)
        results.append({**news, "score": round(s["score"], 4),
                        "parts": {kk: round(vv, 4) for kk, vv in s["parts"].items()}})
    return results
