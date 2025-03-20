import logging
import asyncio
from flask import current_app
from application_filler.services.job_service import get_user_by_id, get_job_recommendations_for_user
from application_filler.services.user_service import get_user_profile_dict
from application_filler.auto_filler import AutoApplicationFiller
from application_filler.utils.browser_utils import get_playwright_instance, launch_browser, create_new_page, close_browser
from models.user import db

logger = logging.getLogger(__name__)

async def auto_apply_jobs_for_user(user_id, headless=False):
    """
    Automatically applies to job recommendations for the given user.
    
    Steps:
      1. Fetch the user by ID.
      2. Retrieve pending job recommendations for that user.
      3. Extract and normalize the user profile.
      4. Initialize Playwright once for the user session.
      5. For each job:
           a. Launch a browser instance.
           b. Create a new page.
           c. Use AutoApplicationFiller to fill and submit the application.
           d. Close the browser.
           e. Mark the job as applied in the DB.
      6. Stop the Playwright instance after all jobs are processed.
    """
    with current_app.app_context():
        user = get_user_by_id(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found.")
            return

        jobs = get_job_recommendations_for_user(user, min_score=0)
        if not jobs:
            logger.info(f"No job recommendations found for user {user.email}")
            return

        # Retrieve a clean dictionary representation of the user's profile
        user_data = get_user_profile_dict(user.id)
        logger.info(f"Starting auto-apply for {user.email} on {len(jobs)} jobs.")
        
        playwright = await get_playwright_instance()

        for job in jobs:
            logger.info(f"Processing job: {job.job_title} at {job.company} - {job.url}")
            try:
                # Launch browser using our utility function
                browser, context = await launch_browser(playwright, headless=False, slow_mo=200, test_mode=False)
                page = await create_new_page(context)
                if not page:
                    logger.error("Failed to create a new page. Skipping job.")
                    await close_browser(browser)
                    continue

                # Use AutoApplicationFiller to fill and submit the application form
                filler = AutoApplicationFiller(user_data, job.url)
                await filler.fill_application(browser_context=context)
                logger.info(f"Job {job.url} processed using {browser.browser_type.name}")
                await close_browser(browser)

                # Mark the job as applied and commit the change to the database
                job.applied = True
                db.session.commit()
                logger.info(f"Completed application for job at URL: {job.url}")
            except Exception as e:
                logger.error(f"Error applying to job {job.url}: {str(e)}")
                db.session.rollback()
                continue
        
        await playwright.stop()
        logger.info(f"Auto-apply process completed for user {user.email}")
        
        logger.info(f"Auto-apply process completed for user {user.email}")