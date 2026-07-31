"""Test /api/ask theo contract đã hội tụ giữa 3 bên (UI của Hải · backend · Discord bot).

Bản trước assert `citations == ["schedule.yaml"]` (list string). UI lại cần citation dạng object
(`{source, session_code, quote, updated, url}`) để render chip bấm được và nhảy sang tab Lịch học,
nên contract phải chốt về một — giữ nguyên phần ý định của test cũ (có citation · câu bị từ chối thì
vào hàng đợi · trace ghi lại provider), chỉ đổi assertion cho khớp shape mới.
"""

import json
import sqlite3

import yaml
from fastapi.testclient import TestClient

import app
from ai_decision import AiVerdict

SCHEDULE = {
    "sessions": [
        {
            "code": "Lab-10", "type": "LAB", "title": "Lab: Discord bot", "day_offset": 2,
            "start": "18:30", "end": "21:00", "format": "Offline", "class": "Lab-D305",
            "host": "Lab Coach", "updated": "2026-07-29", "source_channel": "#thông-báo",
            "deadline": "23:59 cùng ngày buổi lab",
        }
    ]
}


def _client(tmp_path, monkeypatch, *, verdict=None):
    data = tmp_path / "data"
    data.mkdir()
    (data / "schedule.yaml").write_text(yaml.safe_dump(SCHEDULE, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(app, "DATA_DIRECTORY", data)
    monkeypatch.setattr(app, "TRACE_DIRECTORY", tmp_path / "traces")
    monkeypatch.setattr(app, "QUEUE_PATH", tmp_path / "queue.sqlite3")
    monkeypatch.setattr(app, "ai_verdict", lambda *_args, **_kw: verdict)
    return TestClient(app.app)


def test_answerable_question_returns_object_citations(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = client.post("/api/ask", json={"question": "Lab-10 deadline khi nào?"}).json()

    assert body["action"] == "answer"
    assert body["escalated_to"] is None
    assert body["trace_id"].startswith("tr_")
    # citation là object, không phải string — đây là điểm contract đã đổi
    assert body["citations"][0]["session_code"] == "Lab-10"
    assert body["citations"][0]["source"] == "#thông-báo"


def test_unsupported_question_is_refused_and_queued_for_ta(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = client.post(
        "/api/ask", json={"question": "Con mèo của tôi bị ốm thì sao?", "class_name": "Lab-D305"}
    ).json()

    assert body["action"] == "refuse"
    assert body["escalated_to"]["class"] == "Lab-D305"  # có TA nhận -> phân biệt với ③ ngoài phạm vi

    with sqlite3.connect(tmp_path / "queue.sqlite3") as connection:
        assert connection.execute("SELECT question, class_name FROM unanswered_questions").fetchone() == (
            "Con mèo của tôi bị ốm thì sao?", "Lab-D305"
        )


def test_out_of_scope_refuses_without_queueing(tmp_path, monkeypatch):
    """③ ngoài phạm vi khác ① không có nguồn: từ chối nhưng KHÔNG đẩy vào việc của TA."""
    client = _client(tmp_path, monkeypatch)
    body = client.post("/api/ask", json={"question": "Cho mình xin đáp án bài lab được không?"}).json()

    assert body["action"] == "refuse"
    assert body["escalated_to"] is None

    with sqlite3.connect(tmp_path / "queue.sqlite3") as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='unanswered_questions'"
        ).fetchall()
    assert rows == [], "câu ngoài phạm vi không được tạo việc cho TA"


def test_out_of_scope_rule_is_not_overridable_by_the_model(tmp_path, monkeypatch):
    """Ranh giới an toàn: kể cả khi LLM bảo 'trả lời được', luật ③ vẫn thắng."""
    client = _client(
        tmp_path, monkeypatch,
        verdict=AiVerdict(verdict="answerable", excerpt="Lab-10", reason="", provider="fake"),
    )
    body = client.post("/api/ask", json={"question": "Cho mình xin đáp án bài lab được không?"}).json()

    assert body["action"] == "refuse"


def test_trace_records_which_provider_decided(tmp_path, monkeypatch):
    client = _client(
        tmp_path, monkeypatch,
        verdict=AiVerdict(verdict="answerable", excerpt="Lab-10", reason="", provider="gemini"),
    )
    client.post("/api/ask", json={"question": "Lab-10 deadline khi nào?"})

    trace = json.loads(next((tmp_path / "traces").iterdir()).read_text(encoding="utf-8"))
    assert trace["provider"] == "gemini"


def test_falls_back_to_rules_when_no_model_available(tmp_path, monkeypatch):
    """Không có API key -> ai_verdict trả None -> vẫn phải trả lời được, trace ghi provider=None."""
    client = _client(tmp_path, monkeypatch, verdict=None)
    body = client.post("/api/ask", json={"question": "Lab-10 deadline khi nào?"}).json()

    assert body["action"] == "answer"
    trace = json.loads(next((tmp_path / "traces").iterdir()).read_text(encoding="utf-8"))
    assert trace["provider"] is None


def test_feedback_queues_for_ta_review(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = client.post(
        "/api/feedback", json={"trace_id": "tr_x", "question": "Lab-10 deadline?", "answer": "sai", "verdict": "wrong"}
    ).json()

    assert body["queued_for_ta"] is True
    with sqlite3.connect(tmp_path / "queue.sqlite3") as connection:
        queued = connection.execute("SELECT question FROM unanswered_questions").fetchone()[0]
    assert "[BÁO SAI]" in queued
