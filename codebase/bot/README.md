# Companion Discord Bot

Bot điều khiển của Companion: 5 slash commands (`/ask` `/digest` `/schedule` `/bio` `/hub` — xem `companion_discord/bot.py`; luồng TA/ta-digest đã bỏ theo MASTERPLAN) và bộ công cụ rebuild/replication dựng lại kênh trên server đích qua Discord Bot API (destination-only: chỉ tạo/xoá/replay tài nguyên managed trong `DESTINATION_GUILD_ID` sau khi duyệt dry-run).

> Phần thu thập dữ liệu bằng web-collector đã được gỡ khỏi repo. Rebuild/replication
> đọc manifest có sẵn tại `data/discord_crawl/manifest.json` (artifact đầu vào).

## Chạy bot

```powershell
Copy-Item codebase/bot/.env.example codebase/bot/.env   # điền DISCORD_TOKEN, COMPANION_API_URL, COMPANION_UI_URL...
uv run --no-project --with-requirements codebase/bot/requirements.txt python codebase/bot/run_bot.py
```

`/ask` gọi `COMPANION_API_URL/api/ask` (backend `codebase/backend` — chạy `uvicorn api.main:app --port 8000`).

### 5 slash commands

Reply của `/schedule` và `/digest` là Discord **embed** (icon theo loại buổi/tag,
masked link nên không sinh link preview) — build bởi
`companion_discord.formatting.schedule_embed` / `digest_embed` (module thuần,
test tại `tests/test_bot_formatting.py`).

**Resilience:** `_request_json` giữ timeout 10s + retry 2 lần (backoff) cho lỗi
tạm thời (mạng/timeout/5xx); lỗi 4xx (vd bio bị guardrail chặn) không retry mà
hiển thị lý do từ server. `/digest personalize` nếu hỏng → tự hạ cấp về tin mới
nhất kèm ghi chú. Nội dung bio/câu hỏi bị chặn (tục tĩu / prompt injection) được
server guardrail xử lý; bot chỉ hiển thị lý do.

- `/ask <question>` — hỏi Companion (RAG), trả lời kèm nguồn trích dẫn.
- `/schedule [date]` — lịch học của người dùng theo ngày (`date` dạng `YYYY-MM-DD`,
  tuỳ chọn, mặc định là hôm nay theo giờ máy chạy bot). Gọi
  `GET /api/schedule?user_id=<username>&from=<date>&to=<date>` và
  `GET /api/users/<username>/settings` để lấy khoá (cohort) — nhóm buổi học theo
  Sáng/Chiều/Tối kèm tài liệu, phòng/Zoom.
- `/digest [option]` — bản tin mới nhất (`option=latest`, mặc định) từ
  `GET /api/news` (10 bài đầu, nhóm theo tag) hoặc gợi ý cá nhân hoá
  (`option=personalize`) từ `GET /api/recommendations?user_id=<username>&k=10`
  (mỗi bài có `✨<%>` theo độ tương đồng; user chưa có bio/bookmark thì ẩn % và
  footer hướng dẫn dùng `/bio`).
- `/bio [text]` — xem/cập nhật bio của user (lưu server-side, dùng cho gợi ý).
  Discord API không cho bot đọc About Me của người dùng (privacy), nên cách
  nhanh nhất là copy About Me và dán vào `/bio text:...`.
- `/hub` — trả về link Companion Web UI kèm `?user=<username>`, đọc từ biến môi
  trường `COMPANION_UI_URL` (mặc định `http://localhost:5173` nếu chưa cấu hình
  trong `.env`).

## Rebuild server đích (destination-only)

Cần `data/discord_crawl/manifest.json` + `config.yaml` (copy từ `config.example.yaml`), và `DISCORD_TOKEN` + `DESTINATION_GUILD_ID` trong `codebase/bot/.env`. Để tái dùng kênh đích có sẵn, khai IDs trong `discord_bot.destination_channel_mappings` — rebuild validate guild/type/quyền gửi, không bao giờ match theo tên.

Xem plan (không thay đổi Discord):

```powershell
uv run --no-project --with-requirements codebase/bot/requirements.txt python codebase/bot/run_rebuild.py --dry-run --config config.yaml
```

Chỉ sau khi duyệt plan, chạy apply với xác nhận kép:

```powershell
uv run --no-project --with-requirements codebase/bot/requirements.txt python codebase/bot/run_rebuild.py --config config.yaml --apply `
  --destination-guild-id <DESTINATION_GUILD_ID> `
  --confirm-destination-guild-id <DESTINATION_GUILD_ID>
```

`managed_categories`, `managed_channels`, and Bot-created IDs are the default deletion scope. `preserve_channels` and Discord system channels are never planned for deletion. `--replace-all-destination-channels` additionally requires `--confirm-replace-all`.

The state file maps `categories`, `channels`, `threads`, and `messages` incrementally, so resumed applies skip completed work. All replayed messages use disabled mentions. Attachment files are not downloaded or uploaded; their filename and original URL are replayed.

`replay.visual_fidelity: true` keeps source plaintext and URLs without injecting author/timestamp metadata. Discord performs native URL unfurls when available; custom embeds are sent only for source embeds that are independent of a plaintext URL.

Discord creates new message IDs and timestamps, original authors cannot be impersonated, Community-dependent channel types may fall back to text channels, and older attachment URLs may expire.
