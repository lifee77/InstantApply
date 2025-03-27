from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, session
from flask_login import login_required, current_user
import os
import json
from werkzeug.utils import secure_filename
import PyPDF2
import docx2txt
import datetime
import logging
import time

from models.user import db, User
from forms.profile import ProfileForm

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    # Check if we should direct user to upload resume first
    if request.method == 'GET' and not current_user.resume_file_path and not session.get('skip_resume_upload'):
        return redirect(url_for('profile.upload_resume'))
    
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
                    
                    # Ensure job_titles is a list (not a dict or something else)
                    if not isinstance(job_titles, list):
                        job_titles = list(job_titles) if hasattr(job_titles, '__iter__') else [str(job_titles)]
                        current_app.logger.warning(f"Converted job_titles to list: {job_titles}")
                    
                    # The property setter will handle JSON serialization
                    current_user.desired_job_titles = job_titles
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
                
            # Process projects
            projects_json = request.form.get('projects')
            if projects_json:
                current_user.projects = json.loads(projects_json)
                
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
        
        # Process demographic information fields
        current_user.race_ethnicity = request.form.get('race_ethnicity')
        current_user.gender = request.form.get('gender')
        
        # Process graduation date
        grad_date = request.form.get('graduation_date')
        if grad_date:
            try:
                current_user.graduation_date = datetime.datetime.strptime(grad_date, '%Y-%m-%d').date()
            except ValueError:
                current_user.graduation_date = None
        else:
            current_user.graduation_date = None
        
        current_user.disability_status = request.form.get('disability_status')
        current_user.military_status = request.form.get('military_status')
        current_user.military_branch = request.form.get('military_branch')
        
        # Process military discharge date
        discharge_date = request.form.get('military_discharge_date')
        if discharge_date:
            try:
                current_user.military_discharge_date = datetime.datetime.strptime(discharge_date, '%Y-%m-%d').date()
            except ValueError:
                current_user.military_discharge_date = None
        else:
            current_user.military_discharge_date = None
            
        current_user.veteran_status = request.form.get('veteran_status')
        current_user.needs_sponsorship = 'needs_sponsorship' in request.form
        current_user.visa_status = request.form.get('visa_status')
        
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
                except Exception as e:
                    flash(f'Error processing resume: {str(e)}', 'danger')
        
        # Save all changes to database
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.profile'))
    
    # Reset the skip_resume_upload flag if it was set
    if session.get('skip_resume_upload'):
        session.pop('skip_resume_upload')
    
    # For GET requests
    return render_template('profile.html', form=form)


@profile_bp.route('/profile/upload-resume', methods=['GET', 'POST'])
@login_required
def upload_resume():
    form = ProfileForm()
    
    if request.method == 'POST':
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file and file.filename != '':
                try:
                    # Track start time for parsing
                    start_time = time.time()
                    
                    # Process the resume file
                    file_path, filename, resume_text = process_resume_file(file)
                    
                    # Log parsing time for debugging
                    parsing_time = time.time() - start_time
                    current_app.logger.info(f"Resume parsed in {parsing_time:.2f} seconds")
                    
                    if file_path:
                        # Update user's resume information
                        current_user.resume_filename = filename
                        current_user.resume_file_path = file_path
                        if resume_text:
                            current_user.resume = resume_text
                        
                        # Save changes to database
                        db.session.commit()
                        
                        # Redirect with success message (only once)
                        flash('Resume uploaded and parsed successfully. Please review your profile information.', 'success')
                        return redirect(url_for('profile.profile'))
                except Exception as e:
                    current_app.logger.error(f"Error in resume upload: {str(e)}")
                    flash(f'Error processing resume: {str(e)}', 'danger')
                    return redirect(url_for('profile.upload_resume'))
        else:
            flash('No resume file selected.', 'warning')
    
    # Skip the resume upload if requested
    if request.args.get('skip') == 'true':
        session['skip_resume_upload'] = True
        return redirect(url_for('profile.profile'))
    
    return render_template('upload_resume.html', form=form)


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
    """Process an uploaded resume file, extract text, and auto-fill fields."""
    from utils.document_parser import parse_pdf  # Use parse_pdf which includes Gemini integration
    
    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    # Ensure upload folder exists
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    # Extract text from the file
    resume_text = extract_text_from_resume(file_path)
    
    # Parse resume using the updated parse_pdf function that uses Gemini first
    parsed_data = parse_pdf(file_path)
    current_app.logger.info(f"Auto-filled data: {parsed_data}")
    # Auto-fill fields into current_user with better structure for experience
    if parsed_data.get("name"):
        current_user.name = parsed_data["name"]
    if parsed_data.get("linkedin"):
        current_user.linkedin_url = parsed_data["linkedin"]
    if parsed_data.get("professional_summary"):
        current_user.professional_summary = parsed_data["professional_summary"]
    if parsed_data.get("skills"):
        current_user.skills = json.dumps(parsed_data["skills"])
    
    # Improved experience handling
    if parsed_data.get("experience"):
        # Convert experience from objects to properly formatted JSON
        current_user.experience = json.dumps(parsed_data["experience"])
    
    # Projects handling
    if parsed_data.get("projects"):
        current_user.projects = json.dumps(parsed_data["projects"])
    
    # Other fields
    if parsed_data.get("certifications"):
        current_user.certifications = json.dumps([{"name": cert, "organization": "", "expiry": ""} for cert in parsed_data["certifications"]])
    if parsed_data.get("languages"):
        current_user.languages = json.dumps([{"language": lang, "proficiency": "Intermediate"} for lang in parsed_data["languages"]])
    if parsed_data.get("values"):
        current_user.applicant_values = json.dumps(parsed_data["values"])
    if parsed_data.get("work_mode_preference"):
        current_user.work_mode_preference = parsed_data["work_mode_preference"]
    if parsed_data.get("career_goals"):
        current_user.career_goals = parsed_data["career_goals"]
    if parsed_data.get("biggest_achievement"):
        current_user.biggest_achievement = parsed_data["biggest_achievement"]
    if parsed_data.get("work_style"):
        current_user.work_style = parsed_data["work_style"]
    if parsed_data.get("industry_attraction"):
        current_user.industry_attraction = parsed_data["industry_attraction"]
    
    # If we have job titles from the resume, use them
    if parsed_data.get("job_titles"):
        current_user.desired_job_titles = parsed_data["job_titles"]
    return file_path, filename, resume_text