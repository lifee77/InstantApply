#!/usr/bin/env python3
import os
import logging
import json
import time
import sys
import random
import re # Import regex for better text parsing
import csv # Import CSV module
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black, grey, blue # Import blue for links
import requests # Ensure requests is imported

# Add the project root to the Python path when running standalone
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) # Assumes script is in a subdirectory like 'utils'
sys.path.insert(0, project_root)
# print(f"Project Root added to sys.path: {project_root}") # Debug print

# --- Attempt to import User model, provide fallback ---
User = None
try:
    from models.user import User as DBUser # Rename to avoid conflict
    User = DBUser # Use the database user model if import succeeds
    print("Successfully imported User model from models.user")
except ImportError:
    print("Could not import User from models.user. Using fallback class for standalone run.")
    # If running standalone without Flask context, define a simple User class
    class FallbackUser:
        """Simple User class for standalone testing"""
        def __init__(self, name="", email="", skills="", experience="", resume="", desired_job_titles=None, work_mode_preference="", min_salary_hourly=0.0):
            self.id = random.randint(10000, 99999) # Assign a random ID for testing
            self.name = name
            self.email = email
            self.skills = skills
            self.experience = experience
            self.resume = resume
            self.desired_job_titles = desired_job_titles if desired_job_titles else []
            self.work_mode_preference = work_mode_preference
            self.min_salary_hourly = float(min_salary_hourly) if min_salary_hourly else 0.0

        @property
        def is_active(self): return True
        @property
        def is_authenticated(self): return True
        def get_id(self): return str(self.id)

    User = FallbackUser # Use the fallback class

