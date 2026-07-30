# Schedule + Settings + Bot Commands — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lịch học thật (Lab sáng 9-13 + LT chiều 14-18 rule-based T2–T7; buổi tối do agent trích từ 3 kênh thông-báo), settings server-side gắn user (cohort/phòng), page Settings + rewire Lịch học, bot `/schedule` `/digest` `/hub` format mới.

**Architecture:** Store mở rộng (users settings cols, schedule_events + schedule_extracted); ManifestSource đọc thêm 3 kênh announcements → channel `thong-bao:{3|4|all}`; agent `schedule_extractor` extract-once từng message; `ingest/schedule.py` thuần sinh recurring + merge; API `/api/schedule`, `/api/users/{id}/settings`; UI nâng user state lên App + SettingsPage + CalendarPage rewire; bot formatter thuần test được. Spec: `docs/superpowers/specs/2026-07-31-schedule-settings-bot-commands-design.md`.

**Tech Stack:** như hiện trạng (openai-agents, FastAPI, sqlite3, React UI, discord bot của Nghĩa).

## Global Constraints

- Backend cwd `codebase/backend`, python `.venv/Scripts/python.exe`; UI cwd `codebase/ui`; bot code `codebase/bot/companion_discord`; root tests chạy từ repo root (`pytest.ini` pythonpath có backend + bot).
- Python 3.10 compat: KHÔNG dùng `datetime.UTC` (dùng `timezone.utc`), không dùng `fromisoformat` với hậu tố `Z`.
- `/ask` (bot + backend app.py) KHÔNG được đụng.
- Deviation đã duyệt so với spec §2.1: `schedule_events` dùng `id INTEGER PRIMARY KEY AUTOINCREMENT` + cột `message_id` (1 thông báo có thể chứa NHIỀU buổi) và bảng đánh dấu riêng `schedule_extracted(message_id TEXT PRIMARY KEY, extracted_at TEXT, trace_id TEXT, event_count INTEGER)` thay cho `announce_state`.
- Recurring: T2–T7 (weekday 0–5), CN nghỉ; Lab 09:00–13:00 type `LAB`; Lý thuyết 14:00–18:00 type `LT`; format Offline.
- Materials tĩnh: LAB → `{"label": "Tài liệu hướng dẫn", "url": "https://codelabs.vlearn.dev/codelab", "kind": "doc"}`; LT → `{"label": "Slide trên VLearn", "url": "https://vlearn.dev", "kind": "slide"}`.
- Settings defaults: cohort `'4'`, lt_room `'D302'`, lab_room `'D305'`.
- Bước gọi API thật được ghi rõ (`.env` đã có key); unit tests offline hoàn toàn.
- Commit trên dev/An, message tiếng Anh, KHÔNG chứa ký tự `"` (PowerShell here-string), kết thúc:

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

---

### Task 1: Store — settings + schedule tables

**Files:**
- Modify: `codebase/backend/ingest/store.py`
- Test: `codebase/backend/tests/test_store_schedule.py`

**Interfaces:**
- Consumes: `Store` hiện có (users table + `_now()` + PRAGMA-migration idiom của `embedded_at`).
- Produces:
  - Migration users (PRAGMA table_info + ALTER, DB cũ mở được): `cohort TEXT DEFAULT '4'`, `lt_room TEXT DEFAULT 'D302'`, `lab_room TEXT DEFAULT 'D305'`. LƯU Ý: ALTER TABLE ADD COLUMN với DEFAULT áp cho hàng CŨ trong SQLite chỉ khi default là hằng — dùng `ALTER TABLE users ADD COLUMN cohort TEXT DEFAULT '4'` là đủ.
  - SCHEMA thêm:

```sql
CREATE TABLE IF NOT EXISTS schedule_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT, type TEXT, title TEXT, date TEXT, start TEXT, end TEXT,
  cohort TEXT, format TEXT, zoom_url TEXT, host TEXT, location TEXT,
  session_code TEXT, jump_url TEXT
);
CREATE TABLE IF NOT EXISTS schedule_extracted(
  message_id TEXT PRIMARY KEY, extracted_at TEXT, trace_id TEXT,
  event_count INTEGER DEFAULT 0
);
```

  - Methods:
    - `ensure_user(user_id: str, name: str | None = None) -> dict` — INSERT OR IGNORE (name mặc định = user_id) rồi trả `get_user`.
    - `get_settings(user_id) -> dict` — `{cohort, lt_room, lab_room}` (user không tồn tại → defaults `{'4','D302','D305'}` KHÔNG tự tạo).
    - `set_settings(user_id, cohort, lt_room, lab_room) -> None`.
    - `is_schedule_extracted(message_id) -> bool`.
    - `save_schedule_extraction(message_id, events: list[dict], trace_id: str) -> int` — insert từng event (keys như cột; thiếu → None) + upsert `schedule_extracted` với event_count; trả số event. Idempotent: nếu đã extracted → return 0, KHÔNG insert đôi.
    - `list_schedule_events(cohort: str, date_from: str, date_to: str) -> list[dict]` — `date BETWEEN ? AND ? AND cohort IN (?, 'all')` sort (date, start NULLS LAST → dùng `ORDER BY date, COALESCE(start,'99:99')`).

