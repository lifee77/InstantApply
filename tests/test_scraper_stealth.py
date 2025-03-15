#!/usr/bin/env python3
import sys
import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# List of user agents to rotate through
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
]

async def test_indeed_scraper():
    """Test Indeed job search with stealth mode"""
    # Format the search query
    job_title = "Software Engineer"
    location = "Remote"
    search_url = f"https://www.indeed.com/jobs?q={job_title.replace(' ', '+')}&l={location.replace(' ', '+')}"
    
    logger.info(f"Testing Indeed scraper with stealth mode...")
    logger.info(f"URL: {search_url}")
    
    async with async_playwright() as p:
        try:
            # Use a random user agent
            user_agent = random.choice(USER_AGENTS)
            
            # Create debug directory
            debug_dir = os.path.join(os.path.dirname(__file__), '../debug')
            os.makedirs(debug_dir, exist_ok=True)
            
            # Launch browser with debugging options
            browser = await p.chromium.launch(
                headless=False,  # Non-headless for debugging
                slow_mo=50  # Slow down operations for better visibility
            )
            
            # Enhanced context with timezone, geolocation and permissions
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                java_script_enabled=True,
            )
            
            # Add extra headers for legitimacy
            await context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'https://www.google.com/'
            })
            
            # Page setup
            page = await context.new_page()
            
            # Masking automation
            await page.evaluate("""() => {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // Overwrite the plugins property to use a custom getter
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        return [1, 2, 3, 4, 5];
                    }
                });
                
                // Overwrite the languages property to use a custom getter
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            }""")
            
            # Navigate to Indeed
            logger.info("Navigating to Indeed...")
            await page.goto(search_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Take screenshot
            screenshot_path = os.path.join(debug_dir, 'indeed_stealth_test.png')
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Check for job listings
            job_selectors = [
                "div.job_seen_beacon",
                "div.jobsearch-ResultsList div[data-testid='job-card']", 
                "div.tapItem"
            ]
            
            job_listings_found = False
            for selector in job_selectors:
                try:
                    job_cards = await page.query_selector_all(selector)
                    if job_cards:
                        job_listings_found = True
                        logger.info(f"Found {len(job_cards)} jobs using selector: {selector}")
                        break
                except Exception:
                    pass
            
            if not job_listings_found:
                logger.error("No job listings found - likely blocked!")
                
                # Save page content for debugging
                content = await page.content()
                with open(os.path.join(debug_dir, 'indeed_html.txt'), 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info("Saved page HTML to debug/indeed_html.txt")
            
            # Check if we're being blocked
            blocked_phrases = ["captcha", "unusual traffic", "automated access", "suspicious activity"]
            page_text = await page.evaluate('() => document.body.innerText')
            
            for phrase in blocked_phrases:
                if phrase.lower() in page_text.lower():
                    logger.error(f"Detected blocking: page contains '{phrase}'")
            
            # Pause to keep browser open for manual inspection
            logger.info("Browser will stay open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            
            await browser.close()
            logger.info("Test completed")
            
        except Exception as e:
            logger.error(f"Error during test: {str(e)}")
            try:
                if 'browser' in locals() and not browser.is_closed():
                    await browser.close()
            except:
                pass

if __name__ == "__main__":
    asyncio.run(test_indeed_scraper())
