"""
Form detection functionality for application filler
"""
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from playwright.async_api import Page, ElementHandle
import asyncio

logger = logging.getLogger(__name__)

# Form type constants
FORM_TYPE_LINKEDIN = "linkedin"
FORM_TYPE_INDEED = "indeed"
FORM_TYPE_GREENHOUSE = "greenhouse" 
FORM_TYPE_LEVER = "lever"
FORM_TYPE_WORKDAY = "workday"
FORM_TYPE_JOBVITE = "jobvite"
FORM_TYPE_TALEO = "taleo"
FORM_TYPE_SMARTRECRUITERS = "smartrecruiters"
FORM_TYPE_UNKNOWN = "unknown"

# Button and link text patterns for various actions
APPLY_BUTTON_PATTERNS = [
    r'(?i)^apply$', 
    r'(?i)^apply now$',
    r'(?i)^easy apply$',
    r'(?i)^submit application$',
    r'(?i)^submit$',
    r'(?i)^continue$',
    r'(?i)^next$',
    r'(?i)^begin application$',
    r'(?i)^start application$',
    r'(?i)^i agree$'
]

SKIP_BUTTON_PATTERNS = [
    r'(?i)^skip$',
    r'(?i)^skip this step$',
    r'(?i)^skip for now$',
    r'(?i)^i\'ll do this later$',
    r'(?i)^not now$'
]

SUBMIT_BUTTON_PATTERNS = [
    r'(?i)^submit$',
    r'(?i)^submit application$',
    r'(?i)^send$',
    r'(?i)^send application$',
    r'(?i)^finish$',
    r'(?i)^complete$',
    r'(?i)^complete application$'
]

async def detect_form_type(page: Page) -> str:
    """
    Detect the type of application form/system being used
    
    Args:
        page: The playwright page object
        
    Returns:
        The detected form type as a string
    """
    url = page.url
    
    # Check URL patterns first
    if 'linkedin.com' in url:
        return FORM_TYPE_LINKEDIN
    elif 'indeed.com' in url:
        return FORM_TYPE_INDEED
    elif 'greenhouse.io' in url:
        return FORM_TYPE_GREENHOUSE
    elif 'lever.co' in url:
        return FORM_TYPE_LEVER
    elif 'myworkdayjobs.com' in url or 'myworkday.com' in url:
        return FORM_TYPE_WORKDAY
    elif 'jobvite.com' in url:
        return FORM_TYPE_JOBVITE
    elif 'taleo.net' in url:
        return FORM_TYPE_TALEO
    elif 'smartrecruiters.com' in url:
        return FORM_TYPE_SMARTRECRUITERS
        
    # If URL doesn't give it away, check page content
    content = await page.content()
    content = content.lower()
    
    if 'powered by greenhouse' in content or 'greenhouse job board' in content:
        return FORM_TYPE_GREENHOUSE
    elif 'powered by lever' in content or 'jobs by lever' in content:
        return FORM_TYPE_LEVER
    elif 'powered by jobvite' in content:
        return FORM_TYPE_JOBVITE
    elif 'powered by workday' in content or 'workday' in content:
        return FORM_TYPE_WORKDAY
    elif 'taleo' in content:
        return FORM_TYPE_TALEO
    elif 'linkedin' in content and 'easy apply' in content:
        return FORM_TYPE_LINKEDIN
    elif 'smartrecruiters' in content:
        return FORM_TYPE_SMARTRECRUITERS
    elif 'indeed' in content and 'apply now' in content:
        return FORM_TYPE_INDEED
        
    # Check for specific elements
    try:
        if await page.locator('div[data-test="easy-apply-button"]').count() > 0:
            return FORM_TYPE_LINKEDIN
        if await page.locator('button[data-testid="indeedApplyButton"]').count() > 0:
            return FORM_TYPE_INDEED
    except Exception:
        # Ignore element check errors
        pass
        
    return FORM_TYPE_UNKNOWN

