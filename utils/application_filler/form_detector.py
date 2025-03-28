"""
Module for detecting different application form types
"""
import logging
import asyncio
from playwright.async_api import Page

from .utils import save_full_page_screenshot

logger = logging.getLogger(__name__)

async def check_and_click_apply_button(page: Page):
    """
    Look for and click an "Apply" button if one exists.
    
    Args:
        page: The Playwright page object
        
    Returns:
        bool: True if an apply button was found and clicked
    """
    # Common selectors for apply buttons
    apply_button_selectors = [
        'button:has-text("Apply")', 
        'button:has-text("Apply Now")',
        'a:has-text("Apply")',
        'a:has-text("Apply Now")',
        'a.apply-button',
        'button.apply-button',
        '[data-automation="apply-button"]',
        '[aria-label*="apply"]'
    ]
    
    for selector in apply_button_selectors:
        try:
            logger.info(f"Looking for apply button with selector: {selector}")
            button = await page.query_selector(selector)
            if button:
                # Check if button is visible
                is_visible = await button.is_visible()
                if is_visible:
                    logger.info(f"Found apply button with selector: {selector}")
                    await button.click()
                    logger.info("Clicked apply button")
                    return True
        except Exception as e:
            logger.debug(f"Error checking apply button selector '{selector}': {str(e)}")
    
    logger.info("No apply button found or could not be clicked")
    return False

async def detect_and_handle_form_type(page: Page):
    """
    Detect what type of application form we're dealing with and handle it appropriately.
    
    Args:
        page: The Playwright page object
        
    Returns:
        bool: True if a form was detected and handled
    """
    # Take a screenshot before detection
    await save_full_page_screenshot(page, "before_form_detection")
    
    # Check for different types of application forms
    form_types = [
        check_for_standard_form,
        check_for_greenhouse_form,
        check_for_lever_form,
        check_for_workday_form,
        check_for_ashby_form,
        check_for_indeed_form,
        check_for_linkedin_form
    ]
    
    for check_function in form_types:
        try:
            logger.info(f"Trying form detection with {check_function.__name__}")
            form_detected = await check_function(page)
            if form_detected:
                logger.info(f"Form detected with {check_function.__name__}")
                return True
        except Exception as e:
            logger.error(f"Error in {check_function.__name__}: {str(e)}")
    
    logger.warning("No form type detected")
    return False

async def check_for_standard_form(page: Page):
    """Check for a standard HTML form"""
    form = await page.query_selector('form')
    if form:
        logger.info("Standard form detected")
        return True
    return False

async def check_for_greenhouse_form(page: Page):
    """Check for Greenhouse ATS form"""
    if 'greenhouse' in await page.content():
        logger.info("Greenhouse form detected")
        # Handle Greenhouse specific logic here
        return True
    return False

async def check_for_lever_form(page: Page):
    """Check for Lever ATS form"""
    if 'lever' in await page.content():
        logger.info("Lever form detected")
        # Handle Lever specific logic here
        return True
    return False

async def check_for_workday_form(page: Page):
    """Check for Workday ATS form"""
    if 'workday' in await page.content():
        logger.info("Workday form detected")
        # Handle Workday specific logic here
        return True
    return False

async def check_for_ashby_form(page: Page):
    """Check for Ashby ATS form"""
    url = page.url
    if 'ashbyhq' in url or 'ashby' in await page.content():
        logger.info("Ashby form detected")
        
        # Look for and click the first step in the application
        try:
            # Check if there's a "start application" or similar button
            start_buttons = [
                'button:has-text("Start")',
                'button:has-text("Begin")',
                'button:has-text("Start Application")',
                'a:has-text("Start Application")'
            ]
            
            for selector in start_buttons:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    await button.click()
                    logger.info(f"Clicked start button with selector: {selector}")
                    await asyncio.sleep(2)
                    await save_full_page_screenshot(page, "after_ashby_start_button")
                    break
            
            # Look for name input fields - Ashby typically has these at the beginning
            name_fields = await page.query_selector_all('input[name*="name"], input[placeholder*="name"]')
            if name_fields:
                for field in name_fields:
                    field_name = await field.get_attribute('name') or await field.get_attribute('placeholder') or "unknown"
                    if "first" in field_name.lower():
                        await field.fill("First Name")  # Placeholder - this will be replaced by user data
                    elif "last" in field_name.lower():
                        await field.fill("Last Name")   # Placeholder - this will be replaced by user data
                    else:
                        await field.fill("Full Name")   # Placeholder - this will be replaced by user data
            
            # Look for email input
            email_field = await page.query_selector('input[type="email"], input[name*="email"], input[placeholder*="email"]')
            if email_field:
                await email_field.fill("email@example.com")  # Placeholder - this will be replaced by user data
            
            # Look for "Next" button to proceed to questions
            next_buttons = [
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'button[type="submit"]',
                'button.next-button'
            ]
            
            for selector in next_buttons:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    await button.click()
                    logger.info(f"Clicked next button with selector: {selector}")
                    await asyncio.sleep(3)
                    await save_full_page_screenshot(page, "after_ashby_next_button")
                    break
        except Exception as e:
            logger.error(f"Error handling Ashby form: {str(e)}")
        
        return True
    return False

