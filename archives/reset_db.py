#!/usr/bin/env python3
"""
Script to reset the database and create tables directly using SQLAlchemy
without using Flask-Migrate/Alembic
"""
import os
import sys

# Add the project root directory to Python's path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from models.user import db

def reset_database():
    # Create the Flask app with its configurations
    app = create_app()
    
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating all tables from models...")
        db.create_all()
        
        print("Database reset complete!")
        
if __name__ == '__main__':
    reset_database()