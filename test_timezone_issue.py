#!/usr/bin/env python3
"""
Test script to demonstrate the timezone issue with date formatting
"""

from datetime import datetime, date, timezone, timedelta
import json

def test_date_formatting():
    """Test how JavaScript's toISOString() equivalent behaves in different scenarios"""
    
    print("Testing date formatting issues...")
    print("=" * 50)
    
    # Test case 1: June 30, 2025 (the week you mentioned)
    test_date = datetime(2025, 6, 30, 0, 0, 0)  # Midnight local time
    
    print(f"Original date: {test_date}")
    print(f"ISO string (UTC): {test_date.isoformat()}Z")
    print(f"Date only: {test_date.date()}")
    print(f"ISO date: {test_date.date().isoformat()}")
    print()
    
    # Test case 2: What happens with timezone-aware datetime
    
    # Simulate different timezones
    timezones = [
        ("UTC", timezone.utc),
        ("CET (UTC+1)", timezone(timedelta(hours=1))),
        ("EST (UTC-5)", timezone(timedelta(hours=-5))),
        ("PST (UTC-8)", timezone(timedelta(hours=-8))),
    ]
    
    for tz_name, tz in timezones:
        tz_date = test_date.replace(tzinfo=tz)
        utc_date = tz_date.astimezone(timezone.utc)
        
        print(f"{tz_name}:")
        print(f"  Local: {tz_date}")
        print(f"  UTC: {utc_date}")
        print(f"  ISO string: {utc_date.isoformat()}")
        print(f"  Date part: {utc_date.date()}")
        print()

def test_javascript_equivalent():
    """Test what JavaScript's toISOString().split('T')[0] would return"""
    
    print("JavaScript toISOString() equivalent test:")
    print("=" * 50)
    
    # This simulates what happens in the browser
    test_date = datetime(2025, 6, 30, 0, 0, 0)
    
    # JavaScript Date.toISOString() always returns UTC
    # If the browser is in a timezone ahead of UTC, the date might shift
    
    print(f"Original date: {test_date}")
    
    # Simulate browser in different timezones
    browser_timezones = [
        ("Browser in UTC", 0),
        ("Browser in CET (UTC+1)", 1),
        ("Browser in EST (UTC-5)", -5),
        ("Browser in JST (UTC+9)", 9),
    ]
    
    for tz_name, offset_hours in browser_timezones:
        # When JavaScript creates a Date object, it's in local time
        # But toISOString() converts to UTC
        local_midnight = datetime(2025, 6, 30, 0, 0, 0)
        
        # Simulate what happens when this gets converted to UTC
        utc_equivalent = local_midnight - timedelta(hours=offset_hours)
        iso_string = utc_equivalent.isoformat() + 'Z'
        date_part = iso_string.split('T')[0]
        
        print(f"{tz_name}:")
        print(f"  Local midnight: {local_midnight}")
        print(f"  UTC equivalent: {utc_equivalent}")
        print(f"  ISO string: {iso_string}")
        print(f"  Date part: {date_part}")
        print()

if __name__ == '__main__':
    test_date_formatting()
    print("\n" + "=" * 70 + "\n")
    test_javascript_equivalent()
