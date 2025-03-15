import logging
import asyncio
import os
from typing import Dict, Any
from playwright.async_api import async_playwright, Playwright
from models.user import User
import time
import tempfile

logger = logging.getLogger(__name__)

async def submit_application_async(job_id: str, user: User, responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit a job application using Playwright
    
    Args:
        job_id: The Indeed job ID
        user: User object with profile information
        responses: Dictionary of question responses
        
    Returns:
        Dictionary with submission status and details
    """
    result = {
        'success': False,
        'message': '',
        'job_id': job_id
    }
    
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
            
            # Fill out personal information
            try:
                # Name fields
                name_input = await page.query_selector("#input-applicant\\.name")
                if name_input:
                    await name_input.fill(user.name)
                    logger.info(f"Filled name field with: {user.name}")
                
                # Email field
                email_input = await page.query_selector("#input-applicant\\.email")
                if email_input:
                    await email_input.fill(user.email)
                    logger.info(f"Filled email field with: {user.email}")
                
                # Phone number field
                phone_input = await page.query_selector("#input-applicant\\.phone")
                if phone_input:
                    await phone_input.fill(user.phone)
                    logger.info(f"Filled phone field with: {user.phone}")
                
                # Upload resume if available
                if user.resume_file_path and os.path.exists(user.resume_file_path):
                    # Look for resume upload field
                    file_input = await page.query_selector('input[type="file"][accept=".pdf,.doc,.docx"]')
                    if file_input:
                        await file_input.wait_for_element_state('visible', timeout=10000)
                        logger.info("Resume upload field detected.")
                        # Create a temporary PDF file
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                            temp_file.write(b"%PDF-1.4\n%...")  # Add valid PDF content here
                            temp_file_path = temp_file.name
                        await file_input.set_input_files(temp_file_path)
                        logger.info(f"Uploaded resume file: {temp_file_path}")
                    else:
                        logger.warning("Resume upload field not found")
            except Exception as e:
                logger.warning(f"Standard fields not found: {str(e)}")
            
            # Process each question based on the responses
            for question in responses:
                try:
                    # Determine question text and type
                    if isinstance(question, dict):
                        question_text = question.get("text")
                        question_type = question.get("type", "text")
                    else:
                        question_text = question
                        question_type = "text"
                    
                    # Find question element by label text
                    # Escape single quotes in the XPath expression
                    safe_question_text = question_text.replace("'", "\\'")
                    question_label = await page.query_selector(f"//label[contains(text(), '{safe_question_text}')]")
                    
                    if question_label:
                        logger.info(f"Detected question label: {question_text}")
                        # Go up one level to the container
                        question_container_handle = await question_label.evaluate("node => node.parentElement")
                        question_container = await page.query_selector(f"xpath=//div[@id='{question_container_handle.id}']")
                        
                        if question_container:
                            # Handle different input types
                            # Text input
                            if question_type == "text":
                                text_input = await question_container.query_selector("input[type='text']")
                                if text_input:
                                    await text_input.fill(question_text)
                                    logger.info(f"Filled text input for question '{question_text}' with: {question_text}")
                                    # Validate input
                                    filled_value = await text_input.input_value()
                                    if filled_value == question_text:
                                        logger.info(f"Confirmed text input for question '{question_text}' is correct.")
                                    else:
                                        logger.warning(f"Text input for question '{question_text}' is incorrect. Expected: {question_text}, Found: {filled_value}")
                                    continue
                                
                            # Textarea
                            textarea = await question_container.query_selector("textarea")
                            if textarea:
                                await textarea.fill(question_text)
                                logger.info(f"Filled textarea for question '{question_text}' with: {question_text}")
                                # Validate input
                                filled_value = await textarea.input_value()
                                if filled_value == question_text:
                                    logger.info(f"Confirmed textarea for question '{question_text}' is correct.")
                                else:
                                    logger.warning(f"Textarea for question '{question_text}' is incorrect. Expected: {question_text}, Found: {filled_value}")
                                continue
                                
                            # Radio buttons or checkboxes
                            # Find the label with the text that matches our answer
                            safe_answer = question_text.replace("'", "\\'")
                            answer_label = await question_container.query_selector(f"//label[contains(text(), '{safe_answer}')]")
                            if answer_label:
                                await answer_label.click()
                                logger.info(f"Clicked answer for question '{question_text}': {question_text}")
                                continue
                except Exception as e:
                    logger.warning(f"Failed to fill field for question '{question_text}': {str(e)}")
            
            # Find and click the submit button
            try:
                submit_button = await page.query_selector("//button[contains(text(), 'Submit')]")
                if submit_button:
                    await submit_button.click()
                    
                    # Wait for confirmation
                    try:
                        # Wait for a success message
                        await page.wait_for_selector("//div[contains(text(), 'Application submitted')]", timeout=10000)
                        result['success'] = True
                        result['message'] = 'Application submitted successfully'
                    except:
                        result['message'] = 'Submission may have failed, no confirmation element found'
                else:
                    result['message'] = 'Could not find submit button'
            except Exception as e:
                result['message'] = f'Could not submit application: {str(e)}'
            
            await browser.close()
            
        except Exception as e:
            logger.error(f"Error submitting application: {str(e)}")
            result['message'] = f'Error: {str(e)}'
    
    return result

def submit_application(job_id: str, user: User, responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper for the async submit_application_async function
    """
    return asyncio.run(submit_application_async(job_id, user, responses))
