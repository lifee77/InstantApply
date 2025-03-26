#!/usr/bin/env python3
from flask import Flask
from models.user import db, User
from models.application import Application
import os
from dotenv import load_dotenv
from app import app, db

# Load environment variables
load_dotenv()

def init_db():
    """Initialize the database with tables"""
    print("Creating database tables...")
    
    # Create a minimal Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instant_apply.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the database with the app
    db.init_app(app)
    
    # Create the tables within the app context
    with app.app_context():
        # Create the resumes directory
        resumes_dir = os.path.join(app.instance_path, 'resumes')
        if not os.path.exists(resumes_dir):
            os.makedirs(resumes_dir)
            print(f"Created directory for storing resumes: {resumes_dir}")
        
        # Create all tables
        db.create_all()
        print("Database tables created.")
        
        # Check if tables were created
        engine = db.engine
        inspector = db.inspect(engine)
        tables = inspector.get_table_names()
        
        if 'users' in tables and 'applications' in tables:
            print("✅ Database tables created successfully:")
            for table in tables:
                print(f"  - {table}")
        else:
            print("❌ Error: Some tables were not created.")
            print(f"Available tables: {tables}")
            
if __name__ == "__main__":
    init_db()
