from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
import os
import json
from werkzeug.utils import secure_filename
import PyPDF2
import docx2txt
import datetime
import logging

from models.user import db, User
from forms.profile import ProfileForm

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    if request.method == 'POST':
        # Debug logging
        current_app.logger.debug(f"Form data received: {list(request.form.keys())}")
        
        # Process standard form fields
        current_user.name = request.form.get('name', current_user.name)
        current_user.professional_summary = request.form.get('professional_summary')
        current_user.willing_to_relocate = 'willing_to_relocate' in request.form
        current_user.authorization_status = request.form.get('authorization_status')
        current_user.linkedin_url = request.form.get('linkedin_url')
        
        # Process JSON fields with proper error handling
        try:
            # Process desired job titles
            job_titles_json = request.form.get('desired_job_titles')
            if job_titles_json:
                current_app.logger.debug(f"Raw job titles: {job_titles_json}")
                try:
                    job_titles = json.loads(job_titles_json)
                    current_app.logger.debug(f"Parsed job titles type: {type(job_titles)}")
                    current_app.logger.debug(f"Parsed job titles: {job_titles}")
                    
                    # Ensure job_titles is a list (not a dict or something else)
                    if not isinstance(job_titles, list):
                        job_titles = list(job_titles) if hasattr(job_titles, '__iter__') else [str(job_titles)]
                        current_app.logger.warning(f"Converted job_titles to list: {job_titles}")
                    
                    # The property setter will handle JSON serialization
                    current_user.desired_job_titles = job_titles
                    current_app.logger.info(f"Processed job titles: {current_user.desired_job_titles}")
                    current_app.logger.debug(f"Stored representation: {current_user._desired_job_titles}")
                except Exception as e:
                    current_app.logger.error(f"Error processing job titles: {str(e)}")
                    flash(f"Error processing job titles: {str(e)}", "danger")
            
            # Process portfolio links
            portfolio_links_json = request.form.get('portfolio_links')
            if portfolio_links_json:
                current_app.logger.debug(f"Raw portfolio links: {portfolio_links_json}")
                portfolio_links = json.loads(portfolio_links_json)
                current_user.portfolio_links = portfolio_links
            
            # Process certifications
            certifications_json = request.form.get('certifications')
            if certifications_json:
                current_user.certifications = json.loads(certifications_json)
            
            # Process languages
            languages_json = request.form.get('languages')
            if languages_json:
                current_user.languages = json.loads(languages_json)
            
            # Process applicant values
            values_json = request.form.get('applicant_values')
            if values_json:
                current_user.applicant_values = json.loads(values_json)
                
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON parsing error: {str(e)}")
            flash(f"Error processing form data: {str(e)}", "danger")
        
        # Process other fields
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
        current_user.career_goals = request.form.get('career_goals')
        current_user.biggest_achievement = request.form.get('biggest_achievement')
        current_user.work_style = request.form.get('work_style')
        current_user.industry_attraction = request.form.get('industry_attraction')
        
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
                reader = PyPDF2.PdfReader(file)
                text = ''
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
