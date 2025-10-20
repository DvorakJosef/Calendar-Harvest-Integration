#!/usr/bin/env python3
"""
Simple script to clean up all mappings for a user
"""

import os
import sys
from flask import Flask
from models import db, ProjectMapping, User

def create_app():
    """Create Flask app with database configuration"""
    app = Flask(__name__)
    
    # Load configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///calendar_harvest.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app

def cleanup_user_mappings(user_email):
    """Clean up all mappings for a specific user"""
    app = create_app()
    
    with app.app_context():
        # Find user by email
        user = User.query.filter_by(email=user_email).first()
        if not user:
            print(f"User with email {user_email} not found")
            return False
        
        print(f"Found user: {user.name} ({user.email})")
        
        # Get all mappings for this user
        mappings = ProjectMapping.query.filter_by(user_id=user.id).all()
        
        if not mappings:
            print("No mappings found for this user")
            return True
        
        print(f"Found {len(mappings)} mappings to delete:")
        for mapping in mappings:
            print(f"  - {mapping.calendar_label} -> {mapping.harvest_project_name}")
        
        # Ask for confirmation
        confirm = input(f"\nAre you sure you want to delete all {len(mappings)} mappings? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cleanup cancelled")
            return False
        
        # Delete all mappings
        deleted_count = 0
        for mapping in mappings:
            db.session.delete(mapping)
            deleted_count += 1
        
        db.session.commit()
        print(f"Successfully deleted {deleted_count} mappings")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cleanup_mappings.py <user_email>")
        print("Example: python cleanup_mappings.py josef.dvorak@directpeople.com")
        sys.exit(1)
    
    user_email = sys.argv[1]
    success = cleanup_user_mappings(user_email)
    sys.exit(0 if success else 1)
