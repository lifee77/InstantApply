import logging
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from models.user import User
import time

logger = logging.getLogger(__name__)

def submit_application(job_id: str, user: User, responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit a job application using Selenium
    
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
    
    try:
        # Setup Chrome browser
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # Navigate to the application page
        driver.get(f"https://www.indeed.com/viewjob?jk={job_id}&apply=1")
        
        # Wait for application form to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        
        # Fill out personal information
        try:
            # Name fields
            name_input = driver.find_element(By.ID, "input-applicant.name")
            if name_input:
                name_input.send_keys(user.name)
            
            # Email field
            email_input = driver.find_element(By.ID, "input-applicant.email")
            if email_input:
                email_input.send_keys(user.email)
            
            # Resume upload (this would be more complex in a real implementation)
            # We'd need to handle file uploads which might require additional logic
        except Exception as e:
            logger.warning(f"Standard fields not found: {str(e)}")
        
        # Process each question based on the responses
        for question_text, answer in responses.items():
            try:
                # Find question element by label text
                question_label = driver.find_element(By.XPATH, f"//label[contains(text(), '{question_text}')]")
                question_container = question_label.find_element(By.XPATH, "./..")
                
                # Handle different input types
                try:
                    # Text input
                    input_field = question_container.find_element(By.TAG_NAME, "input")
                    input_field.send_keys(answer)
                except:
                    try:
                        # Textarea
                        textarea = question_container.find_element(By.TAG_NAME, "textarea")
                        textarea.send_keys(answer)
                    except:
                        try:
                            # Radio buttons or checkboxes
                            options = question_container.find_elements(By.XPATH, f".//label[contains(text(), '{answer}')]")
                            if options:
                                # Click the matching option
                                options[0].click()
                        except Exception as e:
                            logger.warning(f"Failed to fill field for question '{question_text}': {str(e)}")
            except Exception as e:
                logger.warning(f"Question not found: {question_text}, {str(e)}")
        
        # Find and click the submit button
        try:
            submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
            submit_button.click()
            
            # Wait for confirmation
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Application submitted')]"))
                )
                result['success'] = True
                result['message'] = 'Application submitted successfully'
            except:
                result['message'] = 'Submission may have failed, no confirmation element found'
        except Exception as e:
            result['message'] = f'Could not submit application: {str(e)}'
        
        driver.quit()
        
    except Exception as e:
        logger.error(f"Error submitting application: {str(e)}")
        result['message'] = f'Error: {str(e)}'
    
    return result
