#!/usr/bin/env python3
import os
import logging
import json
import time
import sys
import random
import re # Import regex for better text parsing
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.colors import black, grey

# Add the project root to the Python path when running standalone
# Use absolute path from this file's location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) # Assumes script is in a subdirectory like 'utils'
sys.path.insert(0, project_root)
# print(f"Project Root added to sys.path: {project_root}") # Debug print

# Now we can import our project modules (handle potential errors)
try:
    # This might fail if 'models' isn't directly under project_root
    # or if run from a different working directory.
    from models.user import User
except ImportError:
    # logger.warning("Could not import User from models.user. Using fallback class.")
    # If running standalone without Flask context, define a simple User class
    class User:
        """Simple User class for standalone testing"""
        def __init__(self, name="", email="", skills="", experience="", resume="", desired_job_titles=None, work_mode_preference="", min_salary_hourly=0.0):
            self.id = 0 # Typically assigned by DB
            self.name = name
            self.email = email
            self.skills = skills
            self.experience = experience
            self.resume = resume
            self.desired_job_titles = desired_job_titles if desired_job_titles else []
            self.work_mode_preference = work_mode_preference
            self.min_salary_hourly = min_salary_hourly

# Load environment variables
# Look for .env in the script's directory or parent directories
dotenv_path = os.path.join(script_dir, '.env')
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(project_root, '.env') # Check project root
    
load_dotenv(dotenv_path=dotenv_path)
# print(f"Attempting to load .env from: {dotenv_path}") # Debug print


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
        genai = genai_import # Assign to module-level variable
        genai.configure(api_key=GEMINI_API_KEY)
        GENERATION_CONFIG = {"temperature": 0.2, "top_p": 0.95, "top_k": 40, "max_output_tokens": 2048}
        SAFETY_SETTINGS = { category: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for category in HarmCategory if category != HarmCategory.HARM_CATEGORY_UNSPECIFIED }
        logger.info("Gemini API configured successfully")
    except ImportError:
        logger.warning("google-generativeai package not installed. Install with: pip install google-generativeai")
        genai = None # Ensure it's None if import fails
    except Exception as e:
        logger.error(f"Error configuring Gemini: {e}")
        genai = None
else:
    logger.warning("GEMINI_API_KEY not found. Job match analysis will use simple scoring.")

# --- Job Search Functions ---

def parse_salary(salary_text: Optional[str], min_salary: Optional[float], max_salary: Optional[float], salary_period: Optional[str]) -> Optional[float]:
    """
    Attempts to parse salary information and return an approximate annualized salary.
    Returns None if parsing fails or information is insufficient.
    """
    if min_salary is not None and isinstance(min_salary, (int, float)) and min_salary > 0:
        salary = float(min_salary)
        period = str(salary_period).upper() if salary_period else None
        
        if period == 'HOURLY':
            return salary * 40 * 52 # Approx annual
        elif period == 'WEEKLY':
             return salary * 52
        elif period == 'MONTHLY':
            return salary * 12
        elif period == 'YEARLY':
            return salary
        # If period is unknown but salary seems annual (e.g., > 20000), assume yearly
        elif salary > 20000: 
             return salary
        # If period is unknown and salary is low, assume hourly
        elif salary < 1000: 
             return salary * 40 * 52
             
    # Fallback: Try parsing from text if numerical fields failed
    if isinstance(salary_text, str):
        salary_text = salary_text.replace(',', '').replace('$', '').lower()
        value = None
        period_mult = 1 # Default annual

        # Find numerical value
        match = re.search(r'([\d\.]+)\s*(k)?', salary_text)
        if match:
            value = float(match.group(1))
            if match.group(2) == 'k':
                value *= 1000

        if value is not None:
             # Determine period multiplier
            if 'hour' in salary_text or 'hr' in salary_text:
                period_mult = 40 * 52
            elif 'week' in salary_text:
                 period_mult = 52
            elif 'month' in salary_text:
                period_mult = 12
            elif 'year' in salary_text or 'annum' in salary_text or value > 20000: # Assume large numbers are annual
                period_mult = 1
            # If low value and no period, assume hourly
            elif value < 1000 and 'year' not in salary_text and 'month' not in salary_text and 'week' not in salary_text: 
                 period_mult = 40 * 52
                 
            return value * period_mult
            
    return None # Cannot determine salary