# Load environment variables
dotenv_path = os.path.join(script_dir, '.env')
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(project_root, '.env') # Check project root
load_dotenv(dotenv_path=dotenv_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- API Configurations ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
RAPID_API_KEY = os.environ.get('RAPID_API_KEY', '')

# --- Gemini Setup ---
genai = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai_import
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        genai = genai_import 
        genai.configure(api_key=GEMINI_API_KEY)
        GENERATION_CONFIG = {"temperature": 0.2, "top_p": 0.95, "top_k": 40, "max_output_tokens": 2048}
        SAFETY_SETTINGS = { category: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for category in HarmCategory if category != HarmCategory.HARM_CATEGORY_UNSPECIFIED }
        logger.info("Gemini API configured successfully")
    except ImportError:
        logger.warning("google-generativeai package not installed. Cannot use Gemini.")
        genai = None 
    except Exception as e:
        logger.error(f"Error configuring Gemini: {e}")
        genai = None
else:
    logger.warning("GEMINI_API_KEY not found. Using simple scoring.")

# --- Job Search Functions ---

def parse_salary(salary_text: Optional[str], min_salary: Optional[float], max_salary: Optional[float], salary_period: Optional[str]) -> Optional[float]:
    """Attempts to parse salary info and return an approximate annualized salary."""
    # Try numerical fields first
    salary = None
    if min_salary is not None:
        try: salary = float(min_salary); salary = None if salary <= 0 else salary
        except (ValueError, TypeError): salary = None

    if salary is not None:
        period = str(salary_period).upper() if salary_period else None
        if period == 'HOURLY': return salary * 40 * 52
        elif period == 'WEEKLY': return salary * 52
        elif period == 'MONTHLY': return salary * 12
        elif period == 'YEARLY': return salary
        elif salary > 25000: return salary # Likely annual
        elif salary < 1000: return salary * 40 * 52 # Likely hourly
        else: return None # Ambiguous mid-range without period

    # Fallback: Try parsing from text string
    if isinstance(salary_text, str):
        salary_text_clean = salary_text.replace(',', '').replace('$', '').lower()
        value = None; period_mult = 1
        match = re.search(r'([\d\.]+)\s*(k)?', salary_text_clean)
        if match:
            try:
                value = float(match.group(1))
                if match.group(2) == 'k': value *= 1000
                if value <= 0: value = None
            except ValueError: value = None

        if value is not None:
            if 'hour' in salary_text_clean or 'hr' in salary_text_clean: period_mult = 40 * 52
            elif 'week' in salary_text_clean: period_mult = 52
            elif 'month' in salary_text_clean: period_mult = 12
            elif 'year' in salary_text_clean or 'annum' in salary_text_clean or value > 25000: period_mult = 1
            elif value < 1000 and not any(p in salary_text_clean for p in ['year', 'month', 'week']): period_mult = 40 * 52
            elif 1000 <= value <= 25000 and not any(p in salary_text_clean for p in ['year', 'month', 'week', 'hour']): return None
            return value * period_mult
    return None

def search_jobs_api(job_title: str, location: str, page: int = 1, min_annual_salary: Optional[float] = None) -> List[Dict[str, Any]]:
    """Search Jsearch API, simplifying query and removing problematic params."""
    if not RAPID_API_KEY:
        logger.warning("RAPID_API_KEY not found. Using mock data.")
        return search_jobs_mock(job_title, location)

    try:
        # --- Simplified Query Construction ---
        title_lower = job_title.lower()
        entry_keywords = ["associate", "coordinator", "analyst", "assistant", "intern", "junior", "entry", "fellow", "trainee"]
        # If title implies entry level, search directly. Otherwise, prepend "entry level".
        if any(kw in title_lower for kw in entry_keywords):
             query = f"{job_title} in {location}"
        else:
             query = f"entry level {job_title} in {location}" # Simpler prefix
        
        logger.info(f"Searching API: Page={page}, Query='{query}'")
        url = "https://jsearch.p.rapidapi.com/search"
        
        querystring = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
            "employment_types": "FULLTIME,PARTTIME,CONTRACT,INTERN", 
            # "date_posted": "month", # Optional: uncomment to filter recent jobs
            # REMOVED: "job_requirements": "no_experience_required,under_3_years_experience" 
        }
        # Note: Minimum salary filter via API is also removed for now, as its support/name is unclear.
        # We will filter based on normalized salary later if needed.

        headers = {
            "X-RapidAPI-Key": RAPID_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        response = requests.get(url, headers=headers, params=querystring, timeout=25)
        response.raise_for_status() # Will raise HTTPError for 4xx/5xx

        data = response.json()
        api_jobs = []
        job_count = 0; skipped_exp = 0; skipped_incomplete = 0

        for job_data in data.get('data', []):
            job_count += 1
            title = job_data.get('job_title', ''); company = job_data.get('employer_name', ''); url_link = job_data.get('job_apply_link', '')
            if not title or not company or not url_link: skipped_incomplete += 1; continue 

            job_city = job_data.get('job_city', ''); job_state = job_data.get('job_state', '')
            location_str = f"{job_city}, {job_state}".strip(", ") if job_city or job_state else location

            job_description = job_data.get('job_description', '')
            desc_snippet = (job_description[:200] + '...') if job_description else "No description"
            
            requirements = []
            highlights = job_data.get('job_highlights', {})
            if isinstance(highlights, dict):
                 qualifications = highlights.get('Qualifications'); responsibilities = highlights.get('Responsibilities')
                 if isinstance(qualifications, list): requirements.extend(qualifications)
                 # Optionally extract keywords from responsibilities if needed

            normalized_salary = parse_salary(
                job_data.get('job_salary_info'), job_data.get('job_min_salary'), 
                job_data.get('job_max_salary'), job_data.get('job_salary_period') )
            
            # Experience Filtering (using API fields + text analysis)
            req_exp = job_data.get('job_required_experience', {}); no_exp_req = req_exp.get('no_experience_required', False)
            req_months = req_exp.get('required_experience_in_months'); exp_in_years = req_months / 12 if req_months else 0
            
            title_lower = title.lower(); desc_lower = job_description.lower()
            is_entry_title = any(kw in title_lower for kw in entry_keywords)
            years_match = re.search(r'\b(\d+)\s*(-\s*\d+\s*)?(\+|plus|years?)\b', desc_lower)
            min_years_required = 0; max_years_required = 100 # Assume high if not specified
            if years_match:
                 try: min_years_required = int(years_match.group(1))
                 except ValueError: pass
                 # Try to find max years if range exists, e.g., "1-3 years"
                 range_match = re.search(r'\b\d+\s*-\s*(\d+)\s*years?\b', desc_lower)
                 if range_match:
                      try: max_years_required = int(range_match.group(1))
                      except ValueError: pass
            
            # --- Keep Logic ---
            # Keep if API says no exp OR API says <= 3 years OR (API unknown AND (title implies entry OR text implies 0-3 years))
            # AND text doesn't explicitly require 4+ years unless API confirms <=3 years.
            keep_job = False
            if no_exp_req: keep_job = True
            elif 0 < exp_in_years <= 3: keep_job = True
            elif exp_in_years == 0: # API unknown/0
                 if is_entry_title or (min_years_required <= 3):
                      # Double check text doesn't ask for too much
                      if min_years_required >= 4 or max_years_required >= 4 : 
                           # Text contradicts entry-level target, skip
                           keep_job = False
                           # logger.debug(f"Skipping '{title}' despite entry title/low text years, as text also mentions >=4 years.")
                      else:
                           keep_job = True # Seems ok

            if not keep_job: skipped_exp += 1; continue

            job = {
                'id': job_data.get('job_id', f"jsearch-{random.randint(1000,9999)}"), 'title': title, 'company': company,
                'location': location_str, 'job_type': job_data.get('job_employment_type', ''),
                'description_snippet': desc_snippet, 'full_description': job_description, 'url': url_link,
                'source': 'JSearch API', 'date_generated': job_data.get('job_posted_at_datetime_utc', ''),
                'normalized_salary': normalized_salary,
                'raw_salary_info': {"text": job_data.get('job_salary_info'), "min": job_data.get('job_min_salary'),
                                    "max": job_data.get('job_max_salary'), "period": job_data.get('job_salary_period')},
                'requirements': requirements, 'api_required_months': req_months,
            }
            api_jobs.append(job)
            
        logger.info(f"API Page {page} for '{job_title}': Found {len(api_jobs)} suitable jobs (Processed: {job_count}, Skip Incomplete: {skipped_incomplete}, Skip Exp: {skipped_exp}).")
        return api_jobs
            
    except requests.exceptions.Timeout:
         logger.error(f"API request timed out for page {page}")
         return [] 
    except requests.exceptions.RequestException as e:
        # Log specific 400 errors
        if e.response is not None and e.response.status_code == 400:
             logger.error(f"API returned 400 Bad Request (Page {page}). URL: {e.request.url}. Check API parameters and query structure. Returning empty.")
        else: # Log other network errors
             logger.error(f"Network error during API job search (Page {page}): {str(e)}")
        return [] # Return empty on client errors or network issues now
    except Exception as e:
        logger.error(f"Unexpected error in API job search (Page {page}): {str(e)}")
        import traceback; logger.error(traceback.format_exc())
        return [] # Return empty on unexpected errors


# Mock search function (minimal example, same as before)
def search_jobs_mock(job_title: str, location: str) -> List[Dict[str, Any]]:
    logger.warning(f"FALLBACK: Generating mock data for: {job_title} in {location}")
    mock_jobs = [] 
    for i in range(3): # Generate even fewer mock jobs
        salary = random.choice([None, 55000, 65000, 75000])
        reqs = random.sample(["python", "communication", "analysis", "excel", "teamwork"], k=3)
        job = {
            'id': f"mock-{random.randint(1000,9999)}", 'title': f"Entry Level {job_title}",
            'company': f"MockFirm {chr(65+i)}", 'location': location, 'job_type': "Full-time",
            'description_snippet': "Mock description snippet...", 'full_description': "More detailed mock description.",
            'url': f"https://example.com/mockjob/{i}", 'source': 'Mock Data', 'date_generated': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'normalized_salary': salary, 'raw_salary_info': {"text": f"${salary}/year" if salary else "Competitive"},
            'requirements': reqs, 'api_required_months': random.choice([None, 0, 6, 12]),
        }
        mock_jobs.append(job)
    return mock_jobs


# --- User Profile and Matching Functions (Mostly unchanged) ---

def extract_user_profile(user: User) -> Dict[str, Any]:
    min_salary_hourly_attr = getattr(user, 'min_salary_hourly', 0.0) 
    profile = {
        "name": getattr(user, 'name', 'N/A'), "skills": [],
        "experience_summary": getattr(user, 'experience', ""),
        "resume_text": getattr(user, 'resume', ""), "keywords": [],
        "min_salary_preference": min_salary_hourly_attr * 40 * 52 if min_salary_hourly_attr else 0
    }
    all_skill_texts = [getattr(user, 'skills', "")] 
    unique_skills = set()
    for text in all_skill_texts:
        if not text or not isinstance(text, str): continue
        unique_skills.update(skill.strip().lower() for skill in text.split(",") if skill.strip())
    profile["skills"] = sorted(list(unique_skills))
    if profile["resume_text"]: profile["keywords"] = extract_keywords_from_text(profile["resume_text"])
    logger.info(f"Extracted profile for {profile['name']}: {len(profile['skills'])} skills. Min Salary Pref: ${profile['min_salary_preference']:.0f}/yr")
    return profile

def extract_keywords_from_text(text: str, max_keywords: int = 30) -> List[str]:
    common_words = {"the","and","a","to","of","in","i","is","that","it","with","as","for","was","on","are","be","this","have","an","by","at","not","from","or","my","work","job","jobs","year","years","experience","skills","skill","project","team","development","management","analysis","data","operations","business", "university", "education", "student", "students", "program", "support", "community", "responsibilities", "requirements", "qualifications"}
    words = text.lower(); words = re.sub(r'[^\w\s-]', '', words); words = words.split()
    words = [word for word in words if word and word not in common_words and len(word) > 3 and not word.isdigit()]
    word_count = {}; [word_count.update({word: word_count.get(word, 0) + 1}) for word in words]
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]

