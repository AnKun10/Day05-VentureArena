# Reflection cá nhân — Lê Ngọc Minh

> **Vai trò:** Discord Bot & Ingestion · branch `dev/Minh`

## 1. Vai trò của mình

Mình phụ trách toàn bộ phía Discord của **Companion**: bot 5 lệnh, worker đọc tin từ các kênh của
khoá, và cơ chế chuyển câu hỏi bot không trả lời được cho đúng TA phụ trách lớp. Sau đó mình làm thêm
phần **tích hợp 3 mảnh** (UI của Hải · backend của Nghĩa · bot của mình) khi phát hiện ba bên đang nói
ba contract khác nhau nên không nối được với nhau.

**Nói trước cho minh bạch:** phần lớn code dưới đây nằm trên nhánh `dev/Minh` (đã push lên GitHub) và
**chưa được merge vào `main`**. Nhóm cuối cùng chọn bản bot của Nghĩa (`companion_discord/`). Vì sao
lại thành ra như vậy — mình viết ở mục 4, vì đó chính là bài học lớn nhất của mình trong sự kiện này.

## 2. Phần mình làm (chỉ được tận file — để bảo vệ ở CP5/CP6)

Tất cả ở branch `dev/Minh`.

**a) Discord bot 5 lệnh** — `codebase/bot/`
`/ask` `/schedule` `/digest` `/hub` `/ta-digest`, mỗi lệnh một cog trong `cogs/`. `/ta-digest` có
chặn quyền theo role (`ta_digest_cog.py`), gom câu hỏi tồn theo lớp và gửi DM cho TA phụ trách.

**b) Quyết định trung tâm 4 action** — `codebase/bot/decision.py`
`answer / clarify / refuse_escalate / refuse_scope`, phủ đúng 4 lớp chỗ khó của đề bài. Điểm mình
cân nhắc kỹ nhất là lớp ④: câu hỏi deadline chỉ được trả lời khi buổi **thật sự có** field deadline
trong nguồn — không có thì từ chối, vì trả lời sai deadline làm học viên nộp muộn mất điểm thật.

**c) Ingestion worker** — `codebase/bot/ingestion/`
`listener.py` nghe 4 nhóm kênh và ghi metadata vào SQLite; `session_linker.py` nhận mã buổi
(`WS2`, `Workshop 3`, `Lab-10`...) để gắn tài liệu vào đúng buổi.

**d) 25 unit test** — `codebase/bot/tests/` (4 file), chạy được không cần token Discord.

**e) Golden set + eval runner** — `eval/golden_set.yaml` (21 case, ≥2 case mỗi lớp chỗ khó),
`eval/run_eval.py` xuất bảng % gồm cả case fail.

**f) Tích hợp 3 mảnh** — `codebase/backend/decision_core.py`, `codebase/backend/ai_decision.py`,
`codebase/backend/app.py`, `INTEGRATION.md`
Chuyển logic quyết định vào backend để bot và UI dùng chung một bộ não, theo đúng contract mà UI của
Hải đã thiết kế sẵn. Thêm CORS (thiếu là trình duyệt chặn sạch), `/api/feedback` cho nút "Báo sai",
`/api/health` để biết AI có đang bật thật không.

**g) Đưa lời gọi LLM về đúng chỗ quyết định** — `codebase/backend/ai_decision.py`
Bản backend cũ chỉ gọi LLM **sau khi** action đã chốt và chỉ để gọt câu chữ, nên LLM không bao giờ
đổi được `answer` → `refuse`. Mình để LLM tự phán `answerable / ambiguous / out_of_scope / no_basis`.
Riêng ranh giới ③ (đáp án / điểm / gia hạn) mình **cố ý giữ bằng luật cứng, không giao cho LLM** —
thà chặn nhầm một câu vô hại còn hơn để lọt một câu lộ đáp án. Có test khoá điều này lại
(`test_out_of_scope_rule_is_not_overridable_by_the_model`).

**h) Kịch bản & script demo** — `run-demo.ps1`, `DEMO.md`

## 3. AI hỗ trợ mình thế nào

Mình dùng Claude Code như người ngồi cạnh viết cùng, nhưng có một nguyên tắc tự đặt sau vài lần bị
hớ: **mọi thứ AI viết ra mà mình chưa chạy thì chưa tính là xong.** Nguyên tắc đó ra đời vì chính
những lần AI (và mình) sai ở mục 4.

