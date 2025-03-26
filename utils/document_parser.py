import os
import logging
import tempfile
import base64
import uuid
import shutil
from typing import Tuple, Optional
from werkzeug.utils import secure_filename
from flask import current_app
import spacy
import re
# PDF parsing
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    
# DOCX parsing
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

logger = logging.getLogger(__name__)

nlp = spacy.load("en_core_web_sm")

def parse_resume_with_spacy(text):
    """
    Parse resume text using spaCy NLP to extract structured information.
    
    Args:
        text: The plain text content of a resume
        
    Returns:
        Dictionary containing extracted resume components
    """
    clean_text = text.replace('\n', '. ').replace('  ', ' ')
    doc = nlp(clean_text)
    
    parsed = {
        "name": None,
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "location": None,
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "languages": [],
        "job_titles": [],
        "professional_summary": None,
        "authorization_status": None,
        "work_mode_preference": None,
        "desired_salary_range": None,
        "career_goals": None,
        "biggest_achievement": None,
        "work_style": None,
        "industry_attraction": None,
        "values": []
    }
    
    # Original text for regex searches
    orig_lines = text.strip().split('\n')
    
    # Extract name (improved)
    for ent in doc.ents:
        if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
            parsed["name"] = ent.text
            break
    
    # Fallback: check if the first line looks like a name
    if not parsed["name"] and orig_lines:
        first_line = orig_lines[0].strip()
        if len(first_line.split()) in [2, 3, 4] and first_line.istitle() and len(first_line) < 40:
            parsed["name"] = first_line
    
    # Extract email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        parsed["email"] = email_match.group(0)
    
    # Extract phone number
    phone_matches = re.findall(r'(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', text)
    if phone_matches:
        parsed["phone"] = ''.join(phone_matches[0]).strip()
    
    # Extract LinkedIn URL
    linkedin_match = re.search(r'(?:linkedin\.com/in/|linkedin\.com/profile/|linkedin\s*:\s*)([^\s/]+)', text, re.I)
    if linkedin_match:
        username = linkedin_match.group(1).strip('/').strip()
        parsed["linkedin"] = f"https://www.linkedin.com/in/{username}"
    
    # Extract GitHub URL
    github_match = re.search(r'(?:github\.com/|github\s*:\s*)([^\s/]+)', text, re.I)
    if github_match:
        username = github_match.group(1).strip('/').strip()
        parsed["github"] = f"https://github.com/{username}"
    
    # Extract location
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"] and not parsed["location"]:
            parsed["location"] = ent.text
    
    # Extract job titles
    job_titles_pattern = r'\b(Software Engineer|Data Scientist|Project Manager|Product Manager|Web Developer|Full Stack|Frontend|Backend|DevOps|UX Designer|UI Designer|QA Engineer|Database Administrator|Systems Administrator|Network Engineer|Cloud Architect|AI Engineer|Machine Learning|Data Analyst|Business Analyst|Technical Writer)\b'
    job_matches = re.findall(job_titles_pattern, text, re.I)
    if job_matches:
        parsed["job_titles"] = list(set([title.strip() for title in job_matches]))
    
    # Skills extraction
    # Common technical skills
    tech_skills = [
        # Programming Languages
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin",
        "Go", "Rust", "Scala", "Perl", "R", "SQL", "Shell", "Bash", "PowerShell", "Objective-C",
        
        # Web Development
        "HTML", "CSS", "React", "Angular", "Vue", "Node.js", "Express", "Django", "Flask",
        "Spring", "ASP.NET", "Laravel", "Ruby on Rails", "jQuery", "Bootstrap", "Tailwind",
        "REST API", "GraphQL", "WebSockets", "JSON", "XML", "AJAX",
        
        # Databases
        "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "SQL Server", "Redis", "Elasticsearch",
        "DynamoDB", "Cassandra", "MariaDB", "Firebase", "Neo4j", "CouchDB",
        
        # DevOps & Cloud
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "GitLab CI", "GitHub Actions", "Travis CI",
        "Terraform", "Ansible", "Chef", "Puppet", "Vagrant", "ECS", "EKS", "Lambda", "S3", "EC2", "RDS", 
        "Heroku", "Netlify", "Vercel", "Digital Ocean",
        
        # Data Science & ML
        "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy", "SciPy", "Matplotlib",
        "Seaborn", "NLTK", "spaCy", "OpenCV", "Hadoop", "Spark", "Tableau", "Power BI", "Jupyter",
        
        # Mobile Development
        "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic", "SwiftUI", "Kotlin Multiplatform",
        
        # Tools & Others
        "Git", "SVN", "Mercurial", "Jira", "Confluence", "Notion", "Slack", "Agile", "Scrum", "Kanban",
        "CI/CD", "Test-Driven Development", "A/B Testing", "Microservices", "RESTful", "Service-Oriented Architecture"
    ]
    
    # Extract skills based on the predefined list
    for skill in tech_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.I):
            parsed["skills"].append(skill)
    
    # Soft skills
    soft_skills = [
        "Leadership", "Communication", "Teamwork", "Problem Solving", "Critical Thinking", "Time Management",
        "Decision Making", "Organization", "Adaptability", "Creativity", "Collaboration", "Conflict Resolution",
        "Emotional Intelligence", "Negotiation", "Presentation", "Analytical", "Project Management",
        "Customer Service", "Interpersonal", "Flexibility", "Attention to Detail", "Self-Motivation"
    ]
    
    for skill in soft_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.I):
            if skill not in parsed["skills"]:
                parsed["skills"].append(skill)
    
    # Extract professional summary
    summary_pattern = r'(?:SUMMARY|PROFILE|OBJECTIVE|ABOUT)(?:\s*OF\s*(?:QUALIFICATIONS|EXPERIENCE))?[\s:]*([^\n]+(?:\n[^\n]+){0,4})'
    summary_match = re.search(summary_pattern, text, re.I)
    if summary_match:
        summary_text = summary_match.group(1).strip()
        if len(summary_text) > 30:  # Avoid capturing just section headers
            parsed["professional_summary"] = summary_text
    
    # Extract experience blocks
    experience_section = extract_section(text, ["EXPERIENCE", "EMPLOYMENT", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE"])
    if experience_section:
        # Try to find company-role-date patterns
        exp_pattern = r'(.+?)\s*(?:at|@|,)?\s*(.+?)\s*(?:from|-)?\s*(\w+\s+\d{4})\s*(?:to|-)?\s*(\w+\s+\d{4}|Present)'
        exp_matches = re.finditer(exp_pattern, experience_section, re.I | re.M)
        for match in exp_matches:
            try:
                exp_item = {
                    "role": match.group(1).strip(),
                    "company": match.group(2).strip(),
                    "start_date": match.group(3).strip(),
                    "end_date": match.group(4).strip()
                }
                parsed["experience"].append(exp_item)
            except:
                continue
        
        # If we couldn't extract structured experience, save the whole section
        if not parsed["experience"]:
            lines = experience_section.split('\n')
            for i in range(len(lines)):
                line = lines[i].strip()
                if line and len(line) > 10:
                    parsed["experience"].append(line)
                if len(parsed["experience"]) >= 10:  # Limit to avoid too much data
                    break
    
    # Extract education
    education_section = extract_section(text, ["EDUCATION", "ACADEMIC", "DEGREE"])
    if education_section:
        edu_pattern = r'((?:Bachelor|Master|PhD|B\.S\.|M\.S\.|B\.A\.|M\.A\.|B\.Eng|M\.Eng|B\.Sc\.|M\.Sc\.|Ph\.D).+?)(?:at|,)?\s*((?:University|College|Institute|School).+?)(?:,|\s+)(\d{4})\s*(?:-|to|–)?\s*(\d{4}|Present)?'
        edu_matches = re.finditer(edu_pattern, education_section, re.I)
        
        for match in edu_matches:
            try:
                edu_item = {
                    "degree": match.group(1).strip(),
                    "institution": match.group(2).strip(),
                    "start_year": match.group(3).strip(),
                    "end_year": match.group(4).strip() if match.group(4) else "Present"
                }
                parsed["education"].append(edu_item)
            except:
                continue
        
        # If we couldn't extract structured education, save the whole section
        if not parsed["education"]:
            lines = education_section.split('\n')
            for i in range(len(lines)):
                line = lines[i].strip()
                if line and len(line) > 10:
                    parsed["education"].append(line)
                if len(parsed["education"]) >= 5:  # Limit to avoid too much data
                    break
    
    # Extract certifications
    cert_section = extract_section(text, ["CERTIFICATION", "CERTIFICATE"])
    if cert_section:
        cert_matches = re.finditer(r'([\w\s]+(?:Certification|Certificate|Certified|License))(?:\s*[\(\[]([\w\s]+)[\)\]])?(?:\s*:\s*([\w\s]+))?', cert_section, re.I)
        for match in cert_matches:
            cert = match.group(1).strip()
            if len(cert) > 5:
                parsed["certifications"].append(cert)
    
    # Extract languages
    languages = ["English", "Spanish", "French", "German", "Chinese", "Japanese", "Korean", "Russian", 
                "Hindi", "Arabic", "Portuguese", "Italian", "Dutch", "Swedish", "Norwegian", "Danish", 
                "Finnish", "Greek", "Turkish", "Polish", "Czech", "Hungarian", "Romanian", "Bulgarian", 
                "Ukrainian", "Hebrew", "Thai", "Vietnamese", "Malay", "Indonesian", "Tagalog", "Mandarin", 
                "Cantonese", "Bengali", "Urdu", "Persian"]
    
    for lang in languages:
        if re.search(r'\b' + re.escape(lang) + r'\b', text, re.I):
            parsed["languages"].append(lang)
    
    # Extract work preferences
    work_modes = ["Remote", "Hybrid", "On-site", "In-office", "Telecommute", "Work from home", "Flexible"]
    for mode in work_modes:
        if re.search(r'\b' + re.escape(mode) + r'\b', text, re.I):
            parsed["work_mode_preference"] = mode
            break
    
    # Extract authorization status
    auth_patterns = [
        (r'\bU\.?S\.? Citizen\b', "US Citizen"),
        (r'\bPermanent Resident\b', "Permanent Resident"),
        (r'\bGreen Card\b', "Permanent Resident"),
        (r'\bWork Authorization\b', "Work Authorization"),
        (r'\bVisa\b', "Visa Holder")
    ]
    
    for pattern, status in auth_patterns:
        if re.search(pattern, text, re.I):
            parsed["authorization_status"] = status
            break
    
    # Extract salary expectations
    salary_match = re.search(r'\$(\d{2,3})[k\,]?\s*(?:-|to)\s*\$?(\d{2,3})k?', text, re.I)
    if salary_match:
        lower = salary_match.group(1)
        upper = salary_match.group(2)
        parsed["desired_salary_range"] = f"${lower}K - ${upper}K"
    
    # Career goals, achievements, work style
    goal_match = re.search(r'career goal[s]?:?\s*(.+?)[\n\.]', text, re.I)
    if goal_match:
        parsed["career_goals"] = goal_match.group(1).strip()
    
    achievement_match = re.search(r'(?:key|notable|major|significant)?\s*achievement[s]?[:\-]?\s*(.+?)[\n\.]', text, re.I)
    if achievement_match:
        parsed["biggest_achievement"] = achievement_match.group(1).strip()
    
    style_match = re.search(r'work(?:ing)? style[:\-]?\s*(.+?)[\n\.]', text, re.I)
    if style_match:
        parsed["work_style"] = style_match.group(1).strip()
    
    # Values people might list in resumes
    values_keywords = ["integrity", "teamwork", "innovation", "excellence", "accountability", 
                      "collaboration", "diversity", "inclusion", "efficiency", "growth mindset",
                      "customer focus", "quality", "leadership", "passion", "creativity",
                      "transparency", "work-life balance", "continuous improvement"]
                      
    for value in values_keywords:
        if re.search(r'\b' + re.escape(value) + r'\b', text, re.I):
            parsed["values"].append(value.title())
    
    return parsed

def extract_section(text, section_headers):
    """
    Extract a section from the resume text based on potential section headers
    
    Args:
        text: The full resume text
        section_headers: List of possible headers for the section
        
    Returns:
        String containing the section text, or None if not found
    """
    pattern_parts = []
    for header in section_headers:
        pattern_parts.append(r'\b' + re.escape(header) + r'\b')
    
    pattern = '|'.join(pattern_parts)
    
    # Split the text into sections based on all-uppercase lines
    sections = re.split(r'\n([A-Z][A-Z\s]+[A-Z])\n', text)
    
    for i in range(len(sections) - 1):
        if re.search(pattern, sections[i], re.I):
            # Return the content of the section (the next item in the list)
            return sections[i+1]
    
    # Alternative: try to find the section using regex
    for header in section_headers:
        match = re.search(rf'(?:{re.escape(header)})\s*(?:\n|:)(.*?)(?:\n\s*\n|\Z)', text, re.I | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return None

def get_resumes_dir():
    """Get or create directory for storing resume files"""
    # Create directory within the instance folder
    instance_path = current_app.instance_path if current_app else 'instance'
    resumes_dir = os.path.join(instance_path, 'resumes')
    
    if not os.path.exists(resumes_dir):
        os.makedirs(resumes_dir)
        
    return resumes_dir

def parse_and_save_resume(data_uri: str, user_id: int) -> Tuple[str, str, str, str]:
    """
    Parse resume content from a base64 data URI and save the original file
    
    Args:
        data_uri: Base64 data URI (e.g., "data:application/pdf;base64,...")
        user_id: User ID for file organization
        
    Returns:
        Tuple of (parsed_text, file_path, file_name, mime_type)
    """
    if not data_uri or not data_uri.startswith('data:'):
        return "", "", "", ""
    
    try:
        # Split the header from the Base64 data
        header, encoded = data_uri.split(",", 1)
        file_type = header.split(";")[0].split(":")[1]
        
        # Get file extension from mime type
        ext_mapping = {
            'application/pdf': '.pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/msword': '.doc',
            'text/plain': '.txt'
        }
        file_extension = ext_mapping.get(file_type, '.bin')
        
        # Decode the Base64 data
        file_data = base64.b64decode(encoded)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp:
            temp.write(file_data)
            temp_filename = temp.name
            
        # Parse the file to extract text
        parsed_text = ""
        if file_extension == '.pdf':
            parsed_text = parse_pdf(temp_filename)
        elif file_extension == '.docx':
            parsed_text = parse_docx(temp_filename)
        elif file_extension == '.txt':
            with open(temp_filename, 'r', errors='ignore') as f:
                parsed_text = f.read()
        else:
            parsed_text = f"[Unsupported file format: {file_type}]"
        
        # Generate a unique filename for storage
        unique_id = str(uuid.uuid4())
        safe_filename = f"resume_{user_id}_{unique_id}{file_extension}"
        original_filename = f"resume{file_extension}"
        
        # Copy the file to the resumes directory
        resumes_dir = get_resumes_dir()
        dest_path = os.path.join(resumes_dir, safe_filename)
        
        # Copy the file
        shutil.copy2(temp_filename, dest_path)
        
        # Clean up the temporary file
        os.unlink(temp_filename)
        
        return parsed_text, dest_path, original_filename, file_type
        
    except Exception as e:
        logger.error(f"Error processing resume: {str(e)}")
        return f"[Error processing resume: {str(e)}]", "", "", ""

def parse_pdf(filepath: str) -> str:
    """Extract text from a PDF file"""
    if not HAS_PYPDF2:
        return "[Error: PDF parsing library not available]"
        
    try:
        text = ""
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        return f"[Error parsing PDF: {str(e)}]"

def parse_docx(filepath: str) -> str:
    """Extract text from a DOCX file"""
    if not HAS_DOCX:
        return "[Error: DOCX parsing library not available]"
        
    try:
        doc = docx.Document(filepath)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        logger.error(f"Error parsing DOCX: {str(e)}")
        return f"[Error parsing DOCX: {str(e)}]"

def get_resume_file(user_id: int) -> Optional[str]:
    """Get the path to the user's resume file if it exists"""
    resumes_dir = get_resumes_dir()
    # List all files in the resumes directory
    if os.path.exists(resumes_dir):
        for filename in os.listdir(resumes_dir):
            # Check if filename matches the pattern for this user
            if filename.startswith(f"resume_{user_id}_") and os.path.isfile(os.path.join(resumes_dir, filename)):
                return os.path.join(resumes_dir, filename)
    return None
