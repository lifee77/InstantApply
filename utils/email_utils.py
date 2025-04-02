"""
Email utility functions for InstantApply
"""
from flask import current_app, render_template
from flask_mail import Message, Mail
import os

mail = Mail()

def send_waitlist_confirmation(email, discount_applied=False):
    """Send a confirmation email to users who joined the waitlist"""
    try:
        subject = "Welcome to InstantApply Waitlist"
        
        msg = Message(
            subject=subject,
            recipients=[email],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Prepare the email content
        msg.html = render_template(
            'emails/waitlist_confirmation.html',
            email=email,
            discount_applied=discount_applied
        )
        
        # Send the email
        mail.send(msg)
        current_app.logger.info(f"Confirmation email sent to {email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send confirmation email: {str(e)}")
        return False
