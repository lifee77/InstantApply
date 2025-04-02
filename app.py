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
from flask_mail import Mail
from utils.email_utils import mail, send_waitlist_confirmation

# Import modules
from models.user import db, User
from models.application import Application
from models.job_recommendation import JobRecommendation
from models.waitlist import Waitlist  # Import the Waitlist model
from routes.profile import profile_bp
from routes.api import api_bp
from routes.auth import auth_bp
from routes.debug import debug_bp
from routes.checkout import checkout_bp

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
    
    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'yes', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-password')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'InstantApply <noreply@instantapply.com>')
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    mail.init_app(app)
    
    # Ensure all tables exist
    with app.app_context():
        try:
            # Check if waitlist table exists, if not create all tables
            if not db.engine.dialect.has_table(db.engine, 'waitlist'):
                print("Creating database tables including waitlist...")
                db.create_all()
                print("Database tables created successfully")
        except Exception as e:
            print(f"Database initialization error: {str(e)}")
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(checkout_bp)

    
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
            return render_template('dashboard.html')
        return render_template('index.html')

    @app.route('/api/search', methods=['POST'])
    def search_jobs():
        # Placeholder for search job implementation
        return jsonify({"message": "Search endpoint hit"})

    # Add this API endpoint to your Flask application
    from flask import request, jsonify
    from datetime import datetime

    # Assuming you have a route setup for your API endpoints
    @app.route('/api/save-waitlist', methods=['POST'])
    def save_waitlist():
        try:
            # Get data from request
            data = request.json
            email = data.get('email')
            source = data.get('source', 'checkout_page')
            discount_applied = data.get('discount_applied', False)
            
            # Validate email
            if not email or '@' not in email:
                return jsonify({'error': 'Invalid email address'}), 400
            
            try:
                # Check if email already exists to avoid duplicate entries
                existing_waitlist = Waitlist.query.filter_by(email=email).first()
                
                if existing_waitlist:
                    # Update existing record instead of creating duplicate
                    existing_waitlist.source = source
                    existing_waitlist.discount_applied = discount_applied
                    existing_waitlist.created_at = datetime.now()  # Use datetime.now() directly
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Email updated successfully', 'email': email}), 200
                
                # Create new waitlist entry
                new_waitlist = Waitlist(
                    email=email,
                    source=source,
                    discount_applied=discount_applied,
                    created_at=datetime.now()  # Use datetime.now() directly
                )
                
                db.session.add(new_waitlist)
                db.session.commit()
                
                # Send confirmation email
                email_sent = send_waitlist_confirmation(email, discount_applied)
                
                return jsonify({
                    'success': True, 
                    'message': 'Email saved successfully', 
                    'email': email,
                    'email_sent': email_sent
                }), 200
                
            except Exception as db_error:
                print(f"Database operation error: {str(db_error)}")
                # If table doesn't exist, try to create it
                if "no such table" in str(db_error).lower():
                    with app.app_context():
                        db.create_all()
                    # Try again after creating tables
                    new_waitlist = Waitlist(
                        email=email,
                        source=source,
                        discount_applied=discount_applied,
                        created_at=datetime.now()  # Use datetime.now() directly
                    )
                    db.session.add(new_waitlist)
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Email saved successfully', 'email': email}), 200
                else:
                    raise
                
        except Exception as e:
            print(f"Error saving waitlist email: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to save email', 'details': str(e)}), 500

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
