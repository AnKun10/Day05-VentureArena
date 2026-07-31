"""Chạy golden_set.yaml qua decision.decide() thật (codebase/bot/) — in bảng % + lưu kết quả đầy đủ
(kể cả case fail) vào eval/results/, đúng luật "ghi nhận trung thực" của rubric.

Chạy: python eval/run_eval.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BOT_DIR = ROOT / "codebase" / "bot"
sys.path.insert(0, str(BOT_DIR))

from decision import decide  # noqa: E402
from knowledge import Knowledge  # noqa: E402


def main() -> None:
    golden_set = yaml.safe_load((ROOT / "eval" / "golden_set.yaml").read_text(encoding="utf-8"))
    cases = golden_set["cases"]
    kb = Knowledge.load(BOT_DIR / "data")

    rows = []
    passed = 0
    for case in cases:
        result = decide(case["question"], kb)
        ok = result.action == case["expected_action"]
        passed += ok
        rows.append(
            {
                "id": case["id"],
                "lop": case["lop"],
                "source": case["source"],
                "question": case["question"],
                "expected": case["expected_action"],
                "actual": result.action,
                "pass": ok,
                "actual_message": result.message,
            }
        )

    total = len(rows)
    pct = round(100 * passed / total, 1) if total else 0.0

    lines = [
        f"# Kết quả golden set — lượt chạy {datetime.now(timezone.utc).isoformat()}",
        "",
        f"**{passed}/{total} case đạt ({pct}%)**",
        "",
        "| id | lớp | nguồn | câu hỏi | kỳ vọng | thực tế | đạt? |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        mark = "✅" if r["pass"] else "❌"
        lines.append(
            f"| {r['id']} | {r['lop']} | {r['source']} | {r['question']} | {r['expected']} | {r['actual']} | {mark} |"
        )

    lines.append("")
    lines.append("## Case fail — chi tiết")
    for r in rows:
        if not r["pass"]:
            lines.append(f"- **{r['id']}** ({r['question']}): kỳ vọng `{r['expected']}`, thực tế `{r['actual']}` — bot trả lời: {r['actual_message']}")

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()