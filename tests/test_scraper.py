#!/usr/bin/env python3
import logging
import json
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.job_search.indeed_scraper import search_jobs

def test_scraper():
    """Test the Indeed job scraper with a sample search"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Starting Indeed job scraper test...")
    
    # Test parameters
    job_title = "Software Engineer"
    location = "Remote"
    
    # Run search
    print(f"Searching for {job_title} jobs in {location}...")
    jobs = search_jobs(job_title, location)
    
    if jobs:
        print(f"✅ Success! Found {len(jobs)} jobs")
        
        # Save results to file for inspection
        with open('search_results.json', 'w') as f:
            json.dump(jobs, f, indent=2)
        print(f"Results saved to search_results.json")
        
        # Print first job details
        print("\nSample job details:")
        job = jobs[0]
        for key, value in job.items():
            if key in ['title', 'company', 'location', 'id']:
                print(f"{key}: {value}")
    else:
        print("❌ No jobs found or an error occurred.")
        
if __name__ == "__main__":
    test_scraper()
