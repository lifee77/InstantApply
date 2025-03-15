from flask import Flask, render_template, session, redirect, url_for, flash, request, jsonify, current_app
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.user import db, User
from routes.api import api_bp
from routes.auth import auth_bp
import os
import sys
from setup_gemini import check_gemini_api
import json

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

# User API endpoints
@app.route('/api/user/current', methods=['GET'])
@login_required
def get_current_user():
    """Return the current logged-in user's data in JSON format"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
        
    # Convert user model to dictionary, adjust based on your User model
    user_data = {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'phone': current_user.phone if hasattr(current_user, 'phone') else None,
        'resume': current_user.resume_url if hasattr(current_user, 'resume_url') else None,
    }
    
    # Include skills if available
    if hasattr(current_user, 'skills') and current_user.skills:
        user_data['skills'] = current_user.skills.split(',') if isinstance(current_user.skills, str) else current_user.skills
    
    # Include experience if available
    if hasattr(current_user, 'experience') and current_user.experience:
        try:
            if isinstance(current_user.experience, str):
                user_data['experience'] = json.loads(current_user.experience)
            else:
                user_data['experience'] = current_user.experience
        except:
            # If JSON parsing fails, omit experience
            pass
    
    # Include education if available
    if hasattr(current_user, 'education') and current_user.education:
        try:
            if isinstance(current_user.education, str):
                user_data['education'] = json.loads(current_user.education)
            else:
                user_data['education'] = current_user.education
        except:
            # If JSON parsing fails, omit education
            pass
            
    return jsonify(user_data)

# Get applications for the current user
@app.route('/api/user/applications', methods=['GET'])
@login_required
def get_user_applications():
    """Return the current user's job applications"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Import the Application model
    from models.application import Application
    
    # Query applications for the current user
    applications = Application.query.filter_by(user_id=current_user.id).all()
    
    # Convert to list of dictionaries
    app_list = []
    for app in applications:
        app_data = {
            'id': app.id,
            'job_id': app.job_id,
            'job_title': app.job_title,
            'company_name': app.company_name,
            'status': app.status,
            'applied_date': app.applied_date.isoformat() if app.applied_date else None
        }
        app_list.append(app_data)
    
    return jsonify(app_list)

@app.route('/api/job/apply', methods=['POST'])
@login_required
def apply_to_job():
    """Process a job application"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated', 'success': False}), 401
    
    # Get application data from request
    data = request.json
    if not data or 'jobId' not in data:
        return jsonify({'error': 'Invalid request data', 'success': False}), 400
    
    try:
        # Import the Application model
        from models.application import Application
        from datetime import datetime
        
        # Create new application record
        application = Application(
            user_id=current_user.id,
            job_id=data['jobId'],
            job_title=data.get('jobTitle', 'Untitled Position'),
            company_name=data.get('companyName', 'Unknown Company'),
            status='applied',
            applied_date=datetime.now(),
            custom_message=data.get('customMessage', '')
        )
        
        # Save to database
        db.session.add(application)
        db.session.commit()
        
        # In a real implementation, you would use utils/job_submitter.py
        # and utils/application_filler.py here to submit the actual application
        
        return jsonify({'success': True, 'applicationId': application.id})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error applying to job: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

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
