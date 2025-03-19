"""
Migration script to convert existing list data to JSON strings
Run this script after updating the User model but before restarting the app
"""
import os
import sys
import json

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from models.user import db, User

def migrate_lists_to_json():
    """Convert any list objects in the database to JSON strings"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        for user in users:
            # Check each field that should be JSON
            fields_to_check = [
                '_desired_job_titles', 
                '_portfolio_links', 
                '_certifications',
                '_languages',
                '_applicant_values'
            ]
            
            modified = False
            
            for field in fields_to_check:
                # Get the raw value using getattr
                raw_value = getattr(user, field)
                
                # Skip if it's already a string or None
                if raw_value is None or isinstance(raw_value, str):
                    continue
                
                # If it's a list or dict, convert to JSON string
                if isinstance(raw_value, (list, dict)):
                    setattr(user, field, json.dumps(raw_value))
                    modified = True
                    print(f"Converted {field} for user {user.id} from {type(raw_value)} to JSON string")
            
            if modified:
                try:
                    db.session.add(user)
                    db.session.commit()
                    print(f"Updated user {user.id}")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error updating user {user.id}: {str(e)}")

if __name__ == "__main__":
    migrate_lists_to_json()
    print("Migration complete")
