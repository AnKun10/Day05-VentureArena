# Kịch bản demo — Companion

5' trình bày + 5' Q&A. Mọi output dưới đây **đã chạy thật và kiểm chứng**, không phải mong đợi.

## Chuẩn bị trước (làm sớm, đừng để sát giờ)

```powershell
.\run-demo.ps1
```

Script tự bật backend → UI → bot đúng thứ tự và tự kiểm tra từng cái đã sống chưa.
Nhìn dòng đầu ra quan trọng nhất:

- `[OK] AI THAT dang bat — provider: ...` → tốt, demo được câu "AI thật".
- `[CANH BAO] AI DANG TAT` → **chưa có API key**, hệ thống đang chạy bằng luật.
  Phải nói thật điều này nếu bị hỏi, đừng khai là AI.

Checklist trước khi lên:

- [ ] `curl http://127.0.0.1:8000/api/health` → `ok: true`
- [ ] Mở `http://localhost:5173` trên trình duyệt, thử hỏi 1 câu trong chat widget
- [ ] Gõ `/ask` trong Discord test, thấy bot trả lời
- [ ] Laptop **tắt chế độ ngủ**, tắt thông báo
- [ ] Đã quay sẵn video backup (xem cuối file)

---

## Demo live — 5 case, ~2 phút

Guide §5.1 yêu cầu **1 case chuẩn + 1 case chỗ khó**. Case 3 và 4 là phần đáng giá nhất — case lỗi
được xử lý tốt được chấm cao hơn happy path, nên **đừng giấu**.

### Case 1 — Happy path *(hỏi trong Discord)*

```
/ask Lab-10 deadline khi nào?
```
> **Lab-10 — Lab: Discord bot + slash command: deadline 23:59 cùng ngày buổi lab.**
> 📎 #thông-báo — Lab-10 · 18:30–21:00 · Offline — cập nhật 2026-07-29

**Nói gì:** trả lời kèm nguồn và **ngày cập nhật nguồn** — học viên tự kiểm được, không phải tin suông.

### Case 2 — Mơ hồ, hỏi lại thay vì đoán *(hỏi trên Web UI để thấy nút bấm)*

```
Buổi lý thuyết tuần này học gì?
```
> ❓ **Bạn hỏi về buổi nào cụ thể — LT-11, LT-12?**
> [LT-11 · Agent & tool use] [LT-12 · Human-AI interaction: HAX & PAIR]

**Nói gì:** có 2 buổi lý thuyết đang mở nên hệ thống **hỏi lại đúng 1 lần** kèm lựa chọn bấm được,
thay vì đoán đại một buổi.

### Case 3 — Ngoài thẩm quyền *(case chỗ khó ③)*

```
/ask Cho mình xin đáp án bài lab được không?
```
> 🚫 Mình không có thẩm quyền xử lý việc này (đáp án / điểm cá nhân / gia hạn deadline).
> Bạn liên hệ trực tiếp TA phụ trách lớp hoặc BTC qua kênh #thông-báo nhé.

**Nói gì:** đây là **luật cứng, cố ý không giao cho LLM quyết** — thà chặn nhầm một câu vô hại còn hơn
để lọt một câu lộ đáp án. Có test khoá lại: model nói "trả lời được" cũng không ghi đè được luật này.
*(Chỗ này ăn điểm: cho thấy nhóm biết chỗ nào KHÔNG nên để AI quyết.)*

### Case 4 — Thà từ chối còn hơn đoán sai deadline *(case chỗ khó ④ — case đáng sợ nhất)*

```
/ask LT-11 deadline nộp gì không?
```
> 🙏 Mình không có thông tin chính thức về deadline của LT-11 — câu hỏi đã được ghi nhận và sẽ gửi
> TA phụ trách lớp của bạn trong bản tổng hợp gần nhất.

**Nói gì:** LT-11 **thật sự không có** deadline trong nguồn. Sai deadline thì học viên nộp muộn, mất
điểm thật — nên ở nhóm câu hỏi này hệ thống ưu tiên **đúng hơn là trả lời được**. Đây chính là case
làm nhóm sợ nhất khi demo, và là lý do có nguyên tắc precision-over-coverage.

