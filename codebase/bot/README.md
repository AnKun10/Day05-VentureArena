# Companion Bot — `codebase/bot/`

> ⚠️ **Thư mục này hiện chứa HAI bot Discord khác nhau, cùng làm 5 lệnh giống hệt nhau.**
> Đây là kết quả hai người build song song không biết việc của nhau (Minh trên `dev/Minh`,
> và bản trong `dev/nghia` đã merge vào `main`). **Chưa ai quyết định giữ bản nào** — cần cả nhóm
> thống nhất trước CP4, không nên tự ý xoá code của người khác.

| | **Bot A** — `main.py` | **Bot B** — `run_bot.py` |
|---|---|---|
| Người viết | Minh | (theo nhánh `dev/nghia`) |
| Code | `cogs/` · `ingestion/` · `decision.py` · `config.py` · `knowledge.py` · `db.py` | `companion_discord/` |
| Quyết định AI | `decision.py` — rule-based tại chỗ, 4 action | Gọi HTTP tới `codebase/backend` `/api/ask`, 3 action |
| Điểm golden set | **19/21 (90,5%)** | **8/21 (38,1%)** |
| Lời gọi AI thật | ❌ chưa có | ⚠️ có, nhưng **không ở quyết định trung tâm** |
| Test | 25 unit test (`tests/`) | test ở `tests/` gốc repo |

Số liệu và phân tích đầy đủ: **`eval/results/comparison-bot-vs-backend.md`** (chạy cùng bộ
`eval/golden_set.yaml`, đã chấm có lợi cho Bot B khi gộp 2 action refuse của Bot A làm một).

Kiến trúc tổng thể + phân công: `MASTERPLAN.md` §3/§6.

---

# Bot A — `main.py` (Minh)

## Trạng thái (CP2 → CP3)

- ✅ 5 slash command bấm được: `/ask` `/schedule` `/digest` `/hub` `/ta-digest`
- ✅ Quyết định trung tâm (`decision.py`): **answer / clarify / refuse-escalate / refuse-scope**
  (rule-based thật, không hardcode câu trả lời) — phủ đủ 4 lớp chỗ khó, có unit test.
  **Chưa phải LLM thật.** Kế hoạch CP3 là swap sang gọi `/api/ask`; nhưng đo xong thấy backend hiện tại
  kém hơn hẳn (xem bảng trên) nên **việc swap đang treo chờ nhóm quyết**.
- ✅ Ingestion worker (`ingestion/listener.py`): lắng nghe 4 nhóm kênh (chat lớp / forum / `#tài-nguyên` /
  `#thông-báo`), lưu metadata vào SQLite, Session Linker tự gắn mã buổi cho bài `#tài-nguyên`.
- ⚠️ **Cấu trúc server thật khác giả định ban đầu**: `lý-thuyết` VÀ `thực-hành-lab` cũng là **kênh Forum** —
  mỗi phòng lớp (`Lab-D305`, `Lec-D302`...) là 1 **thread** riêng bên trong, giống `hỏi-đáp`/`chia-sẻ`/`bài-học`.
  Đã sửa để soi mã lớp trên tên thread thay vì tên forum cha (xem `tests/test_ingestion.py`).
- ⚠️ **Khoá 3 và Khoá 4 dùng chung số phòng** (cả 2 khoá đều có riêng một "Lab-D305") — mã lớp có tiền tố
  khoá (`K3-Lab-D305` / `K4-Lab-D305`), suy từ category cha qua `config.cohort_from_category()`.
- ⏳ **Chưa làm**: phân loại tin theo taxonomy (chờ An chốt — cột `category` để trống, cắm qua
  `apply_category()`); `ta_roster.yaml` mới có discord_id test của Minh, chờ bản chính thức của Bình.

## Chạy

```bash
pip install -r requirements.txt
cp .env.example .env   # điền DISCORD_TOKEN + DISCORD_GUILD_ID (server test)
python main.py
```

Không có token vẫn chạy được toàn bộ logic (không cần Discord):

```bash
python -m unittest tests.test_decision tests.test_session_linker tests.test_config tests.test_ingestion -v
```

Chạy golden set (từ gốc repo): `python eval/run_eval.py`

## Cấu trúc

| File/thư mục | Vai trò |
|---|---|
| `main.py` | Entrypoint: load cogs, sync slash command, khởi động bot |
| `config.py` | Env config + phân loại kênh + suy mã lớp/khoá (`CHANNEL_EXACT_NAMES`) |
| `decision.py` | **Quyết định trung tâm** — answer/clarify/refuse-escalate/refuse-scope |
| `knowledge.py` | Load `data/schedule.yaml` + `data/faq.yaml` + `data/ta_roster.yaml` |
| `db.py` | SQLite: `posts` (ingest), `escalations` (hàng đợi TA), `ask_logs` (trace mọi lượt `/ask`) |
| `ingestion/session_linker.py` | Regex nhận mã buổi (`LT-x`/`Lab-x`/`WS-x`/`OH-x`/`MD-x`) |
| `ingestion/listener.py` | Cog `on_message` ở 4 nhóm kênh, ghi vào `posts` |
| `cogs/*.py` | 5 slash command |
| `data/*.yaml` | **Placeholder** — Bình thay bằng bản chính thức, giữ nguyên format |
| `tests/` | 25 unit test |

## Lệnh Discord

| Lệnh | Ai dùng | Việc |
|---|---|---|
| `/ask <câu hỏi>` | Học viên | Quyết định trung tâm: trả lời + citation, hỏi lại, hoặc từ chối + ghi hàng đợi TA |
| `/schedule` | Học viên | 5 buổi sắp tới |
| `/digest` | Học viên | Bản tin cộng đồng (fallback seed nếu chưa ingest lần nào) |
| `/hub` | Học viên | Link Web UI |
| `/ta-digest` | **TA/Lab Coach/Mentor/BTC/Admin** | Câu hỏi tồn theo lớp, gửi DM cho TA phụ trách |

---

# Bot B — `run_bot.py` (`companion_discord/`)

Dùng Discord Bot API đọc các channel ID khai trong `sources.yaml` vào SQLite, và expose 5 slash command.
Quyết định Q&A không nằm trong bot mà gọi sang `codebase/backend` `/api/ask`.

```powershell
Copy-Item .env.example .env
Copy-Item sources.example.yaml sources.yaml
uv run --no-project --with-requirements requirements.txt python run_bot.py
uv run --no-project --with-requirements requirements.txt python run_ingest.py
```

Cần `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `COMPANION_API_URL` và các channel ID được phép trước khi chạy.
Bot không tạo, xoá hay replay kênh/tin nhắn Discord.

---

## Việc cần làm tiếp

1. **Nhóm chốt giữ bot nào** — hoặc gộp: giữ logic quyết định của Bot A + tầng gọi AI/trace của backend,
   và đưa lời gọi AI **vào đúng chỗ quyết định** (hiện AI chỉ hậu xử lý văn bản, xem file so sánh).
2. Khi An chốt taxonomy loại tin: viết agent phân loại gọi `ingestion.listener.apply_category()`.
3. Khi Bình có `schedule.yaml`/`ta_roster.yaml` chính thức: thay file trong `data/`, không cần sửa code.
4. Thống nhất contract `/api/ask` — hiện **ba bên đang khác nhau**: UI của Hải cần `citations` dạng
   object (`{source, session_code, quote, updated, url}`), backend trả list string, `decision.py` dùng
   shape riêng. Phải chốt một shape trước khi nối.
