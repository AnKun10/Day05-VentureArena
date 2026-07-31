# 🎓 Companion — Trợ lý Discord cá nhân hoá cho khoá **AI Thực Chiến**

> **Một nơi cho mọi thứ của khoá học:** lịch học, bản tin AI, hỏi-đáp có căn cứ và gợi ý dành riêng cho bạn — ngay trên Discord *và* trên web.

Học viên đang phải nhảy giữa hàng chục kênh Discord, kênh thông báo, tài nguyên rải rác và những câu hỏi lặp đi lặp lại. **Companion** gom tất cả lại: một trợ lý hiểu lịch của bạn, tóm tắt tin tức AI, trả lời câu hỏi *chỉ khi có căn cứ* và gợi ý đúng thứ bạn quan tâm.

<p align="center"><i>React + Vite • FastAPI • OpenAI Agents SDK • Qdrant • Discord.py</i></p>

---

## ✨ Tính năng nổi bật

### 🤖 `/ask` — Hỏi-đáp có căn cứ, **không bịa**
Agent (OpenAI Agents SDK) với **tool tra cứu hybrid** (lexical + semantic, hợp nhất bằng **RRF**) trên kho tri thức khoá học. Điều khác biệt: **thà nói "chưa có thông tin" còn hơn đoán sai.**
- Có nguồn → trả lời **kèm trích dẫn Discord gốc**.
- Câu mơ hồ → **hỏi lại**, không đoán.
- Ngoài phạm vi / đòi thao tác / xin dữ liệu người khác → **từ chối** lịch sự, hướng đúng kênh.
- Thông tin hệ trọng (deadline, đậu/rớt, điểm) không chắc → **không phán bừa**.
- Có **tool xem giờ hiện tại** để hiểu "hôm nay", "tuần này", "sắp tới".

### 📅 Lịch học cá nhân hoá — **sửa được**
Lịch cố định theo khoá (Khoá 4 sáng Lý thuyết/chiều Lab, Khoá 3 ngược lại) + **buổi tối (workshop/office-hour/mentor-duty) do AI trích tự động** từ kênh thông báo, gắn sẵn slide/record/link Zoom.
- Không phụ thuộc hoàn toàn vào AI: **tự sửa phòng/giờ/tiêu đề, ẩn buổi sai, thêm buổi mới** — mọi chỉnh sửa **chỉ áp cho riêng bạn**.

### 📰 Bản tin AI tự tổng hợp
AI đọc kênh `#chia-sẻ` / `#bài-học`, **tóm tắt + gắn 10 nhãn chủ đề + tìm ảnh minh hoạ** (Tavily) tự động. Lọc theo tag, xem chi tiết, bookmark.

### ✨ Gợi ý dành riêng cho bạn
Từ **bio + bài đã bookmark**, một agent suy ra hồ sơ sở thích → gợi ý bản tin sát khẩu vị. Xếp hạng **hybrid** (độ tương đồng chuẩn hoá theo pool + độ hot + độ mới), có **fallback keyword** khi vector store gặp sự cố — *không bao giờ chết*.

### 🔖 Bookmark & 💬 Bot Discord
Trang lưu bài riêng của bạn. Bot 5 lệnh: `/ask` `/schedule` `/digest` `/bio` `/hub` — reply dạng **embed đẹp** (icon, masked link), kèm **log quan sát** (độ trễ, token, số lần gọi tool).

### 🛡️ An toàn & tuân thủ dữ liệu
- **Guardrail đầu vào**: chặn nội dung tục tĩu và **prompt injection** *trước khi* chạm tới model.
- **Access-gated knowledge base**: kho tri thức chỉ nạp phần **được duyệt & không nhạy cảm** (loại personal_data/internal_only), có auditable log — dữ liệu cá nhân không lọt vào bot học viên.

---

## 🏗️ Kiến trúc

