# Tích hợp 3 phần — UI (Hải) · Backend (Nghĩa) · Discord bot (Minh)

Trước tích hợp, ba phần chạy độc lập và **nói ba contract khác nhau** nên không nối được:
UI cần `citations` dạng object, backend trả list string, bot dùng shape riêng trong `decision.py`.
Ngoài ra bot và UI đi qua hai bộ não khác nhau nên **cùng một câu hỏi có thể ra hai câu trả lời khác nhau**.

## Kiến trúc sau tích hợp

```
Discord  ──/ask──►  bot (codebase/bot)  ──HTTP──┐
                                                 ├──►  backend (codebase/backend)  ──►  LLM
Trình duyệt ──►  Web UI (codebase/ui)  ──HTTP──┘         decision_core + ai_decision
```

Một cửa duy nhất: `POST /api/ask`. Bot và UI cùng gọi, nên không thể trả lời lệch nhau.

## Contract đã chốt (theo thiết kế sẵn có của UI — `codebase/ui/src/api/client.js`)

```jsonc
POST /api/ask   { "question": str, "clarify_context": str|null, "class_name": str|null }

{
  "action": "answer" | "clarify" | "refuse",
  "answer": "...",
  "confidence": 0.95,
  "citations": [{ "source", "session_code", "quote", "updated", "url" }],
  "clarify_options": ["Lab-10 · ...", "Lab-11 · ..."],
  "escalated_to": null | { "ta", "class", "queue_position" },
  "trace_id": "tr_0a784506"
}
```

`action` chỉ có 3 giá trị, nhưng **4 đường trải nghiệm** phân biệt được nhờ `escalated_to`:

| Đường (đề bài) | action | escalated_to |
|---|---|---|
| Happy | `answer` | `null` |
| ② Mơ hồ | `clarify` | `null` |
| ③ Ngoài phạm vi / thẩm quyền | `refuse` | **`null`** — không tạo việc cho TA |
| ① Không có căn cứ | `refuse` | **`{ta, class, ...}`** — vào hàng đợi TA |

Đây vốn là thiết kế của Hải; backend và bot nay khớp theo.

`POST /api/feedback` — nút "Báo sai" trên UI, đẩy câu hỏi vào hàng đợi TA xác nhận.
`GET  /api/health` — cho biết AI có đang bật thật không (`ai_enabled`, `providers`), khỏi phải đoán lúc demo.

## Lời gọi AI nằm ở đâu (điểm quan trọng cho R5)

```
1. Luật chặn ③ ngoài phạm vi  ← chặn cứng, KHÔNG hỏi LLM, LLM không được ghi đè
2. LLM quyết định phần còn lại ← answerable / ambiguous / out_of_scope / no_basis
3. Không có key / LLM lỗi     ← lui về quyết định thuần luật, sản phẩm vẫn chạy
```

Khác với bản backend cũ (LLM chỉ chạy **sau khi** action đã chốt và chỉ gọt câu chữ — nên thêm API key
cũng không sửa được case sai nào), giờ LLM **quyết định action**. Xem `codebase/backend/ai_decision.py`.

Hai thứ giữ lại từ bản cũ vì thiết kế tốt: chuỗi fallback nhiều provider, và bắt buộc `excerpt` phải là
**substring có thật** của nguồn — LLM không chế ra được chữ không tồn tại.

Ranh giới ③ cố ý **không** uỷ cho LLM: thà chặn nhầm một câu vô hại còn hơn để lọt một câu lộ đáp án/điểm.
Có test khoá điều này (`tests/test_companion_api.py::test_out_of_scope_rule_is_not_overridable_by_the_model`).

## Kết quả đo

| | Golden set (21 case) |
|---|---|
| Backend **trước** tích hợp | 8/21 — 38,1% |
| Backend **sau** tích hợp | **19/21 — 90,5%** |
| `decision.py` trong bot (đường lui) | 19/21 — 90,5% |

Bất biến đã kiểm: **mọi `answer` đều có citation** (không có câu trả lời trôi nổi không nguồn).
Chi tiết: `eval/results/run-integrated.txt` · `eval/results/comparison-bot-vs-backend.md`.

2 case chưa đạt (c15, c17) là **kỳ vọng trong bộ đo bị viết sai**, không phải lỗi sản phẩm — giữ nguyên
trong bảng và ghi rõ thay vì sửa lén số liệu.

## Chạy cả hệ thống

Ba cửa sổ terminal:

```bash
# 1. Backend  (bắt buộc chạy trước)
cd codebase/backend
pip install -r requirements.txt
uvicorn app:app --port 8000

# 2. Web UI
cd codebase/ui
cp .env.local.example .env.local     # VITE_USE_MOCK=false -> gọi backend thật
npm install && npm run dev            # http://localhost:5173

# 3. Discord bot
cd codebase/bot
pip install -r requirements.txt
cp .env.example .env                  # điền DISCORD_TOKEN + DISCORD_GUILD_ID
python main.py
```

Kiểm tra nhanh backend sống: `curl http://127.0.0.1:8000/api/health`

## Bật AI thật

Backend chạy được **không cần** API key (tự lui về luật, `ai_enabled: false`). Muốn bật AI thật:

```bash
# codebase/backend/.env   (KHÔNG commit — .gitignore đã chặn)
GEMINI_API_KEY=...
# hoặc OPENAI_API_KEY / OPENROUTER_API_KEY / CEREBRAS_API_KEY
AI_PROVIDER_ORDER=gemini,openai,openrouter,cerebras
```

