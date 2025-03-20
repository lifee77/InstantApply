import unittest
from unittest.mock import AsyncMock, patch
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from application_filler.utils import browser_utils


class TestBrowserUtils(unittest.IsolatedAsyncioTestCase):
    """Unit tests for browser_utils async functions"""

    @patch('application_filler.utils.browser_utils.async_playwright', new_callable=AsyncMock)
    async def test_launch_browser_success(self, mock_async_playwright):
        mock_context_manager = AsyncMock()
        mock_async_playwright.return_value = mock_context_manager
        mock_playwright_instance = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_playwright_instance
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context

        browser, context = await browser_utils.launch_browser(headless=True)

        mock_playwright_instance.chromium.launch.assert_called_once()
        mock_browser.new_context.assert_called_once()
        self.assertEqual(browser, mock_browser)
        self.assertEqual(context, mock_context)

    @patch('application_filler.utils.browser_utils.logger')
    async def test_create_new_page_success(self, mock_logger):
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page

        page = await browser_utils.create_new_page(mock_context)

        self.assertEqual(page, mock_page)
        mock_logger.info.assert_called_with("✅ New page created")

    @patch('application_filler.utils.browser_utils.logger')
    async def test_create_new_page_failure(self, mock_logger):
        mock_context = AsyncMock()
        mock_context.new_page.side_effect = Exception("Page creation failed")

        page = await browser_utils.create_new_page(mock_context)
        self.assertIsNone(page)
        mock_logger.error.assert_called_once()

    @patch('application_filler.utils.browser_utils.logger')
    async def test_close_browser_success(self, mock_logger):
        mock_browser = AsyncMock()
        await browser_utils.close_browser(mock_browser)
        mock_browser.close.assert_awaited_once()
        mock_logger.info.assert_called_with("✅ Browser closed successfully")

    @patch('application_filler.utils.browser_utils.logger')
    async def test_close_browser_failure(self, mock_logger):
        mock_browser = AsyncMock()
        mock_browser.close.side_effect = Exception("Close failed")
        await browser_utils.close_browser(mock_browser)
        mock_logger.error.assert_called_once()


if __name__ == '__main__':
    unittest.main()
