# Deploy — UI trên Vercel, backend + bot chạy máy local (qua tunnel)

## Kiến trúc
- **UI**: Vercel (tĩnh, public HTTPS).
- **Backend (uvicorn) + Discord bot**: chạy trên máy bạn.
- Backend được expose ra internet qua **Cloudflare Tunnel** (HTTPS) để UI trên
  Vercel (chạy trong trình duyệt người xem) gọi tới được. `localhost` KHÔNG dùng
  trực tiếp được vì người xem ở máy khác.

```
Trình duyệt người xem ─▶ https://app.vercel.app (UI tĩnh)
        │  fetch VITE_API_BASE
        ▼
https://xxx.trycloudflare.com (tunnel) ─▶ localhost:8000 (backend máy bạn) ─▶ bot local
```

## 1. Chạy backend + bot (như hiện tại)
```powershell
cd codebase/backend; .venv\Scripts\python -m uvicorn api.main:app --port 8000
cd codebase/bot; ..\backend\.venv\Scripts\python run_bot.py
```

## 2. Expose backend qua Cloudflare Tunnel (HTTPS public, free)
Cài `cloudflared` (Cloudflare Zero Trust > downloads), rồi:
```powershell
cloudflared tunnel --url http://localhost:8000
```
→ in URL kiểu `https://<ngẫu-nhiên>.trycloudflare.com` = **API base public**.
- URL này ĐỔI mỗi lần chạy lại. Muốn cố định: dùng **Named Tunnel** + domain Cloudflare (vẫn free).
- Thay thế: `ngrok http 8000` (HTTPS; free có trang cảnh báo + URL đổi).

## 3. Deploy UI lên Vercel
- Import repo vào Vercel, đặt **Root Directory = `codebase/ui`** (Framework: Vite).
- Thêm **Environment Variable**: `VITE_API_BASE = https://<tunnel-url ở bước 2>`
  (không có dấu `/` ở cuối).
- Deploy → được `https://<app>.vercel.app`.
- CORS: backend đã tự cho phép mọi `*.vercel.app` (regex) → không cần chỉnh gì.
  Origin khác thì set env `CORS_ORIGINS="https://a.com,https://b.com"` cho backend.

## 4. Trỏ /hub về UI public (tuỳ chọn)
`codebase/bot/.env`: `COMPANION_UI_URL=https://<app>.vercel.app` (giữ
`COMPANION_API_URL=http://localhost:8000` vì bot cùng máy backend), rồi restart bot.

## Lưu ý quan trọng
- Backend chỉ sống khi **máy bạn bật + uvicorn + tunnel + bot** đang chạy. Tắt máy → app sập. Hợp để demo trực tiếp, không hợp chạy 24/7.
- Tunnel quick-URL đổi mỗi lần khởi động lại → phải cập nhật `VITE_API_BASE` trên Vercel rồi **Redeploy**. Named tunnel tránh việc này.
- **Chưa có auth**: ai có URL tunnel đều gọi được `/api/ask`, `/api/ai-news` → tốn tiền OpenAI/Tavily. Hãy đặt **hạn mức chi tiêu** ở dashboard OpenAI + Tavily; tắt tunnel sau khi demo.
- `?user=<tên discord>` không xác thực → chỉ dùng cho demo, không để lộ dữ liệu thật.
- ai-news lần đầu/ngày ~45s: backend local không giới hạn timeout nên OK.