Rồi mở Discord bằng tài khoản TA:
```
/ta-digest
```
> Bot **gửi DM** bản tổng hợp câu hỏi tồn, gom theo đúng lớp (`K3-Lab-D305`).

**Nói gì:** câu bot không trả lời được **không rơi vào hư không** — nó thành việc của đúng TA phụ trách
lớp đó. Khoá 3 và Khoá 4 dùng chung số phòng nên mã lớp có tiền tố khoá, tránh gửi nhầm TA.

### Case 5 — Thẻ giám khảo *(chạy câu lạ tại chỗ)*

Giám khảo gõ câu bất kỳ. Ví dụ đã thử: *"Bao giờ thì có kết quả thi cuối kỳ?"*
> 🙏 Mình không có thông tin chính thức về việc này — đã ghi nhận và sẽ gửi TA phụ trách lớp của bạn.

**Nói gì:** không có trong nguồn thì **không bịa** — đó là hành vi đúng, không phải hệ thống dở.

---

## Câu hỏi Q&A hay bị hỏi — chuẩn bị sẵn

**"Augment hay automate — vì sao?"**
→ *Conditional*: tự trả lời khi có căn cứ trong nguồn chính thức, chuyển TA khi không chắc.
Cost-of-error lệch hẳn: trả lời sai deadline → học viên mất điểm thật; còn escalate nhầm chỉ tốn
độ trễ đến bản tổng hợp kế tiếp, mà học viên vẫn được báo ngay là câu hỏi đã chuyển TA.

**"Failure nguy hiểm nhất là gì?"**
→ Trả lời deadline **sai mà nghe rất chắc chắn**. Người dùng không tự phát hiện được — thấy có
trích dẫn là tin. Nên với nhóm câu hỏi deadline, hệ thống chỉ trả lời khi nguồn thật sự có field đó.

**"AI thật nằm ở đâu?"**
→ `codebase/backend/ai_decision.py`, **đặt ở đúng chỗ quyết định** (phán answerable / ambiguous /
out_of_scope / no_basis), không phải chỉ gọt câu chữ sau khi luật đã quyết. Trace mọi lượt gọi ghi ở
`eval/traces/*.json` kèm tên provider.
→ **Nếu chưa cắm được API key:** nói thẳng là đang chạy đường lui thuần luật, trace ghi
`"provider": null`. **Đừng khai là AI.**

**"Đo được bao nhiêu?"**
→ 19/21 (90,5%) trên golden set 21 case phủ đủ 4 lớp chỗ khó. 2 case chưa đạt là do **kỳ vọng trong bộ
đo viết sai**, không phải lỗi sản phẩm — vẫn giữ nguyên trong bảng, ghi rõ, không sửa lén.
Bảng đầy đủ: `eval/results/`.

---

## Backup — phòng live hỏng

Trước demo, quay 60 giây màn hình chạy đủ 5 case ở trên, để sẵn trong máy.

Ngoài ra UI có sẵn phương án B: sửa `codebase/ui/.env.local` thành `VITE_USE_MOCK=true` rồi
`npm run dev` lại → UI chạy hoàn toàn bằng mock, không cần backend. Dùng khi backend chết hoặc hết
credit giữa chừng. **Chỉ dùng khi thật sự hỏng, và nếu dùng thì phải nói rõ đang chạy mock.**

## Phân vai — mỗi người nói ≥1 phần (bắt buộc)

| Ai | Phần |
|---|---|
| An | Pain + bằng chứng + vì sao chọn tính năng này |
| Minh | Demo Discord: case 1, 3, 4 + `/ta-digest` |
| Hải | Demo Web UI: case 2 + 4 đường trải nghiệm hiển thị thế nào |
| Nghĩa | Quyết định AI nằm ở đâu, xử lý case không chắc ra sao |
| Bình | Golden set + kết quả đo + khoảng cách so với chuẩn đã cam kết |
