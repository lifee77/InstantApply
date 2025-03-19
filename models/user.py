from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    resume = db.Column(db.Text)  # Store parsed resume text
    resume_file_path = db.Column(db.String(255))  # Path to the stored resume file
    resume_filename = db.Column(db.String(255))  # Original filename
    resume_mime_type = db.Column(db.String(100))  # MIME type of the resume file
    skills = db.Column(db.Text)  # JSON string of skills
    experience = db.Column(db.Text)  # JSON string of experience
    
    # Personal Information
    professional_summary = db.Column(db.Text)  # Professional summary/objective statement
    willing_to_relocate = db.Column(db.Boolean, default=False)
    authorization_status = db.Column(db.String(100))  # Work authorization status
    desired_job_titles = db.Column(db.Text)  # JSON string of job titles
    linkedin_url = db.Column(db.String(255))
    portfolio_links = db.Column(db.Text)  # JSON string of GitHub/portfolio links
    
    # Work Preferences
    desired_salary_range = db.Column(db.String(100))
    work_mode_preference = db.Column(db.String(50))  # Remote/hybrid/in-office
    available_start_date = db.Column(db.Date)
    preferred_company_type = db.Column(db.String(100))  # Startup vs. enterprise
    
    # Additional Qualifications
    certifications = db.Column(db.Text)  # JSON string of certifications with expiry dates
    languages = db.Column(db.Text)  # JSON string of languages and proficiency levels
    
    # Application-Specific Questions
    career_goals = db.Column(db.Text)  # Short and long-term goals
    biggest_achievement = db.Column(db.Text)  # Biggest professional achievement
    work_style = db.Column(db.Text)  # Work style and team preferences
    industry_attraction = db.Column(db.Text)  # What attracted to this industry/field
    
    # Values
    applicant_values = db.Column(db.Text)  # JSON string of applicant values
    
    # Demographic Information
    race_ethnicity = db.Column(db.String(100))
    gender = db.Column(db.String(50))
    graduation_date = db.Column(db.Date)
    military_status = db.Column(db.String(100))
    military_branch = db.Column(db.String(100))
    military_discharge_date = db.Column(db.Date)
    disability_status = db.Column(db.String(100))
    needs_sponsorship = db.Column(db.Boolean, default=False)
    visa_status = db.Column(db.String(100))
    veteran_status = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.name}>'
        
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'skills': self.skills,
            'experience': self.experience,
            'has_resume': bool(self.resume),
            'has_resume_file': bool(self.resume_file_path),
            'resume_filename': self.resume_filename,
            'professional_summary': self.professional_summary,
            'willing_to_relocate': self.willing_to_relocate,
            'authorization_status': self.authorization_status,
            'desired_job_titles': self.desired_job_titles,
            'linkedin_url': self.linkedin_url,
            'portfolio_links': self.portfolio_links,
            'desired_salary_range': self.desired_salary_range,
            'work_mode_preference': self.work_mode_preference,
            'available_start_date': self.available_start_date.isoformat() if self.available_start_date else None,
            'preferred_company_type': self.preferred_company_type,
            'certifications': self.certifications,
            'languages': self.languages,
            'career_goals': self.career_goals,
            'biggest_achievement': self.biggest_achievement,
            'work_style': self.work_style,
            'industry_attraction': self.industry_attraction,
            'applicant_values': self.applicant_values,
            'race_ethnicity': self.race_ethnicity,
            'gender': self.gender,
            'graduation_date': self.graduation_date.isoformat() if self.graduation_date else None,
            'military_status': self.military_status,
            'military_branch': self.military_branch,
            'military_discharge_date': self.military_discharge_date.isoformat() if self.military_discharge_date else None,
            'disability_status': self.disability_status,
            'needs_sponsorship': self.needs_sponsorship,
            'visa_status': self.visa_status,
            'veteran_status': self.veteran_status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