async def find_apply_button(page: Page) -> Optional[ElementHandle]:
    """
    Find the apply button on a job posting
    
    Args:
        page: The playwright page object
        
    Returns:
        The apply button element if found, None otherwise
    """
    # First check for specific button selectors by ATS type
    form_type = await detect_form_type(page)
    
    if form_type == FORM_TYPE_LINKEDIN:
        # LinkedIn specific apply buttons
        try:
            # Try for the primary Easy Apply button
            easy_apply_btn = await page.wait_for_selector(
                'div[data-test="easy-apply-button"], button:has-text("Easy Apply")', 
                timeout=2000
            )
            if easy_apply_btn:
                return easy_apply_btn
        except Exception:
            pass
    
    elif form_type == FORM_TYPE_INDEED:
        # Indeed specific apply buttons
        try:
            indeed_btn = await page.wait_for_selector(
                'button[data-testid="indeedApplyButton"], ' + 
                'button.jobsearch-IndeedApplyButton-newDesign',
                timeout=2000
            )
            if indeed_btn:
                return indeed_btn
        except Exception:
            pass
    
    # Generic apply button finders for all ATS systems
    button_selectors = [
        'button:has-text("Apply")',
        'button:has-text("Apply Now")',
        'button:has-text("Easy Apply")',
        'button:has-text("Submit Application")',
        'a:has-text("Apply")',
        'a:has-text("Apply Now")',
        'a.button:has-text("Apply")',
        'div.apply-button',
        'div[role="button"]:has-text("Apply")'
    ]
    
    # Try each selector
    for selector in button_selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=2000)
            if element:
                return element
        except Exception:
            # Try next selector if this one fails
            continue
    
    # If we still haven't found a button, look for any button or link containing apply text
    all_buttons = await page.query_selector_all('button, a.button, a[role="button"], div[role="button"]')
    
    for btn in all_buttons:
        try:
            text = await btn.inner_text()
            # Check for common apply button text patterns
            for pattern in APPLY_BUTTON_PATTERNS:
                if re.search(pattern, text):
                    return btn
        except Exception:
            continue
    
    return None

async def find_next_button(page: Page) -> Optional[ElementHandle]:
    """
    Find the next/continue button in a multi-step application form
    
    Args:
        page: The playwright page object
        
    Returns:
        The next/continue button element if found, None otherwise
    """
    # Common next/continue button selectors
    next_button_selectors = [
        'button:has-text("Next")', 
        'button:has-text("Continue")',
        'button.next-button',
        'button.continue-button',
        'button[data-test="continue-button"]',
        'button[data-control-name="continue_unify"]',
        'button:has-text("Save and Continue")'
    ]
    
    # Try each selector
    for selector in next_button_selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=2000)
            if element:
                return element
        except Exception:
            # Try next selector
            continue
    
    # If we haven't found a button yet, look for any button with next/continue text
    all_buttons = await page.query_selector_all('button')
    
    for btn in all_buttons:
        try:
            text = await btn.inner_text()
            if re.search(r'(?i)next|continue|proceed|save', text):
                return btn
        except Exception:
            continue
            
    return None

async def find_submit_button(page: Page) -> Optional[ElementHandle]:
    """
    Find the final submit button in an application form
    
    Args:
        page: The playwright page object
        
    Returns:
        The submit button element if found, None otherwise
    """
    submit_selectors = [
        'button:has-text("Submit")',
        'button:has-text("Submit Application")',
        'button:has-text("Send")',
        'button:has-text("Send Application")',
        'button:has-text("Complete")',
        'button:has-text("Complete Application")',
        'button[type="submit"]'
    ]
    
    # Try each selector
    for selector in submit_selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=2000)
            if element:
                return element
        except Exception:
            # Try next selector
            continue
    
    # If we haven't found a submit button, check all buttons
    all_buttons = await page.query_selector_all('button')
    
    for btn in all_buttons:
        try:
            text = await btn.inner_text()
            for pattern in SUBMIT_BUTTON_PATTERNS:
                if re.search(pattern, text):
                    return btn
        except Exception:
            continue
            
    return None

