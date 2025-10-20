#!/usr/bin/env python3
"""
Database migration script to add multi-user support
This script will:
1. Create the new users table
2. Add user_id columns to existing tables
3. Create a default admin user for existing data
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, ProjectMapping, UserConfig, ProcessingHistory, RecurringEventMapping

def create_default_user():
    """Create a default admin user for existing data"""
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
    return default_user

def add_user_id_columns():
    """Add user_id columns to existing tables"""
    import sqlite3

    # Get database path - check both possible locations
    db_paths = ['calendar_harvest.db', 'instance/calendar_harvest_dev.db']
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("No database file found. Creating new database...")
        db_path = 'instance/calendar_harvest_dev.db'
        # Ensure instance directory exists
        os.makedirs('instance', exist_ok=True)

    print(f"Using database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Creating users table...")
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    google_id VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    picture VARCHAR(500),
                    domain VARCHAR(255),
                    created_at DATETIME,
                    last_login DATETIME,
                    is_active BOOLEAN
                )
            ''')

        # Add user_id columns to existing tables if they don't exist
        tables_to_update = [
            'project_mappings',
            'user_config',
            'processing_history',
            'recurring_event_mappings'
        ]

        for table in tables_to_update:
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                # Check if user_id column exists
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [column[1] for column in cursor.fetchall()]

                if 'user_id' not in columns:
                    print(f"Adding user_id column to {table}...")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")

        # Add OAuth columns to user_config table if they don't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_config'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(user_config)")
            columns = [column[1] for column in cursor.fetchall()]

            oauth_columns = [
                ('harvest_oauth_token', 'TEXT'),
                ('harvest_refresh_token', 'VARCHAR(255)'),
                ('harvest_token_expires_at', 'DATETIME'),
                ('harvest_user_id', 'INTEGER'),
                ('harvest_user_email', 'VARCHAR(255)'),
                ('harvest_account_name', 'VARCHAR(255)')
            ]

            for column_name, column_type in oauth_columns:
                if column_name not in columns:
                    print(f"Adding {column_name} column to user_config...")
                    cursor.execute(f"ALTER TABLE user_config ADD COLUMN {column_name} {column_type}")

        conn.commit()
        print("Database schema updated successfully")

    except Exception as e:
        print(f"Error updating schema: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def migrate_existing_data(default_user_id):
    """Migrate existing data to be associated with the default user"""
    from sqlalchemy import text

    # Update ProjectMapping records
    db.session.execute(
        text("UPDATE project_mappings SET user_id = :user_id WHERE user_id IS NULL"),
        {'user_id': default_user_id}
    )

    # Update UserConfig records
    db.session.execute(
        text("UPDATE user_config SET user_id = :user_id WHERE user_id IS NULL"),
        {'user_id': default_user_id}
    )

    # Update ProcessingHistory records
    db.session.execute(
        text("UPDATE processing_history SET user_id = :user_id WHERE user_id IS NULL"),
        {'user_id': default_user_id}
    )

    # Update RecurringEventMapping records
    db.session.execute(
        text("UPDATE recurring_event_mappings SET user_id = :user_id WHERE user_id IS NULL"),
        {'user_id': default_user_id}
    )

    db.session.commit()

def run_migration():
    """Run the complete migration"""
    print("Starting multi-user migration...")

    try:
        # First, update the database schema
        print("Updating database schema...")
        add_user_id_columns()

        with app.app_context():
            # Create all tables (including the new users table)
            print("Creating/updating database tables...")
            db.create_all()

            # Check if we need to migrate existing data
            # Check if project_mappings table exists and has data
            from sqlalchemy import text
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM project_mappings")).scalar()
                has_existing_data = result > 0

                # If we have data, check if user_id column exists and is NULL
                if has_existing_data:
                    try:
                        null_result = db.session.execute(text("SELECT COUNT(*) FROM project_mappings WHERE user_id IS NULL")).scalar()
                        has_existing_data = null_result > 0
                    except:
                        # user_id column doesn't exist yet, so all data needs migration
                        has_existing_data = True
            except:
                # Table doesn't exist
                has_existing_data = False

            if has_existing_data:
                print("Found existing data. Creating default user...")
                default_user = create_default_user()

                print(f"Migrating existing data to user: {default_user.email}")
                migrate_existing_data(default_user.id)

                print("Migration completed successfully!")
                print(f"Default user created: {default_user.email}")
                print("You can now set up Google OAuth and have users log in with their Google Workspace accounts.")
                print("The existing data has been associated with the default admin user.")
            else:
                print("No existing data found. Database is ready for multi-user setup.")
                print("Users can now log in with their Google Workspace accounts.")

    except Exception as e:
        print(f"Migration failed: {e}")
        if 'app_context' in locals():
            db.session.rollback()
        return False

    return True

if __name__ == '__main__':
    success = run_migration()
    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Set up Google OAuth credentials (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)")
        print("2. Update the redirect URI in Google Console to match your domain")
        print("3. Restart the application")
        print("4. Users can now log in with their Google Workspace accounts")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
