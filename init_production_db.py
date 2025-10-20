#!/usr/bin/env python3
"""
Initialize production database with multi-user schema
"""

import os
import sys
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User, ProjectMapping, UserConfig, ProcessingHistory, RecurringEventMapping
from flask import Flask

def create_app():
    """Create Flask app with production configuration"""
    app = Flask(__name__)
    
    # Use production database URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'production-secret-key')
    
    db.init_app(app)
    return app

def init_production_database():
    """Initialize the production database with proper multi-user schema"""
    print("🗄️  Initializing production database with multi-user schema...")
    print(f"Database URL: {os.environ.get('DATABASE_URL', 'Not set')[:50]}...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables with new schema (don't drop existing ones)
            print("Creating database tables...")
            db.create_all()
            print("✅ Created database tables successfully")
            
            # Check if tables exist by trying to query users table
            try:
                user_count = db.session.execute(db.text("SELECT COUNT(*) FROM users")).scalar()
                print(f"✅ Users table exists with {user_count} users")
            except Exception as e:
                print(f"⚠️  Error checking users table: {e}")
            
            print("\n🎉 Production database initialized successfully!")
            print("The database is now ready for multi-user usage.")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    success = init_production_database()
    if success:
        print("\n🚀 Production database is ready!")
    else:
        print("\n❌ Production database initialization failed!")
        sys.exit(1)
