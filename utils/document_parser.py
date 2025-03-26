import os
import logging
import tempfile
import base64
import uuid
import shutil
from typing import Tuple, Optional, List, Dict, Any
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

# Load spaCy model only once when module is imported
try:
    nlp = spacy.load("en_core_web_sm")
except:
    logger.warning("Failed to load spaCy model. Using basic parser instead.")
    nlp = None

# Predefined lists of common skills and keywords
TECHNICAL_SKILLS = set([
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "swift",
    "react", "vue", "angular", "node.js", "express", "django", "flask", "spring", 
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "matplotlib",
    "sql", "nosql", "mongodb", "postgresql", "mysql", "oracle", "dynamodb",
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "gitlab",
    "git", "github", "bitbucket", "jira", "confluence", "agile", "scrum"
])

def parse_resume_with_spacy(text):
    """
    Parse resume text using spaCy NLP to extract structured information.
    Improved version with better pattern recognition and performance.
    
    Args:
        text: The plain text content of a resume
        
    Returns:
        Dictionary containing extracted resume components
    """
    # Initialize parsed data structure
    parsed = {
        "name": None,
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "location": None,
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "languages": [],
        "job_titles": [],
        "professional_summary": None,
        "work_mode_preference": None,
        "career_goals": None,
        "biggest_achievement": None,
        "work_style": None,
        "industry_attraction": None,
        "values": []
    }
    
    try:
        # Don't process empty text
        if not text or len(text.strip()) == 0:
            return parsed
            
        # Clean the text for better processing (remove excessive whitespace)
        clean_text = re.sub(r'\s+', ' ', text).strip()
        
        # Original text lines for section-based extraction
        orig_lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
        
        # Extract basic information with regex (faster than NLP for these patterns)
        # Name - first line if it looks like a name (1-4 words)
        if orig_lines and len(orig_lines[0].split()) <= 4:
            parsed["name"] = orig_lines[0]
        
        # Email
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            parsed["email"] = email_match.group(0)
        
        # Phone
        phone_matches = re.findall(r'(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', text)
        if phone_matches:
            parsed["phone"] = ''.join(phone_matches[0]).strip()
        
        # LinkedIn URL
        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+/?', text, re.IGNORECASE)
        if linkedin_match:
            parsed["linkedin"] = "https://" + linkedin_match.group(0)
        
        # GitHub URL
        github_match = re.search(r'github\.com/[\w-]+/?', text, re.IGNORECASE)
        if github_match:
            parsed["github"] = "https://" + github_match.group(0)
        
        # Extract clearly marked sections
        sections = extract_resume_sections(text)
        
        # === SKILLS EXTRACTION (improved) ===
        # First try section-based extraction
        skills = []
        
        if 'skills' in sections:
            skills_text = sections['skills']
            
            # Try different common separators
            for sep in [',', '•', '·', '|', '/', ';', '\n']:
                if sep in skills_text:
                    candidate_skills = [s.strip() for s in skills_text.split(sep) if s.strip()]
                    if len(candidate_skills) > 1:
                        skills = candidate_skills
                        break
            
            # If no skills found yet, use general text processing
            if not skills:
                # Fallback to basic word extraction for single-word skills
                words = re.findall(r'\b\w+\b', skills_text.lower())
                skills = [word for word in words if word in TECHNICAL_SKILLS]
                    
            # Remove any skills that are just numbers or single characters
            skills = [s for s in skills if not s.isdigit() and len(s) > 1]
            
            parsed["skills"] = skills
        
        # === EXPERIENCE EXTRACTION (improved) ===
        experiences = []
        
        if 'experience' in sections:
            exp_text = sections['experience']
            
            # Split experience by date patterns
            exp_entries = re.split(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\s*[-–—]\s*(?:\d{4}|Present|Current|Now))\b', exp_text, flags=re.IGNORECASE)
            
            # If no dates found, try another common format
            if len(exp_entries) <= 1:
                exp_entries = re.split(r'\b(\d{4}\s*[-–—]\s*(?:\d{4}|Present|Current|Now))\b', exp_text)
            
            # Process each entry
            current_period = None
            for i, entry in enumerate(exp_entries):
                # If this looks like a time period, store it and continue
                if re.search(r'\d{4}', entry) and len(entry.split()) <= 5:
                    current_period = entry.strip()
                    continue
                
                # Skip empty entries
                if not entry.strip():
                    continue
                    
                # This must be a job description
                if current_period:
                    lines = entry.strip().split('\n')
                    
                    # First line is typically job title and/or company
                    first_line = lines[0].strip() if lines else ""
                    
                    # Try to extract job title and company if there's an "at" or similar separator
                    title_company = re.search(r'(.+?)\s+(?:at|@|with|for)\s+(.+?)(?:\.|\n|$)', first_line, re.IGNORECASE)
                    
                    job_title = None
                    company = None
                    
                    if title_company:
                        job_title = title_company.group(1).strip()
                        company = title_company.group(2).strip()
                    else:
                        # If no clear separator, just use the first line as title
                        job_title = first_line
                        
                        # Try to find company name in second line
                        if len(lines) > 1:
                            company = lines[1].strip()
                    
                    # Create the experience entry
                    experiences.append({
                        "title": job_title,
                        "company": company,
                        "period": current_period,
                        "description": entry.strip()
                    })
        
        parsed["experience"] = experiences
        
        # === EDUCATION EXTRACTION ===
        if 'education' in sections:
            edu_text = sections['education']
            parsed["education"] = edu_text.split('\n') if '\n' in edu_text else [edu_text]
        
        # === CERTIFICATIONS EXTRACTION ===
        if 'certifications' in sections:
            cert_text = sections['certifications']
            # Split by common list item indicators
            certs = re.split(r'[•·]|\n', cert_text)
            parsed["certifications"] = [cert.strip() for cert in certs if cert.strip()]
        
        # === LANGUAGES EXTRACTION ===
        if 'languages' in sections:
            lang_text = sections['languages']
            # Split languages by common separators
            langs = re.split(r'[,;]|\n', lang_text)
            parsed["languages"] = [lang.strip() for lang in langs if lang.strip()]
        
        # === SUMMARY EXTRACTION ===
        if 'summary' in sections:
            parsed["professional_summary"] = sections['summary'].strip()
        
        # === PROJECT EXTRACTION ===
        if 'projects' in sections:
            proj_text = sections['projects']
            # Simple extraction - split by project names that likely have dates
            project_parts = re.split(r'\n(?=\w+[^:]+(?:\d{4}|github|link))', proj_text)
            parsed["projects"] = [{"name": p.strip().split('\n')[0], "description": p.strip()} for p in project_parts if p.strip()]
        
        # Extract job titles from experience entries for desired job titles
        if experiences:
            job_titles = [exp["title"] for exp in experiences if exp.get("title")]
            if job_titles:
                parsed["job_titles"] = job_titles[:3]  # Take the first three as most relevant
        
        logger.info("Resume parsing completed successfully")
        return parsed
    except Exception as e:
        logger.error(f"Error in resume parsing: {str(e)}")
        return parsed  # Return whatever we've parsed so far
        
