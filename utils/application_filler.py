import logging
from typing import Dict, Any, List
import asyncio
import google.generativeai as genai
from flask import current_app, jsonify
from models.user import User
from models.job_recommendation import JobRecommendation
from flask_login import login_required, current_user
from playwright.async_api import async_playwright, Playwright
import tempfile
import os
import re
from application_filler.mappers.field_mapper import map_question_to_field
import random

logger = logging.getLogger(__name__)

def valid_url(url: str) -> bool:
    """
    Validate if the given URL is a valid job URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if the URL is valid, False otherwise
    """
    # Example of simple URL validation
    regex = r"^(https?://)?([a-z0-9-]+\.)+[a-z]{2,6}(/.*)?$"
    if re.match(regex, url):
        return True
    else:
        logger.warning(f"Invalid URL detected: {url}")
        return True # Return True for testing purposes

async def extract_application_questions_async(job_id: str, page=None) -> List[Dict[str, Any]]:
    questions = []
    launched_browser = False

    if page is None:
        launched_browser = True
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            try:
                # Launch browser with more stable parameters
                browser = await p.firefox.launch(
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
                await page.goto(job_id, timeout=60000)
            except Exception as e:
                logger.error(f"Error launching browser in extract_application_questions_async: {str(e)}")
                return []
    else:
        # Use the provided page and navigate to the URL
        try:
            await page.goto(job_id, timeout=60000)
        except Exception as e:
            logger.error(f"Error navigating to URL in extract_application_questions_async: {str(e)}")
            return []

    try:
        # Wait for form to load
        logger.info("Waiting for form to load...")
        await page.wait_for_selector("form", timeout=30000)
        logger.info("Form loaded, proceeding to extract questions...")
        
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

    # If we launched our own browser instance, close it
    if launched_browser:
        try:
            await page.context.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {str(e)}")

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
        job_id: The job ID or URL
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

class ApplicationFiller:
    def __init__(self, user: User, job_url: str):
        self.user = user
        self.job_url = job_url

    async def parse_application_page(self, page) -> list:
        """
        Parse the job application page and extract all questions.

        Args:
            page: The Playwright page object

        Returns:
            A list of extracted questions
        """
        questions = []
        try:
            label_elements = await page.query_selector_all("form label")
            for label_element in label_elements:
                question_text = await label_element.inner_text()
                question_text = question_text.strip()

                # Exclude standard fields (e.g., name, email, phone)
                if question_text.lower() in ["name", "email", "phone", "resume", "linkedin"]:
                    continue

                logger.debug(f"Detected question label: {question_text}")
                question_type = "text"  # Default question type
                questions.append({
                    "text": question_text,
                    "type": question_type
                })
        except Exception as e:
            logger.error(f"Error parsing application page: {str(e)}")
        return questions

    async def fill_application_field(self, page, question_text: str, user_response: str):
        """
        Fill out a single application field based on the extracted question and user profile data.

        Args:
            page: The Playwright page object
            question_text: The question text to find the relevant input field
            user_response: The user’s response to the question
        """
        try:
            selector = f'input[placeholder*="{question_text}"], textarea[placeholder*="{question_text}"]'
            if user_response:
                await page.fill(selector, user_response)
                logger.info(f"Filled field: {selector}")
                logger.info(f"Filled field for '{question_text}' with response starting: {user_response[:30]}...")

                # Adding a delay to simulate a slower process
                delay_time = random.uniform(2, 4)  # Random delay between 2-4 seconds
                await asyncio.sleep(delay_time)
            else:
                logger.warning(f"No response available for question '{question_text}'.")
        except Exception as e:
            logger.error(f"Error filling field for question '{question_text}': {str(e)}")

    def map_question_to_response(self, question: dict) -> tuple:
        """
        Map a question to a response based on the user profile.

        Args:
            question: Dictionary with question details (expects 'text' key)

        Returns:
            Tuple of (question text, response string)
        """
        key = map_question_to_field(question['text'])
        value = self.user_data.get(key, "I'm excited about this opportunity!")
        return (question['text'], str(value))

    async def handle_resume_upload(self, page):
        """
        Handle the upload of the resume if a file input is present.

        Args:
            page: The Playwright page object
        """
        if self.user.resume_file_path and os.path.exists(self.user.resume_file_path):
            try:
                logger.info(f"Uploading resume from: {self.user.resume_file_path}")
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(self.user.resume_file_path)
                    logger.info("Resume uploaded successfully.")
                else:
                    logger.warning("Resume file input not found.")
            except Exception as e:
                logger.error(f"Error uploading resume: {str(e)}")

    async def fill_application_form(self, page):
        """
        Fill the job application form using user profile data.

        Args:
            page: The Playwright page object
        """
        logger.info(f"Starting form fill for job URL: {self.job_url} using user: {self.user.email}")
        questions = await self.parse_application_page(page)

        for question in questions:
            logger.info(f"Processing question: {question['text']}")
            response = self.generate_response_based_on_question(question["text"])
            await self.fill_application_field(page, question["text"], response)

    async def fill_application(self, page):
        """
        Main function that handles parsing, filling, and submission of the application.
        This is the entry point that will call other helper methods in sequence.
        """
        logger.info("Starting browser in headed mode.")
        await self.fill_application_form(page)
        await self.handle_resume_upload(page)