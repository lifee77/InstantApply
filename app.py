#!/usr/bin/env python3
"""
InstantApply - Main application entry point
"""
import os
import sys
from datetime import datetime

# Add the project root directory to Python path to fix imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import Flask, render_template, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Import modules
from models.user import User, db
from routes.api import api_bp
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.debug import debug_bp


def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_pyfile('config.py')
    
    # Initialize database
    db.init_app(app)
    
    # Initialize LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    
    # Only register debug routes in debug mode
    if app.debug:
        app.register_blueprint(debug_bp)
    
    @app.route('/')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
        
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Calculate profile completion percentage
        profile_fields = [
            current_user.name,
            current_user.resume,
            current_user.skills,
            current_user.experience,
            current_user.professional_summary,
            current_user._desired_job_titles,
            current_user.linkedin_url
        ]
        
        # Count non-empty fields
        filled_fields = sum(1 for field in profile_fields if field and str(field).strip())
        
        # Calculate completion percentage
        profile_completion = int((filled_fields / len(profile_fields)) * 100) if profile_fields else 0
        
        # Get application count
        from models.application import Application
        application_count = Application.query.filter_by(user_id=current_user.id).count()
        
        # Get recent applications
        recent_applications = Application.query.filter_by(user_id=current_user.id).order_by(Application.applied_at.desc()).limit(5).all()
        
        # Group completion stats (optional)
        group_completions = {
            'basic_info': calculate_group_completion([current_user.name, current_user.professional_summary]),
            'skills_experience': calculate_group_completion([current_user.skills, current_user.experience]),
            'resume': calculate_group_completion([current_user.resume, current_user.resume_file_path])
        }
        
        return render_template('dashboard.html', 
                               user=current_user,
                               profile_completion=profile_completion,
                               application_count=application_count,
                               recent_applications=recent_applications,
                               group_completions=group_completions)

    def calculate_group_completion(fields):
        """Helper function to calculate completion percentage for a group of fields"""
        filled = sum(1 for f in fields if f and str(f).strip())
        return int((filled / len(fields)) * 100) if fields else 0
        
    @app.route('/recommendations')
    @login_required
    def recommendations():
        return render_template('recommendations.html')
        
    @app.route('/apply-url')
    @login_required
    def apply_url():
        return render_template('apply_url.html')
        
    @app.route('/applications')
    @login_required
    def applications():
        return render_template('applications.html')
        
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
        
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        
    return app

# This app instance can be accessed by both `flask run` and `gunicorn`
app = create_app()

# This allows you to run the app directly with `python app.py`
if __name__ == '__main__':
    app.run(debug=True)