- [ ] **Step 1: Failing tests** — `tests/test_store_schedule.py`:

```python
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
```

- [ ] **Step 2: FAIL → Step 3: Implement** (theo Interfaces; đặt migration users cạnh migration `embedded_at`; methods cuối class, mirror style hiện có).
- [ ] **Step 4: `pytest tests/test_store_schedule.py -v` PASS; full suite PASS.**
- [ ] **Step 5: Commit** — `feat(schedule): store settings columns and schedule event tables`.

---

### Task 2: ManifestSource — 3 kênh thông báo

**Files:**
- Modify: `codebase/backend/ingest/sources/manifest.py`
- Modify: `codebase/backend/tests/test_sources_manifest.py`

**Interfaces:**
- Produces: manifest text channels `announcements` → RawPost channel `thong-bao:all`, `cohort_3_common_announcements` → `thong-bao:3`, `cohort_4_common_announcements` → `thong-bao:4`. Dùng lại `split_header` (author/ts/clean content); bỏ message rỗng/welcome; title = dòng đầu [:120]; checkpoint theo từng channel key (`since.get("thong-bao:3", 0)`…).
- Map nội bộ: `_ANNOUNCE_MAP = {"announcements": "thong-bao:all", "cohort_3_common_announcements": "thong-bao:3", "cohort_4_common_announcements": "thong-bao:4"}` — xử lý trong `fetch` như nhánh `_RESOURCE_SOURCE` (tái dùng `_resource_post`-style builder mới `_announce_post(message, channel)`; giống resource nhưng channel truyền vào, KHÔNG lọc mention-only — thông báo có thể ngắn).

- [ ] **Step 1: Failing tests** — thêm vào `tests/test_sources_manifest.py`: mở rộng `MANIFEST` fixture thêm channel:

```python
        {
            "source_name": "cohort_4_common_announcements",
            "type": "text",
            "messages": [
                {"id": "2050", "content": "Vonhatcuong—14:15 23/7/26lúc 14:15 Thứ Năm, 23 tháng 7, 2026THÔNG BÁO LỊCH WORKSHOP 3\nThời gian: 20:00 tối nay",
                 "jump_url": "https://discord.com/x/2050", "created_at": "2026-07-23T07:15:00.000Z"},
            ],
        },
```

và tests:

```python
def test_announcement_channels_mapped_with_cohort_suffix(tmp_path):
    posts = ManifestSource(write_manifest(tmp_path)).fetch(since={})
    ann = [p for p in posts if p.channel.startswith("thong-bao")]
    assert len(ann) == 1
    p = ann[0]
    assert p.channel == "thong-bao:4"
    assert p.author == "Vonhatcuong"
    assert p.title.startswith("THÔNG BÁO LỊCH WORKSHOP 3")
    assert p.created_at == "2026-07-23T07:15:00.000+00:00"


def test_announcement_respects_checkpoint(tmp_path):
    src = ManifestSource(write_manifest(tmp_path))
    posts = src.fetch(since={"thong-bao:4": 3000})
    assert not any(p.channel == "thong-bao:4" for p in posts)
```

(cập nhật `test_maps_channels_and_skips_unrelated`: set kênh giờ gồm `{"chia-se","bai-hoc","tai-nguyen","thong-bao:4"}`.)

- [ ] **Step 2: FAIL → Step 3: Implement.** Step 4: manifest tests + full suite PASS.
- [ ] **Step 5: Commit** — `feat(schedule): manifest source reads announcement channels`.

---

### Task 3: Agent schedule_extractor

