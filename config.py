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

# OpenAI API (for AI form filling)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Session settings
PERMANENT_SESSION_LIFETIME = timedelta(days=7)
