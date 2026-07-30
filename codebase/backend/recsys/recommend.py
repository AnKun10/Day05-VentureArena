import math
from datetime import datetime

W_SIM, W_ENG, W_REC = 0.5, 0.25, 0.25
TAU_HOURS = 72.0
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
