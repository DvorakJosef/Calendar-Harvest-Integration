#!/usr/bin/env python3
"""
Test script to create a time entry and verify it appears in Harvest
"""

import requests
from datetime import date
import sys

def test_create_time_entry():
    """Test creating a time entry"""
    
    access_token = "1154003.pt.odN48XY1TnZCWa9RAM7Mz6XiquIKO-TsoV5OQmeJfFCQmpW1r7Ln3-NIf7yJS_qCo0UE3MATljw5rxzVeHjrzw"
    account_id = "267801"
    
    base_url = 'https://api.harvestapp.com/v2'
    user_agent = 'Calendar-Harvest-Integration (contact@example.com)'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Harvest-Account-Id': account_id,
        'User-Agent': user_agent,
        'Content-Type': 'application/json'
    }
    
    # Test data - using known project/task IDs from logs
    test_entry = {
        'project_id': 39586657,  # AI project
        'task_id': 1639387,      # Project Management task
        'spent_date': '2025-06-23',
        'hours': 0.25,
        'notes': 'TEST ENTRY - Calendar Integration Debug - Please delete'
    }
    
    print("=== Creating test time entry ===")
    print(f"Data: {test_entry}")
    
    response = requests.post(f'{base_url}/time_entries', headers=headers, json=test_entry)
    print(f"Create response: {response.status_code}")
    print(f"Response body: {response.text}")
    
    if response.status_code == 201:
        entry_data = response.json()
        entry_id = entry_data['id']
        print(f"✅ SUCCESS: Created entry with ID {entry_id}")
        
        # Verify it exists by fetching it directly
        print(f"\n=== Verifying created entry ===")
        response = requests.get(f'{base_url}/time_entries/{entry_id}', headers=headers)
        print(f"Verify response: {response.status_code}")
        if response.status_code == 200:
            entry = response.json()
            print(f"✅ Entry verified:")
            print(f"  - ID: {entry['id']}")
            print(f"  - Date: {entry['spent_date']}")
            print(f"  - Hours: {entry['hours']}")
            print(f"  - Notes: {entry['notes']}")
            print(f"  - Project: {entry['project']['name']}")
            print(f"  - Task: {entry['task']['name']}")
        else:
            print("❌ Entry not found after creation")
            
        # Check if it appears in the time entries list for that date
        print(f"\n=== Checking time entries list for 2025-06-23 ===")
        response = requests.get(f'{base_url}/time_entries?from=2025-06-23&to=2025-06-23', headers=headers)
        print(f"List response: {response.status_code}")
        if response.status_code == 200:
            entries = response.json()['time_entries']
            found = False
            for entry in entries:
                if entry['id'] == entry_id:
                    found = True
                    print(f"✅ Entry found in list: {entry['hours']}h - {entry['notes']}")
                    break
            if not found:
                print(f"❌ Entry {entry_id} not found in time entries list")
        
        # Clean up - delete the test entry
        print(f"\n=== Cleaning up test entry ===")
        response = requests.delete(f'{base_url}/time_entries/{entry_id}', headers=headers)
        print(f"Delete response: {response.status_code}")
        if response.status_code == 200:
            print("✅ Test entry deleted successfully")
        else:
            print("❌ Failed to delete test entry")
            
    else:
        print(f"❌ FAILED to create entry: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_create_time_entry()
