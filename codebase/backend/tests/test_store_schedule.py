from ingest.store import Store


def test_users_settings_migration_and_defaults(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    assert s.get_settings("nobody") == {"cohort": "4", "lt_room": "D302", "lab_room": "D305"}
    u = s.ensure_user("an.k")
    assert u["user_id"] == "an.k" and u["cohort"] == "4"
    s.set_settings("an.k", "3", "D201", "D202")
    assert s.get_settings("an.k") == {"cohort": "3", "lt_room": "D201", "lab_room": "D202"}
    assert s.ensure_user("an.k")["cohort"] == "3"          # ensure không ghi đè


def test_users_migration_on_old_db(tmp_path):
    import sqlite3
    p = str(tmp_path / "old.db")
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE users(user_id TEXT PRIMARY KEY, name TEXT, bio TEXT DEFAULT '',"
                 " bio_source TEXT DEFAULT 'manual', bio_hash TEXT, interest_summary TEXT,"
                 " interest_tags TEXT)")
    conn.execute("INSERT INTO users(user_id, name) VALUES('u1','U1')")
    conn.commit(); conn.close()
    s = Store(p)
    assert s.get_settings("u1") == {"cohort": "4", "lt_room": "D302", "lab_room": "D305"}


def test_schedule_extraction_once_and_query(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    events = [
        {"type": "WS", "title": "Workshop 3", "date": "2026-07-30", "start": "20:00",
         "end": "22:00", "cohort": "all", "format": "Zoom", "zoom_url": "https://zoom/x",
         "host": "Diễn giả A", "session_code": "WS-3", "jump_url": "https://d/1"},
        {"type": "OH", "title": "Office hour", "date": "2026-07-31", "start": None,
         "end": None, "cohort": "3", "format": "Zoom"},
    ]
    assert s.is_schedule_extracted("m1") is False
    assert s.save_schedule_extraction("m1", events, "tr1") == 2
    assert s.is_schedule_extracted("m1") is True
    assert s.save_schedule_extraction("m1", events, "tr1") == 0     # extract-once
    rows = s.list_schedule_events("4", "2026-07-29", "2026-07-31")
    assert [r["title"] for r in rows] == ["Workshop 3"]             # cohort 3 bị lọc
    rows3 = s.list_schedule_events("3", "2026-07-29", "2026-07-31")
    assert len(rows3) == 2 and rows3[0]["date"] == "2026-07-30"


def test_extraction_with_zero_events_still_marked(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    assert s.save_schedule_extraction("m2", [], "tr2") == 0
    assert s.is_schedule_extracted("m2") is True
