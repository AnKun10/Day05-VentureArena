"""Weekly schedule builder (pure — no I/O besides receiving already-loaded data)."""

import re
from datetime import date, timedelta

RECURRING_DAYS = range(0, 5)          # T2..T6 (Mon-Fri); T7/CN nghỉ
MORNING_SLOT = ("09:00", "13:00")
AFTERNOON_SLOT = ("14:00", "18:00")
# Khoá 4: sáng Lý thuyết, chiều Lab. Khoá 3: ngược lại (sáng Lab, chiều LT).
COHORT_SLOTS = {
    "4": {"LT": MORNING_SLOT, "LAB": AFTERNOON_SLOT},
    "3": {"LAB": MORNING_SLOT, "LT": AFTERNOON_SLOT},
}
STATIC_MATERIALS = {
    "LAB": [{"label": "Tài liệu hướng dẫn", "url": "https://codelabs.vlearn.dev/codelab", "kind": "doc"}],
    "LT": [{"label": "Slide trên VLearn", "url": "https://vlearn.dev", "kind": "slide"}],
}

_OVERRIDE_FIELDS = ("host", "zoom_url", "location")


def recurring_sessions(settings: dict, date_from: str, date_to: str) -> list[dict]:
    d0 = date.fromisoformat(date_from)
    d1 = date.fromisoformat(date_to)
    slots = COHORT_SLOTS.get(settings["cohort"], COHORT_SLOTS["4"])
    titles = {"LAB": "Buổi Lab", "LT": "Buổi Lý thuyết"}
    rooms = {"LAB": settings["lab_room"], "LT": settings["lt_room"]}
    items: list[dict] = []
    d = d0
    while d <= d1:
        if d.weekday() in RECURRING_DAYS:
            date_str = d.isoformat()
            for stype in sorted(slots, key=lambda t: slots[t][0]):   # sáng trước chiều
                slot = slots[stype]
                items.append({
                    "type": stype, "title": titles[stype], "date": date_str,
                    "start": slot[0], "end": slot[1],
                    "location": rooms[stype], "host": "Giảng viên khoá",
                    "format": "Offline", "cohort": settings["cohort"], "zoom_url": None,
                    "session_code": None, "jump_url": None,
                    "materials": [dict(m) for m in STATIC_MATERIALS[stype]],
                })
        d += timedelta(days=1)
    return items


def _dedup_events(events: list[dict]) -> list[dict]:
    """Dedup repeated announcements of the same evening event, keyed by
    (type, date, start).

    Keeps the richer record: prefer one with a zoom_url, then one with a host,
    otherwise keep whichever was seen first.

    Only applied to evening event types (WS/OH/MD/OTHER). LAB/LT events are
    excluded from this call site — they are often partial-update announcements
    with start=None, and multiple distinct partial updates for the same day
    must ALL flow through the override loop in build_schedule rather than
    collide on (type, date, start) and have one dropped.
    """
    best: dict[tuple, dict] = {}
    for e in events:
        key = (e.get("type"), e.get("date"), e.get("start"))
        if key not in best:
            best[key] = e
            continue
        cur = best[key]
        cur_score = (1 if cur.get("zoom_url") else 0, 1 if cur.get("host") else 0)
        new_score = (1 if e.get("zoom_url") else 0, 1 if e.get("host") else 0)
        if new_score > cur_score:
            best[key] = e
    return list(best.values())


def _ws_code_from_title(title: str | None) -> str | None:
    """'Workshop 1: Kick-off' / 'Workshop 02' / 'WS3' -> 'WS-1'/'WS-2'/'WS-3'."""
    m = re.search(r"(?:ws|workshop)\s*-?\s*0*(\d+)", title or "", re.IGNORECASE)
    return f"WS-{m.group(1)}" if m else None


def _norm(text: str | None) -> str:
    return re.sub(r"[^0-9a-zà-ỹ]+", " ", (text or "").lower()).strip()


