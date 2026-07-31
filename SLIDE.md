# SLIDE.md — Hướng dẫn dựng pitch deck 6 trang (kêu gọi đầu tư) cho **Companion**

> Deck ~6 trang, pitch 5–7 phút + demo live. Đối tượng: nhà đầu tư / giám khảo demo-day.
> **Thông điệp xuyên suốt:** *"Companion biến một server Discord học tập hỗn loạn thành trợ giảng AI cá nhân hoá — và nó đã chạy thật."*
> Chỗ `[trong ngoặc]` là số liệu/nội dung **bạn tự điền** — đừng bịa traction/tài chính.

---

## Nguyên tắc thiết kế (áp cho cả 6 trang)
- **1 ý / 1 slide.** Tiêu đề là một **câu khẳng định**, không phải danh từ ("Companion học từng người" > "Cá nhân hoá").
- Tối giản, nhiều khoảng trắng, **ảnh lớn > chữ** (≤ ~20 chữ/slide). Ưu tiên **screenshot thật** từ app đang chạy.
- Bảng màu giống VLearn: nền trắng, chữ navy, nhấn xanh dương (oklch xanh). Font sans (Inter/Geist).
- Công cụ: Google Slides / Canva / Pitch / **Gamma** (Gamma có thể sinh deck thẳng từ file này rất nhanh).

## Ảnh cần chụp trước (tái dùng xuyên deck)
1. **Web UI – Bản tin**: sidebar (avatar + tên user) + "Dành cho bạn" + section **Daily AI News cho bạn**.
2. **Web UI – Lịch học** (calendar nhiều màu, buổi học + workshop).
3. **Discord bot**: `/ask` trả lời kèm nguồn; `/daily-ai-news` 5 bài; `/schedule`.
4. **Sơ đồ luồng cá nhân hoá** (vẽ đơn giản): `Bio + Bookmark → AI Agent → Hồ sơ sở thích → Gợi ý`.

---

## Slide 1 — Bìa (Hook)
**Mục tiêu:** gây ấn tượng trong 5 giây.
**Nội dung:**
- Tên + logo: **Companion**
- Tagline: *"Trợ giảng AI cá nhân hoá cho mọi cộng đồng học tập trên Discord."*
- 1 dòng vision: *"Mỗi học viên có một trợ lý AI hiểu đúng mình — ngay trong cộng đồng họ đang học."*
- Tên team + link demo (Vercel) + QR code.
**Visual:** ảnh hero UI (Bản tin + Daily AI News), hoặc split màn hình Web UI | Bot Discord.
**Lời thoại (~20s):** *"Cộng đồng học AI sống trên Discord, nhưng Discord không được sinh ra để học. Companion là lớp AI cá nhân hoá phủ lên trên — và hôm nay nó đã chạy thật."*

## Slide 2 — Vấn đề
**Mục tiêu:** làm nhà đầu tư gật đầu "đúng, đau thật".
**Nội dung (3 nỗi đau):**
- **Thông tin phân mảnh** khắp 10+ kênh → học viên **bỏ lỡ** lịch, thông báo, tài liệu.
- **Không cá nhân hoá** → ai cũng thấy cùng một feed; nội dung liên quan bị chôn vùi.
- **Câu hỏi lặp lại, TA quá tải**, và **không ai biết học viên thực sự quan tâm gì** → khó giữ chân, khó hoàn thành khoá.
- `[Số liệu nếu có: N kênh · ~X bài/ngày · chỉ Y% học viên theo kịp]`
**Visual:** ảnh Discord nhiều kênh lộn xộn + nhãn "chaos".
**Lời thoại (~30s):** nêu 3 nỗi đau, chốt: *"Cộng đồng càng lớn, càng ồn, càng mất người."*

## Slide 3 — Giải pháp & Tính năng hệ thống
**Mục tiêu:** chứng minh sản phẩm **hoàn chỉnh, chạy thật**.
**Nội dung (grid, mỗi tính năng 1 dòng + icon):**
- 📰 **Bản tin AI** — tự tóm tắt bài cộng đồng, gắn 10 tag, tìm ảnh minh hoạ.
- 📅 **Lịch & Tài nguyên** — Agent tự trích buổi học/workshop/office-hour + slide/record/link Zoom từ kênh thông báo.
- ✨ **Gợi ý cá nhân hoá** — mục "Dành cho bạn" theo sở thích.
- 🗞️ **Daily AI News** — Agent **crawl + verify nguồn**, 5 tin AI mới mỗi ngày theo sở thích.
- 💬 **/ask chống bịa** — hỏi-đáp hybrid retrieval; không có nguồn thì nói *"chưa có thông tin"*, không bịa.
- 🔎 **Hybrid search + Bot Discord 6 lệnh** (`/ask /schedule /digest /bio /hub /daily-ai-news`).
- **Nhấn mạnh:** *"Không phải mockup — data thật, demo được ngay."*
**Visual:** 3–4 screenshot UI/bot + sơ đồ 1 dòng: `Discord → Pipeline AI (tóm tắt·trích·embed) → Web + Bot`.
**Lời thoại (~45s) → chuyển demo live nếu có.**

