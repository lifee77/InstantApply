# InstantApply

An AI-powered job application assistant that automatically fills out and submits job applications on behalf of users.

## Features

- Search for jobs on Indeed based on job title and location
- Extract application questions from job postings
- Generate intelligent responses to application questions using AI
- Automatically fill and submit applications
- Track application status

## Setup

### Prerequisites

- Python 3.8+
- Node.js (required for Playwright)
- OpenAI API key

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
python setup_playwright.py
```

5. Set environment variables:
```
export FLASK_APP=app.py
export FLASK_DEBUG=1
export SECRET_KEY=your_secret_key
export OPENAI_API_KEY=your_openai_api_key
```

On Windows:
```
set FLASK_APP=app.py
set FLASK_DEBUG=1
set SECRET_KEY=your_secret_key
set OPENAI_API_KEY=your_openai_api_key
```

6. Initialize the database:
```
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

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
  - `application_filler.py` - AI-powered form filling
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
   - Generates appropriate responses
   - Fills out the application form
   - Submits the application

## License

[MIT License](LICENSE)