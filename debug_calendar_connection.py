#!/usr/bin/env python3
"""
Debug script to check Google Calendar connection status
"""

import os
from dotenv import load_dotenv

# Load environment variables
env_file = '.env.development'
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded configuration from {env_file}")

# Import modules individually (not from main.py)
from models import db, User, UserConfig
from working_main import app

print("🔍 DEBUGGING GOOGLE CALENDAR CONNECTION")
print("=" * 60)

with app.app_context():
    # Get the user
    user = User.query.filter_by(email='josef.dvorak@directpeople.com').first()
    if not user:
        print("❌ User not found")
        exit(1)
    
    print(f"👤 User: {user.email} (ID: {user.id})")
    
    # Check user config
    user_config = UserConfig.query.filter_by(user_id=user.id).first()
    if not user_config:
        print("❌ No user config found")
        exit(1)
    
    print(f"🔧 User config found")
    
    # Check Google Calendar credentials
    print("\n🔍 GOOGLE CALENDAR STATUS:")
    print("-" * 40)
    
    try:
        from google_calendar_service import GoogleCalendarService
        
        # Create a mock request context for testing
        with app.test_request_context():
            # Set up session
            from flask import session
            session['user_id'] = user.id
            
            google_service = GoogleCalendarService()
            
            # Check if connected
            is_connected = google_service.is_connected()
            print(f"📊 Connected: {is_connected}")
            
            if is_connected:
                print("✅ Google Calendar is connected")
                
                # Try to get some events
                from datetime import datetime
                week_start = datetime(2025, 8, 4)
                print(f"📅 Testing events for week: {week_start.strftime('%Y-%m-%d')}")
                
                try:
                    events = google_service.get_calendar_events(week_start=week_start)
                    print(f"📊 Found {len(events) if events else 0} events")
                    
                    if events:
                        print("\n📋 Sample events:")
                        for i, event in enumerate(events[:3]):
                            print(f"  {i+1}. {event.get('summary', 'No title')}")
                            print(f"     Start: {event.get('start', 'No start')}")
                            print(f"     End: {event.get('end', 'No end')}")
                except Exception as e:
                    print(f"❌ Error getting events: {e}")
            else:
                print("❌ Google Calendar is NOT connected")
                print("💡 User needs to authenticate with Google Calendar first")
                
    except Exception as e:
        print(f"❌ Error checking Google Calendar: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("🎯 RECOMMENDATIONS:")
print("-" * 20)
print("1. Go to Setup page")
print("2. Check if Google Calendar shows as 'Connected'")
print("3. If not, click 'Connect Google Calendar'")
print("4. Complete the authentication flow")
print("5. Return to Process page and try again")
