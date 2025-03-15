#!/usr/bin/env python3
import os
import logging
import json
import time
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add the project root to the Python path when running standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import our project modules
try:
    from models.user import User
except ImportError:
    # If running standalone without Flask context, define a simple User class
    class User:
        """Simple User class for standalone testing"""
        def __init__(self, name="", email="", skills="", experience="", resume=""):
            self.id = 0
            self.name = name
            self.email = email
            self.skills = skills
            self.experience = experience
            self.resume = resume

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Only import and configure if the key is available
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Model configuration for Gemini API
        GENERATION_CONFIG = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        SAFETY_SETTINGS = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        logger.info("Gemini API configured successfully")
    except ImportError:
        logger.warning("google-generativeai package not installed. Install with: pip install google-generativeai")
else:
    logger.warning("GEMINI_API_KEY not found. Job recommendations will be limited.")

# Import job search with error handling
try:
    from utils.job_search import search_jobs
except ImportError:
    # Define a minimal mock search function for standalone testing
    def search_jobs(job_title, location):
        logger.warning("Running with mock job search (utils.job_search not available)")
        return [
            {
                'id': 'mock-1',
                'title': f"Senior {job_title}",
                'company': "TechCorp",
                'location': location,
                'job_type': "Full-time",
                'description_snippet': f"We're looking for a {job_title} with experience in Python, JavaScript, and React.",
                'requirements': ["Python", "JavaScript", "React", "SQL", "AWS"],
                'url': "https://example.com/jobs/1",
                'source': 'Mock Data'
            },
            {
                'id': 'mock-2',
                'title': f"Mid-level {job_title}",
                'company': "InnovateTech",
                'location': location,
                'job_type': "Full-time",
                'description_snippet': f"Join our team as a {job_title} working on cutting-edge applications.",
                'requirements': ["Java", "Spring", "MongoDB", "Docker", "Kubernetes"],
                'url': "https://example.com/jobs/2",
                'source': 'Mock Data'
            }
        ]

def extract_user_profile(user: User) -> Dict[str, Any]:
    """
    Extract and structure user profile data for job matching
    
    Args:
        user: User object from database
        
    Returns:
        Dictionary with structured profile information
    """
    profile = {
        "name": user.name,
        "skills": [],
        "experience": "",
        "resume_text": "",
        "keywords": []
    }
    
    # Process skills (stored as comma-separated text or JSON)
    if user.skills:
        try:
            # Try to parse as JSON
            skills_data = json.loads(user.skills)
            if isinstance(skills_data, list):
                profile["skills"] = skills_data
            elif isinstance(skills_data, dict) and "skills" in skills_data:
                profile["skills"] = skills_data["skills"]
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated list
            profile["skills"] = [skill.strip() for skill in user.skills.split(",") if skill.strip()]
    
    # Process experience
    if user.experience:
        profile["experience"] = user.experience
        
    # Process resume text
    if user.resume:
        profile["resume_text"] = user.resume
        
    # Extract keywords from resume using simple frequency analysis
    if profile["resume_text"]:
        profile["keywords"] = extract_keywords_from_text(profile["resume_text"])
        
    return profile

