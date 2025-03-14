from flask import Blueprint, request, jsonify
from utils.indeed_scraper import search_jobs
from utils.application_filler import generate_application_responses
from utils.job_submitter import submit_application
from models.user import User, db
from models.application import Application

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/search', methods=['POST'])
def search():
    data = request.json
    job_title = data.get('job_title')
    location = data.get('location')
    
    if not job_title or not location:
        return jsonify({'error': 'Job title and location are required'}), 400
    
    jobs = search_jobs(job_title, location)
    return jsonify({'jobs': jobs})

@api_bp.route('/apply', methods=['POST'])
def apply():
    data = request.json
    job_id = data.get('job_id')
    user_id = data.get('user_id')
    
    if not job_id or not user_id:
        return jsonify({'error': 'Job ID and user ID are required'}), 400
    
    # Get user profile
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Generate responses for application questions
    application_responses = generate_application_responses(job_id, user)
    
    # Submit the application
    result = submit_application(job_id, user, application_responses)
    
    # Log application in database if successful
    if result['success']:
        application = Application(
            user_id=user_id,
            job_id=job_id,
            company=data.get('company', 'Unknown'),
            position=data.get('title', 'Unknown'),
            status='Submitted',
            response_data=str(application_responses)
        )
        db.session.add(application)
        db.session.commit()
        result['application_id'] = application.id
    
    return jsonify(result)

@api_bp.route('/user', methods=['POST'])
def create_user():
    data = request.json
    
    # Check if user with email already exists
    existing_user = User.query.filter_by(email=data.get('email')).first()
    if existing_user:
        # Update existing user
        existing_user.name = data.get('name', existing_user.name)
        existing_user.resume = data.get('resume', existing_user.resume)
        existing_user.skills = data.get('skills', existing_user.skills)
        existing_user.experience = data.get('experience', existing_user.experience)
        
        db.session.commit()
        return jsonify({'id': existing_user.id, 'message': 'User profile updated'}), 200
    
    # Create new user
    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        resume=data.get('resume'),
        skills=data.get('skills'),
        experience=data.get('experience')
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'id': new_user.id, 'message': 'User profile created'}), 201

@api_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify(user.to_dict())

@api_bp.route('/applications/<int:user_id>', methods=['GET'])
def get_applications(user_id):
    applications = Application.query.filter_by(user_id=user_id).all()
    return jsonify([app.to_dict() for app in applications])
