#!/usr/bin/env python3
"""
Debug script to analyze event filtering for the week Aug 4-10, 2025
"""

import os
import sys
from datetime import datetime, timedelta
from google_calendar_service import GoogleCalendarService
from models import User, db
from main import app

def debug_event_filtering():
    """Debug what events are being filtered out"""
    
    with app.app_context():
        # Get user (assuming user ID 1)
        user = User.query.first()
        if not user:
            print("❌ No user found")
            return
            
        print(f"🔍 Debugging event filtering for user: {user.email}")
        print(f"📅 Week: Aug 4-10, 2025")
        print("=" * 60)
        
        # Initialize Google Calendar service
        google_service = GoogleCalendarService()
        
        # Set the week we're interested in
        week_start = datetime(2025, 8, 4)  # Monday Aug 4, 2025
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        print(f"🗓️  Week range: {week_start.date()} to {week_end.date()}")
        print()
        
        try:
            # Get raw events from Google Calendar API
            credentials = google_service._get_credentials()
            if not credentials:
                print("❌ No credentials found")
                return
                
            from googleapiclient.discovery import build
            service = build('calendar', 'v3', credentials=credentials)
            
            # Format dates for API
            time_min = week_start.isoformat() + 'Z'
            time_max = week_end.isoformat() + 'Z'
            
            print(f"🔍 Fetching raw events from Google Calendar API...")
            print(f"   Time range: {time_min} to {time_max}")
            
            # Fetch ALL events (no filtering)
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100
            ).execute()
            
            raw_events = events_result.get('items', [])
            print(f"📋 Found {len(raw_events)} raw events from Google Calendar")
            print()
            
            # Analyze each event
            filtered_out = []
            processed_events = []
            
            for i, event in enumerate(raw_events, 1):
                summary = event.get('summary', 'Untitled Event')
                start = event.get('start', {})
                end = event.get('end', {})
                
                print(f"🔍 Event {i}: {summary}")
                
                # Check filtering conditions
                reasons_filtered = []
                
                # Check 1: All-day events
                if 'dateTime' not in start or 'dateTime' not in end:
                    reasons_filtered.append("All-day event (no dateTime)")
                    print(f"   ❌ FILTERED: All-day event")
                    print(f"      Start: {start}")
                    print(f"      End: {end}")
                else:
                    # Parse times
                    try:
                        start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                        duration = (end_time - start_time).total_seconds() / 3600
                        
                        print(f"   ⏰ Start: {start_time}")
                        print(f"   ⏰ End: {end_time}")
                        print(f"   ⏱️  Duration: {duration:.2f} hours")
                        
                        # Check 2: Short events
                        if duration < 0.25:
                            reasons_filtered.append(f"Too short ({duration:.2f} hours < 0.25)")
                            print(f"   ❌ FILTERED: Too short ({duration:.2f} hours)")
                        else:
                            print(f"   ✅ PASSED: Duration OK")
                            
                    except Exception as e:
                        reasons_filtered.append(f"Time parsing error: {e}")
                        print(f"   ❌ FILTERED: Time parsing error: {e}")
                
                if reasons_filtered:
                    filtered_out.append({
                        'summary': summary,
                        'reasons': reasons_filtered,
                        'start': start,
                        'end': end
                    })
                else:
                    # Try to format the event
                    formatted_event = google_service._format_event(event)
                    if formatted_event:
                        processed_events.append(formatted_event)
                        print(f"   ✅ PROCESSED: Event will be included")
                    else:
                        filtered_out.append({
                            'summary': summary,
                            'reasons': ['Unknown formatting issue'],
                            'start': start,
                            'end': end
                        })
                        print(f"   ❌ FILTERED: Unknown formatting issue")
                
                print()
            
            # Summary
            print("=" * 60)
            print("📊 FILTERING SUMMARY")
            print("=" * 60)
            print(f"📋 Total raw events: {len(raw_events)}")
            print(f"✅ Events processed: {len(processed_events)}")
            print(f"❌ Events filtered out: {len(filtered_out)}")
            print()
            
            if filtered_out:
                print("🚫 FILTERED OUT EVENTS:")
                for event in filtered_out:
                    print(f"   • {event['summary']}")
                    for reason in event['reasons']:
                        print(f"     - {reason}")
                print()
            
            if processed_events:
                print("✅ PROCESSED EVENTS:")
                total_hours = 0
                for event in processed_events:
                    duration = event.get('duration', 0)
                    total_hours += duration
                    print(f"   • {event['summary']} ({duration:.2f}h)")
                print(f"   📊 Total hours: {total_hours:.1f}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_event_filtering()
