#!/usr/bin/env python3
"""
InstantApply - Main application entry point
"""
import os
import sys

# Add the project root directory to Python's path before any imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_migrate import Migrate
import json
import uuid
import datetime
import asyncio

# Import modules
from models.user import db, User
from models.application import Application
from models.job_recommendation import JobRecommendation
from routes.profile import profile_bp
from routes.api import api_bp
from routes.auth import auth_bp
from routes.debug import debug_bp

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(BASE_DIR, 'brand_new_db.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    
    # Register debug blueprint if in debug mode
    if app.debug:
        app.register_blueprint(debug_bp)

    
    @app.template_filter('from_json')
    def from_json_filter(s):
        try:
            return json.loads(s)
        except Exception:
            return [] 

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            # Get application count
            application_count = Application.query.filter_by(user_id=current_user.id).count()
            
            # Calculate profile completion with a more comprehensive approach
            # Define field groups with weights
            field_groups = {
                'basic_info': {
                    'weight': 20,
                    'fields': [
                        ('name', current_user.name),
                        ('email', current_user.email),
                        ('professional_summary', current_user.professional_summary),
                        ('linkedin_url', current_user.linkedin_url)
                    ]
                },
                'skills_experience': {
                    'weight': 30,
                    'fields': [
                        ('skills', current_user.skills),
                        ('experience', current_user.experience),
                        ('projects', current_user._projects)
                    ]
                },
                'resume': {
                    'weight': 15,
                    'fields': [
                        ('resume_file', current_user.resume_file_path)
                    ]
                },
                'work_preferences': {
                    'weight': 10,
                    'fields': [
                        ('desired_salary_range', current_user.desired_salary_range),
                        ('work_mode_preference', current_user.work_mode_preference),
                        ('available_start_date', current_user.available_start_date)
                    ]
                },
                'additional_qualifications': {
                    'weight': 15,
                    'fields': [
                        ('certifications', current_user._certifications),
                        ('languages', current_user._languages)
                    ]
                },
                'professional_details': {
                    'weight': 10,
                    'fields': [
                        ('career_goals', current_user.career_goals),
                        ('work_style', current_user.work_style),
                        ('applicant_values', current_user._applicant_values)
                    ]
                }
            }
            
            # Calculate completion for each group
            group_completions = {}
            overall_completion = 0
            
            for group, data in field_groups.items():
                weight = data['weight']
                fields = data['fields']
                
                # Calculate how many fields in this group are completed
                completed = sum(1 for _, value in fields if value)
                total = len(fields)
                
                # Calculate group completion percentage
                group_pct = int((completed / max(total, 1)) * 100)
                group_completions[group] = group_pct
                
                # Add weighted contribution to overall completion
                overall_completion += (group_pct * weight / 100)
            
            # Round to nearest integer
            profile_completion = int(overall_completion)
            
            # Get recent applications
            recent_applications = Application.query.filter_by(
                user_id=current_user.id
            ).order_by(Application.submitted_at.desc()).limit(5).all()
            
            return render_template('dashboard.html',
                                  application_count=application_count,
                                  profile_completion=profile_completion,
                                  recent_applications=recent_applications,
                                  group_completions=group_completions)  # Pass group data for detailed display
        return render_template('index.html')

    @app.route('/api/search', methods=['POST'])
    def search_jobs():
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({"error": "You must be logged in to search for jobs"}), 401
            
        # Get search parameters from request
        data = request.json
        job_title = data.get('job_title')
        location = data.get('location')
        
        if not job_title:
            return jsonify({"error": "Job title is required"}), 400
        
        try:
            # Import job search function
            from utils.job_search.job_search import search_jobs as search_jobs_util
            
            # Search for jobs
            app.logger.info(f"Searching for jobs: {job_title} in {location}")
            jobs = search_jobs_util(job_title, location)
            app.logger.info(f"Found {len(jobs)} jobs")
            
            # Return the results
            return jsonify({"jobs": jobs})
        except Exception as e:
            app.logger.error(f"Error searching for jobs: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # Define your other routes here
    # @app.route('/login', methods=['GET', 'POST'])
    # @app.route('/register', methods=['GET', 'POST'])
    # etc...
    
    return app

# This app instance can be accessed by both `flask run` and `gunicorn`
app = create_app()

# This allows you to run the app directly with `python app.py`
if __name__ == '__main__':
    app.run(debug=True)
