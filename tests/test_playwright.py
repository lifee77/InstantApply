import os
import asyncio
import pytest
import google.generativeai as genai
from unittest.mock import patch, MagicMock, AsyncMock
from flask import Flask, current_app
from dotenv import load_dotenv
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
from models.user import User


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

# 📌 Function to Save a Text to a PDF
def save_text_as_pdf(text, filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(190, 10, text)
    pdf.output(filename)

# 📌 Generate and Save Resume + Cover Letter
def generate_and_save_files(user_data):
    cover_letter_text = generate_cover_letter("Software Engineer", "TestCorp", user_data)
    resume_text = extract_resume_data("""
    John Doe
    Experienced Python Developer skilled in AI, Machine Learning, and API Development.
    Previous roles include Software Engineer at ABC and Developer at XYZ.
    Expertise in NLP, automation, and cloud computing.
    """)

    cover_letter_path = "cover_letter.pdf"
    resume_path = "resume.pdf"

    save_text_as_pdf(cover_letter_text, cover_letter_path)
    save_text_as_pdf(resume_text, resume_path)

    return cover_letter_path, resume_path

# 📌 Integration Test Using Playwright
async def integration_test():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox"
                ],
                channel="chrome"
            )
        except Exception as e:
            print("Failed to launch browser with bundled Chromium:", e)
            return

        page = await browser.new_page()
        
        # --- Step 1: Open Website ---
        try:
            await page.goto(TEST_URL)
            print("✅ Opened the website:", TEST_URL)
        except Exception as e:
            print("Error navigating to URL:", e)
            await browser.close()
            return

        await page.wait_for_timeout(3000)  # Wait for page load

        # --- Step 2: Generate Cover Letter and Resume ---
        with app.app_context():  # Fixes `RuntimeError: Working outside of application context`
            user_data = {
                "name": "John Doe",
                "skills": ["Python", "Playwright", "AI"],
                "experience": ["Software Engineer at ABC", "Developer at XYZ"],
            }
            cover_letter_path, resume_path = generate_and_save_files(user_data)

        print("\n✅ Saved Cover Letter & Resume as PDFs.")

        # --- Step 3: Upload Resume ---
        try:
            resume_input = await page.wait_for_selector('input[type="file"]', timeout=5000)
            await resume_input.set_input_files(resume_path)
            print("✅ Uploaded Resume")
        except Exception as e:
            print("⚠️ Resume upload failed:", e)

        # --- Step 4: Upload Cover Letter ---
        try:
            cover_letter_input = await page.wait_for_selector('input[type="file"]', timeout=5000)
            await cover_letter_input.set_input_files(cover_letter_path)
            print("✅ Uploaded Cover Letter")
        except Exception as e:
            print("⚠️ Cover letter upload failed:", e)

        # --- Step 5: Extract Application Questions ---
        try:
            questions = await extract_application_questions_async("dummy_job_id")
            print("\n✅ Extracted Application Questions:", questions)
        except Exception as e:
            print("⚠️ Error extracting application questions:", e)

        # --- Step 6: Fill Out Form Fields ---
        try:
            await page.fill('input[name="name"]', "John Doe")
            await page.fill('input[name="email"]', "johndoe@example.com")
            print("✅ Filled out name & email fields.")
        except Exception as e:
            print("⚠️ Error filling form fields:", e)

        # --- Step 7: Submit Application ---
        try:
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
            await submit_button.click()
            print("✅ Clicked Submit Button")
        except Exception as e:
            print("⚠️ Submission failed:", e)

        # --- Step 8: Cleanup ---
        await asyncio.sleep(5)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(integration_test())