def _materials_for_event(event: dict, resources: list[dict]) -> list[dict]:
    session_code = event.get("session_code")
    if not session_code and event.get("type") == "WS":
        # event trích từ thông báo không có session_code -> suy từ số trong title
        session_code = _ws_code_from_title(event.get("title"))
    matched = []
    if session_code:
        matched = [r for r in resources if r.get("session_code") == session_code]
    # Fallback cho resource chưa được gán session_code (vd "Tài liệu Workshop
    # Kick-off" không có số): khớp khi phần tên riêng của buổi (sau dấu ':')
    # xuất hiện trong title resource.
    subtitle = _norm((event.get("title") or "").split(":", 1)[-1])
    if len(subtitle) >= 4:
        for r in resources:
            if r.get("session_code") is None and r not in matched \
                    and subtitle in _norm(r.get("title")):
                matched.append(r)
    return [{"label": r.get("title"), "url": r.get("url"), "kind": r.get("kind")}
            for r in matched]


def build_schedule(settings: dict, events: list[dict], resources: list[dict],
                   date_from: str, date_to: str) -> list[dict]:
    lab_lt_events = [e for e in events if e.get("type") in ("LAB", "LT")]
    evening_events = _dedup_events([e for e in events if e.get("type") not in ("LAB", "LT")])
    events = lab_lt_events + evening_events
    items = recurring_sessions(settings, date_from, date_to)
    recurring_index = {(it["date"], it["type"]): it
                       for it in items if it["type"] in ("LAB", "LT")}

    extra: list[dict] = []
    for e in events:
        etype = e.get("type")
        key = (e.get("date"), etype)
        if etype in ("LAB", "LT") and key in recurring_index:
            block = recurring_index[key]
            for field in _OVERRIDE_FIELDS:
                if e.get(field) is not None:
                    block[field] = e[field]
            continue
        extra.append({
            "type": etype,
            "title": e.get("title"),
            "date": e.get("date"),
            "start": e.get("start"),
            "end": e.get("end"),
            "location": e.get("location"),
            "host": e.get("host"),
            "format": e.get("format"),
            "cohort": e.get("cohort"),
            "zoom_url": e.get("zoom_url"),
            "session_code": e.get("session_code"),
            "jump_url": e.get("jump_url"),
            "materials": _materials_for_event(e, resources),
        })

    items.extend(extra)
    items.sort(key=lambda i: (i["date"], i["start"] or "99:99"))
    for it in items:
        it["key"] = block_key(it)
    return items


# ---- Cá nhân hoá lịch: override theo user (không phụ thuộc hoàn toàn vào Agent) ----

_OVERRIDE_KEYS = ("title", "start", "end", "location", "format", "host", "zoom_url")


def block_key(item: dict) -> str:
    """Khoá ỔN ĐỊNH của 1 buổi (KHÔNG gồm field sửa được) để gắn override —
    dùng start GỐC nên user sửa giờ vẫn khớp khoá ở lần build sau."""
    return f"{item.get('date')}|{item.get('type')}|{item.get('start') or 'na'}"


def _custom_item(c: dict) -> dict:
    return {"type": c.get("type") or "OTHER", "title": c.get("title") or "(buổi tự thêm)",
            "date": c.get("date"), "start": c.get("start"), "end": c.get("end"),
            "location": c.get("location"), "host": c.get("host"),
            "format": c.get("format") or "Offline", "cohort": c.get("cohort") or "all",
            "zoom_url": c.get("zoom_url"), "session_code": None, "jump_url": None,
            "materials": []}


def apply_user_overrides(items: list[dict], overrides: list[dict],
                         date_from: str, date_to: str) -> list[dict]:
    """Áp override của 1 user lên lịch build sẵn: ẩn buổi, sửa field, thêm buổi
    tự tạo. Đánh dấu `edited`/`custom` để UI hiển thị khác."""
    by_key = {o["block_key"]: o for o in overrides}
    out = []
    for it in items:
        ov = by_key.get(it["key"])
        if ov and ov.get("hidden"):
            continue
        if ov and ov.get("patch"):
            it = {**it, **{k: v for k, v in ov["patch"].items()
                           if k in _OVERRIDE_KEYS and v is not None}}
            it["edited"] = True
        out.append(it)
    for o in overrides:
        c = o.get("custom")
        if c and c.get("date") and date_from <= c["date"] <= date_to:
            out.append({**_custom_item(c), "key": o["block_key"], "custom": True})
    out.sort(key=lambda i: (i["date"], i["start"] or "99:99"))
    return out
