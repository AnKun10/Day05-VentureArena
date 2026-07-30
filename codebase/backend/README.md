# Companion backend — ingestion + API

## Setup
```bash
cd codebase/backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # điền OPENAI_API_KEY (+ TAVILY, DISCORD nếu có)
```

## Chạy
```bash
python -m ingest --source seed          # ingest + enrich seed (enrich-once)
python -m ingest --source discord       # đọc forum thật (cần token + channel id)
python -m ingest --loop 30              # lặp mỗi 30 phút
python -m ingest --force                # enrich lại (khi đổi prompt version)
uvicorn api.main:app --port 8000        # API cho UI (CORS localhost:5173)
pytest                                  # unit tests (không gọi API ngoài)
python -m ingest.smoke                  # smoke prompt (cần OPENAI_API_KEY)
```

Enrich-once: bài đã có `enriched_at` trong `companion.db` không bao giờ bị
enrich lại (không tốn phí) trừ khi `--force`. Trace từng lời gọi AI nằm ở
`eval/traces/ingest/`. Spec: `docs/superpowers/specs/2026-07-31-news-ingestion-pipeline-design.md`.
