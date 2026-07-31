"""Test agent /ask: formatter + mapping AskResult→AskResponse (offline, fake runner)."""

from fastapi.testclient import TestClient

from ask import AskResult, answer_question
from ask.agent import _format_qa, _format_resources
import ask


def test_format_qa_empty_and_nonempty():
    assert "Không tìm thấy" in _format_qa([])
    s = _format_qa([{"source": "hỏi-đáp", "title": "Tải slide", "snippet": "vào vlearn",
                     "url": "https://d/1"}])
    assert "hỏi-đáp" in s and "Tải slide" in s and "https://d/1" in s


def test_format_resources_with_when():
    s = _format_resources([{"source": "lịch", "kind": "zoom", "title": "WS1",
                            "url": "https://z/1", "when": "2026-07-24 20:00"}])
    assert "zoom" in s and "2026-07-24 20:00" in s and "https://z/1" in s


def test_answer_question_uses_injected_runner():
    fake = lambda store, q: AskResult(found=True, answer_vi="đáp", citations=["u"])
    r = answer_question(store=None, question="hỏi gì đó", cfg=None, runner=fake)
    assert r.found and r.answer_vi == "đáp" and r.citations == ["u"]


def test_api_ask_maps_found_true(monkeypatch):
    from api.main import app, get_store
    monkeypatch.setattr(ask, "answer_question",
                        lambda store, q, cfg: AskResult(found=True, answer_vi="Có workshop tối nay",
                                                        citations=["https://d/1"]))
    app.dependency_overrides[get_store] = lambda: object()
    try:
        r = TestClient(app).post("/api/ask", json={"question": "Khi nào có workshop?"})
        body = r.json()
        assert body["action"] == "answer" and body["confidence"] == 1.0
        assert body["citations"] == ["https://d/1"]
    finally:
        app.dependency_overrides.clear()


def test_api_ask_maps_no_info(monkeypatch):
    from api.main import app, get_store
    monkeypatch.setattr(ask, "answer_question",
                        lambda store, q, cfg: AskResult(found=False,
                                                        answer_vi="Mình chưa có thông tin", citations=[]))
    app.dependency_overrides[get_store] = lambda: object()
    try:
        r = TestClient(app).post("/api/ask", json={"question": "Câu hỏi vu vơ"})
        body = r.json()
        assert body["action"] == "no_info" and body["confidence"] == 0.0
    finally:
        app.dependency_overrides.clear()