Xác nhận đã bật: `curl http://127.0.0.1:8000/api/health` → `"ai_enabled": true`.

### Trạng thái AI (cập nhật sau khi cắm key Gemini thật)

✅ **Đã có lời gọi AI thật, ở đúng chỗ quyết định.** Trace ghi `"provider": "gemini"`.

Ba thứ phải sửa mới gọi được, đều phát hiện bằng cách gọi thật chứ không đoán:

| Vấn đề | Xử lý |
|---|---|
| SDK `genai.Client().interactions.create()` ném "Connection error" (API còn experimental) | Chuyển sang REST `v1beta/models/{model}:generateContent` |
| Model mặc định `gemini-3.5-flash` → 404 (không tồn tại); `gemini-2.0-flash*` → 429 `limit: 0` | Dò 42 model của key, chỉ **`gemini-2.5-flash-lite`** còn hạn mức |
| Lượt đo đầu: `"Lab-10 deadline khi nào?"` bị model phán `ambiguous` dù đã nêu rõ mã buổi | Sửa prompt: nêu rõ có mã buổi khớp SOURCE thì KHÔNG phải mơ hồ, thêm ví dụ cho từng verdict → 5/5 đúng |

### Model dùng được PHỤ THUỘC VÀO KEY — phải dò lại mỗi lần đổi key

Đã gặp thật với 2 key khác nhau, kết quả ngược hẳn nhau:

| Model | Key #1 | Key #2 (đang dùng) |
|---|---|---|
| `gemini-3.5-flash` | 404 — không tồn tại | ✅ chạy |
| `gemini-2.5-flash-lite` | ✅ chạy | 404 — "no longer available" |
| `gemini-2.0-flash*` | 429 `limit: 0` | 404 |

**Dò model cho key mới:**

```bash
KEY=<key của bạn>
# 1. Liệt kê model key này thấy
curl -s "https://generativelanguage.googleapis.com/v1beta/models" -H "x-goog-api-key: $KEY"

# 2. Gọi thử một model cụ thể — có hạn mức thật hay không chỉ biết khi gọi
curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/<MODEL>:generateContent" \
  -H "x-goog-api-key: $KEY" -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"say ok"}]}]}'
```

Model chạy được thì khai vào `codebase/backend/.env` → `GEMINI_MODEL=<model>`, không phải sửa code.

### ⚠️ Rate limit — ảnh hưởng trực tiếp tới demo

Cả hai key đều bị giới hạn, chỉ khác mức độ. Key #1: 20 request/ngày, gọi lần 2 đã 429.
Key #2 thoáng hơn (5 lần liên tiếp vẫn được) nhưng **vẫn không chịu nổi 21 lượt liên tục**.

Đo thật khi chạy trọn golden set với key #2: chỉ **7/21 lượt tới được AI**, 14 lượt còn lại rơi về luật.

Đã thêm **cache verdict** (`codebase/backend/.ai_cache.json`): câu đã hỏi thì lấy lại verdict AI thật cũ
thay vì đốt thêm quota, để dành hạn mức cho **câu lạ giám khảo hỏi tại chỗ** — đúng lúc bắt buộc phải
gọi thật. Tắt cache khi cần đo trung thực: `AI_CACHE=0`.

**Nên làm trước demo:** thêm key dự phòng (`OPENROUTER_API_KEY`, hoặc key Gemini từ tài khoản Google
khác) — `AI_PROVIDER_ORDER` sẽ tự chuyển sang provider kế tiếp khi cái đầu hết hạn mức.

### Kết quả đo với AI thật

| Cấu hình | Điểm | Ghi chú |
|---|---|---|
| Thuần luật (không AI) | **19/21 — 90,5%** | ổn định, không phụ thuộc mạng/quota |
| Có AI (key #2) | **17/21 — 81,0%** | nhưng chỉ 7/21 lượt thật sự tới AI, còn lại fallback |

**Nói thẳng: bật AI vào chưa làm điểm tốt hơn.** Hai case AI làm sai mà luật làm đúng:

- `"Buổi học sắp tới là gì?"` — AI phán `no_basis` (từ chối) trong khi đúng ra phải `ambiguous` (hỏi lại),
  vì nguồn có nhiều buổi.
- `"Điểm danh online được không?"` — AI trả lời từ FAQ điểm danh; kỳ vọng trong bộ đo là từ chối.
  Case này **có thể do kỳ vọng viết sai**, cần xem lại chứ không chắc AI sai.

Việc chạy nửa AI nửa luật (do rate limit) khiến hành vi **không nhất quán giữa các lượt** — đó mới là
vấn đề đáng lo hơn con số, và là lý do cần key dự phòng trước khi demo.
Chi tiết từng case: `eval/results/run-with-real-ai.txt`.

## Việc còn lại

1. **Cấp API key + đo lại** — xem AI có nâng được 19/21 không, và ghi số thật (đây là điều kiện của CP3).
2. **Nhóm chốt bỏ bot trùng** — `codebase/bot/companion_discord/` (Bot B) làm cùng 5 lệnh với Bot A;
   hiện giữ cả hai, chưa ai xoá. Xem `codebase/bot/README.md`.
3. `codebase/bot/data/*.yaml` vẫn là placeholder — chờ bản chính thức của Bình.
4. Taxonomy phân loại tin — chờ An chốt.
