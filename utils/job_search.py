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

def search_jobs_api(job_title: str, location: str) -> List[Dict[str, Any]]:
    """
    Search for jobs using a public jobs API (Jsearch API from RapidAPI)
    
    Args:
        job_title: The job title to search for
        location: The location to search in
    
    Returns:
        List of job dictionaries containing job details
    """
    # Get API key and log what we found (for debugging)
    api_key = os.environ.get('RAPID_API_KEY', '')
    
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
        url = "https://jsearch.p.rapidapi.com/search"
        
        querystring = {
            "query": f"{job_title} in {location}",
            "page": "1",
            "num_pages": "1"
        }
        
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        response = requests.get(url, headers=headers, params=querystring)
        
        if response.status_code == 200:
            data = response.json()
            api_jobs = []
            
            # Parse API response
            for job_data in data.get('data', []):
                job = {
                    'id': job_data.get('job_id', f"jsearch-{len(api_jobs) + 1}"),
                    'title': job_data.get('job_title', ''),
                    'company': job_data.get('employer_name', ''),
                    'location': job_data.get('job_city', '') + ', ' + job_data.get('job_state', ''),
                    'job_type': job_data.get('job_employment_type', ''),
                    'description_snippet': job_data.get('job_description', '')[:150] + '...',
                    'url': job_data.get('job_apply_link', ''),
                    'source': 'JSearch API',
                    'date_generated': job_data.get('job_posted_at_datetime_utc', '')
                }
                
                # Only add if we have the essential fields
                if job['title'] and job['company'] and job['url']:
                    api_jobs.append(job)
            
            if api_jobs:
                logger.info(f"Found {len(api_jobs)} jobs via API")
                return api_jobs
                
        # If we get here, the API didn't return useful results, fall back to mock data
        logger.warning("API returned no usable results. Using mock data.")
        return search_jobs_mock(job_title, location)
        
    except Exception as e:
        logger.error(f"Error in API job search: {str(e)}")
        return search_jobs_mock(job_title, location)

def search_jobs(job_title: str, location: str) -> List[Dict[str, Any]]:
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
    try:
        jobs = search_jobs_api(job_title, location)
        if jobs:
            return jobs
    except Exception as e:
        logger.error(f"API search failed: {str(e)}")
    
    # If API search fails, use mock data as fallback
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
