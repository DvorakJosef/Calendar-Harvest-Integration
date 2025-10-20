#!/usr/bin/env python3
"""
Test the calendar API endpoint directly
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
env_file = '.env.development'
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded configuration from {env_file}")

# Import modules individually (not from main.py)
from models import db, User, UserConfig
from working_main import app

print("🔍 TESTING CALENDAR API ENDPOINT DIRECTLY")
print("=" * 60)

with app.app_context():
    # Get the user
    user = User.query.filter_by(email='josef.dvorak@directpeople.com').first()
    if not user:
        print("❌ User not found")
        exit(1)
    
    print(f"👤 User: {user.email} (ID: {user.id})")

# Test the API endpoint using the test client
print("\n🔍 TESTING API ENDPOINT:")
print("-" * 40)

with app.test_client() as client:
    # Create a session
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
    
    # Test the calendar events endpoint
    response = client.get('/api/calendar/events?week_start=2025-08-04')
    
    print(f"📊 Response Status: {response.status_code}")
    print(f"📊 Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        try:
            data = response.get_json()
            print(f"✅ Success: {data.get('success', False)}")
            
            if data.get('success'):
                events = data.get('events', [])
                print(f"📊 Events count: {len(events)}")
                
                if events:
                    print("\n📋 Sample events:")
                    for i, event in enumerate(events[:3]):
                        print(f"  {i+1}. {event.get('summary', 'No title')}")
                        print(f"     Start: {event.get('start', 'No start')}")
                        print(f"     End: {event.get('end', 'No end')}")
                else:
                    print("❌ No events returned")
            else:
                print(f"❌ API returned error: {data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error parsing JSON response: {e}")
            print(f"📄 Raw response: {response.get_data(as_text=True)[:500]}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"📄 Response: {response.get_data(as_text=True)[:500]}")

print("\n" + "=" * 60)
print("🎯 NEXT STEPS:")
print("-" * 20)
print("If this test shows events but the frontend doesn't:")
print("1. Check browser console for JavaScript errors")
print("2. Check browser network tab for failed requests")
print("3. Check if session cookies are being sent")
print("4. Try refreshing the page and clearing browser cache")