**Files:**
- Create: `codebase/backend/ingest/prompts/schedule_v1.py`
- Modify: `codebase/backend/ingest/prompts/__init__.py` (thêm `SCHEDULE_V1`, `SCHEDULE_VERSION = "v1"`, registry `SCHEDULE_PROMPTS`)
- Create: `codebase/backend/ingest/agents/schedule_extractor.py`
- Modify: `codebase/backend/ingest/agents/__init__.py` (re-export `extract_schedule`, `ScheduleExtraction`, `ScheduleEvent`)
- Test: `codebase/backend/tests/test_schedule_extractor.py`

**Interfaces:**
- Produces:

```python
class ScheduleEvent(BaseModel):
    type: Literal["LAB", "LT", "WS", "OH", "MD", "OTHER"]
    title: str
    date: str                      # YYYY-MM-DD
    start: str | None = None       # HH:MM
    end: str | None = None
    cohort: Literal["3", "4", "all"] = "all"
    format: Literal["Zoom", "Offline"] = "Zoom"
    zoom_url: str | None = None
    host: str | None = None
    location: str | None = None

class ScheduleExtraction(BaseModel):
    events: list[ScheduleEvent] = Field(default_factory=list)
```

- `extract_schedule(post: dict, cfg, runner=None) -> tuple[ScheduleExtraction, str]` — post keys `message_id, title, content, channel, created_at, jump_url`; input_text = kênh (kèm hint cohort từ suffix `:3`/`:4`) + ngày đăng (`created_at[:10]`) + nội dung; agent (model `cfg.enrich_model`, instructions SCHEDULE_V1, output_type ScheduleExtraction, KHÔNG tool); runner injectable như enrich; trace `eval/traces/schedule/<message_id>.json` (ensure_ascii=False; keys message_id, prompt_version, model, input[:500], output). Trả `(extraction, trace_id)`.
- `SCHEDULE_V1` (tiếng Việt): vai trò trích lịch; CHỈ trích khi message chứa buổi học/sự kiện có yếu tố thời gian; quy đổi "tối nay"= ngày đăng, "ngày mai"= +1, thiếu năm → năm ngày đăng; KHÔNG bịa giờ/link/diễn giả — thiếu thì để null; kênh cohort_3/cohort_4 → cohort tương ứng, announcements chung → all trừ khi nêu rõ; type: workshop→WS, office hour→OH, mentor duty→MD, buổi lab→LAB, lý thuyết→LT, khác→OTHER; 2 ví dụ few-shot: (1) thông báo Workshop có giờ+Zoom+diễn giả → 1 event WS; (2) thông báo nhắc nộp bài (không lịch) → events rỗng.

- [ ] **Step 1: Failing tests** — `tests/test_schedule_extractor.py` (offline, runner giả):

```python
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
```

- [ ] **Step 2: FAIL → Step 3: Implement** (mirror `news_enricher.py` / `profile.py` style; `_run_agent` với Agents SDK khi runner None).
- [ ] **Step 4: tests PASS; full suite PASS. Step 5: Commit** — `feat(schedule): announcement schedule extractor agent`.

---

### Task 4: run_once hook + chạy thật extraction

**Files:**
- Modify: `codebase/backend/ingest/__main__.py`
- Modify: `codebase/backend/tests/test_pipeline.py`

**Interfaces:**
- `run_once(..., schedule_runner=None)` param mới. Trong vòng fetch: `p.channel.startswith("thong-bao")` → nếu `not store.is_schedule_extracted(p.message_id)`: `extraction, trace_id = extract_schedule({...post fields...}, cfg, runner=schedule_runner)` → `store.save_schedule_extraction(p.message_id, [e.model_dump() for e in extraction.events], trace_id)`; except → print `[schedule-fail]`, tiếp tục (KHÔNG mark — lượt sau thử lại); vẫn `set_checkpoint`. KHÔNG upsert_post cho thong-bao. Stats thêm `"schedule_events": tổng_event_mới`.

- [ ] **Step 1: Failing test** — thêm `tests/test_pipeline.py`:

```python
def test_run_once_extracts_announcements(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from ingest.agents import ScheduleEvent, ScheduleExtraction
    from ingest.models import RawPost

    class AnnounceSource:
        def fetch(self, since):
            return [RawPost(message_id="3001", channel="thong-bao:4", title="TB",
                            content="Workshop tối nay 20:00", author="BTC",
                            created_at="2026-07-30T07:00:00+00:00")]

    fake = ScheduleExtraction(events=[ScheduleEvent(
        type="WS", title="WS3", date="2026-07-30", start="20:00", cohort="4")])
    store = Store(str(tmp_path / "t.db"))
    stats = run_once(store, AnnounceSource(), Config(), runner=fake_runner,
                     schedule_runner=lambda t: fake)
    assert stats["schedule_events"] == 1
    assert store.get_news("3001") is None                       # không vào posts
    stats2 = run_once(store, AnnounceSource(), Config(), runner=fake_runner,
                      schedule_runner=lambda t: fake)
    assert stats2["schedule_events"] == 0                       # extract-once (checkpoint + mark)
```

