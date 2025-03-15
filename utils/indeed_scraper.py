import asyncio
import logging
import time
import random
import json
import os
import requests
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from flask import current_app

logger = logging.getLogger(__name__)

# List of user agents to rotate through
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

async def search_jobs_async(job_title: str, location: str) -> List[Dict[str, Any]]:
    """
    Search for jobs on Indeed based on job title and location using Playwright
    with enhanced stealth features
    
    Args:
        job_title: The job title to search for
        location: The location to search in
    
    Returns:
        List of job dictionaries containing job details
    """
    jobs = []
    
    # Format the search query
    search_url = f"https://www.indeed.com/jobs?q={job_title.replace(' ', '+')}&l={location.replace(' ', '+')}"
    
    async with async_playwright() as p:
        try:
            # Use a random user agent
            user_agent = random.choice(USER_AGENTS)
            
            # Browser configuration for better stealth
            # IMPORTANT: Set headless=False for debugging, True for production
            browser = await p.chromium.launch(
                headless=False,  # Try with headless=False first to debug
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
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
            
            # Page setup with stealth mode
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
            
            # Random delay before navigating (0.5-1.5 seconds)
            await page.wait_for_timeout(500 + random.randint(0, 1000))
            
            logger.info(f"Navigating to {search_url}")
            await page.goto(search_url, wait_until='domcontentloaded')
            
            # Wait for a random period (2-4 seconds)
            await page.wait_for_timeout(2000 + random.randint(0, 2000))
            
            # Try to find the job cards with different selectors
            selectors = ["div.job_seen_beacon", "div.jobsearch-ResultsList div[data-testid='job-card']", "div.tapItem"]
            job_cards = []
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    job_cards = await page.query_selector_all(selector)
                    if job_cards:
                        logger.info(f"Found {len(job_cards)} jobs using selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not job_cards:
                logger.warning("No job cards found with any selector")
                logger.info("Current page content:")
                content = await page.content()
                logger.info(content[:500] + "..." if len(content) > 500 else content)
                
                # Take screenshot for debugging
                debug_dir = os.path.join(os.path.dirname(__file__), '../debug')
                os.makedirs(debug_dir, exist_ok=True)
                screenshot_path = os.path.join(debug_dir, 'indeed_debug.png')
                await page.screenshot(path=screenshot_path)
                logger.info(f"Debug screenshot saved to {screenshot_path}")
                
                raise Exception("No job cards found with any selector")
            
            # Human-like scrolling
            for i in range(10):
                # Scroll progressively
                await page.evaluate(f"window.scrollBy(0, {200 + random.randint(100, 300)})")
                # Random delay between scrolls (100-300ms)
                await page.wait_for_timeout(100 + random.randint(0, 200))
            
            # Process job cards
            count = 0
            for card in job_cards:
                job = {}
                
                try:
                    # Try different selectors for job title
                    title_selectors = ['h2.jobTitle', 'h2[data-testid="jobTitle"]', 'a.jcs-JobTitle']
                    for selector in title_selectors:
                        title_element = await card.query_selector(selector)
                        if title_element:
                            job['title'] = await title_element.inner_text()
                            break
                    
                    # Company name
                    company_selectors = ['span.companyName', '[data-testid="company-name"]', '.company']
                    for selector in company_selectors:
                        company_element = await card.query_selector(selector)
                        if company_element:
                            job['company'] = await company_element.inner_text()
                            break
                    
                    # Location
                    location_selectors = ['div.companyLocation', '[data-testid="text-location"]', '.location']
                    for selector in location_selectors:
                        location_element = await card.query_selector(selector)
                        if location_element:
                            job['location'] = await location_element.inner_text()
                            break
                    
                    # Description snippet
                    desc_selectors = ['div.job-snippet', '.job-snippet-container', '.summary']
                    for selector in desc_selectors:
                        description_element = await card.query_selector(selector)
                        if description_element:
                            job['description_snippet'] = await description_element.inner_text()
                            break
                    
                    # Job link & ID 
                    link_selectors = ['a.jcs-JobTitle', 'a[data-testid="job-link"]', 'a.jobtitle']
                    for selector in link_selectors:
                        link_element = await card.query_selector(selector) 
                        if link_element:
                            href = await link_element.get_attribute('href')
                            if href:
                                if href.startswith('/'):
                                    job['url'] = f"https://www.indeed.com{href}"
                                else:
                                    job['url'] = href
                                    
                                # Extract job ID from URL
                                if 'jk=' in href:
                                    job['id'] = href.split('jk=')[1].split('&')[0]
                                    break
                except Exception as e:
                    logger.error(f"Error processing job card: {str(e)}")
                    continue
                
                # Only add jobs with all necessary information
                if all(key in job for key in ['title', 'company', 'location', 'url', 'id']):
                    jobs.append(job)
                    count += 1
                    logger.info(f"Found job: {job['title']} at {job['company']}")
                else:
                    missing_keys = [k for k in ['title', 'company', 'location', 'url', 'id'] if k not in job]
                    logger.warning(f"Skipping incomplete job entry. Missing: {', '.join(missing_keys)}")
                
                # Random delay between processing (100-200ms)
                await page.wait_for_timeout(100 + random.randint(0, 100))
                
                # Limit to 10 jobs initially for testing
                if count >= 10:
                    break
            
            await browser.close()
            
        except Exception as e:
            logger.error(f"Error scraping jobs: {str(e)}")
            try:
                if 'browser' in locals() and not browser.is_closed():
                    await browser.close()
            except:
                pass
            
    return jobs

def search_jobs_api(job_title: str, location: str) -> List[Dict[str, Any]]:
    """
    Search for jobs using a public jobs API as a fallback
    
    Args:
        job_title: The job title to search for
        location: The location to search in
    
    Returns:
        List of job dictionaries containing job details
    """
    jobs = []
    
    try:
        # Use Adzuna API for job search (example - replace with your preferred public API)
        # You'll need to register for a free API key at https://developer.adzuna.com/
        app_id = os.environ.get('ADZUNA_APP_ID', '')
        app_key = os.environ.get('ADZUNA_APP_KEY', '')
        
        # If API keys are not set, use mock data instead
        if not app_id or not app_key:
            logger.warning("Adzuna API keys not found. Using mock data.")
            return get_mock_job_data(job_title, location)
        
        # Format location for Adzuna API
        country = 'us'  # default to US
        
        # Base URL for Adzuna API
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'results_per_page': 10,
            'what': job_title,
            'where': location,
            'content-type': 'application/json'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract jobs from response
            for result in data.get('results', []):
                job = {
                    'title': result.get('title', ''),
                    'company': result.get('company', {}).get('display_name', 'Unknown'),
                    'location': result.get('location', {}).get('display_name', ''),
                    'description_snippet': result.get('description', '')[:100] + '...',
                    'url': result.get('redirect_url', ''),
                    'id': str(result.get('id', '')),
                    'source': 'Adzuna API'
                }
                
                if all(key in job for key in ['title', 'company', 'location', 'url', 'id']):
                    jobs.append(job)
        else:
            logger.error(f"API request failed with status {response.status_code}")
            # Fall back to mock data
            return get_mock_job_data(job_title, location)
            
    except Exception as e:
        logger.error(f"Error in API job search: {str(e)}")
        # Fall back to mock data
        return get_mock_job_data(job_title, location)
    
    return jobs

def get_mock_job_data(job_title: str, location: str) -> List[Dict[str, Any]]:
    """Provide mock job data when API fails"""
    logger.info("Using mock job data as fallback")
    
    # Create some fake job listings
    companies = ["TechCorp", "InnoSoft", "CodeMasters", "DevGenius", "ByteWorks"]
    job_types = ["Remote", "Hybrid", "Full-time", "Contract"]
    
    mock_jobs = []
    
    for i in range(1, 6):
        company = random.choice(companies)
        job_type = random.choice(job_types)
        
        mock_job = {
            'title': f"{job_title} - {job_type}",
            'company': f"{company} Inc.",
            'location': location,
            'description_snippet': f"We're looking for an experienced {job_title} to join our team. You'll be working on exciting projects with cutting-edge technology.",
            'url': f"https://example.com/jobs/{i}",
            'id': f"mock-{i}",
            'source': 'Mock Data'
        }
        
        mock_jobs.append(mock_job)
    
    return mock_jobs

def search_jobs(job_title: str, location: str) -> List[Dict[str, Any]]:
    """
    Search for jobs with fallback mechanisms
    
    Args:
        job_title: The job title to search for
        location: The location to search in
    
    Returns:
        List of job dictionaries containing job details
    """
    try:
        logger.info(f"Searching for {job_title} jobs in {location}...")
        
        # Try the enhanced scraper first
        try:
            jobs = asyncio.run(search_jobs_async(job_title, location))
            if jobs:
                logger.info(f"Found {len(jobs)} jobs via scraping")
                return jobs
        except Exception as e:
            logger.error(f"Scraper failed: {str(e)}")
        
        # If scraping failed, try the API
        logger.info("Scraper failed. Falling back to API...")
        jobs = search_jobs_api(job_title, location)
        
        if jobs:
            logger.info(f"Found {len(jobs)} jobs via API")
            return jobs
        else:
            logger.error("API search returned no results")
            return []
            
    except Exception as e:
        logger.error(f"All job search methods failed: {str(e)}")
        return []

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    print("Searching for Software Engineer jobs...")
    job_title = "Software Engineer"
    location = "Remote" 
    jobs = search_jobs(job_title, location)
    
    if jobs:
        print(f"Found {len(jobs)} jobs:")
        for i, job in enumerate(jobs, 1):
            print(f"\nJob #{i}:")
            print(f"Title: {job['title']}")
            print(f"Company: {job['company']}")
            print(f"Location: {job['location']}")
            print(f"URL: {job['url']}")
            if 'source' in job:
                print(f"Source: {job['source']}")
    else:
        print("No jobs found or error occurred.")