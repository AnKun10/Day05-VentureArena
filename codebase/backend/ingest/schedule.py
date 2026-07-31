"""Weekly schedule builder (pure — no I/O besides receiving already-loaded data)."""

from datetime import date, timedelta

RECURRING_DAYS = range(0, 6)          # T2..T7 (Mon-Sat); weekday() Sunday == 6
LAB_SLOT = ("09:00", "13:00")
LT_SLOT = ("14:00", "18:00")
STATIC_MATERIALS = {
    "LAB": [{"label": "Tài liệu hướng dẫn", "url": "https://codelabs.vlearn.dev/codelab", "kind": "doc"}],
    "LT": [{"label": "Slide trên VLearn", "url": "https://vlearn.dev", "kind": "slide"}],
}

_OVERRIDE_FIELDS = ("host", "zoom_url", "location")


def recurring_sessions(settings: dict, date_from: str, date_to: str) -> list[dict]:
    d0 = date.fromisoformat(date_from)
    d1 = date.fromisoformat(date_to)
    items: list[dict] = []
    d = d0
    while d <= d1:
        if d.weekday() in RECURRING_DAYS:
            date_str = d.isoformat()
            items.append({
                "type": "LAB", "title": "Buổi Lab", "date": date_str,
                "start": LAB_SLOT[0], "end": LAB_SLOT[1],
                "location": settings["lab_room"], "host": "Giảng viên khoá",
                "format": "Offline", "cohort": settings["cohort"], "zoom_url": None,
                "session_code": None, "jump_url": None,
                "materials": [dict(m) for m in STATIC_MATERIALS["LAB"]],
            })
            items.append({
                "type": "LT", "title": "Buổi Lý thuyết", "date": date_str,
                "start": LT_SLOT[0], "end": LT_SLOT[1],
                "location": settings["lt_room"], "host": "Giảng viên khoá",
                "format": "Offline", "cohort": settings["cohort"], "zoom_url": None,
                "session_code": None, "jump_url": None,
                "materials": [dict(m) for m in STATIC_MATERIALS["LT"]],
            })
        d += timedelta(days=1)
    return items


def _dedup_events(events: list[dict]) -> list[dict]:
    """Dedup repeated announcements of the same event, keyed by (type, date, start).

    Keeps the richer record: prefer one with a zoom_url, then one with a host,
    otherwise keep whichever was seen first.
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


def _materials_for_event(event: dict, resources: list[dict]) -> list[dict]:
    session_code = event.get("session_code")
    if not session_code:
        return []
    return [{"label": r.get("title"), "url": r.get("url"), "kind": r.get("kind")}
            for r in resources if r.get("session_code") == session_code]


def build_schedule(settings: dict, events: list[dict], resources: list[dict],
                   date_from: str, date_to: str) -> list[dict]:
    events = _dedup_events(events)
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
    return items
