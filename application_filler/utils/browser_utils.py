import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def launch_browser(headless: bool = True):
    """
    Launch a Playwright browser instance with default settings.
    
    Args:
        headless (bool): Whether to run the browser in headless mode.
    
    Returns:
        A tuple of (browser, context)
    """
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context()
        logger.info("Browser launched using Firefox")
        return browser, context

async def create_new_page(context):
    """
    Create a new Playwright page with error handling.
    
    Args:
        context: Playwright browser context.
    
    Returns:
        A Playwright page object.
    """
    try:
        page = await context.new_page()
        logger.info("✅ New page created")
        return page
    except Exception as e:
        logger.error(f"❌ Failed to create new page: {str(e)}")
        return None

async def close_browser(browser):
    """
    Gracefully close the browser instance.
    
    Args:
        browser: The Playwright browser instance to close.
    """
    try:
        await browser.close()
        logger.info("✅ Browser closed successfully")
    except Exception as e:
        logger.error(f"❌ Error closing browser: {str(e)}")