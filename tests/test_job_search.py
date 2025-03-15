#!/usr/bin/env python3
import sys
import os
import logging
import json
import time
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Add project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.job_search.job_search import search_jobs, search_jobs_mock

def run_test():
    """Test job search functionality"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Print environment check
    api_key = os.environ.get('RAPID_API_KEY', '')
    if api_key:
        logger.info(f"RAPID_API_KEY is set: {api_key[:4]}...{api_key[-4:]} ({len(api_key)} characters)")
    else:
        logger.warning("RAPID_API_KEY is not set in environment")
    
    # Test case 1: Mock data
    logger.info("TEST 1: Using mock data")
    mock_jobs = search_jobs_mock("Software Engineer", "Remote")
    logger.info(f"Found {len(mock_jobs)} mock jobs")
    
    # Show sample job details
    if mock_jobs:
        job = mock_jobs[0]
        print("\nSample mock job:")
        for key in ['title', 'company', 'location', 'job_type', 'salary']:
            print(f"  {key}: {job.get(key, 'N/A')}")
        print(f"  description: {job.get('description_snippet', 'N/A')}")
    
    # Test case 2: Real search
    logger.info("\nTEST 2: Running actual search with API")
    start_time = time.time()
    jobs = search_jobs("Software Developer", "Remote")
    end_time = time.time()
    
    logger.info(f"Search completed in {end_time - start_time:.2f} seconds")
    logger.info(f"Found {len(jobs)} jobs")
    
    # Show sample job details
    if jobs:
        # Save results to file for inspection
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        
        with open(os.path.join(debug_dir, 'search_results.json'), 'w') as f:
            json.dump(jobs, f, indent=2)
        
        print("\nSaved results to debug/search_results.json")
        
        # Print first job details
        job = jobs[0]
        print("\nSample job from search:")
        for key in ['title', 'company', 'location', 'source']:
            print(f"  {key}: {job.get(key, 'N/A')}")
        print(f"  description: {job.get('description_snippet', 'N/A')}")
        print(f"  url: {job.get('url', 'N/A')}")
    
    logger.info("\nTests completed successfully")

if __name__ == "__main__":
    run_test()
