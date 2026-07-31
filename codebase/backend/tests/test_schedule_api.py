from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app, get_store
from ingest.schedule import build_schedule, recurring_sessions
from ingest.store import Store

SET4 = {"cohort": "4", "lt_room": "D302", "lab_room": "D305"}


def test_recurring_skips_sunday_and_slots():
    # 2026-07-27 (T2) .. 2026-08-02 (CN)
    items = recurring_sessions(SET4, "2026-07-27", "2026-08-02")
    assert len(items) == 12                                     # 6 ngày × 2 buổi
    dates = {i["date"] for i in items}
    assert "2026-08-02" not in dates                            # CN nghỉ
    lab = next(i for i in items if i["date"] == "2026-07-27" and i["type"] == "LAB")
    assert (lab["start"], lab["end"], lab["location"]) == ("09:00", "13:00", "D305")
    lt = next(i for i in items if i["date"] == "2026-07-27" and i["type"] == "LT")
    assert (lt["start"], lt["end"], lt["location"]) == ("14:00", "18:00", "D302")
    assert lab["materials"][0]["url"].startswith("https://codelabs.vlearn.dev")
    assert lt["materials"][0]["url"] == "https://vlearn.dev"


def test_build_schedule_merges_evening_and_overrides_host():
    events = [
        {"type": "WS", "title": "Workshop 3", "date": "2026-07-27", "start": "20:00",
         "end": "22:00", "cohort": "all", "format": "Zoom", "zoom_url": "https://z/1",
         "host": "Diễn giả A", "session_code": "WS-3", "jump_url": "https://d/1",
         "location": None},
        {"type": "LT", "title": "LT hôm nay", "date": "2026-07-27", "start": None,
         "end": None, "cohort": "4", "format": "Offline", "zoom_url": None,
         "host": "Cô B", "session_code": None, "jump_url": None, "location": None},
    ]
    resources = [{"message_id": "9", "kind": "record", "title": "Record WS-3",
                  "session_code": "WS-3", "author": "BTC", "url": "https://r/1",
                  "created_at": "2026-07-28T00:00:00"}]
    items = build_schedule(SET4, events, resources, "2026-07-27", "2026-07-27")
    assert len(items) == 3                                      # LAB + LT + WS (LT event chỉ override)
    lt = next(i for i in items if i["type"] == "LT")
    assert lt["host"] == "Cô B"                                 # override từ thông báo
    ws = next(i for i in items if i["type"] == "WS")
    assert ws["zoom_url"] == "https://z/1"
    assert any(m["url"] == "https://r/1" for m in ws["materials"])  # resource WS-3 gắn vào
    assert items[-1]["type"] == "WS"                            # sort theo giờ


def test_build_schedule_dedups_repeated_announcements():
    events = [
        {"type": "OH", "title": "Office Hours 02", "date": "2026-07-27", "start": "20:00",
         "end": None, "cohort": "all", "format": "Zoom", "zoom_url": None, "host": None,
         "session_code": None, "jump_url": None, "location": None},
        {"type": "OH", "title": "Office Hours 02 (nhắc lại)", "date": "2026-07-27",
         "start": "20:00", "end": "21:00", "cohort": "all", "format": "Zoom",
         "zoom_url": "https://z/oh2", "host": "TA A", "session_code": None,
         "jump_url": None, "location": None},
    ]
    items = build_schedule(SET4, events, [], "2026-07-27", "2026-07-27")
    ohs = [i for i in items if i["type"] == "OH"]
    assert len(ohs) == 1 and ohs[0]["zoom_url"] == "https://z/oh2"


def test_lab_lt_partial_updates_both_apply():
    events = [
        {"type": "LT", "title": "x", "date": "2026-07-27", "start": None, "end": None,
         "cohort": "4", "format": "Offline", "zoom_url": None, "host": "Cô B",
         "session_code": None, "jump_url": None, "location": None},
        {"type": "LT", "title": "y", "date": "2026-07-27", "start": None, "end": None,
         "cohort": "4", "format": "Offline", "zoom_url": None, "host": None,
         "session_code": None, "jump_url": None, "location": "D999"},
    ]
    items = build_schedule(SET4, events, [], "2026-07-27", "2026-07-27")
    lt = next(i for i in items if i["type"] == "LT")
    assert lt["host"] == "Cô B" and lt["location"] == "D999"
    assert len(items) == 2                                  # không sinh block LT thừa


def _client(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "t.db"))
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app), store


def test_settings_roundtrip_and_schedule_uses_them(tmp_path, monkeypatch):
    client, store = _client(tmp_path, monkeypatch)
    assert client.get("/api/users/newbie/settings").json() == SET4     # ensure_user + defaults
    r = client.put("/api/users/newbie/settings",
                   json={"cohort": "3", "lt_room": "D201", "lab_room": "D202"})
    assert r.json()["cohort"] == "3"
    day = client.get("/api/schedule", params={"user_id": "newbie",
                                              "from": "2026-07-27", "to": "2026-07-27"}).json()
    lab = next(i for i in day if i["type"] == "LAB")
    assert lab["location"] == "D202" and lab["cohort"] == "3"


def test_schedule_cohort_filter_on_events(tmp_path, monkeypatch):
    client, store = _client(tmp_path, monkeypatch)
    store.save_schedule_extraction("m1", [
        {"type": "OH", "title": "OH K3", "date": "2026-07-27", "start": "19:00",
         "end": "20:00", "cohort": "3", "format": "Zoom"},
        {"type": "WS", "title": "WS chung", "date": "2026-07-27", "start": "20:00",
         "end": "21:00", "cohort": "all", "format": "Zoom"},
    ], "tr")
    day = client.get("/api/schedule", params={"cohort": "4",
                                              "from": "2026-07-27", "to": "2026-07-27"}).json()
    titles = [i["title"] for i in day if i["type"] in ("OH", "WS")]
    assert titles == ["WS chung"]
