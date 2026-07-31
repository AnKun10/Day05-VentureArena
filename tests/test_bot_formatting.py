import pytest

from companion_discord.formatting import TAG_LABELS, bucket, format_digest, format_schedule


# ---- bucket -----------------------------------------------------------

@pytest.mark.parametrize(
    "start,expected",
    [
        (None, "Tối"),
        ("09:00", "Sáng"),
        ("12:59", "Sáng"),
        ("13:00", "Chiều"),
        ("17:59", "Chiều"),
        ("18:00", "Tối"),
        ("23:00", "Tối"),
    ],
)
def test_bucket_maps_start_time_to_vietnamese_period(start, expected):
    assert bucket(start) == expected


# ---- format_schedule ---------------------------------------------------

def _session(**overrides):
    base = {
        "type": "LAB", "title": "Buổi Lab", "date": "2026-07-30",
        "start": "09:00", "end": "13:00", "location": "D305", "host": "Giảng viên",
        "format": "Offline", "cohort": "4", "zoom_url": None,
        "session_code": None, "jump_url": None, "materials": [],
    }
    base.update(overrides)
    return base


def test_format_schedule_header_includes_date_label_and_cohort():
    text = format_schedule([], "2026-07-30", "4")
    assert text.startswith("📅 Lịch 2026-07-30 — Khoá 4")


def test_format_schedule_groups_sessions_into_sang_chieu_toi_sorted_by_start():
    items = [
        _session(title="Lab", start="09:00", end="13:00", location="D305"),
        _session(title="LT", start="14:00", end="18:00", location="D302"),
        _session(type="WS", title="Workshop", start="19:00", end="20:00", format="Zoom", location=None, zoom_url="https://zoom/1"),
        _session(type="WS", title="Sớm hơn", start="08:00", end="08:30", location="D100"),
    ]
    text = format_schedule(items, "2026-07-30", "4")
    lines = text.splitlines()

    # Sáng group has both morning sessions, sorted by start (08:00 before 09:00)
    sang_idx = lines.index("Sáng:")
    assert "  [08:00–08:30: Sớm hơn — D100]" in lines[sang_idx + 1]
    assert "  [09:00–13:00: Lab — D305]" in lines[sang_idx + 2]

    assert "Chiều:" in lines
    chieu_idx = lines.index("Chiều:")
    assert "  [14:00–18:00: LT — D302]" in lines[chieu_idx + 1]

    assert "Tối:" in lines
    toi_idx = lines.index("Tối:")
    assert "  [19:00–20:00: Workshop — Zoom]" in lines[toi_idx + 1]


def test_format_schedule_empty_group_shows_khong_co_lich():
    items = [_session(title="Lab", start="09:00", end="13:00")]
    text = format_schedule(items, "2026-07-30", "4")
    lines = text.splitlines()
    assert "Chiều: không có lịch" in lines
    assert "Tối: không có lịch" in lines
    assert "Chiều:" not in [line for line in lines if line == "Chiều:"]


def test_format_schedule_all_groups_empty():
    text = format_schedule([], "2026-07-30", "4")
    lines = text.splitlines()
    assert "Sáng: không có lịch" in lines
    assert "Chiều: không có lịch" in lines
    assert "Tối: không có lịch" in lines


def test_format_schedule_material_lines_and_zoom_url_line():
    items = [
        _session(
            title="Buổi Lab", start="09:00", end="13:00", location="D305",
            materials=[{"label": "Tài liệu hướng dẫn", "url": "https://codelabs.vlearn.dev/codelab"}],
        ),
        _session(
            type="WS", title="Workshop", start="19:00", end="20:00", format="Zoom",
            location=None, zoom_url="https://zoom/42", materials=[{"label": "Slide", "url": "https://slide"}],
        ),
    ]
    text = format_schedule(items, "2026-07-30", "4")
    lines = text.splitlines()
    assert "    - Tài liệu hướng dẫn: https://codelabs.vlearn.dev/codelab" in lines
    assert "    - Slide: https://slide" in lines
    assert "    - Zoom: https://zoom/42" in lines


def test_format_schedule_start_end_none_shows_gio_tba():
    items = [_session(title="Buổi bù", start=None, end=None, location=None, format=None)]
    text = format_schedule(items, "2026-07-30", "4")
    assert "  [giờ TBA: Buổi bù]" in text.splitlines()


# ---- format_digest -------------------------------------------------------

def _news(**overrides):
    base = {
        "message_id": "1", "title": "Tin tức A",
        "summary": "x" * 200,
        "tags": ["ai-model"],
        "jump_url": "https://discord.com/channels/1/2/3",
    }
    base.update(overrides)
    return base


def test_format_digest_empty_returns_placeholder():
    assert format_digest([], personalized=False) == "Chưa có bản tin nào."
    assert format_digest([], personalized=True) == "Chưa có bản tin nào."


def test_format_digest_groups_by_first_tag_label_and_truncates_summary_to_120():
    items = [
        _news(title="A", tags=["ai-model"]),
        _news(title="B", tags=["dataset", "ai-model"]),
        _news(title="C", tags=[]),
    ]
    text = format_digest(items, personalized=False)
    lines = text.splitlines()

    assert "**AI Model**" in lines
    assert "**Dataset**" in lines
    assert "**Other**" in lines

    bullet_a = next(line for line in lines if line.startswith("• A"))
    assert bullet_a == f"• A — {'x' * 120} (https://discord.com/channels/1/2/3)"


def test_format_digest_all_ten_taxonomy_labels_present():
    assert TAG_LABELS == {
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


def test_format_digest_personalized_not_grouped_with_sim_prefix():
    items = [
        _news(title="A", tags=["ai-model"], summary="short summary"),
        _news(title="B", tags=["dataset"], summary="another one", parts={"sim": 0.851}),
    ]
    text = format_digest(items, personalized=True)
    lines = text.splitlines()

    assert lines[0] == "✨0% • A — short summary (https://discord.com/channels/1/2/3)"
    assert lines[1] == "✨85% • B — another one (https://discord.com/channels/1/2/3)"
    assert "**" not in text


def test_format_digest_personalized_missing_parts_defaults_to_zero():
    items = [_news(title="A", summary="s")]
    text = format_digest(items, personalized=True)
    assert text.startswith("✨0% • A")
