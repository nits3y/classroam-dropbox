import unittest

from app.exams import extract_import_questions_payload, normalize_imported_questions


class ExamImportValidationTests(unittest.TestCase):
    def test_extract_import_questions_payload_ignores_metadata_fields(self):
        payload = {
            "questions": [
                {
                    "questionType": "Multiple Choice",
                    "questionText": "What is 2 + 2?",
                    "answerOptions": ["3", "4", "5"],
                    "correctAnswer": "4",
                    "points": 1,
                }
            ],
            "title": "Imported exam",
            "Class": "Section A",
            "classId": 7,
            "Description": "Ignored",
            "Instructions": "Ignored",
        }

        questions, error = extract_import_questions_payload(payload)

        self.assertIsNone(error)
        self.assertEqual(len(questions), 1)

    def test_require_correct_answers_for_multiple_choice_questions(self):
        parsed = [
            {
                "questionType": "Multiple Choice",
                "questionText": "Choose the correct answer",
                "answerOptions": ["A", "B"],
                "points": 1,
            }
        ]

        normalized, errors = normalize_imported_questions(parsed)

        self.assertEqual(normalized, [])
        self.assertTrue(errors)
        self.assertIn("correctAnswer", errors[0])


if __name__ == "__main__":
    unittest.main()
