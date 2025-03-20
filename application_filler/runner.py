import asyncio
import logging
from flask import Flask
from models.user import User, db
from models.job_recommendation import JobRecommendation
from application_filler.services.job_service import get_user_by_id, get_job_recommendations_for_user
from application_filler.services.user_service import get_user_profile_dict
from application_filler.auto_filler import AutoApplicationFiller
from application_filler.utils.browser_utils import launch_browser, create_new_page, close_browser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_pyfile('../config.py')  # Adjust the path to your actual config

async def run_application_filler_for_user(user_id):
    logger.info(f"Starting auto-apply runner for user_id: {user_id}")
    from application_filler.runner_service import auto_apply_jobs_for_user
    await auto_apply_jobs_for_user(user_id, headless=False)
    logger.info(f"Finished auto-apply runner for user_id: {user_id}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python runner.py <user_id>")
        sys.exit(1)
    user_id = int(sys.argv[1])
    logger.info(f"Triggering auto-apply for user_id: {user_id}")
    asyncio.run(run_application_filler_for_user(user_id))