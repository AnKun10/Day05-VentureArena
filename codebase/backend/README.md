# Companion backend — ingestion + API

## Setup
```bash
cd codebase/backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # điền OPENAI_API_KEY (+ TAVILY, DISCORD nếu có)
```

## Chạy
```bash
python -m ingest --source seed          # ingest + enrich seed (enrich-once)
python -m ingest --source discord       # đọc forum thật (cần token + channel id)
python -m ingest --loop 30              # lặp mỗi 30 phút
python -m ingest --force                # enrich lại (khi đổi prompt version)
uvicorn api.main:app --port 8000        # API cho UI (CORS localhost:5173)
pytest                                  # unit tests (không gọi API ngoài)
python -m ingest.smoke                  # smoke prompt (cần OPENAI_API_KEY)
```

Enrich-once: bài đã có `enriched_at` trong `companion.db` không bao giờ bị
enrich lại (không tốn phí) trừ khi `--force`. Trace từng lời gọi AI nằm ở
`eval/traces/ingest/`. Spec: `docs/superpowers/specs/2026-07-31-news-ingestion-pipeline-design.md`.

## Recommendations (recsys)
```bash
python -m recsys.smoke                  # smoke recsys thật (cần OPENAI_API_KEY; ~13 call nhỏ)
# Windows: đặt PYTHONIOENCODING=utf-8 trước khi chạy smoke để tránh
# UnicodeEncodeError khi in tiếng Việt (cp1252 console):
#   $env:PYTHONIOENCODING="utf-8"; .venv\Scripts\python.exe -m recsys.smoke
```

3 endpoint mới trong `api.main` (cộng thêm users/bookmarks để phục vụ chúng):
- `GET /api/users` — danh sách user demo (seed tự động từ `recsys/seeds/users.json`
  qua `_seed_users` nếu bảng `users` rỗng); `PUT /api/users/{user_id}/bio` — cập nhật
  bio thủ công. Suy hồ sơ (`ensure_profile`) chạy NGAY tại đây (write-time) nên
  `/api/recommendations` về sau luôn nhanh (<1s), không phải chờ OpenAI lúc đọc.
- `GET /api/users/{user_id}/bookmarks`, `PUT`/`DELETE .../bookmarks/{message_id}` —
  bookmark bài viết (bookmark cũng là tín hiệu đầu vào cho profile).
- `GET /api/recommendations?user_id=&k=` — **không bao giờ 503**. Chuỗi hạ cấp:
  (1) Qdrant + vector (hồ sơ đã suy lúc lưu bio); (2) Qdrant chết / user chưa có
  vector → `recommend_keyword` xếp hạng bằng từ khoá trùng (SQLite thuần, không
  cần OpenAI/Qdrant); (3) không có bio → keyword degenerate về hot ranking
  (tương tác + độ mới).

### Guardrails (an toàn đầu vào)
`guardrails.py` (thuần, `tests/test_guardrails.py`) chặn 2 lớp TRƯỚC khi nội dung
người dùng tới model/retrieval, áp cho cả `PUT /bio` (→ HTTP 422) và `POST /api/ask`
(→ `action="blocked"`, bọc quanh RAG của Nghĩa, không sửa logic bên trong):
- **Tục tĩu / xúc phạm / slur** (VI+EN, khớp theo ranh giới từ).
- **Prompt injection** ("bỏ qua hướng dẫn", "đóng vai...", "reveal system prompt"...).
- Chuẩn hoá: bỏ ký tự ẩn zero-width + ký tự điều khiển, gộp khoảng trắng, giới hạn
  độ dài. Defense-in-depth: prompt suy hồ sơ cũng coi bio là DỮ LIỆU, phớt lờ mọi
  câu lệnh nhúng trong đó.

Công thức điểm: `score = 0.6*sim_n + 0.2*eng(log1p(hearts+comments), chuẩn hoá
theo max) + 0.2*rec(exp(-tuổi_bài/72h))`, sau đó chọn top-k bằng MMR (`λ=0.15`
— mức đa dạng thấp, chỉnh trong `recsys/recommend.py::MMR_LAMBDA`).

