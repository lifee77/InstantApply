from datetime import datetime
from .user import db

class JobRecommendation(db.Model):
    __tablename__ = 'job_recommendations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_title = db.Column(db.String(255))
    company = db.Column(db.String(255))
    location = db.Column(db.String(255))
    url = db.Column(db.String(500))
    match_score = db.Column(db.Integer)
    applied = db.Column(db.Boolean, default=False)
    recommended_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('job_recommendations', lazy=True))