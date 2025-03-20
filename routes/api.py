from flask import Blueprint, request, jsonify, current_app, send_file, send_from_directory, abort
from flask_login import login_required, current_user
# Update import to use the new job_search module
from utils.job_search.job_search import search_jobs
from utils.application_filler import generate_application_responses
from utils.job_search.job_submitter import submit_application
from utils.document_parser import parse_and_save_resume, get_resume_file
from models.user import User, db
from models.application import Application
from utils.job_recommender import search_and_save_jobs_for_current_user
import os
import json

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/recommendations', methods=['POST'])
@login_required
def generate_recommendations():
    """
    Trigger job search and save recommendations for the current user.
    """
    try:
        search_and_save_jobs_for_current_user(limit=10)  # You can adjust limit if needed
        return jsonify({'message': 'Job recommendations have been saved successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error generating recommendations: {str(e)}")
        return jsonify({'error': 'Failed to generate recommendations'}), 500


@api_bp.route('/recommendations', methods=['GET'])
@login_required
def get_user_recommendations():
    """
    Return all job recommendations for the current user.
    """
    try:
        recommendations = JobRecommendation.query.filter_by(user_id=current_user.id).all()
        return jsonify([
            {
                'id': rec.id,
                'job_title': rec.job_title,
                'company': rec.company,
                'location': rec.location,
                'url': rec.url,
                'match_score': rec.match_score,
                'applied': rec.applied,
                'recommended_at': rec.recommended_at.isoformat()
            } for rec in recommendations
        ])
    except Exception as e:
        current_app.logger.error(f"Error fetching recommendations: {str(e)}")
        return jsonify({'error': 'Could not fetch recommendations'}), 500
    
@api_bp.route('/recommendations/<int:recommendation_id>', methods=['PATCH'])
@login_required
def update_applied_status(recommendation_id):
    """
    Mark a job recommendation as applied or not applied.
    """
    data = request.json
    applied_status = data.get('applied')

    if applied_status is None:
        return jsonify({'error': 'Applied status is required'}), 400

    rec = JobRecommendation.query.filter_by(id=recommendation_id, user_id=current_user.id).first()
    if not rec:
        return jsonify({'error': 'Recommendation not found'}), 404

    rec.applied = bool(applied_status)
    db.session.commit()
    return jsonify({'message': 'Recommendation updated', 'applied': rec.applied})

@api_bp.route('/search', methods=['POST'])
def search():
    data = request.json
    job_title = data.get('job_title')
    location = data.get('location')
    
    if not job_title or not location:
        return jsonify({'error': 'Job title and location are required'}), 400
    
    # Use the new job search function
    jobs = search_jobs(job_title, location)
    return jsonify({'jobs': jobs})

@api_bp.route('/apply', methods=['POST'])
@login_required
def apply():
    data = request.json
    job_id = data.get('job_id')
    
    if not job_id:
        return jsonify({'error': 'Job ID is required'}), 400
    
    # Use current_user instead of querying by user_id
    user = current_user
    
    # Generate responses for application questions
    application_responses = generate_application_responses(job_id, user)
    
    # Submit the application
    result = submit_application(job_id, user, application_responses)
    
    # Log application in database if successful
    if result['success']:
        application = Application(
            user_id=user.id,
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
@login_required
def update_user():
    """Update the current user's profile"""
    data = request.json
    
    # Update current user's profile
    current_user.name = data.get('name', current_user.name)
    
    # Process resume if it contains a base64 data URI
    resume_data = data.get('resume', '')
    if resume_data and resume_data.startswith('data:'):
        # Parse and save the resume file
        parsed_text, file_path, filename, mime_type = parse_and_save_resume(
            resume_data, current_user.id)
        
        # Update user record with file information
        current_user.resume = parsed_text
        current_user.resume_file_path = file_path
        current_user.resume_filename = filename
        current_user.resume_mime_type = mime_type
        
        current_app.logger.info(f"Saved resume file for user {current_user.id}: {file_path}")
    elif resume_data:
        # Just update the resume text
        current_user.resume = resume_data
    
    current_user.skills = data.get('skills', current_user.skills)
    current_user.experience = data.get('experience', current_user.experience)
    
    try:
        db.session.commit()
        current_app.logger.info(f"Updated profile for user: {current_user.id}")
        return jsonify({
            'success': True, 
            'id': current_user.id, 
            'message': 'Profile updated successfully'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error updating user profile: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating profile: {str(e)}'}), 500

@api_bp.route('/user/resume', methods=['GET'])
@login_required
def download_resume():
    """Download the user's original resume file."""
    if not current_user.resume_file_path or not os.path.exists(current_user.resume_file_path):
        abort(404, "No resume file available")
    
    directory = os.path.dirname(current_user.resume_file_path)
    filename = os.path.basename(current_user.resume_file_path)
    
    return send_from_directory(
        directory, 
        filename,
        as_attachment=True,
        attachment_filename=current_user.resume_filename or filename
    )

@api_bp.route('/user/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    # Only allow access to the current user's profile
    if current_user.id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
        
    return jsonify(current_user.to_dict())

@api_bp.route('/applications/<int:user_id>', methods=['GET'])
@login_required
def get_applications(user_id):
    # Only allow access to current user's applications
    if current_user.id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
        
    applications = Application.query.filter_by(user_id=user_id).all()
    return jsonify([app.to_dict() for app in applications])