async def find_and_click_submit_button(page: Page) -> bool:
    """
    Find and click the submit button on the page.
    
    Args:
        page: The playwright page object
        
    Returns:
        Boolean indicating whether the submit button was found and clicked.
    """
    logger.info("Looking for submit button")
    
    # First check for any validation errors before submission
    validation_errors = await check_form_validation_errors(page)
    if validation_errors > 0:
        logger.warning(f"Found {validation_errors} validation errors before submission. Not submitting.")
        return False
    
    # Make sure all required fields are filled before trying to submit
    empty_required_fields = await page.query_selector_all('input:required:invalid, select:required:invalid, textarea:required:invalid')
    if empty_required_fields:
        logger.warning(f"Found {len(empty_required_fields)} empty required fields. Not submitting.")
        return False
    
    # Wait a moment before submission to ensure all async validations complete
    logger.info("Waiting before submission to ensure form is ready...")
    await asyncio.sleep(3)
    
    # Try to find the submit button
    submit_button = await find_submit_button(page)
    
    if submit_button:
        logger.info("Submit button found, checking if it's enabled...")
        # Check if button is enabled
        is_disabled = await submit_button.get_attribute('disabled')
        if is_disabled:
            logger.warning("Submit button is disabled. Form may be incomplete.")
            return False
            
        logger.info("Submit button is enabled, clicking...")
        try:
            # Click the submit button
            await submit_button.click()
            await page.wait_for_load_state("networkidle", timeout=5000)
            logger.info("Submit button clicked successfully")
            return True
        except Exception as e:
            logger.error(f"Error clicking submit button: {str(e)}")
            return False
    else:
        logger.warning("No submit button found")
        return False

async def check_form_validation_errors(page: Page) -> int:
    """
    Check for form validation errors or missing required fields
    
    Args:
        page: The playwright page object
        
    Returns:
        Number of validation errors found
    """
    # Common selectors for validation errors
    error_selectors = [
        '.error',
        '.invalid-feedback',
        '[aria-invalid="true"]',
        '.form-error',
        '.validation-error',
        '.error-message',
        'input:invalid',
        'select:invalid',
        'textarea:invalid'
    ]
    
    error_count = 0
    for selector in error_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                is_visible = await element.is_visible()
                if is_visible:
                    error_count += 1
                    try:
                        error_text = await element.inner_text()
                        logger.warning(f"Validation error: {error_text}")
                    except:
                        pass
        except Exception:
            pass
            
    return error_count

async def detect_and_handle_form_type(page: Page) -> Tuple[str, Dict[str, Any]]:
    """
    Detect the form type and return appropriate handling strategy.
    
    Args:
        page: The playwright page object
        
    Returns:
        Tuple containing form type string and additional metadata.
    """
    form_type = await detect_form_type(page)
    
    # Initialize form metadata
    form_metadata = {
        "form_type": form_type,
        "detected_fields": [],
        "special_handling_required": False,
        "is_multi_step": False
    }
    
    # Set form-specific handling information
    if form_type == FORM_TYPE_LINKEDIN:
        form_metadata["special_handling_required"] = True
        form_metadata["is_multi_step"] = True
        logger.info("LinkedIn form detected - special handling enabled")
    elif form_type == FORM_TYPE_INDEED:
        form_metadata["special_handling_required"] = True
        form_metadata["is_multi_step"] = True
        logger.info("Indeed form detected - special handling enabled")
    elif form_type == FORM_TYPE_GREENHOUSE:
        form_metadata["is_multi_step"] = False
        logger.info("Greenhouse form detected")
    elif form_type == FORM_TYPE_LEVER:
        form_metadata["is_multi_step"] = False
        logger.info("Lever form detected")
    elif form_type == FORM_TYPE_WORKDAY:
        form_metadata["special_handling_required"] = True
        form_metadata["is_multi_step"] = True
        logger.info("Workday form detected - special handling enabled")
    else:
        logger.info(f"Generic form handling for type: {form_type}")
    
    return form_type, form_metadata