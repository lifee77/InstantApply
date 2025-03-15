import logging
from typing import Dict, Any, List
import asyncio
import google.generativeai as genai
from flask import current_app
from models.user import User
from playwright.async_api import async_playwright, Playwright

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
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to the application page
            await page.goto(f"https://www.indeed.com/viewjob?jk={job_id}&apply=1")
            
            # Wait for application form to load
            await page.wait_for_selector("form", timeout=10000)
            
            # Find all question fields
            form_elements = await page.query_selector_all("div.ia-Questions-item")
            
            for element in form_elements:
                label_element = await element.query_selector("label")
                if not label_element:
                    continue
                    
                question_text = await label_element.inner_text()
                question_text = question_text.strip()
                
                # Determine question type
                question_type = "text"
                
                # Check for text input
                text_input = await element.query_selector("input[type='text']")
                if text_input:
                    question_type = "text"
                else:
                    # Check for textarea
                    textarea = await element.query_selector("textarea")
                    if textarea:
                        question_type = "textarea"
                    else:
                        # Check for radio buttons
                        radio_buttons = await element.query_selector_all("input[type='radio']")
                        if radio_buttons:
                            question_type = "radio"
                        else:
                            # Check for checkboxes
                            checkboxes = await element.query_selector_all("input[type='checkbox']")
                            if checkboxes:
                                question_type = "checkbox"
                            else:
                                # If no input element is found, skip this question
                                continue
                
                # Add question to list
                question = {
                    "text": question_text,
                    "type": question_type
                }
                
                # For radio/checkbox, get options
                if question_type in ["radio", "checkbox"]:
                    options = []
                    option_elements = await element.query_selector_all("label:not(:first-child)")
                    
                    for option_elem in option_elements:
                        option_text = await option_elem.inner_text()
                        options.append(option_text.strip())
                    
                    question["options"] = options
                    
                questions.append(question)
            
            await browser.close()
            
        except Exception as e:
            logger.error(f"Error extracting application questions: {str(e)}")
    
    return questions

def extract_application_questions(job_id: str) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for the async extract_application_questions_async function
    """
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
    
    # Prepare responses
    responses = {}
    
    try:
        # For each question, generate a response using Gemini
        for question in questions:
            question_text = question["text"]
            question_type = question["type"]
            
            # Create prompt for AI
            prompt = f"""
            Based on the user profile below, generate an appropriate response for the job application question: "{question_text}"
            
            User Profile:
            - Name: {user.name}
            - Skills: {user.skills}
            - Experience: {user.experience}
            
            Response should be concise, professional, and tailored to the question.
            """
            
            # Get response from Gemini
            response = model.generate_content(prompt)
            
            # Extract the answer text
            answer = response.text.strip()
            
            # Format response based on question type
            if question_type in ["text", "textarea"]:
                responses[question_text] = answer
            elif question_type in ["radio", "checkbox"]:
                # For multiple choice questions, select the best option
                options = question.get("options", [])
                if options:
                    # Ask Gemini to choose the best option from the available options
                    option_prompt = f"""
                    Based on the user profile, which of these options is the best response for the job application question: "{question_text}"
                    
                    Options:
                    {', '.join(options)}
                    
                    User Profile:
                    - Name: {user.name}
                    - Skills: {user.skills}
                    - Experience: {user.experience}
                    
                    Just return the exact text of the best option, nothing else.
                    """
                    
                    option_response = model.generate_content(option_prompt)
                    chosen_option = option_response.text.strip()
                    
                    # Find the closest matching option
                    best_match = None
                    best_match_score = 0
                    for option in options:
                        # Simple matching algorithm - can be improved
                        if option.lower() in chosen_option.lower():
                            if len(option) > best_match_score:
                                best_match = option
                                best_match_score = len(option)
                    
                    # If no good match found, use the first option
                    if not best_match and options:
                        best_match = options[0]
                        
                    responses[question_text] = best_match or chosen_option
    
    except Exception as e:
        logger.error(f"Error generating application responses: {str(e)}")
    
    return responses
