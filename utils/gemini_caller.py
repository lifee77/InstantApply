import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
# Set up Gemini API key globally
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_cover_letter(job_title, company, user_data):
    """Generates a cover letter using Gemini AI with provided user data."""
    if not user_data:
        return "User data is missing."

    user_name = user_data.get('name', 'Applicant')
    user_skills = user_data.get('skills', [])
    user_experience = user_data.get('experience', [])

    model = genai.GenerativeModel("gemini-2.0-pro-exp")

    prompt = f"""
    Write a professional cover letter for a {job_title} position at {company}.
    The applicant's name is {user_name}.
    Highlight their skills in {', '.join(user_skills)}.
    Mention relevant experience such as {', '.join(user_experience)}.
    """
    
    response = model.generate_content(prompt)
    return response.text

def match_job_description(job_description, user_data):
    """Uses Gemini AI to compare a resume with a job description using provided user data."""
    if not user_data:
        return "User data is missing."

    user_name = user_data.get('name', 'Applicant')
    user_resume = user_data.get('resume', "No resume available.")
    user_skills = user_data.get('skills', [])
    user_experience = user_data.get('experience', [])

    model = genai.GenerativeModel("gemini-2.0-pro-exp")

    prompt = f"""
    Compare the following resume with the job description.
    Rate the match on a scale of 1-10 and highlight missing skills.

    Applicant Name: {user_name}
    Resume:
    {user_resume}

    Skills:
    {', '.join(user_skills)}

    Experience:
    {', '.join(user_experience)}

    Job Description:
    {job_description}
    """
    
    response = model.generate_content(prompt)
    return response.text


def extract_resume_data(resume_text):
    """Extracts key skills, experience, and keywords from a resume using Gemini AI."""
    model = genai.GenerativeModel("gemini-2.0-pro-exp")

    prompt = f"""
    Analyze the following resume and extract:
    1. Key skills
    2. Work experience
    3. Keywords for job search

    Resume:
    {resume_text}
    """
    
    response = model.generate_content(prompt)
    return response.text
