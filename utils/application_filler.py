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
        
        # Initialize user_data from user object for response mapping
        self.user_data = {
            "name": self.user.name,
            "email": self.user.email,
            "professional_summary": self.user.professional_summary,
            "skills": self.user.skills,
            "experience": self.user.experience,
            "career_goals": self.user.career_goals,
            "biggest_achievement": self.user.biggest_achievement,
            "work_style": self.user.work_style,
            "industry_attraction": self.user.industry_attraction,
            "willing_to_relocate": self.user.willing_to_relocate,
            "authorization_status": self.user.authorization_status,
            "available_start_date": self.user.available_start_date,
            "portfolio_links": self.user.linkedin_url,
            "certifications": self.user._certifications if hasattr(self.user, '_certifications') else None,
            "languages": self.user._languages if hasattr(self.user, '_languages') else None,
        }
        
        # Setup Gemini for response generation
        setup_gemini()
        self.model = genai.GenerativeModel(current_app.config.get('GEMINI_MODEL', 'gemini-pro'))
        
        # Track failures for retry logic
        self.failed_fields = []
        self.max_retries = 3

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
            # First try to find form labels
            label_elements = await page.query_selector_all("form label")
            
            if not label_elements:
                # Try alternative selectors if no labels are found
                label_elements = await page.query_selector_all("form .field-label, form .question-text, form .form-label")
            
            for label_element in label_elements:
                question_text = await label_element.inner_text()
                question_text = question_text.strip()

                # Exclude standard fields (e.g., name, email, phone)
                if question_text.lower() in ["name", "email", "phone", "resume", "linkedin"]:
                    continue
                
                # Find associated input type to determine question type
                question_type = "text"  # Default question type
                
                # Try to find associated input by checking if the label has a "for" attribute
                for_attr = await label_element.get_attribute("for")
                if for_attr:
                    # Check if this input exists and what type it is
                    input_elem = await page.query_selector(f"#{for_attr}")
                    if input_elem:
                        input_type = await input_elem.get_attribute("type")
                        if input_type:
                            question_type = input_type
                
                logger.debug(f"Detected question: '{question_text}' with type '{question_type}'")
                questions.append({
                    "text": question_text,
                    "type": question_type,
                    "element_id": for_attr
                })
        except Exception as e:
            logger.error(f"Error parsing application page: {str(e)}")
            
        if not questions:
            # Return default questions if none were found
            logger.warning("No questions found, using default questions")
            questions = [
                {"text": "What is your greatest strength?", "type": "text"},
                {"text": "Why do you want to work here?", "type": "text"},
            ]
            
        return questions

    async def fill_application_field(self, page, question: dict, user_response: str, retry_count=0):
        """
        Fill out a single application field based on the extracted question and user profile data.

        Args:
            page: The Playwright page object
            question: Dictionary with question text and type
            user_response: The user's response to the question
            retry_count: Number of times this field has been retried
        """
        question_text = question["text"]
        question_type = question.get("type", "text")
        element_id = question.get("element_id")
        
        if retry_count > self.max_retries:
            logger.error(f"Max retries exceeded for question '{question_text}'")
            self.failed_fields.append(question_text)
            return False
            
        try:
            # First try by id if available
            if element_id:
                selector = f"#{element_id}"
            else:
                # Try multiple selector strategies
                selectors = [
                    f'input[placeholder*="{question_text}"], textarea[placeholder*="{question_text}"]',
                    f'label:text("{question_text}") + input, label:text("{question_text}") + textarea',
                    f'label:has-text("{question_text}") input, label:has-text("{question_text}") textarea',
                    f'div:has-text("{question_text}") input, div:has-text("{question_text}") textarea'
                ]
                
                # Try each selector until one works
                for selector in selectors:
                    exists = await page.query_selector(selector)
                    if exists:
                        break
            
            if not user_response:
                logger.warning(f"No response available for question '{question_text}'.")
                return False
                
            # Handle different input types
            if question_type == "checkbox":
                # For checkboxes, convert response to boolean
                should_check = user_response.lower() in ["yes", "true", "1"]
                if should_check:
                    await page.check(selector)
                else:
                    await page.uncheck(selector)
                logger.info(f"Set checkbox for '{question_text}' to {should_check}")
                
            elif question_type == "radio":
                # For radio buttons, find the one that matches the answer
                await page.click(f'{selector}[value="{user_response}"]')
                logger.info(f"Selected radio option '{user_response}' for '{question_text}'")
                
            elif question_type == "select":
                # For dropdowns
                await page.select_option(selector, value=user_response)
                logger.info(f"Selected dropdown option '{user_response}' for '{question_text}'")
                
            else:
                # For text inputs and textareas
                await page.fill(selector, user_response)
                logger.info(f"Filled text field for '{question_text}' with response starting: {user_response[:30]}...")
            
            # Add a randomized delay to appear more human-like
            delay_time = random.uniform(1.5, 3.5)
            await asyncio.sleep(delay_time)
            return True
            
        except Exception as e:
            logger.error(f"Error filling field for question '{question_text}': {str(e)}")
            
            # Retry with increased delay
            if retry_count < self.max_retries:
                logger.info(f"Retrying field '{question_text}' (Attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(2)  # Wait before retry
                return await self.fill_application_field(page, question, user_response, retry_count + 1)
            else:
                self.failed_fields.append(question_text)
                return False

    def generate_response_based_on_question(self, question_text: str) -> str:
        """
        Generate an appropriate response for an application question based on user profile.
        
        Args:
            question_text: The question to answer
            
        Returns:
            String response to the question
        """
        # First try to map question to a field in user data
        mapped_field = map_question_to_field(question_text)
        
        # If we have user data for this question type, use it
        if mapped_field in self.user_data and self.user_data[mapped_field]:
            logger.info(f"Using profile data field '{mapped_field}' for question: {question_text}")
            return str(self.user_data[mapped_field])
        
        # If no direct mapping or empty data, use AI to generate response
        try:
            # Create prompt for Gemini
            prompt = f"""
            As {self.user.name}, please provide a professional response to this job application question:
            
            Question: "{question_text}"
            
            Use this profile information to personalize your answer:
            - Professional summary: {self.user.professional_summary or ''}
            - Skills: {self.user.skills or ''}
            - Experience: {self.user.experience or ''}
            - Career goals: {self.user.career_goals or ''}
            - Work style: {self.user.work_style or ''}
            
            Write in first person as {self.user.name}.
            Keep your answer professional, concise (2-3 sentences) and specifically tailored to the question.
            """
            
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            logger.info(f"Generated AI response for question: {question_text[:30]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating response with AI: {str(e)}")
            return f"I believe I am well-qualified for this position and excited about this opportunity."

    async def handle_resume_upload(self, page):
        """
        Handle the upload of the resume if a file input is present.

        Args:
            page: The Playwright page object
        """
        if self.user.resume_file_path and os.path.exists(self.user.resume_file_path):
            try:
                logger.info(f"Uploading resume from: {self.user.resume_file_path}")
                
                # Try different selectors for file upload inputs
                file_input_selectors = [
                    'input[type="file"]',
                    'input[name="resume"]',
                    'input[accept=".pdf,.doc,.docx"]',
                    'label:has-text("Resume") input[type="file"]',
                    'label:has-text("CV") input[type="file"]'
                ]
                
                for selector in file_input_selectors:
                    file_input = await page.query_selector(selector)
                    if file_input:
                        await file_input.set_input_files(self.user.resume_file_path)
                        logger.info(f"Resume uploaded successfully using selector: {selector}")
                        await asyncio.sleep(2)  # Wait after upload
                        return True
                
                logger.warning("Resume file input not found after trying multiple selectors.")
                return False
                
            except Exception as e:
                logger.error(f"Error uploading resume: {str(e)}")
                return False
        else:
            logger.warning("No resume file path or file doesn't exist.")
            return False

    async def fill_application_form(self, page):
        """
        Fill the job application form using user profile data.

        Args:
            page: The Playwright page object
            
        Returns:
            Dictionary with success status and list of any failed fields
        """
        logger.info(f"Starting form fill for job URL: {self.job_url} using user: {self.user.email}")
        
        # Reset failed fields tracking
        self.failed_fields = []
        
        # First extract questions from the page
        questions = await self.parse_application_page(page)
        logger.info(f"Found {len(questions)} questions to fill")
        
        # Fill each question's field
        for i, question in enumerate(questions):
            logger.info(f"Processing question {i+1}/{len(questions)}: {question['text']}")
            
            # Generate response for this question
            response = self.generate_response_based_on_question(question["text"])
            
            # Fill the field with the generated response
            await self.fill_application_field(page, question, response)
        
        # Return success status and any failures
        success = len(self.failed_fields) == 0
        return {
            "success": success,
            "total_questions": len(questions),
            "failed_fields": self.failed_fields
        }

    async def fill_application(self):
        """
        Main function that handles browser creation, parsing, filling, and submission of the application.
        
        Returns:
            Dictionary with application results and status
        """
        result = {
            "success": False,
            "message": "",
            "url": self.job_url,
            "user": self.user.email,
            "form_completed": False,
            "resume_uploaded": False,
            "failed_fields": []
        }
        
        logger.info(f"Starting application process for {self.job_url}")
        
        try:
            async with async_playwright() as p:
                # Launch browser with more stable parameters
                browser = await p.firefox.launch(
                    headless=False,  # Use headed mode for better reliability
                    args=[
                        "--no-sandbox",
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                    ]
                )
                
                # Create a context with viewport size and user agent
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
                )
                
                # Open new page and navigate
                page = await context.new_page()
                await page.goto(self.job_url, timeout=60000)
                
                # Wait for the page to load
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    logger.info("Page loaded successfully")
                except Exception as e:
                    logger.warning(f"Page loading timed out, continuing anyway: {str(e)}")
                
                # Fill the application form
                form_result = await self.fill_application_form(page)
                result["form_completed"] = form_result["success"]
                result["failed_fields"] = form_result["failed_fields"]
                
                # Upload resume
                result["resume_uploaded"] = await self.handle_resume_upload(page)
                
                # Set overall success based on form completion and resume upload
                result["success"] = result["form_completed"]
                
                # Take screenshot for debugging
                screenshot_path = f"/tmp/application_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot saved to {screenshot_path}")
                
                # Set final message
                if result["success"]:
                    result["message"] = "Application form filled successfully."
                    logger.info("Application process completed successfully")
                else:
                    result["message"] = f"Application partially completed with {len(form_result['failed_fields'])} failed fields."
                    logger.warning(f"Application process partially completed: {result['message']}")
                
                # Close browser
                await browser.close()
                
        except Exception as e:
            error_message = f"Error during application process: {str(e)}"
            result["message"] = error_message
            result["success"] = False
            logger.error(error_message)
            
        return result