def extract_keywords_from_text(text: str, max_keywords: int = 20) -> List[str]:
    """
    Extract important keywords from text using basic frequency analysis
    
    Args:
        text: Text to analyze
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    # Simple implementation - in a real app you'd use NLP libraries
    # Remove common words, punctuation, and normalize
    common_words = {
        "the", "and", "a", "to", "of", "in", "i", "is", "that", "it", "with", "as", "for", 
        "was", "on", "are", "be", "this", "have", "an", "by", "at", "not", "from", "or", "my",
        "but", "they", "you", "all", "your", "their", "has", "what", "his", "her", "she", "he",
        "can", "will", "we", "me", "them", "who", "its", "if", "would", "about", "which",
        "when", "there", "been", "were", "how", "had", "our", "one", "do", "very", "up",
        "out", "so", "work", "job", "jobs", "year", "years", "experience", "skills", "skill",
        "experienced", "proficient"
    }
    
    # Tokenize and clean text
    words = text.lower().split()
    words = [word.strip('.,!?:;()[]{}""\'') for word in words]
    words = [word for word in words if word and word not in common_words and len(word) > 2]
    
    # Count word frequencies
    word_count = {}
    for word in words:
        if word in word_count:
            word_count[word] += 1
        else:
            word_count[word] = 1
    
    # Get top keywords by frequency
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, count in sorted_words[:max_keywords]]
    
    return keywords

def analyze_job_match_with_gemini(user_profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze how well a job matches with the user's profile using Gemini API
    
    Args:
        user_profile: User's profile data
        job: Job listing data
        
    Returns:
        Dictionary with match analysis
    """
    if not GEMINI_API_KEY or 'genai' not in globals():
        # Fallback scoring without Gemini
        logger.info("Using simple match scoring (Gemini API not available)")
        return simple_match_scoring(user_profile, job)
    
    try:
        # Prepare context for Gemini
        prompt = f"""
        Task: Evaluate how well the candidate's profile matches with the job requirements.
        
        Candidate Profile:
        - Skills: {', '.join(user_profile.get('skills', []))}
        - Experience: {user_profile.get('experience', 'Not provided')}
        - Resume Keywords: {', '.join(user_profile.get('keywords', []))}
        
        Job Details:
        - Title: {job.get('title', '')}
        - Company: {job.get('company', '')}
        - Description: {job.get('description_snippet', '')}
        - Requirements: {', '.join(job.get('requirements', []))}
        
        Instructions:
        1. Analyze the match between the candidate's profile and the job requirements
        2. Consider skills, experience, and keywords
        3. Provide a match score from 0-100%
        4. Provide a brief explanation for the score
        5. Identify missing/required skills the candidate should develop
        
        Format your response as a valid JSON with these fields:
        - match_score: (integer between 0-100)
        - explanation: (brief explanation of score)
        - matching_skills: (list of skills that match)
        - missing_skills: (list of skills the candidate should develop)
        - recommendation: (whether to "apply" or "skip" this job)
        """
        
        # Get Gemini model
        model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config=GENERATION_CONFIG,
            safety_settings=SAFETY_SETTINGS
        )
        
        logger.info("Sending request to Gemini API...")
        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse JSON response
        try:
            # Find JSON content between ```json and ``` if present
            if "```json" in response_text and "```" in response_text.split("```json", 1)[1]:
                json_text = response_text.split("```json", 1)[1].split("```", 1)[0]
            else:
                json_text = response_text
            
            # Clean up and parse JSON
            json_text = json_text.strip()
            analysis = json.loads(json_text)
            logger.info("Successfully parsed Gemini API response")
            
            # Ensure all expected fields exist
            required_fields = ['match_score', 'explanation', 'matching_skills', 'missing_skills', 'recommendation']
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = "" if field in ['explanation', 'recommendation'] else [] if field in ['matching_skills', 'missing_skills'] else 0
            
            # Validate match_score
            if not isinstance(analysis['match_score'], (int, float)) or analysis['match_score'] < 0 or analysis['match_score'] > 100:
                analysis['match_score'] = 50  # Default to 50% if invalid
                
            return analysis
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Gemini response as JSON: {response_text}")
            # Fallback to simple scoring
            return simple_match_scoring(user_profile, job)
    
    except Exception as e:
        logger.error(f"Error using Gemini API for job matching: {str(e)}")
        # Fallback to simple scoring
        return simple_match_scoring(user_profile, job)

