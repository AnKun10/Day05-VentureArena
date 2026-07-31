"""Tests cho companion_discord.formatting (embed builders thuần, không cần discord)."""

import pytest

from companion_discord.formatting import (
    TAG_LABELS,
    bucket,
    digest_embed,
    schedule_embed,
)


# ---------- bucket ----------

@pytest.mark.parametrize("start,expected", [
    (None, "Tối"),
    ("08:00", "Sáng"),
    ("12:59", "Sáng"),
    ("13:00", "Chiều"),
    ("17:59", "Chiều"),
    ("18:00", "Tối"),
    ("20:00", "Tối"),
])
def test_bucket(start, expected):
    assert bucket(start) == expected


# ---------- schedule_embed ----------

def _ev(**kw):
    base = {"type": "WS", "title": "X", "date": "2026-07-27", "start": None,
            "end": None, "cohort": "all", "format": "Zoom", "zoom_url": None,
            "host": None, "location": None, "session_code": None,
            "jump_url": None, "materials": []}
    base.update(kw)
    return base


def test_schedule_embed_groups_and_order():
    items = [
        _ev(type="LT", title="Buổi Lý thuyết", start="09:00", end="13:00",
            format="Offline", location="D302"),
        _ev(type="LAB", title="Buổi Lab", start="14:00", end="18:00",
            format="Offline", location="D305"),
        _ev(type="OH", title="Office Hours", start="20:00"),
    ]
    embed = schedule_embed(items, "Thứ 5 · 31/07/2026", "4")
    assert embed["title"] == "📅 Lịch Thứ 5 · 31/07/2026 — Khoá 4"
    names = [f["name"] for f in embed["fields"]]
    assert names == ["🌅 Sáng", "🌇 Chiều", "🌙 Tối"]
    sang, chieu, toi = (f["value"] for f in embed["fields"])
    assert "📘 **09:00–13:00** · Buổi Lý thuyết · 📍 D302" in sang
    assert "🧪 **14:00–18:00** · Buổi Lab · 📍 D305" in chieu
    assert "💬" in toi and "Office Hours" in toi and "💻 Zoom" in toi


def test_schedule_embed_empty_group_and_tba():
    items = [_ev(type="MD", title="Mentor Duty", start=None)]
    embed = schedule_embed(items, "d", "3")
    sang, chieu, toi = (f["value"] for f in embed["fields"])
    assert sang == "_Không có lịch_" and chieu == "_Không có lịch_"
    assert "**chưa rõ giờ**" in toi
    # chỉ có start (thiếu end) → hiện đúng giờ start
    embed2 = schedule_embed([_ev(start="20:00")], "d", "3")
    assert "**20:00**" in embed2["fields"][2]["value"]


def test_schedule_embed_materials_and_zoom_links():
    items = [_ev(type="WS", title="Workshop 1: Kick-off", start="20:00",
                 zoom_url="https://zoom.us/j/1",
                 materials=[
                     {"label": "Video Recording WS1: Kick offhttps://zoom.us/rec/x",
                      "url": "https://d/1", "kind": "record"},
                     {"label": "Slide trên VLearn", "url": "https://vlearn.dev",
                      "kind": "slide"},
                 ])]
    value = schedule_embed(items, "d", "4")["fields"][2]["value"]
    assert "└ 📹 [Tham gia Zoom](https://zoom.us/j/1)" in value
    # label được làm sạch URL dính liền và giữ dạng masked link
    assert "└ 🎬 [Video Recording WS1: Kick off](https://d/1)" in value
    assert "└ 📑 [Slide trên VLearn](https://vlearn.dev)" in value


def test_schedule_embed_caps_field_length():
    items = [_ev(title="A" * 200, start="20:00") for _ in range(30)]
    value = schedule_embed(items, "d", "4")["fields"][2]["value"]
    assert len(value) <= 1024 and value.endswith("…")


# ---------- digest_embed ----------

def _news(**kw):
    base = {"message_id": "1", "title": "Bài viết", "summary": "Tóm tắt",
            "tags": ["ai-tools"], "jump_url": "https://discord.com/x"}
    base.update(kw)
    return base


def test_digest_embed_empty():
    embed = digest_embed([], personalized=False)
    assert embed["description"] == "Chưa có bản tin nào."
    assert digest_embed([], personalized=True)["description"] == "Chưa có bản tin nào."


def test_digest_embed_groups_by_tag_with_emoji():
    items = [
        _news(title="Bài 1", tags=["ai-tools"]),
        _news(title="Bài 2", tags=["ai-tools"]),
        _news(title="Bài 3", tags=["dataset"]),
        _news(title="Bài 4", tags=[]),                # không tag → Other
        _news(title="Bài 5", tags=["tag-la"]),        # tag lạ → Other
    ]
    embed = digest_embed(items, personalized=False)
    assert embed["title"] == "📰 Bản tin mới nhất"
    names = [f["name"] for f in embed["fields"]]
    assert names == ["🛠️ AI Tools", "📊 Dataset", "📌 Other"]
    ai_tools = embed["fields"][0]["value"]
    assert "[**Bài 1**](https://discord.com/x)" in ai_tools
    assert "▸ Tóm tắt" in ai_tools
    other = embed["fields"][2]["value"]
    assert "Bài 4" in other and "Bài 5" in other


def test_digest_embed_clips_title_and_summary():
    long = _news(title="T" * 200, summary="S" * 300)
    value = digest_embed([long], personalized=False)["fields"][0]["value"]
    assert "T" * 79 + "…" in value          # title cắt 80
    assert "S" * 99 + "…" in value          # summary cắt 100
    # không có jump_url → title vẫn in đậm, không thành link
    no_link = digest_embed([_news(jump_url=None)], personalized=False)
    assert "• **Bài viết**" in no_link["fields"][0]["value"]


def test_digest_embed_personalized_prefix_and_no_groups():
    items = [
        _news(title="Gợi ý 1", parts={"sim": 0.87}),
        _news(title="Gợi ý 2", parts={}),             # thiếu sim → 0%
    ]
    embed = digest_embed(items, personalized=True)
    assert embed["title"] == "✨ Gợi ý dành riêng cho bạn"
    assert embed["fields"] == []
    assert "✨ **87%** · [**Gợi ý 1**](https://discord.com/x)" in embed["description"]
    assert "✨ **0%** · [**Gợi ý 2**]" in embed["description"]


def test_tag_labels_complete():
    assert set(TAG_LABELS) == {
        "ai-model", "ai-skill", "ai-tools", "api-mcp", "dataset",
        "soft-skills", "survey", "system-design", "ui-ux", "other",
    }
