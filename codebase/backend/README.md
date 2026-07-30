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
  bio thủ công (trigger tính lại profile ở lần gọi recommend kế tiếp).
- `GET /api/users/{user_id}/bookmarks`, `PUT`/`DELETE .../bookmarks/{message_id}` —
  bookmark bài viết (bookmark cũng là tín hiệu đầu vào cho profile).
- `GET /api/recommendations?user_id=&k=` — `ensure_profile` (suy luận lại interest
  summary/tags từ bio + bookmark khi hash đổi) rồi `recommend` trả về top-k bài.

Công thức điểm: `score = 0.5*sim(cosine user↔news) + 0.25*eng(log1p(hearts+comments),
chuẩn hoá theo max) + 0.25*rec(exp(-tuổi_bài/72h))`, sau đó chọn top-k bằng MMR
(`λ=0.15` — mức đa dạng thấp, chỉnh trong `recsys/recommend.py::MMR_LAMBDA`)
để giảm trùng lặp giữa các bài được chọn (phạt các ứng viên gần với bài
đã chọn trước theo cosine similarity).

Qdrant chạy embedded trong 1 process (chưa hỗ trợ đa process cùng mở 1
`qdrant_data/`) — muốn chạy `python -m ingest` (embed) thì tắt `uvicorn` trước, hoặc
chấp nhận log `[recsys] qdrant busy/unavailable: ... (bỏ qua embed)` và ingest chạy
tiếp phần enrich/không embed. Thư mục `qdrant_data/` không commit vào git (xem
`.gitignore` gốc); `smoke_qdrant/` không cần khai báo gitignore vì
`recsys/smoke.py` tự dọn (`shutil.rmtree`) sau mỗi lần chạy — nếu script crash
giữa chừng, xoá thủ công `smoke-rec.db` và `smoke_qdrant/` trước khi chạy lại.
