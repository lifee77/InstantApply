from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    resume = db.Column(db.Text)  # Store resume text or file path
    skills = db.Column(db.Text)  # JSON string of skills
    experience = db.Column(db.Text)  # JSON string of experience
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.name}>'
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'skills': self.skills,
            'experience': self.experience,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
