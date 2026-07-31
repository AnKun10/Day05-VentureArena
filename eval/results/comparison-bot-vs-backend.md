# So sánh 2 phương án quyết định AI — `decision.py` (bot) vs `codebase/backend` (RAG API)

**Ngày chạy:** 2026-07-31 · **Bộ đo:** `eval/golden_set.yaml` (21 case) · **Người chạy:** Minh

Repo hiện có **hai** implementation cho cùng một quyết định trung tâm (answer / clarify / refuse).
Tài liệu này đo cả hai trên cùng bộ case để nhóm chọn có căn cứ, thay vì chọn theo cảm tính.
Đây cũng chính là mục **§8 Multi-prototype** trong template spec (2 phương án khác trục ở một quyết định
thiết kế có tên → thử → chọn → giữ bằng chứng cả phương án bị loại).

## Cách chạy lại

```bash
# Phương án A — decision.py (rule-based, trong bot)
python eval/run_eval.py

# Phương án B — backend RAG API
cd codebase/backend
COMPANION_DATA_DIR=../bot/data python -m uvicorn app:app --port 8011
# rồi POST từng case trong golden_set.yaml tới http://127.0.0.1:8011/api/ask
```

Backend chỉ có 3 action (`answer`/`clarify`/`refuse`), bot có 4 (tách thêm `refuse_scope`).
Khi chấm, `refuse_escalate` và `refuse_scope` của bot đều map về `refuse` — tức là **đã chấm có lợi
cho backend**, không phạt nó vì thiếu action.

## Kết quả

| | Phương án A — `decision.py` | Phương án B — `codebase/backend` |
|---|---|---|
| Đạt (theo expected gốc) | **19/21 — 90,5%** | **8/21 — 38,1%** |
| Đạt (sau khi sửa 2 expected sai của tôi, xem ghi chú) | 21/21 — 100% | 10/21 — 47,6% |
| Gọi AI thật | ❌ Không | ⚠️ Có code gọi, nhưng **không ở quyết định trung tâm** (xem dưới) |
| Xử lý ③ ngoài phạm vi | ✅ Có nhánh riêng | ❌ Không có |
| Trace log cho eval | Ghi vào SQLite `ask_logs` | ✅ Ghi file JSON `eval/traces/` |

*Ghi chú về 2 expected sai:* case c15 và c17 tôi ghi expected là `refuse` nhưng thực tế cả hai
implementation đều trả lời được (schedule placeholder chỉ có 1 buổi mỗi loại nên type-match không hề
mơ hồ). Lỗi ở bộ đo của tôi, không phải lỗi sản phẩm — giữ nguyên trong bảng và ghi rõ, không sửa
lén số liệu.

## Vì sao backend fail — 4 nhóm lỗi

**① Bịa bằng retrieval — nguy hiểm nhất.** Câu hoàn toàn ngoài phạm vi vẫn được trả lời tự tin:

- `"Con mèo của tôi bị ốm thì sao?"` → trả lời FAQ về **thẻ vào phòng lab**, confidence 0.57.
- `"Hôm nay có thông báo gì mới không?"` → trả lời FAQ **đăng ký office hour**, confidence 0.75.

Nguyên nhân: `answer()` trong `companion_rag.py` chọn source có **word-overlap cao nhất** rồi trả về,
chỉ refuse khi `score <= 0.5`. Câu tiếng Việt bất kỳ luôn trùng vài từ với một FAQ nào đó, nên ngưỡng
này lọt rất nhiều.

**Trả về dòng YAML thô, thậm chí trả về câu HỎI thay vì câu TRẢ LỜI.** `_excerpt()` chọn dòng có
overlap cao nhất — mà dòng `q:` (câu hỏi FAQ) bao giờ cũng giống câu người dùng hỏi hơn dòng `a:`:

