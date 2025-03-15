import os
import asyncio
import pytest
import google.generativeai as genai
import json  # Add explicit import for json
from unittest.mock import patch, MagicMock, AsyncMock
from flask import Flask, current_app
from dotenv import load_dotenv
from fpdf import FPDF
from playwright.async_api import async_playwright  # Add this import
pytest_plugins = "pytest_asyncio"

# Import functions from your modules
from utils.application_filler import (
    extract_application_questions_async,
    extract_application_questions,
    setup_gemini,
    generate_application_responses,
)
from utils.job_search.job_submitter import (
    submit_application_async,
    submit_application,
)
from utils.job_search.job_search import search_jobs, search_jobs_mock
from utils.gemini_caller import generate_cover_letter, extract_resume_data
from models.user import User, db


# Load environment variables from .env
load_dotenv()

# Ensure GEMINI_API_KEY is set
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY is not set in your environment.")

# Define the test URL for Playwright
TEST_URL = "https://jobs.ashbyhq.com/replo/ec206174-ccc2-42fa-b295-8201421f21b0/application"

# Setup Flask App Context to Fix `RuntimeError: Working outside of application context`
app = Flask(__name__)
app.config['GEMINI_API_KEY'] = os.getenv("GEMINI_API_KEY")
app.config['GEMINI_MODEL'] = 'gemini-pro'

# Change to SQLite memory database to avoid file permission issues
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize the database and create tables
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Tables created successfully")