```
  Discord Bot (5 lệnh)              Web UI (React + Vite + Tailwind)
        │                                   │
        └──────────────┬────────────────────┘
                       ▼
              FastAPI backend  ──►  Guardrails (chặn injection/tục tĩu)
                       │
     ┌─────────────────┼───────────────────────────────┐
     ▼                 ▼                                 ▼
  /ask Agent      Recsys                          Ingest pipeline
  (tools + RRF)   (Qdrant + keyword fallback)     (enrich · schedule extract)
     │                 │                                 │
     └────────► SQLite (news · KB chunks · lịch · user · bookmark) ◄──┘
                          ▲
                  Access-gated KB (discord_kb) — chỉ chunk đã duyệt
```

## 🧰 Tech stack
| Lớp | Công nghệ |
|---|---|
| Web UI | React 19 · Vite · Tailwind v4 · shadcn/ui |
| Backend | FastAPI · Pydantic · SQLite |
| AI | OpenAI Agents SDK · `gpt-5-mini` · `text-embedding-3-small` · Tavily |
| Vector / retrieval | Qdrant (embedded) · hybrid lexical+semantic · RRF |
| Bot | discord.py (slash commands, embed) |

## 🚀 Chạy thử nhanh
```powershell
# 1) Backend  (điền OPENAI_API_KEY, TAVILY_API_KEY... vào codebase/backend/.env)
cd codebase/backend; uvicorn api.main:app --port 8000

# 2) Web UI
cd codebase/ui; npm install; npm run dev        # http://localhost:5173

# 3) Bot Discord  (điền DISCORD_TOKEN, COMPANION_API_URL vào codebase/bot/.env)
cd codebase/bot; python run_bot.py
```

## 📏 Chất lượng — đo chứ không đoán
Có **bộ 55 câu thử** (`eval/`) gồm cả câu **nguyên văn từ log Discord thật** (typo, cụt lủn, trộn Anh-Việt), phủ: trả lời có nguồn, chống bịa, câu mơ hồ, việc vượt quyền, tình huống hệ trọng, guardrail. Chuẩn cam kết: **≥80% đạt VÀ không bịa thông tin hệ trọng dù một lần**. Chạy: `python eval/run_ask_eval.py`.

## 👥 Nhóm & phân công
| Thành viên | Vai trò | Nhánh |
|---|---|---|
| **An** | PM · taxonomy · điều phối/tích hợp | `dev/An` |
| **Minh** | Discord Bot & ingestion | `dev/Minh` |
| **Nghĩa** | AI Core (Q&A / `/ask`) | `dev/nghia` |
| **Hải** | Web UI | `dev/Hai` |
| **Bình** | Data & QA | `dev/Binh` |

> *(Điền mã HV cạnh tên khi nộp bài theo yêu cầu rubric.)*

## 📂 Tài liệu chi tiết
- **Backend** (ingest · recsys · `/ask` · KB · schedule): [`codebase/backend/README.md`](codebase/backend/README.md)
- **Bot Discord** (5 lệnh · resilience · metrics): [`codebase/bot/README.md`](codebase/bot/README.md)
- **Kế hoạch tổng**: [`MASTERPLAN.md`](MASTERPLAN.md) · **AI Spec**: [`spec.md`](spec.md)

Chạy test cục bộ (không kết nối Discord): `pytest -q`

---

<details>
<summary><b>📋 Thông tin Hackathon (đề bài · lịch · rubric · luật · bảo mật dữ liệu)</b></summary>

# Mini Hackathon AI — Batch 03

**SPEC → Prototype → Demo.** Đây không phải cuộc thi code — đây là cuộc thi **tư duy sản phẩm AI**.

- Thời lượng: **1,5 ngày** (một ngày build + một buổi demo)
- Nhóm: **4-5 người** · zone tối đa 5 nhóm · thi theo lớp

## Bắt đầu từ đâu?