## Slide 4 — Cá nhân hoá & Phân tích sở thích người dùng ⭐ (điểm khác biệt / moat)
**Mục tiêu:** đây là slide *"tại sao chúng tôi thắng"*.
**Nội dung:**
- **Companion học từng người.** Luồng dữ liệu:
  `Bio + Bài bookmark + Hành vi  →  AI Agent suy hồ sơ sở thích (tóm tắt + tag)  →  embedding  →  cá nhân hoá Bản tin · Daily AI News · Digest`
- **Data flywheel (moat):** càng dùng → hồ sơ càng chuẩn → gợi ý càng "dính" → engagement & giữ chân tăng → càng nhiều dữ liệu. Đối thủ chép được UI, **không chép được hồ sơ sở thích tích luỹ**.
- **Ví dụ thật:** học viên khai sở thích *"VLM, Multimodal Retrieval"* → hệ thống **tự** đẩy tin **MoCa · CLIP-RAG · Graph-RAG** và ưu tiên bài multimodal — không cần cấu hình tay.
- `[Chỉ số nếu có: % match trung bình · thời gian ở lại · tỉ lệ mở gợi ý]`
**Visual:** sơ đồ **flywheel** + 2 screenshot Daily AI News của **2 user khác nhau → 2 feed khác nhau**.
**Lời thoại (~45s):** *"Hầu hết công cụ cộng đồng đối xử mọi người như nhau. Companion xây một hồ sơ sở thích sống cho từng học viên — đó là dữ liệu và là hào của chúng tôi."*

## Slide 5 — Thị trường & Mô hình kinh doanh
**Mục tiêu:** cho thấy đây là **business**, không chỉ là feature hay.
**Nội dung:**
- **Thị trường:** bootcamp/khoá học online, cộng đồng dev, edtech — rất nhiều nơi đã "sống" trên Discord/Slack. `[Ước lượng TAM/SAM/SOM]`.
- **Khách hàng trả tiền (B2B SaaS):** tổ chức đào tạo / bootcamp / cộng đồng — trả **theo cộng đồng hoặc /seat/tháng**. KPI họ cần là **retention & completion** — đúng thứ cá nhân hoá của chúng tôi cải thiện.
- **Why now:** chi phí LLM giảm mạnh (chạy `gpt-5-mini` + fallback tiết kiệm), học qua Discord phổ biến, cá nhân hoá đã là kỳ vọng mặc định.
- **Giá gợi ý:** `[Free (1 cộng đồng nhỏ) → Pro $X/tháng/cộng đồng → Enterprise]`.
**Visual:** phễu TAM/SAM/SOM + vài logo phân khúc khách hàng mục tiêu.
**Lời thoại (~40s).**

## Slide 6 — Roadmap · Team · Lời kêu gọi
**Mục tiêu:** chốt và **xin tiền rõ ràng**.
**Nội dung:**
- **Đã có (traction):** MVP hoàn chỉnh chạy live — `[N tính năng · bot 6 lệnh · data thật · build trong X ngày]`.
- **Roadmap:** đa cộng đồng • dashboard analytics cho tổ chức • đăng nhập Discord OAuth • ingest realtime • mobile.
- **Team:** An (PM & taxonomy) • Nghĩa (AI Core) • Minh (Discord Bot & Ingestion) • Hải (Web UI) • Bình (Data & QA). `[chỉnh nếu cần]`
- **Ask:** gọi **$[số tiền]** để `[thuê 2 kỹ sư · hạ tầng + credit LLM · go-to-market]` trong **[N] tháng**, mục tiêu **[X cộng đồng trả phí]**.
- **CTA:** `[link demo]` • `[email/liên hệ]`.
**Visual:** timeline roadmap + ảnh team + con số **ask** nổi bật ở giữa.
**Lời thoại (~40s) — kết bằng đúng câu vision ở slide 1.**

---

## Checklist trước khi pitch
- [ ] Thay mọi placeholder ảnh bằng **screenshot thật** từ app.
- [ ] Điền mọi `[ngoặc]`: số liệu, tài chính, TAM, giá, ask.
- [ ] Tập **demo live 2 phút**: Bản tin + Daily AI News + `/ask` trên Discord.
- [ ] Thuộc lòng **1 câu hook** + **1 con số ask** duy nhất.
- [ ] Nếu demo live: bật sẵn backend + tunnel + bot (xem `docs/DEPLOY.md`).

## Bố cục 1 dòng (in ra để nhớ)
`1 Hook → 2 Vấn đề → 3 Giải pháp+Tính năng → 4 Cá nhân hoá (moat) → 5 Thị trường+Mô hình → 6 Ask`
