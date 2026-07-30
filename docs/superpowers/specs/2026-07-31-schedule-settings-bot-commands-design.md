# Spec — Lịch học thật (rule + agent trích thông báo), Settings, rework bot commands

> Phạm vi: (1) pipeline lịch học = khung giờ cố định theo khoá + agent trích buổi tối từ kênh thông-báo; (2) API schedule; (3) UI page Settings + rewire page Lịch học; (4) bot `/schedule` `/digest` `/hub` theo format mới. `/ask` GIỮ NGUYÊN (user thiết kế sau).
> Nguồn dữ liệu: manifest crawl snapshot (3 kênh text: `announcements`, `cohort_3_common_announcements`, `cohort_4_common_announcements`; kênh `resources` đã ingest ở vòng trước).

## 1. Quyết định đã chốt

| Quyết định | Lựa chọn |
|---|---|
| Khung giờ cố định (cả K3 & K4) | **Sáng 09:00–13:00 Lab · Chiều 14:00–18:00 Lý thuyết**, offline; áp dụng **T2–T7** (CN nghỉ — hằng số `RECURRING_DAYS`, chỉnh được) |
| Buổi tối (WS / Office hour / Mentor duty) | **Agent trích từ message 3 kênh thông-báo**: loại buổi, tiêu đề, ngày, giờ bắt đầu/kết thúc, hình thức, link Zoom, diễn giả/giảng viên, khoá (3/4/chung). Extract-once theo message_id, `--force` re-extract |
| Giảng viên buổi Lab/LT | Khác nhau tùy buổi — nếu thông báo có nêu thì agent trích và gắn đè theo (cohort, date, type); mặc định "Giảng viên khoá" |
| Tài liệu buổi học | LT → link tĩnh `https://vlearn.dev` (Slide trên VLearn) · Lab → `https://codelabs.vlearn.dev/codelab` (Tài liệu hướng dẫn) · WS/tối → match `resources.session_code` (linker sẵn có) |
| Settings (server-side, gắn user) | Page Settings ghi qua API vào **cùng DB với bio/bookmarks** — bảng `users` thêm cột `cohort` ('3'/'4', default '4'), `lt_room` (default 'D302'), `lab_room` (default 'D305'). `GET/PUT /api/users/{id}/settings`. → bot `/schedule` tra settings của user gọi lệnh, trả đúng ngay |
| User hiện tại trên UI | Nâng `selectedUser` + danh sách users lên **App level** (shared state) — News, Settings, Lịch học dùng chung một user đang chọn |
| Bot cohort | KHÔNG cần option cohort — `/schedule` dùng settings của `user_id` = tên Discord (user chưa tồn tại → upsert với defaults) |
| `/hub` cá nhân hoá | Gửi `COMPANION_UI_URL?user=<user_id>`; UI đọc query param `user` → tự chọn user đó trong "Dành cho bạn" (không có → như cũ) |
| User mapping bot ↔ backend | `user_id` = tên Discord (`interaction.user.name`); backend `ensure user` (upsert bio rỗng) → chưa có bio/bookmark thì personalize fallback hot-trend tự nhiên |

## 2. Backend — schedule pipeline

### 2.1 Bảng mới (Store)

```sql
CREATE TABLE IF NOT EXISTS schedule_events(      -- buổi TỐI trích từ thông báo
  message_id TEXT PRIMARY KEY,                   -- extract-once theo message
  type TEXT,            -- WS | OH | MD | OTHER
  title TEXT, date TEXT, start TEXT, end TEXT,   -- date YYYY-MM-DD, giờ HH:MM
  cohort TEXT,          -- '3' | '4' | 'all'
  format TEXT,          -- 'Zoom' | 'Offline'
  zoom_url TEXT, host TEXT, location TEXT,
  session_code TEXT,    -- WS-3… nếu suy ra được (match resources)
  jump_url TEXT, extracted_at TEXT, trace_id TEXT
);
CREATE TABLE IF NOT EXISTS announce_state(key TEXT PRIMARY KEY, value TEXT);  -- checkpoint extract
```

