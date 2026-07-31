"""Pure formatting helpers for Discord bot replies.

No discord/aiohttp imports here — this module must be importable (and
testable) without any bot dependencies installed.
"""

TAG_LABELS = {
    "ai-model": "AI Model",
    "ai-skill": "AI Skill",
    "ai-tools": "AI Tools",
    "api-mcp": "API & MCP",
    "dataset": "Dataset",
    "soft-skills": "Soft Skills",
    "survey": "Survey",
    "system-design": "System Design",
    "ui-ux": "UI/UX",
    "other": "Other",
}

_BUCKET_ORDER = ("Sáng", "Chiều", "Tối")


def bucket(start: str | None) -> str:
    if start is None:
        return "Tối"
    if start < "13:00":
        return "Sáng"
    if start < "18:00":
        return "Chiều"
    return "Tối"


def _time_label(item: dict) -> str:
    start, end = item.get("start"), item.get("end")
    if start is None or end is None:
        return "giờ TBA"
    return f"{start}–{end}"


def _location_suffix(item: dict) -> str:
    if item.get("format") == "Offline" and item.get("location"):
        return f" — {item['location']}"
    if item.get("format") == "Zoom":
        return " — Zoom"
    return ""


def _session_lines(item: dict) -> list[str]:
    lines = [f"  [{_time_label(item)}: {item.get('title')}{_location_suffix(item)}]"]
    for material in item.get("materials") or []:
        lines.append(f"    - {material.get('label')}: {material.get('url')}")
    zoom_url = item.get("zoom_url")
    if zoom_url:
        lines.append(f"    - Zoom: {zoom_url}")
    return lines


def format_schedule(items: list[dict], date_label: str, cohort: str) -> str:
    lines = [f"📅 Lịch {date_label} — Khoá {cohort}"]
    groups: dict[str, list[dict]] = {name: [] for name in _BUCKET_ORDER}
    for item in items:
        groups[bucket(item.get("start"))].append(item)

    for name in _BUCKET_ORDER:
        group_items = groups[name]
        if not group_items:
            lines.append(f"{name}: không có lịch")
            continue
        lines.append(f"{name}:")
        for item in sorted(group_items, key=lambda i: i.get("start") or ""):
            lines.extend(_session_lines(item))
    return "\n".join(lines)


def _digest_line(item: dict) -> str:
    summary = (item.get("summary") or "")[:120]
    return f"• {item.get('title')} — {summary} ({item.get('jump_url')})"


def format_digest(items: list[dict], personalized: bool) -> str:
    if not items:
        return "Chưa có bản tin nào."

    if personalized:
        lines = []
        for item in items:
            sim = (item.get("parts") or {}).get("sim") or 0
            lines.append(f"✨{round(sim * 100)}% {_digest_line(item)}")
        return "\n".join(lines)

    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for item in items:
        tags = item.get("tags") or []
        slug = tags[0] if tags else "other"
        label = TAG_LABELS.get(slug, TAG_LABELS["other"])
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(item)

    lines = []
    for label in order:
        lines.append(f"**{label}**")
        lines.extend(_digest_line(item) for item in groups[label])
    return "\n".join(lines)
