"""Test IngestionCog._store() với post dạng thread trong kênh Forum "lý-thuyết"/"thực-hành-lab".

Bug thật đã bắt được: trên server thật, mỗi phòng (`Lab-D305`, `Lec-D302`...) là 1 THREAD bên trong
kênh Forum cha ("thực-hành-lab"/"lý-thuyết"), không phải kênh con riêng. Bản đầu tiên suy `class_code`
từ tên kênh CHA (đã bị resolve trước khi vào `_store`) nên mọi bài trong 2 forum này luôn ra
class_code=None — không bao giờ escalation/TA digest route đúng lớp được. Test này khoá lại việc soi
mã lớp phải dựa trên tên THREAD, không phải tên forum cha.
"""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import discord

import db
from ingestion.listener import IngestionCog


def _make_thread_message(*, thread_name: str, parent_name: str, category_name: str | None = None, content: str = "noi dung demo"):
    parent = MagicMock()
    parent.name = parent_name
    if category_name is not None:
        parent.category = MagicMock()
        parent.category.name = category_name
    else:
        parent.category = None

    thread = MagicMock(spec=discord.Thread)
    thread.name = thread_name
    # Discord luôn gán ID (snowflake) khác nhau dù 2 thread trùng tên (vd "Lab-D305" ở cả 2 khoá) —
    # băm thêm category_name để mock không vô tình trùng ID giữa các case test.
    thread.id = abs(hash((thread_name, category_name))) % 10_000_000
    thread.parent = parent
    thread.applied_tags = []
    thread.message_count = 5

    message = MagicMock()
    message.channel = thread
    message.reactions = []
    message.jump_url = f"https://discord.com/channels/1/2/{thread.id}"
    message.author.display_name = "T185"
    message.author.roles = []
    message.content = content
    message.created_at = datetime.now(timezone.utc)
    return message


class TestIngestionClassCode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        db.init_db(self.db_path)
        self.cog = IngestionCog(bot=None, db_path=self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_lab_room_thread_gets_class_code_from_thread_name_not_parent(self):
        message = _make_thread_message(thread_name="Lab-D305", parent_name="thực-hành-lab")
        self.cog._store(message, channel_name="thực-hành-lab", group="chat_lop")

        rows = db.recent_posts(self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["class_code"], "Lab-D305")
        self.assertEqual(rows[0]["channel_group"], "chat_lop")

    def test_lecture_room_thread_gets_class_code(self):
        message = _make_thread_message(thread_name="Lec-D302", parent_name="lý-thuyết")
        self.cog._store(message, channel_name="lý-thuyết", group="chat_lop")

        rows = db.recent_posts(self.db_path)
        self.assertEqual(rows[0]["class_code"], "Lec-D302")

    def test_qa_forum_thread_has_no_class_code(self):
        # Thread trong #hỏi-đáp có tiêu đề tự do (vd "QR báo lỗi/thiếu thẻ") -> không khớp prefix Lab-/Lec-
        message = _make_thread_message(thread_name="QR báo lỗi/thiếu thẻ", parent_name="hỏi-đáp")
        self.cog._store(message, channel_name="hỏi-đáp", group="forum")

        rows = db.recent_posts(self.db_path)
        self.assertIsNone(rows[0]["class_code"])

    def test_same_room_number_different_cohort_gets_distinct_class_code(self):
        # Bug thật: Khoá 3 và Khoá 4 đều có phòng "Lab-D305" riêng (server thật quan sát được) — nếu
        # không tách theo category cha (khoá), escalation của 2 khoá sẽ gộp nhầm vào 1 mã lớp.
        msg_k3 = _make_thread_message(
            thread_name="Lab-D305", parent_name="thực-hành-lab", category_name="LỚP HỌC - KHOÁ 3"
        )
        msg_k4 = _make_thread_message(
            thread_name="Lab-D305", parent_name="thực-hành-lab", category_name="LỚP HỌC - KHOÁ 4"
        )
        self.cog._store(msg_k3, channel_name="thực-hành-lab", group="chat_lop")
        self.cog._store(msg_k4, channel_name="thực-hành-lab", group="chat_lop")

        rows = {r["message_id"]: r["class_code"] for r in db.recent_posts(self.db_path)}
        self.assertEqual(rows[str(msg_k3.channel.id)], "K3-Lab-D305")
        self.assertEqual(rows[str(msg_k4.channel.id)], "K4-Lab-D305")


if __name__ == "__main__":
    unittest.main()