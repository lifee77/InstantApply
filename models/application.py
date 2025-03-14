from datetime import datetime
from models.user import db

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.String(50), nullable=False)  # Indeed job ID
    company = db.Column(db.String(100))
    position = db.Column(db.String(100))
    status = db.Column(db.String(20))  # Submitted, Rejected, Interview, Accepted
    response_data = db.Column(db.Text)  # Serialized JSON of responses
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Application {self.id} - {self.position} at {self.company}>'
        
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job_id': self.job_id,
            'company': self.company,
            'position': self.position,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
