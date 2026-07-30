"""Test config.classify_channel() với tên kênh THẬT quan sát trên server BTC (không phải tên tôi tự đoán) —
xem ảnh chụp cấu trúc server trong lịch sử trao đổi khi build phần này.

Điểm quan trọng nhất: match phải CHÍNH XÁC (exact), không phải substring — "thông-báo" là cụm rất phổ biến,
kênh riêng của một nhóm khác trên cùng server cũng đặt tên kiểu "thông-báo-nhóm"/"thảo-luận-nhóm". Nếu lỡ
match lỏng, ingestion sẽ nuốt luôn nội dung riêng tư của nhóm khác vào KB chung — đây là bug thật đã bắt được
và sửa (không phải case giả định).
"""

import unittest
from types import SimpleNamespace

import config


class TestClassifyChannel(unittest.TestCase):
    def test_official_channels_recognized(self):
        cases = {
            "thông-báo-chung": "thong_bao",
            "🔔-thông-báo": "thong_bao",
            "🖼-tài-nguyên": "tai_nguyen",
            "🙋-hỏi-đáp": "forum",
            "🏆-chia-sẻ": "forum",
            "📖-bài-học": "forum",
            "lý-thuyết": "chat_lop",
            "thực-hành-lab": "chat_lop",
        }
        for name, expected_group in cases.items():
            with self.subTest(name=name):
                self.assertEqual(config.classify_channel(name), expected_group)

    def test_other_teams_private_channels_are_not_ingested(self):
        # Bug đã bắt được: substring match cũ coi "thông-báo-nhóm" (kênh riêng nhóm khác) là kênh thông báo chính thức.
        for name in ["thông-báo-nhóm", "thảo-luận-nhóm", "team", "build-phase-tickets"]:
            with self.subTest(name=name):
                self.assertIsNone(config.classify_channel(name))

    def test_lab_and_lecture_rooms_get_class_code(self):
        self.assertEqual(config.class_code_for_channel("Lab-D305"), "Lab-D305")
        self.assertEqual(config.class_code_for_channel("Lec-D302"), "Lec-D302")
        self.assertIsNone(config.class_code_for_channel("lý-thuyết"))

    def test_cohort_from_category(self):
        self.assertEqual(config.cohort_from_category("LỚP HỌC - KHOÁ 3"), "K3")
        self.assertEqual(config.cohort_from_category("LỚP HỌC - KHOÁ 4"), "K4")
        self.assertIsNone(config.cohort_from_category("CỘNG ĐỒNG"))
        self.assertIsNone(config.cohort_from_category(None))

    def test_same_room_number_in_different_cohorts_gets_distinct_class_code(self):
        # Bug đã bắt được: Khoá 3 và Khoá 4 đều có phòng "Lab-D305" riêng (2 thread khác nhau, cùng tên) —
        # không tách theo khoá thì escalation của học viên 2 khoá bị gộp nhầm vào 1 mã lớp khi route cho TA.
        k3 = config.class_code_for_channel("Lab-D305", cohort=config.cohort_from_category("LỚP HỌC - KHOÁ 3"))
        k4 = config.class_code_for_channel("Lab-D305", cohort=config.cohort_from_category("LỚP HỌC - KHOÁ 4"))
        self.assertEqual(k3, "K3-Lab-D305")
        self.assertEqual(k4, "K4-Lab-D305")
        self.assertNotEqual(k3, k4)

    def test_class_code_for_discord_channel_shared_by_ask_and_ingestion(self):
        # Bug thật: ask_cog.py từng gọi class_code_for_channel() thẳng, KHÔNG truyền cohort, nên escalation
        # từ /ask trong thread "Lab-D305" ra mã lớp trần "Lab-D305" — không khớp "K3-Lab-D305"/"K4-Lab-D305"
        # mà ingestion.listener.py ghi cho CÙNG thread đó. Giờ cả 2 nơi phải dùng chung hàm này.
        category = SimpleNamespace(name="LỚP HỌC - KHOÁ 3")
        forum = SimpleNamespace(name="thực-hành-lab", category=category)
        thread = SimpleNamespace(name="Lab-D305", parent=forum)

        self.assertEqual(config.class_code_for_discord_channel(thread), "K3-Lab-D305")

    def test_class_code_for_discord_channel_non_thread_returns_none(self):
        # Kênh Text thường (không phải thread trong forum) không có .parent -> không phải phòng lớp cụ thể.
        text_channel = SimpleNamespace(name="chung")
        self.assertIsNone(config.class_code_for_discord_channel(text_channel))

    def test_unrelated_channels_ignored(self):
        for name in ["🔝-activity", "🤖-gõ-commands", "💬-chung", "OFFICE HOURS - KÊNH 01"]:
            with self.subTest(name=name):
                self.assertIsNone(config.classify_channel(name))


if __name__ == "__main__":
    unittest.main()