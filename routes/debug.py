from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required
import json
from utils.job_search.job_search import search_jobs

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

@debug_bp.route('/search-test')
@login_required
def search_test():
    """Debug endpoint to test the job search functionality"""
    job_title = request.args.get('title', 'Software Engineer')
    location = request.args.get('location', 'Remote')
    
    try:
        jobs = search_jobs(job_title, location)
        return render_template('debug/search_test.html', 
                             job_title=job_title,
                             location=location,
                             jobs=jobs,
                             jobs_json=json.dumps(jobs, indent=2))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
