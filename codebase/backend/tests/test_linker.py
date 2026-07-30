import pytest
from ingest.linker import detect_kind, detect_session


@pytest.mark.parametrize("title,expected", [
    ("Slide Workshop WS2: Problem → MVP Canvas", "WS-2"),
    ("Video Recording WS1: Kick off", "WS-1"),
    ("Record LT-10: Eval & Golden set", "LT-10"),
    ("Slide buổi lý thuyết 11 — Agent & tool use", "LT-11"),
    ("Đề bài + hướng dẫn Lab 10 (Discord bot)", "Lab-10"),
    ("Thông tin Workshop 3 tối nay", "WS-3"),
    ("Office hour 5 cuối tuần", "OH-5"),
    ("OH-6 đăng ký slot", "OH-6"),
    ("Ngân hàng đề chính thức Build Phase", None),
    ("Tổng quan chương trình 6 tuần", None),
])
def test_detect_session(title, expected):
    assert detect_session(title) == expected


@pytest.mark.parametrize("title,expected", [
    ("Slide Workshop WS2", "slide"),
    ("Video Recording WS1", "record"),
    ("Record LT-10: Eval", "record"),
    ("Đề bài + hướng dẫn Lab 10", "doc"),
    ("Worksheet JTBD bản dịch", "link"),
])
def test_detect_kind(title, expected):
    assert detect_kind(title) == expected
