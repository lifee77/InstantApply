# Step 1: Set up Python environment
# Create a virtual environment using venv
python3 -m venv myenv
source myenv/bin/activate

# Alternatively, create a virtual environment using conda
# conda create --name myenv python=3.8
# conda activate myenv

# Step 2: Install Playwright and dependencies
pip install playwright
playwright install

# Step 3: Configure Gmail API for job response tracking
# Install the Google client library
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Follow the steps to configure Gmail API:
# 1. Go to https://console.developers.google.com/
# 2. Create a new project
# 3. Enable the Gmail API
# 4. Create credentials (OAuth 2.0 Client IDs)
# 5. Download the credentials.json file and save it in your project directory

# Example code to authenticate and list Gmail labels
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def list_labels():
    service = authenticate_gmail()
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        print(label['name'])

if __name__ == '__main__':
    list_labels()

# Step 4: Prepare a basic resume & cover letter template
# Create a basic resume template (resume_template.txt)
resume_template = """
Name: [Your Name]
Address: [Your Address]
Phone: [Your Phone Number]
Email: [Your Email]

Objective:
[Your Objective]

Experience:
[Your Experience]

Education:
[Your Education]

Skills:
[Your Skills]
"""

with open('resume_template.txt', 'w') as file:
    file.write(resume_template)

# Create a basic cover letter template (cover_letter_template.txt)
cover_letter_template = """
[Your Name]
[Your Address]
[City, State, ZIP Code]
[Email Address]
[Today’s Date]

[Recipient’s Name]
[Company’s Name]
[Company’s Address]

Dear [Recipient’s Name],

I am writing to express my interest in the [Job Title] position at [Company Name]. With my background in [Your Background], I am confident that I can contribute to your team.

[Body of the letter]

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and experiences align with the needs of your team.

Sincerely,
[Your Name]
"""

with open('cover_letter_template.txt', 'w') as file:
    file.write(cover_letter_template)
