#!/usr/bin/env python3
import logging
import random
import os
import json
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

def search_jobs_mock(job_title: str, location: str) -> List[Dict[str, Any]]:
    """
    Generate mock job listings for testing and fallback
    
    Args:
        job_title: The job title to search for
        location: The location to search in
    
    Returns:
        List of job dictionaries containing job details
    """
    logger.info(f"Generating mock data for: {job_title} in {location}")
    
    # Common companies and their details
    companies = [
        {"name": "Google", "rating": 4.5, "reviews": 12000},
        {"name": "Microsoft", "rating": 4.3, "reviews": 9800},
        {"name": "Amazon", "rating": 3.9, "reviews": 15300},
        {"name": "Apple", "rating": 4.4, "reviews": 11200},
        {"name": "Meta", "rating": 4.1, "reviews": 7600},
        {"name": "Netflix", "rating": 4.2, "reviews": 3200},
        {"name": "Uber", "rating": 3.7, "reviews": 5100},
        {"name": "Airbnb", "rating": 4.0, "reviews": 2800},
        {"name": "Twitter", "rating": 3.8, "reviews": 2100},
        {"name": "LinkedIn", "rating": 4.2, "reviews": 4700},
        {"name": "Salesforce", "rating": 4.3, "reviews": 6300},
        {"name": "Adobe", "rating": 4.1, "reviews": 5800},
        {"name": "IBM", "rating": 3.9, "reviews": 14200},
        {"name": "Oracle", "rating": 3.7, "reviews": 9400},
        {"name": "Intel", "rating": 4.0, "reviews": 8700}
    ]
    
    # Job types and requirements
    job_types = ["Full-time", "Part-time", "Contract", "Temporary", "Remote", "Hybrid"]
    experience_levels = ["Entry Level", "Mid-Level", "Senior", "Lead", "Manager", "Director"]
    
    salary_ranges = [
        "$60,000 - $80,000",
        "$80,000 - $100,000",
        "$100,000 - $120,000",
        "$120,000 - $150,000",
        "$150,000 - $180,000",
        "$180,000 - $220,000",
        "$220,000+"
    ]
    
    # Create mock jobs
    mock_jobs = []
    num_jobs = random.randint(10, 20)  # Generate a random number of jobs
    
    for i in range(1, num_jobs + 1):
        company = random.choice(companies)
        job_type = random.choice(job_types)
        experience = random.choice(experience_levels)
        salary = random.choice(salary_ranges)
        
        days_ago = random.randint(0, 14)
        posted = f"{days_ago} day{'s' if days_ago != 1 else ''} ago"
        
        # Build realistic description
        skills = []
        if "Software" in job_title or "Developer" in job_title or "Engineer" in job_title:
            possible_skills = ["Python", "JavaScript", "Java", "C++", "React", "Node.js", 
                               "AWS", "Docker", "Kubernetes", "SQL", "NoSQL", "Git"]
            skills = random.sample(possible_skills, k=random.randint(3, 6))
            
        elif "Data" in job_title:
            possible_skills = ["SQL", "Python", "R", "Tableau", "PowerBI", "Excel", 
                               "Machine Learning", "Statistics", "Hadoop", "Spark"]
            skills = random.sample(possible_skills, k=random.randint(3, 6))
            
        elif "Design" in job_title:
            possible_skills = ["Figma", "Adobe XD", "Sketch", "Photoshop", "Illustrator", 
                               "UI/UX", "Wireframing", "Prototyping"]
            skills = random.sample(possible_skills, k=random.randint(3, 6))
        
        else:
            possible_skills = ["Communication", "Project Management", "Problem Solving", 
                               "Teamwork", "Microsoft Office", "Leadership", "Analysis"]
            skills = random.sample(possible_skills, k=random.randint(3, 6))
        
        # Create description
        description = f"{experience} {job_title} position. {job_type}. "
        description += f"Looking for candidates with experience in {', '.join(skills[:-1])} and {skills[-1]}. "
        description += f"Competitive salary: {salary}. Join our team at {company['name']}!"
        
        # Create job entry
        job = {
            'id': f"mock-{i}",
            'title': f"{experience} {job_title}",
            'company': company['name'],
            'company_rating': company['rating'],
            'company_reviews': company['reviews'],
            'location': location if location != "Remote" else "Remote",
            'job_type': job_type,
            'salary': salary,
            'description_snippet': description[:150] + "...",
            'full_description': description,
            'posted': posted,
            'url': f"https://example.com/jobs/{i}",
            'requirements': skills,
            'source': 'Mock Data',
            'date_generated': '2023-03-14'
        }
        
        mock_jobs.append(job)
    
    return mock_jobs

