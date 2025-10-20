#!/usr/bin/env python3
"""
Test script to verify that the user authentication fix is working
This simulates the calendar processing with proper user context
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import db, User, UserConfig
from harvest_service import HarvestService

def test_user_auth_fix():
    """Test that Harvest service properly uses user credentials"""
    
    with app.app_context():
        # Get the first user from the database
        user = User.query.first()
        if not user:
            print("❌ No users found in database")
            return False
            
        print(f"✅ Found user: {user.email} (ID: {user.id})")
        
        # Check if user has Harvest credentials
        user_config = UserConfig.query.filter_by(user_id=user.id).first()
        if not user_config or not user_config.harvest_access_token:
            print("❌ User has no Harvest credentials configured")
            return False
            
        print(f"✅ User has Harvest credentials configured")
        print(f"   Account ID: {user_config.harvest_account_id}")
        print(f"   Token (first 10 chars): {user_config.harvest_access_token[:10]}...")
        
        # Test HarvestService with explicit user_id
        harvest_service = HarvestService()
        
        # Test 1: Check if user credentials work
        print("\n🔍 Testing Harvest API connection with user credentials...")
        is_connected = harvest_service.is_connected(user_id=user.id)
        if not is_connected:
            print("❌ Harvest API connection failed with user credentials")
            return False
        print("✅ Harvest API connection successful")
        
        # Test 2: Try to get projects with user_id
        print("\n🔍 Testing get_projects with user_id...")
        try:
            projects = harvest_service.get_projects(user_id=user.id)
            print(f"✅ Successfully retrieved {len(projects)} projects")
            if projects:
                print(f"   First project: {projects[0]['name']}")
        except Exception as e:
            print(f"❌ Error getting projects: {e}")
            return False
        
        # Test 3: Try to get time entries with user_id
        print("\n🔍 Testing get_time_entries with user_id...")
        try:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            entries = harvest_service.get_time_entries(week_start, week_end, user_id=user.id)
            print(f"✅ Successfully retrieved {len(entries)} time entries for this week")
        except Exception as e:
            print(f"❌ Error getting time entries: {e}")
            return False
        
        # Test 4: Test create_time_entry method signature
        print("\n🔍 Testing create_time_entry method signature...")
        try:
            # Just verify the method signature accepts user_id
            import inspect
            sig = inspect.signature(harvest_service.create_time_entry)
            if 'user_id' in sig.parameters:
                print("✅ create_time_entry method accepts user_id parameter")
            else:
                print("❌ create_time_entry method does not accept user_id parameter")
                return False
        except Exception as e:
            print(f"❌ Error checking method signature: {e}")
            return False
        
        print("\n🎉 All tests passed! The user authentication fix is working correctly.")
        return True

if __name__ == "__main__":
    success = test_user_auth_fix()
    sys.exit(0 if success else 1)
