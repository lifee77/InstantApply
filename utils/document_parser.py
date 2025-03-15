import os
import logging
import tempfile
import base64
import uuid
import shutil
from typing import Tuple, Optional
from werkzeug.utils import secure_filename
from flask import current_app

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
