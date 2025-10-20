#!/usr/bin/env python3
"""
Database Migration: Add OAuth Fields to UserConfig
Adds the new OAuth fields to the user_config table
"""

import sqlite3
import sys
import os

def migrate_database():
    """Add OAuth fields to user_config table"""
    
    db_path = 'calendar_harvest.db'
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Adding OAuth fields to user_config table...")
        
        # Add new OAuth columns
        oauth_columns = [
            ('harvest_oauth_token', 'TEXT'),
            ('harvest_refresh_token', 'VARCHAR(255)'),
            ('harvest_token_expires_at', 'DATETIME'),
            ('harvest_user_id', 'INTEGER'),
            ('harvest_user_email', 'VARCHAR(255)'),
            ('harvest_account_name', 'VARCHAR(255)')
        ]
        
        for column_name, column_type in oauth_columns:
            try:
                cursor.execute(f'ALTER TABLE user_config ADD COLUMN {column_name} {column_type}')
                print(f"✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"⏭️  Column {column_name} already exists")
                else:
                    print(f"❌ Error adding column {column_name}: {e}")
                    return False
        
        conn.commit()
        
        # Verify the new schema
        cursor.execute("PRAGMA table_info(user_config)")
        columns = cursor.fetchall()
        
        print("\n📋 Updated user_config schema:")
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
        conn.close()
        
        print("\n✅ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def clear_legacy_credentials():
    """Clear legacy personal access tokens"""
    
    try:
        conn = sqlite3.connect('calendar_harvest.db')
        cursor = conn.cursor()
        
        print("\n🧹 Clearing legacy personal access tokens...")
        
        # Check what's currently stored
        cursor.execute("SELECT user_id, harvest_access_token FROM user_config WHERE harvest_access_token IS NOT NULL")
        legacy_tokens = cursor.fetchall()
        
        if legacy_tokens:
            print(f"Found {len(legacy_tokens)} legacy tokens:")
            for user_id, token in legacy_tokens:
                print(f"   User {user_id}: {token[:20]}...")
            
            # Clear legacy tokens
            cursor.execute("UPDATE user_config SET harvest_access_token = NULL WHERE harvest_access_token IS NOT NULL")
            conn.commit()
            
            print("✅ Legacy tokens cleared")
        else:
            print("No legacy tokens found")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error clearing legacy credentials: {e}")

if __name__ == "__main__":
    print("🛠️  DATABASE MIGRATION: OAuth Fields")
    print("=" * 50)
    
    # Run migration
    if migrate_database():
        # Ask user if they want to clear legacy tokens
        response = input("\n🤔 Clear legacy personal access tokens? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            clear_legacy_credentials()
        
        print("\n🎉 Migration complete! You can now use OAuth authentication.")
        print("💡 Next step: Reconnect to Harvest using OAuth on the setup page.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)
