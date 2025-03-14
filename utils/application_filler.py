import logging
from typing import Dict, Any, List
import openai
from flask import current_app
from models.user import User
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

def extract_application_questions(job_id: str) -> List[Dict[str, Any]]:
    """
    Extract application questions from a job posting
    
    Args:
        job_id: The Indeed job ID
        
    Returns:
        List of question dictionaries
    """
    questions = []
    
    try:
        # Setup headless Chrome browser
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
        
        # Find all question fields
        form_elements = driver.find_elements(By.CSS_SELECTOR, "div.ia-Questions-item")
        
        for element in form_elements:
            question_text = element.find_element(By.CSS_SELECTOR, "label").text.strip()
            
            # Determine question type
            input_element = None
            question_type = "text"
            
            try:
                # Check for text input
                input_element = element.find_element(By.CSS_SELECTOR, "input[type='text']")
                question_type = "text"
            except:
                try:
                    # Check for textarea
                    input_element = element.find_element(By.CSS_SELECTOR, "textarea")
                    question_type = "textarea"
                except:
                    try:
                        # Check for radio buttons
                        input_element = element.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        question_type = "radio"
                    except:
                        try:
                            # Check for checkboxes
                            input_element = element.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                            question_type = "checkbox"
                        except:
                            # If no input element is found, skip this question
                            continue
            
            # Add question to list
            question = {
                "text": question_text,
                "type": question_type
            }
            
            # For radio/checkbox, get options
            if question_type in ["radio", "checkbox"] and isinstance(input_element, list):
                options = []
                for option in input_element:
                    label = option.find_element(By.XPATH, "following-sibling::label")
                    options.append(label.text.strip())
                question["options"] = options
                
            questions.append(question)
        
        driver.quit()
        
    except Exception as e:
        logger.error(f"Error extracting application questions: {str(e)}")
    
    return questions

def generate_application_responses(job_id: str, user: User) -> Dict[str, Any]:
    """
    Generate responses to job application questions using AI
    
    Args:
        job_id: The Indeed job ID
        user: User object with profile information
        
    Returns:
        Dictionary of question responses
    """
    # Set OpenAI API key
    openai.api_key = current_app.config.get('OPENAI_API_KEY')
    
    # Extract questions from job application
    questions = extract_application_questions(job_id)
    
    # Prepare responses
    responses = {}
    
    try:
        # For each question, generate a response using AI
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
            
            # Get response from OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert job application assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Format response based on question type
            if question_type in ["text", "textarea"]:
                responses[question_text] = answer
            elif question_type in ["radio", "checkbox"]:
                # For multiple choice questions, select the best option
                options = question.get("options", [])
                if options:
                    # Ask AI to choose the best option from the available options
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
                    
                    option_response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are an expert job application assistant."},
                            {"role": "user", "content": option_prompt}
                        ]
                    )
                    
                    chosen_option = option_response.choices[0].message.content.strip()
                    responses[question_text] = chosen_option
    
    except Exception as e:
        logger.error(f"Error generating application responses: {str(e)}")
    
    return responses
