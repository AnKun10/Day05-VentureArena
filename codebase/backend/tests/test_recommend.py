from datetime import datetime

from recsys.recommend import cosine, hybrid_scores, mmr_select

NOW = datetime(2026, 7, 31, 12, 0, 0)


def item(mid, vec, hearts=0, comments=0, hours_ago=0):
    from datetime import timedelta
    return (mid, vec, {"message_id": mid, "hearts": hearts, "comment_count": comments,
                       "created_at": (NOW - timedelta(hours=hours_ago)).isoformat()})


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0


def test_scores_without_user_vec_is_eng_plus_rec():
    scored = hybrid_scores(None, [item("1", [1, 0], hearts=10, hours_ago=0),
                                  item("2", [0, 1], hearts=0, hours_ago=200)], NOW)
    by = {s["message_id"]: s for s in scored}
    assert by["1"]["parts"]["sim"] == 0.0
    assert by["1"]["score"] > by["2"]["score"]          # nhiều tim + mới hơn thắng
    assert by["1"]["parts"]["eng"] == 1.0               # log-chuẩn hoá theo max


def test_scores_with_user_vec_prefers_similar():
    scored = hybrid_scores([1, 0], [item("sim", [1, 0]), item("far", [0, 1])], NOW)
    by = {s["message_id"]: s for s in scored}
    assert by["sim"]["parts"]["sim"] == 1.0 and by["far"]["parts"]["sim"] == 0.0
    assert by["sim"]["score"] > by["far"]["score"]


def test_recency_decay():
    scored = hybrid_scores(None, [item("new", [1, 0], hours_ago=0),
                                  item("old", [1, 0], hours_ago=72)], NOW)
    by = {s["message_id"]: s for s in scored}
    assert by["new"]["parts"]["rec"] == 1.0
    assert 0.35 < by["old"]["parts"]["rec"] < 0.38      # e^-1 ≈ 0.3679


def test_mmr_diversifies():
    # 2 bài gần trùng vector, 1 bài khác hẳn: top-2 phải chứa bài khác hẳn
    scored = hybrid_scores([1, 0, 0], [item("a1", [1, 0, 0], hearts=10),
                                       item("a2", [0.999, 0.04, 0], hearts=9),
                                       item("b", [0, 1, 0], hearts=8)], NOW)
    picked = [s["message_id"] for s in mmr_select(scored, k=2, lam=0.7)]
    assert picked[0] == "a1" and picked[1] == "b"


def test_negative_sim_ranks_below_positive():
    # cosine thô hiển thị vẫn giữ dấu; sau min-max sim, bài anti-tương-quan luôn
    # xếp dưới bài trùng hướng và không bao giờ được sim ưu ái.
    scored = hybrid_scores([1, 0], [item("anti", [-1, 0]), item("pos", [1, 0])], NOW)
    by = {s["message_id"]: s for s in scored}
    assert by["anti"]["parts"]["sim"] == -1.0          # hiển thị cosine thô
    assert by["anti"]["score"] < by["pos"]["score"]
    picked = [s["message_id"] for s in mmr_select(scored, k=2)]
    assert picked == ["pos", "anti"]                   # anti không bao giờ vượt pos


def test_blank_profile_gets_no_personalization(tmp_path):
    from ingest.store import Store
    from recsys.vectorstore import VectorStore
    from recsys.recommend import recommend
    from ingest.models import NewsEnrichment
    from tests.test_store import make_post
    s = Store(str(tmp_path / "t.db"))
    vs = VectorStore(str(tmp_path / "q"), dim=4)
    s.upsert_user("u1", "An", bio="cũ")
    vs.upsert_user("u1", [1, 0, 0, 0])          # vector cũ còn trong Qdrant
    s.save_profile("u1", "h", "", [])            # profile đã bị xoá trắng
    s.upsert_post(make_post(mid="1"))
    s.save_enrichment("1", NewsEnrichment(summary_vi="x", tags=["ai-model"],
                                          image_query="q"), "placeholder", "v1", "t")
    vs.upsert_news("1", [1, 0, 0, 0], {"message_id": "1", "tags": ["ai-model"],
                                       "created_at": "2026-07-31T08:00:00",
                                       "hearts": 5, "comment_count": 0})
    recs = recommend(s, vs, "u1", k=3)
    assert recs and all(r["parts"]["sim"] == 0.0 for r in recs)