def simple_match_scoring(user_profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple matching algorithm without using Gemini API
    
    Args:
        user_profile: User's profile data
        job: Job listing data
        
    Returns:
        Dictionary with match analysis
    """
    # Get user skills as a set
    user_skills = set([skill.lower() for skill in user_profile.get('skills', [])])
    user_keywords = set([keyword.lower() for keyword in user_profile.get('keywords', [])])
    
    # Get job requirements as a set
    job_requirements = set([req.lower() for req in job.get('requirements', [])])
    
    # If job has no requirements, extract some from the description
    if not job_requirements and 'description_snippet' in job:
        # Simple keyword extraction - in a production system, use NLP
        common_tech_skills = {
            "python", "javascript", "react", "node", "sql", "java", "c#", "c++", 
            "aws", "azure", "gcp", "docker", "kubernetes", "git", "devops", "agile",
            "scrum", "machine learning", "ai", "data science", "cloud", "backend",
            "frontend", "fullstack"
        }
        
        desc = job['description_snippet'].lower()
        for skill in common_tech_skills:
            if skill in desc:
                job_requirements.add(skill)
    
    # Count matching skills
    matching_skills = user_skills.intersection(job_requirements)
    
    # Calculate match score
    if job_requirements:
        skill_match = len(matching_skills) / len(job_requirements) * 70  # 70% weight
    else:
        skill_match = 50  # Default if no requirements
        
    # Check for keyword matches in job title and description
    keyword_score = 0
    if user_keywords and ('title' in job or 'description_snippet' in job):
        job_text = (job.get('title', '') + ' ' + job.get('description_snippet', '')).lower()
        matching_keywords = [keyword for keyword in user_keywords if keyword in job_text]
        keyword_score = len(matching_keywords) / len(user_keywords) * 30  # 30% weight
    
    total_score = int(skill_match + keyword_score)
    
    # Cap score between 0-100
    match_score = max(0, min(total_score, 100))
    
    # Determine recommendation
    recommendation = "apply" if match_score >= 60 else "skip"
    
    # Missing skills
    missing_skills = list(job_requirements - user_skills)
    
    return {
        'match_score': match_score,
        'explanation': f"Matched {len(matching_skills)} out of {len(job_requirements)} required skills.",
        'matching_skills': list(matching_skills),
        'missing_skills': missing_skills,
        'recommendation': recommendation
    }

def get_job_recommendations(user: User, job_title: str = None, location: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get job recommendations for a user based on their profile
    
    Args:
        user: User object from database
        job_title: Optional job title to search for (uses user skills if not provided)
        location: Optional location to search in
        limit: Maximum number of recommendations to return
        
    Returns:
        List of job recommendations with match scores
    """
    # Extract user profile
    user_profile = extract_user_profile(user)
    
    # If no job title provided, use most frequent skill as job title
    if not job_title and user_profile['skills']:
        job_title = "Software Engineer"  # Default
        if len(user_profile['skills']) > 0:
            job_title = user_profile['skills'][0]
    elif not job_title:
        job_title = "Software Engineer"  # Default fallback
    
    # If no location provided, use "Remote" as default
    if not location:
        location = "Remote"
    
    # Search for jobs
    logger.info(f"Searching for {job_title} jobs in {location} for user: {user.name}")
    jobs = search_jobs(job_title, location)
    
    if not jobs:
        logger.warning(f"No jobs found for {job_title} in {location}")
        return []
    
    # Analyze each job match
    recommendations = []
    for job in jobs:
        try:
            # Get match analysis
            match_analysis = analyze_job_match_with_gemini(user_profile, job)
            
            # Add match details to job
            job_with_match = job.copy()
            job_with_match.update({
                'match_score': match_analysis.get('match_score', 0),
                'match_explanation': match_analysis.get('explanation', ''),
                'matching_skills': match_analysis.get('matching_skills', []),
                'missing_skills': match_analysis.get('missing_skills', []),
                'recommendation': match_analysis.get('recommendation', 'skip')
            })
            
            recommendations.append(job_with_match)
            
        except Exception as e:
            logger.error(f"Error analyzing job match: {str(e)}")
            continue
    
    # Sort recommendations by match score (highest first)
    recommendations.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    # Return top recommendations
    return recommendations[:limit]

def recommend_jobs_for_user_id(user_id: int, job_title: str = None, location: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get job recommendations for a user by ID
    
    Args:
        user_id: User ID
        job_title: Optional job title to search for
        location: Optional location to search in
        limit: Maximum number of recommendations to return
        
    Returns:
        List of job recommendations with match scores
    """
    try:
        # This import is here to avoid circular imports
        from flask import current_app
        from models.user import User, db
        
        with current_app.app_context():
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User ID {user_id} not found")
                return []
                
            return get_job_recommendations(user, job_title, location, limit)
    except ImportError:
        logger.error("Flask app context not available. This function must be called within a Flask application.")
        return []

if __name__ == "__main__":
    # Example usage as a standalone script
    print("\n==== InstantApply Job Recommender ====")
    print("Running in standalone testing mode...")
    
    # Simple test with mock user data
    mock_user = User(
        name="John Developer",
        skills="Python, JavaScript, React, SQL, AWS, Docker",
        experience="Software Engineer with 3 years of experience in web development",
        resume="""
        JOHN DEVELOPER
        Software Engineer
        
        SUMMARY
        Full-stack developer with 3 years of experience building web applications.
        Proficient in Python, JavaScript, React, and SQL.
        
        SKILLS
        - Languages: Python, JavaScript, HTML, CSS
        - Frontend: React, Redux, Bootstrap
        - Backend: Flask, Django, Node.js
        - Database: PostgreSQL, MySQL, MongoDB
        - DevOps: Docker, AWS, CI/CD
        
        EXPERIENCE
        Software Engineer, TechCorp (2020-2023)
        - Developed and maintained web applications using React and Flask
        - Implemented RESTful APIs and integrated with third-party services
        - Deployed applications on AWS using Docker containers
        
        Junior Developer, StartupX (2018-2020)
        - Built responsive frontends with React and Bootstrap
        - Contributed to backend development using Django
        """
    )
    
    # Get job recommendations for the mock user
    print(f"\nFinding job recommendations for: {mock_user.name}")
    print("This may take a moment...")
    
    results = get_job_recommendations(mock_user, "Software Engineer", "Remote", 5)
    
    # Print results
    print(f"\nTop {len(results)} job recommendations for {mock_user.name}:")
    for i, job in enumerate(results, 1):
        print(f"\n--- Job #{i} ({job.get('match_score', 0)}% match) ---")
        print(f"Title: {job.get('title', '')}")
        print(f"Company: {job.get('company', '')}")
        print(f"Match: {job.get('match_explanation', '')}")
        print(f"Matching Skills: {', '.join(job.get('matching_skills', []))}")
        print(f"Missing Skills: {', '.join(job.get('missing_skills', []))}")
        print(f"Recommendation: {job.get('recommendation', '')}")
