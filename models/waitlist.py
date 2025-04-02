from datetime import datetime
from .user import db

class Waitlist(db.Model):
    __tablename__ = 'waitlist'
    __table_args__ = (
        db.UniqueConstraint('email', name='uq_waitlist_email'),
    )
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    source = db.Column(db.String(50), default='checkout_page')
    discount_applied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Updated to use datetime.utcnow directly
    
    def __repr__(self):
        return f'<Waitlist {self.email}>'
