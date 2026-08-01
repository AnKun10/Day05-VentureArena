# Reflection cá nhân — An

> **Vai trò:** PM / Evidence & Spec Lead · thiết kế taxonomy · điều phối & tích hợp · branch `dev/An`

## 1. Vai trò của mình

Mình là PM kiêm người chủ ý tưởng sản phẩm **Companion** cho nhóm 5 người. Việc của mình
không phải viết nhiều code nhất, mà là: chốt *lát cắt* làm gì, thiết kế các **bộ phân loại
(taxonomy)** xương sống, viết canvas + spec, chia việc theo 5 branch `dev/<tên>`, và giữ cho
`main` luôn ở trạng thái chạy được để TA verify checkpoint. Mình cũng nhận thêm **lớp an toàn
cho /ask** (chống bịa) vì đó là chỗ rủi ro nhất của sản phẩm.

## 2. Phần mình làm (chỉ được tận file — để bảo vệ ở CP5/CP6)

**a) Thiết kế taxonomy** — hai bộ phân loại quyết định cách sản phẩm hiểu dữ liệu:
- *10 loại tin* cho Bản tin: `ai-model · ai-tools · dataset · api-mcp · system-design ·
  ui-ux · ai-skill · soft-skills · survey · other`. Dùng khi enrich + gom nhóm digest
  (`codebase/bot/companion_discord/formatting.py: TAG_LABELS`). Đây là taxonomy **mình tự
  định nghĩa từ quan sát kênh thật**, không lấy tag Discord làm nhãn.
- *Taxonomy loại buổi* cho Lịch học: `LT · Lab · WS · OH · MD`, kèm khung giờ theo khoá
  (K4 sáng Lý thuyết / chiều Lab, K3 ngược lại).

**b) Lớp an toàn & đánh giá cho /ask** (dựng *trên* RAG core của Nghĩa, không sửa lõi):
- Agent 4 action có **Chain-of-Thought** (`AskResult.reasoning` đứng trước khi quyết định)
  → `answer / no_info / clarify / refuse`.
- **Guardrail hậu-xử-lý `enforce_citations`** (`codebase/backend/ask/agent.py`): answer thiếu
  nguồn → back-fill URL mà tool đã trả; answer không có nguồn nào → hạ `no_info`. Chống bịa
  bằng **code**, không chỉ bằng prompt.
- **Bộ 55 câu eval** (`eval/ask_testset.json`) — có câu nguyên văn từ log Discord thật (typo,
  cụt lủn, trộn Anh-Việt) — + `eval/run_ask_eval.py` chấm action / must_cite / must_not_contain.

**c) Guardrail đầu vào** — chặn tục tĩu + prompt injection *trước khi* chạm model
(`codebase/backend/guardrails.py`), áp cho cả `PUT /bio` và `POST /api/ask`.

**d) KB governance** — chỉ ingest chunk `sensitivity_category == 'none'`, loại
`personal_data / internal_only`; KB pack để trong `.gitignore`, không đẩy lên GitHub.

**e) PM / tích hợp** — canvas CP1, spec, phân công 5 branch, review + merge PR về `main`,
viết README dạng product-showcase.

## 3. AI hỗ trợ mình thế nào

Mình dùng **Claude Code như một pair-programmer**, nhưng giữ mọi quyết định thiết kế cho
mình — đúng tinh thần *vibe-coding rule* (bị hỏi phải giải thích được):

- **AI làm phần cơ bắp:** sinh scaffold agent/tool, viết bản nháp guardrail và unit test, chạy
  bộ 55-case eval rồi tóm tắt case fail, dò lỗi vặt (CORS port, bot `.env`, Python 3.10 datetime).
- **Mình giữ phần đầu:** *định nghĩa* taxonomy (AI không tự nghĩ ra 10 loại tin — mình chốt từ
  dữ liệu thật), *chốt quality bar* (≥80% đạt **và** không bịa thông tin hệ trọng dù một lần),
  quyết định "khi nào answer / khi nào no_info", và **đọc từng diff trước khi merge** — không
  merge mù.

Nguyên tắc làm việc: *AI đề xuất, mình phán quyết và chịu trách nhiệm giải thích.*

## 4. Một bài học từ case fail của chính nhóm

**Case:** Sau khi tích hợp KB thật vào /ask, điểm eval **tụt xuống 43/55**. Nhóm câu
A1 / A4 / A6 / A11 fail cùng một kiểu: agent trả lời **đúng nội dung** nhưng **bỏ trống
`citations`** — nặng hơn là có nguy cơ trả lời không nguồn (mầm mống bịa). Mình đã thử siết
prompt ("BẮT BUỘC trích nguồn, answer mà citations rỗng là SAI") nhưng vẫn **flaky**, vì model
là xác suất — không phải lần nào cũng nghe.

**Bài học:** *Không thể ép một hành vi bắt-buộc-đúng chỉ bằng prompt.* Với ràng buộc **an toàn**
(trích nguồn, chống bịa), phải có một **guardrail deterministic hậu-xử-lý** làm lớp lưới:
prompt để model làm đúng phần lớn thời gian, **code** để đảm bảo phần còn lại không bao giờ lọt.
Mình viết `enforce_citations` (back-fill nguồn, hoặc hạ `no_info` nếu không có nguồn) → eval lên
**50/55 (91%)**, và quan trọng hơn số điểm: **0 lần bịa thông tin hệ trọng**.

**Rút ra cho lần sau:** (1) viết eval **trước** khi tích hợp data thật, để bắt regression sớm
thay vì phát hiện lúc điểm đã tụt; (2) mọi ràng buộc an toàn phải có **một lớp không-phải-LLM
đứng gác**. Mình đã áp lại chính tư duy "phòng thủ nhiều lớp" này cho guardrail đầu vào và KB
governance.
