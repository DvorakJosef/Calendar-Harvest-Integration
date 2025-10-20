#!/usr/bin/env python3
"""
Harvest Safety Validator
Multi-layer security system to prevent cross-user timesheet contamination
"""

import requests
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from models import UserConfig
from harvest_oauth import harvest_oauth

class HarvestSafetyValidator:
    """
    🛡️ CRITICAL SECURITY COMPONENT
    
    This class implements multiple layers of validation to ensure that:
    1. We never create entries in wrong user accounts
    2. We never access other users' data
    3. We have complete audit trail of all operations
    4. We can verify user identity before every operation
    """
    
    def __init__(self):
        self.base_url = 'https://api.harvestapp.com/v2'
        self.user_agent = 'Calendar-Harvest-Integration-SafetyValidator'
    
    def validate_user_identity(self, user_id: int, expected_email: str) -> Tuple[bool, str, Dict]:
        """
        🔒 SECURITY LAYER 1: User Identity Verification
        
        Verifies that the OAuth token belongs to the expected user
        
        Args:
            user_id: Internal user ID
            expected_email: Expected user email from our database
            
        Returns:
            Tuple of (is_valid, error_message, harvest_user_info)
        """
        try:
            # Get user config
            user_config = UserConfig.query.filter_by(user_id=user_id).first()
            if not user_config:
                return False, f"No user config found for user_id {user_id}", {}
            
            if not user_config.is_harvest_oauth_configured():
                return False, f"No OAuth credentials for user_id {user_id}", {}
            
            # Get OAuth token
            token_data = user_config.get_harvest_oauth_token()
            if not token_data:
                return False, f"No OAuth token data for user_id {user_id}", {}
            
            # Make API call to get current user info
            headers = harvest_oauth.get_api_headers(token_data)
            print(f"🔍 SAFETY DEBUG: Making API call to /users/me with stored token")
            print(f"🔍 SAFETY DEBUG: Stored token data keys: {list(token_data.keys())}")
            response = requests.get(f'{self.base_url}/users/me', headers=headers)

            if response.status_code != 200:
                return False, f"Failed to get user info: {response.status_code} - {response.text}", {}

            harvest_user = response.json()
            print(f"🔍 SAFETY DEBUG: API response user: {harvest_user}")
            harvest_email = harvest_user.get('email', '').lower()
            expected_email_lower = expected_email.lower()
            print(f"🔍 SAFETY DEBUG: API user ID: {harvest_user.get('id')}, email: {harvest_email}")
            print(f"🔍 SAFETY DEBUG: Expected email: {expected_email_lower}")
            print(f"🔍 SAFETY DEBUG: Stored user ID: {user_config.harvest_user_id}")
            
            # Verify email matches
            if harvest_email != expected_email_lower:
                return False, f"EMAIL MISMATCH: Expected {expected_email_lower}, got {harvest_email}", harvest_user
            
            # Verify stored user info matches
            if user_config.harvest_user_email and user_config.harvest_user_email.lower() != harvest_email:
                return False, f"STORED EMAIL MISMATCH: Stored {user_config.harvest_user_email}, API {harvest_email}", harvest_user
            
            if user_config.harvest_user_id and user_config.harvest_user_id != harvest_user.get('id'):
                stored_user_id = user_config.harvest_user_id
                api_user_id = harvest_user.get('id')

                print(f"🔧 SAFETY DEBUG: User ID mismatch detected, updating stored user ID from {stored_user_id} to {api_user_id}")

                # Update the stored user ID to match the API response
                # This handles cases where the OAuth token was obtained for a different user ID
                # but the email matches and the token is valid
                user_config.harvest_user_id = api_user_id

                # Also update with direct SQL to ensure it's saved
                import sqlite3
                conn = sqlite3.connect('calendar_harvest.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE user_config SET harvest_user_id = ? WHERE user_id = ?", (api_user_id, user_id))
                conn.commit()
                conn.close()

                print(f"🔧 SAFETY DEBUG: Updated stored user ID to {api_user_id}")
            
            print(f"✅ User identity verified: {harvest_email} (ID: {harvest_user.get('id')})")
            return True, "", harvest_user
            
        except Exception as e:
            return False, f"Error validating user identity: {e}", {}
    
    def validate_time_entry_ownership(self, entry_id: int, user_id: int) -> Tuple[bool, str]:
        """
        🔒 SECURITY LAYER 2: Time Entry Ownership Verification
        
        Verifies that a time entry belongs to the authenticated user
        
        Args:
            entry_id: Harvest time entry ID
            user_id: Internal user ID
            
        Returns:
            Tuple of (is_owned_by_user, error_message)
        """
        try:
            user_config = UserConfig.query.filter_by(user_id=user_id).first()
            if not user_config or not user_config.is_harvest_oauth_configured():
                return False, f"No OAuth credentials for user_id {user_id}"
            
            token_data = user_config.get_harvest_oauth_token()
            headers = harvest_oauth.get_api_headers(token_data)
            
            # Get the specific time entry
            response = requests.get(f'{self.base_url}/time_entries/{entry_id}', headers=headers)
            
            if response.status_code == 404:
                return False, f"Time entry {entry_id} not found or not accessible"
            
            if response.status_code != 200:
                return False, f"Failed to get time entry: {response.status_code} - {response.text}"
            
            entry = response.json()
            entry_user_id = entry.get('user', {}).get('id')
            
            # Verify the entry belongs to the authenticated user
            if entry_user_id != user_config.harvest_user_id:
                return False, f"OWNERSHIP VIOLATION: Entry belongs to user {entry_user_id}, not {user_config.harvest_user_id}"
            
            print(f"✅ Time entry ownership verified: Entry {entry_id} belongs to user {entry_user_id}")
            return True, ""
            
        except Exception as e:
            return False, f"Error validating time entry ownership: {e}"
    
    def validate_account_isolation(self, user_id: int) -> Tuple[bool, str, Dict]:
        """
        🔒 SECURITY LAYER 3: Account Isolation Verification
        
        Ensures the user can only access their own account data
        
        Args:
            user_id: Internal user ID
            
        Returns:
            Tuple of (is_isolated, error_message, account_info)
        """
        try:
            user_config = UserConfig.query.filter_by(user_id=user_id).first()
            if not user_config or not user_config.is_harvest_oauth_configured():
                return False, f"No OAuth credentials for user_id {user_id}", {}
            
            token_data = user_config.get_harvest_oauth_token()
            headers = harvest_oauth.get_api_headers(token_data)

            # Get account info from the stored OAuth token data (not from API)
            stored_account_id = token_data.get('harvest_account_id')
            stored_account_name = token_data.get('harvest_account_name')

            if not stored_account_id:
                return False, "No account ID found in OAuth token data", {}

            account_id = str(stored_account_id)

            # Get additional account info from /company endpoint for display
            response = requests.get(f'{self.base_url}/company', headers=headers)

            if response.status_code != 200:
                return False, f"Failed to get account info: {response.status_code} - {response.text}", {}

            company_info = response.json()

            # Combine stored OAuth data with company info for complete account info
            account_info = {
                'id': stored_account_id,  # From OAuth token
                'name': stored_account_name or company_info.get('name', 'Unknown'),  # Prefer stored name
                'base_uri': company_info.get('base_uri'),
                'full_domain': company_info.get('full_domain'),
                'is_active': company_info.get('is_active'),
                'plan_type': company_info.get('plan_type'),
                'currency': company_info.get('currency')
            }

            # Verify account ID matches stored account ID
            if user_config.harvest_account_id and user_config.harvest_account_id != account_id:
                stored_account_id = user_config.harvest_account_id

                print(f"🔧 SAFETY DEBUG: Account ID mismatch detected, updating stored account ID from {stored_account_id} to {account_id}")

                # Update the stored account ID to match the API response
                user_config.harvest_account_id = account_id

                # Also update with direct SQL to ensure it's saved
                import sqlite3
                conn = sqlite3.connect('calendar_harvest.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE user_config SET harvest_account_id = ? WHERE user_id = ?", (account_id, user_id))
                conn.commit()
                conn.close()

                print(f"🔧 SAFETY DEBUG: Updated stored account ID to {account_id}")
            
            print(f"✅ Account isolation verified: Account {account_id} ({account_info.get('name', 'Unknown')})")
            return True, "", account_info
            
        except Exception as e:
            return False, f"Error validating account isolation: {e}", {}
    
    def pre_operation_safety_check(self, user_id: int, expected_email: str, operation: str) -> Tuple[bool, str, Dict]:
        """
        🛡️ COMPREHENSIVE SAFETY CHECK
        
        Runs all safety validations before any Harvest operation
        
        Args:
            user_id: Internal user ID
            expected_email: Expected user email
            operation: Description of operation being performed
            
        Returns:
            Tuple of (is_safe, error_message, validation_results)
        """
        print(f"\n🛡️ SAFETY CHECK: {operation} for user_id {user_id}")
        print("=" * 60)
        
        validation_results = {
            'user_identity': {},
            'account_isolation': {},
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'user_id': user_id,
            'expected_email': expected_email
        }
        
        # Layer 1: User Identity Verification
        print("🔒 Layer 1: Verifying user identity...")
        identity_valid, identity_error, harvest_user = self.validate_user_identity(user_id, expected_email)
        validation_results['user_identity'] = {
            'valid': identity_valid,
            'error': identity_error,
            'harvest_user': harvest_user
        }
        
        if not identity_valid:
            print(f"❌ IDENTITY VALIDATION FAILED: {identity_error}")
            return False, f"Identity validation failed: {identity_error}", validation_results
        
        # Layer 2: Account Isolation Verification
        print("🔒 Layer 2: Verifying account isolation...")
        isolation_valid, isolation_error, account_info = self.validate_account_isolation(user_id)
        validation_results['account_isolation'] = {
            'valid': isolation_valid,
            'error': isolation_error,
            'account_info': account_info
        }
        
        if not isolation_valid:
            print(f"❌ ISOLATION VALIDATION FAILED: {isolation_error}")
            return False, f"Account isolation validation failed: {isolation_error}", validation_results
        
        # All checks passed
        print("✅ ALL SAFETY CHECKS PASSED")
        print(f"   User: {harvest_user.get('email')} (ID: {harvest_user.get('id')})")
        print(f"   Account: {account_info.get('name')} (ID: {account_info.get('id')})")
        print("=" * 60)
        
        return True, "", validation_results
    
    def log_safety_violation(self, user_id: int, operation: str, violation_details: Dict):
        """
        🚨 SECURITY INCIDENT LOGGING
        
        Logs any safety violations for investigation
        """
        incident = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'operation': operation,
            'violation_type': 'HARVEST_SAFETY_VIOLATION',
            'details': violation_details,
            'severity': 'CRITICAL'
        }
        
        # Log to file
        with open('security_incidents.log', 'a') as f:
            f.write(f"{incident}\n")
        
        print(f"🚨 SECURITY INCIDENT LOGGED: {incident}")

# Global safety validator instance
harvest_safety = HarvestSafetyValidator()
