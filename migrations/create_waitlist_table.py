"""
Migration script to create the waitlist table if it doesn't exist
"""
from flask import current_app
from models.user import db
from models.waitlist import Waitlist
from datetime import datetime

def run_migration():
    """Create the waitlist table if it doesn't exist"""
    print("Running waitlist table migration...")
    try:
        # Check if table exists
        if not db.engine.dialect.has_table(db.engine, 'waitlist'):
            # Create table
            Waitlist.__table__.create(db.engine)
            print("Waitlist table created successfully")
        else:
            print("Waitlist table already exists")
        return True
    except Exception as e:
        print(f"Error creating waitlist table: {str(e)}")
        return False

# This will be imported and run in app.py
def apply_migrations():
    """Apply all migrations"""
    return run_migration()