# --- analyze_job_match_with_gemini (unchanged from previous version) ---
def analyze_job_match_with_gemini(user_profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes job match using Gemini, incorporating salary and experience preferences."""
    if not genai:
        # logger.info(f"Using simple match scoring for '{job.get('title')}' (Gemini not available)") # Reduce log noise
        return simple_match_scoring(user_profile, job)
    
    try:
        min_salary_pref_str = f"${user_profile.get('min_salary_preference', 0):.0f}/year"
        job_salary_str = "${:.0f}/year".format(job['normalized_salary']) if job.get('normalized_salary') else "Not specified"
        
        prompt = f"""
        Task: Evaluate match: Candidate profile vs. early-career Job (0-3 years exp target).

        Candidate Profile:
        - Skills: {', '.join(user_profile.get('skills', []))}
        - Experience Summary: {user_profile.get('experience_summary', 'Not provided')}
        - Resume Keywords: {', '.join(user_profile.get('keywords', []))}
        - Minimum Salary Preference: {min_salary_pref_str}

        Job Details:
        - Title: {job.get('title', '')} @ {job.get('company', '')}
        - Location: {job.get('location', '')}
        - Description: {job.get('description_snippet', '')} (Full desc available if needed)
        - Requirements: {', '.join(job.get('requirements', []))}
        - Salary: {job_salary_str}

        Instructions:
        1. Score (0-100): Fit for skills, potential (0-3yr lens), and salary alignment (if job salary known).
        2. Explain Score: Key skill overlaps, experience relevance (internships count!), salary factor.
        3. Matching Skills: List strong matches from profile.
        4. Missing Skills: List key skills needed.
        5. Recommendation: "apply" if good fit & salary reasonable, else "skip".

        Respond ONLY with valid JSON object:
        {{
            "match_score": integer, "explanation": "string", 
            "matching_skills": ["string"], "missing_skills": ["string"], 
            "recommendation": "apply" or "skip"
        }}
        """
        
        model = genai.GenerativeModel("gemini-pro", generation_config=GENERATION_CONFIG, safety_settings=SAFETY_SETTINGS)
        # logger.info(f"Sending request to Gemini API for job: {job.get('title')}") # Reduce log noise
        response = model.generate_content(prompt, request_options={'timeout': 45}) # Add timeout to API call
        
        if not response.parts:
             logger.warning(f"Gemini API returned no parts for job: {job.get('title')}")
             return simple_match_scoring(user_profile, job)
        
        response_text = response.text
        # --- (Robust JSON Parsing and Validation - same as before) ---
        try:
            json_match = None
            # Try finding JSON block first
            json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_block_match:
                try: json_match = json.loads(json_block_match.group(1).strip())
                except json.JSONDecodeError: logger.warning("Found JSON block but failed to parse.")
            
            # If block parsing failed or no block found, try parsing the whole text
            if json_match is None: 
                 try: json_match = json.loads(response_text.strip())
                 except json.JSONDecodeError:
                      logger.error(f"Failed to parse Gemini response as JSON: {response_text[:200]}...")
                      return simple_match_scoring(user_profile, job)

            # Validate structure and types
            analysis = {}
            analysis['match_score'] = int(json_match.get('match_score', 0))
            analysis['explanation'] = str(json_match.get('explanation', 'No explanation provided.'))
            analysis['matching_skills'] = [str(s).strip() for s in json_match.get('matching_skills', []) if isinstance(s, str) and str(s).strip()]
            analysis['missing_skills'] = [str(s).strip() for s in json_match.get('missing_skills', []) if isinstance(s, str) and str(s).strip()]
            analysis['recommendation'] = str(json_match.get('recommendation', 'skip')).lower()

            if not (0 <= analysis['match_score'] <= 100): analysis['match_score'] = 50 
            if analysis['recommendation'] not in ['apply', 'skip']: analysis['recommendation'] = 'skip'
                
            # logger.info(f"Successfully parsed Gemini API response for job: {job.get('title')}") # Reduce log noise
            return analysis

        except Exception as parse_err:
            logger.error(f"Error processing Gemini JSON: {parse_err} - Response: {response_text[:200]}...")
            return simple_match_scoring(user_profile, job)

    except Exception as e: # Catch errors during API call itself (e.g., timeouts, connection errors)
        logger.error(f"Error calling Gemini API for job matching '{job.get('title')}': {str(e)}")
        # Consider specific error types (e.g., google.api_core.exceptions.DeadlineExceeded)
        return simple_match_scoring(user_profile, job) # Fallback on error

# --- simple_match_scoring (unchanged from previous version) ---
def simple_match_scoring(user_profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Basic scoring, slightly adjusted for experience and salary awareness."""
    user_skills = {skill.lower() for skill in user_profile.get('skills', [])}
    job_reqs_list = job.get('requirements', []) # Use requirements from API if available
    job_requirements = {req.lower() for req in job_reqs_list if isinstance(req, str)}
    
    # Add potential requirements from description/title if explicit list is empty
    if not job_requirements:
         text_to_scan = (job.get('title', '') + ' ' + job.get('full_description', '')).lower()
         common_keywords = {"python","r","java","sql","excel","sheets","project management","communication","analysis","customer service","marketing","sales","recruitment","operations","teaching","curriculum","research","data analysis","reporting","financial modelling","canva","trello","salesforce"}
         job_requirements.update(kw for kw in common_keywords if kw in text_to_scan)

    matching_skills_count = len(user_skills.intersection(job_requirements))
    total_reqs_count = len(job_requirements) if len(job_requirements) > 0 else 1 # Avoid division by zero
    
    # Base score on skill overlap
    skill_score = int((matching_skills_count / total_reqs_count) * 70) if total_reqs_count > 1 else (30 if matching_skills_count > 0 else 0)

    # Experience factor (using API info if available)
    exp_months = job.get('api_required_months')
    exp_boost = 0
    if exp_months is not None:
         if exp_months == 0: exp_boost = 15 # Explicitly no experience
         elif 0 < exp_months <= 36: exp_boost = 10 # Matches 0-3 years target
    # Use text/title guess if API data missing
    elif job.get('is_entry_level_guess') or job.get('mentions_1_3_years'): # These flags are from older text analysis
         exp_boost = 5

    # Salary factor
    job_salary = job.get('normalized_salary')
    user_min_salary = user_profile.get('min_salary_preference', 0)
    salary_adjust = 0
    if job_salary is not None and user_min_salary > 0:
        if job_salary < user_min_salary * 0.85: salary_adjust = -25 # Significant penalty
        elif job_salary < user_min_salary: salary_adjust = -10 # Minor penalty
        elif job_salary >= user_min_salary: salary_adjust = 15 # Bonus

    # Combine scores
    final_score = max(0, min(100, skill_score + exp_boost + salary_adjust))
    recommendation = "apply" if final_score >= 50 else "skip" # Adjust threshold as needed

    return {
        'match_score': final_score,
        'explanation': f"Simple score ({skill_score} skills + {exp_boost} exp + {salary_adjust} salary). Matched {matching_skills_count}/{total_reqs_count} reqs.",
        'matching_skills': list(user_skills.intersection(job_requirements)),
        'missing_skills': list(job_requirements - user_skills),
        'recommendation': recommendation
    }

# --- Main Job Fetching and Processing Logic ---

def search_and_get_jobs_for_user(user: User, limit=300) -> List[Dict[str, Any]]:
    user_profile = extract_user_profile(user)
    min_annual_salary_pref = user_profile.get('min_salary_preference', None)

    # Job Titles
    job_titles_to_search = getattr(user, 'desired_job_titles', []) or []
    if not job_titles_to_search: # Fallback logic
         skill_keywords = ["operations", "business development", "project management", "analyst", "teacher", "consultant", "research", "administration", "coordinator", "assistant", "engagement", "curriculum"]
         derived_titles = {s for s in user_profile['skills'] if isinstance(s, str) and any(kw in s.lower() for kw in skill_keywords)}
         if len(derived_titles) < 5: derived_titles.update(["Associate", "Coordinator", "Analyst", "Specialist", "Intern", "Assistant"])
         job_titles_to_search = sorted(list(derived_titles))[:12] # Limit number of derived titles
    logger.info(f"Job titles to search: {job_titles_to_search}")

    location = "United States"; logger.info(f"Location search: {location}")
    
    all_recommendations = []; searched_urls = set()
    MAX_PAGES_PER_TITLE = 5 # Reduce pages per title to limit API calls if errors persist

    for job_title in job_titles_to_search:
        if len(all_recommendations) >= limit: break
        logger.info(f"--- Starting search for: {job_title} ---")
        no_results_streak = 0 
        
        for page in range(1, MAX_PAGES_PER_TITLE + 1):
            if len(all_recommendations) >= limit: break
            try:
                jobs_from_api = search_jobs_api(job_title, location, page, min_annual_salary=min_annual_salary_pref)
                
                if not jobs_from_api: 
                    no_results_streak += 1
                    if no_results_streak >= 2: 
                         logger.info(f"Stopping search for '{job_title}' after {page} pages (no new results).")
                         break 
                    continue 
                
                no_results_streak = 0; new_jobs_this_page = 0; processed_this_page = 0
                for job in jobs_from_api:
                    processed_this_page += 1
                    job_url = job.get('url')
                    if not job_url or job_url in searched_urls: 
                        continue
                    match_analysis = analyze_job_match_with_gemini(user_profile, job)
                    job.update(match_analysis) 

                    all_recommendations.append(job); searched_urls.add(job_url); new_jobs_this_page += 1
                    if len(all_recommendations) >= limit: break 

                logger.info(f"Page {page} for '{job_title}': Processed {processed_this_page}, Added {new_jobs_this_page}. Total: {len(all_recommendations)}")
                if len(all_recommendations) >= limit: break # Break outer loop too if limit reached

                if page < MAX_PAGES_PER_TITLE: time.sleep(random.uniform(1.5, 2.5)) # Increase delay
                
            except Exception as e:
                logger.error(f"Critical error during job processing loop for '{job_title}' page {page}: {str(e)}")
                import traceback; logger.error(traceback.format_exc())
                break # Stop searching this title on critical error
    
    # Final Sort: By SALARY (High to Low), Nones last, then by match_score
    all_recommendations.sort(
        key=lambda x: (x.get('normalized_salary') if x.get('normalized_salary') is not None else -1, x.get('match_score', 0)),
        reverse=True )

    logger.info(f"Finished search. Found {len(all_recommendations)} total recommendations for {user_profile['name']}. Sorted by salary.")
    return all_recommendations[:limit] 

# --- Output Saving Functions (unchanged from previous version) ---
def save_recommendations_to_pdf(user: User, recommendations: List[Dict[str, Any]], filename="job_recommendations.pdf"):
    """Saves job recommendations to a PDF file, including salary info."""
    try:
        doc = SimpleDocTemplate(filename, pagesize=letter,
                                leftMargin=0.75*inch, rightMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='SmallNormal', parent=styles['Normal'], fontSize=8.5, leading=10))
        styles.add(ParagraphStyle(name='JobTitle', parent=styles['h3'], fontSize=10, spaceAfter=2))
        styles.add(ParagraphStyle(name='CompanyItalic', parent=styles['Italic'], fontSize=9, spaceAfter=4))
        styles.add(ParagraphStyle(name='ExplanationItalic', parent=styles['SmallNormal'], fontName='Times-Italic'))

        story = []
        user_name = getattr(user, 'name', 'N/A') # Safe access
        user_min_salary_hourly = getattr(user, 'min_salary_hourly', 0.0)

        story.append(Paragraph(f"Job Recommendations for {user_name}", styles['h1']))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}. Target Exp: 0-3 Years. Min Salary Pref: ~${user_min_salary_hourly*2080:.0f}/year.", styles['SmallNormal']))
        story.append(Paragraph(f"Sorted by Estimated Salary (High to Low), then Match Score.", styles['SmallNormal']))
        story.append(Spacer(1, 0.25 * inch))

        for i, job in enumerate(recommendations):
            # --- Job Header ---
            story.append(Paragraph(f"{i+1}. {job.get('title', 'N/A')}", styles['JobTitle']))
            story.append(Paragraph(f"{job.get('company', 'N/A')}", styles['CompanyItalic']))

            # --- Core Details ---
            salary_str = "Not specified"
            if job.get('normalized_salary') is not None and job['normalized_salary'] > 0:
                 salary_str = f"~${job['normalized_salary']:,.0f}/year"
            elif job.get('raw_salary_info', {}).get('text'): 
                 salary_str = job['raw_salary_info']['text'][:50] # Limit length

            details = [ f"<b>Loc:</b> {job.get('location', 'N/A')}", f"<b>Salary:</b> {salary_str}",
                        f"<b>Score:</b> {job.get('match_score', 'N/A')}%", f"<b>Rec:</b> {job.get('recommendation', 'N/A').capitalize()}" ]
            story.append(Paragraph(" | ".join(details), styles['SmallNormal']))

            # --- URL ---
            if job.get('url'):
                 url = job.get("url"); display_url = url if len(url) < 80 else url[:77] + "..."
                 story.append(Paragraph(f'<a href="{url}"><font color="blue">{display_url}</font></a>', styles['SmallNormal']))

            # --- Match Explanation & Skills ---
            if job.get('match_explanation'): story.append(Paragraph(f"<i>Explanation:</i> {job.get('match_explanation')}", styles['ExplanationItalic']))
            matching_s = ', '.join(job.get('matching_skills', [])); missing_s = ', '.join(job.get('missing_skills', []))
            if matching_s: story.append(Paragraph(f"<b>Match Skills:</b> {matching_s}", styles['SmallNormal']))
            if missing_s: story.append(Paragraph(f"<b>Dev Skills:</b> {missing_s}", styles['SmallNormal']))

            story.append(Spacer(1, 0.15 * inch)) # Space between entries

        logger.info(f"Building PDF document: {filename}")
        doc.build(story)
        logger.info(f"Successfully saved {len(recommendations)} recommendations to {filename}")

    except ImportError: logger.error("ReportLab not found. Cannot save PDF. `pip install reportlab`")
    except Exception as e: logger.error(f"Error generating PDF: {str(e)}", exc_info=True)


