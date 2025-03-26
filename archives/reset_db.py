#!/usr/bin/env python3
from flask import Flask
from models.user import db, User
from models.application import Application
import os
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def reset_db():
    """Reset the database and recreate all tables"""
    print("Resetting database...")
    
    # Create a minimal Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instant_apply.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the database with the app
    db.init_app(app)
    
    # Database path
    db_path = 'instance/instant_apply.db'
    
    # Delete the existing database file
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Removed existing database: {db_path}")
    
    # Create the resumes directory (and clean it)
    with app.app_context():
        resumes_dir = os.path.join(app.instance_path, 'resumes')
        if os.path.exists(resumes_dir):
            shutil.rmtree(resumes_dir)
            print(f"✓ Cleaned up existing resumes directory")
            
        # Recreate the directory
        os.makedirs(resumes_dir, exist_ok=True)
        print(f"✓ Created directory for storing resumes: {resumes_dir}")
        
        # Create all tables
        db.create_all()
        print("✓ Created all database tables")
        
        # Check if tables were created
        engine = db.engine
        inspector = db.inspect(engine)
        tables = inspector.get_table_names()
        
        # Get columns for the users table
        columns = [column['name'] for column in inspector.get_columns('users')]
        
        print("\nDatabase Tables:")
        for table in tables:
            print(f"  - {table}")
            
        print("\nUsers Table Columns:")
        for column in columns:
            print(f"  - {column}")
        
        print("\n✅ Database reset complete. You'll need to create a new user account.")

if __name__ == "__main__":
    reset_db()
