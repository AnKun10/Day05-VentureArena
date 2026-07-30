# Spec — RecSys: Gợi ý bản tin cá nhân hoá (Qdrant)

> Phạm vi: package `recsys/` trong backend (embed news → Qdrant → recommend), API users/bookmarks/recommendations, và nối UI phần "Dành cho bạn" (thay Hot trend). Feed/tag-filter/detail của UI vẫn mock — ngoài phạm vi.
> Tham chiếu: spec ingestion `2026-07-31-news-ingestion-pipeline-design.md` (Store, enrich-once, seeds).

## 1. Quyết định đã chốt

| Quyết định | Lựa chọn |
|---|---|
| Vector DB | **Qdrant embedded local** — `QdrantClient(path="qdrant_data/")`, không cần server; đổi sang server chỉ đổi cách khởi tạo client |
| Embedding | OpenAI `text-embedding-3-small` (1536d, cosine); env `EMBED_MODEL` |
| Tín hiệu sở thích | **Bio + danh sách news đã bookmark** → agent suy luận → embed đoạn sở thích → retrieve |
| Nguồn bio | User nhập/sửa trên UI (bảng `users`); default best-effort từ Discord (nickname/roles — **bot API không đọc được About Me**, ghi nhận giới hạn); seed 3 user demo bio khác nhau |
| Công thức điểm | `score = 0.5·cos(user, news) + 0.25·eng + 0.25·rec` với `eng = log1p(hearts+comments)/log1p(max)`, `rec = exp(−tuổi_giờ/72)` |
| Đa dạng chủ đề | **MMR** λ=0.7 khi chọn k bài: `argmax λ·score − (1−λ)·max cos(v, đã_chọn)` |
| Fallback | User không bio & không bookmark → trọng số sim=0 (hot trend thuần engagement+recency, vẫn qua MMR) |
| Loại trừ | Bài user đã bookmark KHÔNG xuất hiện trong gợi ý |
| Cache | Profile inference theo `bio_hash = sha256(bio + sorted(bookmark_ids))`; **lazy re-infer** khi gọi recommendations mà hash stale. Embed news một lần (`embedded_at`), `--force` re-embed |
| k mặc định | 6 (UI hiển thị 3, lấy dư để user thấy thêm khi refresh) |

## 2. Package `recsys/`

```
codebase/backend/recsys/
├── __init__.py        # re-export public API
├── embedder.py        # embed_texts(texts, cfg) -> list[vector]  (OpenAI embeddings API)
├── vectorstore.py     # NewsVectors / UserVectors trên Qdrant embedded
├── profile.py         # users table CRUD + profile_inferencer agent + ensure_profile()
├── recommend.py       # score + MMR + recommend(user_id, k)
├── prompts/
│   └── interest_v1.py # prompt suy luận sở thích (INTEREST_V1, đăng ký registry)
└── seeds/users.json   # 3 user demo
```

- **`embedder.py`**: `embed_texts(texts: list[str], cfg) -> list[list[float]]` — OpenAI embeddings, batch 1 call. Text của news = `f"{title}\n{summary_vi}\nTags: {', '.join(tag labels)}"`.
- **`vectorstore.py`**: class `VectorStore(path)` bọc QdrantClient local; collections `news` và `user_profiles` (cosine, 1536). API: `upsert_news(message_id, vector, payload)` (payload: tags, created_at, hearts, comment_count), `update_news_payload(message_id, hearts, comment_count)`, `all_news() -> list[(id, vector, payload)]`, `upsert_user(user_id, vector)`, `get_user(user_id) -> vector|None`. ID Qdrant = int(message_id) / hash user_id.
- **`profile.py`**:
  - SQLite (dùng chung `Store.conn` hoặc bảng riêng qua Store mở rộng): `users(user_id TEXT PK, name, bio, bio_source, bio_hash, interest_summary, interest_tags TEXT)` + `bookmarks(user_id, message_id, created_at, PRIMARY KEY(user_id, message_id))`.
  - Agent `profile_inferencer` (Agents SDK, `gpt-5-mini`, output `InterestProfile{interest_summary_vi: str, interest_tags: list[TagId] 1-4}`; không tool). Input = bio + tối đa 10 bookmark gần nhất (title + tags + summary cắt 150 ký tự). Prompt `INTEREST_V1` trong `recsys/prompts/`.
  - `ensure_profile(user_id)`: tính hash hiện tại; nếu khác `bio_hash` đã lưu → chạy agent → embed interest_summary → upsert `user_profiles` → lưu hash. Trace JSON vào `eval/traces/recsys/<user_id>.json`.