def search_jobs_api(job_title: str, location: str, page: int = 1, min_annual_salary: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Search for jobs using Jsearch API, prioritizing entry-level/early-career roles.
    Adds optional minimum salary query parameter if supported and provided.
    """
    if not RAPID_API_KEY:
        logger.warning("RAPID_API_KEY not found. Using mock data.")
        return search_jobs_mock(job_title, location) # Mock data doesn't use salary param

    logger.info(f"Found RAPID_API_KEY.")

    try:
        # Add keywords relevant to 0-3 years experience
        query_keywords = ["entry level", "junior", "associate", "graduate", "coordinator", "analyst"]
        # Add job title, try variations
        query = f"{job_title} ({' OR '.join(query_keywords)}) in {location}"
        # Also consider searching for title without keywords if first query yields few results
        # query = f"{job_title} in {location}" # Alternative simpler query

        logger.info(f"Searching jobs via API: Query='{query}', Page={page}")
        url = "https://jsearch.p.rapidapi.com/search"
        
        querystring = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
            # "date_posted": "month", # Example: Filter recent jobs
            # "employment_types": "FULLTIME,INTERN", # Example
        }

        # Add minimum salary if provided and API supports it (check JSearch docs for exact param name)
        # Assuming 'salary_min' might work based on common patterns, but verify.
        if min_annual_salary and min_annual_salary > 0:
             # JSearch might expect integer, needs verification
             querystring["salary_min"] = str(int(min_annual_salary)) 
             logger.info(f"Added minimum salary parameter: {querystring['salary_min']}")

        headers = {
            "X-RapidAPI-Key": RAPID_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        response = requests.get(url, headers=headers, params=querystring, timeout=20) # Add timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json()
        api_jobs = []
        
        # Debug saving removed for brevity, can be re-added if needed

        for job_data in data.get('data', []):
            # --- Extract Core Info ---
            title = job_data.get('job_title', '')
            company = job_data.get('employer_name', '')
            url_link = job_data.get('job_apply_link', '')
            
            if not title or not company or not url_link: continue # Skip incomplete entries

            # --- Location ---
            job_city = job_data.get('job_city') or ''
            job_state = job_data.get('job_state') or ''
            location_str = f"{job_city}, {job_state}".strip(", ") if job_city or job_state else location if location else "United States"

            # --- Description ---
            job_description = job_data.get('job_description', '')
            desc_snippet = (job_description[:200] + '...') if job_description else "No description available"

            # --- Salary Parsing ---
            normalized_salary = parse_salary(
                job_data.get('job_salary_info'), # Assuming this field exists, check API docs
                job_data.get('job_min_salary'), 
                job_data.get('job_max_salary'), 
                job_data.get('job_salary_period')
            )
            
            # --- Experience Level Guess ---
            # Basic check, can be improved with regex on description
            title_lower = title.lower()
            desc_lower = job_description.lower() if job_description else ""
            is_entry_level_guess = any(keyword in title_lower for keyword in ["entry", "junior", "associate", "intern", "graduate", "coordinator"])
            # Check description for years (simple check)
            mentions_1_3_years = bool(re.search(r'\b(1|2|3)\s*(\+|years?)\b', desc_lower))
            requires_many_years = bool(re.search(r'\b([4-9]|10)\+?\s*years?\b', desc_lower)) # Check for 4+ years specifically
            
            # Filter based on experience guess: Keep if title suggests entry OR description mentions 1-3 years AND doesn't explicitly ask for 4+
            keep_based_on_exp = is_entry_level_guess or (mentions_1_3_years and not requires_many_years)
            # If query was specifically 'intern', be less strict
            if "intern" in job_title.lower(): keep_based_on_exp = True 
            # Stricter: Only keep if explicitly entry or mentions 1-3 years
            # keep_based_on_exp = is_entry_level_guess or mentions_1_3_years

            if not keep_based_on_exp:
                 # logger.debug(f"Skipping job due to experience filter: {title}")
                 continue

            job = {
                'id': job_data.get('job_id', f"jsearch-{random.randint(1000,9999)}"),
                'title': title,
                'company': company,
                'location': location_str,
                'job_type': job_data.get('job_employment_type', ''),
                'description_snippet': desc_snippet,
                'full_description': job_description, # Store full desc for better analysis
                'url': url_link,
                'source': 'JSearch API',
                'date_generated': job_data.get('job_posted_at_datetime_utc', ''),
                'normalized_salary': normalized_salary, # Store parsed salary
                'raw_salary_info': { # Store raw fields for reference
                     "text": job_data.get('job_salary_info'),
                     "min": job_data.get('job_min_salary'),
                     "max": job_data.get('job_max_salary'),
                     "period": job_data.get('job_salary_period')
                 },
                'requirements': job_data.get('job_highlights', {}).get('Qualifications', []), # Get requirements if available
                'is_entry_level_guess': is_entry_level_guess,
                'mentions_1_3_years': mentions_1_3_years
            }
            api_jobs.append(job)
            
        logger.info(f"Found {len(api_jobs)} potentially relevant jobs via API on page {page}")
        return api_jobs
            
    except requests.exceptions.Timeout:
         logger.error(f"API request timed out for page {page}")
         return [] # Return empty on timeout, don't fallback immediately
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during API job search: {str(e)}")
        # Consider fallback or returning empty based on error type
        # If it's auth error (401/403), fallback is useless. If server error (5xx), maybe retry later?
        if e.response is not None and 400 <= e.response.status_code < 500:
             logger.error("Client-side API error (e.g., bad request, auth). Won't fallback.")
             return []
        else: # Network issue or server error, maybe fallback is ok
             logger.info("Attempting fallback to mock data due to API error.")
             return search_jobs_mock(job_title, location) 
    except Exception as e:
        logger.error(f"Unexpected error in API job search: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("Attempting fallback to mock data due to unexpected error.")
        return search_jobs_mock(job_title, location)

# Mock search function remains largely the same, just ensure it returns similar dict structure
def search_jobs_mock(job_title: str, location: str) -> List[Dict[str, Any]]:
    logger.info(f"Generating mock data for: {job_title} in {location}")
    # ... (mock data generation logic from previous versions) ...
    # Ensure the generated mock job dictionaries include:
    # 'title', 'company', 'location', 'url', 'description_snippet', 'full_description',
    # 'requirements' (list), 'normalized_salary' (can be random or None),
    # 'is_entry_level_guess' (bool), 'mentions_1_3_years' (bool)
    # Example addition for salary:
    mock_jobs = [] # Assume this is populated as before
    for job in mock_jobs:
         job['normalized_salary'] = random.choice([None, 50000, 60000, 70000]) # Example
         job['full_description'] = job.get('full_description', job['description_snippet'])
         job['requirements'] = job.get('requirements', [])
         job['is_entry_level_guess'] = True # Assume mock jobs are entry level
         job['mentions_1_3_years'] = random.choice([True, False])
    return mock_jobs # Return the list


# --- User Profile and Matching Functions ---

def extract_user_profile(user: User) -> Dict[str, Any]:
    profile = {
        "name": user.name,
        "skills": [],
        "experience_summary": user.experience or "",
        "resume_text": user.resume or "",
        "keywords": [],
        "min_salary_preference": user.min_salary_hourly * 40 * 52 if user.min_salary_hourly else 0 # Annualized preference
    }
    # Skill Parsing (Combine from multiple fields if necessary)
    all_skill_texts = [user.skills] 
    # Add skills from resume text analysis if desired
    
    unique_skills = set()
    for text in all_skill_texts:
        if not text: continue
        # Handle JSON list or comma-separated
        try:
            skills_list = json.loads(text)
            if isinstance(skills_list, list):
                 unique_skills.update(str(s).strip() for s in skills_list if str(s).strip())
            else: # Assume comma-separated if not a list
                 unique_skills.update(skill.strip() for skill in str(text).split(",") if skill.strip())
        except (json.JSONDecodeError, TypeError):
             unique_skills.update(skill.strip() for skill in str(text).split(",") if skill.strip())
             
    profile["skills"] = sorted(list(unique_skills))
        
    if profile["resume_text"]:
        profile["keywords"] = extract_keywords_from_text(profile["resume_text"])
        
    logger.info(f"Extracted profile for {user.name}: {len(profile['skills'])} skills, {len(profile['keywords'])} keywords, Min Salary Pref: ${profile['min_salary_preference']:.0f}/year")
    return profile

def extract_keywords_from_text(text: str, max_keywords: int = 30) -> List[str]:
    # Keep common words list concise
    common_words = {"the","and","a","to","of","in","i","is","that","it","with","as","for","was","on","are","be","this","have","an","by","at","not","from","or","my","work","job","jobs","year","years","experience","skills","skill","project","team","development","management","analysis","data","operations","business", "university", "education", "student", "students", "program", "support", "community"}
    
    words = text.lower()
    words = re.sub(r'[^\w\s-]', '', words) # Keep words, spaces, hyphens
    words = words.split()
    words = [word for word in words if word and word not in common_words and len(word) > 2 and not word.isdigit()]
    
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
        
    # Simple TF-IDF idea: Penalize very common words across typical resumes (like 'responsibilities')
    # For now, just frequency based
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, count in sorted_words[:max_keywords]]
    return keywords

def analyze_job_match_with_gemini(user_profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes job match using Gemini, incorporating salary and experience preferences."""
    if not genai:
        logger.info(f"Using simple match scoring for '{job.get('title')}' (Gemini API not available/configured)")
        return simple_match_scoring(user_profile, job)
    
    try:
        # Construct prompt with updated context
        min_salary_pref_str = f"${user_profile.get('min_salary_preference', 0):.0f}/year (approx ${user_profile.get('min_salary_preference', 0)/2080:.2f}/hour)"
        
        prompt = f"""
        Task: Evaluate the match between the candidate profile and the job description for an early-career role (0-3 years experience).

        Candidate Profile:
        - Skills: {', '.join(user_profile.get('skills', []))}
        - Experience Summary: {user_profile.get('experience_summary', 'Not provided')}
        - Resume Keywords: {', '.join(user_profile.get('keywords', []))}
        - Minimum Salary Preference: {min_salary_pref_str}

        Job Details:
        - Title: {job.get('title', '')}
        - Company: {job.get('company', '')}
        - Location: {job.get('location', '')}
        - Description Snippet: {job.get('description_snippet', '')} 
        - Known Requirements: {', '.join(job.get('requirements', []))}
        - Estimated Annual Salary (if known): {"${:.0f}".format(job.get('normalized_salary')) if job.get('normalized_salary') else "Not specified"}

        Instructions:
        1. Analyze the match focusing on skills, relevant projects/internships, and potential for growth, considering the 0-3 year experience range.
        2. Provide a match score (0-100). Higher scores indicate better fit for skills AND potential alignment with salary preference (if job salary is known).
        3. Briefly explain the score, mentioning key skill overlaps, experience relevance (even internships), and any salary considerations (if possible).
        4. List skills from the profile that strongly match the job.
        5. List key skills potentially missing or needing development.
        6. Recommend "apply" if it's a reasonable fit (skills/potential) AND doesn't obviously conflict with salary preference (if known), otherwise "skip".

        Format your response as a valid JSON object:
        {{
            "match_score": integer (0-100),
            "explanation": "string",
            "matching_skills": ["string"],
            "missing_skills": ["string"],
            "recommendation": "apply" or "skip"
        }}
        """
        
        model = genai.GenerativeModel("gemini-pro", generation_config=GENERATION_CONFIG, safety_settings=SAFETY_SETTINGS)
        logger.info(f"Sending request to Gemini API for job: {job.get('title')}")
        response = model.generate_content(prompt)
        
        if not response.parts:
             logger.warning(f"Gemini API returned no parts for job: {job.get('title')}")
             return simple_match_scoring(user_profile, job)
        
        response_text = response.text
        # --- (JSON Parsing and Validation - same robust logic as before) ---
        try:
            json_match = None
            if "```json" in response_text:
                try:
                    json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                    json_match = json.loads(json_str)
                except (IndexError, json.JSONDecodeError): pass # Ignore if block extraction fails
            
            if json_match is None: json_match = json.loads(response_text.strip())

            analysis = {}
            analysis['match_score'] = int(json_match.get('match_score', 0))
            analysis['explanation'] = str(json_match.get('explanation', 'No explanation provided.'))
            analysis['matching_skills'] = [str(s) for s in json_match.get('matching_skills', []) if isinstance(s, str)]
            analysis['missing_skills'] = [str(s) for s in json_match.get('missing_skills', []) if isinstance(s, str)]
            analysis['recommendation'] = str(json_match.get('recommendation', 'skip')).lower()

            # Validation
            if not (0 <= analysis['match_score'] <= 100): analysis['match_score'] = 50 
            if analysis['recommendation'] not in ['apply', 'skip']: analysis['recommendation'] = 'skip'
                
            logger.info(f"Successfully parsed Gemini API response for job: {job.get('title')}")
            return analysis

        except Exception as parse_err:
            logger.error(f"Error processing Gemini JSON response: {parse_err} - Response: {response_text[:200]}...")
            return simple_match_scoring(user_profile, job)

    except Exception as e:
        logger.error(f"Error using Gemini API for job matching: {str(e)}")
        return simple_match_scoring(user_profile, job)

def simple_match_scoring(user_profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Basic scoring, slightly adjusted for experience and salary awareness."""
    user_skills = {skill.lower() for skill in user_profile.get('skills', [])}
    job_reqs_list = job.get('requirements', [])
    job_requirements = {req.lower() for req in job_reqs_list if isinstance(req, str)}
    
    # Add potential requirements from description if list is empty
    if not job_requirements and job.get('full_description'):
         desc_lower = job['full_description'].lower()
         common_keywords = {"python", "java", "sql", "excel", "project management", "communication", "analysis", "customer service", "marketing", "sales", "recruitment", "operations", "teaching", "curriculum", "research", "data analysis", "reporting"}
         job_requirements.update(kw for kw in common_keywords if kw in desc_lower)

    matching_skills = user_skills.intersection(job_requirements)
    score = 0
    if job_requirements:
        score = int((len(matching_skills) / len(job_requirements)) * 80) # Skill match weight
    elif user_skills:
         score = 20 # Base score if user has skills but job reqs unclear
         
    # Boost for experience indicators match
    if job.get('is_entry_level_guess') or job.get('mentions_1_3_years'):
        score = min(100, score + 10)

    # Check salary (if known) against preference
    job_salary = job.get('normalized_salary')
    user_min_salary = user_profile.get('min_salary_preference', 0)
    salary_penalty = 0
    if job_salary is not None and user_min_salary > 0:
        if job_salary < user_min_salary * 0.9: # Penalize if significantly below preference
            salary_penalty = 20 
        elif job_salary >= user_min_salary:
             score = min(100, score + 10) # Small boost if meets/exceeds preference

    score = max(0, min(100, score - salary_penalty))
    recommendation = "apply" if score >= 45 else "skip" # Slightly higher threshold

    return {
        'match_score': score,
        'explanation': f"Simple score: {len(matching_skills)}/{len(job_requirements)} skills. Salary known: {'Yes' if job_salary is not None else 'No'}. Meets min pref: {'Yes' if job_salary and user_min_salary and job_salary >= user_min_salary else 'No/Unknown'}.",
        'matching_skills': list(matching_skills),
        'missing_skills': list(job_requirements - user_skills),
        'recommendation': recommendation
    }

# --- Main Job Fetching and Processing Logic ---

def search_and_get_jobs_for_user(user: User, limit=300) -> List[Dict[str, Any]]:
    user_profile = extract_user_profile(user)
    min_annual_salary_pref = user_profile.get('min_salary_preference', None)

    # Determine job titles to search
    job_titles_to_search = user.desired_job_titles or []
    if not job_titles_to_search:
         # Fallback based on skills or generic early-career titles
         if user_profile['skills']:
              # Prioritize keywords from skills list
              skill_keywords = ["operations", "business development", "project management", "analyst", "teacher", "consultant", "research", "administration"]
              job_titles_to_search = [s for s in user_profile['skills'] if any(kw in s.lower() for kw in skill_keywords)]
              if not job_titles_to_search: job_titles_to_search = user_profile['skills'][:3] # Top 3 skills if no keywords match
         else:
              job_titles_to_search = ["Associate", "Coordinator", "Analyst", "Specialist", "Intern"] # Generic fallback
    # Ensure 'Intern' is included if summer preference exists (though not explicitly used here)
    if "summer" in user.work_mode_preference.lower() and "Intern" not in job_titles_to_search:
         job_titles_to_search.append("Intern")
         
    logger.info(f"Job titles to search: {job_titles_to_search}")

    # Location: Default to broad US search
    location = "United States"
    logger.info(f"Location search: {location}")
    
    all_recommendations = []
    searched_urls = set()
    MAX_PAGES_PER_TITLE = 6 # Increase slightly to get more potential results

    for job_title in job_titles_to_search:
        if len(all_recommendations) >= limit: break
        logger.info(f"--- Starting search for: {job_title} ---")
        
        for page in range(1, MAX_PAGES_PER_TITLE + 1):
            if len(all_recommendations) >= limit: break

            logger.info(f"Searching page {page}/{MAX_PAGES_PER_TITLE} for '{job_title}'...")
            try:
                # Pass min salary preference to API search function
                jobs_from_api = search_jobs_api(job_title, location, page, min_annual_salary=min_annual_salary_pref)
                
                if not jobs_from_api: # API returned empty list for this page
                    logger.info(f"No more jobs found via API for '{job_title}' on page {page}.")
                    # If page 1 had no results, maybe try a simpler query? Not implemented here.
                    break # Stop searching this title

                new_jobs_found_this_page = 0
                for job in jobs_from_api:
                    job_url = job.get('url')
                    if not job_url or job_url in searched_urls: continue

                    # Optional: Stricter Salary Filter (Apply *before* Gemini analysis if desired)
                    # job_salary = job.get('normalized_salary')
                    # if min_annual_salary_pref and job_salary is not None and job_salary < min_annual_salary_pref * 0.85: # Allow some leeway
                    #     logger.debug(f"Skipping job due to salary filter: {job.get('title')} (${job_salary:.0f} < ${min_annual_salary_pref * 0.85:.0f})")
                    #     continue

                    # Perform Matching (Gemini or Simple)
                    match_analysis = analyze_job_match_with_gemini(user_profile, job)
                    job.update(match_analysis) # Add match scores etc.
                    
                    all_recommendations.append(job)
                    searched_urls.add(job_url)
                    new_jobs_found_this_page += 1
                        
                    if len(all_recommendations) >= limit:
                         logger.info(f"Reached recommendation limit ({limit}). Stopping search.")
                         break 

                logger.info(f"Processed {new_jobs_found_this_page} new jobs from page {page} for '{job_title}'. Total recommendations: {len(all_recommendations)}")
                
                if page < MAX_PAGES_PER_TITLE and len(all_recommendations) < limit:
                    time.sleep(1.2) # Slightly longer delay between pages
                
            except Exception as e:
                logger.error(f"Error during job processing loop for '{job_title}' page {page}: {str(e)}")
                break # Stop searching this title on error
    
    # Final Sort: By SALARY (High to Low), then by match_score as secondary
    # Handle None salaries by treating them as lowest (-1)
    all_recommendations.sort(
        key=lambda x: (x.get('normalized_salary', -1), x.get('match_score', 0)),
        reverse=True # Highest salary first, then highest score for ties
    )

    logger.info(f"Finished search. Found {len(all_recommendations)} recommendations for {user.name}. Sorted by salary.")
    return all_recommendations[:limit] 

# --- PDF Saving Function ---

def save_recommendations_to_pdf(user: User, recommendations: List[Dict[str, Any]], filename="job_recommendations.pdf"):
    """Saves job recommendations to a PDF file, including salary info."""
    try:
        doc = SimpleDocTemplate(filename, pagesize=letter,
                                leftMargin=0.75*inch, rightMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        # Add a smaller style for details
        styles.add(ParagraphStyle(name='SmallNormal', parent=styles['Normal'], fontSize=9))
        story = []

        story.append(Paragraph(f"Job Recommendations for {user.name}", styles['h1']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}. Target Exp: 0-3 Years. Min Salary Pref: ~${user.min_salary_hourly*2080:.0f}/year.", styles['SmallNormal']))
        story.append(Paragraph(f"Sorted by Salary (High to Low), then Match Score.", styles['SmallNormal']))
        story.append(Spacer(1, 0.3 * inch))

        for i, job in enumerate(recommendations):
            # Job Title and Company
            story.append(Paragraph(f"{i+1}. {job.get('title', 'N/A')}", styles['h3']))
            story.append(Paragraph(f"<i>{job.get('company', 'N/A')}</i>", styles['Italic']))
            story.append(Spacer(1, 0.05 * inch))

            # Core Details
            salary_str = "Not specified"
            if job.get('normalized_salary') is not None and job['normalized_salary'] > 0:
                 salary_str = f"~${job['normalized_salary']:,.0f}/year"
            elif job.get('raw_salary_info', {}).get('text'): # Show raw text if normalization failed
                 salary_str = job['raw_salary_info']['text']
                 
            details = [
                f"<b>Location:</b> {job.get('location', 'N/A')}",
                f"<b>Salary:</b> {salary_str}",
                f"<b>Match Score:</b> {job.get('match_score', 'N/A')}%",
                f"<b>Recommendation:</b> {job.get('recommendation', 'N/A').capitalize()}"
            ]
            if job.get('url'):
                 url = job.get("url")
                 # Truncate long URLs for display
                 display_url = url if len(url) < 70 else url[:67] + "..."
                 details.append(f'<b>URL:</b> <a href="{url}"><font color="blue">{display_url}</font></a>')
                 
            for detail in details:
                 story.append(Paragraph(detail, styles['SmallNormal'])) # Use smaller font

            # Match Explanation & Skills
            if job.get('match_explanation'):
                story.append(Paragraph(f"<i>Explanation:</i> {job.get('match_explanation')}", styles['SmallNormal']))
            if job.get('matching_skills'):
                 story.append(Paragraph(f"<b>Matching Skills:</b> {', '.join(job.get('matching_skills'))}", styles['SmallNormal']))
            if job.get('missing_skills'):
                 story.append(Paragraph(f"<b>Skills to Develop:</b> {', '.join(job.get('missing_skills'))}", styles['SmallNormal']))

            story.append(Spacer(1, 0.20 * inch)) # Space between entries

        logger.info(f"Building PDF document: {filename}")
        doc.build(story)
        logger.info(f"Successfully saved {len(recommendations)} recommendations to {filename}")

    except ImportError:
        logger.error("ReportLab library not found. Cannot save to PDF. Install with: pip install reportlab")
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


# --- Main Execution Block ---

if __name__ == "__main__":
    print("\n==== InstantApply Job Recommender (Early Career Focus) ====")
    print("Running in standalone testing mode...")
    
    # --- Updated User Data ---
    user_skills_list = [
        "Statistical Data Analysis", "Data Management", "R", "Python", "Financial Modelling", 
        "MS Excel", "Google Sheets", "Project Management", "Trello", "Organizational Strategy", 
        "Recruitment", "Graphic Design", "Canva", "Research", "CRM", "Salesforce", 
        "Teaching", "Curriculum Development", "Classroom Management", "Restorative Justice", 
        "Trauma-Informed Care", "Cross-cultural Communication", "Leadership", "Teambuilding", 
        "Conflict Management", "Adaptability", "Creative Problem Solving", "Critical Thinking", 
        "Analytical Skills", "Customer Service", "Time Management", "Interpersonal Skills", 
        "English", "Malay", "Mandarin", "Cantonese", "Spanish"
    ]
    # Join skills into a comma-separated string for the User class field
    user_skills_str = ", ".join(sorted(list(set(user_skills_list)))) 

    user_experience_summary = (
        "Founder/Exec Director (Hands for Education); Ops Associate/Math Teaching Fellow (Breakthrough TC); "
        "Ops Coordinator (Citizenship Coalition); Outreach Intern (Minerva U); TA (Minerva U); "
        "Teacher (Think Academy); Office Intern (State Assemblywoman KT & SJ); Biz Dev Intern (Roomah)."
    )
    
    user_resume_full_text = """
    KAH VERN CHIANG
    San Francisco, CA • kahvern@uni.minerva.edu • +1 (415) 580 2439 • linkedin.com/in/kahvern/

    EDUCATION
    Minerva University, San Francisco, CA	Expected Graduation: June 2025
    Candidate for Bachelor of Science in Social Science (Political Science and Economics) and Business (Operations)
    - Studying in seven international cities (SF, Seoul, Hyderabad, Berlin, Buenos Aires, London, Taipei)
    - GPA: 3.93/4.00 | Relevant Coursework: Financial Modelling, Marketing, Business Operations, Public Policy, Constitutional Design, Social Psychology, Formal Analyses, Empirical Analyses, Complex Systems

    EXPERIENCE
    Hands for Education, Petaling Jaya, Malaysia	March 2018 – Present
    Founder and Executive Director
    - Lead a team of 70 people and report to 20 board members to implement education equity projects.
    - Recruited 80+ volunteers via LinkedIn (budget $4, 8.4% application rate from 659 views).
    - Raised and managed RM48,000 (~$10,800) through grants, crowdfunding, prizes.
    - Conducted 20+ workshops, 300 enrichment classes, 40 learning sessions impacting 500+ students.
    - Distributed 24,000 face masks & 6420 hand sanitizers to 5,000+ underprivileged families during COVID.

    Minerva University, San Francisco, CA	 September 2023 - Present
    Constitutional Design & Political Science Teaching Assistant				 	   
    - Hosted weekly office hours and 1-on-1s providing academic guidance to 50 students from 30+ countries.
    - Graded over 1400 class assessment polls providing personalized formative feedback to 30 students.

    Think Academy, San Jose, CA	 January 2024 – August 2024
    Elementary Math Teacher							            	         
    - Delivered 50 hours of advanced math instruction for students aged 6-8 via interactive online platform.
    - Graded 120+ class assignments, providing personalized feedback within 24 hours.

    Breakthrough Twin Cities, Saint Paul, MN	May 2024 – August 2024 (Operations Associate) / June 2022 – August 2023 (Math Teaching Fellow)
    Operations Associate (Summer 2024)
    - Managed $11,000 budget for site operations, field trips, events; ensured fiscal responsibility.
    - Oversaw inventory management and supply orders for 180+ students & 34 staff.
    - Supervised five interns, delegating tasks and fostering professional growth.
    - Coordinated bus transportation for 180+ students, resolving issues for timely access.
    - Streamlined document creation using mail merge, saving 50+ hours.
    Math Teaching Fellow (Summer 2022, 2023)
    - Delivered 150+ hours of classroom instruction, improving 30 underserved students’ math literacy by 80%.
    - Led committee of 10 coworkers creating community spirit for 100+ students.
    - Initiated and created a suitable prayer room for 20+ Muslim students.
    - Researched resources for three students facing personal crises.

    Citizenship Coalition, Boston, MA	May 2024 – August 2024
    Operations Coordinator
    - Recruited 100+ volunteer tutors ($0 budget) via VolunteerMatch, LinkedIn, Google Ads.
    - Developed partnerships with three non-profits to enhance program reach.
    - Secured $10,000 Google Ads grant for outreach.

    Minerva University, San Francisco, CA	August 2022 - April 2023
    Southeast and South Asia Outreach Intern
    - Organized two-day Design Thinking workshop for 60+ participants from 11 SEA countries.
    - Developed database of 200+ schools/organizations in Malaysia.
    - Provided application support to 80+ applicants (info sessions, 1:1s), achieving 25% acceptance rate (vs <1% overall).

    The Office of the State Assemblywoman of Kampung Tunku, Malaysia	 February 2021 – April 2021
    Office Intern									           
    - Reached out to 200+ residents offering food aid/welfare.
    - Organized logistics for 2 welfare voucher events (1,500+ seniors).
    - Managed digitalization initiative for 30+ female micro-entrepreneurs during COVID.
    - Designed 3 videos, 2 posters, website for party’s 55th anniversary.
 
    The Office of the State Assemblywoman of Subang Jaya, Malaysia	December 2020 – February 2021
    Office Intern									      
    - Designed 2 bilingual report cards, 20 social media graphics, 3 videos.
    - Coordinated collection/distribution of 50 used laptops for students.
    - Assisted 250+ residents with welfare applications/inquiries (100% satisfaction).
    - Delivered 1,000+ food aid packages during lockdown.

    Roomah (previously HUT Coliving), Kuala Lumpur, Malaysia	 August 2020 – October 2020
    Business Development Intern							            	           
    - Researched list of 150+ potential hotel partners.
    - Prepared/presented pitch resulting in successful partnership.
    - Ideated 10 company names; one adopted during rebranding.

    SKILLS
    Technical: Statistical Analysis, Data Management & Analysis (R, Python), Financial Modelling & Analysis (MS Excel/Google Sheets), Project Management (Trello), Graphic Design (Canva), Research, CRM (Salesforce)
    Teaching/Education: Curriculum Development, Classroom Management, Restorative Justice, Trauma-Informed Care
    Soft Skills: Cross-cultural Communication, Leadership, Teambuilding, Conflict Management, Adaptability, Creative Problem Solving, Critical Thinking, Analytical Skills, Customer Service, Time Management, Interpersonal Skills
    Languages: English & Malay (Fluent), Mandarin (Proficient), Cantonese (Conversational), Spanish (Basic)
    """

    # --- Instantiate the User ---
    kah_vern_user = User(
        name="Kah Vern Chiang",
        skills=user_skills_str,
        experience=user_experience_summary,
        resume=user_resume_full_text,
        # Updated desired job types based on input
        desired_job_titles=[
            "Operations Associate", "Business Development Associate", "Program Coordinator", 
            "Project Coordinator", "Executive Assistant", "Administrative Assistant", 
            "Education Coordinator", "Curriculum Development Associate", "Community Engagement",
            "Research Associate", "Junior Consultant", "Business Analyst", "Operations Analyst", 
            "Intern" # Include specifically
        ],
        work_mode_preference="No Preference", # Location preference handled in search logic
        min_salary_hourly=30.0 # Set minimum wage preference
    )
    
    # --- Run Recommendation ---
    print(f"\nFinding early-career (0-3 yrs) job recommendations for: {kah_vern_user.name}")
    print(f"Targeting jobs in: United States (No location preference)")
    print(f"Minimum Salary Preference: Approx ${kah_vern_user.min_salary_hourly * 2080:,.0f}/year")
    print("This may take several minutes...")
    
    recommendation_limit = 300 
    results = search_and_get_jobs_for_user(kah_vern_user, limit=recommendation_limit)
    
    # --- Save Results ---
    if results:
        # Sanitize username for filename
        safe_user_name = re.sub(r'[^\w\-]+', '_', kah_vern_user.name)
        pdf_filename = f"{safe_user_name}_Job_Recommendations_{time.strftime('%Y%m%d')}.pdf"
        try:
             save_recommendations_to_pdf(kah_vern_user, results, filename=pdf_filename)
        except Exception as pdf_err:
             logger.error(f"Failed to save PDF: {pdf_err}") # Log error but continue
             print(f"Error: Could not save PDF recommendations.")
    else:
        print("No recommendations were found matching the criteria.")

    print(f"\nScript finished. Found {len(results)} recommendations.")
    if results and 'pdf_filename' in locals():
        print(f"Results saved to: {pdf_filename}")