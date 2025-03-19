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

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_migrate import Migrate
import json
import uuid
import datetime

# Import modules
from models.user import db, User
from models.application import Application
from routes.profile import profile_bp
from routes.api import api_bp

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instant_apply.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Register blueprints
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return render_template('dashboard.html')
        return render_template('index.html')
    
    # Define your other routes here
    # @app.route('/login', methods=['GET', 'POST'])
    # @app.route('/register', methods=['GET', 'POST'])
    # etc...
    
    return app

# This allows you to run the app directly with `python app.py`
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
