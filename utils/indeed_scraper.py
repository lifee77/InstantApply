import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Any
from flask import current_app

logger = logging.getLogger(__name__)

def search_jobs(job_title: str, location: str) -> List[Dict[str, Any]]:
    """
    Search for jobs on Indeed based on job title and location
    
    Args:
        job_title: The job title to search for
        location: The location to search in
    
    Returns:
        List of job dictionaries containing job details
    """
    jobs = []
    
    try:
        # Format the search query
        search_url = f"https://www.indeed.com/jobs?q={job_title.replace(' ', '+')}&l={location.replace(' ', '+')}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all job cards
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            
            for card in job_cards:
                job = {}
                
                # Extract job title
                title_element = card.find('h2', class_='jobTitle')
                if title_element:
                    job['title'] = title_element.get_text().strip()
                
                # Extract company name
                company_element = card.find('span', class_='companyName')
                if company_element:
                    job['company'] = company_element.get_text().strip()
                
                # Extract location
                location_element = card.find('div', class_='companyLocation')
                if location_element:
                    job['location'] = location_element.get_text().strip()
                
                # Extract job description snippet
                description_element = card.find('div', class_='job-snippet')
                if description_element:
                    job['description_snippet'] = description_element.get_text().strip()
                
                # Extract job link
                link_element = card.find('a', class_='jcs-JobTitle')
                if link_element and 'href' in link_element.attrs:
                    job_path = link_element['href']
                    if job_path.startswith('/'):
                        job['url'] = f"https://www.indeed.com{job_path}"
                        # Extract job ID from URL
                        job['id'] = job_path.split('jk=')[1].split('&')[0] if 'jk=' in job_path else None
                
                # Only add jobs with all necessary information
                if all(key in job for key in ['title', 'company', 'location', 'url', 'id']):
                    jobs.append(job)
                    
                # Respect rate limiting
                time.sleep(current_app.config.get('INDEED_SCRAPE_DELAY', 2))
                
                # Limit to 20 jobs for performance
                if len(jobs) >= 20:
                    break
                    
        else:
            logger.error(f"Failed to retrieve jobs: Status code {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error searching jobs: {str(e)}")
    
    return jobs
