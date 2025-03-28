"""
Application filler package for automated job applications
"""
from .core import ApplicationFiller
from .resume_handler import prioritize_resume_upload, handle_resume_upload
from .form_detector import detect_and_handle_form_type, find_and_click_submit_button
from .form_filler import FormFiller
from .response_generator import ResponseGenerator

__all__ = [
    'ApplicationFiller',
    'FormFiller',
    'ResponseGenerator',
    'prioritize_resume_upload',
    'handle_resume_upload',
    'detect_and_handle_form_type',
    'find_and_click_submit_button'
]