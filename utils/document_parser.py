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
    clean_text = text.replace('\n', '. ').replace('  ', ' ')

    doc = nlp(clean_text)

    parsed = {
        "name": None,
        "linkedin": None,
        "skills": [],
        "experience": [],
        "certifications": [],
        "languages": [],
        "professional_summary": None,
        "authorization_status": None,
        "work_mode_preference": None,
        "desired_salary_range": None,
        "career_goals": None,
        "biggest_achievement": None,
        "work_style": None,
        "industry_attraction": None,
        "values": [],
        "education": [],
    }

    # Extract name (improved)
    for ent in doc.ents:
        if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
            parsed["name"] = ent.text
            break
    
    # Fallback: check if the first line looks like a name
    lines = text.strip().split("\n")
    if not parsed["name"] and lines:
        first_line = lines[0].strip()
        if len(first_line.split()) in [2, 3] and first_line.istitle():
            parsed["name"] = first_line    
    
    # Extract name
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            parsed["name"] = ent.text
            break

    # LinkedIn
    linkedin_match = re.search(r'https?://(www\.)?linkedin\.com/in/[^\s]+', text)
    if linkedin_match:
        parsed["linkedin"] = linkedin_match.group(0)

    # Skills
    predefined_skills = ["Python", "SQL", "Flask", "JavaScript", "Docker", "Leadership", "Agile", "Machine Learning"]
    for token in doc:
        if token.text in predefined_skills:
            parsed["skills"].append(token.text)

    # Work experience
    for sent in doc.sents:
        if re.search(r'\b(Engineer|Manager|Intern|Developer|Consultant|Analyst|Specialist)\b', sent.text, re.I):
            parsed["experience"].append(sent.text.strip())

    # Certifications
    for sent in doc.sents:
        if re.search(r'certified|certification|certificate', sent.text, re.I):
            parsed["certifications"].append(sent.text.strip())

    # Languages
    lang_matches = re.findall(r'(English|Spanish|French|German|Chinese|Russian|Arabic)', text, re.I)
    parsed["languages"] = list(set([lang.capitalize() for lang in lang_matches]))

    # Summary
    summary_match = re.search(r'(Summary|Objective)\s*[:\-]?\s*(.+)', text, re.IGNORECASE)
    if summary_match:
        parsed["professional_summary"] = summary_match.group(2).strip()

    # Values
    values_keywords = ["integrity", "teamwork", "innovation", "excellence", "accountability"]
    parsed["values"] = [word for word in values_keywords if word in text.lower()]

    # Career goals, achievements, work style, industry attraction:
    goal_match = re.search(r'career goal[s]?:?\s*(.+?)[\n\.]', text, re.IGNORECASE)
    if goal_match:
        parsed["career_goals"] = goal_match.group(1).strip()

    achievement_match = re.search(r'achievements?[:\-]?\s*(.+?)[\n\.]', text, re.IGNORECASE)
    if achievement_match:
        parsed["biggest_achievement"] = achievement_match.group(1).strip()

    style_match = re.search(r'work style[:\-]?\s*(.+?)[\n\.]', text, re.IGNORECASE)
    if style_match:
        parsed["work_style"] = style_match.group(1).strip()

    attraction_match = re.search(r'industry attraction[:\-]?\s*(.+?)[\n\.]', text, re.IGNORECASE)
    if attraction_match:
        parsed["industry_attraction"] = attraction_match.group(1).strip()

    # Education block extractor
    edu_matches = re.findall(r'(Bachelor|Master|PhD|B\.Sc\.|M\.Sc\.|Bachelors|Masters|Doctorate).*?(University|College|School).*?(\d{4})?', text, re.IGNORECASE)
    for match in edu_matches:
        parsed["education"].append(" ".join([m for m in match if m]))

    return parsed

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
