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
                    slow_mo=100,  # Using slow_mo for visibility
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
            
            # --- Part 2: Import and use Gemini and Document Parser functions ---
            try:
                from archive.gemini_caller import generate_cover_letter, match_job_description, extract_resume_data
                from utils.document_parser import parse_and_save_resume
                
                # Sample base64 encoded resume data (truncated for brevity)
                resume_base64 = "data:application/pdf;base64,JVBERi0xLjQKJcTl8uXr..."
                parsed_text, _, _, _ = parse_and_save_resume(resume_base64, user_id=1)
                print("\n✅ Parsed resume text from sample resume:")
                print(parsed_text)
                
                extracted_data = extract_resume_data(parsed_text)
                print("\n✅ Extracted resume data:")
                print(extracted_data)
                
                # Construct user data dictionary using extracted data (default name provided)
                user_data_dict = {
                    "name": "John Doe",
                    "skills": extracted_data.get("skills", []),
                    "experience": extracted_data.get("experience", [])
                }
                
                # Generate and display cover letter
                cover_letter = generate_cover_letter("Software Engineer", "TestCompany", user_data_dict)
                print("\n✅ Generated Cover Letter:")
                print(cover_letter)
            except Exception as e:
                print(f"❌ Error in Gemini integration: {str(e)}")
                user_data_dict = {"name": "John Doe", "skills": [], "experience": []}
                cover_letter = "Default Cover Letter"
            
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
                input_fields = await page.query_selector_all('input:visible, textarea:visible, select:visible')
                if input_fields:
                    print(f"Found {len(input_fields)} visible input fields")
                    
                    # Try to fill each input field
                    for i, input_field in enumerate(input_fields):
                        try:
                            input_type = await input_field.get_attribute('type') or 'text'
                            placeholder = await input_field.get_attribute('placeholder') or ''
                            name = await input_field.get_attribute('name') or ''
                            id_attr = await input_field.get_attribute('id') or ''
                            
                            # Check if it's a visible input we can interact with
                            is_visible = await input_field.is_visible()
                            if not is_visible:
                                continue
                                
                            print(f"Field {i+1}: type={input_type}, placeholder='{placeholder}', name='{name}', id='{id_attr}'")
                            
                            # Focus on the input field to make interaction more visible
                            await input_field.focus()
                            await page.wait_for_timeout(500)  # Small delay for visibility
                            
                            # Fill field with appropriate data based on field hints and input type
                            if input_type == 'date' or 'date' in name.lower() or 'date' in placeholder.lower() or 'start' in name.lower():
                                # Use specific date (March 25, 2025)
                                value = "2025-03-25"
                                await input_field.fill(value)
                                print(f"✅ Filled date field with: '{value}' (March 25, 2025)")
                            elif 'name' in name.lower() or 'name' in placeholder.lower():
                                value = user_data_dict.get("name", "John Doe")
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
                            elif 'cover letter' in name.lower() or 'cover letter' in placeholder.lower():
                                value = cover_letter
                                await input_field.fill(value)
                                print(f"✅ Filled cover letter field with generated cover letter")
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
                
                # --- Look for calendar widgets or date pickers that aren't standard inputs ---
                try:
                    date_labels = await page.query_selector_all('label:has-text("start date"), label:has-text("Start date"), span:has-text("start date"), div:has-text("When can you start")')
                    
                    for label in date_labels:
                        print("Found a start date question element")
                        
                        parent = label
                        for _ in range(3):
                            parent = await page.evaluate('(el) => el.parentElement', parent)
                            if not parent:
                                break
                            
                            container_inputs = await page.evaluate('''
                                (container) => {
                                    const inputs = container.querySelectorAll('input, textarea, [contenteditable="true"]');
                                    return Array.from(inputs).map(el => el.id || el.name || '');
                                }
                            ''', parent)
                            
                            if container_inputs:
                                print(f"Found input elements related to date: {container_inputs}")
                                for input_id in container_inputs:
                                    if not input_id:
                                        continue
                                    input_el = await page.query_selector(f'#{input_id}')
                                    if input_el:
                                        await input_el.fill("2025-03-25")
                                        print("✅ Filled start date field with: '2025-03-25' (March 25, 2025)")
                                        break
                    
                    date_pickers = await page.query_selector_all('div[role="calendar"], [data-testid="datepicker"], .calendar-input, .date-picker')
                    
                    if date_pickers:
                        print(f"Found {len(date_pickers)} potential date picker elements")
                        for i, picker in enumerate(date_pickers):
                            if await picker.is_visible():
                                print(f"Attempting to interact with date picker {i+1}")
                                await picker.click()
                                await page.wait_for_timeout(1000)  
                                try:
                                    month_selectors = await page.query_selector_all('[class*="month-select"], [class*="year-select"], [aria-label*="month"], button:has-text("March")')
                                    if month_selectors:
                                        await month_selectors[0].click()
                                        await page.wait_for_timeout(500)
                                        
                                        march_option = await page.query_selector('option:has-text("March"), div:has-text("March 2025")')
                                        if march_option:
                                            await march_option.click()
                                            await page.wait_for_timeout(500)
                                            
                                            day25 = await page.query_selector('td:has-text("25"), div:has-text("25")')
                                            if day25:
                                                await day25.click()
                                                print("✅ Selected March 25, 2025 in date picker")
                                                continue
                                except Exception as e:
                                    print(f"Error navigating date picker: {str(e)}")
                                
                                day_cells = await page.query_selector_all('.calendar-day, .day, [role="gridcell"]')
                                if day_cells:
                                    for day_cell in day_cells:
                                        if await day_cell.is_visible() and not (await day_cell.get_attribute('disabled')):
                                            await day_cell.click()
                                            print(f"✅ Selected a date in date picker {i+1} (fallback)")
                                            break
                except Exception as e:
                    print(f"❌ Error handling date pickers: {str(e)}")
                
                # --- Handle Yes/No buttons and radio buttons for questions like visa requirements ---
                try:
                    visa_labels = await page.query_selector_all('label:has-text("visa"), label:has-text("Visa"), span:has-text("visa"), span:has-text("Visa")')
                    
                    for label in visa_labels:
                        label_text = await label.inner_text()
                        print(f"Found visa-related question: '{label_text}'")
                        
                        parent = label
                        for _ in range(3):
                            parent = await page.evaluate('(el) => el.parentElement', parent)
                            if not parent:
                                break
                            
                            radio_inputs = await page.query_selector_all('input[type="radio"]')
                            if radio_inputs:
                                for radio in radio_inputs:
                                    value = await radio.get_attribute('value') or ''
                                    if value.lower() in ['no', 'false', '0', 'n']:
                                        await radio.check()
                                        print("✅ Selected 'No' for visa question")
                                        break
                                break
                            
                            buttons = await page.query_selector_all('button, .btn')
                            for button in buttons:
                                button_text = await button.inner_text()
                                if button_text.lower() == 'no':
                                    await button.click()
                                    print("✅ Clicked 'No' button for visa question")
                                    break
                except Exception as e:
                    print(f"❌ Error handling yes/no questions: {str(e)}")
                
                # --- Look for other radio button groups ---
                try:
                    radio_groups = {}
                    all_radios = await page.query_selector_all('input[type="radio"]')
                    
                    for radio in all_radios:
                        name = await radio.get_attribute('name')
                        if name:
                            if name not in radio_groups:
                                radio_groups[name] = []
                            radio_groups[name].append(radio)
                    
                    for name, radios in radio_groups.items():
                        if not radios:
                            continue
                        parent_text = await page.evaluate('''
                            (radio) => {
                                let el = radio;
                                for (let i = 0; i < 5; i++) {
                                    el = el.parentElement;
                                    if (!el) break;
                                    if (el.textContent) return el.textContent.trim();
                                }
                                return "";
                            }
                        ''', radios[0])
                        
                        print(f"Found radio group '{name}' with question text: '{parent_text[:50]}...'")
                        
                        if "visa" in parent_text.lower() or "authorized" in parent_text.lower():
                            target_value = "yes" if "authorized" in parent_text.lower() else "no"
                            selected = False
                            for radio in radios:
                                value = await radio.get_attribute('value') or ''
                                label_text = await page.evaluate('''
                                    (radio) => {
                                        const id = radio.id;
                                        if (id) {
                                            const label = document.querySelector(`label[for="${id}"]`);
                                            return label ? label.textContent.trim() : "";
                                        }
                                        return "";
                                    }
                                ''', radio)
                                
                                if (value.lower() == target_value or label_text.lower() == target_value):
                                    await radio.check()
                                    print(f"✅ Selected '{target_value}' for question: '{parent_text[:30]}...'")
                                    selected = True
                                    break
                            if not selected and radios:
                                await radios[0].check()
                                print(f"✅ Selected first option for '{parent_text[:30]}...' (fallback)")
                        else:
                            await radios[0].check()
                            print(f"✅ Selected first option for radio group '{name}'")
                except Exception as e:
                    print(f"❌ Error handling radio button groups: {str(e)}")
                
                # Attempt to upload a resume if a file input is available
                try:
                    file_input = await page.query_selector('input[type="file"]')
                    if file_input:
                        with NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                            temp_file.write(b"%PDF-1.4\n%Mock Resume")
                            temp_path = temp_file.name
                        
                        await file_input.set_input_files(temp_path)
                        print(f"✅ Uploaded resume file: '{temp_path}'")
                        
                        await page.evaluate("""
                            () => {
                                const fileInput = document.querySelector('input[type="file"]');
                                if (fileInput && fileInput.parentElement) {
                                    fileInput.parentElement.style.border = '2px solid green';
                                    fileInput.parentElement.style.padding = '5px';
                                }
                            }
                        """)
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
                    
                # --- Prevent accidental form submission ---
                try:
                    submit_buttons = await page.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Apply")')
                    
                    if submit_buttons:
                        print(f"\n⚠️ Found {len(submit_buttons)} submit buttons - WILL NOT CLICK (test mode)")
                        
                        for i, button in enumerate(submit_buttons):
                            await page.evaluate('''
                                (button, index) => {
                                    button.style.border = '3px solid red';
                                    button.style.position = 'relative';
                                    const overlay = document.createElement('div');
                                    overlay.innerText = 'TEST MODE - NO SUBMIT';
                                    overlay.style.position = 'absolute';
                                    overlay.style.top = '0';
                                    overlay.style.left = '0';
                                    overlay.style.right = '0';
                                    overlay.style.bottom = '0';
                                    overlay.style.backgroundColor = 'rgba(255, 0, 0, 0.7)';
                                    overlay.style.color = 'white';
                                    overlay.style.display = 'flex';
                                    overlay.style.alignItems = 'center';
                                    overlay.style.justifyContent = 'center';
                                    overlay.style.fontWeight = 'bold';
                                    overlay.style.zIndex = '9999';
                                    overlay.style.pointerEvents = 'none';
                                    button.parentElement.style.position = 'relative';
                                    button.parentElement.appendChild(overlay);
                                }
                            ''', button, i)
                except Exception as e:
                    print(f"❌ Error highlighting submit buttons: {str(e)}")
    
            except Exception as e:
                print(f"❌ Error during form interaction: {str(e)}")
            
            # --- Part 5: Cleanup ---
            print("\n✅ Test complete - pausing for visual inspection (15 seconds)...")
            await asyncio.sleep(15)  # Pause for visual inspection
            await browser.close()
            
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            if browser:
                await browser.close()

if __name__ == '__main__':
    asyncio.run(integration_test())