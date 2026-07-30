# Spec — News Ingestion Pipeline (Bản tin cộng đồng)

> Phạm vi: worker ingestion cho **Bản tin** (kênh `chia-sẻ`, `bài-học`) + Session Linker (`#tài-nguyên`) + 3 API read-only cho UI.
> KHÔNG thuộc phạm vi: Q&A core (`/api/ask`), Discord bot commands, digest kênh chat lớp — thiết kế ở vòng sau.
> Tham chiếu: `MASTERPLAN.md` (taxonomy 10 tag, cấu trúc repo, phân công).

## 1. Quyết định đã chốt

| Quyết định | Lựa chọn |
|---|---|
| Hình dạng agent | **A — một agent/bài, có tool ảnh**: structured output + tự gọi `search_image` (Tavily) |
| Framework | **OpenAI Agents SDK** (model `gpt-5-mini`) |
| Kiến trúc worker | **Batch độc lập** (`python -m ingest`), cờ `--loop <phút>`; interface `Source` swap được Discord ↔ seed JSON |
| Nguồn đọc | `DiscordSource` (bot token, đọc forum `chia-sẻ` + `bài-học`) · fallback `SeedSource` (JSON, dùng khi demo không có quyền/mạng) |
| Comment | Có sync — UI có màn đọc comment |
| Persistence | **Enrich-once**: kết quả lưu vĩnh viễn vào SQLite, bài đã enrich không bao giờ chạy lại trừ khi `--force` |

## 2. Kiến trúc & flow

```
codebase/backend/ingest/
├── __main__.py     # CLI: python -m ingest [--loop 30] [--source discord|seed] [--force] [--limit 20]
├── sources.py      # Source (interface) → DiscordSource / SeedSource
├── enrich.py       # NewsEnricher — agent Agents SDK
├── linker.py       # SessionLinker cho #tài-nguyên
├── store.py        # SQLite + checkpoint + truy vấn cho API
├── prompts.py      # system prompt đánh version (ENRICH_V1, …)
└── seeds/posts.json
```

Flow một lượt chạy:

1. `Source.fetch(since=checkpoint)` → danh sách `RawPost{message_id, channel, title, content, author, role, jump_url, created_at, hearts, comments[]}`.
2. Upsert raw post + comments vào SQLite (bài cũ: chỉ update `hearts`, `comment_count`, comments mới).
3. Với mỗi bài **chưa có `enriched_at`** (hoặc mọi bài nếu `--force`): chạy `NewsEnricher` → update `summary, tags, image_url, image_source, enriched_at, trace_id`.
4. Bài từ `#tài-nguyên`: qua `SessionLinker` → bảng `resources`.
5. Cập nhật checkpoint = max(message_id) theo kênh. Chạy lại bất kỳ lúc nào đều an toàn (idempotent).

**Enrich-once (yêu cầu chốt):** enrich là bước tốn tiền duy nhất — kết quả nằm vĩnh viễn trong DB; lượt chạy mới chỉ trả phí cho bài mới. `--force` dùng khi nâng version prompt và muốn enrich lại có chủ đích.

## 3. NewsEnricher (OpenAI Agents SDK)

- **Agent** `news_enricher`: model `gpt-5-mini`, `output_type` Pydantic:

```python
class NewsEnrichment(BaseModel):
    summary_vi: str          # 1-3 câu tiếng Việt
    tags: list[TagId]        # 1-3 tag, TagId = Literal["ai-model","ai-skill","ai-tools",
                             # "api-mcp","system-design","uiux","dataset","soft-skills","survey","other"]
    image_query: str         # tiếng Anh, dùng cho tool search_image
    image_url: str | None    # điền từ kết quả tool; None nếu tool thất bại
```

Tag lệch taxonomy → Pydantic validation fail → Agents SDK tự retry.

- **Tool duy nhất** `search_image(query: str) -> str`: gọi Tavily Image Search, trả URL ảnh đầu tiên đạt điều kiện (https, không phải favicon/logo nhỏ). Timeout 10s.
- **Instructions (prompts.py — `ENRICH_V1`):** vai trò biên tập viên bản tin nội bộ khoá; bảng 10 tag kèm mô tả 1 dòng/tag; quy tắc: (1) tóm tắt 1-3 câu **chỉ từ nội dung bài — không thêm thông tin ngoài bài**, giữ nguyên thuật ngữ kỹ thuật; (2) chọn 1-3 tag, không chắc thì ít tag lại, không khớp gì → `["other"]`; (3) tạo `image_query` tiếng Anh mô tả chủ đề trực quan; (4) gọi `search_image` đúng 1 lần rồi điền `image_url`. Kèm 2 ví dụ few-shot (1 bài kỹ thuật đa tag, 1 bài survey).
- **Trace:** ngoài tracing sẵn của SDK, persist mỗi run một file JSON `eval/traces/ingest/<message_id>.json` (input rút gọn, output, tool calls, usage tokens, prompt version) — artifact cho R5.

