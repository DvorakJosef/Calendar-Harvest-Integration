#!/usr/bin/env python3
"""
Debug script to test Google Calendar date range calculations
"""

from datetime import datetime, timedelta

def test_google_calendar_date_range():
    """Test how Google Calendar API date ranges are calculated"""
    
    print("Testing Google Calendar date range calculations...")
    print("=" * 60)
    
    # Test the specific week you mentioned: June 30 - July 6, 2025
    week_start_str = '2025-06-30'
    week_start = datetime.fromisoformat(week_start_str)
    
    print(f"Week start input: {week_start_str}")
    print(f"Week start datetime: {week_start}")
    
    # This is the logic from google_calendar_service.py line 245
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    print(f"Week end calculated: {week_end}")
    
    # This is the logic from google_calendar_service.py lines 248-249
    time_min = week_start.isoformat() + 'Z' if week_start.tzinfo is None else week_start.isoformat()
    time_max = week_end.isoformat() + 'Z' if week_end.tzinfo is None else week_end.isoformat()
    
    print(f"Google Calendar API time_min: {time_min}")
    print(f"Google Calendar API time_max: {time_max}")
    
    print()
    print("Expected week range:")
    for i in range(7):
        day = week_start + timedelta(days=i)
        print(f"  {day.strftime('%A')}: {day.date()}")

def test_timezone_scenarios():
    """Test different timezone scenarios that might cause issues"""
    
    print("\nTesting timezone scenarios...")
    print("=" * 60)
    
    # Test what happens if the browser sends a different date due to timezone
    scenarios = [
        ("Browser sends correct date", "2025-06-30"),
        ("Browser in CET might send", "2025-06-29"),  # If timezone conversion shifts it
        ("Browser in JST might send", "2025-06-29"),  # If timezone conversion shifts it
    ]
    
    for scenario_name, week_start_str in scenarios:
        print(f"\n{scenario_name}: {week_start_str}")
        
        week_start = datetime.fromisoformat(week_start_str)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        print(f"  Week range: {week_start.date()} to {week_end.date()}")
        
        # Show what days this would cover
        days = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            days.append(day.strftime('%a %m-%d'))
        print(f"  Days: {' | '.join(days)}")

def test_event_date_extraction_scenarios():
    """Test how event dates would be extracted in different scenarios"""
    
    print("\nTesting event date extraction scenarios...")
    print("=" * 60)
    
    # Simulate events that might be returned by Google Calendar for different week ranges
    scenarios = [
        {
            'name': 'Correct week (June 30 - July 6)',
            'events': [
                {'summary': 'Monday Event', 'start': '2025-06-30T09:00:00+02:00'},
                {'summary': 'Tuesday Event', 'start': '2025-07-01T10:00:00+02:00'},
                {'summary': 'Wednesday Event', 'start': '2025-07-02T11:00:00+02:00'},
            ]
        },
        {
            'name': 'Wrong week (July 7 - July 13)',
            'events': [
                {'summary': 'Monday Event', 'start': '2025-07-07T09:00:00+02:00'},
                {'summary': 'Tuesday Event', 'start': '2025-07-08T10:00:00+02:00'},
                {'summary': 'Wednesday Event', 'start': '2025-07-09T11:00:00+02:00'},
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        for event in scenario['events']:
            # Simulate the _create_timesheet_entry logic
            event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            event_date = event_start.date()
            
            print(f"  {event['summary']}: {event['start']} -> {event_date}")

if __name__ == '__main__':
    test_google_calendar_date_range()
    test_timezone_scenarios()
    test_event_date_extraction_scenarios()
