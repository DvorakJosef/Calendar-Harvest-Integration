#!/usr/bin/env python3
"""
Debug script to compare proposed timesheet entries vs actual Harvest entries.
This will help identify why the app shows different entries than what exists in Harvest.
"""

import os
import sys
import requests
from datetime import datetime, timedelta

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the working main app
from working_main import app, db
from models import User, UserConfig
from harvest_service import HarvestService

def debug_proposed_vs_actual():
    """Compare proposed timesheet entries vs actual Harvest entries."""
    
    print("🔍 DEBUGGING PROPOSED VS ACTUAL ENTRIES")
    print("=" * 70)
    print("Comparing what the app proposes vs. what's actually in Harvest")
    print()
    
    with app.app_context():
        try:
            # Find a user with valid credentials
            user_configs = UserConfig.query.filter(
                UserConfig.harvest_oauth_token.isnot(None)
            ).all()
            
            if not user_configs:
                print("❌ No users with Harvest OAuth credentials found!")
                return
            
            user_config = user_configs[0]
            app_user = User.query.filter_by(id=user_config.user_id).first()
            
            print(f"📡 Using credentials from app user: {app_user.email}")
            print(f"   (App User ID: {app_user.id})")
            print()
            
            # Test period: July 21-27, 2025
            start_date = datetime(2025, 7, 21).date()
            end_date = datetime(2025, 7, 27).date()
            
            print(f"📅 Testing period: {start_date} to {end_date}")
            print()
            
            # 1. Get what the app proposes to create
            print("🔍 STEP 1: Getting proposed timesheet entries from app...")
            
            # Call the preview API endpoint directly to simulate what the frontend does
            print("🔍 Calling preview API endpoint...")

            # Make a request to the preview endpoint
            import json
            from flask import Flask
            from flask.testing import FlaskClient

            # Create a test client
            with app.test_client() as client:
                # Simulate the user session
                with client.session_transaction() as sess:
                    sess['user_id'] = app_user.id

                # Make the preview request
                response = client.post('/api/process/preview',
                    json={'week_start': start_date.isoformat()},
                    content_type='application/json'
                )

                if response.status_code == 200:
                    result = response.get_json()
                    print(f"✅ Preview API successful")
                else:
                    print(f"❌ Preview API failed: {response.status_code}")
                    print(f"   Response: {response.get_data(as_text=True)}")
                    result = {'timesheet_entries': []}
            
            proposed_entries = result.get('timesheet_entries', [])
            print(f"📊 App proposes to create: {len(proposed_entries)} entries")
            
            if proposed_entries:
                print("\n📋 PROPOSED ENTRIES:")
                print("-" * 40)
                for i, entry in enumerate(proposed_entries, 1):
                    date = entry.get('date', 'Unknown')
                    hours = entry.get('hours', 0)
                    project = entry.get('project_name', 'Unknown')
                    task = entry.get('task_name', 'Unknown')
                    event_summary = entry.get('event_summary', 'Unknown')
                    
                    print(f"{i}. 📅 {date}: {hours}h")
                    print(f"   🎯 {project} / {task}")
                    print(f"   📝 Event: {event_summary}")
                    print()
            
            # 2. Get what actually exists in Harvest
            print("🔍 STEP 2: Getting actual entries from Harvest...")
            
            harvest_service = HarvestService()
            actual_entries = harvest_service.get_time_entries(
                start_date, 
                end_date, 
                user_id=app_user.id
            )
            
            print(f"📊 Actually exists in Harvest: {len(actual_entries)} entries")
            
            if actual_entries:
                print("\n📋 ACTUAL ENTRIES IN HARVEST:")
                print("-" * 40)
                for i, entry in enumerate(actual_entries, 1):
                    spent_date = entry.get('spent_date', 'Unknown')
                    hours = entry.get('hours', 0)
                    project = entry.get('project', {}).get('name', 'Unknown')
                    task = entry.get('task', {}).get('name', 'Unknown')
                    entry_id = entry.get('id', 'Unknown')
                    notes = entry.get('notes', '')
                    
                    print(f"{i}. 📅 {spent_date}: {hours}h")
                    print(f"   🎯 {project} / {task}")
                    print(f"   🆔 Entry ID: {entry_id}")
                    if notes:
                        print(f"   📝 Notes: {notes}")
                    print()
            
            # 3. Compare and analyze differences
            print("=" * 70)
            print("📊 COMPARISON ANALYSIS:")
            print("=" * 70)
            
            print(f"📈 Proposed entries: {len(proposed_entries)}")
            print(f"📊 Actual entries: {len(actual_entries)}")
            print(f"📉 Difference: {len(proposed_entries) - len(actual_entries)}")
            print()
            
            # Group proposed entries by date
            proposed_by_date = {}
            for entry in proposed_entries:
                date = entry.get('date', 'Unknown')
                if date not in proposed_by_date:
                    proposed_by_date[date] = []
                proposed_by_date[date].append(entry)
            
            # Group actual entries by date
            actual_by_date = {}
            for entry in actual_entries:
                date = entry.get('spent_date', 'Unknown')
                if date not in actual_by_date:
                    actual_by_date[date] = []
                actual_by_date[date].append(entry)
            
            # Compare by date
            all_dates = set(proposed_by_date.keys()) | set(actual_by_date.keys())
            
            print("📅 COMPARISON BY DATE:")
            print("-" * 50)
            
            for date in sorted(all_dates):
                proposed_count = len(proposed_by_date.get(date, []))
                actual_count = len(actual_by_date.get(date, []))
                
                print(f"📅 {date}:")
                print(f"   📈 Proposed: {proposed_count} entries")
                print(f"   📊 Actual: {actual_count} entries")
                
                if proposed_count != actual_count:
                    print(f"   ⚠️  MISMATCH: {proposed_count - actual_count} difference")
                
                # Show details for mismatched dates
                if proposed_count != actual_count:
                    if date in proposed_by_date:
                        print(f"   📋 Proposed entries for {date}:")
                        for entry in proposed_by_date[date]:
                            project = entry.get('project_name', 'Unknown')
                            task = entry.get('task_name', 'Unknown')
                            hours = entry.get('hours', 0)
                            print(f"      - {project} / {task}: {hours}h")
                    
                    if date in actual_by_date:
                        print(f"   📋 Actual entries for {date}:")
                        for entry in actual_by_date[date]:
                            project = entry.get('project', {}).get('name', 'Unknown')
                            task = entry.get('task', {}).get('name', 'Unknown')
                            hours = entry.get('hours', 0)
                            print(f"      - {project} / {task}: {hours}h")
                
                print()
            
            # 4. Analyze potential causes
            print("🔍 POTENTIAL CAUSES OF DISCREPANCY:")
            print("-" * 50)
            
            if len(proposed_entries) > len(actual_entries):
                print("📈 App proposes MORE entries than exist in Harvest:")
                print("   1. Calendar events are being processed that shouldn't be")
                print("   2. Project/task mappings are creating duplicate entries")
                print("   3. Event filtering is not working correctly")
                print("   4. Time zone issues causing date mismatches")
                
            elif len(proposed_entries) < len(actual_entries):
                print("📉 App proposes FEWER entries than exist in Harvest:")
                print("   1. Some calendar events are being filtered out")
                print("   2. Project/task mappings are missing")
                print("   3. Calendar service is not finding all events")
                
            else:
                print("📊 Same number of entries, but content differs:")
                print("   1. Project/task mappings are incorrect")
                print("   2. Hours calculation is different")
                print("   3. Date processing has issues")
            
            # 5. Summary and recommendations
            print("\n🔍 STEP 3: Summary and recommendations...")
            
            print("\n🎯 RECOMMENDATION:")
            print("-" * 50)
            print("1. Check the calendar event filtering logic")
            print("2. Verify project/task mapping rules")
            print("3. Review time zone handling")
            print("4. Test with a smaller date range")
            print("5. Check for duplicate event processing")
                
        except Exception as e:
            print(f"❌ Error during debugging: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_proposed_vs_actual()
