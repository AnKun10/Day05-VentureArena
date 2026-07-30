# Companion Bot — Discord Bot & Ingestion (Minh)

Phần **Discord Bot & Ingestion** của [Personalized Discord Companion Agent](../../MASTERPLAN.md) —
xem kiến trúc tổng thể + phân công ở `MASTERPLAN.md` §3/§6.

## Trạng thái hiện tại (CP2 → CP3)

- ✅ 5 slash command bấm được: `/ask` `/schedule` `/digest` `/hub` `/ta-digest`
- ✅ Quyết định AI trung tâm (`decision.py`): logic **answer / clarify / refuse-escalate / refuse-scope**
  thật (rule-based trên schedule/FAQ, không hardcode câu trả lời) — bao phủ đủ 4 lớp chỗ khó, có unit test
  (`tests/test_decision.py`). **Chưa phải LLM thật** — đây là mock cho CP2, sẽ swap sang gọi
  `/api/ask` của Nghĩa (backend RAG Core thật) ở CP3. Khi swap: chỉ sửa `decision.py`, cogs không đổi.
- ✅ Ingestion worker (`ingestion/listener.py`): lắng nghe 4 nhóm kênh (chat lớp / forum / `#tài-nguyên` /
  `#thông-báo`), lưu metadata vào SQLite, Session Linker tự gắn mã buổi cho bài `#tài-nguyên`.
- ⏳ **Chưa làm**: nối bot vào server Discord thật/test thật (cần token + mời bot); phân loại tin theo
  taxonomy chính thức (chờ An chốt — cột `category` đang để trống, cắm qua `apply_category()`); DM thật
  cho TA (cần `ta_roster.yaml` điền `discord_id` thật — hiện là placeholder).

## Chạy thử

```bash
pip install -r requirements.txt
cp .env.example .env   # điền DISCORD_TOKEN + DISCORD_GUILD_ID (server test)
python main.py
```

Không có token vẫn chạy được phần logic thuần Python (không cần Discord):

```bash
python -m unittest tests.test_decision tests.test_session_linker -v
```

## Cấu trúc

| File/thư mục | Vai trò |
|---|---|
| `main.py` | Entrypoint: load cogs, sync slash command, khởi động bot |
| `config.py` | Env config + mapping tên kênh Discord → nhóm kênh (`CHANNEL_GROUPS`) |
| `decision.py` | **Quyết định AI trung tâm** — answer/clarify/refuse, chấm điểm bằng golden set |
| `knowledge.py` | Load `data/schedule.yaml` + `data/faq.yaml` + `data/ta_roster.yaml` vào bộ nhớ |
| `db.py` | SQLite: `posts` (ingest), `escalations` (hàng đợi TA), `ask_logs` (trace mọi lượt `/ask`) |
| `ingestion/session_linker.py` | Regex nhận diện mã buổi (`LT-x`/`Lab-x`/`WS-x`/`OH-x`/`MD-x`) trong text |
| `ingestion/listener.py` | Cog lắng nghe `on_message` ở 4 nhóm kênh, ghi vào `posts` |
| `cogs/*.py` | 5 slash command |
| `data/*.yaml` | **Placeholder** — Bình sẽ thay bằng bản chính thức (`schedule.yaml`, `ta_roster.yaml`); giữ nguyên format |
| `tests/` | Unit test cho `decision.py` (4 lớp chỗ khó) và `session_linker.py` |

## Lệnh Discord

| Lệnh | Ai dùng | Việc |
|---|---|---|
| `/ask <câu hỏi>` | Học viên | Quyết định trung tâm: trả lời + citation, hỏi lại, hoặc từ chối + ghi hàng đợi TA |
| `/schedule` | Học viên | 5 buổi sắp tới |
| `/digest` | Học viên | Bản tin cộng đồng theo loại tin (fallback seed nếu chưa ingest lần nào) |
| `/hub` | Học viên | Link Web UI (Hải) |
| `/ta-digest` | **TA/Lab Coach/Mentor/BTC/Admin** | Bản tổng hợp câu hỏi tồn theo lớp, gửi DM cho TA phụ trách |

## Việc cần làm tiếp (theo MASTERPLAN.md §7)

1. **Trước CP2/CP3**: dựng server Discord test mô phỏng cấu trúc thật (kênh `lý-thuyết`, `lab-d305`,
   forum `hỏi-đáp`/`bài-học` có tag, `tài-nguyên`, `thông-báo`) + mời bot + gán role TA test.
2. **CP3**: thay `decide()` trong `decision.py` bằng HTTP call tới `/api/ask` (contract bàn với Nghĩa) —
   giữ nguyên interface `Decision(action, message, citations, confidence, class_code, reason)`.
3. Khi An chốt taxonomy loại tin: viết agent phân loại gọi `ingestion.listener.apply_category()`.
4. Khi Bình có `schedule.yaml`/`ta_roster.yaml` chính thức: thay file trong `data/`, không cần sửa code.
5. Log AI call thật (`eval/traces/`) khi decision.py gọi API thật — hiện `ask_logs` trong SQLite đã log
   mọi lượt `/ask` (question/action/answer/citations/confidence), export sang `eval/traces/` khi cần.