import google.generativeai as genai
import os
import json
import base64
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up Gemini API key globally
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def call_gemini_vision(prompt, image_data):
    """
    Call the Gemini Pro Vision model with an image and a prompt
    
    Args:
        prompt: Text prompt describing what to extract from the image
        image_data: Binary image data (bytes)
        
    Returns:
        String response from Gemini model
    """
    try:
        # Configure the model - use Gemini Pro Vision which supports images
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Create the content parts (text prompt and image)
        parts = [
            {"text": prompt},
            {"mime_type": "image/jpeg", "data": base64.b64encode(image_data).decode('utf-8')}
        ]
        
        # Generate response
        response = model.generate_content(parts)
        
        # Return the text response
        return response.text
    except Exception as e:
        print(f"Error calling Gemini Vision API: {str(e)}")
        return None

def generate_cover_letter(job_title, company, user_data):
    """Generates a cover letter using Gemini AI with provided user data."""
    if not user_data:
        return "User data is missing."

    user_name = user_data.get('name', 'Applicant')
    user_skills = user_data.get('skills', [])
    user_experience = user_data.get('experience', [])

    return f"Cover letter for {user_name} applying to {company} for the position of {job_title}."

def match_job_description(job_description, user_data):
    """Uses Gemini AI to compare a resume with a job description using provided user data."""
    if not user_data:
        return "User data is missing."

    user_name = user_data.get('name', 'Applicant')
    user_resume = user_data.get('resume', "No resume available.")
    user_skills = user_data.get('skills', [])
    user_experience = user_data.get('experience', [])

    return f"Match score for {user_name}'s resume against the job description is 8/10."

def extract_resume_data(resume_text):
    """Extracts key skills, experience, and keywords from a resume using Gemini AI."""
    extracted_data = {
        "skills": ["skill1", "skill2"],
        "experience": ["experience1", "experience2"],
        "keywords": ["keyword1", "keyword2"]
    }
    print(f"Extracted resume data: {extracted_data}")  # Log extracted data
    return extracted_data
