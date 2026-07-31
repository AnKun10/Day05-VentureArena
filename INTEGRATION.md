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

> ⚠️ **Tính đến lần chạy này, chưa có API key nào được cấu hình** — mọi số đo ở trên là của đường lui
> thuần luật, và trace đều ghi `"provider": null`. Cần một key thật rồi **đo lại** trước khi khai với
> giám khảo là sản phẩm có lời gọi AI thật.

## Việc còn lại

1. **Cấp API key + đo lại** — xem AI có nâng được 19/21 không, và ghi số thật (đây là điều kiện của CP3).
2. **Nhóm chốt bỏ bot trùng** — `codebase/bot/companion_discord/` (Bot B) làm cùng 5 lệnh với Bot A;
   hiện giữ cả hai, chưa ai xoá. Xem `codebase/bot/README.md`.
3. `codebase/bot/data/*.yaml` vẫn là placeholder — chờ bản chính thức của Bình.
4. Taxonomy phân loại tin — chờ An chốt.