Ghi chú: message thông báo KHÔNG phải buổi học (nhắc nộp bài, quy định…) → agent trả `events: []`, vẫn đánh dấu đã extract (không tốn lại tiền).

### 2.2 Agent `schedule_extractor` (recsys-style, package `ingest/agents/`)

- Model `cfg.enrich_model`, output_type:

```python
class ScheduleEvent(BaseModel):
    type: Literal["WS", "OH", "MD", "OTHER"]
    title: str
    date: str            # YYYY-MM-DD; thông báo dạng "tối nay/mai" → suy từ ngày đăng message
    start: str | None    # HH:MM
    end: str | None
    cohort: Literal["3", "4", "all"]
    format: Literal["Zoom", "Offline"]
    zoom_url: str | None
    host: str | None     # diễn giả/giảng viên nếu nêu
    location: str | None

class ScheduleExtraction(BaseModel):
    events: list[ScheduleEvent]  # rỗng nếu message không chứa lịch buổi học
```

- Input: nội dung message (đã tách header author/time bằng `split_header` sẵn có) + ngày đăng + tên kênh (cohort_3/cohort_4 → hint cohort).
- Prompt `SCHEDULE_V1` (đăng ký registry như enrich/interest): quy tắc — chỉ trích khi có buổi học/sự kiện kèm thời gian; "tối nay" = ngày đăng, "mai" = +1; không bịa giờ/link; ví dụ few-shot từ format thông báo thật ("THÔNG BÁO NHẮC LẠI LỊCH WORKSHOP 3 … 20:00 … Zoom … Diễn giả …").
- Trace: `eval/traces/schedule/<message_id>.json`.
- Chạy trong `run_once` (nguồn manifest/discord): kênh announcements → extract-once từng message; stats thêm `schedule_events`.
- ManifestSource mở rộng: đọc thêm 3 kênh announcements → RawPost channel `thong-bao` (KHÔNG enrich/news — route thẳng sang extractor; cohort hint từ source_name).

### 2.3 Users mở rộng + sinh lịch tổng hợp

Bảng `users` thêm cột (migration PRAGMA như `embedded_at`): `cohort TEXT DEFAULT '4'`, `lt_room TEXT DEFAULT 'D302'`, `lab_room TEXT DEFAULT 'D305'`. Store thêm: `get_settings(user_id) -> dict`, `set_settings(user_id, cohort, lt_room, lab_room)`, và `ensure_user(user_id, name)` (upsert với defaults — dùng cho bot).

API: `GET /api/users/{id}/settings` · `PUT /api/users/{id}/settings` body `{cohort, lt_room, lab_room}` (validate cohort ∈ {'3','4'}).

`GET /api/schedule?user_id=<id>&from=YYYY-MM-DD&to=YYYY-MM-DD` (default: tuần hiện tại; `user_id` không tồn tại → tự `ensure_user` với defaults; vẫn nhận `cohort=` làm override không cần user):
1. **Recurring** mỗi ngày T2–T7 trong [from, to]: Lab 09:00–13:00 (type LAB) + LT 14:00–18:00 (type LT), format Offline, host = override từ schedule_events nếu agent trích được buổi trùng (cohort, date, type) else "Giảng viên khoá". **`location` = `lab_room`/`lt_room` từ settings của user** (override cohort → dùng defaults D305/D302).
2. **Events tối** từ `schedule_events` where date trong khoảng AND (cohort = ? OR 'all').
3. Materials từng buổi: LAB → `[{label: "Tài liệu hướng dẫn", url: "https://codelabs.vlearn.dev/codelab"}]`; LT → `[{label: "Slide trên VLearn", url: "https://vlearn.dev"}]`; WS/OH/MD → resources có `session_code` khớp (`list_resources`) + `zoom_url` nếu có.
4. Response item: `{date, start, end, type, title, cohort, format, location, host, zoom_url, materials: [{label, url, kind}], jump_url}`.

## 3. UI

### 3.1 Shared user state + Page Settings (sidebar item mới, icon Settings)

