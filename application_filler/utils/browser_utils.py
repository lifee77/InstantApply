import logging
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)
async def get_playwright_instance():
    playwright = await async_playwright().start()
    return playwright

async def launch_browser(playwright, headless: bool = False, slow_mo: int = 200, test_mode: bool = True):
    """
    Launch a Playwright browser instance with fallback logic.
 
    Args:
        playwright: An instance of the Playwright object.
        headless (bool): Whether to run the browser in headless mode.
        slow_mo (int): Delay in ms between actions to slow down browser actions.
        test_mode (bool): If True, disables submit buttons to prevent accidental submissions.
 
    Returns:
        A tuple of (browser, context)
    """
    for browser_type in [playwright.chromium, playwright.firefox, playwright.webkit]:
        try:
            browser = await browser_type.launch(
                headless=headless,
                slow_mo=slow_mo,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context()
            logger.info(f"Browser launched using {browser_type.name}")
            selected_browser = browser_type.name
 
            if test_mode:
                page = await context.new_page()
                await page.add_init_script("""
    document.addEventListener('DOMContentLoaded', () => {
        const buttons = document.querySelectorAll('button[type="submit"], input[type="submit"]');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.style.border = '2px solid red';
            btn.title = 'Disabled in test mode';
        });
    });
""")
                await page.close()
 
            logger.info(f"Returning browser instance using {selected_browser}")
            return browser, context
        except Exception as e:
            logger.warning(f"Failed to launch {browser_type.name}: {str(e)}")
 
    raise RuntimeError("Failed to launch any supported browser.")

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
        await page.add_init_script("""
  window.highlightFilledFields = () => {
      const inputs = document.querySelectorAll('input, textarea, select');
      inputs.forEach(input => {
          input.addEventListener('input', () => {
              input.style.border = '2px solid green';
              input.style.backgroundColor = '#e0ffe0';
          });
      });
  };
  document.addEventListener('DOMContentLoaded', window.highlightFilledFields);
""")
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