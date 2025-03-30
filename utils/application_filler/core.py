"""
Core module for application filler functionality
"""
import os
import time
import logging
import asyncio
from typing import Dict, Any
from playwright.async_api import Page

from models.user import User
from .utils import valid_url, save_full_page_screenshot
from .resume_handler import prioritize_resume_upload, handle_resume_upload
from .form_detector import (
    check_and_click_apply_button, detect_and_handle_form_type, 
    find_and_click_submit_button
)
from .form_filler import FormFiller
from .response_generator import ResponseGenerator
from .browser_manager import BrowserManager

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
        self.browser_manager = BrowserManager()

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
            # Create browser using the browser manager
            browser, context, page = await self.browser_manager.create_browser()
            
            try:
                # Navigate to the job URL
                navigation_success = await self.browser_manager.navigate_with_retry(page, self.job_url)
                
                if not navigation_success:
                    result["message"] = f"Failed to navigate to {self.job_url}"
                    logger.error(result["message"])
                    return result
                
                # Take a screenshot of the initial page
                try:
                    await save_full_page_screenshot(page, "initial_page")
                except Exception as e:
                    logger.warning(f"Failed to save initial page screenshot: {str(e)}")
                
                # Handle cookie banners and login prompts
                await self._handle_cookie_banners(page)
                await asyncio.sleep(1)
                await self._handle_login_prompts(page)
                await asyncio.sleep(1)
                
                # Check if we need to click an "Apply" button first
                apply_button_found = await check_and_click_apply_button(page)
                if apply_button_found:
                    logger.info("Apply button found and clicked")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=15000)
                        await asyncio.sleep(3)
                        
                        # Save screenshot after clicking apply
                        await save_full_page_screenshot(page, "after_apply_button")
                        
                        # Handle any new cookie banners or login prompts
                        await self._handle_cookie_banners(page)
                        await self._handle_login_prompts(page)
                    except Exception as e:
                        logger.warning(f"Wait for load state after apply button failed: {str(e)}")
                
                # Look for application form patterns
                form_found = await detect_and_handle_form_type(page)
                if not form_found:
                    result["message"] = "Could not detect application form on the page"
                    logger.warning(result["message"])
                    
                    # Analyze page elements for debugging
                    await self._analyze_page_elements(page)
                    await save_full_page_screenshot(page, "no_form_detected")
                    
                    # Keep browser open for debugging
                    if os.environ.get('DEBUG_MODE') == '1':
                        logger.info("DEBUG_MODE enabled - keeping browser open for 30 seconds")
                        await asyncio.sleep(30)
                    
                    return result
                
                # Upload resume first to trigger auto-population
                resume_uploaded = await prioritize_resume_upload(page, self.user.resume_file_path)
                result["resume_uploaded"] = resume_uploaded
                
                if resume_uploaded:
                    logger.info("Resume uploaded successfully, waiting for potential autofill...")
                    await asyncio.sleep(5)
                    await save_full_page_screenshot(page, "after_resume_upload")
                
                # Fill the basic identifier fields
                await self.form_filler.fill_basic_fields(page, self.user_data)
                await asyncio.sleep(1)
                
                # Fill the rest of the form fields
                form_result = await self.form_filler.fill_application_form(page)
                result["form_completed"] = form_result["success"]
                result["failed_fields"] = form_result["failed_fields"]
                
                # Take a screenshot of the completed form
                await save_full_page_screenshot(page, "filled_form")
                
                # Submit the form if not in debug mode
                if not os.environ.get('DEBUG_MODE') == '1':
                    submit_clicked = await find_and_click_submit_button(page)
                    if submit_clicked:
                        logger.info("Submit button clicked successfully")
                        await asyncio.sleep(5)
                        await save_full_page_screenshot(page, "submission_result")
                    else:
                        logger.warning("Could not find submit button")
                else:
                    logger.info("DEBUG_MODE enabled - skipping form submission")
                    submit_clicked = False
                
                # Set overall success
                result["success"] = result["form_completed"]
                
                # Set final message
                if result["success"]:
                    result["message"] = "Application form filled successfully."
                    if submit_clicked:
                        result["message"] += " Form was submitted."
                    logger.info("Application process completed successfully")
                else:
                    result["message"] = f"Application partially completed with {len(result['failed_fields'])} failed fields."
                    logger.warning(f"Application process partially completed: {result['message']}")
                
                # Keep browser open for debugging in debug mode
                if os.environ.get('DEBUG_MODE') == '1':
                    logger.info("DEBUG_MODE enabled - keeping browser open for 30 seconds")
                    await asyncio.sleep(30)
                
            except Exception as e:
                error_message = f"Error during application process: {str(e)}"
                result["message"] = error_message
                result["error_details"] = str(e)
                result["success"] = False
                logger.error(error_message)
                
                # Try to take a screenshot of the error state
                try:
                    await save_full_page_screenshot(page, "error_state")
                except Exception:
                    logger.warning("Failed to save error state screenshot")
            
            finally:
                # Clean up resources using browser manager
                await self.browser_manager.cleanup()
                
        except Exception as e:
            error_message = f"Failed to initialize browser: {str(e)}"
            result["message"] = error_message
            result["error_details"] = str(e)
            result["success"] = False
            logger.error(error_message)
        
        return result
    
    async def _handle_cookie_banners(self, page: Page):
        """Handle common cookie consent banners"""
        try:
            # Common cookie consent button selectors
            cookie_button_selectors = [
                'button:has-text("Accept")', 
                'button:has-text("Accept All")',
                'button:has-text("I Accept")',
                'button:has-text("Allow All")',
                'button:has-text("Agree")',
                'button:has-text("Accept Cookies")',
                'button:has-text("Got It")',
                'button:has-text("Reject")',
                'button:has-text("Reject All")',
                'button:has-text("Decline")',
                'button:has-text("No")',
                'button:has-text("Close")',
                '[id*="cookie"] button',
                '[class*="cookie"] button',
                '[id*="gdpr"] button',
                '[class*="gdpr"] button'
            ]
            
            for selector in cookie_button_selectors:
                try:
                    # Check if the selector exists and is visible
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        logger.info(f"Found cookie banner button: {selector}")
                        await button.click()
                        logger.info("Clicked cookie banner button")
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.debug(f"Error handling cookie selector {selector}: {str(e)}")
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error in cookie banner handler: {str(e)}")
            return False
    
    async def _handle_login_prompts(self, page: Page):
        """Handle login/signup prompts that might appear"""
        try:
            # Common selectors for closing login prompts or skipping sign in
            login_button_selectors = [
                'button:has-text("Skip")',
                'button:has-text("Skip for now")',
                'button:has-text("Continue without")',
                'button:has-text("Not now")',
                'button:has-text("Later")',
                'button:has-text("Close")',
                'a:has-text("Skip")',
                'a:has-text("Continue without")',
                'a:has-text("No thanks")',
                '.modal button:has-text("Close")',
                '.modal .close',
                '.login-modal .close',
                '[aria-label="Close"]'
            ]
            
            for selector in login_button_selectors:
                try:
                    # Check if the selector exists and is visible
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        logger.info(f"Found login/signup prompt button: {selector}")
                        await button.click()
                        logger.info("Clicked login/signup prompt button")
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.debug(f"Error handling login selector {selector}: {str(e)}")
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error in login prompt handler: {str(e)}")
            return False

    async def _analyze_page_elements(self, page: Page):
        """Analyze page elements to debug why form detection failed"""
        try:
            logger.info("Analyzing page elements to debug form detection issues")
            
            # Check for iframes
            iframes = await page.query_selector_all('iframe')
            logger.info(f"Found {len(iframes)} iframes on the page")
            
            # Check for forms
            forms = await page.query_selector_all('form')
            logger.info(f"Found {len(forms)} forms on the page")
            
            # Check for input elements
            inputs = await page.query_selector_all('input')
            logger.info(f"Found {len(inputs)} input elements on the page")
            
            # Check for buttons
            buttons = await page.query_selector_all('button')
            logger.info(f"Found {len(buttons)} buttons on the page")
            
            # Check page URL (might have redirected)
            current_url = page.url
            logger.info(f"Current page URL: {current_url}")
            
            # Check for login-related elements
            login_elements = await page.query_selector_all('*:has-text("login"), *:has-text("sign in"), *:has-text("register"), *:has-text("create account")')
            if len(login_elements) > 0:
                logger.info(f"Found {len(login_elements)} login-related elements")
                logger.warning("Page might require login before accessing application form")
            
            return True
        except Exception as e:
            logger.error(f"Error analyzing page elements: {str(e)}")
            return False