- [ ] **Step 2: FAIL → Step 3: Implement. Step 4: pipeline tests + full suite PASS.**
- [ ] **Step 5: CHẠY THẬT** (từ codebase/backend, `$env:PYTHONIOENCODING="utf-8"`): `.venv/Scripts/python.exe -m ingest --source manifest --limit 40` — news/resources đã ingest nên lượt này chỉ tốn ~38 call extract. Sau đó in bảng: `.venv/Scripts/python.exe -c` query `SELECT type,title,date,start,cohort,format FROM schedule_events ORDER BY date` — dán vào report. Kỳ vọng bắt được các buổi Workshop/OH tối trong data thật; thông báo thường (nộp bài, quy định) → 0 event.
- [ ] **Step 6: Commit** — `feat(schedule): pipeline extracts evening sessions from announcements`.

---

### Task 5: Schedule generator + API

**Files:**
- Create: `codebase/backend/ingest/schedule.py`
- Modify: `codebase/backend/api/main.py`
- Test: `codebase/backend/tests/test_schedule_api.py`

**Interfaces:**
- `ingest/schedule.py` (thuần, không I/O trừ nhận data):

```python
RECURRING_DAYS = range(0, 6)          # T2..T7
LAB_SLOT = ("09:00", "13:00")
LT_SLOT = ("14:00", "18:00")
STATIC_MATERIALS = {
    "LAB": [{"label": "Tài liệu hướng dẫn", "url": "https://codelabs.vlearn.dev/codelab", "kind": "doc"}],
    "LT": [{"label": "Slide trên VLearn", "url": "https://vlearn.dev", "kind": "slide"}],
}

def recurring_sessions(settings: dict, date_from: str, date_to: str) -> list[dict]
    # mỗi ngày weekday 0-5: LAB (location settings["lab_room"]) + LT (settings["lt_room"]),
    # host "Giảng viên khoá", format "Offline", cohort settings["cohort"], zoom_url None

def build_schedule(settings, events: list[dict], resources: list[dict],
                   date_from, date_to) -> list[dict]
    # 1) recurring; 2) events (đã lọc cohort ở Store): type LAB/LT trùng (date) →
    #    override host/zoom_url/location lên block recurring cùng type (không thêm block);
    #    WS/OH/MD/OTHER → block riêng; 3) materials: STATIC cho LAB/LT; evening: nếu
    #    session_code → resources khớp thành {label: title, url, kind}; zoom_url giữ field riêng;
    # 4) sort theo (date, start); item shape spec §2.3.
```

- API:
  - `GET /api/users/{user_id}/settings` → `store.ensure_user(user_id)` rồi `get_settings` (bot/khách mới dùng được ngay).
  - `PUT /api/users/{user_id}/settings` body `{cohort, lt_room, lab_room}` — validate cohort in {"3","4"} (422 nếu sai — Pydantic Literal), ensure_user trước, trả settings mới.
  - `GET /api/schedule?user_id=&cohort=&from_=&to=` (query params `from`/`to` dùng alias: `from_: str | None = Query(None, alias="from")`): mặc định from/to = thứ 2..thứ 7 tuần hiện tại (`datetime.now()` — chấp nhận không xác định trong test bằng cách LUÔN truyền from/to trong tests); settings từ user_id (ensure_user) hoặc `{cohort đề, D302, D305}` khi chỉ truyền cohort; events = `store.list_schedule_events(cohort, from, to)`; resources = `store.list_resources()`; trả `build_schedule(...)`.
  - `recommendations`: thay `raise HTTPException(404)` bằng `store.ensure_user(user_id)` (giữ nguyên phần còn lại; cập nhật test cũ `test_recommendations...` bỏ assert 404 → giờ trả list cho user lạ).

- [ ] **Step 1: Failing tests** — `tests/test_schedule_api.py`:

```python
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
```

