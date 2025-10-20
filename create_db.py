#!/usr/bin/env python3
"""
Create database with proper schema
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from app import app
from models import db, User, ProjectMapping, UserConfig, ProcessingHistory, RecurringEventMapping

def create_database():
    """Create the database with all tables"""
    print("Creating database...")
    
    # Remove existing database
    db_path = 'calendar_harvest.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Created all tables")
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Created tables: {tables}")
            
            # Create default user
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
            print(f"Created default user: {default_user.email} (ID: {default_user.id})")
            
            # Verify the schema
            for table_name in tables:
                columns = inspector.get_columns(table_name)
                print(f"\nTable '{table_name}' columns:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")
            
            print("\n✅ Database created successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = create_database()
    if not success:
        sys.exit(1)
