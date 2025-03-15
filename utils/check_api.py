#!/usr/bin/env python3
import os
import json
import requests
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def test_jsearch_api():
    """Direct test of the JSearch API to debug response format"""
    # Get API key
    api_key = os.environ.get('RAPID_API_KEY', '')
    
    if not api_key:
        logger.error("RAPID_API_KEY not found in environment variables")
        return
        
    logger.info(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # API request parameters
    url = "https://jsearch.p.rapidapi.com/search"
    
    querystring = {
        "query": "Software Engineer in Remote",
        "page": "1",
        "num_pages": "1"
    }
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    try:
        logger.info("Sending API request...")
        response = requests.get(url, headers=headers, params=querystring)
        
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Create debug directory if it doesn't exist
            debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            
            # Save raw response for inspection
            with open(os.path.join(debug_dir, 'raw_api_response.json'), 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Raw API response saved to debug/raw_api_response.json")
            
            # Analyze response structure
            if 'data' in data:
                logger.info(f"Found {len(data['data'])} job listings in the response")
                
                if data['data']:
                    # Examine the first job to understand its structure
                    first_job = data['data'][0]
                    
                    # Get all available keys
                    all_keys = sorted(list(first_job.keys()))
                    logger.info(f"Available job fields: {all_keys}")
                    
                    # Check for location fields specifically
                    location_keys = [k for k in all_keys if 'loc' in k.lower() or 'cit' in k.lower() or 'state' in k.lower()]
                    logger.info(f"Location related fields: {location_keys}")
                    
                    for key in location_keys:
                        logger.info(f"{key}: {first_job.get(key)}")
            else:
                logger.warning("No 'data' key found in the API response")
        else:
            logger.error(f"API request failed. Status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
    except Exception as e:
        logger.error(f"Error testing API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Testing JSearch API...")
    test_jsearch_api()
    logger.info("API test complete")
