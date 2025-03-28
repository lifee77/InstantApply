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
            
            # Calculate profile completion
            profile_completion = 0
            total_fields = 0
            
            # Check for presence of key user profile fields
            if current_user.name: profile_completion += 1; total_fields += 1
            if current_user.email: profile_completion += 1; total_fields += 1
            if current_user.professional_summary: profile_completion += 1; total_fields += 1
            if current_user.skills: profile_completion += 1; total_fields += 1
            if current_user.experience: profile_completion += 1; total_fields += 1
            if current_user._projects: profile_completion += 1; total_fields += 1  # Using the database column name
            if current_user.resume_file_path: profile_completion += 1; total_fields += 1
            if current_user.linkedin_url: profile_completion += 1; total_fields += 1
            
            profile_completion = int((profile_completion / max(total_fields, 1)) * 100)
            
            # Get recent applications
            recent_applications = Application.query.filter_by(
                user_id=current_user.id
            ).order_by(Application.submitted_at.desc()).limit(5).all()
            
            return render_template('dashboard.html',
                                  application_count=application_count,
                                  profile_completion=profile_completion,
                                  recent_applications=recent_applications)
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
