#!/usr/bin/env python3
"""
Debug script to test date processing in the mapping engine
"""

from datetime import datetime, date
import json

def test_event_date_extraction():
    """Test how event dates are extracted in _create_timesheet_entry"""
    
    print("Testing event date extraction...")
    print("=" * 50)
    
    # Simulate different event start time formats that might come from Google Calendar
    test_events = [
        {
            'id': 'test1',
            'summary': 'Test Event 1',
            'start': '2025-06-30T08:45:00+02:00',  # CET timezone
            'end': '2025-06-30T09:30:00+02:00',
            'duration': 0.75
        },
        {
            'id': 'test2', 
            'summary': 'Test Event 2',
            'start': '2025-06-30T08:45:00Z',  # UTC timezone
            'end': '2025-06-30T09:30:00Z',
            'duration': 0.75
        },
        {
            'id': 'test3',
            'summary': 'Test Event 3', 
            'start': '2025-06-30T08:45:00-05:00',  # EST timezone
            'end': '2025-06-30T09:30:00-05:00',
            'duration': 0.75
        }
    ]
    
    for event in test_events:
        print(f"Event: {event['summary']}")
        print(f"  Original start: {event['start']}")
        
        # Simulate the logic from _create_timesheet_entry
        if isinstance(event['start'], str):
            event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        else:
            event_start = event['start']
        
        event_date = event_start.date()
        
        print(f"  Parsed datetime: {event_start}")
        print(f"  Extracted date: {event_date}")
        print(f"  ISO date: {event_date.isoformat()}")
        print()

def test_week_start_processing():
    """Test how week_start is processed in the API endpoints"""
    
    print("Testing week_start processing...")
    print("=" * 50)
    
    # Test different week_start formats
    week_start_strings = [
        '2025-06-30',
        '2025-06-30T00:00:00',
        '2025-06-30T00:00:00Z'
    ]
    
    for week_start_str in week_start_strings:
        print(f"Week start string: {week_start_str}")
        
        try:
            # Simulate calendar_events endpoint
            week_start_datetime = datetime.fromisoformat(week_start_str)
            print(f"  Calendar API datetime: {week_start_datetime}")
            
            # Simulate process_preview endpoint  
            week_start_date = datetime.fromisoformat(week_start_str).date()
            print(f"  Process preview date: {week_start_date}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        print()

def test_date_comparison():
    """Test if there's a mismatch between calendar events and timesheet dates"""
    
    print("Testing date comparison...")
    print("=" * 50)
    
    # Simulate a scenario where week_start is 2025-06-30
    week_start_str = '2025-06-30'
    week_start_date = datetime.fromisoformat(week_start_str).date()
    
    print(f"Week start: {week_start_date}")
    
    # Simulate an event that should be in this week
    event_start_str = '2025-07-01T10:00:00+02:00'  # July 1st in CET
    event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
    event_date = event_start.date()
    
    print(f"Event start: {event_start_str}")
    print(f"Event datetime: {event_start}")
    print(f"Event date: {event_date}")
    
    # Check if event date is in the week
    from datetime import timedelta
    week_end_date = week_start_date + timedelta(days=6)
    print(f"Week range: {week_start_date} to {week_end_date}")
    print(f"Event in week: {week_start_date <= event_date <= week_end_date}")

if __name__ == '__main__':
    test_event_date_extraction()
    print("\n" + "=" * 70 + "\n")
    test_week_start_processing()
    print("\n" + "=" * 70 + "\n")
    test_date_comparison()