def search_jobs_api(job_title: str, location: str, page: int = 1) -> List[Dict[str, Any]]:   
    """
    Search for jobs using a public jobs API (active-jobs-db API from RapidAPI)
    
    Args:
        job_title: The job title to search for
        location: The location to search in
        page: Page number for pagination
    
    Returns:
        List of job dictionaries containing job details
    """
    # Force reload environment variables from .env file to avoid cached values
    load_dotenv(override=True)
    
    # Get API key and log what we found (for debugging)
    api_key = os.environ.get('RAPID_API_KEY', '')
    api_host = os.environ.get('RAPID_API_HOST', 'active-jobs-db.p.rapidapi.com')
    
    if api_key:
        logger.info(f"Found RAPID_API_KEY: {api_key[:5]}...{api_key[-5:]} ({len(api_key)} chars)")
    else:
        logger.warning("RAPID_API_KEY not found in environment variables")
    
    # If API key is not set, fall back to mock data
    if not api_key:
        logger.warning("RapidAPI key not found. Using mock data.")
        return search_jobs_mock(job_title, location)
    
    try:
        logger.info(f"Searching for jobs via API: {job_title} in {location}")
        
        # Set the correct endpoint based on the API host
        if api_host == 'active-jobs-db.p.rapidapi.com':
            # Use the known working endpoint for the active-jobs-db API
            endpoint = "/active-ats-7d"
            url = f"https://{api_host}{endpoint}"
            
            # Prepare query parameters for active-jobs-db API
            querystring = {
                "query": f"{job_title} {location}",
                "page": str(page),
                "per_page": "20"
            }
        else:
            # Original jsearch API
            url = f"https://{api_host}/search"
            querystring = {
                "query": f"{job_title} in {location}",
                "page": str(page),
                "num_pages": "1"
            }
        
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": api_host
        }
        
        logger.info(f"Making API request to: {url}")
        
        # Add exponential backoff retry logic for rate limit issues
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            response = requests.get(url, headers=headers, params=querystring, timeout=10)
            
            if response.status_code == 200:
                break
            elif response.status_code == 429:  # Rate limit exceeded
                logger.warning(f"API rate limit exceeded (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {sleep_time} seconds before retrying...")
                    import time
                    time.sleep(sleep_time)
            else:
                logger.warning(f"API returned error status code: {response.status_code}")
                break
        
        if response.status_code == 200:
            data = response.json()
            api_jobs = []
            
            # Save raw response for debugging
            debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            with open(os.path.join(debug_dir, 'api_response.json'), 'w') as f:
                json.dump(data, f, indent=2)
            
            # Parse API response based on the API format
            if api_host == 'active-jobs-db.p.rapidapi.com':
                # New active-jobs-db API format
                # Check if data is a list (direct jobs list) or has a specific structure
                job_list = data if isinstance(data, list) else data.get('data', [])
                
                for job_data in job_list:
                    # Extract location information
                    location_parts = []
                    if job_data.get('cities_derived'):
                        location_parts.append(job_data['cities_derived'][0] if isinstance(job_data['cities_derived'], list) and job_data['cities_derived'] else None)
                    if job_data.get('regions_derived'):
                        location_parts.append(job_data['regions_derived'][0] if isinstance(job_data['regions_derived'], list) and job_data['regions_derived'] else None)
                    if job_data.get('countries_derived'):
                        location_parts.append(job_data['countries_derived'][0] if isinstance(job_data['countries_derived'], list) and job_data['countries_derived'] else None)
                    
                    location_str = ", ".join(filter(None, location_parts)) or location or "Unknown"
                    
                    # Format the job description
                    desc_snippet = f"Position at {job_data.get('organization', '')} in {location_str}"
                    if job_data.get('employment_type'):
                        emp_type = job_data.get('employment_type')
                        if isinstance(emp_type, list) and emp_type:
                            desc_snippet += f". Employment type: {emp_type[0]}"
                    
                    job = {
                        'id': job_data.get('id', f"rapidapi-{len(api_jobs) + 1}"),
                        'title': job_data.get('title', ''),
                        'company': job_data.get('organization', ''),
                        'location': location_str,
                        'job_type': job_data.get('employment_type', [''])[0] if isinstance(job_data.get('employment_type', ''), list) else job_data.get('employment_type', ''),
                        'description_snippet': desc_snippet,
                        'url': job_data.get('url', ''),
                        'source': 'Active Jobs DB API',
                        'date_generated': job_data.get('date_posted', '')
                    }
                    
                    # Only add if we have the essential fields
                    if job['title'] and job['company'] and job['url']:
                        api_jobs.append(job)
            else:
                # Original jsearch API format
                for job_data in data.get('data', []):
                    # Get location fields, ensuring they're strings
                    job_city = job_data.get('job_city') or ''
                    job_state = job_data.get('job_state') or ''
                    
                    # Create a properly formatted location string
                    location_str = ''
                    if job_city:
                        location_str = job_city
                    if job_state:
                        if location_str:
                            location_str += f", {job_state}"
                        else:
                            location_str = job_state
                    
                    # If we still don't have location, use a default or the input location
                    if not location_str:
                        location_str = location if location else "Unknown"
                    
                    # Format the job description for the snippet
                    job_description = job_data.get('job_description', '')
                    if job_description:
                        desc_snippet = job_description[:150] + '...'
                    else:
                        desc_snippet = "No description available"
                    
                    job = {
                        'id': job_data.get('job_id', f"jsearch-{len(api_jobs) + 1}"),
                        'title': job_data.get('job_title', ''),
                        'company': job_data.get('employer_name', ''),
                        'location': location_str,
                        'job_type': job_data.get('job_employment_type', ''),
                        'description_snippet': desc_snippet,
                        'url': job_data.get('job_apply_link', ''),
                        'source': 'JSearch API',
                        'date_generated': job_data.get('job_posted_at_datetime_utc', '')
                    }
                    
                    # Only add if we have the essential fields
                    if job['title'] and job['company'] and job['url']:
                        api_jobs.append(job)
        
            if api_jobs:
                logger.info(f"Found {len(api_jobs)} jobs via API")
                for job in api_jobs[:3]:  # Log just the first 3 jobs to avoid too much output
                    logger.info(f"Job: {job['title']} at {job['company']} ({job['location']})")
                return api_jobs
            else:
                logger.warning("API returned data but no valid jobs were found")
                
        # If we get here, the API didn't return useful results, fall back to mock data
        return search_jobs_mock(job_title, location)
        
    except Exception as e:
        logger.error(f"Error in API job search: {str(e)}")
        # Log detailed exception for debugging
        import traceback
        logger.error(traceback.format_exc())
        return search_jobs_mock(job_title, location)



