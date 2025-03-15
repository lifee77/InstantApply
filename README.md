# InstantApply

An AI-powered job application assistant that automatically fills out and submits job applications on behalf of users.

## Features

- Search for jobs on Indeed based on job title and location
- Extract application questions from job postings
- Generate intelligent responses to application questions using Google Gemini 2.0
- Automatically fill and submit applications
- Track application status

## Setup

### Prerequisites

- Python 3.8+
- Node.js (required for Playwright)
- Google Gemini API key

### Installation

1. Clone the repository:
```
git clone <repository-url>
cd InstantApply
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Install Playwright browsers:
```
python -m playwright install chromium
```

5. Set up your Google Gemini API key:
```
python setup_gemini.py
```

6. Set environment variables:
```
export FLASK_APP=app.py
export FLASK_DEBUG=1
export SECRET_KEY=your_secret_key
```

On Windows:
```
set FLASK_APP=app.py
set FLASK_DEBUG=1
set SECRET_KEY=your_secret_key
```

7. Initialize the database:
```
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

### Getting a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Use the setup script to configure your key: `python setup_gemini.py`

### Running the Application

```
flask run
```

Navigate to `http://localhost:5000` in your browser.

## Project Structure

- `app.py` - Main Flask application file
- `config.py` - Configuration settings
- `utils/` - Utility modules
  - `indeed_scraper.py` - Indeed job search functionality
  - `application_filler.py` - AI-powered form filling using Gemini
  - `job_submitter.py` - Job submission handling
- `models/` - Database models
  - `user.py` - User model definitions
- `templates/` - HTML templates
- `static/` - Static assets (CSS, JS)

## How It Works

1. Users create a profile with their personal information, resume, skills, and experience
2. Users search for jobs by title and location
3. The system searches Indeed for matching job listings
4. Users select jobs to apply for
5. The AI automatically:
   - Extracts application questions
   - Generates appropriate responses using Gemini 2.0
   - Fills out the application form
   - Submits the application

## License

[MIT License](LICENSE)