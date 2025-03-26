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
        "projects": [],  # Added projects section
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
    
    # Extract experience blocks - IMPROVED VERSION
    experience_section = extract_section(text, ["EXPERIENCE", "EMPLOYMENT", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE"])
    if experience_section:
        # Try to extract experience entries with more details
        exp_entries = re.split(r'\n(?=[A-Z][a-zA-Z\s]+(?:,|\s+at|\s+\-|\s+\|)\s+[A-Za-z\s]+)', experience_section)
        
        for entry in exp_entries:
            lines = entry.strip().split('\n')
            if not lines:
                continue
                
            # Look for company/role line first
            title_line = lines[0].strip()
            
            # Try to extract company and role
            role_company_match = re.match(r'([^,|]+)(?:,|\s+at|\s+\-|\s+\|)\s+(.+)', title_line)
            
            # Try to extract dates
            date_pattern = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z.\s,]*\d{4}\s*(?:–|-|to|until|present|current|\d{4})'
            date_match = re.search(date_pattern, entry, re.I)
            
            # Try to extract location
            location_match = re.search(r'(?:New York|San Francisco|Remote|Hybrid|Boston|Seattle|Austin|Chicago|London|Berlin|Tokyo|\w+,\s*[A-Z]{2})', entry)
            
            exp_item = {}
            
            # Set role and company
            if role_company_match:
                exp_item["role"] = role_company_match.group(1).strip()
                exp_item["company"] = role_company_match.group(2).strip()
            else:
                # No clear separation, use the title line as role
                exp_item["role"] = title_line
                exp_item["company"] = ""
            
            # Set dates
            if date_match:
                date_text = date_match.group(0)
                exp_item["dates"] = date_text.strip()
            else:
                exp_item["dates"] = ""
            
            # Set location if found
            if location_match:
                exp_item["location"] = location_match.group(0).strip()
            else:
                exp_item["location"] = ""
            
            # Extract responsibilities/achievements
            responsibilities = []
            for i in range(1, min(len(lines), 10)):  # Limit to 10 lines per entry
                line = lines[i].strip()
                if line and len(line) > 10 and not re.match(date_pattern, line, re.I):
                    # Clean up bullet points
                    line = re.sub(r'^[•\-\*\>\◦\‣\⁃\⦿\⦾\+]\s*', '', line)
                    if line:
                        responsibilities.append(line)
            
            exp_item["responsibilities"] = responsibilities
            
            if exp_item["role"] or exp_item["company"]:
                parsed["experience"].append(exp_item)
        
        # If we couldn't extract structured experience, try a simpler approach
        if not parsed["experience"]:
            # First look for date ranges to split experience entries
            date_positions = []
            for match in re.finditer(r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z.\s,]*\d{4}', experience_section, re.I):
                date_positions.append(match.start())
            
            if date_positions:
                # Split by date positions
                date_positions.append(len(experience_section))
                for i in range(len(date_positions) - 1):
                    start = date_positions[i]
                    end = date_positions[i+1]
                    
                    # Extract the experience entry
                    entry_text = experience_section[start:end].strip()
                    if entry_text:
                        lines = entry_text.split('\n')
                        
                        exp_item = {
                            "role": lines[0] if lines else "Unknown",
                            "company": lines[1] if len(lines) > 1 else "",
                            "dates": re.search(r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z.\s,]*\d{4}', lines[0] if lines else "", re.I).group(0) if re.search(r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z.\s,]*\d{4}', lines[0] if lines else "", re.I) else "",
                            "location": "",
                            "responsibilities": [line.strip() for line in lines[2:] if line.strip() and len(line.strip()) > 10 and line.strip()[0] in '•-*']
                        }
                        parsed["experience"].append(exp_item)
            
            # If still no experience entries, just take the raw text
            if not parsed["experience"]:
                lines = experience_section.split('\n')
                current_entry = {}
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # If line looks like a title (not a bullet point), start new entry
                    if not line.startswith(('•', '-', '*')) and len(line) < 80:
                        if current_entry and current_entry.get("role"):
                            parsed["experience"].append(current_entry)
                        current_entry = {"role": line, "company": "", "dates": "", "responsibilities": []}
                    elif current_entry:  # Add as responsibility to current entry
                        current_entry["responsibilities"].append(line.lstrip('•-* '))
                
                # Add the last entry if it exists
                if current_entry and current_entry.get("role"):
                    parsed["experience"].append(current_entry)
    
    # Extract projects section
    projects_section = extract_section(text, ["PROJECTS", "PERSONAL PROJECTS", "PORTFOLIO PROJECTS", "SIDE PROJECTS", "ACADEMIC PROJECTS"])
    if projects_section:
        # Split project entries by recognizable patterns
        project_entries = re.split(r'\n(?=[A-Z][^\n]+(?:\n|:))', projects_section)
        
        for entry in project_entries:
            lines = entry.strip().split('\n')
            if not lines:
                continue
            
            project_item = {
                "name": "",
                "description": "",
                "technologies": [],
                "link": "",
                "details": []
            }
            
            # Extract project name
            title_line = lines[0].strip()
            project_item["name"] = title_line.split(':')[0].strip() if ':' in title_line else title_line
            
            # Look for GitHub/project link
            link_match = re.search(r'((?:github\.com|gitlab\.com)/[\w\-/]+|(?:http|https)://[\w\-./]+)', entry, re.I)
            if link_match:
                project_item["link"] = link_match.group(0)
            
            # Extract technologies used
            tech_list = []
            for skill in tech_skills:
                if re.search(r'\b' + re.escape(skill) + r'\b', entry, re.I):
                    tech_list.append(skill)
            project_item["technologies"] = tech_list
            
            # Extract description and details
            description_started = False
            for i in range(1, len(lines)):
                line = lines[i].strip()
                if not line:
                    continue
                
                # Skip if it's just a link
                if re.match(r'^https?://', line):
                    continue
                
                # The first non-empty line is likely the description
                if not description_started:
                    project_item["description"] = line
                    description_started = True
                else:
                    # Clean up bullet points
                    detail = re.sub(r'^[•\-\*\>\◦\‣\⁃\⦿\⦾\+]\s*', '', line)
                    if detail:
                        project_item["details"].append(detail)
            
            if project_item["name"]:
                parsed["projects"].append(project_item)
    
    # If no projects section was found, try to identify projects in the experience section
    if not parsed["projects"] and parsed["experience"]:
        for exp in parsed["experience"]:
            # Look for project mentions in responsibilities
            for resp in exp.get("responsibilities", []):
                if re.search(r'\b(project|developed|built|created|designed|implemented)\b', resp, re.I):
                    # This responsibility likely describes a project
                    project_item = {
                        "name": re.search(r'"([^"]+)"', resp) and re.search(r'"([^"]+)"', resp).group(1) or f"Project at {exp.get('company', '')}",
                        "description": resp,
                        "technologies": [],
                        "details": []
                    }
                    
                    # Extract technologies
                    for skill in tech_skills:
                        if re.search(r'\b' + re.escape(skill) + r'\b', resp, re.I):
                            project_item["technologies"].append(skill)
                    
                    parsed["projects"].append(project_item)
    
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