`sim_n` là cosine(user↔news) **chuẩn hoá min-max trong pool** (bài giống user
nhất → 1.0, ít nhất → 0.0). Lý do: cosine tuyệt đối của embedding có nền cao và
phụ thuộc chủ đề, nên với user có niche mỏng trong corpus mọi sim dồn vào dải
hẹp (vd 0.36–0.51); nếu dùng sim thô, eng+rec (giống nhau cho MỌI user) sẽ lấn
át và thứ hạng hội tụ về "hot chung" — mọi user nhận gần như cùng danh sách.
Min-max rút tín hiệu TƯƠNG ĐỐI để cá nhân hoá thực sự dẫn dắt. `parts.sim` trả
về vẫn là cosine THÔ (hiển thị % trung thực), chỉ ranking dùng `sim_n`.

Qdrant chạy embedded trong 1 process (chưa hỗ trợ đa process cùng mở 1
`qdrant_data/`) — muốn chạy `python -m ingest` (embed) thì tắt `uvicorn` trước, hoặc
chấp nhận log `[recsys] qdrant busy/unavailable: ... (bỏ qua embed)` và ingest chạy
tiếp phần enrich/không embed. Thư mục `qdrant_data/` không commit vào git (xem
`.gitignore` gốc); `smoke_qdrant/` không cần khai báo gitignore vì
`recsys/smoke.py` tự dọn (`shutil.rmtree`) sau mỗi lần chạy — nếu script crash
giữa chừng, xoá thủ công `smoke-rec.db` và `smoke_qdrant/` trước khi chạy lại.

## Schedule

2 endpoint trong `api.main`:
- `GET/PUT /api/users/{user_id}/settings` — cohort ("3"/"4") + phòng LT/LAB của
  user, lưu trong SQLite (`ensure_user` tự tạo user nếu chưa có); mặc định
  `{"cohort": "4", "lt_room": "D302", "lab_room": "D305"}`. Bot `/schedule` đọc
  settings này mỗi lần gọi nên đổi phòng/cohort có hiệu lực ngay, không cần
  ingest lại.
- `GET /api/schedule?user_id=&cohort=&from=&to=` — lịch tuần đã build sẵn
  (`ingest/schedule.py::build_schedule`). Có `user_id` thì suy ra settings của
  user đó; chỉ có `cohort` (không `user_id`) thì dùng phòng mặc định ở trên —
  nhánh này phục vụ UI/bot khi chưa biết user. Thiếu `from`/`to` thì mặc định
  tuần hiện tại (thứ 2 → thứ 7).

Lịch gồm 2 phần ghép lại theo `date`:
- **Recurring** (`RECURRING_DAYS = range(0, 5)`, tức thứ 2 → thứ 6; T7/CN nghỉ):
  mỗi ngày 1 buổi sáng (09:00–13:00) + 1 buổi chiều (14:00–18:00), hình thức
  Offline. Slot theo khoá (`COHORT_SLOTS`): **Khoá 4 sáng Lý thuyết, chiều
  Lab**; **Khoá 3 ngược lại** (sáng Lab, chiều Lý thuyết). Phòng lấy từ
  settings (`lt_room`/`lab_room`), tài liệu tĩnh đính kèm sẵn (LT →
  `https://vlearn.dev`, LAB → `https://codelabs.vlearn.dev/codelab`).
- **Buổi tối trích từ thông báo** (WS/OH/MD): agent
  `ingest.agents.schedule_extractor` đọc bài đăng ở các channel `thong-bao`,
  extract-once — bài đã trích lưu trong bảng đánh dấu riêng
  (`schedule_extracted`) nên không gọi AI lại cho bài cũ, giống cơ chế
  enrich-once ở trên. Type `OTHER` chứa deadline/checkpoint (có mốc thời gian
  nhưng không phải buổi học có mặt tham dự) — vẫn hiển thị trên lịch nhưng với
  màu riêng (xám, nhãn Deadline/Khác). Nếu 1 buổi LAB/LT trong tuần có
  announcement đổi phòng/host riêng (override phòng/host/zoom_url), event
  trích được sẽ ghi đè field tương ứng lên block recurring cùng ngày thay vì
  tạo dòng riêng; WS/OH/MD được dedup theo `(type, date, start)` trước khi
  ghép vào lịch.

`GET /api/schedule` không cần `OPENAI_API_KEY` (build từ dữ liệu đã trích sẵn
trong `companion.db`); chỉ `python -m ingest` (bước extract) mới gọi AI.
