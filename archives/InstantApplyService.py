import google.generativeai as genai
import os
from models.user import db, User
import json

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')


def generate_cover_letter(user_email, job_title, company):
    """Generates a cover letter using Gemini AI with user database information."""
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return "User not found in the database."

    user_skills = json.loads(user.skills) if user.skills else []
    user_experience = json.loads(user.experience) if user.experience else []
    
    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
    Write a professional cover letter for a {job_title} position at {company}.
    The applicant's name is {user.name}.
    Highlight their skills in {', '.join(user_skills)}.
    Mention relevant experience such as {', '.join(user_experience)}.
    """
    
    response = model.generate_content(prompt)
    return response.text

# Example Usage
cover_letter = generate_cover_letter("user@example.com", "Software Engineer", "Google")
print(cover_letter)

def match_job_description(user_email, job_description):
    """Uses Gemini AI to compare a resume with a job description using user database data."""
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return "User not found in the database."

    user_resume = user.resume or "No resume available."
    user_skills = json.loads(user.skills) if user.skills else []
    user_experience = json.loads(user.experience) if user.experience else []

    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
    Compare the following resume with the job description.
    Rate the match on a scale of 1-10 and highlight missing skills.

    Applicant Name: {user.name}
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

# Example Usage
resume_text = "Experienced Python Developer skilled in AI and automation."
job_desc = "Looking for a Software Engineer with expertise in Python, AI, and API Development."

match_result = match_job_description("user@example.com", job_desc)
print(match_result)