def search_jobs(job_title: str, location: str, page: int = 1) -> List[Dict[str, Any]]:
    """
    Main job search function that tries available methods
    
    Args:
        job_title: The job title to search for
        location: The location to search in
    
    Returns:
        List of job dictionaries containing job details
    """
    logger.info(f"Searching for jobs: {job_title} in {location}")
    
    # Try API search first
    logger.info(f"Searching for jobs: {job_title} in {location} (Page {page})")
    try:
        jobs = search_jobs_api(job_title, location, page)
        if jobs:
            return jobs
    except Exception as e:
        logger.error(f"API search failed: {str(e)}")
    return search_jobs_mock(job_title, location)

def save_test_data():
    """Generate and save test data for development"""
    job_titles = ["Software Engineer", "Data Scientist", "Product Manager", "UX Designer"]
    locations = ["San Francisco, CA", "New York, NY", "Remote", "Seattle, WA"]
    
    all_jobs = {}
    
    for title in job_titles:
        for location in locations:
            key = f"{title.replace(' ', '_')}_{location.replace(' ', '_').replace(',', '')}"
            jobs = search_jobs_mock(title, location)
            all_jobs[key] = jobs
    
    # Save to file
    debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug')
    os.makedirs(debug_dir, exist_ok=True)
    
    with open(os.path.join(debug_dir, 'test_jobs.json'), 'w') as f:
        json.dump(all_jobs, f, indent=2)
    
    print(f"Test data saved to debug/test_jobs.json")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Uncomment to generate test data
    # save_test_data()
    
    # Example usage
    jobs = search_jobs("Software Engineer", "Remote")
    
    print(f"Found {len(jobs)} jobs:")
    for i, job in enumerate(jobs[:5]):  # Print first 5 jobs
        print(f"\nJob #{i+1}:")
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Description: {job['description_snippet']}")
        print(f"URL: {job['url']}")
        print(f"Source: {job['source']}")
