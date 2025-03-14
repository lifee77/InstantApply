from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from utils.indeed_scraper import search_jobs
from utils.application_filler import generate_application_responses
from utils.job_submitter import submit_application
from models.user import User, db
import os

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app)
db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    job_title = data.get('job_title')
    location = data.get('location')
    
    if not job_title or not location:
        return jsonify({'error': 'Job title and location are required'}), 400
    
    jobs = search_jobs(job_title, location)
    return jsonify({'jobs': jobs})

@app.route('/api/apply', methods=['POST'])
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
    
    return jsonify(result)

@app.route('/api/user', methods=['POST'])
def create_user():
    data = request.json
    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        resume=data.get('resume'),
        skills=data.get('skills'),
        experience=data.get('experience')
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'id': new_user.id}), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=app.config['DEBUG'])
