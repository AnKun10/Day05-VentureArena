import json

from fastapi.testclient import TestClient

import app


def test_ask_answers_with_citation_and_refuses_unsupported_questions(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "schedule.yaml").write_text("deadline: Hạn nộp spec là 23:59 ngày 1.", encoding="utf-8")
    monkeypatch.setattr(app, "DATA_DIRECTORY", data)
    monkeypatch.setattr(app, "TRACE_DIRECTORY", tmp_path / "traces")
    monkeypatch.setattr(app, "model_excerpt", lambda *_: ("Hạn nộp spec là 23:59 ngày 1.", "gemini"))
    client = TestClient(app.app)

    answered = client.post("/api/ask", json={"question": "Hạn nộp spec là khi nào?"})
    refused = client.post("/api/ask", json={"question": "Có được gia hạn deadline không?"})

    assert answered.json()["citations"] == ["schedule.yaml"]
    assert "provider" not in answered.json()
    assert refused.json()["action"] == "refuse"
    assert "#hỏi-đáp" in refused.json()["answer"]          # từ chối chỉ hướng kênh, không còn queue TA
    assert json.loads(next((tmp_path / "traces").iterdir()).read_text(encoding="utf-8"))["provider"] == "gemini"
