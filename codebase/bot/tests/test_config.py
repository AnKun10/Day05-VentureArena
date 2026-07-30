"""Test config.classify_channel() với tên kênh THẬT quan sát trên server BTC (không phải tên tôi tự đoán) —
xem ảnh chụp cấu trúc server trong lịch sử trao đổi khi build phần này.

Điểm quan trọng nhất: match phải CHÍNH XÁC (exact), không phải substring — "thông-báo" là cụm rất phổ biến,
kênh riêng của một nhóm khác trên cùng server cũng đặt tên kiểu "thông-báo-nhóm"/"thảo-luận-nhóm". Nếu lỡ
match lỏng, ingestion sẽ nuốt luôn nội dung riêng tư của nhóm khác vào KB chung — đây là bug thật đã bắt được
và sửa (không phải case giả định).
"""

import unittest

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

    def test_unrelated_channels_ignored(self):
        for name in ["🔝-activity", "🤖-gõ-commands", "💬-chung", "OFFICE HOURS - KÊNH 01"]:
            with self.subTest(name=name):
                self.assertIsNone(config.classify_channel(name))


if __name__ == "__main__":
    unittest.main()