#!/usr/bin/env python3
"""
Test Harvest OAuth Configuration
Simple test to verify OAuth credentials are working
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_oauth_configuration():
    """Test OAuth configuration and credentials"""
    print("🔐 HARVEST OAUTH CONFIGURATION TEST")
    print("=" * 50)
    
    # Check environment variables
    client_id = os.getenv('HARVEST_CLIENT_ID')
    client_secret = os.getenv('HARVEST_CLIENT_SECRET') 
    redirect_uri = os.getenv('HARVEST_REDIRECT_URI')
    
    print(f"Client ID: {client_id[:10] if client_id else 'Not set'}...")
    print(f"Client Secret: {'✅ Set' if client_secret else '❌ Not set'}")
    print(f"Redirect URI: {redirect_uri if redirect_uri else '❌ Not set'}")
    
    # Test OAuth service
    try:
        from harvest_oauth import harvest_oauth
        is_configured = harvest_oauth.is_configured()
        print(f"OAuth Service: {'✅ Configured' if is_configured else '❌ Not configured'}")
        
        if is_configured:
            print(f"Authorization URL: {harvest_oauth.authorization_base_url}")
            print(f"Token URL: {harvest_oauth.token_url}")
            
            # Test authorization URL generation
            try:
                auth_url, state = harvest_oauth.get_authorization_url(user_id=1)
                print(f"Auth URL Generation: ✅ Working")
                print(f"Sample Auth URL: {auth_url[:80]}...")
                print(f"State Parameter: {state[:20]}...")
                
                return True
                
            except Exception as e:
                print(f"Auth URL Generation: ❌ Error: {e}")
                return False
        else:
            print("❌ OAuth not properly configured")
            return False
    
    except Exception as e:
        print(f"OAuth Service: ❌ Error: {e}")
        return False

def test_oauth_endpoints():
    """Test OAuth endpoints are accessible"""
    print("\n🌐 TESTING OAUTH ENDPOINTS")
    print("=" * 50)
    
    import requests
    
    base_url = "http://127.0.0.1:5001"
    
    endpoints = [
        "/auth/harvest",
        "/auth/harvest/callback",
        "/api/harvest/oauth/status"
    ]
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, allow_redirects=False, timeout=5)
            
            # Any response (even redirect) means endpoint exists
            if response.status_code in [200, 302, 401, 403]:
                print(f"✅ {endpoint}: Accessible (status: {response.status_code})")
            else:
                print(f"⚠️  {endpoint}: Unexpected status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: Server not running")
        except Exception as e:
            print(f"❌ {endpoint}: Error: {e}")

def main():
    """Run all OAuth tests"""
    print("🧪 COMPREHENSIVE OAUTH TESTING")
    print("=" * 60)
    
    # Test configuration
    config_ok = test_oauth_configuration()
    
    # Test endpoints (if server is running)
    test_oauth_endpoints()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    if config_ok:
        print("✅ OAuth Configuration: READY")
        print("🎯 Next Steps:")
        print("1. Ensure server is running: python3 main.py")
        print("2. Visit: http://127.0.0.1:5001")
        print("3. Register/login to the application")
        print("4. Go to Setup page")
        print("5. Click 'Connect with Harvest OAuth'")
        print("6. Complete OAuth flow with your Harvest account")
    else:
        print("❌ OAuth Configuration: FAILED")
        print("🔧 Fix Required:")
        print("1. Check HARVEST_CLIENT_ID in .env")
        print("2. Check HARVEST_CLIENT_SECRET in .env") 
        print("3. Check HARVEST_REDIRECT_URI in .env")
        print("4. Ensure Harvest OAuth app is properly registered")

if __name__ == "__main__":
    main()
