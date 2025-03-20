import unittest
from unittest.mock import patch, AsyncMock
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from application_filler import runner

class TestRunner(unittest.IsolatedAsyncioTestCase):
    @patch('application_filler.runner.get_user_by_id')
    @patch('application_filler.runner.get_job_recommendations_for_user')
    @patch('application_filler.runner.get_user_profile_dict')
    @patch('application_filler.runner.launch_browser')
    @patch('application_filler.runner.create_new_page')
    @patch('application_filler.runner.close_browser')
    @patch('application_filler.runner.AutoApplicationFiller')
    async def test_run_application_filler_for_user_success(
        self, mock_filler_cls, mock_close_browser, mock_create_new_page, 
        mock_launch_browser, mock_get_user_profile, mock_get_jobs, mock_get_user
    ):
        mock_user = AsyncMock(id=1, email="test@example.com")
        mock_get_user.return_value = mock_user
        mock_get_jobs.return_value = [AsyncMock(url="https://job.com")]
        mock_get_user_profile.return_value = {"email": "test@example.com"}
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_launch_browser.return_value = (mock_browser, mock_context)
        mock_create_new_page.return_value = AsyncMock()

        mock_filler = AsyncMock()
        mock_filler_cls.return_value = mock_filler

        await runner.run_application_filler_for_user(1)

        mock_get_user.assert_called_once_with(1)
        mock_get_jobs.assert_called_once()
        mock_filler.fill_application.assert_awaited_once()

    @patch('application_filler.runner.get_user_by_id', return_value=None)
    async def test_run_application_filler_for_user_no_user(self, mock_get_user):
        result = await runner.run_application_filler_for_user(999)
        self.assertIsNone(result)
        mock_get_user.assert_called_once_with(999)

    @patch('application_filler.runner.get_user_by_id')
    @patch('application_filler.runner.get_job_recommendations_for_user', return_value=[])
    async def test_run_application_filler_for_user_no_jobs(self, mock_get_jobs, mock_get_user):
        mock_user = AsyncMock(id=1, email="test@example.com")
        mock_get_user.return_value = mock_user
        result = await runner.run_application_filler_for_user(1)
        self.assertIsNone(result)
        mock_get_jobs.assert_called_once()

if __name__ == '__main__':
    unittest.main()
