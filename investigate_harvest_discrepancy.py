#!/usr/bin/env python3
"""
Investigate the discrepancy between what the app shows and what's actually in Harvest.
This will help identify why the app shows more entries than actually exist.
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
from harvest_oauth import harvest_oauth

def investigate_discrepancy():
    """Investigate the discrepancy between app display and actual Harvest entries."""
    
    print("🔍 INVESTIGATING HARVEST DISCREPANCY")
    print("=" * 70)
    print("Comparing what the app shows vs. what's actually in Harvest")
    print()
    
    with app.app_context():
        try:
            # Find a user with valid Harvest OAuth credentials
            user_configs = UserConfig.query.filter(
                UserConfig.harvest_oauth_token.isnot(None)
            ).all()
            
            if not user_configs:
                print("❌ No users with Harvest OAuth credentials found!")
                return
            
            # Use the first available user's credentials
            user_config = user_configs[0]
            app_user = User.query.filter_by(id=user_config.user_id).first()
            
            print(f"📡 Using credentials from app user: {app_user.email}")
            print(f"   (App User ID: {app_user.id})")
            
            # Check what Harvest user ID is stored in the database
            harvest_user_id = user_config.harvest_user_id
            print(f"🎯 Stored Harvest User ID: {harvest_user_id}")
            print()
            
            # Get OAuth token data
            token_data = user_config.get_harvest_oauth_token()
            if not token_data:
                print("❌ No valid OAuth token found!")
                return
            
            # Check if token is still valid
            if not user_config.is_harvest_token_valid():
                print("🔄 Token expired, attempting to refresh...")
                if user_config.harvest_refresh_token:
                    try:
                        new_token_data = harvest_oauth.refresh_token(user_config.harvest_refresh_token)
                        user_config.set_harvest_oauth_token(new_token_data)
                        db.session.commit()
                        token_data = new_token_data
                        print("✅ Token refreshed successfully!")
                    except Exception as e:
                        print(f"❌ Failed to refresh token: {e}")
                        return
                else:
                    print("❌ No refresh token available!")
                    return
            
            # Get API headers
            headers = harvest_oauth.get_api_headers(token_data)
            
            # Test period: July 21-27, 2025
            start_date = '2025-07-21'
            end_date = '2025-07-27'
            
            print(f"📅 Investigating period: {start_date} to {end_date}")
            print()
            
            # 1. Get ALL time entries for the period (no user filter)
            print("🔍 STEP 1: Getting ALL time entries for the period...")
            params_all = {
                'from': start_date,
                'to': end_date
            }
            
            response_all = requests.get('https://api.harvestapp.com/v2/time_entries', 
                                      headers=headers, params=params_all)
            
            if response_all.status_code != 200:
                print(f"❌ API request failed: {response_all.status_code}")
                print(f"   Response: {response_all.text}")
                return
            
            all_entries = response_all.json().get('time_entries', [])
            print(f"📊 Found {len(all_entries)} total entries in the period")
            
            # Group by user ID
            entries_by_user = {}
            for entry in all_entries:
                user_id = entry.get('user', {}).get('id')
                user_email = entry.get('user', {}).get('name', 'Unknown')
                
                if user_id not in entries_by_user:
                    entries_by_user[user_id] = {
                        'email': user_email,
                        'entries': []
                    }
                entries_by_user[user_id]['entries'].append(entry)
            
            print("\n👥 ENTRIES BY USER:")
            print("-" * 50)
            for user_id, user_data in entries_by_user.items():
                entries = user_data['entries']
                print(f"User ID {user_id} ({user_data['email']}): {len(entries)} entries")
                
                # Show entry details
                for entry in entries:
                    spent_date = entry.get('spent_date')
                    hours = entry.get('hours')
                    project = entry.get('project', {}).get('name', 'Unknown')
                    task = entry.get('task', {}).get('name', 'Unknown')
                    entry_id = entry.get('id')
                    
                    print(f"  📅 {spent_date}: {hours}h - {project} / {task} (ID: {entry_id})")
                print()
            
            # 2. Get entries filtered by the stored user ID
            print(f"🔍 STEP 2: Getting entries filtered by stored user ID ({harvest_user_id})...")
            params_filtered = {
                'from': start_date,
                'to': end_date,
                'user_id': harvest_user_id
            }
            
            response_filtered = requests.get('https://api.harvestapp.com/v2/time_entries', 
                                           headers=headers, params=params_filtered)
            
            if response_filtered.status_code != 200:
                print(f"❌ Filtered API request failed: {response_filtered.status_code}")
                print(f"   Response: {response_filtered.text}")
            else:
                filtered_entries = response_filtered.json().get('time_entries', [])
                print(f"📊 Found {len(filtered_entries)} entries for user ID {harvest_user_id}")
                
                if filtered_entries:
                    print("\n📋 FILTERED ENTRIES:")
                    print("-" * 30)
                    for entry in filtered_entries:
                        spent_date = entry.get('spent_date')
                        hours = entry.get('hours')
                        project = entry.get('project', {}).get('name', 'Unknown')
                        task = entry.get('task', {}).get('name', 'Unknown')
                        entry_id = entry.get('id')
                        user_info = entry.get('user', {})
                        
                        print(f"📅 {spent_date}: {hours}h - {project} / {task}")
                        print(f"   🆔 Entry ID: {entry_id}")
                        print(f"   👤 User: {user_info.get('name', 'Unknown')} (ID: {user_info.get('id', 'Unknown')})")
                        print()
            
            # 3. Check what the current user can see
            print("🔍 STEP 3: Checking current authenticated user...")
            me_response = requests.get('https://api.harvestapp.com/v2/users/me', headers=headers)
            
            if me_response.status_code == 200:
                me_data = me_response.json()
                current_user_id = me_data.get('id')
                current_user_email = me_data.get('email')
                
                print(f"👤 Current authenticated user: {current_user_email} (ID: {current_user_id})")
                print(f"🎯 Stored user ID in app: {harvest_user_id}")
                
                if current_user_id == harvest_user_id:
                    print("✅ User IDs match - this is correct")
                else:
                    print("⚠️  User ID mismatch!")
                    print(f"   Current user: {current_user_id}")
                    print(f"   Stored in app: {harvest_user_id}")
                
                # Get entries for the current authenticated user
                params_current = {
                    'from': start_date,
                    'to': end_date,
                    'user_id': current_user_id
                }
                
                response_current = requests.get('https://api.harvestapp.com/v2/time_entries', 
                                              headers=headers, params=params_current)
                
                if response_current.status_code == 200:
                    current_entries = response_current.json().get('time_entries', [])
                    print(f"📊 Entries for current user ({current_user_id}): {len(current_entries)}")
                    
                    if current_entries:
                        print("\n📋 CURRENT USER'S ACTUAL ENTRIES:")
                        print("-" * 40)
                        for entry in current_entries:
                            spent_date = entry.get('spent_date')
                            hours = entry.get('hours')
                            project = entry.get('project', {}).get('name', 'Unknown')
                            task = entry.get('task', {}).get('name', 'Unknown')
                            entry_id = entry.get('id')
                            
                            print(f"📅 {spent_date}: {hours}h - {project} / {task} (ID: {entry_id})")
                    else:
                        print("❌ No entries found for current authenticated user")
            
            # 4. Summary and analysis
            print("\n" + "=" * 70)
            print("📊 ANALYSIS SUMMARY:")
            print("=" * 70)
            
            print(f"🔢 Total entries in Harvest for period: {len(all_entries)}")
            print(f"👥 Number of different users with entries: {len(entries_by_user)}")
            
            if harvest_user_id in entries_by_user:
                stored_user_entries = len(entries_by_user[harvest_user_id]['entries'])
                print(f"📊 Entries for stored user ID ({harvest_user_id}): {stored_user_entries}")
            else:
                print(f"❌ No entries found for stored user ID ({harvest_user_id})")
            
            print("\n🔍 POSSIBLE CAUSES OF DISCREPANCY:")
            print("-" * 50)
            print("1. App might be showing cached/old data")
            print("2. App might be using a different API endpoint")
            print("3. App might be showing entries from multiple users")
            print("4. App might be showing preview/draft entries")
            print("5. Time zone differences in date filtering")
            print("6. App might be showing entries that were later deleted")
            
            # 5. Check what the app's time entries endpoint returns
            print("\n🔍 STEP 4: Testing app's time entries endpoint...")
            print("(This simulates what the app shows you)")
            
            # Import the harvest service to test the same method the app uses
            from harvest_service import HarvestService
            harvest_service = HarvestService()
            
            try:
                # Convert string dates to date objects
                from datetime import datetime
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                app_entries = harvest_service.get_time_entries(
                    start_date_obj, 
                    end_date_obj, 
                    user_id=app_user.id
                )
                
                print(f"📱 App's get_time_entries() returned: {len(app_entries)} entries")
                
                if app_entries:
                    print("\n📋 APP'S RETURNED ENTRIES:")
                    print("-" * 30)
                    for entry in app_entries[:10]:  # Show first 10
                        spent_date = entry.get('spent_date')
                        hours = entry.get('hours')
                        project = entry.get('project', {}).get('name', 'Unknown')
                        task = entry.get('task', {}).get('name', 'Unknown')
                        entry_id = entry.get('id')
                        user_info = entry.get('user', {})
                        
                        print(f"📅 {spent_date}: {hours}h - {project} / {task}")
                        print(f"   🆔 Entry ID: {entry_id}")
                        print(f"   👤 User: {user_info.get('name', 'Unknown')} (ID: {user_info.get('id', 'Unknown')})")
                        print()
                    
                    if len(app_entries) > 10:
                        print(f"   ... and {len(app_entries) - 10} more entries")
                
            except Exception as e:
                print(f"❌ Error testing app's time entries method: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ Error during investigation: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    investigate_discrepancy()
