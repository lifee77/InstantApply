"""
Application Filler module for automatically filling out job applications
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from .utils import valid_url, extract_job_id, save_full_page_screenshot
from .form_detector import (
    detect_form_type, 
    find_apply_button,
    find_next_button,
    find_submit_button
)
from .mappers.field_mapper import map_question_to_field

logger = logging.getLogger(__name__)

# Add missing functions
async def extract_application_questions_async(job_id: str, page: Page) -> List[Dict[str, Any]]:
    """
    Extract application questions from a job application page
    
    Args:
        job_id: The ID of the job
        page: The playwright page object
        
    Returns:
        List of dictionaries containing question text and type
    """
    logger.info(f"Extracting application questions for job {job_id}")
    
    questions = []
    
    try:
        # Get all form elements that could be questions
        form_elements = await page.evaluate('''() => {
            const questions = [];
            
            // Find all input fields, textareas and select elements
            const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"])'));
            const textareas = Array.from(document.querySelectorAll('textarea'));
            const selects = Array.from(document.querySelectorAll('select'));
            
            const getLabel = (element) => {
                // Try to find an associated label
                const id = element.id;
                if (id) {
                    const label = document.querySelector(`label[for="${id}"]`);
                    if (label) return label.textContent.trim();
                }
                
                // Check for aria-label
                const ariaLabel = element.getAttribute('aria-label');
                if (ariaLabel) return ariaLabel;
                
                // Check for placeholder
                const placeholder = element.getAttribute('placeholder');
                if (placeholder) return placeholder;
                
                // Check for parent label
                let parent = element.parentElement;
                for (let i = 0; i < 3 && parent; i++) {
                    const label = parent.querySelector('label');
                    if (label) return label.textContent.trim();
                    
                    // Check for header-like elements
                    const header = parent.querySelector('h1, h2, h3, h4, h5, h6, .field-label, .form-label, .question-label');
                    if (header) return header.textContent.trim();
                    
                    // Check text nodes directly in parent
                    if (parent.childNodes.length > 0) {
                        for (const child of parent.childNodes) {
                            if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
                                return child.textContent.trim();
                            }
                        }
                    }
                    
                    parent = parent.parentElement;
                }
                
                // Use name or id as fallback
                return element.name || element.id || null;
            };
            
            // Process inputs
            inputs.forEach(input => {
                const type = input.type;
                const label = getLabel(input);
                
                if (label) {
                    questions.push({
                        element_id: input.id || input.name,
                        text: label,
                        type: type === 'number' ? 'integer' : 'text',
                        required: input.required
                    });
                }
            });
            
            // Process textareas
            textareas.forEach(textarea => {
                const label = getLabel(textarea);
                
                if (label) {
                    questions.push({
                        element_id: textarea.id || textarea.name,
                        text: label,
                        type: 'text',
                        required: textarea.required
                    });
                }
            });
            
            // Process selects
            selects.forEach(select => {
                const label = getLabel(select);
                
                if (label) {
                    questions.push({
                        element_id: select.id || select.name,
                        text: label,
                        type: 'select',
                        required: select.required,
                        options: Array.from(select.options).map(opt => opt.text)
                    });
                }
            });
            
            return questions;
        }''')
        
        # Filter and clean up questions
        for question in form_elements:
            # Skip empty or likely non-question texts
            if not question.get('text') or len(question.get('text', '')) < 3:
                continue
                
            # Skip common non-question elements
            text = question.get('text', '').lower()
            if any(skip in text for skip in ['submit', 'cancel', 'password', 'login', 'forgot']):
                continue
                
            questions.append({
                'text': question.get('text'),
                'type': question.get('type', 'text'),
                'options': question.get('options', []),
                'required': question.get('required', False)
            })
        
        logger.info(f"Extracted {len(questions)} questions")
        return questions
        
    except Exception as e:
        logger.error(f"Error extracting questions: {str(e)}")
        return []

def generate_application_responses(questions: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate responses for application questions based on user profile
    
    Args:
        questions: List of extracted questions
        user_profile: User profile data
        
    Returns:
        Dictionary mapping question text to response text
    """
    logger.info(f"Generating responses for {len(questions)} questions")
    
    responses = {}
    
    for question in questions:
        question_text = question.get('text', '')
        question_type = question.get('type', 'text')
        
        # Skip empty questions
        if not question_text:
            continue
            
        # Map question to profile field
        field_name = map_question_to_field(question_text)
        
        # Generate response based on question type and available profile data
        if field_name and field_name in user_profile:
            # Direct mapping to user profile field
            responses[question_text] = str(user_profile[field_name])
            logger.debug(f"Mapped question '{question_text}' to user data: '{field_name}'")
        else:
            # Handle common question types
            question_lower = question_text.lower()
            
            if 'name' in question_lower:
                responses[question_text] = user_profile.get('name', '')
            elif 'email' in question_lower:
                responses[question_text] = user_profile.get('email', '')
            elif 'phone' in question_lower:
                responses[question_text] = user_profile.get('phone', '')
            elif 'address' in question_lower:
                responses[question_text] = user_profile.get('address', '')
            elif 'linkedin' in question_lower:
                responses[question_text] = user_profile.get('linkedin_url', '')
            elif 'salary' in question_lower or 'compensation' in question_lower:
                responses[question_text] = user_profile.get('salary_expectation', 'Competitive')
            elif 'start date' in question_lower or 'available' in question_lower:
                responses[question_text] = user_profile.get('start_date', 'Immediately')
            elif 'relocate' in question_lower:
                responses[question_text] = user_profile.get('willing_to_relocate', 'Yes')
            elif 'visa' in question_lower or 'authorized' in question_lower or 'sponsor' in question_lower:
                responses[question_text] = user_profile.get('work_authorization', 'Yes, I am authorized to work in the US')
            elif 'experience' in question_lower and question_type == 'integer':
                # Try to extract years of experience for specific skills
                skill_words = question_lower.split()
                for skill in ['python', 'javascript', 'typescript', 'react', 'node', 'java', 'c++', 'ruby']:
                    if skill in skill_words:
                        responses[question_text] = user_profile.get(f'{skill}_years', '2')
                        break
                if question_text not in responses:
                    responses[question_text] = user_profile.get('total_years_experience', '5')
            elif 'why' in question_lower and 'join' in question_lower:
                responses[question_text] = user_profile.get('why_join', 
                    "I'm excited about this role because it aligns perfectly with my skills and career aspirations. "
                    "I'm particularly drawn to the company's innovative approach and the opportunity to make a meaningful impact.")
    
    logger.info(f"Generated {len(responses)} responses")
    return responses