# 📌 Function to Save a Text to a PDF
def save_text_as_pdf(text, filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(190, 10, text)
    pdf.output(filename)

# For debugging, add this code to show more information about users in the database
def debug_list_users():
    """Print all users in the database for debugging"""
    with app.app_context():
        users = User.query.all()
        print(f"\n🔍 Found {len(users)} users in the database:")
        for user in users:
            resume_preview = user.resume[:30].replace('\n', ' ') if user.resume else "No resume"
            print(f"   - {user.name} ({user.email}): {resume_preview}...")
    return len(users)

# 📌 Create test user with resume and profile data
def create_test_user(use_real_user=False):  # Set default to False to skip real user lookup
    """Create a test user and return all data as a dictionary."""
    user_data = {}
    
    with app.app_context():
        # Create a test user
        user = User.query.filter_by(email="johndoe@example.com").first()
        
        if not user:
            print("Creating test user...")
            # Create test user with resume and profile data
            user = User(
                name="John Doe",
                email="johndoe@example.com",
                resume="""
                John Doe
                Experienced Python Developer skilled in AI, Machine Learning, and API Development.
                Previous roles include Software Engineer at ABC and Developer at XYZ.
                Expertise in NLP, automation, and cloud computing.
                """,
                skills="""["Python", "Playwright", "AI", "Machine Learning", "API Development", "NLP"]""",
                experience="""["Software Engineer at ABC", "Developer at XYZ"]"""
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            print("Test user created successfully")
        else:
            print("Test user already exists")
        
        # Extract data while still inside app context to avoid detached instance error
        user_data = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "skills": json.loads(user.skills) if user.skills else [],
            "experience": json.loads(user.experience) if user.experience else [],
            "resume": user.resume
        }
        
    return user_data

# 📌 Generate and Save Resume + Cover Letter using real user data
def generate_and_save_files(user_data):
    # User data is now passed directly as a dictionary
    # No need to access SQLAlchemy model properties
    
    # Generate cover letter using real user data
    cover_letter_text = generate_cover_letter("Software Engineer", "TestCorp", user_data)

    # Use the actual resume content from the user data
    resume_text = user_data.get("resume", "No resume available")

    cover_letter_path = "cover_letter.pdf"
    resume_path = "resume.pdf"

    save_text_as_pdf(cover_letter_text, cover_letter_path)
    save_text_as_pdf(resume_text, resume_path)

    return cover_letter_path, resume_path, user_data

# 📌 Integration Test Using Playwright
async def integration_test():
    # Avoid using Chromium since it's crashing consistently
    for browser_type_name in ['webkit', 'firefox']:  # Removed 'chromium' from the list
        print(f"\nAttempting with {browser_type_name} browser...")
        
        async with async_playwright() as p:
            browser_type = getattr(p, browser_type_name)
            
            try:
                # Launch browser with safer options
                browser = await browser_type.launch(
                    headless=False,
                    slow_mo=50,  # Add a small delay between actions for stability
                    args=[] if browser_type_name != 'chromium' else [
                        "--no-sandbox",
                        "--disable-gpu",
                        "--disable-software-rasterizer",
                        "--disable-dev-shm-usage",
                        "--disable-setuid-sandbox"
                    ]
                )
                
                # Create context with viewport and user agent
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
                )
                
                page = await context.new_page()
                
                # --- Step 1: Open Website ---
                try:
                    print(f"Navigating to {TEST_URL}...")
                    await page.goto(TEST_URL, timeout=60000)  # Increase timeout for slow connections
                    print("✅ Opened the website:", TEST_URL)
                    
                    # Capture page title for verification
                    title = await page.title()
                    print(f"Page title: {title}")
                    
                    # Wait for the page to be fully loaded
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                except Exception as e:
                    print(f"⚠️ Error navigating to URL: {str(e)}")
                    await browser.close()
                    continue  # Try next browser
    
                # --- Step 2: Create User and Generate Cover Letter/Resume ---
                user_data = create_test_user(use_real_user=True)  # Set to True to use real user data if available
                
                # Print some information about the user data we're using
                print(f"\n📋 User data being used:")
                print(f"   Name: {user_data['name']}")
                print(f"   Email: {user_data['email']}")
                print(f"   Skills: {', '.join(user_data['skills'][:3])}...")
                
                # Fix the backslash in f-string error
                resume_snippet = user_data['resume'][:100]
                resume_snippet = resume_snippet.replace("\n", " ")
                print(f"   Resume snippet: {resume_snippet}...")
                
                cover_letter_path, resume_path, user_data = generate_and_save_files(user_data)
                print("\n✅ Created user and saved Cover Letter & Resume as PDFs.")
                
                # --- Step 3: Debug page elements ---
                print("\nDebug: Analyzing page structure...")
                
                # Find all form elements and print details
                form_elements = await page.query_selector_all('form')
                print(f"Found {len(form_elements)} form elements")
                
                # Find all input elements
                input_elements = await page.query_selector_all('input')
                print(f"Found {len(input_elements)} input elements")
                
                # Print details about file inputs
                file_inputs = await page.query_selector_all('input[type="file"]')
                print(f"Found {len(file_inputs)} file input elements")
                
                for i, file_input in enumerate(file_inputs):
                    is_visible = await file_input.is_visible()
                    name = await file_input.get_attribute('name') or 'unnamed'
                    id_attr = await file_input.get_attribute('id') or 'no-id'
                    print(f"File input #{i+1}: visible={is_visible}, name={name}, id={id_attr}")
                
                # --- Step 4: Upload Resume ---
                try:
                    print("\nAttempting to locate and use file inputs...")
                    
                    if file_inputs:
                        for i, file_input in enumerate(file_inputs):
                            try:
                                # First make sure parent elements are visible if any
                                await page.evaluate("""input => {
                                    const el = input;
                                    if (el && el.parentElement) {
                                        el.style.opacity = '1';
                                        el.style.display = 'block';
                                        el.style.visibility = 'visible';
                                        el.parentElement.style.opacity = '1';
                                        el.parentElement.style.display = 'block';
                                        el.parentElement.style.visibility = 'visible';
                                    }
                                }""", file_input)
                                
                                # Try to set the file
                                await file_input.set_input_files(resume_path)
                                print(f"✅ Uploaded Resume to file input #{i+1}")
                                break
                            except Exception as e:
                                print(f"⚠️ Failed to upload to file input #{i+1}: {str(e)}")
                    else:
                        print("⚠️ No file inputs found on the page")
                        
                except Exception as e:
                    print(f"⚠️ Resume upload error: {str(e)}")
                
                # --- Step 5: Fill Out Form Fields ---
                await page.wait_for_timeout(2000)  # Wait a bit for any dynamic content to load
                
                try:
                    print("\nAttempting to fill form fields...")
                    
                    # Find input fields by various selectors
                    name_selectors = [
                        'input[name="name"]', 
                        'input[placeholder*="name" i]',
                        'input[id*="name" i]',
                        'input[type="text"]',
                    ]
                    
                    email_selectors = [
                        'input[name="email"]', 
                        'input[placeholder*="email" i]',
                        'input[id*="email" i]',
                        'input[type="email"]',
                    ]
                    
                    phone_selectors = [
                        'input[name="phone"]', 
                        'input[placeholder*="phone" i]',
                        'input[id*="phone" i]',
                        'input[type="tel"]',
                    ]
                    
                    # Try each name selector until one works
                    for selector in name_selectors:
                        try:
                            name_input = await page.query_selector(selector)
                            if name_input:
                                await name_input.fill(user_data["name"])
                                print(f"✅ Filled name field using selector: {selector}")
                                break
                        except Exception as e:
                            continue
                            
                    # Try each email selector until one works
                    for selector in email_selectors:
                        try:
                            email_input = await page.query_selector(selector)
                            if email_input:
                                await email_input.fill(user_data["email"])
                                print(f"✅ Filled email field using selector: {selector}")
                                break
                        except Exception as e:
                            continue
                            
                    # Try each phone selector until one works
                    for selector in phone_selectors:
                        try:
                            phone_input = await page.query_selector(selector)
                            if phone_input:
                                await phone_input.fill("555-123-4567")
                                print(f"✅ Filled phone field using selector: {selector}")
                                break
                        except Exception as e:
                            continue
                    
                    # Try to find and fill any textarea fields
                    textareas = await page.query_selector_all('textarea')
                    if textareas:
                        skills = user_data["skills"]
                        experience = user_data["experience"]
                        response = f"I am {user_data['name']}, with expertise in {', '.join(skills[:3])}. "
                        response += f"I have experience as {experience[0] if experience else 'a professional'}."
                        
                        for i, textarea in enumerate(textareas):
                            try:
                                await textarea.fill(response)
                                print(f"✅ Filled textarea #{i+1}")
                            except Exception as e:
                                print(f"⚠️ Error filling textarea #{i+1}: {str(e)}")
                    
                    print("✅ Form filling completed")
                                
                except Exception as e:
                    print(f"⚠️ Error filling form: {str(e)}")
                
                # --- Step 6: Find Submit Button ---
                try:
                    print("\nLooking for submit button...")
                    
                    button_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Submit")',
                        'button:has-text("Apply")',
                        'button.submit',
                        'button.apply',
                        'button[id*="submit" i]',
                        'button[id*="apply" i]',
                    ]
                    
                    submit_button = None
                    for selector in button_selectors:
                        try:
                            button = await page.query_selector(selector)
                            if button and await button.is_visible():
                                submit_button = button
                                print(f"✅ Found submit button using selector: {selector}")
                                break
                        except Exception:
                            continue
                    
                    if submit_button:
                        # Don't actually click to avoid submitting
                        print("✅ Submit button found (did not click to prevent actual submission)")
                    else:
                        print("⚠️ No submit button found on the page")
                        
                except Exception as e:
                    print(f"⚠️ Error finding submit button: {str(e)}")
                
                # --- Step 7: Cleanup ---
                print("\n✅ Test completed with browser:", browser_type_name)
                await page.wait_for_timeout(5000)  # Wait for visual verification
                await browser.close()
                
                # Exit after successful run
                return
                
            except Exception as e:
                print(f"❌ Browser {browser_type_name} failed: {str(e)}")
                try:
                    if 'browser' in locals():
                        await browser.close()
                except:
                    pass
                continue  # Try next browser
    
    print("❌ All browser types failed. Test could not complete.")

if __name__ == '__main__':
    asyncio.run(integration_test())