## 4. SessionLinker (#tài-nguyên)

- Tầng 1 — regex + alias: `WS-?(\d+)`, `LT-?(\d+)`, `Lab ?-?(\d+)`, `OH-?(\d+)` và alias tiếng Việt ("Workshop 3" → `WS-3`, "buổi lý thuyết 11" → `LT-11`) sinh từ `schedule.yaml`.
- Tầng 2 — chỉ khi tầng 1 không match và tiêu đề có từ khoá tài liệu (slide/record/recording/đề): gọi 1 call phân loại nhỏ (cùng SDK) trả `session_code | null`.
- Không xác định được buổi → `session_code = NULL` (hiện ở "Tài nguyên chung"). `kind` suy từ từ khoá tiêu đề: slide / record / doc / link.

## 5. Data model (SQLite — `companion.db`, gitignore)

```sql
posts(
  message_id TEXT PRIMARY KEY, channel TEXT, title TEXT, content TEXT,
  author TEXT, author_role TEXT, jump_url TEXT, created_at TEXT,
  hearts INTEGER, comment_count INTEGER,
  summary TEXT, tags TEXT,            -- JSON array
  image_url TEXT, image_source TEXT,  -- 'tavily' | 'placeholder'
  enriched_at TEXT, enrich_failed INTEGER DEFAULT 0,  -- số lần enrich thất bại

  prompt_version TEXT, trace_id TEXT
)
comments(id TEXT PRIMARY KEY, post_id TEXT REFERENCES posts, author TEXT,
         author_role TEXT, content TEXT, created_at TEXT)
resources(message_id TEXT PRIMARY KEY, kind TEXT, title TEXT,
          session_code TEXT NULL, author TEXT, url TEXT, created_at TEXT)
ingest_state(key TEXT PRIMARY KEY, value TEXT)   -- checkpoint mỗi kênh
```

## 6. API read-only cho UI (FastAPI router `news`)

| Endpoint | Trả về |
|---|---|
| `GET /api/news?tag=<id>` | Danh sách bài đã enrich, lọc theo tag, sort mới nhất; kèm trường `hot` (hearts + comment_count ≥ 20) |
| `GET /api/news/{message_id}` | Chi tiết bài + toàn bộ comments |
| `GET /api/resources` | Danh sách resources kèm `session_code` |

Bookmark hiện là state phía client (chưa có user identity) — ngoài phạm vi backend vòng này.

## 7. Error handling & vận hành

- **Tavily lỗi / không có ảnh đạt điều kiện** → `image_url = null`, `image_source = 'placeholder'`; UI render SVG placeholder theo màu tag đầu (đã có sẵn). Không fail bài.
- **Enrich lỗi** (sau 2 retry của SDK): giữ raw post, `tags=["other"]`, `summary` = 2 câu đầu của content (truncate 200 ký tự), tăng `enrich_failed += 1` — bài có `enrich_failed < 3` được tự thử lại ở lượt sau; đạt 3 thì giữ nguyên fallback vĩnh viễn (trừ khi `--force`).
- Xử lý tuần tự, `--limit` mặc định 20 bài/lượt (chặn chi phí bất ngờ khi backfill).
- Secrets: `OPENAI_API_KEY`, `TAVILY_API_KEY`, `DISCORD_TOKEN` qua `.env` (gitignore).
- Data khoá: DB và seed không chứa data thật ngoài quan sát đã ẩn danh; `companion.db` không commit.

## 8. Kiểm thử

- **Smoke set** `ingest/tests/smoke_posts.json`: ~10 bài (từ seed) kèm `expected_tags`; script `python -m ingest.smoke` chạy enrich và pass khi mỗi bài có **≥1 tag trùng expected** và summary ≤ 3 câu. Dùng để bắt regression khi đổi prompt version — không phải golden set chấm điểm (đây là lời gọi AI phụ; golden set thuộc Q&A core).
- **Unit (không gọi API):** linker table-driven (10+ case tiêu đề thật); store: enrich-once (chạy 2 lượt liên tiếp → lượt 2 không enrich bài nào), checkpoint, upsert comment không trùng.

## 9. Phân công gợi ý

- **Minh** (`bot/` + ingestion): `sources.py`, CLI, checkpoint, seed.
- **Nghĩa** (`backend/`): `enrich.py`, `prompts.py`, `linker.py` tầng 2, API router, trace.
- **Bình**: seed data + smoke set + unit tests.
