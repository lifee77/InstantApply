import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def get_playwright_instance():
    playwright = await async_playwright().start()
    return playwright

async def launch_browser(playwright, headless: bool = False, slow_mo: int = 200, test_mode: bool = True):
    """
    Launch a browser with fallback support for multiple engines.
    
    Args:
        playwright: Playwright instance
        headless: Whether to run browser in headless mode
        slow_mo: Delay between actions for more human-like behavior
        test_mode: Whether to run in test mode (prevents form submission)
        
    Returns:
        tuple: (browser, context)
    """
    # Try different browser engines in order of preference
    browser_types = [
        (playwright.chromium, "chromium", ["--no-sandbox"]),
        (playwright.firefox, "firefox", []),
        (playwright.webkit, "webkit", [])
    ]
    
    for browser_type, name, args in browser_types:
        try:
            logger.info(f"Attempting to launch browser using {name}")
            browser = await browser_type.launch(
                headless=headless,
                slow_mo=slow_mo,
                args=args
            )
            
            # Create a persistent context
            context = await browser.new_context(
                viewport={"width": 1280, "height": 960},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            )
            
            # Apply test mode to prevent actual submissions if needed
            if test_mode:
                # Create and close a page just to add the init script to all future pages
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
            
            logger.info(f"Successfully launched {name}")
            logger.info(f"Returning browser instance using {name}")
            return browser, context
            
        except Exception as e:
            logger.warning(f"Failed to launch {name}: {str(e)}")
    
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