"""
Common utility functions for application filler
"""
import os
import re
import time
import logging
from urllib.parse import urlparse
from typing import Tuple, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)

def valid_url(url: str) -> bool:
    """
    Check if a URL is valid
    
    Args:
        url: URL to validate
        
    Returns:
        True if the URL appears valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
        
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"Error validating URL {url}: {str(e)}")
        return False

def extract_job_id(url: str) -> str:
    """
    Extract job ID from URL
    
    Args:
        url: Job posting URL
    
    Returns:
        Job ID if found, empty string otherwise
    """
    if not url:
        return ""
    
    # Extract LinkedIn job ID
    linkedin_match = re.search(r'linkedin\.com/jobs/view/(\d+)', url)
    if linkedin_match:
        return linkedin_match.group(1)
    
    # Extract Indeed job ID
    indeed_match = re.search(r'jk=([a-zA-Z0-9]+)', url)
    if indeed_match:
        return indeed_match.group(1)
        
    # Extract Lever job ID
    lever_match = re.search(r'lever\.co/[^/]+/([a-zA-Z0-9-]+)', url)
    if lever_match:
        return lever_match.group(1)
        
    # Extract Greenhouse job ID
    greenhouse_match = re.search(r'greenhouse\.io/[^/]+/jobs/(\d+)', url)
    if greenhouse_match:
        return greenhouse_match.group(1)
    
    # Extract from path if no specific pattern matches
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    # Try to find a numeric ID or a slug that could be a job ID
    for part in path_parts:
        if part and (part.isdigit() or '-' in part):
            return part
            
    # Fallback
    return ""

async def save_full_page_screenshot(page: Page, name_prefix: str) -> Tuple[str, Optional[str]]:
    """
    Save a full page screenshot and HTML for debugging
    
    Args:
        page: The Playwright page object
        name_prefix: Prefix for the screenshot filename
        
    Returns:
        Tuple with paths to screenshot and HTML files
    """
    timestamp = int(time.time())
    screenshot_path = f"/tmp/{name_prefix}_{timestamp}.png"
    html_path = f"/tmp/{name_prefix}_{timestamp}.html"
    
    try:
        # Take full page screenshot
        await page.screenshot(path=screenshot_path, full_page=True)
        logger.debug(f"Saved screenshot to {screenshot_path}")
        
        # Save HTML content
        html_content = await page.content()
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.debug(f"Saved HTML to {html_path}")
        
        return screenshot_path, html_path
    except Exception as e:
        logger.error(f"Error saving screenshot/HTML: {str(e)}")
        return screenshot_path, None