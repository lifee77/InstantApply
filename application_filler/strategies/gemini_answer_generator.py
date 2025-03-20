

import os
import logging
import google.generativeai as genai
from flask import current_app

logger = logging.getLogger(__name__)

def setup_gemini():
    """Configure Gemini API with current_app context"""
    api_key = current_app.config.get('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY not found.")
        raise ValueError("Missing GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    logger.info("Gemini API configured.")

def generate_dynamic_answer(user_data: dict, question: str) -> str:
    """
    Use Gemini to generate a dynamic answer for a given question based on the user profile.
    
    Args:
        user_data: Dictionary with user profile information
        question: The application question to answer
    
    Returns:
        AI-generated response string
    """
    setup_gemini()
    model = genai.GenerativeModel(current_app.config.get('GEMINI_MODEL', 'gemini-pro'))

    # Build context with user profile details
    context = f"""
    User profile:
    - Name: {user_data.get('name')}
    - Professional Summary: {user_data.get('professional_summary')}
    - Skills: {', '.join(user_data.get('skills', []))}
    - Biggest Achievement: {user_data.get('biggest_achievement')}
    - Career Goals: {user_data.get('career_goals')}
    - Work Style: {user_data.get('work_style')}
    - Industry Attraction: {user_data.get('industry_attraction')}
    """

    # Construct prompt
    prompt = f"""
    Based on the following user profile, answer this question in a concise, professional manner.
    
    Question: {question}
    
    {context}
    """

    # Generate content
    logger.info(f"Sending prompt to Gemini for question: {question[:50]}...")
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else "I am excited about this opportunity."