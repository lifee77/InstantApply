"""
Core module for application filler functionality
"""
import os
import time
import logging
import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright, Playwright, Page
from flask import current_app

from models.user import User
from .utils import valid_url, save_full_page_screenshot
from .resume_handler import prioritize_resume_upload, handle_resume_upload
from .form_detector import (
    check_and_click_apply_button, detect_and_handle_form_type, 
    find_and_click_submit_button
)
from .form_filler import FormFiller
from .response_generator import ResponseGenerator

logger = logging.getLogger(__name__)

class ApplicationFiller:
    """
    Main class for automating job applications
    Coordinates the different components for filling out job applications
    """
    
    def __init__(self, user: User, job_url: str):
        """
        Initialize the application filler
        
        Args:
            user: User object with profile information
            job_url: URL of the job application
        """
        self.user = user
        self.job_url = job_url
        
        # Validate URL
        if not valid_url(job_url):
            logger.warning(f"Invalid job URL provided: {job_url}")
        
        # Initialize user_data from user object for response mapping
        self.user_data = {
            "name": self.user.name,
            "email": self.user.email,
            "professional_summary": self.user.professional_summary,
            "skills": self.user.skills,
            "experience": self.user.experience,
            "career_goals": self.user.career_goals,
            "biggest_achievement": self.user.biggest_achievement,
            "work_style": self.user.work_style,
            "industry_attraction": self.user.industry_attraction,
            "willing_to_relocate": self.user.willing_to_relocate,
            "authorization_status": self.user.authorization_status,
            "available_start_date": self.user.available_start_date,
            "portfolio_links": self.user.linkedin_url,
            "phone": getattr(self.user, 'phone', ''),
            "certifications": getattr(self.user, '_certifications', None),
            "languages": getattr(self.user, '_languages', None),
        }
        
        # Initialize components
        self.response_generator = ResponseGenerator(self.user_data)
        self.form_filler = FormFiller(self.response_generator)

    async def fill_application(self):
        """
        Main function that handles browser creation, parsing, filling, and submission of the application.
        
        Returns:
            Dictionary with application results and status
        """
        result = {
            "success": False,
            "message": "",
            "url": self.job_url,
            "user": self.user.email,
            "form_completed": False,
            "resume_uploaded": False,
            "failed_fields": []
        }
        
        logger.info(f"Starting application process for {self.job_url}")
        
        try:
            async with async_playwright() as p:
                # Launch browser with more stable parameters
                browser = await p.firefox.launch(
                    headless=False,  # Keep browser visible
                    slow_mo=100,    # Slow down automation for stability
                    args=[
                        "--no-sandbox",
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                    ]
                )
                
                # Create a context with viewport size and user agent
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
                )
                
                # Open new page and navigate
                page = await context.new_page()
                await page.goto(self.job_url, timeout=60000)
                
                # Wait for the page to load
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    logger.info("Page loaded successfully")
                except Exception as e:
                    logger.warning(f"Page loading timed out, continuing anyway: {str(e)}")
                
                # Take full page screenshot and save HTML for analysis
                await save_full_page_screenshot(page, "initial_page")
                
                # Add manual delay to ensure page is fully loaded
                await asyncio.sleep(5)
                
                # Check if we need to click an "Apply" button or similar first
                apply_button_found = await check_and_click_apply_button(page)
                if apply_button_found:
                    # Wait for navigation after clicking apply button
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        # Save screenshot of the application form page
                        await save_full_page_screenshot(page, "after_apply_button")
                    except Exception as e:
                        logger.warning(f"Page loading after apply button timed out: {str(e)}")
                
                # Look for common application form patterns and handle them
                form_found = await detect_and_handle_form_type(page)
                if not form_found:
                    result["message"] = "Could not detect application form on the page"
                    logger.warning(result["message"])
                    
                    # Save final screenshot
                    await save_full_page_screenshot(page, "final_state")
                    
                    # Keep browser open longer if debug mode is enabled
                    if os.environ.get('DEBUG_MODE') == '1':
                        logger.info("DEBUG_MODE enabled - keeping browser open for 60 seconds")
                        await asyncio.sleep(60)
                    return result
                
                # Step 1: Upload resume FIRST before filling the form
                # This should trigger auto-population of fields in many application systems
                resume_uploaded = await prioritize_resume_upload(page, self.user.resume_file_path)
                result["resume_uploaded"] = resume_uploaded
                
                if resume_uploaded:
                    # Wait for potential auto-fill to happen
                    logger.info("Resume uploaded successfully, waiting for potential autofill...")
                    await asyncio.sleep(5)
                    await save_full_page_screenshot(page, "after_resume_upload_autofill")
                
                # Step 2: Fill in the basic identifier fields (name, email, etc.)
                await self.form_filler.fill_basic_fields(page, self.user_data)
                
                # Step 3: Now fill the rest of the form
                form_result = await self.form_filler.fill_application_form(page)
                result["form_completed"] = form_result["success"]
                result["failed_fields"] = form_result["failed_fields"]
                
                # Check if there's a submit button and click it
                submit_clicked = await find_and_click_submit_button(page)
                if submit_clicked:
                    logger.info("Submit button clicked successfully")
                    
                    # Wait a bit for submission to complete
                    await asyncio.sleep(5)
                    
                    # Save screenshot of confirmation page
                    await save_full_page_screenshot(page, "confirmation_page")
                
                # Set overall success based on form completion and resume upload
                result["success"] = result["form_completed"]
                
                # Keep browser open for manual inspection if requested (dev mode)
                if os.environ.get('DEBUG_MODE') == '1':
                    logger.info("DEBUG_MODE enabled - keeping browser open for 30 seconds")
                    await asyncio.sleep(30)
                
                # Set final message
                if result["success"]:
                    result["message"] = "Application form filled successfully."
                    if submit_clicked:
                        result["message"] += " Submit button was clicked."
                    logger.info("Application process completed successfully")
                else:
                    result["message"] = f"Application partially completed with {len(form_result['failed_fields'])} failed fields."
                    logger.warning(f"Application process partially completed: {result['message']}")
                
                # Close browser
                await browser.close()
                
        except Exception as e:
            error_message = f"Error during application process: {str(e)}"
            result["message"] = error_message
            result["success"] = False
            logger.error(error_message)
            
        return result