- `"Không có thẻ vào phòng lab thì làm sao?"` → trả về `"q: Không có thẻ vào phòng lab / thẻ lỗi thì làm sao?"`
- `"Lab-10 deadline khi nào?"` → trả về `"code: Lab-10"`

**Confidence sai lệch nghiêm trọng.** `confidence` chỉ là tỉ lệ trùng từ, không phải độ tin cậy thật.
4 case trả lời **sai** nhưng confidence = **1.0** (c13, c14, c15, c17). Đây là kiểu lỗi người dùng
không tự phát hiện được — thấy số cao thì tin ngay.

**④ Mất nguyên tắc precision cho câu hỏi deadline.** Đúng chỗ `MASTERPLAN.md §4` xác định
cost-of-error cao nhất (*"trả lời sai deadline → học viên nộp muộn, mất điểm thật"*):

- `"LT-11 deadline nộp gì không?"` → trả lời FAQ *"Nộp bài lab ở đâu, deadline khi nào?"* — trong khi
  LT-11 **không hề có** field deadline. Bot A từ chối đúng ở case này.
- `"WS-3 deadline nộp báo cáo là khi nào?"` và `"MD-5 deadline..."` — cùng lỗi, confidence 1.0.

## Điểm quan trọng nhất: lời gọi AI KHÔNG nằm ở quyết định trung tâm

Đọc `codebase/backend/app.py`:

```python
result = answer(request.question, load_sources(DATA_DIRECTORY))   # <- quyết định ở ĐÂY, thuần rule-based
if result.action == "answer":
    excerpt, provider = model_excerpt(request.question, result.answer)   # <- LLM chỉ chạy SAU, chỉ khi đã answer
    if excerpt:
        result = replace(result, answer=excerpt)                          # <- chỉ đổi CHỮ, không đổi quyết định
```

LLM chỉ được gọi **sau khi** action đã chốt, chỉ khi action là `answer`, và chỉ để rút gọn đoạn trích.
Nó **không bao giờ** đổi được `answer` → `refuse`, không đổi được confidence.

Hệ quả thực tế: **thêm API key sẽ KHÔNG sửa được case fail nào ở trên** — vì cả 11-13 case fail đều là
lỗi *quyết định*, xảy ra trước khi LLM được gọi. (Lần chạy này không có API key nên `model_excerpt()`
trả `(None, None)` và bị bỏ qua; nhưng kể cả có key, các case trên vẫn fail y hệt.)

Rubric R5 yêu cầu *"≥1 lời gọi AI thật **ở quyết định trung tâm**"* — kiến trúc hiện tại chưa đáp ứng
đúng chữ đó, vì AI đang ở vai trò hậu xử lý văn bản.

## Điểm ĐÁNG GIỮ của backend

Không phải bỏ hết — có 3 thứ tốt hơn bản của bot:

1. **Có tích hợp API thật** với chuỗi fallback 4 provider (OpenAI → Gemini → OpenRouter → Cerebras),
   đọc key từ env, không hardcode.
2. **Chống bịa ở tầng excerpt**: bắt LLM trả JSON schema cố định và **kiểm tra `excerpt in source_text`**
   — LLM không thể chế ra chữ không có trong nguồn. Thiết kế tốt, nên giữ.
3. **Trace log ra file** `eval/traces/*.json` — đúng thứ rubric R5 đòi ("log/trace trong repo").

## Đề xuất (cần cả nhóm quyết, không phải quyết định của riêng Minh)

Giữ **logic quyết định của `decision.py`** (đủ 4 lớp chỗ khó, 90,5%) + lấy **tầng gọi AI của backend**
(provider fallback + validate excerpt + trace log), và **đưa lời gọi AI vào đúng chỗ quyết định** thay vì
hậu xử lý — ví dụ để LLM phán "câu hỏi này có được trả lời từ nguồn này không / có ngoài phạm vi không",
rồi mới sinh câu trả lời.

Cần thống nhất với Nghĩa trước khi làm — đây là code của bạn ấy, không tự ý thay.