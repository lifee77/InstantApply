import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from app import create_app

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from application_filler.strategies import gemini_answer_generator as generator

class TestGeminiAnswerGenerator(unittest.TestCase):
    def setUp(self):
        self.user_data = {
            "name": "Jane Doe",
            "skills": ["Python", "Flask"],
            "biggest_achievement": "Led a major project",
            "career_goals": "Become a senior developer",
            "work_style": "Collaborative",
            "industry_attraction": "Tech innovation",
            "professional_summary": "Experienced developer in backend systems"
        }
        self.question = "Why do you want to work here?"
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

    @patch('application_filler.strategies.gemini_answer_generator.current_app')
    @patch('application_filler.strategies.gemini_answer_generator.genai.GenerativeModel')
    def test_generate_dynamic_answer_success(self, mock_model_cls, mock_current_app):
        mock_current_app.config.get.side_effect = lambda key, default=None: "gemini-pro" if key == 'GEMINI_MODEL' else "fake-key"
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "I am passionate about your mission."
        mock_model_cls.return_value = mock_model

        result = generator.generate_dynamic_answer(self.user_data, self.question)

        self.assertEqual(result, "I am passionate about your mission.")
        mock_model.generate_content.assert_called_once()
        prompt_sent = mock_model.generate_content.call_args[0][0]
        self.assertIn(self.question, prompt_sent)
        self.assertIn(self.user_data["name"], prompt_sent)

    @patch('application_filler.strategies.gemini_answer_generator.current_app')
    @patch('application_filler.strategies.gemini_answer_generator.genai.GenerativeModel')
    def test_generate_dynamic_answer_empty_response(self, mock_model_cls, mock_current_app):
        mock_current_app.config.get.return_value = "gemini-pro"
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = ""
        mock_model_cls.return_value = mock_model

        result = generator.generate_dynamic_answer(self.user_data, self.question)
        self.assertEqual(result, "I am excited about this opportunity.")

    def tearDown(self):
        self.app_context.pop()

if __name__ == '__main__':
    unittest.main()