1. Đọc **`01-de-bai.md`** để chọn hướng và hiểu tiêu chí.
2. Mở **`02-guide.md`** — hướng dẫn từng giai đoạn, đứng ở đâu đọc mục đó.
3. Viết spec theo **`03-template-ai-spec.md`** — deliverable trung tâm của cả sự kiện.
4. Đọc **`04-rubric.md`** ngay từ đầu — biết trước bài được chấm theo tiêu chí nào.

| File / thư mục | Nội dung |
|---|---|
| `01-de-bai.md` | Đề bài 3 hướng · 5 tiêu chí nghiệm thu · ràng buộc chung |
| `02-guide.md` | Hướng dẫn 5 giai đoạn: khám phá → spec → build → đo & validate → demo |
| `03-template-ai-spec.md` | Template AI Spec (nộp 23:59 ngày 1) |
| `04-rubric.md` | Rubric 100 điểm (25 nộp checkpoint + 75 chấm bài) + checklist xác minh 6 mốc |
| `data/` | Dữ liệu thật đã ẩn danh: chatlog VLearn tutor + 6 transcript bài giảng + 2 bộ slide bản hackathon — dùng để tìm bằng chứng và xây golden set |
| `tham-khao/` | JTBD Playbook (PDF) + worksheet JTBD đầy đủ — đọc khi muốn đào sâu |

## Lịch — 6 mốc

| Mốc | Khoá 3 | Khoá 4 |
|---|---|---|
| Khai mạc + phát đề | 09:00 ngày 1 | 14:00 ngày 1 |
| CP1 · Chốt Canvas | 10:00 ngày 1 | 15:00 ngày 1 |
| CP2 · Show được thứ bấm được | 12:00 ngày 1 | 17:00 ngày 1 |
| CP3 · AI chạy thật + đo lượt đầu | 16:00 ngày 1 | 10:30 ngày 2 |
| CP4 · Chốt tiến độ — spec nộp hạn cứng **23:59 ngày 1** | 17:30 ngày 1 | 12:00 ngày 2 |
| CP5 · Xác minh + validation + dry run | 09:00 ngày 2 | 14:00 ngày 2 |
| CP6 · Demo | 10:00 ngày 2 | 15:00 ngày 2 |

Mỗi mốc cần show gì và được xác minh thế nào: xem bảng trong `04-rubric.md`.

## Nộp bài

Một repo nhóm, cấu trúc như sau. Spec chốt lúc 23:59 ngày 1; bản hoàn chỉnh trước CP6.

```
repo/
├── README.md          ← thành viên (mã HV + tên) + phân công có tên từng phần
├── spec.md            ← AI Spec theo 03-template-ai-spec.md
├── demo-slides.pdf    ← slide 6 trang theo 02-guide.md §5.1
├── codebase/          ← prototype (ghi rõ phần nào mock)
├── eval/              ← golden set + bảng kết quả các lượt chạy
├── validation/        ← feedback log từ vòng user test
└── reflection/        ← mỗi người 1 file
```

## Chấm điểm

Tổng **100 điểm = 25 điểm nộp checkpoint + 75 điểm chấm bài nộp**. Chi tiết từng ý điểm: `04-rubric.md`.

**25 điểm nộp — mỗi checkpoint 5 điểm (CP1-CP5):** nộp đúng hạn → 5 điểm · nộp muộn → 0 điểm cho mốc đó. Mỗi thành viên nộp riêng, cả nhóm dùng chung một link repo.

**75 điểm chấm — trên artifact trong repo, mỗi con điểm trỏ về một file:**

| Khối | Điểm | Chấm trên file nào |
|---|---|---|
| R1 · Bằng chứng & impact | 15 | `spec.md` §1-§2 + log khảo sát/mining |
| R2 · Lát cắt & thiết kế | 15 | `spec.md` §4 |
| R3 · Chỗ khó & kịch bản rủi ro | 11 | `spec.md` §5-§6 |
| R4 · Kiểm thử | 15 | `spec.md` §7 + `eval/` |
| R5 · Prototype chạy được | 8 | `codebase/` + demo |
| R6 · Validation với user | 8 | `validation/` |
| R7 · Quy trình & repo | 3 | cấu trúc repo |