- **App.jsx** quản lý `users` + `currentUser` (fetch `/api/users` on mount; đọc query `?user=` từ `/hub`); truyền xuống News (thay state cục bộ), Settings, Lịch học. Offline → currentUser null, mọi page fallback mock.
- Page Settings: hiển thị user đang chọn; radio **Khoá 3 / Khoá 4**; input **Lớp Lý thuyết** / **Lớp Lab**; Lưu → `PUT /api/users/{id}/settings` → toast/text "Đã lưu"; giá trị nạp từ `GET .../settings`. Note: "Bot /schedule và trang Lịch học trả theo thiết lập này".

### 3.2 Page Lịch học (rewire — giữ layout calendar tuần hiện tại)

- Online: fetch `/api/schedule?user_id=<currentUser>` theo tuần đang xem → render blocks (Lab sáng xanh lá, LT chiều xanh dương, tối WS/OH/MD như palette cũ); `location` lấy thẳng từ response (backend đã điền theo settings); offline → mock cũ.
- Modal buổi học: giữ layout mới (icon info panel + tóm tắt bỏ qua nếu không có) — hiển thị host thật, Zoom button khi có `zoom_url`, materials theo §2.3 (LT/Lab luôn có nút refer tĩnh), nguồn = `#thông-báo` + jump_url khi buổi đến từ thông báo.

## 4. Bot commands (rework `codebase/bot/companion_discord/bot.py`)

- **`/schedule [date: hôm nay]`** — `user_id` = tên Discord của người gọi; gọi `GET /api/schedule?user_id=&from=date&to=date` (backend tự ensure_user + tra settings → đúng khoá/phòng của user ngay), format cố định:

```
📅 Lịch <thứ>, <dd/mm> — Khoá <cohort của user>
Sáng:
  [09:00–13:00: Lab]
    - Tài liệu hướng dẫn: https://codelabs.vlearn.dev/codelab
Chiều:
  [14:00–18:00: Lý thuyết]
    - Slide: https://vlearn.dev
Tối:
  [20:00–22:00: Workshop 3 — Zoom]
    - Zoom: <link>
    - Record WS-3: <url>          (nếu resources có)
  (không có buổi tối → "Tối: không có lịch")
```

- **`/digest [option: latest|personalize = latest]`**:
  - `latest`: `GET /api/news` → lấy 10 bài mới nhất, **nhóm theo tag đầu tiên**, mỗi bài: `• <title> — <tóm tắt cắt 120 ký tự> (<jump_url>)` dưới heading `**<Tag>**`.
  - `personalize`: `GET /api/recommendations?user_id=<discord name>&k=10` — endpoint recommendations tự `ensure_user` (thay vì 404) với defaults → cùng format kèm `✨<sim%>`.
- **`/hub`** — trả `"<COMPANION_UI_URL>?user=<discord name>"`; UI NewsPage đọc `?user=` → nếu trùng user backend thì auto-select.
- **`/ask`** — GIỮ NGUYÊN hành vi hiện tại (gọi `/api/ask`); thiết kế sâu ở vòng sau.
- Bot digest/schedule gọi qua `_request_json` sẵn có (thêm hỗ trợ GET với query).

## 5. Kiểm thử

- Unit (không API ngoài): schedule recurring generator (đúng T2–T7, bỏ CN, đúng khung giờ); merge events + override host; materials mapping LT/Lab tĩnh + WS match resources; Store schedule_events extract-once; **users migration (DB cũ mở được) + settings CRUD + ensure_user defaults**; API /api/schedule (TestClient — location đúng theo settings user, cohort filter events); recommendations `ensure_user` thay vì 404; agent extractor với runner giả (message "không phải lịch" → events rỗng vẫn mark extracted); bot formatter thuần hàm (`format_schedule(day_payload) -> str`, `format_digest(items, personalized) -> str`) — table-driven.
- Chạy thật 1 lần: extract 38 message announcements (~38 call nhỏ) → xem bảng schedule_events; kỳ vọng bắt được Workshop tối trong data thật.

## 6. Ngoài phạm vi

- `/ask` design sâu (vòng sau); settings đồng bộ server-side; lịch K3 phòng khác K4 (settings tự chỉnh); recurring days linh hoạt theo tuần lễ/ngày nghỉ.
