"""
Module for handling resume uploads in job applications
"""
import os
import logging
import asyncio
from playwright.async_api import Page

from .utils import save_full_page_screenshot

logger = logging.getLogger(__name__)

async def handle_resume_upload(page: Page, resume_file_path: str):
    """
    Handle the upload of the resume if a file input is present.

    Args:
        page: The Playwright page object
        resume_file_path: Path to the resume file

    Returns:
        bool: True if resume was uploaded successfully
    """
    if resume_file_path and os.path.exists(resume_file_path):
        try:
            logger.info(f"Uploading resume from: {resume_file_path}")
            
            # Try different selectors for file upload inputs
            file_input_selectors = [
                'input[type="file"]',
                'input[name="resume"]',
                'input[accept=".pdf,.doc,.docx"]',
                'label:has-text("Resume") input[type="file"]',
                'label:has-text("CV") input[type="file"]'
            ]
            
            for selector in file_input_selectors:
                file_input = await page.query_selector(selector)
                if file_input:
                    await file_input.set_input_files(resume_file_path)
                    logger.info(f"Resume uploaded successfully using selector: {selector}")
                    await asyncio.sleep(2)  # Wait after upload
                    return True
            
            logger.warning("Resume file input not found after trying multiple selectors.")
            return False
            
        except Exception as e:
            logger.error(f"Error uploading resume: {str(e)}")
            return False
    else:
        logger.warning("No resume file path or file doesn't exist.")
        return False

async def prioritize_resume_upload(page: Page, resume_file_path: str):
    """
    Upload resume first, before filling any other fields.
    This is important because some forms auto-populate fields from the resume.
    
    Args:
        page: The Playwright page object
        resume_file_path: Path to resume file
        
    Returns:
        bool: True if resume was uploaded
    """
    logger.info("Looking for resume upload field first")
    
    # First take a screenshot to see the current page
    await save_full_page_screenshot(page, "before_resume_upload")
    
    # Common selectors for resume upload fields
    resume_selectors = [
        'input[type="file"][accept*="pdf"]',
        'input[type="file"][accept*="doc"]',
        'input[type="file"]',
        'label:has-text("Resume") input[type="file"]',
        'label:has-text("Upload") input[type="file"]',
        'label:has-text("CV") input[type="file"]',
        'div:has-text("Upload resume") input[type="file"]',
        'div:has-text("Upload your resume") input[type="file"]',
        'div[aria-label*="resume"] input[type="file"]'
    ]
    
    if resume_file_path and os.path.exists(resume_file_path):
        for selector in resume_selectors:
            try:
                logger.info(f"Looking for resume upload with selector: {selector}")
                file_input = await page.wait_for_selector(selector, timeout=3000)
                if file_input:
                    logger.info(f"Found resume upload field with selector: {selector}")
                    await file_input.set_input_files(resume_file_path)
                    logger.info(f"Resume uploaded from: {resume_file_path}")
                    
                    # Wait for autofill to potentially occur
                    await asyncio.sleep(5)
                    
                    # Check if there's a "parse resume" or similar button that needs to be clicked
                    parse_buttons = [
                        'button:has-text("Parse")',
                        'button:has-text("Extract")',
                        'button:has-text("Autofill")',
                        'a:has-text("Autofill")',
                        'button.parse-resume'
                    ]
                    
                    for btn_selector in parse_buttons:
                        parse_button = await page.query_selector(btn_selector)
                        if parse_button and await parse_button.is_visible():
                            await parse_button.click()
                            logger.info(f"Clicked parse button: {btn_selector}")
                            await asyncio.sleep(3)  # Wait for parsing to complete
                            break
                    
                    # Take screenshot after upload
                    await save_full_page_screenshot(page, "after_resume_upload")
                    return True
            except Exception as e:
                logger.debug(f"Error with resume selector {selector}: {str(e)}")
        
        logger.warning("Could not find resume upload field")
        return False
    else:
        logger.warning("No resume file path found or file does not exist")
        return False