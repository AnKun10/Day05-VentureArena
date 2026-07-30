import unittest

from ingestion.session_linker import best_session_code, find_session_codes


class TestSessionLinker(unittest.TestCase):
    def test_hyphenated_code(self):
        self.assertEqual(find_session_codes("Record LT-10: Eval & Golden set"), ["LT-10"])

    def test_glued_code(self):
        self.assertEqual(best_session_code("Slide Workshop WS2: Problem to MVP Canvas"), "WS-2")

    def test_spelled_out_prefix(self):
        self.assertEqual(best_session_code("De bai + huong dan Lab 10 (Discord bot)"), "Lab-10")

    def test_no_match_returns_none(self):
        self.assertIsNone(best_session_code("Tong quan chuong trinh, khong gan buoi nao"))

    def test_multiple_matches_keeps_order_dedup(self):
        codes = find_session_codes("So sanh WS2 voi WS-2 va Lab-10")
        self.assertEqual(codes, ["WS-2", "Lab-10"])


if __name__ == "__main__":
    unittest.main()