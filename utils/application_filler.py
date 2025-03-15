import logging
from typing import Dict, Any, List
import asyncio
import google.generativeai as genai
from flask import current_app
from models.user import User
from playwright.async_api import async_playwright, Playwright
import tempfile
import os

logger = logging.getLogger(__name__)

async def extract_application_questions_async(job_id: str) -> List[Dict[str, Any]]:
    """
    Extract application questions from a job posting using Playwright
    
    Args:
        job_id: The Indeed job ID
        
    Returns:
        List of question dictionaries
    """
    questions = []
    
    async with async_playwright() as p:
        try:
            # Launch browser with more stable parameters
            browser = await p.chromium.launch(
                headless=False,  # Use headed mode to avoid crashes
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-software-rasterizer", 
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox"
                ]
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to the application page
            await page.goto(f"https://www.indeed.com/viewjob?jk={job_id}&apply=1", timeout=30000)
            
            try:
                # Wait for application form to load with a longer timeout
                await page.wait_for_selector("form", timeout=15000)
                
                # Find all label elements within the form
                label_elements = await page.query_selector_all("form label")
                
                for label_element in label_elements:
                    question_text = await label_element.inner_text()
                    question_text = question_text.strip()
                    
                    # Exclude standard fields
                    if question_text.lower() in ["name", "email", "phone", "resume", "linkedin"]:
                        continue
                    
                    logger.debug(f"Detected question label: {question_text}")
                    
                    # Default question type
                    question_type = "text"
                    
                    questions.append({
                        "text": question_text,
                        "type": question_type
                    })
            except Exception as e:
                logger.warning(f"Error finding form elements: {str(e)}")
                # Return default questions if extraction fails
                questions = [
                    {"text": "What is your greatest strength?", "type": "text"},
                    {"text": "Why do you want to work here?", "type": "text"},
                ]
                logger.info(f"Using default questions: {questions}")
                
            await browser.close()
            
        except Exception as e:
            logger.error(f"Error extracting application questions: {str(e)}")
            # Return default questions if browser fails
            questions = [
                {"text": "What is your greatest strength?", "type": "text"},
                {"text": "Why do you want to work here?", "type": "text"},
            ]
            logger.info(f"Using default questions after error: {questions}")
    
    logger.info(f"Extracted questions: {questions}")
    return questions

def extract_application_questions(job_id: str) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for the async extract_application_questions_async function
    """
    with current_app.app_context():
        return asyncio.run(extract_application_questions_async(job_id))

def setup_gemini():
    """Configure the Gemini API"""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in configuration")
        raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")
    
    genai.configure(api_key=api_key)

def generate_application_responses(job_id: str, user: User) -> Dict[str, Any]:
    """
    Generate responses to job application questions using Gemini AI
    
    Args:
        job_id: The Indeed job ID
        user: User object with profile information
        
    Returns:
        Dictionary of question responses
    """
    # Setup Gemini API
    setup_gemini()
    model = genai.GenerativeModel(current_app.config.get('GEMINI_MODEL', 'gemini-pro'))
    
    # Extract questions from job application
    questions = extract_application_questions(job_id)
    
    # Prepare dummy responses
    responses = {question["text"]: "Dummy response" for question in questions}
    
    return responses
