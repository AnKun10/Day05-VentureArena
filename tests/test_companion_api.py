import json
import sqlite3

from fastapi.testclient import TestClient

import app


def test_ask_returns_a_citation_and_queues_unsupported_questions(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "schedule.yaml").write_text("deadline: Hạn nộp spec là 23:59 ngày 1.", encoding="utf-8")
    queue = tmp_path / "queue.sqlite3"
    monkeypatch.setattr(app, "DATA_DIRECTORY", data)
    monkeypatch.setattr(app, "TRACE_DIRECTORY", tmp_path / "traces")
    monkeypatch.setattr(app, "QUEUE_PATH", queue)
    monkeypatch.setattr(app, "model_excerpt", lambda *_: ("Hạn nộp spec là 23:59 ngày 1.", "gemini"))
    client = TestClient(app.app)

    answered = client.post("/api/ask", json={"question": "Hạn nộp spec là khi nào?"})
    refused = client.post("/api/ask", json={"question": "Có được gia hạn deadline không?", "class_name": "Lab-D305"})

    assert answered.json()["citations"] == ["schedule.yaml"]
    assert "provider" not in answered.json()
    assert refused.json()["action"] == "refuse"
    assert json.loads(next((tmp_path / "traces").iterdir()).read_text(encoding="utf-8"))["provider"] == "gemini"
    with sqlite3.connect(queue) as connection:
        assert connection.execute("SELECT question, class_name FROM unanswered_questions").fetchone() == (
            "Có được gia hạn deadline không?", "Lab-D305"
        )
