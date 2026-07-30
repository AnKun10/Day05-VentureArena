# Companion Discord Bot

Bot điều khiển của Companion: 4 slash commands (`/ask` `/digest` `/schedule` `/hub` — xem `companion_discord/bot.py`; luồng TA/ta-digest đã bỏ theo MASTERPLAN) và bộ công cụ rebuild/replication dựng lại kênh trên server đích qua Discord Bot API (destination-only: chỉ tạo/xoá/replay tài nguyên managed trong `DESTINATION_GUILD_ID` sau khi duyệt dry-run).

> Phần thu thập dữ liệu bằng web-collector đã được gỡ khỏi repo. Rebuild/replication
> đọc manifest có sẵn tại `data/discord_crawl/manifest.json` (artifact đầu vào).

## Chạy bot

```powershell
Copy-Item codebase/bot/.env.example codebase/bot/.env   # điền DISCORD_TOKEN, COMPANION_API_URL, COMPANION_UI_URL...
uv run --no-project --with-requirements codebase/bot/requirements.txt python codebase/bot/run_bot.py
```

`/ask` gọi `COMPANION_API_URL/api/ask` (backend `codebase/backend` — chạy `uvicorn api.main:app --port 8000`).

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
