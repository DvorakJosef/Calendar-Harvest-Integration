#!/usr/bin/env python3
"""
Harvest OAuth 2.0 Service
Handles individual user authentication with Harvest using OAuth 2.0
"""

import os
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import requests
from requests_oauthlib import OAuth2Session
from urllib.parse import urlencode
from dotenv import load_dotenv
from secrets_manager import get_oauth_credentials

class HarvestOAuth:
    """
    Harvest OAuth 2.0 authentication service
    
    🔐 SECURITY BENEFITS:
    - Individual user authentication (no shared credentials)
    - Built-in user isolation (tokens tied to specific Harvest users)
    - Revocable access (users can revoke from Harvest account)
    - Complete audit trail (all actions tracked to specific users)
    - Time-limited tokens (automatic expiration and refresh)
    """
    
    def __init__(self):
        # Load environment variables with the same logic as main.py
        env = os.getenv('FLASK_ENV', 'development')
        env_file = f'.env.{env}'
        if os.path.exists(env_file):
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Load Harvest OAuth configuration from secrets manager
        oauth_creds = get_oauth_credentials()
        self.client_id = oauth_creds['harvest_client_id']
        self.client_secret = oauth_creds['harvest_client_secret']
        self.redirect_uri = oauth_creds['harvest_redirect_uri']

        # Harvest OAuth 2.0 endpoints
        self.authorization_base_url = 'https://id.getharvest.com/oauth2/authorize'
        self.token_url = 'https://id.getharvest.com/api/v2/oauth2/token'
        self.user_info_url = 'https://id.getharvest.com/api/v2/accounts'

        # Validate configuration
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            print("⚠️  Harvest OAuth not configured - some features will be unavailable")
        else:
            print(f"✅ Harvest OAuth configured with client_id: {self.client_id[:10]}...")
    
    def is_configured(self) -> bool:
        """Check if OAuth is properly configured"""
        return all([self.client_id, self.client_secret, self.redirect_uri])
    
    def get_authorization_url(self, user_id: int) -> Tuple[str, str]:
        """
        Get OAuth authorization URL for user to authenticate with Harvest
        
        Args:
            user_id: Application user ID (for state verification)
            
        Returns:
            Tuple of (authorization_url, state)
        """
        if not self.is_configured():
            raise ValueError("Harvest OAuth not configured")
        
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        
        # Store user_id in state for verification (simple approach for demo)
        # In production, you might want to store this in Redis or database
        state_data = f"{state}:{user_id}"
        
        # Create OAuth session
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            state=state_data
        )
        
        # Get authorization URL
        authorization_url, state = oauth.authorization_url(
            self.authorization_base_url,
            # Request specific scopes if needed
            # scope=['harvest:read', 'harvest:write']  # Harvest doesn't use scopes
        )
        
        print(f"🔐 Generated OAuth authorization URL for user {user_id}")
        return authorization_url, state_data
    
    def exchange_code_for_token(self, code: str, state: str) -> Tuple[Dict, int]:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from Harvest
            state: State parameter for verification
            
        Returns:
            Tuple of (token_data, user_id)
        """
        if not self.is_configured():
            raise ValueError("Harvest OAuth not configured")



        try:
            # Extract user_id from state
            state_parts = state.split(':')
            if len(state_parts) != 2:
                raise ValueError("Invalid state parameter")
            
            original_state, user_id = state_parts
            user_id = int(user_id)
            
            # Exchange code for token using direct HTTP request
            # This gives us more control over the request format
            token_request_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri
            }

            response = requests.post(
                self.token_url,
                data=token_request_data,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )

            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")

            token_data = response.json()
            
            # Get user information from Harvest
            harvest_user_info = self._get_harvest_user_info(token_data['access_token'])
            
            # Enhance token data with user info
            token_data.update({
                'harvest_user_id': harvest_user_info['user']['id'],
                'harvest_user_email': harvest_user_info['user']['email'],
                'harvest_account_id': harvest_user_info['accounts'][0]['id'],
                'harvest_account_name': harvest_user_info['accounts'][0]['name'],
                'obtained_at': datetime.utcnow().isoformat()
            })
            
            print(f"✅ Successfully obtained OAuth token for user {user_id}")
            print(f"   Harvest User: {harvest_user_info['user']['email']}")
            print(f"   Harvest Account: {harvest_user_info['accounts'][0]['name']}")
            
            return token_data, user_id
            
        except Exception as e:
            print(f"❌ Error exchanging code for token: {e}")
            raise
    
    def refresh_token(self, refresh_token: str) -> Dict:
        """
        Refresh expired access token
        
        Args:
            refresh_token: Refresh token from previous OAuth flow
            
        Returns:
            New token data
        """
        if not self.is_configured():
            raise ValueError("Harvest OAuth not configured")
        
        try:
            # Create OAuth session
            oauth = OAuth2Session(client_id=self.client_id)
            
            # Refresh token
            token_data = oauth.refresh_token(
                self.token_url,
                refresh_token=refresh_token,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Update timestamp
            token_data['obtained_at'] = datetime.utcnow().isoformat()
            
            print(f"✅ Successfully refreshed OAuth token")
            return token_data
            
        except Exception as e:
            print(f"❌ Error refreshing token: {e}")
            raise
    
    def _get_harvest_user_info(self, access_token: str) -> Dict:
        """
        Get Harvest user information using access token
        
        Args:
            access_token: OAuth access token
            
        Returns:
            Harvest user information
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'Calendar-Harvest Integration OAuth'
            }
            
            response = requests.get(self.user_info_url, headers=headers)
            response.raise_for_status()
            
            user_info = response.json()
            
            # Validate response structure
            if 'user' not in user_info or 'accounts' not in user_info:
                raise ValueError("Invalid user info response from Harvest")
            
            if not user_info['accounts']:
                raise ValueError("User has no Harvest accounts")
            
            return user_info
            
        except Exception as e:
            print(f"❌ Error getting Harvest user info: {e}")
            raise
    
    def validate_token(self, token_data: Dict) -> bool:
        """
        Validate if OAuth token is still valid
        
        Args:
            token_data: Token data dictionary
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            if not token_data or 'access_token' not in token_data:
                return False
            
            # Check if token has expiration info
            if 'expires_at' in token_data:
                expires_at = datetime.fromtimestamp(token_data['expires_at'])
                if datetime.utcnow() >= expires_at:
                    print("🔄 OAuth token has expired")
                    return False
            
            # Test token by making a simple API call
            headers = {
                'Authorization': f'Bearer {token_data["access_token"]}',
                'Harvest-Account-Id': str(token_data.get('harvest_account_id', '')),
                'User-Agent': 'Calendar-Harvest Integration OAuth'
            }
            
            # Test with a simple API call
            response = requests.get('https://api.harvestapp.com/v2/users/me', headers=headers)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                print("🔄 OAuth token is invalid or expired")
                return False
            else:
                print(f"⚠️  Unexpected response validating token: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error validating token: {e}")
            return False
    
    def revoke_token(self, token_data: Dict) -> bool:
        """
        Revoke OAuth token (logout user from Harvest)
        
        Args:
            token_data: Token data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: Harvest doesn't provide a token revocation endpoint
            # Users must revoke access from their Harvest account settings
            print("ℹ️  To revoke access, user must visit their Harvest account settings")
            print("   and remove authorization for 'Calendar-Harvest Integration'")
            return True
            
        except Exception as e:
            print(f"❌ Error revoking token: {e}")
            return False
    
    def get_api_headers(self, token_data: Dict) -> Dict[str, str]:
        """
        Get API headers for Harvest API calls using OAuth token
        
        Args:
            token_data: Token data dictionary
            
        Returns:
            Headers dictionary for API calls
        """
        if not token_data or 'access_token' not in token_data:
            raise ValueError("Invalid token data")
        
        return {
            'Authorization': f'Bearer {token_data["access_token"]}',
            'Harvest-Account-Id': str(token_data.get('harvest_account_id', '')),
            'User-Agent': 'Calendar-Harvest Integration OAuth',
            'Content-Type': 'application/json'
        }

# Global OAuth instance
harvest_oauth = HarvestOAuth()

if __name__ == "__main__":
    # Test OAuth configuration
    print("🔐 Testing Harvest OAuth Configuration...")
    
    if harvest_oauth.is_configured():
        print("✅ Harvest OAuth is properly configured")
        print(f"   Client ID: {harvest_oauth.client_id[:10]}...")
        print(f"   Redirect URI: {harvest_oauth.redirect_uri}")
    else:
        print("❌ Harvest OAuth is not configured")
        print("   Please set HARVEST_CLIENT_ID, HARVEST_CLIENT_SECRET, and HARVEST_REDIRECT_URI")
    
    print("\n🎯 Next steps:")
    print("1. Register OAuth application with Harvest")
    print("2. Update environment variables with OAuth credentials")
    print("3. Implement OAuth endpoints in main application")
    print("4. Update UserConfig model for OAuth tokens")
    print("5. Test OAuth flow with real Harvest account")
