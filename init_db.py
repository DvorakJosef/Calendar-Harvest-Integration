#!/usr/bin/env python3
"""
Initialize database with multi-user schema
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, db
from models import User, ProjectMapping, UserConfig, ProcessingHistory, RecurringEventMapping

def init_database():
    """Initialize the database with proper multi-user schema"""
    print("Initializing database with multi-user schema...")
    
    with app.app_context():
        try:
            # Drop all tables and recreate
            db.drop_all()
            print("Dropped existing tables")
            
            # Create all tables with new schema
            db.create_all()
            print("Created new tables with multi-user schema")
            
            # Create a default admin user for testing
            default_user = User(
                google_id='default_admin',
                email='admin@example.com',
                name='Default Admin User',
                domain='example.com',
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db.session.add(default_user)
            db.session.commit()
            print(f"Created default user: {default_user.email}")
            
            print("\n✅ Database initialized successfully!")
            print("The database is now ready for multi-user usage.")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    success = init_database()
    if success:
        print("\n🚀 You can now start the application with: python3 main.py")
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)
