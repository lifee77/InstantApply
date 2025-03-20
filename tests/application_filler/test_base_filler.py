import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from application_filler.base_filler import BaseApplicationFiller

class ConcreteFiller(BaseApplicationFiller):
    async def map_question_to_response(self, question):
        return "input.selector", "Mocked Response"
    
    async def fill_application(self, page=None):
        return "mock fill_application"
    
    async def fill_application_form(self, page):
        return "mock fill_application_form"

class TestBaseApplicationFiller(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "resume_file_path": "/tmp/mock_resume.pdf",
            "skills": ["Python", "JavaScript"],
            "experience": ["Software Engineer at TestCo"]
        }
        self.filler = ConcreteFiller(user_data=self.user_data, job_url="https://example.com/job/123")

    @patch('application_filler.base_filler.Page')
    async def test_parse_application_page_returns_empty_on_error(self, mock_page):
        mock_page.query_selector_all.side_effect = Exception("Simulated parsing error")
        result = await self.filler.parse_application_page(mock_page)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch('application_filler.base_filler.asyncio.sleep', new_callable=AsyncMock)
    async def test_fill_application_field_success(self, mock_sleep):
        page = AsyncMock()
        element = AsyncMock()
        page.query_selector.return_value = element
        element.is_visible.return_value = True
        element.evaluate.return_value = "input"
        element.get_attribute.return_value = "text"
        element.input_value.return_value = ""

        success = await self.filler.fill_application_field(page, "#test-input", "Test Answer")
        self.assertTrue(success)
        element.type.assert_called_once_with("Test Answer", delay=unittest.mock.ANY)

    @patch('application_filler.base_filler.os.path.exists', return_value=False)
    async def test_handle_resume_upload_no_resume(self, mock_exists):
        page = AsyncMock()
        success = await self.filler.handle_resume_upload(page)
        self.assertFalse(success)

    @patch('application_filler.base_filler.os.path.exists', return_value=True)
    @patch('application_filler.base_filler.asyncio.sleep', new_callable=AsyncMock)
    async def test_handle_resume_upload_success(self, mock_sleep, mock_exists):
        page = AsyncMock()
        file_input = AsyncMock()
        page.query_selector.return_value = file_input
        success = await self.filler.handle_resume_upload(page)
        self.assertTrue(success)
        file_input.set_input_files.assert_called_once()

if __name__ == '__main__':
    unittest.main()