def setup_gemini():
    """
    Set up the Gemini API client for AI assistance
    
    Returns:
        Gemini API client or None if setup fails
    """
    try:
        import google.generativeai as genai
        from google.api_core.exceptions import InvalidArgument
        
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not set")
            return None
            
        genai.configure(api_key=api_key)
        
        # Test that the API key works
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Hello, World!")
            logger.info("Gemini API setup successful")
            return model
        except (InvalidArgument, Exception) as e:
            logger.error(f"Failed to initialize Gemini API: {str(e)}")
            return None
    except ImportError:
        logger.error("google.generativeai package not installed")
        return None
    except Exception as e:
        logger.error(f"Unexpected error setting up Gemini: {str(e)}")
        return None

class ApplicationFiller:
    """Main class for filling out job applications automatically"""
    
    def __init__(self, user, job_url: str = None, headless: bool = False):
        """
        Initialize the application filler
        
        Args:
            user: User object with profile information
            job_url: URL of the job to apply to
            headless: Whether to run the browser in headless mode (default: False to show browser)
        """
        self.user = user
        self.job_url = job_url
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        
    async def _setup_browser(self) -> None:
        """Set up the playwright browser instance"""
        playwright = await async_playwright().start()
        # Adding slow_mo to make actions more visible
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            slow_mo=50  # Add a small delay between actions for visibility
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        )
        self.page = await self.context.new_page()
        
        # Add debugging event handlers
        self.page.on("console", lambda msg: logger.debug(f"Browser console: {msg.text}"))
        self.page.on("pageerror", lambda err: logger.error(f"Browser error: {err}"))
    
    async def _close_browser(self) -> None:
        """Close the browser and clean up"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
    
    async def fill_application(self) -> Dict[str, Any]:
        """
        Main method to fill out a job application
        
        Returns:
            Dictionary with result status and details
        """
        if not valid_url(self.job_url):
            return {"success": False, "message": "Invalid job URL"}
        
        try:
            # Set up browser
            await self._setup_browser()
            
            # Navigate to the job posting
            await self.page.goto(self.job_url, wait_until="domcontentloaded")
            await self.page.wait_for_load_state("networkidle")
            
            # Detect form type
            form_type = await detect_form_type(self.page)
            logger.info(f"Detected form type: {form_type}")
            
            # Find and click the apply button
            apply_button = await find_apply_button(self.page)
            if not apply_button:
                return {"success": False, "message": "Could not find apply button"}
            
            await apply_button.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Process application forms
            result = await self._fill_application_forms()
            
            return result
        except Exception as e:
            logger.exception(f"Error filling application: {str(e)}")
            # Take a screenshot of the error state
            screenshot = None
            if self.page:
                screenshot_path, _ = await save_full_page_screenshot(
                    self.page, f"error_{extract_job_id(self.job_url)}")
                screenshot = screenshot_path
            
            return {
                "success": False,
                "message": f"Application failed: {str(e)}",
                "error_details": str(e),
                "screenshot": screenshot,
                "job_url": self.job_url
            }
        finally:
            # Clean up browser
            await self._close_browser()
    
    async def _fill_application_forms(self) -> Dict[str, Any]:
        """Fill out the application forms step by step"""
        steps_completed = 0
        max_steps = 10  # Prevent infinite loops
        
        for step in range(max_steps):
            logger.info(f"Processing application step {step + 1}")
            
            # Take a screenshot for debugging
            screenshot_path, _ = await save_full_page_screenshot(
                self.page, f"step_{step}_{extract_job_id(self.job_url)}")
            
            # Fill out form fields
            await self._fill_current_form()
            
            # Find the next button
            next_button = await find_next_button(self.page)
            
            # If there's no next button, check for submit button
            if not next_button:
                submit_button = await find_submit_button(self.page)
                if submit_button:
                    logger.info("Found submit button, completing application")
                    # If we're in test mode, don't actually submit
                    if os.environ.get("DEBUG_MODE") == "1":
                        logger.info("DEBUG_MODE enabled, skipping final submission")
                        return {
                            "success": True,
                            "message": "Application completed successfully (DEBUG_MODE, not submitted)",
                            "steps_completed": step + 1,
                            "screenshot": screenshot_path,
                            "job_url": self.job_url
                        }
                    
                    # Submit the application
                    await submit_button.click()
                    await self.page.wait_for_load_state("networkidle")
                    steps_completed = step + 1
                    break
                else:
                    # No next or submit button found - we might be done or stuck
                    logger.warning("No next or submit button found")
                    break
            
            # Click next and wait for the next form to load
            await next_button.click()
            await self.page.wait_for_load_state("networkidle")
            steps_completed += 1
        
        # Take a final screenshot
        final_screenshot, _ = await save_full_page_screenshot(
            self.page, f"final_{extract_job_id(self.job_url)}")
        
        if steps_completed >= max_steps:
            return {
                "success": False,
                "message": f"Application process exceeded maximum steps ({max_steps})",
                "steps_completed": steps_completed,
                "screenshot": final_screenshot,
                "job_url": self.job_url
            }
        
        return {
            "success": True,
            "message": "Application completed successfully",
            "steps_completed": steps_completed,
            "screenshot": final_screenshot,
            "job_url": self.job_url
        }
    
    async def _fill_current_form(self) -> None:
        """
        Fill out the current form page with user data
        """
        # Collect all form fields
        input_fields = await self.page.query_selector_all('input:not([type="hidden"]):not([readonly])')
        textareas = await self.page.query_selector_all('textarea:not([readonly])')
        selects = await self.page.query_selector_all('select')
        
        # Process input fields
        for field in input_fields:
            try:
                field_id = await field.get_attribute('id') or ''
                field_name = await field.get_attribute('name') or ''
                field_placeholder = await field.get_attribute('placeholder') or ''
                field_label = await self._find_label_for_field(field)
                field_type = await field.get_attribute('type') or 'text'
                
                # Skip if already filled
                if field_type in ['checkbox', 'radio']:
                    continue  # Handle checkboxes separately
                
                value = await field.input_value()
                if value:
                    logger.debug(f"Field already has value: {field_id or field_name}")
                    continue
                
                # Identify field purpose from attributes
                field_purpose = map_question_to_field(field_label or field_placeholder or field_name or field_id)
                
                # Fill the field if we have matching user data
                await self._fill_field_with_user_data(field, field_purpose, field_type)
                
            except Exception as e:
                logger.error(f"Error processing input field: {str(e)}")
        
        # Process textareas
        for textarea in textareas:
            try:
                field_id = await textarea.get_attribute('id') or ''
                field_name = await textarea.get_attribute('name') or ''
                field_placeholder = await textarea.get_attribute('placeholder') or ''
                field_label = await self._find_label_for_field(textarea)
                
                # Skip if already filled
                value = await textarea.input_value()
                if value:
                    logger.debug(f"Textarea already has value: {field_id or field_name}")
                    continue
                
                # Identify field purpose
                field_purpose = map_question_to_field(field_label or field_placeholder or field_name or field_id)
                
                # Fill the field if we have matching user data
                if field_purpose and hasattr(self.user, field_purpose):
                    user_data = getattr(self.user, field_purpose)
                    if user_data:
                        await textarea.fill(user_data)
                        logger.info(f"Filled textarea '{field_purpose}' with user data")
            except Exception as e:
                logger.error(f"Error processing textarea: {str(e)}")
        
        # Process select fields
        for select in selects:
            try:
                field_id = await select.get_attribute('id') or ''
                field_name = await select.get_attribute('name') or ''
                field_label = await self._find_label_for_field(select)
                
                # Identify field purpose
                field_purpose = map_question_to_field(field_label or field_name or field_id)
                
                # Handle common select fields
                if 'year' in field_id.lower() or 'year' in field_name.lower():
                    # Select most recent year for graduation, etc.
                    await self._select_most_recent_option(select)
                elif 'country' in field_id.lower() or 'country' in field_name.lower():
                    # Try to select user's country
                    country = getattr(self.user, 'country', 'United States')
                    await self._select_option_by_text(select, country)
                elif 'state' in field_id.lower() or 'state' in field_name.lower():
                    # Try to select user's state
                    state = getattr(self.user, 'state', 'California')
                    await self._select_option_by_text(select, state)
                elif 'education' in field_id.lower() or 'degree' in field_name.lower():
                    # Try to select highest education level
                    education = getattr(self.user, 'education_level', "Bachelor's")
                    await self._select_option_containing_text(select, education)
            except Exception as e:
                logger.error(f"Error processing select field: {str(e)}")
    
    async def _find_label_for_field(self, field) -> str:
        """Find the label text for a form field"""
        try:
            # Try to find a label with 'for' attribute matching the field's ID
            field_id = await field.get_attribute('id')
            if field_id:
                label_selector = f'label[for="{field_id}"]'
                label = await self.page.query_selector(label_selector)
                if label:
                    return await label.inner_text()
            
            # Try to find a parent label
            parent_label = await field.evaluate('el => { const label = el.closest("label"); return label ? label.textContent.trim() : null; }')
            if parent_label:
                return parent_label
            
            # Try to find a label-like div near the field
            label_text = await field.evaluate('''
                el => {
                    const findNearestLabelText = (element) => {
                        // Check preceding siblings
                        let sibling = element.previousElementSibling;
                        while (sibling) {
                            if (sibling.tagName === "LABEL" || sibling.tagName === "DIV" || sibling.tagName === "SPAN" || sibling.tagName === "P") {
                                const text = sibling.textContent.trim();
                                if (text) return text;
                            }
                            sibling = sibling.previousElementSibling;
                        }
                        
                        // Check parent and its preceding siblings
                        const parent = element.parentElement;
                        if (parent) {
                            // Check if parent contains label-like text directly
                            const parentText = Array.from(parent.childNodes)
                                .filter(node => node.nodeType === Node.TEXT_NODE)
                                .map(node => node.textContent.trim())
                                .filter(text => text.length > 0)
                                .join(' ');
                            
                            if (parentText) return parentText;
                            
                            // Check parent's previous siblings
                            sibling = parent.previousElementSibling;
                            while (sibling) {
                                if (sibling.tagName === "LABEL" || sibling.tagName === "DIV" || sibling.tagName === "SPAN" || sibling.tagName === "P") {
                                    const text = sibling.textContent.trim();
                                    if (text) return text;
                                }
                                sibling = sibling.previousElementSibling;
                            }
                        }
                        
                        return null;
                    };
                    
                    return findNearestLabelText(el);
                }
            ''')
            if label_text:
                return label_text
            
        except Exception as e:
            logger.error(f"Error finding label for field: {str(e)}")
            
        return ""
    
    async def _fill_field_with_user_data(self, field, field_purpose: str, field_type: str) -> None:
        """Fill a field with appropriate user data based on its purpose"""
        if not field_purpose:
            return
            
        user_value = None
        
        # Map field_purpose to user profile attribute
        if field_purpose == 'name' and hasattr(self.user, 'name'):
            user_value = getattr(self.user, 'name')
        elif field_purpose == 'email' and hasattr(self.user, 'email'):
            user_value = getattr(self.user, 'email')
        elif field_purpose == 'phone' and hasattr(self.user, 'phone'):
            user_value = getattr(self.user, 'phone')
        elif hasattr(self.user, field_purpose):
            user_value = getattr(self.user, field_purpose)
        
        if user_value:
            if field_type == 'file' and hasattr(self.user, 'resume_file_path'):
                # Handle file uploads (resume)
                file_path = getattr(self.user, 'resume_file_path')
                if file_path and os.path.exists(file_path):
                    await field.set_input_files(file_path)
                    logger.info(f"Uploaded file: {file_path}")
            else:
                # Handle regular text input
                await field.fill(str(user_value))
                logger.info(f"Filled field '{field_purpose}' with user data")
    
    async def _select_most_recent_option(self, select) -> None:
        """Select the most recent year option in a select element"""
        try:
            options = await select.query_selector_all('option')
            years = []
            
            # Find all options with years
            for option in options:
                text = await option.inner_text()
                if text.isdigit() and 1900 <= int(text) <= 2030:
                    years.append((int(text), option))
            
            # Sort by year descending and select the most recent
            if years:
                years.sort(reverse=True)
                most_recent_option = years[0][1]
                value = await most_recent_option.get_attribute('value')
                await select.select_option(value=value)
                logger.info(f"Selected most recent year: {years[0][0]}")
        except Exception as e:
            logger.error(f"Error selecting most recent option: {str(e)}")
    
    async def _select_option_by_text(self, select, text: str) -> None:
        """Select an option by exact text match"""
        try:
            options = await select.query_selector_all('option')
            for option in options:
                option_text = await option.inner_text()
                if option_text.lower() == text.lower():
                    value = await option.get_attribute('value')
                    await select.select_option(value=value)
                    logger.info(f"Selected option: {option_text}")
                    return
            
            # If no exact match, try partial match
            await self._select_option_containing_text(select, text)
                
        except Exception as e:
            logger.error(f"Error selecting option by text: {str(e)}")
    
    async def _select_option_containing_text(self, select, text: str) -> None:
        """Select an option containing the given text"""
        try:
            options = await select.query_selector_all('option')
            for option in options:
                option_text = await option.inner_text()
                if text.lower() in option_text.lower():
                    value = await option.get_attribute('value')
                    await select.select_option(value=value)
                    logger.info(f"Selected option containing '{text}': {option_text}")
                    return
        except Exception as e:
            logger.error(f"Error selecting option containing text: {str(e)}")

from .resume_handler import prioritize_resume_upload, handle_resume_upload
from .form_detector import detect_and_handle_form_type, find_and_click_submit_button
from .form_filler import FormFiller
from .response_generator import ResponseGenerator

__all__ = [
    'ApplicationFiller',
    'FormFiller',
    'ResponseGenerator',
    'prioritize_resume_upload',
    'handle_resume_upload',
    'detect_and_handle_form_type',
    'find_and_click_submit_button',
    'extract_application_questions_async',
    'generate_application_responses',
    'setup_gemini'
]