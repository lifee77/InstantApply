"""
Module for parsing and filling application forms
"""
import logging
import asyncio
import random
from typing import Dict, Any, List
from playwright.async_api import Page

from .utils import save_full_page_screenshot
from .response_generator import ResponseGenerator

logger = logging.getLogger(__name__)

class FormFiller:
    """Class for parsing and filling application forms"""
    
    def __init__(self, response_generator: ResponseGenerator):
        """
        Initialize the form filler
        
        Args:
            response_generator: ResponseGenerator instance for generating answers
        """
        self.response_generator = response_generator
        self.failed_fields = []
        self.max_retries = 3
    
    async def parse_application_page(self, page: Page) -> list:
        """
        Parse the job application page and extract all questions.

        Args:
            page: The Playwright page object

        Returns:
            A list of extracted questions
        """
        questions = []
        
        # Take a screenshot before parsing starts
        await save_full_page_screenshot(page, "before_parsing_page")
        
        try:
            # Look for form fields directly rather than just labels
            logger.info("Searching for form input fields...")
            
            # First, look for all input fields, textareas and select dropdowns
            form_fields = await page.query_selector_all('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select')
            
            logger.info(f"Found {len(form_fields)} potential form fields")
            
            for field in form_fields:
                try:
                    field_type = await field.get_attribute('type') or 'text'
                    field_name = await field.get_attribute('name') or ''
                    field_id = await field.get_attribute('id') or ''
                    field_placeholder = await field.get_attribute('placeholder') or ''
                    
                    # Skip basic fields - these are handled separately
                    if any(keyword in field_name.lower() or keyword in field_type.lower() or keyword in field_id.lower() 
                           for keyword in ['email', 'name', 'first', 'last', 'phone', 'resume', 'file', 'password', 'login', 'submit', 'button']):
                        logger.debug(f"Skipping field: {field_name or field_id} (standard field)")
                        continue
                    
                    # Try to find associated label
                    question_text = ""
                    
                    # First check if we can find a label with a 'for' attribute matching this field's ID
                    if field_id:
                        label = await page.query_selector(f'label[for="{field_id}"]')
                        if label:
                            question_text = await label.inner_text()
                    
                    # If no label was found, try looking for enclosing labels or nearby text
                    if not question_text and field_name:
                        # Try to find text elements near this field
                        label_candidates = await page.query_selector_all(f'label, div, p, span')
                        for candidate in label_candidates:
                            candidate_text = await candidate.inner_text()
                            if field_name.lower() in candidate_text.lower() or field_name.replace('_', ' ').lower() in candidate_text.lower():
                                question_text = candidate_text
                                break
                    
                    # Use placeholder text if no label was found
                    if not question_text and field_placeholder:
                        question_text = field_placeholder
                        
                    # Use field name as fallback if still no question text
                    if not question_text:
                        question_text = field_name.replace('_', ' ').capitalize()
                    
                    # Clean up the question text
                    question_text = question_text.strip()
                    if question_text.endswith(':'):
                        question_text = question_text[:-1]
                        
                    if question_text:
                        logger.info(f"Found form field: '{question_text}' (Type: {field_type}, ID: {field_id or 'none'}, Name: {field_name or 'none'})")
                        questions.append({
                            "text": question_text,
                            "type": field_type,
                            "element_id": field_id,
                            "name": field_name,
                            "field": field
                        })
                except Exception as field_error:
                    logger.error(f"Error processing field: {str(field_error)}")
        except Exception as e:
            logger.error(f"Error parsing application page: {str(e)}")
            
        # Only use default questions if we're testing with a dummy URL
        if not questions and ('sample_job_id' in page.url or 'example.com' in page.url):
            logger.warning("No questions found and using test URL, using default questions")
            questions = [
                {"text": "What is your greatest strength?", "type": "text"},
                {"text": "Why do you want to work here?", "type": "text"},
            ]
        elif not questions:
            # For real applications, just log that no fields were found
            logger.warning("No fillable form fields were detected on this page")
            
        return questions

    async def fill_application_field(self, page: Page, question: dict, user_response: str, retry_count=0):
        """
        Fill out a single application field based on the extracted question and user profile data.
        
        Args:
            page: The Playwright page object
            question: Dictionary with question text and type
            user_response: The user's response to the question
            retry_count: Current retry attempt count
            
        Returns:
            bool: True if field was filled successfully
        """
        question_text = question["text"]
        question_type = question.get("type", "text")
        element_id = question.get("element_id")
        
        if retry_count > self.max_retries:
            logger.error(f"Max retries exceeded for question '{question_text}'")
            self.failed_fields.append(question_text)
            return False
            
        try:
            # Debug screenshot before attempting to fill field
            debug_path = f"/tmp/before_fill_{int(time.time())}.png"
            await page.screenshot(path=debug_path)
            logger.info(f"Debug screenshot saved to {debug_path}")
            
            # First try by id if available
            if element_id:
                selector = f"#{element_id}"
                logger.info(f"Using ID selector: {selector}")
                
                # Direct fill approach for ID-based elements
                try:
                    await page.fill(selector, user_response)
                    logger.info(f"Filled field with ID '{element_id}' using direct fill")
                    return True
                except Exception as e:
                    logger.warning(f"Direct fill failed, trying alternative methods: {str(e)}")
            else:
                # Try multiple selector strategies - improved for better detection
                selectors = [
                    f'input[placeholder*="{question_text}"], textarea[placeholder*="{question_text}"]',
                    f'label:has-text("{question_text}") + input, label:has-text("{question_text}") + textarea',
                    f'div:has-text("{question_text}") input, div:has-text("{question_text}") textarea',
                    f'input[name*="{question_text.lower().replace(" ", "_")}"], textarea[name*="{question_text.lower().replace(" ", "_")}"]',
                    'form input[type="text"]:visible, form textarea:visible'  # Fallback to any visible text input
                ]
                
                # Try each selector until one works
                found_element = None
                working_selector = None
                
                for selector in selectors:
                    logger.info(f"Trying selector: {selector}")
                    try:
                        found_element = await page.query_selector(selector)
                        if found_element:
                            logger.info(f"Found element with selector: {selector}")
                            working_selector = selector
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {str(e)}")
                
                if found_element and working_selector:
                    # Try direct fill first
                    try:
                        await found_element.fill(user_response)
                        logger.info(f"Filled using element.fill() method")
                        return True
                    except Exception as e:
                        logger.warning(f"Element.fill() failed: {str(e)}, trying JavaScript")
                        selector = working_selector
                else:
                    # If all selectors fail, try a more generic approach
                    logger.warning(f"No element found for question '{question_text}'. Using fallback approach.")
                    try:
                        # Just find any input or textarea
                        selector = 'input[type="text"], textarea'
                        found_element = await page.query_selector(selector)
                        if not found_element:
                            raise Exception("No input elements found")
                    except Exception as e:
                        logger.error(f"Failed to find any input element: {str(e)}")
                        self.failed_fields.append(question_text)
                        return False
            
            if not user_response:
                logger.warning(f"No response available for question '{question_text}'.")
                return False
            
            # Use JavaScript evaluation with correct syntax (only 2 arguments: js_code and selector+value object)
            await page.evaluate("""
                (args) => {
                    const elements = document.querySelectorAll(args.selector);
                    if (elements.length > 0) {
                        const element = elements[0];
                        element.value = args.value;
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                }
            """, {"selector": selector, "value": user_response})
            
            logger.info(f"Filled field for '{question_text}' with response starting: {user_response[:30]}...")
            
            # Add a randomized delay to appear more human-like
            delay_time = random.uniform(1.5, 3.5)
            await asyncio.sleep(delay_time)
            return True
            
        except Exception as e:
            logger.error(f"Error filling field for question '{question_text}': {str(e)}")
            
            # Take screenshot of the issue
            error_screenshot = f"/tmp/error_fill_{int(time.time())}.png"
            try:
                await page.screenshot(path=error_screenshot)
                logger.info(f"Error screenshot saved to {error_screenshot}")
            except Exception as screenshot_e:
                logger.warning(f"Failed to take error screenshot: {str(screenshot_e)}")
            
            # Retry with increased delay
            if retry_count < self.max_retries:
                logger.info(f"Retrying field '{question_text}' (Attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(2 + retry_count)  # Increasing delay with each retry
                return await self.fill_application_field(page, question, user_response, retry_count + 1)
            else:
                self.failed_fields.append(question_text)
                return False

    async def fill_application_form(self, page: Page):
        """
        Fill the job application form using user profile data.

        Args:
            page: The Playwright page object
            
        Returns:
            Dictionary with success status and list of any failed fields
        """
        logger.info(f"Starting form fill for job URL: {page.url}")
        
        # Reset failed fields tracking
        self.failed_fields = []
        
        # First extract questions from the page
        questions = await self.parse_application_page(page)
        logger.info(f"Found {len(questions)} questions to fill")
        
        # Fill each question's field
        for i, question in enumerate(questions):
            logger.info(f"Processing question {i+1}/{len(questions)}: {question['text']}")
            
            # Generate response for this question
            response = self.response_generator.generate_response(question["text"])
            
            # Fill the field with the generated response
            await self.fill_application_field(page, question, response)
        
        # Return success status and any failures
        success = len(self.failed_fields) == 0
        return {
            "success": success,
            "total_questions": len(questions),
            "failed_fields": self.failed_fields
        }

    async def fill_basic_fields(self, page: Page, user_data: Dict[str, Any]):
        """
        Fill in the basic identifier fields (name, email, phone) that are common in most forms
        
        Args:
            page: The Playwright page object
            user_data: Dictionary with user profile information
            
        Returns:
            bool: True if any fields were filled
        """
        # Look for common basic fields that may be required
        basic_fields = [
            {'selector': 'input[name*="name"], input[placeholder*="name"]', 'value': user_data.get('name', '')},
            {'selector': 'input[type="email"], input[name*="email"], input[placeholder*="email"]', 'value': user_data.get('email', '')},
            {'selector': 'input[name*="phone"], input[placeholder*="phone"], input[type="tel"]', 'value': user_data.get('phone', '')},
            {'selector': 'input[name*="linkedin"], input[placeholder*="linkedin"]', 'value': user_data.get('portfolio_links', '')},
        ]
        
        filled_count = 0
        for field in basic_fields:
            if field['value']:  # Only try to fill if we have a value
                try:
                    elements = await page.query_selector_all(field['selector'])
                    for elem in elements:
                        is_visible = await elem.is_visible()
                        if is_visible:
                            await elem.fill(field['value'])
                            logger.info(f"Filled basic field: {field['selector']} with value: {field['value']}")
                            filled_count += 1
                            break
                except Exception as e:
                    logger.debug(f"Error filling basic field {field['selector']}: {str(e)}")
        
        # Wait a bit after filling basic fields
        if filled_count > 0:
            await asyncio.sleep(2)
            return True
        return False