import logging
import os
import abc
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import random
from playwright.async_api import Page
from application_filler.utils.click_utils import click_accept_or_apply_buttons

logger = logging.getLogger(__name__)

class BaseApplicationFiller(abc.ABC):
    """
    Abstract base class for application fillers that defines
    the common interface and shared functionality.
    """
    
    def __init__(self, user_data: Dict[str, Any], job_url: str):
        """
        Initialize the base application filler.
        
        Args:
            user_data: Dictionary containing user profile information
            job_url: URL of the job application
        """
        self.user_data = user_data
        self.job_url = job_url
        self.response_delay_min = 0.5  # Minimum delay between field inputs (seconds)
        self.response_delay_max = 2.0  # Maximum delay between field inputs (seconds)
    
    async def parse_application_page(self, page: Page) -> List[Dict[str, Any]]:
        """
        Parse the job application page and extract all questions.
        
        Args:
            page: The Playwright page object
        
        Returns:
            A list of extracted questions with their types
        """
        questions = []
        try:
            # Look for form elements and question containers
            selectors = [
                "form label", 
                "div[role='form'] label", 
                "label.form-label", 
                ".form-group label",
                ".field-label"
            ]
            
            for selector in selectors:
                label_elements = await page.query_selector_all(selector)
                if label_elements:
                    logger.info(f"Found {len(label_elements)} potential question elements with selector: {selector}")
                    
                    for label_element in label_elements:
                        question_text = await label_element.inner_text()
                        question_text = question_text.strip()
                        
                        # Skip empty or very short labels
                        if not question_text or len(question_text) < 2:
                            continue
                            
                        # Exclude standard fields (determined more robustly in implementation classes)
                        standard_fields = ["name", "email", "phone", "resume", "linkedin"]
                        if any(field in question_text.lower() for field in standard_fields):
                            logger.debug(f"Skipping standard field: {question_text}")
                            continue
                        
                        logger.debug(f"Detected question label: {question_text}")
                        
                        # Default question type is text, but subclasses should determine better
                        question_type = "text"
                        
                        questions.append({
                            "text": question_text,
                            "type": question_type,
                            "element": label_element  # For mapping to input elements later
                        })
                    break  # If we found any labels with this selector, stop trying others
            
            # If we didn't find any questions with label elements, try input elements directly
            if not questions:
                logger.info("No questions found with label elements. Trying input elements.")
                input_elements = await page.query_selector_all("input:visible, textarea:visible, select:visible")
                
                for input_element in input_elements:
                    placeholder = await input_element.get_attribute("placeholder") or ""
                    name = await input_element.get_attribute("name") or ""
                    id_attr = await input_element.get_attribute("id") or ""
                    
                    # Try to get text from the input's attributes
                    question_text = placeholder or name or id_attr
                    if not question_text:
                        continue
                        
                    # Skip standard fields
                    standard_fields = ["name", "email", "phone", "resume", "linkedin"]
                    if any(field in question_text.lower() for field in standard_fields):
                        continue
                    
                    input_type = await input_element.get_attribute("type") or "text"
                    
                    questions.append({
                        "text": question_text,
                        "type": input_type,
                        "element": input_element
                    })
                
        except Exception as e:
            logger.error(f"Error parsing application page: {str(e)}")
            
        return questions
    
    @abc.abstractmethod
    async def map_question_to_response(self, question: Dict[str, Any]) -> Tuple[str, str]:
        """
        Map a question to a response based on the user profile.
        
        Args:
            question: Question dictionary with 'text' and 'type' keys
            
        Returns:
            Tuple of (field_name, response_text)
        """
        pass
    
    async def fill_application_field(self, page: Page, field_selector: str, response_text: str) -> bool:
        """
        Fill out a single application field with the given text.
        
        Args:
            page: The Playwright page object
            field_selector: CSS selector for the field
            response_text: The text to fill in the field
            
        Returns:
            True if the field was successfully filled, False otherwise
        """
        try:
            # Check if selector exists on the page
            field_element = await page.query_selector(field_selector)
            if not field_element:
                logger.warning(f"Field not found with selector: {field_selector}")
                return False
                
            # Check if it's visible
            is_visible = await field_element.is_visible()
            if not is_visible:
                logger.warning(f"Field not visible: {field_selector}")
                return False
            
            # Get the element type and attribute values
            tag_name = await field_element.evaluate("el => el.tagName.toLowerCase()")
            element_type = await field_element.get_attribute("type") or ""
            
            # Scroll field into view before focusing
            await page.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})", field_element)
            # Apply human-like behavior: focus on the field first
            await field_element.focus()
            # Highlight the field for visual feedback
            await page.evaluate("(el) => { el.style.border = '2px solid green'; el.style.backgroundColor = '#e0ffe0'; }", field_element)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Process based on element type
            if tag_name == "textarea" or (tag_name == "input" and element_type in ["text", "email", "tel", "url", ""]):
                # Clear the field first (if it has a value)
                current_value = await field_element.input_value()
                if current_value:
                    await field_element.fill("")
                    await asyncio.sleep(0.2)
                
                # Fill the field with the response text
                await field_element.type(response_text, delay=random.uniform(50, 150))
                logger.info(f"Filled {tag_name} field with: {response_text[:30]}...")
                
            elif tag_name == "select":
                # Try to select an option by text or value
                try:
                    await field_element.select_option(label=response_text)
                except:
                    try:
                        await field_element.select_option(value=response_text)
                    except:
                        # Try to pick any option as a fallback
                        options = await field_element.evaluate("el => Array.from(el.options).map(o => o.value)")
                        if options:
                            await field_element.select_option(value=options[0])
                            logger.info(f"Selected first option for select field (fallback)")
                        else:
                            logger.warning(f"No options found for select field")
                            return False
                            
            elif tag_name == "input" and element_type in ["radio", "checkbox"]:
                if element_type == "radio":
                    # For radio buttons, check if the value matches
                    value = await field_element.get_attribute("value") or ""
                    label_text = await page.evaluate("""
                        (radio) => {
                            const id = radio.id;
                            if (id) {
                                const label = document.querySelector(`label[for="${id}"]`);
                                return label ? label.textContent.trim() : "";
                            }
                            return "";
                        }
                    """, field_element)
                    
                    if response_text.lower() in value.lower() or response_text.lower() in label_text.lower():
                        await field_element.check()
                        logger.info(f"Checked radio button with value/label matching: {response_text}")
                    else:
                        logger.warning(f"Radio value/label doesn't match response: {value}/{label_text} vs {response_text}")
                        return False
                else:  # checkbox
                    # For checkboxes, check if response is truthy/positive
                    if response_text.lower() in ["yes", "true", "1", "on", "check"]:
                        await field_element.check()
                        logger.info(f"Checked checkbox based on positive response: {response_text}")
                    else:
                        await field_element.uncheck()
                        logger.info(f"Unchecked checkbox based on negative response: {response_text}")
            else:
                logger.warning(f"Unsupported field type: {tag_name}/{element_type}")
                return False
                
            # Simulate pressing Tab to move to the next field
            await field_element.press("Tab")
            
            # Add some delay between fields to simulate human interaction
            await asyncio.sleep(random.uniform(self.response_delay_min, self.response_delay_max))
            return True
            
        except Exception as e:
            logger.error(f"Error filling field ({field_selector}): {str(e)}")
            return False
    
    async def handle_resume_upload(self, page: Page) -> bool:
        """
        Handle the upload of the resume if a file input is present.
        
        Args:
            page: The Playwright page object
            
        Returns:
            True if resume was uploaded successfully, False otherwise
        """
        resume_path = self.user_data.get('resume_file_path')
        if not resume_path or not os.path.exists(resume_path):
            logger.warning(f"Resume file not found at: {resume_path}")
            return False
            
        try:
            # Look for file input elements with various selectors
            file_selectors = [
                'input[type="file"]',
                'input[accept=".pdf,.doc,.docx"]',
                'input[name*="resume"]',
                'input[name*="cv"]'
            ]
            
            for selector in file_selectors:
                file_input = await page.query_selector(selector)
                if file_input:
                    # Check if it's visible or can be interacted with
                    try:
                        await file_input.wait_for_element_state('attached', timeout=1000)
                        logger.info(f"Found file input element with selector: {selector}")
                        
                        # Upload the resume file
                        await file_input.set_input_files(resume_path)
                        logger.info(f"Uploaded resume from: {resume_path}")
                        
                        # Wait for upload to complete
                        await asyncio.sleep(2)
                        return True
                    except Exception as e:
                        logger.warning(f"File input found but couldn't interact with it: {str(e)}")
            
            logger.warning("No file input element found for resume upload")
            return False
            
        except Exception as e:
            logger.error(f"Error uploading resume: {str(e)}")
            return False

    @abc.abstractmethod
    async def fill_application_form(self, page: Page) -> bool:
        """
        Fill the entire job application form.
        
        Args:
            page: The Playwright page object
            
        Returns:
            True if the form was successfully filled, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def fill_application(self, browser_context=None) -> Dict[str, Any]:
        """
        Main method to fill an application, including browser management.
        
        Args:
            browser_context: Optional existing browser context to use
            
        Returns:
            Dictionary with application status and details
        """
        pass
