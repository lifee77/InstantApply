from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.user import db, User
from routes.api import api_bp
from routes.auth import auth_bp
import os
import sys
from setup_gemini import check_gemini_api

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app)

# Set maximum file upload size to 16 MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Initialize database
db.init_app(app)

# Ensure the instance directory exists
if not os.path.exists('instance'):
    os.makedirs('instance')

# Create database tables if they don't exist
with app.app_context():
    db.create_all()
    print("Database tables created or already exist")

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access this page."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/applications')
@login_required
def applications():
    return render_template('applications.html')

if __name__ == '__main__':
    # Check if Gemini API key exists in .env
    check_gemini_api()
    
    # Run the app
    app.run(debug=app.config['DEBUG'])