def extract_resume_sections(text):
    """
    Extract labeled sections from a resume text.
    
    Args:
        text: Full resume text
        
    Returns:
        Dictionary mapping section names to their content
    """
    # Common section headers in resumes
    section_headers = {
        'summary': ['summary', 'professional summary', 'profile', 'about me', 'objective'],
        'experience': ['experience', 'work experience', 'employment history', 'work history', 'professional experience'],
        'skills': ['skills', 'technical skills', 'core competencies', 'competencies', 'expertise', 'technologies'],
        'education': ['education', 'academic background', 'academic history', 'qualifications', 'degrees'],
        'projects': ['projects', 'personal projects', 'professional projects', 'key projects'],
        'certifications': ['certifications', 'certificates', 'professional certifications', 'credentials'],
        'languages': ['languages', 'language proficiency', 'spoken languages', 'foreign languages']
    }
    
    sections = {}
    
    # Convert text to lowercase for case-insensitive section header matching
    lower_text = text.lower()
    
    # Find potential section headers (capitalized words followed by a colon or newline)
    header_candidates = re.finditer(r'^([A-Za-z\s]+)(?::|$)', text, re.MULTILINE)
    
    # Get all header positions
    headers = []
    for match in header_candidates:
        header_text = match.group(1).strip().lower()
        
        # Find which section this header belongs to
        for section, keywords in section_headers.items():
            if header_text in keywords:
                headers.append((match.start(), section))
                break
    
    # Sort headers by position
    headers.sort()
    
    # Extract sections based on header positions
    for i, (pos, section) in enumerate(headers):
        # Section content goes from this header to the next (or end of text)
        start_pos = pos + text[pos:].find('\n') + 1  # Start after the header line
        end_pos = len(text)
        
        # If there's a next header, use its position as the end
        if i < len(headers) - 1:
            end_pos = headers[i+1][0]
            
        section_content = text[start_pos:end_pos].strip()
        sections[section] = section_content
        
    return sections

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
