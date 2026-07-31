"""Chạy bộ câu thử eval/ask_testset.json qua /api/ask và chấm điểm.

Grade mỗi câu:
  - action: nếu case có accept_actions thì action ∈ đó, ngược lại == expected_action
  - must_contain: mọi chuỗi (không phân biệt hoa/thường) PHẢI có trong answer
  - must_not_contain: mọi chuỗi KHÔNG được có trong answer
  - must_cite: nếu true thì citations khác rỗng
Đạt khi mọi điều kiện áp dụng đều thoả.

Xuất: eval/ask_testset_results.md (bảng đầy đủ, có cả câu fail) + tóm tắt X/N.
Dùng:  python eval/run_ask_eval.py [API_URL]
"""

import json
import sys
import urllib.request
from pathlib import Path

API = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
HERE = Path(__file__).resolve().parent
TESTSET = HERE / "ask_testset.json"
OUT_MD = HERE / "ask_testset_results.md"


def ask(question: str) -> dict:
    data = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(API + "/api/ask", data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def grade(case: dict, resp: dict) -> tuple[bool, list[str]]:
    fails = []
    ans = (resp.get("answer") or "").lower()
    action = resp.get("action")
    accept = case.get("accept_actions") or [case["expected_action"]]
    if action not in accept:
        fails.append(f"action={action} ∉ {accept}")
    for s in case.get("must_contain", []):
        if s.lower() not in ans:
            fails.append(f"thiếu '{s}'")
    for s in case.get("must_not_contain", []):
        if s.lower() in ans:
            fails.append(f"có '{s}' (cấm)")
    if case.get("must_cite") and not resp.get("citations"):
        fails.append("thiếu citation")
    return (not fails), fails


def main() -> None:
    ts = json.loads(TESTSET.read_text(encoding="utf-8"))
    cases = ts["cases"]
    rows, passed = [], 0
    for i, c in enumerate(cases, 1):
        try:
            resp = ask(c["input"])
        except Exception as exc:
            resp = {"action": "ERROR", "answer": f"[{type(exc).__name__}: {exc}]", "citations": []}
        ok, fails = grade(c, resp)
        passed += ok
        rows.append((c, resp, ok, fails))
        print(f"[{i:>2}/{len(cases)}] {c['id']:<5} {'PASS' if ok else 'FAIL'} "
              f"({resp.get('action')}) {'; '.join(fails)}")

    lines = [f"# Kết quả chạy thử /ask — {passed}/{len(cases)} đạt", "",
             f"API: `{API}`  ·  bộ thử: `eval/ask_testset.json` (v{ts.get('version')})", "",
             "| ID | origin | expect | got | kết quả | ghi chú (lý do fail) | answer (rút gọn) |",
             "|----|--------|--------|-----|---------|----------------------|------------------|"]
    for c, resp, ok, fails in rows:
        exp = "/".join(c.get("accept_actions") or [c["expected_action"]])
        ans = (resp.get("answer") or "").replace("|", "/").replace("\n", " ")[:70]
        note = "; ".join(fails).replace("|", "/") if fails else ""
        lines.append(f"| {c['id']} | {c.get('origin','')} | {exp} | {resp.get('action')} | "
                     f"{'✅' if ok else '❌'} | {note} | {ans} |")
    # tách điểm theo origin
    real = [r for r in rows if r[0].get("origin") == "real"]
    syn = [r for r in rows if r[0].get("origin") != "real"]
    lines += ["", f"- Tổng: **{passed}/{len(cases)}**",
              f"- Synthetic: {sum(r[2] for r in syn)}/{len(syn)}",
              f"- Real (Discord log): {sum(r[2] for r in real)}/{len(real)}"]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n==> {passed}/{len(cases)} đạt. Bảng đầy đủ: {OUT_MD}")


if __name__ == "__main__":
    main()
