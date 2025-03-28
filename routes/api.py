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
    import subprocess
    import shlex

    command = shlex.split("python -m archive.test_integration_real")
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        return jsonify({'message': 'Applied successfully!'})
    else:
        return jsonify({'error': 'There was an error, check the terminal.'}), 500

# def trigger_auto_apply():
#     """
#     API Endpoint to trigger the auto-apply process.
#     This route will fetch the current user's job recommendations,
#     automatically fill and submit the applications, and mark them as applied.
#     """
#     user_id = current_user.id
#     from application_filler.runner_service import auto_apply_jobs_for_user

#     try:
#         # Create a new event loop to run the async function
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         loop.run_until_complete(auto_apply_jobs_for_user(user_id))
#         loop.close()
#         return jsonify({'message': 'Auto-apply triggered successfully!'}), 200
#     except Exception as e:
#         current_app.logger.error(f"Error in auto-apply: {str(e)}")
#         return jsonify({'error': 'Auto-apply failed'}), 500


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
            # Only attempt to save to DB if we have the job_recommendations table
            saved_jobs = []
            max_retries = 5
            retries = 0

            while len(saved_jobs) < 10 and retries < max_retries:
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

                        if len(saved_jobs) >= 10:
                            break
                    except Exception as inner_e:
                        # Log but continue processing other jobs
                        current_app.logger.error(f"Error saving job: {str(inner_e)}")

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

@api_bp.route('/apply', methods=['GET'])
@login_required
def test_apply():
    """
    Test endpoint for the application filler functionality.
    Access this via browser to test with a sample job application URL.
    """
    # Get job URL from query parameter or use default test URL
    job_url = request.args.get('job_url', 'https://www.linkedin.com/jobs/view/3824957351')
    
    # Show initial form if no URL provided in query string and not submitted via form
    if 'job_url' not in request.args and request.method == 'GET' and 'submit' not in request.args:
        return f"""
        <html>
        <head>
            <title>ApplicationFiller Test</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #333; }}
                form {{ margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }}
                input[type="text"] {{ width: 100%; padding: 8px; margin: 8px 0; box-sizing: border-box; }}
                input[type="submit"] {{ padding: 10px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }}
                .examples {{ margin-top: 20px; }}
                .example {{ padding: 5px 0; }}
            </style>
        </head>
        <body>
            <h1>Test ApplicationFiller</h1>
            <p>Enter a job application URL to test the automatic application filling:</p>
            
            <form action="/api/apply" method="GET">
                <input type="text" name="job_url" placeholder="Enter job URL" 
                       value="https://www.linkedin.com/jobs/view/3824957351" style="width:80%">
                <input type="hidden" name="submit" value="true">
                <input type="submit" value="Test Application">
            </form>
            
            <div class="examples">
                <p><strong>Example URLs you can try:</strong></p>
                <div class="example">
                    <a href="/api/apply?job_url=https://www.linkedin.com/jobs/view/3824957351">
                        LinkedIn Job - Software Engineer
                    </a>
                </div>
                <div class="example">
                    <a href="/api/apply?job_url=https://www.indeed.com/viewjob?jk=79c00d6d31fd4a93">
                        Indeed Job - Web Developer
                    </a>
                </div>
            </div>
            
            <p><em>Note: Set DEBUG_MODE=1 in environment to keep browser open longer for inspection.</em></p>
        </body>
        </html>
        """
    
    # Initialize the ApplicationFiller
    from utils.application_filler import ApplicationFiller
    app_filler = ApplicationFiller(current_user, job_url=job_url)
    
    # Create an async function to run the application filler
    async def test_fill_application():
        result = await app_filler.fill_application()
        return result
    
    try:
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_fill_application())
        loop.close()
        
        # Return a simple HTML result for browser viewing
        html_result = f"""
        <html>
        <head>
            <title>ApplicationFiller Test Result</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #333; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
                pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                .back-button {{ display: inline-block; margin-top: 20px; padding: 10px 15px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>ApplicationFiller Test Results</h1>
            <p><strong>URL:</strong> {job_url}</p>
            <p><strong>Status:</strong> <span class="{'success' if result['success'] else 'error'}">
                {'SUCCESS' if result['success'] else 'FAILED'}
            </span></p>
            <p><strong>Message:</strong> {result['message']}</p>
            <h2>Complete Response:</h2>
            <pre>{json.dumps(result, indent=2)}</pre>
            
            <a href="/api/apply" class="back-button">Test Another URL</a>
        </body>
        </html>
        """
        return html_result
    except Exception as e:
        error_message = f"ApplicationFiller test failed: {str(e)}"
        current_app.logger.error(error_message)
        return f"""
        <html>
        <head>
            <title>ApplicationFiller Test Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #333; }}
                .error {{ color: red; }}
                pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                .back-button {{ display: inline-block; margin-top: 20px; padding: 10px 15px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>ApplicationFiller Test Error</h1>
            <p class="error">{error_message}</p>
            <h2>Stack Trace:</h2>
            <pre>{str(e)}</pre>
            
            <a href="/api/apply" class="back-button">Test Another URL</a>
        </body>
        </html>
        """

@api_bp.route('/apply', methods=['POST'])
@login_required
def apply():
    data = request.json
    job_url = data.get('job_url')
    
    if not job_url:
        return jsonify({'error': 'Job URL is required'}), 400
    
    # Use current_user instead of querying by user_id
    user = current_user
    
    # Instantiate the ApplicationFiller class using the new modular structure
    app_filler = ApplicationFiller(user, job_url=job_url)
    
    # Define an async function to run the application process
    async def run_application_process():
        try:
            # Use the new fill_application method which handles the entire process
            result = await app_filler.fill_application()
            return result
        except Exception as e:
            current_app.logger.error(f"ApplicationFiller error: {str(e)}")
            return {
                "success": False,
                "message": f"ApplicationFiller failed: {str(e)}",
                "url": job_url,
                "user": user.email
            }
    
    try:
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_application_process())
        loop.close()
        
        # Create application record in the database
        if result.get('success'):
            application = Application(
                user_id=user.id,
                job_id=data.get('job_id'),
                company=data.get('company', 'Unknown'),
                position=data.get('title', 'Unknown'),
                status='Submitted',
                response_data=str(result)
            )
            db.session.add(application)
            db.session.commit()
            result['application_id'] = application.id
            
            # If this was applied to a job recommendation, mark it as applied
            if data.get('recommendation_id'):
                rec = JobRecommendation.query.filter_by(
                    id=data.get('recommendation_id'),
                    user_id=user.id
                ).first()
                if rec:
                    rec.applied = True
                    db.session.commit()
        
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Application process failed: {str(e)}")
        return jsonify({
            'error': 'Failed to apply',
            'details': str(e)
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