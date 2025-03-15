import os
from datetime import timedelta

# Flask settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_development')
DEBUG = os.environ.get('FLASK_DEBUG', True)

# Database settings
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///instant_apply.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Indeed scraping settings
INDEED_SCRAPE_DELAY = 2  # seconds between requests to avoid rate limiting

# Gemini API (for AI form filling)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-pro'  # Gemini 2.0 model name

# Session settings
PERMANENT_SESSION_LIFETIME = timedelta(days=7)
