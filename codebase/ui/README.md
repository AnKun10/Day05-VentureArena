# Companion UI — demo (mock data, chưa nối backend)

Web UI thống nhất của **Personalized Discord Companion Agent** (xem `MASTERPLAN.md` ở gốc repo).
Discord bot sẽ gửi link trang này khi user gõ `/hub`.

## Chạy

```bash
npm install
npm run dev   # mở http://localhost:5173
```

## 3 trang

| Trang | Nội dung | Nguồn dữ liệu (khi nối backend) |
|---|---|---|
| **Lịch học** | Calendar tuần kiểu Google Calendar, block theo buổi (LT/Lab/WS/OH/MD). Bấm block → modal: thông tin buổi, link Zoom/slide/record/tài liệu, FAQ theo loại buổi | `schedule.yaml` + enrich từ `#thông-báo` + Session Linker gắn tài liệu từ `#tài-nguyên` |
| **Tài nguyên** | Kho slide/record/tài liệu, lọc theo loại + tìm theo mã buổi, chia nhóm "theo buổi học" / "chung" | kênh `#tài-nguyên` (Session Linker gắn mã buổi) |
| **Bản tin** | News cộng đồng phân loại theo loại tin + mục Hot trend (rank theo reaction/comment) | ingestion 4 nhóm kênh, agent phân loại theo taxonomy |

**Chat widget** (góc phải, nổi trên mọi trang) — mặt tiền của quyết định AI trung tâm, gọi `/api/ask`.

## Chat widget — 4 đường trải nghiệm (R3)

Mỗi `action` render thành một loại card nhìn khác hẳn, để phân biệt được quyết định từ xa:

| `action` | Card | Đường trải nghiệm |
|---|---|---|
| `answer` | viền xanh · badge `✓ Có nguồn` · citation chip bấm được + ngày cập nhật | Happy |
| `clarify` | viền vàng · badge `? Cần làm rõ` · nút chọn từ `clarify_options` (hỏi lại **tối đa 1 lần**) | Low-confidence |
| `refuse` + `escalated_to: null` | viền xám · badge `⛔ Ngoài phạm vi` · chỉ đúng người có thẩm quyền | Ngoài thẩm quyền |
| `refuse` + `escalated_to: {...}` | viền đỏ · badge `→ Đã chuyển TA` · nêu rõ TA nào, lớp nào, vị trí hàng đợi | Failure |

Mọi card đều có nút **⚠ Báo sai** (→ `/api/feedback`) và hiện `action · confidence · latency · trace_id`
— để giám khảo thấy đây là **lời gọi AI thật, không hardcode**.

**Demo strip** dưới ô nhập: 4 nút câu hỏi mẫu, bấm lần lượt là diễn đủ 4 đường trong ~40 giây (dùng ở CP6).

## Contract `/api/ask` (chốt với Nghĩa)

`POST /api/ask` · body `{ "question": string, "clarify_context": string|null }`

```jsonc
{
  "action": "answer",          // "answer" | "clarify" | "refuse"
  "answer": "Hạn cứng nộp spec.md là **23:59 ngày 1**…",  // hỗ trợ **đậm** + xuống dòng
  "confidence": 0.93,
  "citations": [
    { "source": "schedule.yaml",   // tên file / tên kênh nguồn
      "session_code": "WS-3",      // có mã buổi → bấm citation nhảy sang tab Lịch học
      "quote": "WS-3 · 20:00–22:00 · Zoom",
      "updated": "29/07",          // ngày cập nhật nguồn (HAX #5)
      "url": "#" }                 // jump-link Discord / link file
  ],
  "clarify_options": [],           // action=clarify: ["Lab-10 · …", "Lab-11 · …"]
  "escalated_to": null,            // action=refuse do thiếu nguồn: {ta, class, queue_position}
  "trace_id": "tr_0a91"
}
```

Field nào chưa có thì trả `null` / `[]` — UI vẫn render được.
`POST /api/feedback` · body `{ trace_id, question, answer, verdict: "wrong" }`.

## Mock ↔ backend thật

Mặc định chạy **mock** (`src/api/mockAsk.js`) để dev được khi backend chưa lên, và làm
phương án B khi hết credit lúc demo. Đổi sang thật — không phải sửa UI:

```bash
# codebase/ui/.env.local
VITE_USE_MOCK=false
VITE_API_BASE=http://localhost:8000
```

## Chỗ cần sửa khi có quyết định chính thức

- `src/data/mock.js` → `NEWS_CATEGORIES`: **taxonomy loại tin là placeholder**, nhóm chốt bộ chính thức sau — sửa mảng này là toàn UI đổi theo.
- `src/data/mock.js` → `RAW_SESSIONS`: lịch demo sinh quanh tuần hiện tại; thay bằng API `/api/schedule` khi backend sẵn sàng.
- Mọi link `url: "#"` là mock — thay bằng link thật / jump-link Discord.

## Stack

React 18 + Vite 6 + Tailwind CSS 4 (plugin `@tailwindcss/vite`). Không router — chuyển trang bằng state trong `App.jsx`.
