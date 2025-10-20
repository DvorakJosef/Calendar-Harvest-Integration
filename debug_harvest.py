#!/usr/bin/env python3
"""
Debug script to test Harvest API connection
"""

import requests
import sys

def test_harvest_connection(access_token, account_id):
    """Test Harvest API connection with detailed error reporting"""
    
    base_url = 'https://api.harvestapp.com/v2'
    user_agent = 'Calendar-Harvest-Integration (contact@example.com)'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Harvest-Account-Id': account_id,
        'User-Agent': user_agent,
        'Content-Type': 'application/json'
    }
    
    print(f"Testing Harvest API connection...")
    print(f"Account ID: {account_id}")
    print(f"Token (first 10 chars): {access_token[:10]}...")
    print(f"URL: {base_url}/users/me")
    print(f"Headers: {headers}")
    print()
    
    try:
        response = requests.get(f'{base_url}/users/me', headers=headers)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Harvest API connection working!")
            return True
        else:
            print(f"❌ ERROR: Harvest API returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python debug_harvest.py <access_token> <account_id>")
        sys.exit(1)
    
    access_token = sys.argv[1]
    account_id = sys.argv[2]
    
    test_harvest_connection(access_token, account_id)
