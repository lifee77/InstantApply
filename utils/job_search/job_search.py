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

def search_jobs_mock(
    query: str, 
    location: str = "remote",
    page: int = 1, 
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Return mock job search results for testing
    """
    base_jobs = [
        {
            "id": "job1234",
            "title": "Senior Software Engineer",
            "company": "Tech Innovators Inc.",
            "location": "Remote",
            "salary": "$120,000 - $150,000",
            "description": "Senior Software Engineer position with focus on AI and machine learning applications.",
            "url": "https://example.com/job1234",
            "date_posted": "2023-05-15"
        },
        {
            "id": "job5678",
            "title": "Frontend Developer",
            "company": "Web Solutions Ltd",
            "location": "New York, NY",
            "salary": "$90,000 - $110,000",
            "description": "Frontend developer with React expertise needed for our growing team.",
            "url": "https://example.com/job5678",
            "date_posted": "2023-05-16"
        },
        {
            "id": "job9012",
            "title": "Data Scientist",
            "company": "Data Insights Corp",
            "location": "Remote",
            "salary": "$115,000 - $135,000",
            "description": "Data scientist position focused on building predictive models and analytics.",
            "url": "https://example.com/job9012",
            "date_posted": "2023-05-14"
        },
        {
            "id": "job3456",
            "title": "DevOps Engineer",
            "company": "Cloud Systems Inc.",
            "location": "Austin, TX",
            "salary": "$100,000 - $130,000",
            "description": "DevOps engineer needed for maintaining and improving our cloud infrastructure.",
            "url": "https://example.com/job3456",
            "date_posted": "2023-05-17"
        },
        {
            "id": "job7890",
            "title": "Product Manager",
            "company": "Innovation Products",
            "location": "San Francisco, CA",
            "salary": "$130,000 - $160,000",
            "description": "Product manager for our flagship software solution. Lead product development from conception to launch.",
            "url": "https://example.com/job7890",
            "date_posted": "2023-05-13"
        },
    ]
    
    # Customize based on query and location
    filtered_jobs = []
    for job in base_jobs:
        # Simple filtering logic - just for demo purposes
        if (
            query.lower() in job["title"].lower() or 
            query.lower() in job["description"].lower() or
            location.lower() == "remote" or 
            location.lower() in job["location"].lower()
        ):
            filtered_jobs.append(job)
    
    # Apply pagination
    start = (page - 1) * limit
    end = start + limit
    paginated_jobs = filtered_jobs[start:end]
    
    return paginated_jobs

def search_jobs(
    query: str, 
    location: str = "remote", 
    page: int = 1,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search jobs using Indeed API or web scraping
    
    Args:
        query: The job search query
        location: Job location (city, state, or "remote")
        page: Page number for pagination
        limit: Maximum number of results to return
        
    Returns:
        List of job dictionaries
    """
    try:
        logger.info(f"Searching for jobs with query: '{query}', location: '{location}', page: {page}")
        
        # For now, just return mock data
        return search_jobs_mock(query, location, page, limit)
        
    except Exception as e:
        logger.error(f"Error searching jobs: {str(e)}")
        return []

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