def save_recommendations_to_csv(user: User, recommendations: List[Dict[str, Any]], filename="job_recommendations.csv"):
    """Saves job recommendations to a CSV file."""
    try:
        headers = [ 'Rank', 'Title', 'Company', 'Location', 'Estimated Annual Salary', 'Raw Salary Text',
                    'Match Score (%)', 'Recommendation', 'Explanation', 'Matching Skills', 'Missing Skills',
                    'Job URL', 'Source', 'API Required Months' ]
        
        logger.info(f"Preparing to save recommendations to CSV: {filename}")
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore') # Ignore extra keys in dict
            writer.writeheader()
            for i, job in enumerate(recommendations):
                salary_normalized = job.get('normalized_salary')
                salary_raw = job.get('raw_salary_info', {}).get('text', '')
                row = {
                    'Rank': i + 1, 'Title': job.get('title', 'N/A'), 'Company': job.get('company', 'N/A'),
                    'Location': job.get('location', 'N/A'),
                    'Estimated Annual Salary': f"{salary_normalized:.0f}" if salary_normalized is not None else '',
                    'Raw Salary Text': salary_raw if salary_raw else '',
                    'Match Score (%)': job.get('match_score', ''), 'Recommendation': job.get('recommendation', '').capitalize(),
                    'Explanation': job.get('match_explanation', ''),
                    'Matching Skills': ", ".join(job.get('matching_skills', [])),
                    'Missing Skills': ", ".join(job.get('missing_skills', [])),
                    'Job URL': job.get('url', ''), 'Source': job.get('source', ''),
                    'API Required Months': job.get('api_required_months', '') 
                }
                writer.writerow(row)
        logger.info(f"Successfully saved {len(recommendations)} recommendations to {filename}")
    except Exception as e: logger.error(f"Error generating CSV: {str(e)}", exc_info=True)


