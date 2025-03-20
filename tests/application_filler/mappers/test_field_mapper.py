import unittest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the module to test
from application_filler.mappers.field_mapper import map_question_to_field

class TestFieldMapper(unittest.TestCase):
    """Tests for the map_question_to_field function"""

    def test_strength_question(self):
        question = "What is your greatest strength?"
        self.assertEqual(map_question_to_field(question), "biggest_achievement")

    def test_experience_question(self):
        question = "Describe your relevant experience."
        self.assertEqual(map_question_to_field(question), "experience")

    def test_skills_question(self):
        question = "What technical skills do you have?"
        self.assertEqual(map_question_to_field(question), "skills")

    def test_work_authorization_question(self):
        question = "Do you require visa sponsorship?"
        self.assertEqual(map_question_to_field(question), "authorization_status")

    def test_relocation_question(self):
        question = "Are you willing to relocate?"
        self.assertEqual(map_question_to_field(question), "willing_to_relocate")

    def test_start_date_question(self):
        question = "When can you start?"
        self.assertEqual(map_question_to_field(question), "available_start_date")

    def test_portfolio_question(self):
        question = "Do you have a GitHub or portfolio link?"
        self.assertEqual(map_question_to_field(question), "portfolio_links")

    def test_certification_question(self):
        question = "What certifications do you have?"
        self.assertEqual(map_question_to_field(question), "certifications")

    def test_languages_question(self):
        question = "What languages do you speak?"
        self.assertEqual(map_question_to_field(question), "languages")

    def test_fallback_question(self):
        question = "Tell us about yourself"
        self.assertEqual(map_question_to_field(question), "career_goals")

if __name__ == '__main__':
    unittest.main()