async def check_for_indeed_form(page: Page):
    """Check for Indeed application form"""
    url = page.url
    if 'indeed' in url or 'indeed' in await page.content():
        logger.info("Indeed form detected")
        
        # Handle Indeed specific logic here
        try:
            # Look for "Apply now" button
            apply_buttons = await page.query_selector_all('button:has-text("Apply now"), a:has-text("Apply now")')
            if apply_buttons:
                await apply_buttons[0].click()
                logger.info("Clicked 'Apply now' button on Indeed")
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Error with Indeed apply button: {str(e)}")
            
        return True
    return False

async def check_for_linkedin_form(page: Page):
    """Check for LinkedIn EasyApply form"""
    url = page.url
    if 'linkedin.com/jobs' in url:
        logger.info("LinkedIn job page detected")
        
        try:
            # Look for "Easy Apply" button
            easy_apply_buttons = [
                'button:has-text("Easy Apply")',
                'button:has-text("Apply")',
                'button.jobs-apply-button'
            ]
            
            for selector in easy_apply_buttons:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    await button.click()
                    logger.info(f"Clicked LinkedIn apply button with selector: {selector}")
                    await asyncio.sleep(3)
                    await save_full_page_screenshot(page, "after_linkedin_apply_button")
                    
                    # LinkedIn often has a multi-step application form
                    # Look for next button to navigate through steps
                    next_buttons = [
                        'button:has-text("Next")',
                        'button:has-text("Continue")',
                        'button[aria-label="Continue to next step"]'
                    ]
                    
                    for next_selector in next_buttons:
                        next_button = await page.query_selector(next_selector)
                        if next_button and await next_button.is_visible():
                            await next_button.click()
                            logger.info("Clicked LinkedIn next button")
                            await asyncio.sleep(2)
                            await save_full_page_screenshot(page, "linkedin_next_step")
                            break
                    
                    return True
        except Exception as e:
            logger.error(f"Error with LinkedIn apply button: {str(e)}")
            
        return True
    return False

async def find_and_click_submit_button(page: Page):
    """
    Find and click the submit button to complete the application.
    
    Args:
        page: The Playwright page object
        
    Returns:
        bool: True if submit button was found and clicked
    """
    # Common submit button selectors
    submit_selectors = [
        'button[type="submit"]',
        'button:has-text("Submit")',
        'button:has-text("Submit Application")',
        'button:has-text("Apply")',
        'input[type="submit"]',
        'button.submit-button',
        'button:has-text("Send Application")',
        'button:has-text("Complete Application")'
    ]
    
    # Take a screenshot before looking for submit button
    await save_full_page_screenshot(page, "before_submit_button")
    
    for selector in submit_selectors:
        try:
            logger.info(f"Looking for submit button with selector: {selector}")
            submit_button = await page.query_selector(selector)
            if submit_button:
                is_visible = await submit_button.is_visible()
                if is_visible:
                    logger.info(f"Found submit button with selector: {selector}")
                    await submit_button.click()
                    logger.info("Clicked submit button")
                    return True
        except Exception as e:
            logger.debug(f"Error checking submit button selector '{selector}': {str(e)}")
            
    logger.warning("No submit button found or could not be clicked")
    return False