# --- Main Execution Block ---

if __name__ == "__main__":
    print("\n==== InstantApply Job Recommender (Early Career Focus) ====")
    # Determine if using fallback or DB model for logging
    user_class_name = User.__name__ if User else "Unknown"
    print(f"Running in standalone mode (Using User class: {user_class_name})...")

    # --- User Data Setup ---
    user_skills_list = [ # From previous setup
        "Statistical Data Analysis", "Data Management", "R", "Python", "Financial Modelling",
        "MS Excel", "Google Sheets", "Project Management", "Trello", "Organizational Strategy",
        "Recruitment", "Graphic Design", "Canva", "Research", "CRM", "Salesforce",
        "Teaching", "Curriculum Development", "Classroom Management", "Restorative Justice",
        "Trauma-Informed Care", "Cross-cultural Communication", "Leadership", "Teambuilding",
        "Conflict Management", "Adaptability", "Creative Problem Solving", "Critical Thinking",
        "Analytical Skills", "Customer Service", "Time Management", "Interpersonal Skills",
        "English", "Malay", "Mandarin", "Cantonese", "Spanish" ]
    user_skills_str = ", ".join(sorted(list(set(user_skills_list))))
    user_experience_summary = ( # Concise summary
        "Founder/Exec Director (Non-profit); Ops Associate/Teaching Fellow (Edu Non-profit); "
        "Ops Coordinator (Civic Non-profit); Outreach Intern/TA (University); Teacher (EdTech); "
        "Office Intern (State Gov x2); Biz Dev Intern (Startup)." )
    user_resume_full_text = """
    KAH VERN CHIANG - San Francisco, CA - kahvern@uni.minerva.edu - linkedin.com/in/kahvern/
    EDUCATION: Minerva University, SF, CA (Expected Grad: June 2025), BS Social Science & Business (Operations), GPA: 3.93. Relevant Coursework: Financial Modelling, Marketing, Biz Ops, Public Policy.
    EXPERIENCE: Hands for Education (Founder/Exec Director, Mar 2018–Pres): Lead 70/20; Recruited 80+ volunteers; Raised ~$10.8k; 500+ students impacted. | Minerva University (TA, Sep 2023–Pres): Guided 50 students; Graded 1400+ items. | Think Academy (Teacher, Jan–Aug 2024): Taught math (6-8 yrs); Graded 120+ assignments. | Breakthrough Twin Cities (Ops Assoc, May–Aug 2024; Math Teaching Fellow, Jun 2022–Aug 2023): Budget mgt ($11k); Inventory; Supervised interns; Transport coord; Streamlined docs; Taught math (80% literacy gain); Community building; Prayer room setup; Student crisis support. | Citizenship Coalition (Ops Coord, May–Aug 2024): Recruited 100+ tutors; Built partnerships; Secured $10k Google Ads grant. | Minerva University (Outreach Intern, Aug 2022–Apr 2023): Organized workshop; Developed database; Supported 80+ applicants (25% acceptance). | State Assemblywoman Offices (Intern, Dec 2020–Apr 2021): Resident outreach; Event logistics; Digitalization support; Designed materials; Welfare assist; Laptop/Food aid distrib. | Roomah (Biz Dev Intern, Aug–Oct 2020): Partner research; Successful pitch; Rebranding input.
    SKILLS: Technical: Data Analysis (R, Python), Financial Modelling (Excel/Sheets), Project Mgt (Trello), Graphic Design (Canva), Research, CRM (Salesforce). Teaching: Curriculum Dev, Classroom Mgt. Soft: Cross-cultural Comm, Leadership, Teambuilding, Conflict Mgt, Adaptability, Problem Solving, Critical/Analytical Thinking, Customer Service. Languages: English/Malay (Fluent), Mandarin (Proficient), Cantonese (Conversational), Spanish (Basic). """

    # --- Instantiate the User ---
    try:
        # Check which User class we are using (DB model or Fallback)
        if User.__name__ == 'FallbackUser':
             # FallbackUser accepts the argument directly
             user_instance = User(
                 name="Kah Vern Chiang", skills=user_skills_str, experience=user_experience_summary,
                 resume=user_resume_full_text,
                 desired_job_titles=[ # Keep refined list
                     "Operations Associate", "Business Development Associate", "Program Coordinator",
                     "Project Coordinator", "Executive Assistant", "Administrative Coordinator",
                     "Education Program Associate", "Curriculum Development Assistant", "Community Engagement Coordinator",
                     "Research Assistant", "Junior Consultant", "Business Analyst", "Operations Analyst",
                     "Project Assistant", "Nonprofit Program Staff", "Entry Level Consultant", "Management Trainee" ],
                 work_mode_preference="No Preference",
                 min_salary_hourly=30.0
             )
             print("Instantiated using FallbackUser class.")
        else:
             # DBUser (imported) likely doesn't accept it in __init__
             user_instance = User(
                 name="Kah Vern Chiang", skills=user_skills_str, experience=user_experience_summary,
                 resume=user_resume_full_text,
                 desired_job_titles=[ # Keep refined list
                     "Operations Associate", "Business Development Associate", "Program Coordinator",
                     "Project Coordinator", "Executive Assistant", "Administrative Coordinator",
                     "Education Program Associate", "Curriculum Development Assistant", "Community Engagement Coordinator",
                     "Research Assistant", "Junior Consultant", "Business Analyst", "Operations Analyst",
                     "Project Assistant", "Nonprofit Program Staff", "Entry Level Consultant", "Management Trainee" ],
                 work_mode_preference="No Preference",
                 # DO NOT PASS min_salary_hourly here
             )
             # Set the attribute *after* initialization for the DB User model
             setattr(user_instance, 'min_salary_hourly', 30.0)
             print(f"Instantiated using {User.__name__} class and manually set min_salary_hourly.")

    except TypeError as e:
         # This might catch other TypeErrors if the DB User __init__ changes
         print(f"FATAL: TypeError during User initialization: {e}. Check User class __init__ arguments for {User.__name__}. Exiting.")
         sys.exit(1)
    except Exception as e: # Catch other potential init errors
         print(f"FATAL: Error during User initialization: {e}. Exiting.")
         import traceback; traceback.print_exc() # Print full traceback for other errors
         sys.exit(1)


    # --- Run Recommendation ---
    user_name_safe = getattr(user_instance, 'name', 'User')
    # Safely get the attribute we set, default to 0.0 if it somehow wasn't set
    user_min_salary_hourly_safe = getattr(user_instance, 'min_salary_hourly', 0.0) 
    print(f"\nFinding early-career (0-3 yrs) recommendations for: {user_name_safe}")
    print(f"Targeting jobs in: United States")
    print(f"Minimum Salary Preference: Approx ${user_min_salary_hourly_safe * 2080:,.0f}/year")
    print("This may take several minutes...")

    recommendation_limit = 300; start_time = time.time()
    results = search_and_get_jobs_for_user(user_instance, limit=recommendation_limit)
    end_time = time.time(); print(f"Search and analysis took {end_time - start_time:.2f} seconds.")

    # --- Save Results ---
    if results:
        safe_user_name_file = re.sub(r'[^\w\-]+', '_', user_name_safe)
        base_filename = f"{safe_user_name_file}_Job_Recommendations_{time.strftime('%Y%m%d')}"
        pdf_filename = os.path.join(script_dir, f"{base_filename}.pdf") # Save in script dir
        csv_filename = os.path.join(script_dir, f"{base_filename}.csv") # Save in script dir

        print(f"\nAttempting to save results...")
        pdf_saved = False; csv_saved = False
        try: save_recommendations_to_pdf(user_instance, results, filename=pdf_filename); pdf_saved = True
        except Exception as pdf_err: logger.error(f"Failed to save PDF: {pdf_err}", exc_info=True)
        try: save_recommendations_to_csv(user_instance, results, filename=csv_filename); csv_saved = True
        except Exception as csv_err: logger.error(f"Failed to save CSV: {csv_err}", exc_info=True)

    else: print("No recommendations were found matching the criteria.")

    print(f"\nScript finished. Found {len(results)} recommendations.")
    if results and 'pdf_filename' in locals() and 'csv_filename' in locals():
        print(f"Results saved to directory: {script_dir}")
        if pdf_saved: print(f"- PDF: {os.path.basename(pdf_filename)}")
        else: print("- PDF saving failed (see logs).")
        if csv_saved: print(f"- CSV: {os.path.basename(csv_filename)}")
        else: print("- CSV saving failed (see logs).")