- **`recommend.py`**: thuần hàm, test được không cần API: `hybrid_scores(user_vec|None, items, now) -> list[(id, score, parts)]`, `mmr_select(scored, vectors, k, lam=0.7)`, `recommend(store, vs, cfg, user_id, k=6)` — loại bài đã bookmark, trả `[{news…, score, parts:{sim, eng, rec}}]`.

## 3. Hook vào pipeline ingestion

Trong `run_once` sau bước enrich: các bài `enriched_at IS NOT NULL AND embedded_at IS NULL` (hoặc mọi bài nếu `--force`) → embed batch → upsert Qdrant → set `embedded_at` (cột mới trong `posts`, migration `ALTER TABLE` an toàn nếu thiếu). Mỗi lượt chạy cũng `update_news_payload` hearts/comment_count cho bài đã embed (giữ engagement tươi). Stats thêm `embedded: n`.

## 4. API mới (router trong `api/main.py`)

| Endpoint | Hành vi |
|---|---|
| `GET /api/users` | Danh sách users (id, name, bio, interest_tags) — seed nạp lần đầu nếu bảng trống |
| `PUT /api/users/{id}/bio` body `{bio}` | Cập nhật bio (`bio_source='manual'`); KHÔNG infer ngay (lazy) |
| `GET /api/users/{id}/bookmarks` | Danh sách message_id đã bookmark |
| `PUT /api/users/{id}/bookmarks/{message_id}` / `DELETE ...` | Toggle bookmark |
| `GET /api/recommendations?user_id=&k=6` | `ensure_profile(user_id)` (lazy re-infer nếu stale) → recommend → trả news + score parts. User không tồn tại → 404 |

## 5. UI — section "✨ Dành cho bạn" (NewsPage)

- Thay header "Hot trend": dropdown chọn user (từ `GET /api/users`) + nút "Sửa bio" mở Dialog (textarea + Save → PUT bio).
- Card gợi ý: giữ layout hot-card hiện tại + dòng nhỏ lý do (✨ %match · 🔥 tương tác · 🕐 mới) từ `parts`.
- Bookmark button trên card (cả feed lẫn recommend) khi đã chọn user → gọi PUT/DELETE bookmark API rồi refetch recommendations; chưa chọn user → như cũ (local state).
- **Graceful fallback:** API không chạy/không có user → section tự quay về Hot trend tính từ mock như hiện tại; toast/ghi chú nhỏ "demo offline".
- Base URL API: `http://localhost:8000` (hằng số `API_BASE` trong `src/lib/api.js`).

## 6. Error handling & chi phí

- Qdrant local hỏng/khoá (process khác giữ) → API recommendations trả 503 với message rõ; UI fallback mock.
- Embedding lỗi → bỏ qua bài đó lượt này (không set `embedded_at`), log; không chặn pipeline.
- Inference lỗi → giữ profile cũ (nếu có) hoặc fallback no-bio; không 500.
- Chi phí: embed ~10-vài trăm news × text-embedding-3-small (không đáng kể); inference 1 call/lần đổi bio-bookmark; lazy nên không gọi thừa.
- `qdrant_data/` vào `.gitignore`.

## 7. Kiểm thử

- Unit (không API ngoài): `hybrid_scores` (bài mới điểm rec cao hơn; engagement chuẩn hoá đúng; user_vec=None → sim=0), `mmr_select` (2 vector gần trùng không cùng vào top-2 khi λ=0.7), vectorstore round-trip trên Qdrant tmp path, bio_hash cache (đổi bookmark → hash đổi), recommend loại bài đã bookmark, API tests (TestClient + Store/VectorStore tmp, inference mock qua injectable runner như enrich).
- Smoke tay (key thật): script `python -m recsys.smoke` — embed 10 seed + 3 user demo, in top-3 mỗi user kèm score parts; kỳ vọng 3 user ra danh sách khác nhau rõ rệt.

## 8. Phân công gợi ý

- **Nghĩa**: embedder, vectorstore, recommend, hook pipeline, API.
- **An**: prompt INTEREST_V1 + tinh chỉnh trọng số sau smoke.
- **Hải**: UI section Dành cho bạn + bookmark sync.
- **Bình**: seeds users + unit tests + smoke.
