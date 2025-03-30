from flask import Blueprint, request, jsonify, current_app, render_template, send_file, send_from_directory, abort
# Updated import for modular application filler
from utils.application_filler import ApplicationFiller
from utils.application_filler.utils import valid_url
from flask_login import login_required, current_user
# Update import to use the new job_search module
from utils.job_search.job_search import search_jobs
from utils.job_search.job_submitter import submit_application
from utils.document_parser import parse_and_save_resume, get_resume_file
from models.user import User, db
from models.application import Application
from models.job_recommendation import JobRecommendation
from datetime import datetime
from utils.job_recommender import search_and_save_jobs_for_current_user
import os
import json
import asyncio
import asyncio
from flask import current_app
from flask_login import login_required, current_user
from archive.test_integration_real import integration_test

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/auto-apply', methods=['POST'])
@login_required
def run_command_for_show():
    # Get job recommendations that haven't been applied to yet
    pending_jobs = JobRecommendation.query.filter_by(user_id=current_user.id, applied=False).limit(5).all()
    
    if not pending_jobs:
        return jsonify({'message': 'No pending job recommendations found. Search for jobs first!'}), 200
    
    try:
        # Set up the async task for application process
        async def run_application_process():
            results = []
            for job in pending_jobs:
                job_url = job.url
                if not job_url or not valid_url(job_url):
                    current_app.logger.warning(f"Invalid job URL: {job_url}")
                    continue
                
                # Initialize ApplicationFiller with the current user's data
                current_app.logger.info(f"Starting application process for URL: {job_url}")
                app_filler = ApplicationFiller(current_user, job_url=job_url)
                
                # Execute the application filling process
                result = await app_filler.fill_application()
                
                # Log the result
                if result.get('success'):
                    current_app.logger.info(f"Successfully applied to job at {job_url}")
                    
                    # Mark the job recommendation as applied
                    job.applied = True
                    
                    # Create application record
                    try:
                        job_id = job_url.split('/')[-1]  # Extract job ID from URL
                        application = Application(
                            user_id=current_user.id,
                            job_id=job_id,
                            company=job.company,
                            position=job.job_title,
                            status='Submitted',
                            response_data=str(result),
                            applied_at=datetime.utcnow()
                        )
                        db.session.add(application)
                        db.session.commit()
                        current_app.logger.info(f"Created application record for job {job_id}")
                    except Exception as db_error:
                        current_app.logger.error(f"Error saving application record: {str(db_error)}")
                        db.session.rollback()
                else:
                    current_app.logger.warning(f"Failed to apply to job: {result.get('message')}")
                
                results.append({
                    'job_title': job.job_title,
                    'company': job.company,
                    'success': result.get('success', False),
                    'message': result.get('message', 'Unknown error')
                })
                
                # Small delay between applications
                await asyncio.sleep(2)
            
            return results
        
        # Run the async function
        current_app.logger.info("Starting async application process")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_application_process())
        loop.close()
        
        # Return summary of results
        successful = sum(1 for r in results if r.get('success'))
        return jsonify({
            'message': f'Applied to {successful} out of {len(results)} jobs successfully!',
            'details': results
        })
                
    except Exception as e:
        current_app.logger.error(f"Auto-apply process failed with exception: {str(e)}")
        return jsonify({'error': 'There was an error during the auto-apply process.'}), 500


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
@login_required
def search():
    data = request.json
    job_title = data.get('job_title')
    location = data.get('location')
    
    if not job_title or not location:
        return jsonify({'error': 'Job title and location are required'}), 400
    
    try:
        # Log the search query
        current_app.logger.info(f"Searching for jobs: {job_title} in {location}")
        
        # First, search for jobs
        jobs = search_jobs(job_title, location)
        
        # Log what we found
        current_app.logger.info(f"Found {len(jobs)} jobs")
        
        # Always return the jobs we found even if saving to DB fails
        try:
            # Save all jobs to DB instead of limiting to just 10
            saved_jobs = []
            max_retries = 5
            retries = 0
            
            while retries < max_retries:
                retries += 1
                if retries > 1:  # Only fetch new results after the first page
                    current_app.logger.info(f"Fetching more jobs (page {retries})")
                    jobs = search_jobs(job_title, location, page=retries)
                
                for job in jobs:
                    job_url = job.get('url', '').strip()
                    if not job_url:
                        continue
                    try:
                        existing = JobRecommendation.query.filter_by(
                            user_id=current_user.id,
                            url=job_url
                        ).first()
                        
                        if existing:
                            continue
                        recommendation = JobRecommendation(
                            user_id=current_user.id,
                            job_title=job.get('title', ''),
                            company=job.get('company', ''),
                            location=job.get('location', ''),
                            url=job_url,
                            applied=False,
                            match_score=0,
                            recommended_at=datetime.utcnow()
                        )
                        db.session.add(recommendation)
                        saved_jobs.append({
                            'title': recommendation.job_title,
                            'company': recommendation.company,
                            'location': recommendation.location,
                            'url': recommendation.url,
                            'applied': recommendation.applied
                        })
                    except Exception as inner_e:
                        # Log but continue processing other jobs
                        current_app.logger.error(f"Error saving job: {str(inner_e)}")
                
                # If we processed the first page and have enough jobs, stop fetching more pages
                if retries == 1 and len(jobs) < 20:  # Less than a full page of results
                    break
                    
                # Only continue fetching additional pages if we need more jobs or configured to get all
                if len(saved_jobs) >= len(jobs):  # We've saved all jobs from current page
                    break
            
            try:
                if saved_jobs:
                    db.session.commit()
                    current_app.logger.info(f"Successfully committed {len(saved_jobs)} jobs")
            except Exception as commit_e:
                current_app.logger.error(f"Commit failed: {str(commit_e)}")
                db.session.rollback()
        
        except Exception as db_e:
            current_app.logger.error(f"Database error: {str(db_e)}")
            # No need to abort - we'll return the jobs anyway
        
        # Return the jobs we found regardless of any database errors
        return jsonify({
            'message': f'Found {len(jobs)} jobs',
            'jobs': jobs
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Search error: {str(e)}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@api_bp.route('/search-and-recommendations', methods=['POST'])
@login_required
def search_and_recommend():
    data = request.json
    job_title = data.get('job_title')
    location = data.get('location')
    
    if not job_title or not location:
        return jsonify({'error': 'Job title and location are required'}), 400
    
    try:
        jobs = search_jobs(job_title, location)
        search_and_save_jobs_for_current_user(limit=10)
        return jsonify({
            'message': 'Jobs searched and recommendations saved',
            'jobs': jobs
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in search-and-recommendations: {str(e)}")
        return jsonify({'error': 'Failed to search and save recommendations'}), 500

@api_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_job():
    """
    Apply to a job posting using the ApplicationFiller.
    Handles login processes, captcha challenges, and form submission
    using the user's profile data from the database.
    """
    if request.method == 'GET':
        # Get job URL from query parameter if provided
        job_url = request.args.get('job_url', '')
        return render_template('auto_apply.html', job_url=job_url)
    
    elif request.method == 'POST':
        # Get the job URL from form data
        job_url = request.form.get('job_url')
        
        if not job_url or not valid_url(job_url):
            return jsonify({'error': 'Please provide a valid job URL'}), 400
        
        # Get debug mode flag
        debug_mode = request.form.get('debug_mode', 'false').lower() == 'true'
        if debug_mode:
            os.environ['DEBUG_MODE'] = '1'
        else:
            os.environ.pop('DEBUG_MODE', None)
            
        try:
            # Set up the async task for application process
            async def run_application_process():
                # Initialize ApplicationFiller with the current user's data
                current_app.logger.info(f"Starting application process for URL: {job_url}")
                app_filler = ApplicationFiller(current_user, job_url=job_url)
                
                # Execute the application filling process
                result = await app_filler.fill_application()
                
                # Log the result
                if result.get('success'):
                    current_app.logger.info(f"Successfully applied to job at {job_url}")
                else:
                    current_app.logger.warning(f"Failed to apply to job: {result.get('message')}")
                
                # If successful, create a record in the applications table
                if result.get('success'):
                    try:
                        # Extract job details from result or URL
                        job_id = job_url.split('/')[-1]  # Extract job ID from URL
                        company = result.get('company', 'Unknown')
                        position = result.get('job_title', 'Unknown Position')
                        
                        # Create application record
                        application = Application(
                            user_id=current_user.id,
                            job_id=job_id,
                            company=company,
                            position=position,
                            status='Submitted',
                            response_data=str(result),
                            applied_at=datetime.utcnow()
                        )
                        db.session.add(application)
                        db.session.commit()
                        current_app.logger.info(f"Created application record for job {job_id}")
                        
                        # Also check if this was from a job recommendation and mark it as applied
                        recommendation = JobRecommendation.query.filter_by(
                            user_id=current_user.id,
                            url=job_url
                        ).first()
                        
                        if recommendation:
                            recommendation.applied = True
                            db.session.commit()
                            current_app.logger.info(f"Marked job recommendation {recommendation.id} as applied")
                    except Exception as db_error:
                        current_app.logger.error(f"Error saving application record: {str(db_error)}")
                        db.session.rollback()
                
                return result
            
            # Run the async function
            current_app.logger.info("Starting async application process")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_application_process())
            loop.close()
            
            # Return result as JSON for API response
            current_app.logger.info("Application process completed")
            return jsonify({
                'success': result.get('success', False),
                'message': result.get('message', 'Unknown error'),
                'resume_uploaded': result.get('resume_uploaded', False),
                'form_completed': result.get('form_completed', False),
                'failed_fields': result.get('failed_fields', []),
                'job_url': job_url,
                'screenshot': result.get('screenshot')
            })
                
        except Exception as e:
            current_app.logger.error(f"Application failed with exception: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Application process failed: {str(e)}",
                'job_url': job_url
            }), 500

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

@api_bp.route('/auto-apply-pending', methods=['POST'])
@login_required
def auto_apply_pending():
    """
    Automatically apply to all pending job recommendations (applied=False)
    using the integration test functionality.
    """
    pending_jobs = JobRecommendation.query.filter_by(user_id=current_user.id, applied=False).all()
    if not pending_jobs:
        return jsonify({'message': 'No pending jobs found'}), 200

    
    # Create a wrapper function that calls integration_test with a specific URL
    async def run_integration_test_for_job(job_url):
        # Override the TEST_URL global variable by patching it
        with patch('archive.integration.test_integration_real.TEST_URL', job_url):
            await integration_test()
            current_app.logger.info(f"Integration test completed for job: {job_url}")
    
    # Create tasks for each pending job
    tasks = []
    job_ids = []
    for job in pending_jobs:
        if not job.url:
            current_app.logger.warning(f"Job ID {job.id} has no URL, skipping")
            continue
            
        job_url = job.url
        tasks.append(run_integration_test_for_job(job_url))
        job_ids.append(job.id)
        # Mark job as applied (we'll commit only if all tests succeed)
        job.applied = True
    
    if not tasks:
        return jsonify({'message': 'No valid job URLs found to apply to'}), 200
        
    try:
        # Create a new event loop and run all tasks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(asyncio.gather(*tasks))
        loop.close()
        
        # All tests completed successfully, commit the changes
        db.session.commit()
        
        # Log successful applications
        for job_id in job_ids:
            # Create an Application record for each successful job application
            job = JobRecommendation.query.get(job_id)
            application = Application(
                user_id=current_user.id,
                job_id=extract_job_id_from_url(job.url) or str(job.id),
                company=job.company,
                position=job.job_title,
                status='Test Applied',  # Mark as test applied to distinguish from real applications
                response_data=f"Applied via integration test on {datetime.utcnow().isoformat()}"
            )
            db.session.add(application)
        
        db.session.commit()
        return jsonify({
            'message': f'Successfully applied to {len(tasks)} jobs using integration test',
            'jobs_applied': job_ids
        }), 200
    except Exception as e:
        current_app.logger.error(f"Auto apply with integration test failed: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Failed to auto apply using integration test', 
            'details': str(e)
        }), 500

def extract_job_id_from_url(url):
    """
    Extracts the Indeed job ID from a URL, fallback to None if not found
    """
    import re
    match = re.search(r'jk=([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None

@api_bp.route('/applications/<int:user_id>', methods=['GET'])
@login_required
def get_applications(user_id):
    # Only allow access to current user's applications
    if current_user.id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
        
    applications = Application.query.filter_by(user_id=user_id).all()
    return jsonify([app.to_dict() for app in applications])

@api_bp.route('/apply-page', methods=['GET'])
@login_required
def apply_page():
    return render_template('auto_apply.html')

@api_bp.route('/apply-single', methods=['POST'])
@login_required
def apply_single_job():
    """
    Apply to a single job posting by ID or URL
    This endpoint handles both real job URLs and mock job URLs
    
    Request body:
    {
        "job_id": 123,           // Optional job recommendation ID
        "job_url": "https://...", // Optional job URL (required if job_id is not provided)
        "headless": false         // Optional boolean to control browser visibility
    }
    """
    data = request.json
    job_id = data.get('job_id')
    job_url = data.get('job_url')
    headless = data.get('headless', False)  # Default to visible browser
    
    if not job_id and not job_url:
        return jsonify({'error': 'Either job_id or job_url must be provided'}), 400
    
    # If job_id is provided but not job_url, look up the recommendation
    if job_id and not job_url:
        recommendation = JobRecommendation.query.filter_by(
            id=job_id, 
            user_id=current_user.id
        ).first()
        
        if not recommendation:
            return jsonify({'error': 'Job recommendation not found'}), 404
        
        job_url = recommendation.url
    
    # Check if this is a mock URL (example.com)
    is_mock = 'example.com' in job_url
    
    if is_mock:
        # For mock URLs, create a test job application page on localhost
        current_app.logger.info(f"Mock job URL detected: {job_url}")
        
        # Use the stored recommendation as mock data
        if job_id:
            recommendation = JobRecommendation.query.filter_by(
                id=job_id, 
                user_id=current_user.id
            ).first()
            
            if recommendation:
                # Create a successful mock application
                current_app.logger.info(f"Creating mock successful application for job ID {job_id}")
                
                # Mark as applied
                recommendation.applied = True
                
                # Create application record
                application = Application(
                    user_id=current_user.id,
                    job_id=str(job_id),
                    company=recommendation.company,
                    position=recommendation.job_title,
                    status='Submitted',
                    response_data='{"success": true, "message": "Mock application successful"}',
                    applied_at=datetime.utcnow()
                )
                
                db.session.add(application)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Mock application submitted successfully',
                    'job_id': job_id,
                    'company': recommendation.company,
                    'position': recommendation.job_title
                })
            else:
                return jsonify({'error': 'Job recommendation not found'}), 404
        else:
            # Generic mock success for URL-only applications
            return jsonify({
                'success': True,
                'message': 'Mock application submitted successfully',
                'job_url': job_url
            })
    
    # For real URLs, use the ApplicationFiller
    try:
        # Set up the async task for application process
        async def run_application_process():
            # Initialize ApplicationFiller with the current user's data
            current_app.logger.info(f"Starting application process for URL: {job_url}")
            
            # Use the headless parameter provided in the request
            app_filler = ApplicationFiller(current_user, job_url=job_url, headless=headless)
            
            # Execute the application filling process
            result = await app_filler.fill_application()
            
            # Log the result
            if result.get('success'):
                current_app.logger.info(f"Successfully applied to job at {job_url}")
                
                # If we have a job_id, mark the recommendation as applied
                if job_id:
                    recommendation = JobRecommendation.query.filter_by(
                        id=job_id,
                        user_id=current_user.id
                    ).first()
                    
                    if recommendation:
                        recommendation.applied = True
                        db.session.commit()
            else:
                current_app.logger.warning(f"Failed to apply to job: {result.get('message')}")
            
            return result
        
        # Run the async function
        current_app.logger.info("Starting async application process")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_application_process())
        loop.close()
        
        # If successful, create a record in the applications table
        if result.get('success'):
            try:
                # Extract job details from result
                company = result.get('company', 'Unknown')
                position = result.get('job_title', 'Unknown Position')
                
                # Create application record
                application = Application(
                    user_id=current_user.id,
                    job_id=job_id or job_url.split('/')[-1],  # Use provided job_id or extract from URL
                    company=company,
                    position=position,
                    status='Submitted',
                    response_data=str(result),
                    applied_at=datetime.utcnow()
                )
                db.session.add(application)
                db.session.commit()
                
                # Add company and position to the result for display
                result['company'] = company
                result['position'] = position
            except Exception as db_error:
                current_app.logger.error(f"Error saving application record: {str(db_error)}")
                db.session.rollback()
        
        # Return result to frontend
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', 'Unknown error'),
            'job_id': job_id,
            'job_url': job_url,
            'screenshot': result.get('screenshot'),
            'company': result.get('company', 'Unknown'),
            'position': result.get('position', 'Unknown Position'),
            'resume_uploaded': result.get('resume_uploaded', False),
            'form_completed': result.get('form_completed', False)
        })
        
    except Exception as e:
        current_app.logger.error(f"Application failed with exception: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Application process failed",
            'error_details': str(e),
            'job_id': job_id,
            'job_url': job_url
        }), 500