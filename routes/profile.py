from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models.user import db, User
from forms.profile import ProfileForm
import os
import json
from datetime import datetime

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
                current_user.available_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
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
        
        # Process resume file if uploaded
        if 'resume' in request.files and request.files['resume'].filename:
            resume_file = request.files['resume']
            if resume_file:
                filename = secure_filename(resume_file.filename)
                upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
                
                # Create uploads directory if it doesn't exist
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                file_path = os.path.join(upload_dir, filename)
                resume_file.save(file_path)
                
                # Update user model with file details
                current_user.resume_file_path = file_path
                current_user.resume_filename = filename
                current_user.resume_mime_type = resume_file.content_type
                
                # Here you could add code to parse the resume text and extract skills
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.profile'))
    
    return render_template('profile.html', form=form)