- [ ] **Step 2: FAIL → Step 3: Implement** (`ingest/schedule.py` + API; sửa test recommendations cũ trong `tests/test_api_recsys.py`: user lạ giờ trả 200 list — đổi assert 404 thành `assert client.get(...).status_code == 200`).
- [ ] **Step 4: schedule tests + full suite PASS. Step 5: Commit** — `feat(schedule): weekly schedule builder and API with user settings`.

---

### Task 6: UI — App-level user state + Settings page

**Files:**
- Modify: `codebase/ui/src/App.jsx`, `codebase/ui/src/components/Sidebar.jsx`, `codebase/ui/src/pages/NewsPage.jsx`, `codebase/ui/src/lib/api.js`
- Create: `codebase/ui/src/pages/SettingsPage.jsx`

**Hành vi:**
1. `api.js` thêm: `settings: (id) => j(.../api/users/${id}/settings)`, `saveSettings: (id, body) => PUT`, `schedule: (id, from, to) => j(.../api/schedule?user_id=&from=&to=)`.
2. `App.jsx`: state `users` (list|null), `currentUser` (id|null); mount fetch `api.users()`; đọc `new URLSearchParams(location.search).get("user")` — nếu trùng user_id thì chọn, else user đầu; truyền `{users, currentUser, onSelectUser}` xuống NewsPage/SettingsPage/CalendarPage. NewsPage bỏ state users/selectedUser cục bộ, nhận props (đổi mọi tham chiếu `selectedUser` → prop `currentUser`, dropdown gọi `onSelectUser`); hành vi còn lại giữ nguyên.
3. `Sidebar`: thêm item `{id: "settings", icon: Settings (lucide), label: "Cài đặt"}` dưới Bản tin (trên mục Hỏi đáp).
4. `SettingsPage.jsx`: nhận props; offline/currentUser null → Card thông báo offline. Online: fetch `api.settings(currentUser)` khi currentUser đổi; form trong Card (max-w-lg): label "Khoá" — 2 nút toggle (Button variant secondary khi chọn) `Khoá 3`/`Khoá 4`; Input "Lớp Lý thuyết"; Input "Lớp Lab"; Button "Lưu" → `api.saveSettings` → text nhỏ "Đã lưu ✓" 2s. Note: "Trang Lịch học và lệnh /schedule của bot trả theo thiết lập này."
5. Gate: `npm run build` PASS. KHÔNG sửa CalendarPage ở task này (Task 7).

- [ ] **Steps:** implement → build PASS → commit `feat(ui): app-level user state and settings page`.

---

### Task 7: UI — CalendarPage rewire sang /api/schedule

**Files:**
- Modify: `codebase/ui/src/pages/CalendarPage.jsx`, `codebase/ui/src/components/SessionModal.jsx`, `codebase/ui/src/App.jsx` (truyền props calendar)

**Hành vi:**
1. CalendarPage nhận `{currentUser}`; khi currentUser + tuần đang xem đổi → `api.schedule(currentUser, mondayISO, saturdayISO... dùng CN=chủ nhật cuối tuần)` (from = thứ 2, to = chủ nhật của tuần đang xem, format YYYY-MM-DD). Lỗi/offline → dùng mock SESSIONS như hiện tại.
2. Map API item → session shape hiện có của calendar: `{code: item.session_code || item.type, type: item.type === "LAB" ? "LAB" : item.type, title, date: new Date(item.date + "T00:00:00"), start/end: parse "HH:MM" → số thập phân, format, location, cls: "Khoá " + item.cohort, host, links: {zoom: item.zoom_url || undefined}, materials: item.materials, jump_url}`. `OTHER` → dùng palette `OH` màu (hoặc thêm entry OTHER màu xám vào SESSION_TYPES).
3. SessionModal: thêm render `materials` (list button link `label` mở `url` tab mới — thay/khi không có `links` demo cũ); block "Tóm tắt nội dung" chỉ render khi có `desc/summary` (API không có → ẩn); footer nguồn: nếu `jump_url` → link "Xem thông báo gốc".
4. Gate: `npm run build` PASS. (Controller sẽ verify browser sau.)

- [ ] **Steps:** implement → build PASS → commit `feat(ui): calendar renders real schedule from API`.

---

### Task 8: Bot — formatter + rework /schedule /digest /hub

**Files:**
- Create: `codebase/bot/companion_discord/formatting.py`
- Modify: `codebase/bot/companion_discord/bot.py`
- Test: `tests/test_bot_formatting.py` (root)
- Modify: `codebase/bot/README.md` (4 lệnh + options)

**Interfaces:**
- `formatting.py` (thuần):

