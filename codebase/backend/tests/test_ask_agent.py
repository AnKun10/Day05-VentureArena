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
    # runner trả AskResult trần → answer_question bọc thành (result, {})
    fake = lambda store, q: AskResult(action="answer", answer_vi="đáp", citations=["u"])
    r, meta = answer_question(store=None, question="hỏi gì đó", cfg=None, runner=fake)
    assert r.action == "answer" and r.answer_vi == "đáp" and r.citations == ["u"]
    assert meta == {}


def _map(monkeypatch, result: AskResult):
    from api.main import app, get_store
    monkeypatch.setattr(ask, "answer_question",
                        lambda store, q, cfg: (result, {"tool_calls": 1, "output_tokens": 42}))
    app.dependency_overrides[get_store] = lambda: object()
    try:
        return TestClient(app).post("/api/ask", json={"question": "Câu hỏi kiểm thử"}).json()
    finally:
        app.dependency_overrides.clear()


def test_api_ask_maps_answer(monkeypatch):
    body = _map(monkeypatch, AskResult(action="answer", answer_vi="Có workshop",
                                       citations=["https://d/1", "https://d/1"]))
    assert body["action"] == "answer" and body["confidence"] == 1.0
    assert body["citations"] == ["https://d/1"]           # dedup
    assert body["meta"]["tool_calls"] == 1 and "latency_ms" in body["meta"]


def test_api_ask_maps_no_info(monkeypatch):
    body = _map(monkeypatch, AskResult(action="no_info", answer_vi="Chưa có thông tin"))
    assert body["action"] == "no_info" and body["confidence"] == 0.0


def test_api_ask_maps_clarify_and_refuse(monkeypatch):
    b1 = _map(monkeypatch, AskResult(action="clarify", answer_vi="Bạn hỏi buổi nào?"))
    assert b1["action"] == "clarify" and b1["confidence"] == 0.0
    b2 = _map(monkeypatch, AskResult(action="refuse", answer_vi="Mình không đổi điểm được"))
    assert b2["action"] == "refuse" and b2["confidence"] == 0.0
