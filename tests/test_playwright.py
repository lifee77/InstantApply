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

# --- Setup a Dummy Flask App for Testing ---
app = Flask(__name__)
app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')
app.config['GEMINI_MODEL'] = 'gemini-pro'

# Dummy User fixture (assuming the User model has attributes: name, skills, experience, email, resume_file_path)
@pytest.fixture
def dummy_user():
    user = User(name="Jane Doe", skills="Python, AI", experience="3 years", email="jane@example.com", resume_file_path="/dummy/path/resume.pdf")
    return user

# Make sure every test runs in the context of our Flask app
@pytest.fixture(autouse=True)
def flask_app_context():
    with app.app_context():
        yield

# --- Tests for ApplicationFiller Module ---
class TestApplicationFiller:

    @pytest.mark.asyncio
    async def test_extract_application_questions_async(self):
        """
        Test the asynchronous extraction of application questions.
        We patch async_playwright to simulate the browser behavior.
        """
        with patch("utils.application_filler.async_playwright") as mock_playwright:
            # Setup mock chain for async_playwright
            mock_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            # Chain the mocks
            mock_playwright.__aenter__.return_value = mock_instance
            mock_instance.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            # Simulate navigation and waiting for selector
            mock_page.goto.return_value = asyncio.Future()
            mock_page.goto.return_value.set_result(None)
            mock_page.wait_for_selector.return_value = asyncio.Future()
            mock_page.wait_for_selector.return_value.set_result(None)

            # Simulate one question extraction:
            fake_element = AsyncMock()
            fake_label = AsyncMock()
            
            # ✅ Fix: Use `AsyncMock(return_value=...)` for proper async return
            fake_label.inner_text = AsyncMock(return_value="What is your greatest strength?")
            
            fake_element.query_selector.return_value = fake_label
            mock_page.query_selector_all.return_value = [fake_element]

            # Call function
            questions = await extract_application_questions_async("dummy_job_id")
            print("Extracted Questions:", questions)

            assert isinstance(questions, list)
            # ✅ Fix: Ensure the extracted questions contain expected text
            assert any("greatest strength" in q["text"] for q in questions)

    def test_extract_application_questions_sync_wrapper(self):
        """
        Test the synchronous wrapper that calls the asynchronous extraction.
        """
        with patch("utils.application_filler.extract_application_questions_async", new_callable=AsyncMock) as mock_async:
            # Simulate a dummy question list
            mock_async.return_value = [{"text": "What is your greatest strength?", "type": "text"}]
            questions = extract_application_questions("dummy_job_id")
            assert isinstance(questions, list)
            assert "greatest strength" in questions[0]["text"]

    def test_setup_gemini_success(self):
        """
        Test that setup_gemini configures the Gemini API when the key is set.
        """
        with patch("utils.application_filler.genai.configure") as mock_configure:
            setup_gemini()
            mock_configure.assert_called_with(api_key=os.getenv("GEMINI_API_KEY"))

    def test_setup_gemini_failure(self):
        """
        Test that setup_gemini raises an error when the GEMINI_API_KEY is missing.
        """
        # Temporarily remove the API key from config
        app.config['GEMINI_API_KEY'] = None
        with pytest.raises(ValueError):
            setup_gemini()
        # Reset for further tests
        app.config['GEMINI_API_KEY'] = 'dummy_api_key'

    def test_generate_application_responses(self, dummy_user):
        """
        Test the generation of application responses by mocking Gemini.
        """
        job_id = "dummy_job_id"
        # Patch the function that extracts questions to return a dummy question list.
        with patch("utils.application_filler.extract_application_questions", return_value=[{"text": "What is your greatest strength?", "type": "text"}]):
            # Patch the Gemini model to simulate a generated response.
            with patch("utils.application_filler.genai.GenerativeModel") as mock_model_class:
                mock_model_instance = MagicMock()
                fake_response = MagicMock()
                fake_response.text = "I am dedicated and hardworking."
                mock_model_instance.generate_content.return_value = fake_response
                mock_model_class.return_value = mock_model_instance

                responses = generate_application_responses(job_id, dummy_user)
                assert isinstance(responses, dict)
                for question, answer in responses.items():
                    assert answer == "I am dedicated and hardworking."

# --- Tests for JobSubmitter Module ---
class TestJobSubmitter:

    @pytest.mark.asyncio
    async def test_submit_application_async_success(self, dummy_user):
        """
        Test the async job application submission by patching Playwright.
        We simulate standard fields and a submit button.
        """
        responses = {"What is your greatest strength?": "Hardworking."}
        job_id = "dummy_job_id"

        with patch("utils.job_search.job_submitter.async_playwright") as mock_playwright:
            mock_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            # Chain the async mocks
            mock_playwright.__aenter__.return_value = mock_instance
            mock_instance.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Simulate page actions for navigation and waiting
            mock_page.goto.return_value = asyncio.Future()
            mock_page.goto.return_value.set_result(None)
            mock_page.wait_for_selector.return_value = asyncio.Future()
            mock_page.wait_for_selector.return_value.set_result(None)
            
            # Simulate form field interactions:
            # For file upload, assume file upload field exists.
            file_input = AsyncMock()
            def query_selector_side_effect(selector):
                if 'input[type="file"]' in selector:
                    return file_input
                # For name and email fields, return a dummy AsyncMock
                if "#input-applicant.name" in selector or "#input-applicant.email" in selector:
                    return AsyncMock()
                # For submit button, return a dummy AsyncMock
                if "button" in selector:
                    return AsyncMock()
                return None
            mock_page.query_selector.side_effect = query_selector_side_effect
            
            # For wait_for_selector on submit confirmation, simulate a successful wait.
            mock_page.wait_for_selector.return_value = asyncio.Future()
            mock_page.wait_for_selector.return_value.set_result(None)
            
            result = await submit_application_async(job_id, dummy_user, responses)
            assert isinstance(result, dict)
            # Here we check that the result contains the job_id and a message.
            assert result.get("job_id") == job_id

    def test_submit_application_sync_wrapper(self, dummy_user):
        """
        Test the synchronous wrapper for the async submit_application function.
        """
        job_id = "dummy_job_id"
        responses = {"What is your greatest strength?": "Hardworking."}

        with patch("utils.job_search.job_submitter.submit_application_async", new_callable=AsyncMock) as mock_async:
            mock_async.return_value = {"success": True, "job_id": job_id, "message": "Application submitted successfully"}
            result = submit_application(job_id, dummy_user, responses)
            assert result["success"] is True
            assert result["job_id"] == job_id