Cách dùng cụ thể có ích nhất là **đối chiếu code với ảnh chụp server thật** thay vì để nó đoán. 6 lỗi
thật bắt được đều theo cách đó, không lỗi nào tìm ra bằng đọc code suông:

| Lỗi | Hậu quả nếu không sửa |
|---|---|
| Khớp tên kênh kiểu substring | Nuốt luôn kênh riêng `thông-báo-nhóm` của nhóm khác vào KB chung |
| Tưởng `lý-thuyết`/`thực-hành-lab` là kênh chat | Mọi bài trong 2 forum này ra `class_code=None`, TA digest không route được |
| K3 và K4 trùng số phòng (`Lab-D305`) | Câu hỏi 2 khoá gộp chung, gửi nhầm TA |
| `os.getenv(k, default)` với biến rỗng | Backend không mở nổi file SQLite |
| Thiếu `copy_global_to(guild)` | Bot login thành công nhưng sync **0** lệnh |
| `ask_cog` và `listener` lệch logic cohort | Escalation ghi mã lớp không khớp roster |

## 4. Bài học từ case fail của chính nhóm

### Fail lớn nhất: code đúng nhưng không đến được tay nhóm

Timeline có thật trong git:

| Thời điểm | Ai | Việc |
|---|---|---|
| 30/07 21:48 | mình | phát hiện `lý-thuyết`/`thực-hành-lab` là **Forum**, phòng lớp là thread |
| 30/07 22:12 | mình | phát hiện K3/K4 **trùng số phòng**, phải tách mã lớp theo khoá |
| 31/07 00:26 | An | tự làm lại forum discovery |
| 31/07 08:44 | An | tự làm lại cohort slots |

Mình tìm ra hai chỗ khó nhất **sớm hơn ~2,5 tiếng**, có test khoá lại đàng hoàng. Nhưng mình chỉ
`git push` lên nhánh rồi coi như xong — **không mở Pull Request, không nhắn cho ai một câu nào**.
Kết quả là An phải tự vấp lại đúng hai chỗ đó và tự sửa lại từ đầu. Cả nhóm mất gần một buổi làm
trùng việc, và bản của mình cuối cùng không vào `main`.

Bài học mình rút ra: **push không phải là bàn giao.** Việc chỉ tính là xong khi người khác dùng được
nó. Một tin nhắn 3 dòng *"tôi vừa phát hiện lý-thuyết là forum, K3/K4 trùng phòng, code ở nhánh này"*
sẽ tiết kiệm cho nhóm nhiều giờ hơn toàn bộ phần test mình viết. Trong một sự kiện 1,5 ngày, chi phí
của việc im lặng lớn hơn nhiều so với chi phí làm phiền người khác.

### Fail kỹ thuật: đo trên hệ thống đã chết mà không biết

Sau khi cắm API key, mình chạy đo và báo với cả nhóm là "AI đã bật". Thực tế: backend cũ vẫn giữ cổng
8000, tiến trình mới báo lỗi bind rồi chết, còn bài đo vẫn vui vẻ gọi vào backend cũ với key đã cạn
quota. Mọi trace ghi `provider: null` mà mình vẫn kết luận ngược lại — vì mình nhìn con số điểm thay vì
nhìn *bằng chứng có gọi AI hay không*. Sửa xong đo lại thì sự thật là: bật AI vào điểm **giảm** từ
19/21 xuống 17/21, và chỉ 7/21 lượt thật sự tới được model do rate limit.

Bài học: **con số đẹp không chứng minh hệ thống chạy đúng.** Phải kiểm tra bằng dấu vết độc lập —
ở đây là `provider` trong trace — trước khi tin vào kết quả đo. Đây cũng là lý do mình thêm
`/api/health` trả `ai_enabled`, và cho `run-demo.ps1` in cảnh báo to khi AI chưa bật: để không ai
trong nhóm rơi vào đúng cái bẫy đó lần nữa lúc đang demo.

### Fail nhỏ nhưng đáng nhớ: viết script demo mà không chạy thử

`run-demo.ps1` mình viết xong, đọc thấy hợp lý, commit luôn. Đến lúc chạy thật thì nó **không parse
nổi một dòng nào** — file không có BOM, PowerShell 5.1 đọc theo ANSI nên chữ tiếng Việt trong comment
vỡ và làm gãy chuỗi. Nếu không thử trước, cả nhóm sẽ phát hiện đúng lúc cần nó nhất.
Từ đó mình viết file `.ps1` thuần ASCII, và không commit thứ gì mình chưa chạy ít nhất một lần.
