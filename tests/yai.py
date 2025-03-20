import os
import asyncio
from playwright.async_api import async_playwright
from models.user import User
from models.job_recommendation import JobRecommendation
from utils.application_filler import ApplicationFiller
import logging
import sys
import os

# Add the root of the project (where 'models' is located) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def integration_test():
    async with async_playwright() as p:
        browser = None
        for browser_type in [p.firefox, p.webkit, p.chromium]:
            try:
                logger.info(f"Attempting to launch browser using {browser_type.__class__.__name__}")
                browser = await browser_type.launch(
                    headless=False,
                    slow_mo=100,  # Slowing down the process to make it visible
                    args=["--no-sandbox"] if browser_type == p.chromium else []
                )
                logger.info(f"✅ Successfully launched {browser_type.__class__.__name__}")
                break
            except Exception as e:
                logger.error(f"⚠️ Failed to launch {browser_type.__class__.__name__}: {str(e)}")
                continue
        
        if browser is None:
            logger.error("❌ Failed to launch any browser. Exiting test.")
            return

        try:
            # Create a new page with error handling
            page = await browser.new_page()
            logger.info("✅ New page created")

            # Fetch jobs from the database
            jobs = JobRecommendation.query.filter_by(applied=False).all()
            if not jobs:
                logger.error("❌ No jobs found to apply for.")
                await browser.close()
                return

            user = User.query.first()  # Fetch first user or you can modify this to a specific user
            if not user:
                logger.error("❌ No user found.")
                await browser.close()
                return

            # Loop through each job and apply
            for job in jobs:
                try:
                    logger.info(f"Processing job: {job.url}")
                    job_url = job.url
                    
                    # Navigate to the job URL
                    await page.goto(job_url, timeout=60000)
                    logger.info(f"✅ Opened the website: {job_url}")

                    # Wait for page load and extract some content
                    await page.wait_for_timeout(5000)
                    page_title = await page.title()
                    logger.info(f"✅ Page Title: {page_title}")

                    # Create ApplicationFiller instance for the job
                    app_filler = ApplicationFiller(user, job_url)

                    # Fill the application
                    await app_filler.fill_application(page)

                    # Simulate form submission or take other actions
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

                    # Optionally, you could submit the form, but for testing, we will skip the final submission
                    submit_button = await page.query_selector('button[type="submit"]')
                    if submit_button:
                        logger.info("Found submit button, but will not click (test mode).")
                    else:
                        logger.info("No submit button found on the page.")
                    
                except Exception as e:
                    logger.error(f"❌ Error applying to job {job.url}: {str(e)}")
            
            # Clean up by closing the browser
            await browser.close()
            logger.info("✅ Test complete - pausing for visual inspection.")
            await asyncio.sleep(15)  # Pause for visual inspection

        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            if browser:
                await browser.close()

if __name__ == '__main__':
    asyncio.run(integration_test())
