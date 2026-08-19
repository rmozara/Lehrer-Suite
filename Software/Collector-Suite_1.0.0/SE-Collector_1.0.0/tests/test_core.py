import unittest

from se_collector.config import load_form
from se_collector.core import evaluate, grade_for_points


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.form = load_form("SE1")

    def test_grade_value_for_37_points(self):
        self.assertEqual(grade_for_points(self.form, 37), ("3-", 3.3))

    def test_complete_evaluation(self):
        answers = {f"q{i:02d}": 3 for i in range(1, 23)}
        _, total, label, value, sections = evaluate(self.form, answers)
        self.assertEqual(total, 66)
        self.assertEqual((label, value), ("1+", 0.7))
        self.assertEqual(sections["muendlich"], 27)
        self.assertEqual(sections["partner"], 9)
        self.assertEqual(sections["stillarbeit"], 12)
        self.assertEqual(sections["voraussetzungen"], 18)


if __name__ == "__main__":
    unittest.main()
