# InstantApply

An AI-powered job application assistant that automatically fills out and submits job applications on behalf of users.

## Features

- Search for jobs on Indeed based on job title and location
- Extract application questions from job postings
- Generate intelligent responses to application questions using Google Gemini 2.0
- Automatically fill and submit applications
- Track application status
- Parse and extract text from resume documents (PDF, DOCX, TXT)

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

5. Create a .env file with your Google Gemini API key:
```
echo "GEMINI_API_KEY=your_api_key_here" > .env
echo "SECRET_KEY=your_secret_key_here" >> .env
```

6. Initialize the database:
```
python init_db.py
```

### Getting a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your .env file: `GEMINI_API_KEY=your_key_here`

### Running the Application

```
flask run
```

Navigate to `http://localhost:5000` in your browser.

## Troubleshooting

If you encounter database errors like "no such table: users", make sure you've initialized the database:

```
python init_db.py
```

If problems persist, try removing the database file and creating it again:

```
rm instance/instant_apply.db  # On Windows: del instance\instant_apply.db
python init_db.py
```

## Project Structure

- `app.py` - Main Flask application file
- `config.py` - Configuration settings
- `.env` - Environment variables (API keys, secrets)
- `init_db.py` - Database initialization script
- `utils/` - Utility modules
  - `indeed_scraper.py` - Indeed job search functionality
  - `application_filler.py` - AI-powered form filling using Gemini
  - `job_submitter.py` - Job submission handling
- `models/` - Database models
  - `user.py` - User model definitions
  - `application.py` - Application tracking model
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

## Additional Features

### Resume Parsing

InstantApply can extract text from the following file formats:
- PDF documents
- Microsoft Word documents (DOCX)
- Plain text files (TXT)

The extracted text is used to:
1. Help the AI better understand your qualifications
2. Automatically fill out job applications
3. Store a searchable version of your resume

## License

[MIT License](LICENSE)