```python
def bucket(start: str | None) -> str      # None→"Tối"; <"13:00"→"Sáng"; <"18:00"→"Chiều"; else "Tối"

def format_schedule(items: list[dict], date_label: str, cohort: str) -> str
    # Header "📅 Lịch <date_label> — Khoá <cohort>"; nhóm Sáng/Chiều/Tối theo bucket(start),
    # trong nhóm sort theo start; mỗi buổi:
    #   "  [<start>–<end>: <title><location/format suffix>]"
    #   suffix: Offline+location → " — <location>"; Zoom → " — Zoom"
    #   dưới đó mỗi material: "    - <label>: <url>"; zoom_url → "    - Zoom: <url>"
    # start/end None → "[giờ TBA: ...]"; nhóm rỗng → "Sáng: không có lịch" (tương tự Chiều/Tối)

def format_digest(items: list[dict], personalized: bool) -> str
    # personalized False: nhóm theo tags[0] (label hoá: dùng mapping TAG_LABELS nội bộ
    #   {"ai-model": "AI Model", ...} — copy 10 nhãn từ taxonomy); heading "**<Label>**";
    #   mỗi bài "• <title> — <summary cắt 120> (<jump_url>)"
    # personalized True: không nhóm; mỗi bài thêm tiền tố "✨<round(parts.sim*100)>% "
    # rỗng → "Chưa có bản tin nào."
```

- `bot.py`:
  - `_request_json` giữ nguyên (GET khi payload None).
  - `/schedule [date]` (option `date` str "YYYY-MM-DD" optional, default hôm nay theo giờ máy): `user = interaction.user.name`; GET `{api}/api/schedule?user_id={user}&from={d}&to={d}`; cohort lấy từ GET `{api}/api/users/{user}/settings`; reply `_text(format_schedule(items, date_label, cohort))`.
  - `/digest [option: latest|personalize]` (app_commands.choices, default latest): latest → GET `/api/news` lấy 10 phần tử đầu; personalize → GET `/api/recommendations?user_id={user}&k=10`; reply `_text(format_digest(...))`.
  - `/hub` → `os.environ["COMPANION_UI_URL"] + "?user=" + interaction.user.name`.
  - Bỏ dependency `latest_posts`/DB path cho digest (không dùng bot-DB nữa cho 2 lệnh này; import `ingestion` giữ nguyên phần khác nếu còn dùng — nếu không còn chỗ nào dùng `latest_posts` thì bỏ import).
- Root tests `tests/test_bot_formatting.py` — table-driven cho `bucket`, `format_schedule` (đủ 3 nhóm + nhóm rỗng + material lines + TBA), `format_digest` (nhóm tag, cắt 120, personalized prefix, rỗng).

- [ ] **Steps:** failing tests → FAIL → implement → root suite PASS (backend suite không đổi) → commit `feat(bot): schedule and digest commands use companion api with fixed formats`.

---

### Task 9: E2E thật + README

**Files:**
- Modify: `codebase/backend/README.md` (mục Schedule: endpoints, recurring rule, extractor, settings)

**Steps:**
- [ ] **Step 1:** Đảm bảo đã chạy Task 4 Step 5 (schedule_events có data thật). Khởi động uvicorn nền → `GET /api/schedule?user_id=an&from=<thứ2 tuần này>&to=<CN>` → dán response rút gọn vào report: recurring đủ 12 block + các buổi tối trích được. GET `/api/users/an/settings` trả defaults. Tắt uvicorn.
- [ ] **Step 2:** Cập nhật README backend.
- [ ] **Step 3:** Full suite backend + root PASS lần cuối.
- [ ] **Step 4: Commit** — `docs(schedule): backend README for schedule pipeline`.

---

## Self-review đã chạy

- **Spec coverage:** §1 bảng quyết định (T1 settings/ensure_user, T4-T5 recurring+extract, T8 bot); §2.1-2.2 (T1-T3); §2.3 (T5); §3 (T6-T7); §4 (T8); §5 tests phân bổ từng task; chạy thật (T4 step 5 + T9).
- **Type consistency:** `save_schedule_extraction(events: list[dict])` nhận `model_dump()` từ T3 — keys trùng cột T1; `list_schedule_events(cohort, from, to)` dùng ở T5 API; `build_schedule(settings, events, resources, ...)` shapes khớp Store outputs; bot formatter nhận đúng item shape API §2.3.
- **Placeholders:** UI/bot tasks mô tả hành vi + interface đầy đủ thay code verbatim (pattern R8 đã chạy tốt); không TBD.
