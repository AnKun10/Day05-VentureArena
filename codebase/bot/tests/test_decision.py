"""Test decision.py với đúng data/ thật của bot — không mock Knowledge để bắt được lỗi khi ai đó
sửa schedule.yaml/faq.yaml làm gãy logic (vd bỏ field 'deadline').

Bao phủ 4 lớp chỗ khó (đề bài): ① nguồn sự thật · ② mơ hồ · ③ ngoài phạm vi · ④ đặc thù domain.
"""

import unittest
from pathlib import Path

from decision import ANSWER, CLARIFY, REFUSE_ESCALATE, REFUSE_SCOPE, decide
from knowledge import Knowledge

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class TestDecision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = Knowledge.load(DATA_DIR)

    # --- happy path ---
    def test_explicit_code_with_deadline_answers(self):
        d = decide("Lab-10 deadline khi nào?", self.kb)
        self.assertEqual(d.action, ANSWER)
        self.assertIn("23:59", d.message)
        self.assertTrue(d.citations)

    def test_explicit_code_faq_match_answers(self):
        d = decide("Nộp bài Lab-10 ở đâu?", self.kb)
        self.assertEqual(d.action, ANSWER)
        self.assertTrue(d.citations, "answer phải luôn kèm citation")

    # --- ① nguồn sự thật: không có căn cứ -> refuse, không bịa ---
    def test_no_source_refuses_and_escalates(self):
        d = decide("Con mèo của tôi bị ốm thì sao?", self.kb)
        self.assertEqual(d.action, REFUSE_ESCALATE)
        self.assertEqual(d.citations, [], "refuse thì không được có citation bịa ra")

    def test_deadline_without_data_refuses_instead_of_guessing(self):
        # LT-11 không có field 'deadline' trong schedule.yaml -> không được đoán
        d = decide("LT-11 deadline nộp gì không?", self.kb)
        self.assertEqual(d.action, REFUSE_ESCALATE)
        self.assertIn("①", d.reason or "")

    # --- ② mơ hồ / thiếu thông tin ---
    def test_ambiguous_type_asks_to_clarify(self):
        # Cần >=2 buổi cùng loại trong schedule.yaml để rơi vào nhánh clarify — schedule.yaml hiện có
        # nhiều buổi LT (LT-11, LT-12) nên câu hỏi chung chung về "buổi lý thuyết" phải hỏi lại.
        d = decide("Buổi lý thuyết tuần này học gì?", self.kb)
        self.assertEqual(d.action, CLARIFY)

    # --- ③ ngoài phạm vi / thẩm quyền ---
    def test_out_of_scope_refuses_with_reason(self):
        d = decide("Cho mình xin đáp án bài lab được không?", self.kb)
        self.assertEqual(d.action, REFUSE_SCOPE)

    def test_out_of_scope_beats_explicit_code(self):
        # Ngay cả khi có mã buổi hợp lệ, câu hỏi ngoài phạm vi vẫn phải bị chặn trước
        d = decide("Lab-10 cho mình xin đáp án được không?", self.kb)
        self.assertEqual(d.action, REFUSE_SCOPE)

    # --- mọi answer phải có citation (bất biến chống bịa) ---
    def test_every_answer_has_citation(self):
        questions = [
            "Lab-10 deadline khi nào?",
            "Nộp bài Lab-10 ở đâu?",
            "Buổi workshop có bắt buộc tham gia không?",
        ]
        for q in questions:
            d = decide(q, self.kb)
            if d.action == ANSWER:
                self.assertTrue(d.citations, f"answer cho '{q}' phải có citation")


if __name__ == "__main__":
    unittest.main()