import logging
import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright, Playwright
from models.user import User
import time

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
                
                # Email field
                email_input = await page.query_selector("#input-applicant\\.email")
                if email_input:
                    await email_input.fill(user.email)
                
                # Resume upload (this would be more complex in a real implementation)
                # We'd need to handle file uploads which might require additional logic
            except Exception as e:
                logger.warning(f"Standard fields not found: {str(e)}")
            
            # Process each question based on the responses
            for question_text, answer in responses.items():
                try:
                    # Find question element by label text
                    # Escape single quotes in the XPath expression
                    safe_question_text = question_text.replace("'", "\\'")
                    question_label = await page.query_selector(f"//label[contains(text(), '{safe_question_text}')]")
                    
                    if question_label:
                        # Go up one level to the container
                        question_container_handle = await question_label.evaluate("node => node.parentElement")
                        question_container = await page.query_selector(f"xpath=//div[@id='{question_container_handle.id}']")
                        
                        if question_container:
                            # Handle different input types
                            # Text input
                            text_input = await question_container.query_selector("input[type='text']")
                            if text_input:
                                await text_input.fill(answer)
                                continue
                                
                            # Textarea
                            textarea = await question_container.query_selector("textarea")
                            if textarea:
                                await textarea.fill(answer)
                                continue
                                
                            # Radio buttons or checkboxes
                            # Find the label with the text that matches our answer
                            safe_answer = answer.replace("'", "\\'")
                            answer_label = await question_container.query_selector(f"//label[contains(text(), '{safe_answer}')]")
                            if answer_label:
                                await answer_label.click()
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
