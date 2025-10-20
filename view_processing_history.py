#!/usr/bin/env python3
"""
Utility to view recent processing history from the database.
This will show all time entries that have been created by the app.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the working main app
from working_main import app, db
from models import User, ProcessingHistory

def view_processing_history(days=7):
    """View processing history from the past N days."""
    
    print("📊 PROCESSING HISTORY VIEWER")
    print("=" * 60)
    print(f"Showing entries from the past {days} days...")
    print()
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            print(f"👥 Found {len(users)} users in database")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            print(f"📅 Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
            print()
            
            # Get processing history for all users
            history_entries = ProcessingHistory.query.filter(
                ProcessingHistory.processed_at >= start_date,
                ProcessingHistory.processed_at <= end_date
            ).order_by(ProcessingHistory.processed_at.desc()).all()
            
            if not history_entries:
                print("❌ No processing history found in the specified date range!")
                print("   This could mean:")
                print("   1. No time entries were created recently")
                print("   2. The logging system wasn't working")
                print("   3. Entries were created before the logging was implemented")
                return
            
            print(f"📋 Found {len(history_entries)} processing history entries")
            print()
            
            # Group by user
            entries_by_user = {}
            for entry in history_entries:
                user_id = entry.user_id
                if user_id not in entries_by_user:
                    user = User.query.get(user_id)
                    entries_by_user[user_id] = {
                        'user': user,
                        'entries': []
                    }
                entries_by_user[user_id]['entries'].append(entry)
            
            # Display entries by user
            for user_id, user_data in entries_by_user.items():
                user = user_data['user']
                entries = user_data['entries']
                
                print(f"👤 USER: {user.email} (ID: {user.id})")
                print(f"   📊 Total entries: {len(entries)}")
                
                # Count by status
                successful = len([e for e in entries if e.status == 'success'])
                failed = len([e for e in entries if e.status == 'error'])
                skipped = len([e for e in entries if e.status == 'skipped'])
                
                print(f"   ✅ Successful: {successful}")
                print(f"   ❌ Failed: {failed}")
                print(f"   ⏭️ Skipped: {skipped}")
                print()
                
                # Show recent entries (up to 10 most recent)
                recent_entries = sorted(entries, key=lambda x: x.processed_at, reverse=True)[:10]
                
                print("   📋 RECENT ENTRIES:")
                print("   " + "-" * 50)
                
                for entry in recent_entries:
                    status_icon = {
                        'success': '✅',
                        'error': '❌',
                        'skipped': '⏭️'
                    }.get(entry.status, '❓')
                    
                    print(f"   {status_icon} {entry.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"      📝 Event: {entry.calendar_event_summary}")
                    print(f"      ⏱️  Hours: {entry.hours_logged}h")
                    print(f"      🎯 Project: {entry.harvest_project_id}, Task: {entry.harvest_task_id}")
                    
                    if entry.harvest_time_entry_id:
                        print(f"      🆔 Harvest Entry ID: {entry.harvest_time_entry_id}")
                    
                    if entry.error_message:
                        print(f"      ⚠️  Error: {entry.error_message}")
                    
                    print()
                
                if len(entries) > 10:
                    print(f"   ... and {len(entries) - 10} more entries")
                
                print()
            
            # Summary statistics
            print("📊 SUMMARY STATISTICS:")
            print("-" * 60)
            
            total_successful = sum(len([e for e in user_data['entries'] if e.status == 'success']) 
                                 for user_data in entries_by_user.values())
            total_failed = sum(len([e for e in user_data['entries'] if e.status == 'error']) 
                             for user_data in entries_by_user.values())
            total_skipped = sum(len([e for e in user_data['entries'] if e.status == 'skipped']) 
                              for user_data in entries_by_user.values())
            total_hours = sum(e.hours_logged or 0 for e in history_entries if e.status == 'success')
            
            print(f"📈 Total entries processed: {len(history_entries)}")
            print(f"✅ Successful entries: {total_successful}")
            print(f"❌ Failed entries: {total_failed}")
            print(f"⏭️ Skipped entries: {total_skipped}")
            print(f"⏱️  Total hours logged: {total_hours:.2f}h")
            
            # Show most recent activity
            if history_entries:
                most_recent = history_entries[0]  # Already sorted by processed_at desc
                print(f"🕐 Most recent activity: {most_recent.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Event: {most_recent.calendar_event_summary}")
                print(f"   Status: {most_recent.status}")
            
        except Exception as e:
            print(f"❌ Error viewing processing history: {e}")
            import traceback
            traceback.print_exc()

def view_today_only():
    """View processing history from today only."""
    print("🗓️ TODAY'S PROCESSING HISTORY")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Get today's date range
            today = datetime.now().date()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            
            print(f"📅 Showing entries from: {start_of_day.strftime('%Y-%m-%d %H:%M')} to {end_of_day.strftime('%Y-%m-%d %H:%M')}")
            print()
            
            # Get today's processing history
            today_entries = ProcessingHistory.query.filter(
                ProcessingHistory.processed_at >= start_of_day,
                ProcessingHistory.processed_at <= end_of_day
            ).order_by(ProcessingHistory.processed_at.desc()).all()
            
            if not today_entries:
                print("❌ No processing history found for today!")
                print("   Try running the app to create some time entries.")
                return
            
            print(f"📋 Found {len(today_entries)} entries created today")
            print()
            
            for i, entry in enumerate(today_entries, 1):
                user = User.query.get(entry.user_id)
                status_icon = {
                    'success': '✅',
                    'error': '❌',
                    'skipped': '⏭️'
                }.get(entry.status, '❓')
                
                print(f"{i}. {status_icon} {entry.processed_at.strftime('%H:%M:%S')} - {user.email}")
                print(f"   📝 {entry.calendar_event_summary}")
                print(f"   ⏱️  {entry.hours_logged}h - Project: {entry.harvest_project_id}, Task: {entry.harvest_task_id}")
                
                if entry.harvest_time_entry_id:
                    print(f"   🆔 Harvest Entry ID: {entry.harvest_time_entry_id}")
                
                if entry.error_message:
                    print(f"   ⚠️  Error: {entry.error_message}")
                
                print()
                
        except Exception as e:
            print(f"❌ Error viewing today's history: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "today":
            view_today_only()
        elif sys.argv[1].isdigit():
            days = int(sys.argv[1])
            view_processing_history(days)
        else:
            print("Usage:")
            print("  python view_processing_history.py        # View last 7 days")
            print("  python view_processing_history.py today  # View today only")
            print("  python view_processing_history.py 30     # View last 30 days")
    else:
        view_processing_history(7)  # Default: last 7 days
