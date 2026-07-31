"""Pure formatting helpers for Discord bot replies.

No discord/aiohttp imports here — this module must be importable (and
testable) without any bot dependencies installed. Embed builders return
plain dicts {title, color, description?, fields: [{name, value, inline}]}
mà bot.py chuyển thành discord.Embed.
"""

import re

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

TAG_EMOJI = {
    "ai-model": "🧠",
    "ai-skill": "🎯",
    "ai-tools": "🛠️",
    "api-mcp": "🔌",
    "dataset": "📊",
    "soft-skills": "💬",
    "survey": "📋",
    "system-design": "🏗️",
    "ui-ux": "🎨",
    "other": "📌",
}

TYPE_EMOJI = {
    "LT": "📘",
    "LAB": "🧪",
    "WS": "🎤",
    "OH": "💬",
    "MD": "🧑‍🏫",
    "OTHER": "📌",
}

_KIND_EMOJI = {"slide": "📑", "record": "🎬", "doc": "📄"}

_BUCKET_ORDER = ("Sáng", "Chiều", "Tối")
_BUCKET_EMOJI = {"Sáng": "🌅", "Chiều": "🌇", "Tối": "🌙"}

COLOR_SCHEDULE = 0x2563EB
COLOR_DIGEST = 0x16A34A
COLOR_PERSONAL = 0x9333EA


def bucket(start: str | None) -> str:
    if start is None:
        return "Tối"
    if start < "13:00":
        return "Sáng"
    if start < "18:00":
        return "Chiều"
    return "Tối"


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _clean_label(label: str | None, fallback: str = "Tài liệu") -> str:
    """Resource titles đôi khi dính luôn URL ('Video Recording WS1: ...https://...')
    — bỏ URL, dấu thừa, và cắt gọn để làm text cho masked link."""
    label = re.sub(r"https?://\S+", "", label or "").strip(" :–—-·")
    return _clip(label, 48) if label else fallback


def _join_capped(lines: list[str], limit: int) -> str:
    """Ghép lines bằng newline nhưng không vượt limit (giới hạn field/description
    của Discord embed); dòng vượt quá bị bỏ và thay bằng '…'."""
    out: list[str] = []
    used = 0
    for line in lines:
        extra = len(line) + (1 if out else 0)
        if used + extra > limit - 2:
            out.append("…")
            break
        out.append(line)
        used += extra
    return "\n".join(out)


def _time_label(item: dict) -> str:
    start, end = item.get("start"), item.get("end")
    if start and end:
        return f"{start}–{end}"
    if start:
        return start
    return "chưa rõ giờ"


def _session_lines(item: dict) -> list[str]:
    emoji = TYPE_EMOJI.get(item.get("type"), TYPE_EMOJI["OTHER"])
    line = f"{emoji} **{_time_label(item)}** · {item.get('title')}"
    if item.get("format") == "Offline" and item.get("location"):
        line += f" · 📍 {item['location']}"
    elif item.get("format") == "Zoom":
        line += " · 💻 Zoom"
    lines = [line]
    zoom_url = item.get("zoom_url")
    if zoom_url:
        lines.append(f"└ 📹 [Tham gia Zoom]({zoom_url})")
    for material in item.get("materials") or []:
        kind_emoji = _KIND_EMOJI.get(material.get("kind"), "🔗")
        lines.append(f"└ {kind_emoji} [{_clean_label(material.get('label'))}]({material.get('url')})")
    return lines


def schedule_embed(items: list[dict], date_label: str, cohort: str) -> dict:
    groups: dict[str, list[dict]] = {name: [] for name in _BUCKET_ORDER}
    for item in items:
        groups[bucket(item.get("start"))].append(item)

    fields = []
    for name in _BUCKET_ORDER:
        group_items = sorted(groups[name], key=lambda i: i.get("start") or "")
        if group_items:
            lines: list[str] = []
            for item in group_items:
                lines.extend(_session_lines(item))
            value = _join_capped(lines, 1024)
        else:
            value = "_Không có lịch_"
        fields.append({"name": f"{_BUCKET_EMOJI[name]} {name}", "value": value, "inline": False})

    return {
        "title": f"📅 Lịch {date_label} — Khoá {cohort}",
        "color": COLOR_SCHEDULE,
        "fields": fields,
    }


def _digest_line(item: dict, prefix: str = "") -> str:
    title = _clip(item.get("title") or "(không tiêu đề)", 80)
    summary = _clip(item.get("summary") or "", 100)
    jump = item.get("jump_url")
    head = f"[**{title}**]({jump})" if jump else f"**{title}**"
    line = f"• {prefix}{head}"
    if summary:
        line += f"\n ▸ {summary}"
    return line


def digest_embed(items: list[dict], personalized: bool) -> dict:
    if not items:
        return {
            "title": "📰 Bản tin",
            "color": COLOR_DIGEST,
            "description": "Chưa có bản tin nào.",
            "fields": [],
        }

    if personalized:
        lines = []
        any_sim = False
        for item in items:
            sim = (item.get("parts") or {}).get("sim") or 0
            # sim = 0 (chưa có hồ sơ sở thích) → ẩn % thay vì hiện "0%" gây hiểu lầm
            prefix = f"✨ **{round(sim * 100)}%** · " if sim > 0 else ""
            any_sim = any_sim or sim > 0
            lines.append(_digest_line(item, prefix=prefix))
        embed = {
            "title": "✨ Gợi ý dành riêng cho bạn",
            "color": COLOR_PERSONAL,
            "description": _join_capped(lines, 4000),
            "fields": [],
        }
        if not any_sim:
            embed["footer"] = ("💡 Chưa có hồ sơ sở thích — mở /hub, vào trang Bản tin "
                               "để thêm bio hoặc bookmark bài viết, gợi ý sẽ sát bạn hơn.")
        return embed

    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for item in items:
        tags = item.get("tags") or []
        slug = tags[0] if tags else "other"
        slug = slug if slug in TAG_LABELS else "other"
        if slug not in groups:
            groups[slug] = []
            order.append(slug)
        groups[slug].append(item)

    fields = []
    for slug in order:
        name = f"{TAG_EMOJI[slug]} {TAG_LABELS[slug]}"
        value = _join_capped([_digest_line(i) for i in groups[slug]], 1024)
        fields.append({"name": name, "value": value, "inline": False})

    return {"title": "📰 Bản tin mới nhất", "color": COLOR_DIGEST, "fields": fields}
