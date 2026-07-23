import unittest

from app.exams import grade_single_answer


class ExamGradingHelperTests(unittest.TestCase):
    def test_word_bank_answers_are_compared_case_insensitively(self):
        question = {
            "type": "word-bank",
            "correct_answer": '["Alpha", "Beta"]',
        }

        self.assertTrue(grade_single_answer(question, '["alpha", "beta"]'))
        self.assertFalse(grade_single_answer(question, '["alpha", "gamma"]'))

    def test_short_answer_accepts_comma_separated_variants_case_insensitively(self):
        question = {
            "type": "short-answer",
            "correct_answer": "Paris, City of Paris",
        }

        self.assertTrue(grade_single_answer(question, " city of paris "))
        self.assertFalse(grade_single_answer(question, "Rome"))

    def test_essay_is_not_auto_graded(self):
        question = {
            "type": "essay",
            "correct_answer": "",
        }

        self.assertFalse(grade_single_answer(question, "A written response"))


if __name__ == "__main__":
    unittest.main()
