from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
import os
import json
from werkzeug.utils import secure_filename
import PyPDF2
import docx2txt
import datetime

from models.user import db, User
from forms.profile import ProfileForm

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    if request.method == 'POST':
        # Process standard form fields
        current_user.name = request.form.get('name', current_user.name)
        current_user.professional_summary = request.form.get('professional_summary')
        current_user.willing_to_relocate = 'willing_to_relocate' in request.form
        current_user.authorization_status = request.form.get('authorization_status')
        current_user.linkedin_url = request.form.get('linkedin_url')
        
        # Process JSON fields
        current_user.desired_job_titles = request.form.get('desired_job_titles')
        current_user.portfolio_links = request.form.get('portfolio_links')
        current_user.desired_salary_range = request.form.get('desired_salary_range')
        current_user.work_mode_preference = request.form.get('work_mode_preference')
        
        # Process date field
        start_date = request.form.get('available_start_date')
        if start_date:
            try:
                current_user.available_start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                current_user.available_start_date = None
        else:
            current_user.available_start_date = None
            
        current_user.preferred_company_type = request.form.get('preferred_company_type')
        current_user.certifications = request.form.get('certifications')
        current_user.languages = request.form.get('languages')
        current_user.career_goals = request.form.get('career_goals')
        current_user.biggest_achievement = request.form.get('biggest_achievement')
        current_user.work_style = request.form.get('work_style')
        current_user.industry_attraction = request.form.get('industry_attraction')
        current_user.applicant_values = request.form.get('applicant_values')
        
        # Process resume text
        current_user.resume = request.form.get('resume', '')
        
        # Process resume file if uploaded
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file and file.filename != '':
                try:
                    file_path, filename, resume_text = process_resume_file(file)
                    if file_path:
                        # Update user's resume information
                        current_user.resume_filename = filename
                        current_user.resume_file_path = file_path
                        if resume_text:
                            current_user.resume = resume_text
                        
                        flash('Resume uploaded and processed successfully.', 'success')
                except Exception as e:
                    flash(f'Error processing resume: {str(e)}', 'danger')
        
        # Save all changes to database
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.profile'))
    
    # For GET requests
    return render_template('profile.html', form=form)


def extract_text_from_resume(file_path):
    """Extract text from various file formats."""
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            with open(file_path, 'rb') as file:
                # Replace deprecated PdfFileReader with PdfReader
                reader = PyPDF2.PdfReader(file)
                text = ''
                # Update to use the new len(reader.pages) and reader.pages[page_num]
                for page_num in range(len(reader.pages)):
                    text += reader.pages[page_num].extract_text()
                return text
                
        elif file_ext in ['.docx', '.doc']:
            text = docx2txt.process(file_path)
            return text
            
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
                
        else:
            return "Unsupported file format."
    except Exception as e:
        current_app.logger.error(f"Error extracting text from resume: {str(e)}")
        return f"Error processing file: {str(e)}"


def process_resume_file(file):
    """Process an uploaded resume file."""
    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    
    # Ensure upload folder exists
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Extract text from the file
    try:
        resume_text = extract_text_from_resume(file_path)
        return file_path, filename, resume_text
    except Exception as e:
        current_app.logger.error(f"Error extracting text from resume: {str(e)}")
        return file_path, filename, f"Error extracting text: {str(e)}"
