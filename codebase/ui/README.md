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

Tab **Hỏi đáp** (chat với agent) để chỗ sẵn trên sidebar — nối vào `/api/ask` sau.

## Chỗ cần sửa khi có quyết định chính thức

- `src/data/mock.js` → `NEWS_CATEGORIES`: **taxonomy loại tin là placeholder**, nhóm chốt bộ chính thức sau — sửa mảng này là toàn UI đổi theo.
- `src/data/mock.js` → `RAW_SESSIONS`: lịch demo sinh quanh tuần hiện tại; thay bằng API `/api/schedule` khi backend sẵn sàng.
- Mọi link `url: "#"` là mock — thay bằng link thật / jump-link Discord.

## Stack

React 18 + Vite 6 + Tailwind CSS 4 (plugin `@tailwindcss/vite`). Không router — chuyển trang bằng state trong `App.jsx`.
