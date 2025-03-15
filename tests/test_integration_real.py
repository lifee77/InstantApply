import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock
from tempfile import NamedTemporaryFile

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from dotenv import load_dotenv
from utils.application_filler import (
    extract_application_questions_async,
    generate_application_responses,
    setup_gemini,
)
from models.user import User

# Load environment variables from .env
load_dotenv()

# Ensure GEMINI_API_KEY is set
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY is not set in your environment.")

# Define the test URL for Playwright (adjust if needed)
TEST_URL = ("https://jobs.ashbyhq.com/replo/ec206174-ccc2-42fa-b295-8201421f21b0/application"
            "?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organic")

async def integration_test():
    async with async_playwright() as p:
        # Try different browser engines in order of preference
        browser = None
        for browser_type in [p.firefox, p.webkit, p.chromium]:
            try:
                print(f"Attempting to launch browser using {browser_type.__class__.__name__}")
                browser = await browser_type.launch(
                    headless=False,
                    slow_mo=100,  # Changed from slowMo to slow_mo for Python naming convention
                    args=["--no-sandbox"] if browser_type == p.chromium else []
                )
                print(f"✅ Successfully launched {browser_type.__class__.__name__}")
                break
            except Exception as e:
                print(f"⚠️ Failed to launch {browser_type.__class__.__name__}: {str(e)}")
                continue
        
        if browser is None:
            print("❌ Failed to launch any browser. Exiting test.")
            return
            
        try:
            # Create a new page with error handling
            try:
                page = await browser.new_page()
                print("✅ New page created")
            except Exception as e:
                print(f"❌ Failed to create new page: {str(e)}")
                await browser.close()
                return
            
            # --- Part 1: Use Playwright to Open a Real Website ---
            try:
                await page.goto(TEST_URL, timeout=60000)  # Increased timeout for slow connections
                print("✅ Opened the website:", TEST_URL)
            except Exception as e:
                print(f"❌ Error navigating to URL: {str(e)}")
                await browser.close()
                return

            # Wait for page load and extract some content
            await page.wait_for_timeout(5000)  
            page_title = await page.title()
            print("✅ Page Title:", page_title)
            
            # --- Part 2: Import and use gemini_caller functions ---
            try:
                from utils.gemini_caller import generate_cover_letter, match_job_description, extract_resume_data
                
                user_data_dict = {
                    "name": "John Doe",
                    "skills": ["Python", "Playwright", "AI"],
                    "experience": ["Software Engineer at ABC", "Developer at XYZ"],
                }
                
                # Generate a sample cover letter
                cover_letter = generate_cover_letter("Software Engineer", "TestCompany", user_data_dict)
                print("\n✅ Generated Cover Letter:")
                print(cover_letter)
                
                # Job description matching
                sample_job_desc = "Looking for a Python developer with AI experience"
                match_result = match_job_description(sample_job_desc, user_data_dict)
                print("\n✅ Job Description Match Result:")
                print(match_result)
                
                # Resume extraction
                sample_resume = "John Doe - Python Developer with 5 years experience in AI and machine learning"
                resume_data = extract_resume_data(sample_resume)
                print("\n✅ Resume Data Extraction:")
                print(resume_data)
                
            except Exception as e:
                print(f"❌ Error in Gemini integration: {str(e)}")
            
            # --- Part 3: Mock ApplicationFiller Integration ---
            dummy_job_id = "dummy_job_id"
            
            # Define mock questions and responses
            mock_questions = [
                {"text": "What is your greatest strength?", "type": "text"}, 
                {"text": "Why do you want to work here?", "type": "text"}
            ]
            
            mock_responses = {
                "What is your greatest strength?": "My greatest strength is my problem-solving ability.",
                "Why do you want to work here?": "I want to work here because I admire your commitment to innovation."
            }
            
            # Use our mocked questions
            with patch('utils.application_filler.extract_application_questions_async', new_callable=AsyncMock) as mock_extract:
                mock_extract.return_value = mock_questions
                questions = await extract_application_questions_async(dummy_job_id)
                print("\n✅ Extracted Application Questions:")
                print(questions)
            
            print("\n✅ Generated Application Responses:")
            print(mock_responses)
            
            # --- Part 4: Simple form interaction ---
            try:
                print("\n--- Attempting to interact with the form ---")
                
                # Try to find visible input fields on the page
                input_fields = await page.query_selector_all('input:visible, textarea:visible')
                if input_fields:
                    print(f"Found {len(input_fields)} visible input fields")
                    
                    # Try to fill the first text input
                    for i, input_field in enumerate(input_fields):  # Remove limit to fill all fields
                        try:
                            input_type = await input_field.get_attribute('type') or 'text'
                            if input_type == 'file':
                                # Skip file inputs
                                continue
                                
                            placeholder = await input_field.get_attribute('placeholder') or ''
                            name = await input_field.get_attribute('name') or ''
                            
                            # Check if it's a visible input we can interact with
                            is_visible = await input_field.is_visible()
                            if not is_visible:
                                continue
                                
                            print(f"Field {i+1}: type={input_type}, placeholder='{placeholder}', name='{name}'")
                            
                            # Focus on the input field to make interaction more visible
                            await input_field.focus()
                            await page.wait_for_timeout(500)  # Small delay for visibility
                            
                            # Fill field with appropriate data based on field hints
                            if 'name' in name.lower() or 'name' in placeholder.lower():
                                value = "John Doe"
                                await input_field.fill(value)
                                print(f"✅ Filled name field with: '{value}'")
                            elif 'email' in name.lower() or 'email' in placeholder.lower():
                                value = "john.doe@example.com"
                                await input_field.fill(value)
                                print(f"✅ Filled email field with: '{value}'")
                            elif 'phone' in name.lower() or 'phone' in placeholder.lower():
                                value = "555-123-4567"
                                await input_field.fill(value)
                                print(f"✅ Filled phone field with: '{value}'")
                            elif 'location' in name.lower() or 'location' in placeholder.lower():
                                value = "New York, NY"
                                await input_field.fill(value)
                                print(f"✅ Filled location field with: '{value}'")
                            else:
                                # For other text fields, use our first mock response
                                response_key = list(mock_responses.keys())[0]
                                value = mock_responses[response_key]
                                await input_field.fill(value)
                                print(f"✅ Filled field '{name or placeholder}' with: '{value}'")
                            
                            # Press Tab to move to next field and trigger any onChange events
                            await input_field.press("Tab")
                            await page.wait_for_timeout(500)  # Small delay for visibility
                                
                        except Exception as e:
                            print(f"❌ Error interacting with field {i+1}: {str(e)}")
                else:
                    print("No visible input fields found on the page")
                    
                # Attempt to upload a resume if a file input is available
                try:
                    file_input = await page.query_selector('input[type="file"]')
                    if file_input:
                        # Create a simple PDF file
                        with NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                            temp_file.write(b"%PDF-1.4\n%Mock Resume")
                            temp_path = temp_file.name
                        
                        await file_input.set_input_files(temp_path)
                        print(f"✅ Uploaded resume file: '{temp_path}'")
                        
                        # Highlight the file upload section
                        await page.evaluate("""() => {
                            const fileInput = document.querySelector('input[type="file"]');
                            if (fileInput && fileInput.parentElement) {
                                fileInput.parentElement.style.border = '2px solid green';
                                fileInput.parentElement.style.padding = '5px';
                            }
                        }""")
                except Exception as e:
                    print(f"❌ Error uploading resume: {str(e)}")

                # Scroll through the page to show all filled fields
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                print("\n✅ Form filling complete - reviewing entered data:")
                
                # Verify what was entered in each field
                all_inputs = await page.query_selector_all('input:not([type="file"]), textarea')
                for i, input_el in enumerate(all_inputs):
                    try:
                        name = await input_el.get_attribute('name') or ''
                        placeholder = await input_el.get_attribute('placeholder') or ''
                        current_value = await input_el.input_value()
                        if current_value:
                            print(f"Field {i+1} ({name or placeholder}): '{current_value}'")
                    except:
                        pass
                    
            except Exception as e:
                print(f"❌ Error during form interaction: {str(e)}")

            # --- Part 5: Cleanup ---
            print("\n✅ Test complete - pausing for visual inspection (15 seconds)...")
            await asyncio.sleep(15)  # Longer pause for visual inspection
            await browser.close()
            
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            if browser:
                await browser.close()

if __name__ == '__main__':
    asyncio.run(integration_test())