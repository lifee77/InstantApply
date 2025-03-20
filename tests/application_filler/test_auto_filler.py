

import unittest
from unittest.mock import AsyncMock, patch
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from application_filler.auto_filler import AutoApplicationFiller


class TestAutoApplicationFiller(unittest.IsolatedAsyncioTestCase):
    """Unit tests for AutoApplicationFiller"""

    def setUp(self):
        self.user_data = {
            "biggest_achievement": "Led a team project to success",
            "career_goals": "To grow as a data scientist",
            "experience": "3 years in backend development",
            "skills": ["Python", "SQL"],
            "needs_sponsorship": False,
            "willing_to_relocate": True,
            "available_start_date": "2025-06-01"
        }
        self.filler = AutoApplicationFiller(self.user_data, "https://example.com/job")

    async def test_map_question_to_response_strength(self):
        q = {"text": "What is your greatest strength?"}
        question, response = await self.filler.map_question_to_response(q)
        self.assertEqual(response, "Led a team project to success")

    async def test_map_question_to_response_experience(self):
        q = {"text": "Tell us about your experience"}
        question, response = await self.filler.map_question_to_response(q)
        self.assertEqual(response, "3 years in backend development")

    async def test_map_question_to_response_skills(self):
        q = {"text": "What skills do you have?"}
        question, response = await self.filler.map_question_to_response(q)
        self.assertEqual(response, "Python, SQL")

    async def test_map_question_to_response_authorization(self):
        q = {"text": "Do you require visa sponsorship?"}
        question, response = await self.filler.map_question_to_response(q)
        self.assertEqual(response, "Yes")

    async def test_map_question_to_response_relocation(self):
        q = {"text": "Are you willing to relocate?"}
        question, response = await self.filler.map_question_to_response(q)
        self.assertEqual(response, "Yes")

    async def test_map_question_to_response_fallback(self):
        q = {"text": "Why do you want to work here?"}
        question, response = await self.filler.map_question_to_response(q)
        self.assertEqual(response, "I am excited about this opportunity.")


if __name__ == '__main__':
    unittest.main()