#!/usr/bin/env python3
"""
Debug script to check what's happening with week processing
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from google_calendar_service import GoogleCalendarService
from mapping_engine import MappingEngine
from models import User

def debug_week_processing(week_start_str: str, user_id: int = 1):
    """Debug processing for a specific week"""

    print(f"\n🔍 Debugging week processing for {week_start_str}")
    print("=" * 60)

    with app.app_context():
        # Create a test request context to simulate being in a web request
        with app.test_request_context():
            # Initialize services
            google_service = GoogleCalendarService()
            mapping_engine = MappingEngine()

            # Parse week start
            week_start = datetime.fromisoformat(week_start_str)
            week_start_date = week_start.date()
            week_end_date = week_start_date + timedelta(days=6)

            print(f"📅 Week: {week_start_date} to {week_end_date}")

            # 1. Check if user exists and has credentials
            user = User.query.get(user_id)
            if not user:
                print(f"❌ User {user_id} not found")
                return

            print(f"✅ User found: {user.email}")

            # 2. Get calendar events
            try:
                events = google_service.get_calendar_events(week_start)
                print(f"📋 Found {len(events)} calendar events")

                if not events:
                    print("❌ No calendar events found for this week")
                    return

                # Show event details
                for i, event in enumerate(events, 1):
                    print(f"  {i}. {event.get('summary', 'No title')}")
                    print(f"     Start: {event.get('start')}")
                    print(f"     Duration: {event.get('duration')} hours")
                    print(f"     Attendance: {event.get('attendance_status', 'unknown')}")
                    print(f"     Extracted label: {event.get('extracted_label', 'None')}")
                    print()

            except Exception as e:
                print(f"❌ Error getting calendar events: {e}")
                return
        
        # 3. Check mappings
        mappings = mapping_engine.get_mappings(user_id)
        print(f"🗂️  Found {len(mappings)} mappings:")
        for mapping in mappings:
            print(f"  - '{mapping.calendar_label}' → {mapping.harvest_project_name}")
        print()
        
        # 4. Check which events would be mapped
        mapped_count = 0
        unmapped_events = []
        
        for event in events:
            mapping = mapping_engine.find_mapping_for_event(event, user_id)
            if mapping:
                mapped_count += 1
                print(f"✅ '{event.get('summary')}' → {mapping.calendar_label}")
            else:
                unmapped_events.append(event)
                print(f"❌ '{event.get('summary')}' → No mapping found")
        
        print(f"\n📊 Summary: {mapped_count} mapped, {len(unmapped_events)} unmapped")
        
        # 5. Check if events were already processed
        processed_event_ids = mapping_engine._get_processed_event_ids(week_start_date, user_id)
        if processed_event_ids:
            print(f"⚠️  {len(processed_event_ids)} events already processed:")
            for event_id in processed_event_ids:
                print(f"  - {event_id}")
        else:
            print("✅ No events previously processed for this week")
        
        # 6. Try processing
        if mapped_count > 0:
            print(f"\n🔄 Attempting to process {mapped_count} mapped events...")
            try:
                results = mapping_engine.process_events_for_week(events, week_start_date, user_id)
                print(f"📈 Processing results:")
                print(f"  - Total events: {results['total_events']}")
                print(f"  - Mapped events: {results['mapped_events']}")
                print(f"  - Unmapped events: {results['unmapped_events']}")
                print(f"  - Timesheet entries: {len(results['timesheet_entries'])}")
                print(f"  - Warnings: {len(results['warnings'])}")
                
                if results['warnings']:
                    print("⚠️  Warnings:")
                    for warning in results['warnings']:
                        print(f"    - {warning}")
                
                if results['timesheet_entries']:
                    print("📋 Timesheet entries that would be created:")
                    for entry in results['timesheet_entries']:
                        print(f"  - {entry['event_summary']}: {entry['hours']}h → {entry['project_name']}")
                
            except Exception as e:
                print(f"❌ Error processing events: {e}")
                import traceback
                traceback.print_exc()

if __name__ == '__main__':
    # Debug the specific week you mentioned
    debug_week_processing('2025-06-30')
