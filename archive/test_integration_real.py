import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock
from tempfile import NamedTemporaryFile
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from utils.application_filler import (
    extract_application_questions_async,
    generate_application_responses,
    setup_gemini,
)
from models.user import User

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

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
        for browser_type in [p.firefox, p.webkit]:
            try:
                print(f"Attempting to launch browser using {browser_type.__class__.__name__}")
                browser = await browser_type.launch(
                    headless=False,
                    slow_mo=100,  # Changed from slowMo to slow_mo for Python naming convention
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
                await page.bring_to_front()  # Focus the new tab

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
            await page.wait_for_timeout(1000)  
            page_title = await page.title()
            print("✅ Page Title:", page_title)
            
            # --- Part 2: Import and use gemini_caller functions ---
            try:
                from archive.gemini_caller import generate_cover_letter, match_job_description, extract_resume_data
                
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
                {"text": "Linkedin", "type": "text"},
                {"text": "How many years of Typescript experience do you have?", "type": "integer"},
                {"text": "Name something you've built 0 -> 1", "type": "text"},
                {"text": "Name your favorite 3rd-party library,  and why", "type": "text"},
                {"text": "What does your perfect job look like?", "type": "text"}
            ]
            
            mock_responses = {
                "Linkedin": "https://www.linkedin.com/in/annesmith",
                "How many years of Typescript experience do you have?": "2",
                "Name something you've built 0 -> 1": "I built an AI-powered resume matcher from scratch that parses job posts and generates tailored cover letters.",
                "Name your favorite 3rd-party library,  and why": "I love using `zod` for runtime type validation in Typescript—it’s elegant and safe.",
                "What does your perfect job look like?": "A collaborative remote-first role where I can own impactful features and grow with the team."
            }
            
            # Use our mocked questions
            with patch('utils.application_filler.extract_application_questions_async', new_callable=AsyncMock) as mock_extract:
                mock_extract.return_value = mock_questions
                questions = await extract_application_questions_async(dummy_job_id, page)
                print("\n✅ Extracted Application Questions:", questions)
            
            print("\n✅ Generated Application Responses:")
            print(mock_responses)
            
            # --- Part 4: Simple form interaction ---
            try:
                print("\n--- Attempting to interact with the form ---")
                
                # Try to find visible input fields on the page
                input_fields = await page.query_selector_all('input:visible, textarea:visible, select:visible')
                if input_fields:
                    print(f"Found {len(input_fields)} visible input fields")
                    response_iterator = iter(mock_responses.values())
                    
                    # Try to fill each input field
                    for i, input_field in enumerate(input_fields):
                        try:
                            # For the 5th input field, fill with 'no'
                            if i == 4:
                                await input_field.fill("no")
                                print(f"✅ Filled input field 5 with: 'no'")
                                await input_field.press("Tab")
                                await page.wait_for_timeout(500)
                                continue

                            input_type = await input_field.get_attribute('type') or 'text'
                            if input_type == 'file':
                                # Skip file inputs - we'll handle them separately
                                continue
                                
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
                                # Use specific date rather than relative date (March 25, 2025)
                                value = "2025-03-25"
                                await input_field.fill(value)
                                print(f"✅ Filled date field with: '{value}' (March 25, 2025)")
                            elif 'name' in name.lower() or 'name' in placeholder.lower():
                                value = "Anne Smith"
                                await input_field.fill(value)
                                print(f"✅ Filled name field with: '{value}'")
                            elif 'email' in name.lower() or 'email' in placeholder.lower():
                                value = "anne@example.com"
                                await input_field.fill(value)
                                print(f"✅ Filled email field with: '{value}'")
                            elif 'phone' in name.lower() or 'phone' in placeholder.lower():
                                value = "555-123-4567"
                                await input_field.fill(value)
                                print(f"✅ Filled phone field with: '{value}'")
                            elif 'location' in name.lower() or 'location' in placeholder.lower():
                                value = "San Francisco, CA"
                                await input_field.fill(value)
                                print(f"✅ Filled location field with: '{value}'")
                            elif 'Linkedin' in name or 'linkedin' in name.lower():
                                value = "https://www.linkedin.com/in/annesmith"
                                await input_field.fill(value)
                                print(f"✅ Filled LinkedIn field with: '{value}'")
                            elif '2338fe06-551b-42f6-a0ca-7ef1f56a87d5' in name:
                                value = "2"
                                await input_field.fill(value)
                                print(f"✅ Filled Typescript experience field with: '{value}'")
                            elif '674a1700-7669-41f4-9018-5628380dbd08' in name:
                                value = "I built an AI-powered resume matcher from scratch that parses job posts and generates tailored cover letters."
                                await input_field.fill(value)
                                print(f"✅ Filled project description field with: '{value}'")
                            elif '04670e81-4c7c-4e52-8600-4143333affc5' in name:
                                value = "I love using `zod` for runtime type validation in Typescript—it’s elegant and safe."
                                await input_field.fill(value)
                                print(f"✅ Filled library description field with: '{value}'")
                            elif 'd9c8fbe2-4ed3-40c8-a9b3-544c8b4c2803' in name:
                                value = "A collaborative remote-first role where I can own impactful features and grow with the team."
                                await input_field.fill(value)
                                print(f"✅ Filled job description field with: '{value}'")

                            else:
                                try:
                                    value = next(response_iterator)
                                except StopIteration:
                                    value = next(response_iterator)
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
                    # Improve detection of date-related elements - look for text about start date
                    date_labels = await page.query_selector_all('label:has-text("start date"), label:has-text("Start date"), span:has-text("start date"), div:has-text("When can you start")')
                    
                    for label in date_labels:
                        print(f"Found a start date question element")
                        
                        # Try to find related input fields
                        parent = label
                        for _ in range(3):  # Go up to 3 levels to find container
                            parent = await page.evaluate('(el) => el.parentElement', parent)
                            if not parent:
                                break
                                
                            # Look for input fields within this container
                            container_inputs = await page.evaluate('''(container) => {
                                const inputs = container.querySelectorAll('input, textarea, [contenteditable="true"]');
                                return Array.from(inputs).map(el => el.id || el.name || '');
                            }''', parent)
                            
                            if container_inputs:
                                print(f"Found input elements related to date: {container_inputs}")
                                # Try to find and fill each input
                                for input_id in container_inputs:
                                    if not input_id:
                                        continue
                                        
                                    input_el = await page.query_selector(f'#{input_id}')
                                    if input_el:
                                        await input_el.fill("2025-03-25")
                                        print(f"✅ Filled start date field with: '2025-03-25' (March 25, 2025)")
                                        break
                    
                    # Also try the original date picker detection
                    date_pickers = await page.query_selector_all('div[role="calendar"], [data-testid="datepicker"], .calendar-input, .date-picker')
                    
                    if date_pickers:
                        print(f"Found {len(date_pickers)} potential date picker elements")
                        for i, picker in enumerate(date_pickers):
                            if await picker.is_visible():
                                print(f"Attempting to interact with date picker {i+1}")
                                await picker.click()
                                await page.wait_for_timeout(1000)  # Wait for calendar to appear
                                
                                # Try to select a day - look for March 25, 2025 or any available date
                                # First try to navigate to March 2025 if possible
                                try:
                                    # Click the month/year selector if available
                                    month_selectors = await page.query_selector_all('[class*="month-select"], [class*="year-select"], [aria-label*="month"], button:has-text("March")')
                                    if month_selectors:
                                        await month_selectors[0].click()
                                        await page.wait_for_timeout(500)
                                        
                                        # Try to click on March 2025
                                        march_option = await page.query_selector('option:has-text("March"), div:has-text("March 2025")')
                                        if march_option:
                                            await march_option.click()
                                            await page.wait_for_timeout(500)
                                            
                                            # Now try to find the 25th day
                                            day25 = await page.query_selector('td:has-text("25"), div:has-text("25")')
                                            if day25:
                                                await day25.click()
                                                print(f"✅ Selected March 25, 2025 in date picker")
                                                continue
                                except Exception as e:
                                    print(f"Error navigating date picker: {str(e)}")
                                
                                # Fallback - just select any available day
                                day_cells = await page.query_selector_all('.calendar-day, .day, [role="gridcell"]')
                                if day_cells:
                                    # Find a selectable day (not disabled)
                                    for day_cell in day_cells:
                                        if await day_cell.is_visible() and not (await day_cell.get_attribute('disabled')):
                                            await day_cell.click()
                                            print(f"✅ Selected a date in date picker {i+1} (fallback)")
                                            break
                except Exception as e:
                    print(f"❌ Error handling date pickers: {str(e)}")
                
                # --- Handle Yes/No buttons and radio buttons for questions like visa requirements ---
                try:
                    # Global flag to ensure we only click one visa-related "No" button
                    visa_clicked = False
                    visa_elements = await page.query_selector_all('*:has-text("visa"), *:has-text("Visa")')

                    for element in visa_elements:
                        if visa_clicked:
                            break
                        label_text = await element.inner_text()
                        if not label_text:
                            continue

                        print(f"Found possible visa-related question text: '{label_text}'")

                        container = element
                        for _ in range(3):
                            if visa_clicked:
                                break
                            yes_no_buttons = await container.query_selector_all(
                                'button:has-text("Yes"), button:has-text("No"), '
                                '[role="button"]:has-text("Yes"), [role="button"]:has-text("No")'
                            )
                            if yes_no_buttons:
                                for btn in yes_no_buttons:
                                    btn_text = (await btn.inner_text()).strip().lower()
                                    if btn_text == 'no':
                                        aria_pressed = await btn.get_attribute('aria-pressed')
                                        if aria_pressed == 'true':
                                            print(f"ℹ️ 'No' button already selected for visa question: '{label_text}'")
                                        else:
                                            await btn.click()
                                            print(f"✅ Clicked 'No' button for visa question: '{label_text}'")
                                        visa_clicked = True
                                        break
                            container = await page.evaluate_handle('(el) => el.parentElement', container)
                            if not container:
                                break
                except Exception as e:
                    print(f"❌ Error handling yes/no questions: {str(e)}")
                
                # --- Look for other radio button groups ---
                try:
                    # Find all radio groups by looking for multiple radio buttons with the same name
                    radio_groups = {}
                    all_radios = await page.query_selector_all('input[type="radio"]')
                    
                    for radio in all_radios:
                        name = await radio.get_attribute('name')
                        if name:
                            if name not in radio_groups:
                                radio_groups[name] = []
                            radio_groups[name].append(radio)
                    
                    # For each group, select a reasonable default
                    for name, radios in radio_groups.items():
                        if not radios:
                            continue
                            
                        # Try to identify what kind of question this is
                        parent_text = await page.evaluate('''(radio) => {
                            let el = radio;
                            for (let i = 0; i < 5; i++) {
                                el = el.parentElement;
                                if (!el) break;
                                if (el.textContent) return el.textContent.trim();
                            }
                            return "";
                        }''', radios[0])
                        
                        print(f"Found radio group '{name}' with question text: '{parent_text[:50]}...'")
                        
                        # Logic for selecting appropriate radio option based on question text
                        if "visa" in parent_text.lower() or "authorized" in parent_text.lower():
                            # For visa/authorization questions, select "yes" to work authorization or "no" to needing visa
                            if "authorized" in parent_text.lower():
                                # Select "Yes" for "Are you authorized to work?"
                                target_value = "yes"
                            else:
                                # Select "No" for "Do you need a visa?"
                                target_value = "no"
                                
                            selected = False
                            for radio in radios:
                                value = await radio.get_attribute('value') or ''
                                label_text = await page.evaluate('''(radio) => {
                                    const id = radio.id;
                                    if (id) {
                                        const label = document.querySelector(`label[for="${id}"]`);
                                        return label ? label.textContent.trim() : "";
                                    }
                                    return "";
                                }''', radio)
                                
                                if (value.lower() == target_value or 
                                    label_text.lower() == target_value):
                                    await radio.check()
                                    print(f"✅ Selected '{target_value}' for question: '{parent_text[:30]}...'")
                                    selected = True
                                    break
                            
                            if not selected and radios:
                                # If we couldn't match by value/label, just pick the first one
                                await radios[0].check()
                                print(f"✅ Selected first option for '{parent_text[:30]}...' (fallback)")
                        else:
                            # For other radio groups, just select the first option
                            await radios[0].check()
                            print(f"✅ Selected first option for radio group '{name}'")
                except Exception as e:
                    print(f"❌ Error handling radio button groups: {str(e)}")
                
                # Attempt to upload a resume if a file input is available
                try:
                    file_input = await page.query_selector('input[type="file"]')
                    if file_input:
                        import os
                        import tempfile
                        temp_path = os.path.join(tempfile.gettempdir(), "anne_resume.pdf")
                        with open(temp_path, "wb") as temp_file:
                            temp_file.write(b"%PDF-1.4\n%Mock Resume")
                        
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

                try:
                    file_input = await page.query_selector('input[type="file"]')
                    if file_input:
                        import os
                        import tempfile
                        temp_path = os.path.join(tempfile.gettempdir(), "anne_resume.pdf")
                        with open(temp_path, "wb") as temp_file:
                            temp_file.write(b"%PDF-1.4\n%Mock Resume")
                        
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
                    
                # --- Prevent accidental form submission ---
                try:
                    # Find submit buttons and add a warning
                    submit_buttons = await page.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Apply")')
                    
                    if submit_buttons:
                        print(f"\n⚠️ Found {len(submit_buttons)} submit buttons - WILL NOT CLICK (test mode)")
                        
                        # Highlight the buttons to show we found them
                        for i, button in enumerate(submit_buttons):
                            await page.evaluate('''(button, index) => {
                                button.style.border = '3px solid red';
                                button.style.position = 'relative';
                                
                                // Add a "NO SUBMIT" overlay
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
                                overlay.style.pointerEvents = 'none'; // Allow clicks to pass through
                                
                                button.parentElement.style.position = 'relative';
                                button.parentElement.appendChild(overlay);
                            }''', button, i)
                except Exception as e:
                    print(f"❌ Error highlighting submit buttons: {str(e)}")

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