Ba điều nên biết trước khi làm:

- Điểm dựa trên **chuỗi quyết định và bằng chứng**, không dựa trên mức độ hoành tráng của sản phẩm.
- Kết quả đo **ghi nhận trung thực** — kể cả khi không đạt mục tiêu nhóm tự đặt — vẫn được tính đủ điểm. Số liệu bị chỉnh sửa hoặc che giấu sẽ không được tính.
- Reflection cá nhân chấm riêng theo rubric của khoá. Điểm vòng demo, chấm chéo trong zone và thưởng thêm (nếu có) theo thể lệ công bố lúc khai mạc.

## Luật chung

1. Prototype có 3 mức **Sketch / Mock / Working** — mức nào cũng bắt buộc **≥1 lời gọi AI chạy thật**.
2. **Vibe-coding rule:** dùng AI để build thoải mái, nhưng không giải thích được phần có tên mình thì phần đó 0 điểm (kiểm tra tại CP5).
3. **Quality bar** chốt tại spec.md 23:59 ngày 1 và giữ nguyên sau đó.
4. Chỉ dùng dữ liệu trong `data/` hoặc dữ liệu giả tự sinh — không dùng dữ liệu thật của người thật. Không commit API key.
5. Tuân thủ **quy định bảo mật dữ liệu** bên dưới — đây là điều kiện để được cấp data.

## Bảo mật dữ liệu được cung cấp

Dữ liệu trong `data/` là dữ liệu thật của khoá học (đã ẩn danh), cấp riêng cho hackathon này. Khi nhận data, nhóm cam kết:

1. **Chỉ dùng trong phạm vi hackathon** — cho việc tìm bằng chứng, xây golden set và build prototype. Không dùng cho mục đích khác.
2. **Không chia sẻ ra ngoài khoá học** — không đăng lên mạng xã hội, không gửi cho người ngoài, không đưa vào bất kỳ dataset hay repo công khai nào.
3. **Không commit data pack vào repo nộp bài** — repo nhóm chỉ chứa trích dẫn ngắn để minh hoạ (vài dòng); golden set trích từ data ghi rõ mã đoạn/mã hội thoại thay vì dán nguyên văn dài.
4. **Cẩn trọng khi đưa data vào công cụ ngoài** — chỉ đưa phần tối thiểu cần cho việc đang làm; lưu ý API/công cụ free tier có thể dùng dữ liệu để huấn luyện (xem `02-guide.md` §3.4).
5. **Không cố suy ngược danh tính** từ dữ liệu đã ẩn danh ([học viên], mã U/C/T/M).
6. Sau sự kiện, **xoá các bản sao data pack** khỏi máy cá nhân và các công cụ đã upload nếu ban tổ chức yêu cầu.

Vi phạm được xử lý theo quy định của khoá và có thể ảnh hưởng trực tiếp đến điểm của nhóm.

</details>

<details>
<summary><b>⚖️ Discord Developer Portal — Terms &amp; Privacy</b></summary>

Repo có sẵn trang Terms of Service & Privacy Policy tĩnh trong `docs/`. Xuất bản qua GitHub Pages:

```text
Settings → Pages → Deploy from a branch → Branch: main, Folder: /docs → Save
```
Sau khi deploy, dán URL vào Discord Developer Portal → General Information:
```text
Terms of Service URL:  https://AnKun10.github.io/Day05-VentureArena/terms.html
Privacy Policy URL:     https://AnKun10.github.io/Day05-VentureArena/privacy.html
```
Trước khi publish, thay các placeholder trong trang legal bằng tên app Discord công khai, email liên hệ và thời hạn lưu dữ liệu đã duyệt.
</details>
