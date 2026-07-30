import json

from ingest.sources import ManifestSource
from ingest.sources.manifest import split_header


def test_split_header_simple():
    author, ts, content = split_header(
        "Vonhatcuong—14:15 23/7/26lúc 14:15 Thứ Năm, 23 tháng 7, 2026Link tài liệu :https://x")
    assert author == "Vonhatcuong"
    assert ts == "2026-07-23T14:15:00+07:00"
    assert content == "Link tài liệu :https://x"


def test_split_header_name_with_emdash_and_hyphens():
    author, ts, content = split_header(
        "Admin — ODIN—22:40 24/7/26lúc 22:40 Thứ Sáu, 24 tháng 7, 2026Tài liệu Workshop")
    assert author == "Admin — ODIN" and content == "Tài liệu Workshop"
    author2, _, content2 = split_header(
        "T024 - Trần Văn Ngọc - 01512—21:49 26/7/26lúc 21:49 Chủ Nhật, 26 tháng 7, 2026cảm ơn a1Thêm Biểu Cảm")
    assert author2 == "T024 - Trần Văn Ngọc - 01512"
    assert content2 == "cảm ơn a"                       # tail reaction bị strip


def test_split_header_relative_date_variant():
    author, ts, content = split_header(
        "Admin — ODIN—Hôm qua lúc 15:57lúc 15:57 Thứ Tư, 29 tháng 7, 2026Record WS2:https://zoom")
    assert author == "Admin — ODIN"
    assert ts == "2026-07-29T15:57:00+07:00"
    assert content == "Record WS2:https://zoom"


def test_split_header_passthrough_without_header():
    author, ts, content = split_header("Chào cả nhà, đây là bài chia sẻ bình thường.")
    assert author is None and ts is None
    assert content == "Chào cả nhà, đây là bài chia sẻ bình thường."

MANIFEST = {
    "schema_version": 3,
    "channels": [
        {
            "source_name": "sharing",
            "type": "forum",
            "forum_posts": [
                {
                    "id": "2001",
                    "title": "Cách setup AI log",
                    "url": "https://discord.com/x/2001",
                    "author": {"display_name": None},
                    "created_at": "2026-07-25T04:38:38.677Z",
                    "reactions": None,
                    "starter_message": {
                        "content": "Chia sẻ cách setup.\nChi tiết bên dưới.",
                        "author": {"display_name": None},
                        "created_at": "2026-07-25T04:38:38.677Z",
                        "jump_url": "https://discord.com/x/2001/jump",
                        "reactions": [{"emoji": "❤️", "count": 3}, {"emoji": "👍", "count": 2}],
                    },
                    "comments": [
                        {"id": "2002", "content": "Hay quá!", "author": {},
                         "created_at": "2026-07-25T05:00:00.000Z"},
                        {"id": "2003", "content": "   ", "author": {}, "created_at": None},
                    ],
                },
                {"id": "2004", "title": "", "starter_message": None, "content": None},
            ],
        },
        {
            "source_name": "lessons",
            "type": "forum",
            "forum_posts": [
                {"id": "2010", "title": "Bài học tuần 4", "starter_message": {"content": "Nội dung."},
                 "created_at": "2026-07-26T00:00:00Z"},
            ],
        },
        {
            "source_name": "resources",
            "type": "text",
            "messages": [
                {"id": "2020", "content": "Chào mừng bạn đến với #📚-tài-nguyên!Đây là sự khởi đầu."},
                {"id": "2021", "content": "Slide Workshop WS2: Problem\nhttps://slides",
                 "jump_url": "https://discord.com/x/2021", "created_at": None},
            ],
        },
        {"source_name": "general", "type": "text", "messages": [{"id": "2030", "content": "hello"}]},
        {"source_name": "questions", "type": "forum", "forum_posts": [
            {"id": "2040", "title": "Hỏi cái này?", "starter_message": {"content": "?"}}]},
    ],
}


def write_manifest(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_maps_channels_and_skips_unrelated(tmp_path):
    posts = ManifestSource(write_manifest(tmp_path)).fetch(since={})
    by_channel = {}
    for p in posts:
        by_channel.setdefault(p.channel, []).append(p)
    assert set(by_channel) == {"chia-se", "bai-hoc", "tai-nguyen"}   # general/questions bị bỏ
    assert [p.message_id for p in by_channel["chia-se"]] == ["2001"]  # post rỗng 2004 bị bỏ
    assert [p.message_id for p in by_channel["tai-nguyen"]] == ["2021"]  # welcome 2020 bị bỏ


def test_forum_post_fields_normalized(tmp_path):
    post = next(p for p in ManifestSource(write_manifest(tmp_path)).fetch(since={})
                if p.message_id == "2001")
    assert post.created_at == "2026-07-25T04:38:38.677+00:00"        # Z normalize cho py3.10
    assert post.author == "(ẩn danh)" and post.author_role == "Học viên"
    assert post.hearts == 5                                           # 3 + 2 reactions
    assert len(post.comments) == 1                                    # comment trắng bị bỏ
    assert post.comments[0].content == "Hay quá!"
    assert post.jump_url == "https://discord.com/x/2001/jump"


def test_resource_title_is_first_line_with_fallback_ts(tmp_path):
    res = next(p for p in ManifestSource(write_manifest(tmp_path)).fetch(since={})
               if p.channel == "tai-nguyen")
    assert res.title == "Slide Workshop WS2: Problem"
    assert res.created_at == "2026-07-31T00:00:00+00:00"              # thiếu ts → fallback


def test_respects_checkpoint(tmp_path):
    src = ManifestSource(write_manifest(tmp_path))
    posts = src.fetch(since={"chia-se": 2001, "bai-hoc": 0, "tai-nguyen": 3000})
    ids = {p.message_id for p in posts}
    assert ids == {"2010"}                                            # chia-se & tai-nguyen đã qua checkpoint
