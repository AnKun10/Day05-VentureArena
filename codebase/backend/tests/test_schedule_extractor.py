import json
from ingest.agents import ScheduleEvent, ScheduleExtraction, extract_schedule
from ingest.config import Config


def _post(mid="3001", channel="thong-bao:4"):
    return {"message_id": mid, "title": "THÔNG BÁO", "content": "Workshop 20:00",
            "channel": channel, "created_at": "2026-07-30T07:00:00+00:00",
            "jump_url": "https://d/3001"}


def test_extract_with_injected_runner_writes_trace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake = ScheduleExtraction(events=[ScheduleEvent(
        type="WS", title="Workshop 3", date="2026-07-30", start="20:00", end="22:00",
        cohort="4", format="Zoom", zoom_url="https://zoom/x", host="Diễn giả A")])
    captured = {}
    def runner(text):
        captured["text"] = text
        return fake
    extraction, trace_id = extract_schedule(_post(), Config(), runner=runner)
    assert extraction.events[0].type == "WS" and trace_id
    assert "cohort 4" in captured["text"] or "thong-bao:4" in captured["text"]
    assert "2026-07-30" in captured["text"]                      # ngày đăng có trong input
    trace = json.loads((tmp_path / "eval/traces/schedule/3001.json").read_text(encoding="utf-8"))
    assert trace["output"]["events"][0]["title"] == "Workshop 3"


def test_extract_empty_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    extraction, _ = extract_schedule(_post(mid="3002"), Config(),
                                     runner=lambda t: ScheduleExtraction())
    assert extraction.events == []
