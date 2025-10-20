"""
Harvest API integration service
Handles authentication and timesheet operations
"""

import requests
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import json

from models import db, UserConfig, User
from harvest_safety_validator import harvest_safety


class HarvestService:
    """Service for interacting with Harvest API"""

    def __init__(self):
        self.base_url = 'https://api.harvestapp.com/v2'
        self.user_agent = 'Calendar-Harvest-Integration (contact@example.com)'
        self.api_log = []  # Store API call logs for debugging

    def _log_api_call(self, method: str, url: str, request_data: dict = None, response_status: int = None, response_data: dict = None, error: str = None):
        """Log API call for debugging purposes"""
        from datetime import datetime

        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'HARVEST_REQUEST' if response_status is None else 'HARVEST_RESPONSE',
            'method': method,
            'url': url,
            'status': 'SENT' if response_status is None else ('SUCCESS' if 200 <= response_status < 300 else 'ERROR'),
            'status_code': response_status,
            'data': request_data if response_status is None else response_data,
            'error': error
        }

        self.api_log.append(log_entry)

    def get_api_log(self) -> List[Dict]:
        """Get the current API log"""
        return self.api_log.copy()

    def clear_api_log(self):
        """Clear the API log"""
        self.api_log = []

    def _get_headers(self, user_id: int = None) -> Dict[str, str]:
        """Get headers for Harvest API requests using OAuth only"""

        # Get OAuth headers
        oauth_headers = self._get_oauth_headers(user_id)
        if oauth_headers:
            return oauth_headers

        # No OAuth credentials available
        raise ValueError("Harvest OAuth credentials not configured. Please connect your Harvest account.")

    def _get_oauth_headers(self, user_id: int = None) -> Optional[Dict[str, str]]:
        """
        Get headers using OAuth 2.0 authentication

        Args:
            user_id: User ID for authentication

        Returns:
            Headers dictionary for API requests or None if OAuth not available
        """
        try:
            from models import UserConfig

            if user_id is None:
                from flask import session
                user_id = session.get('user_id')
                if not user_id:
                    return None

            user_config = UserConfig.query.filter_by(user_id=user_id).first()
            if not user_config or not user_config.is_harvest_oauth_configured():
                return None

            # Check if token is valid
            if not user_config.is_harvest_token_valid():
                # Try to refresh token
                if not self._refresh_oauth_token(user_config):
                    return None

            # Get token data
            token_data = user_config.get_harvest_oauth_token()
            if not token_data:
                return None

            # Return OAuth headers
            from harvest_oauth import harvest_oauth
            return harvest_oauth.get_api_headers(token_data)

        except Exception as e:
            print(f"Error getting OAuth headers: {e}")
            return None

    def _refresh_oauth_token(self, user_config) -> bool:
        """
        Refresh expired OAuth token

        Args:
            user_config: UserConfig instance

        Returns:
            True if refresh successful, False otherwise
        """
        try:
            from harvest_oauth import harvest_oauth
            from models import db

            if not user_config.harvest_refresh_token:
                print("❌ No refresh token available")
                return False

            # Refresh the token
            new_token_data = harvest_oauth.refresh_token(user_config.harvest_refresh_token)

            # Update user config
            user_config.set_harvest_oauth_token(new_token_data)
            db.session.commit()

            print(f"✅ Successfully refreshed OAuth token for user {user_config.user_id}")
            return True

        except Exception as e:
            print(f"❌ Error refreshing OAuth token: {e}")
            return False

    def is_connected(self, user_id: int = None) -> bool:
        """Check if Harvest is connected and OAuth credentials are valid for specific user"""
        try:
            from models import UserConfig

            if user_id is None:
                from flask import session
                user_id = session.get('user_id')
                if not user_id:
                    return False

            user_config = UserConfig.query.filter_by(user_id=user_id).first()
            if not user_config:
                return False

            # Check if user has OAuth credentials
            if not user_config.is_harvest_oauth_configured():
                return False

            # Test connection with OAuth credentials
            headers = self._get_headers(user_id=user_id)
            response = requests.get(f'{self.base_url}/users/me', headers=headers)
            return response.status_code == 200

        except Exception as e:
            print(f"Error checking Harvest connection: {e}")
            return False
    def get_projects(self, user_id: int = None) -> List[Dict]:
        """
        Fetch all active projects from Harvest

        Args:
            user_id: User ID for authentication (optional, will use session if not provided)

        Returns:
            List of project dictionaries
        """
        try:
            headers = self._get_headers(user_id=user_id)

            # First, let's fetch ALL projects (active and inactive) to debug the missing "Režie" project
            all_projects = []

            # Fetch active projects
            print("🔍 DEBUG: Fetching ACTIVE projects...")
            params_active = {
                'is_active': 'true',
                'page': 1,
                'per_page': 100
            }

            response_active = requests.get(f'{self.base_url}/projects', headers=headers, params=params_active)
            print(f"DEBUG: ACTIVE projects API URL: {self.base_url}/projects")
            print(f"DEBUG: ACTIVE projects API params: {params_active}")
            print(f"DEBUG: ACTIVE projects response status: {response_active.status_code}")

            if response_active.status_code == 200:
                data_active = response_active.json()
                active_projects = data_active.get('projects', [])
                print(f"DEBUG: Found {len(active_projects)} ACTIVE projects")

                for project in active_projects:
                    client = project.get('client', {})
                    project_name = project.get('name', 'Unknown')
                    client_name = client.get('name', 'Unknown')
                    print(f"DEBUG: ACTIVE Project '{project_name}' (Client: {client_name}) - Active: {project.get('is_active')}, Billable: {project.get('is_billable')}")

                    # Look specifically for Režie project
                    if 'režie' in project_name.lower() or 'rezie' in project_name.lower():
                        print(f"🎯 FOUND REŽIE PROJECT: '{project_name}' - Active: {project.get('is_active')}, Billable: {project.get('is_billable')}")

                all_projects.extend(active_projects)

            # Fetch inactive projects
            print("\n🔍 DEBUG: Fetching INACTIVE projects...")
            params_inactive = {
                'is_active': 'false',
                'page': 1,
                'per_page': 100
            }

            response_inactive = requests.get(f'{self.base_url}/projects', headers=headers, params=params_inactive)
            print(f"DEBUG: INACTIVE projects API URL: {self.base_url}/projects")
            print(f"DEBUG: INACTIVE projects API params: {params_inactive}")
            print(f"DEBUG: INACTIVE projects response status: {response_inactive.status_code}")

            if response_inactive.status_code == 200:
                data_inactive = response_inactive.json()
                inactive_projects = data_inactive.get('projects', [])
                print(f"DEBUG: Found {len(inactive_projects)} INACTIVE projects")

                for project in inactive_projects:
                    client = project.get('client', {})
                    project_name = project.get('name', 'Unknown')
                    client_name = client.get('name', 'Unknown')
                    print(f"DEBUG: INACTIVE Project '{project_name}' (Client: {client_name}) - Active: {project.get('is_active')}, Billable: {project.get('is_billable')}")

                    # Look specifically for Režie project
                    if 'režie' in project_name.lower() or 'rezie' in project_name.lower():
                        print(f"🎯 FOUND REŽIE PROJECT (INACTIVE): '{project_name}' - Active: {project.get('is_active')}, Billable: {project.get('is_billable')}")

                all_projects.extend(inactive_projects)

            # Process only active projects for return
            processed_projects = []
            print(f"\n🔍 DEBUG: Processing active projects from {len(all_projects)} total projects...")

            for project in all_projects:
                if project.get('is_active', False):  # Only include active projects
                    client = project.get('client', {})
                    processed_projects.append({
                        'id': project['id'],
                        'name': project['name'],
                        'code': project.get('code', ''),
                        'client_name': client.get('name', ''),
                        'client_id': client.get('id'),
                        'is_billable': project.get('is_billable', False),
                        'budget': project.get('budget'),
                        'budget_by': project.get('budget_by')
                    })

            print(f"DEBUG: Returning {len(processed_projects)} active projects")

            print(f"DEBUG: Found {len(processed_projects)} projects from Harvest API:")
            for project in processed_projects:
                print(f"  - {project['name']} (ID: {project['id']}) - Client: {project['client_name']}")

            return processed_projects

        except Exception as e:
            print(f"Error fetching projects: {e}")
            return []
    
    def get_project_tasks(self, project_id: int, user_id: int = None) -> List[Dict]:
        """
        Fetch tasks for a specific project

        Args:
            project_id: Harvest project ID
            user_id: User ID for authentication (optional, will use session if not provided)

        Returns:
            List of task dictionaries
        """
        try:
            headers = self._get_headers(user_id=user_id)
            response = requests.get(
                f'{self.base_url}/projects/{project_id}/task_assignments',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                tasks = []
                
                for assignment in data.get('task_assignments', []):
                    if assignment.get('is_active', False):
                        task = assignment.get('task', {})
                        tasks.append({
                            'id': task.get('id'),
                            'name': task.get('name'),
                            'is_billable': assignment.get('billable', False),
                            'hourly_rate': assignment.get('hourly_rate'),
                            'budget': assignment.get('budget')
                        })
                
                return tasks
            else:
                print(f"Error fetching tasks: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []
    
    def get_time_entries(self, start_date: date, end_date: date, user_id: int = None) -> List[Dict]:
        """
        Fetch existing time entries for a date range

        Args:
            start_date: Start date for the range
            end_date: End date for the range
            user_id: User ID for authentication (optional, will use session if not provided)

        Returns:
            List of time entry dictionaries
        """
        try:
            # Get user and their config to extract the Harvest user ID
            user = User.query.get(user_id) if user_id else current_user
            if not user:
                print(f"No user found for user_id {user_id}")
                return []

            # Get user config which contains Harvest credentials
            from models import UserConfig
            user_config = UserConfig.query.filter_by(user_id=user.id).first()
            if not user_config or not user_config.harvest_user_id:
                print(f"No Harvest user ID found for user {user_id}")
                return []

            harvest_user_id = user_config.harvest_user_id

            headers = self._get_headers(user_id=user_id)
            params = {
                'from': start_date.isoformat(),
                'to': end_date.isoformat(),
                'user_id': harvest_user_id  # CRITICAL: Filter by Harvest user ID
            }

            print(f"🔒 SECURITY: Filtering time entries for Harvest user ID {harvest_user_id} (app user {user_id})")
            
            response = requests.get(
                f'{self.base_url}/time_entries',
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                entries = []
                
                for entry in data.get('time_entries', []):
                    entries.append({
                        'id': entry['id'],
                        'spent_date': entry['spent_date'],
                        'hours': entry['hours'],
                        'notes': entry.get('notes', ''),
                        'project_id': entry.get('project', {}).get('id'),
                        'project_name': entry.get('project', {}).get('name'),
                        'task_id': entry.get('task', {}).get('id'),
                        'task_name': entry.get('task', {}).get('name'),
                        'is_locked': entry.get('is_locked', False),
                        'is_billed': entry.get('is_billed', False),
                        'is_running': entry.get('is_running', False)
                    })
                
                return entries
            else:
                print(f"Error fetching time entries: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error fetching time entries: {e}")
            return []
    
    def create_time_entry(self, project_id: int, task_id: int, spent_date: date,
                         hours: float, notes: str = '', force_overwrite: bool = False, user_id: int = None) -> tuple[Optional[Dict], Optional[str]]:
        """
        Create a new time entry in Harvest

        ⚠️  CRITICAL SECURITY REQUIREMENT ⚠️
        This method MUST ONLY create time entries for the specific user whose Harvest
        credentials are being used. Cross-user timesheet manipulation is STRICTLY PROHIBITED.
        All timesheet changes MUST be tied to the authenticated user's Harvest account ONLY.

        Args:
            project_id: Harvest project ID
            task_id: Harvest task ID
            spent_date: Date the time was spent
            hours: Number of hours to log
            notes: Optional notes for the time entry
            force_overwrite: If True, delete existing entries for same date/project/task
            user_id: User ID for authentication (REQUIRED - must match credential owner)

        Returns:
            Tuple of (Created time entry dictionary or None if failed, error message or None)
        """
        try:
            # 🔒 SECURITY CHECK 1: Verify user_id is provided
            if user_id is None:
                from flask import session
                user_id = session.get('user_id')
                if not user_id:
                    error_msg = "SECURITY VIOLATION: user_id is required for timesheet operations"
                    print(f"🚨 {error_msg}")
                    return None, error_msg

            # 🛡️ COMPREHENSIVE SAFETY CHECK: Multi-layer security validation
            user = User.query.get(user_id)
            if not user:
                error_msg = f"SECURITY VIOLATION: User {user_id} not found"
                print(f"🚨 {error_msg}")
                return None, error_msg

            operation = f"CREATE_TIME_ENTRY: {hours}h on {spent_date} for project {project_id}, task {task_id}"
            is_safe, safety_error, validation_results = harvest_safety.pre_operation_safety_check(
                user_id, user.email, operation
            )

            if not is_safe:
                error_msg = f"SAFETY VALIDATION FAILED: {safety_error}"
                print(f"🚨 {error_msg}")
                harvest_safety.log_safety_violation(user_id, operation, {
                    'error': safety_error,
                    'validation_results': validation_results,
                    'project_id': project_id,
                    'task_id': task_id,
                    'spent_date': spent_date.isoformat(),
                    'hours': hours
                })
                return None, error_msg

            # 📋 AUDIT LOG: Record validated timesheet creation attempt
            harvest_user = validation_results['user_identity']['harvest_user']
            print(f"🔍 AUDIT: Creating timesheet entry for user_id {user_id}")
            print(f"🔍 AUDIT: Harvest user: {harvest_user.get('email', 'unknown')} (ID: {harvest_user.get('id', 'unknown')})")
            print(f"🔍 AUDIT: Entry details - Project: {project_id}, Task: {task_id}, Date: {spent_date}, Hours: {hours}")

            headers = self._get_headers(user_id=user_id)

            # 🔄 IMPROVED DUPLICATE DETECTION: Only check for exact duplicates when force_overwrite is enabled
            # The application-level grouping already handles combining multiple events appropriately,
            # so we should allow multiple entries per project/task/date combination by default.
            # Only perform duplicate checking when explicitly requested via force_overwrite.

            existing_entry = None
            if force_overwrite:
                # Only check for existing entries when force_overwrite is requested
                existing_entries = self.get_time_entries(spent_date, spent_date, user_id=user_id)
                print(f"🔍 Force overwrite mode: Checking for existing entries on {spent_date} - found {len(existing_entries)} total entries")

                for entry in existing_entries:
                    print(f"   - Entry {entry['id']}: Project {entry['project_id']}, Task {entry['task_id']}, Hours: {entry['hours']}")
                    if (entry['project_id'] == project_id and
                        entry['task_id'] == task_id and
                        entry['spent_date'] == spent_date.isoformat()):
                        existing_entry = entry
                        print(f"   ✅ MATCH FOUND: Entry {entry['id']} matches project {project_id}, task {task_id}")
                        break

                if existing_entry:
                    # Delete the existing entry first (since force_overwrite is enabled)
                    print(f"Force overwrite: Deleting existing entry {existing_entry['id']} for {spent_date} (existing: {existing_entry['hours']}h, new: {hours}h)")
                    delete_success = self.delete_time_entry(existing_entry['id'], user_id=user_id)
                    if not delete_success:
                        error_msg = f"Failed to delete existing entry {existing_entry['id']}"
                        print(error_msg)
                        return None, error_msg
                else:
                    print(f"   ❌ No existing entry found for project {project_id}, task {task_id} on {spent_date}")
            else:
                # 🎯 DEFAULT MODE: Allow multiple entries per project/task/date combination
                # This enables multiple calendar events for the same project on the same day
                # (e.g., multiple Sales meetings, multiple AI Strategy sessions)
                print(f"🎯 Creating new entry for {spent_date} - Project: {project_id}, Task: {task_id}, Hours: {hours}h")
                print(f"   📝 Note: Multiple entries per project/task/date are allowed (application-level grouping handles combination)")

            # Create the time entry
            data = {
                'project_id': project_id,
                'task_id': task_id,
                'spent_date': spent_date.isoformat(),
                'hours': hours,
                'notes': notes
            }

            print(f"Creating time entry: {data}")

            # Log the API request
            self._log_api_call('POST', f'{self.base_url}/time_entries', request_data=data)

            response = requests.post(
                f'{self.base_url}/time_entries',
                headers=headers,
                json=data
            )
            print(f"Harvest API response: {response.status_code} - {response.text}")

            # Log the API response
            try:
                response_data = response.json() if response.status_code == 201 else {'error': response.text}
            except:
                response_data = {'error': response.text}

            self._log_api_call('POST', f'{self.base_url}/time_entries',
                             response_status=response.status_code,
                             response_data=response_data,
                             error=None if response.status_code == 201 else response.text)

            if response.status_code == 201:
                entry = response.json()
                result = {
                    'id': entry['id'],
                    'spent_date': entry['spent_date'],
                    'hours': entry['hours'],
                    'notes': entry.get('notes', ''),
                    'project_id': entry.get('project', {}).get('id'),
                    'project_name': entry.get('project', {}).get('name'),
                    'task_id': entry.get('task', {}).get('id'),
                    'task_name': entry.get('task', {}).get('name')
                }

                # ✅ AUDIT LOG: Record successful timesheet creation
                print(f"✅ AUDIT: Successfully created time entry ID {entry['id']} for user_id {user_id}")
                print(f"✅ AUDIT: Entry confirmed in Harvest account: {harvest_user.get('email', 'unknown')}")

                return result, None
            else:
                error_msg = f"Harvest API error {response.status_code}: {response.text}"
                print(f"Error creating time entry: {error_msg}")
                return None, error_msg

        except Exception as e:
            error_msg = f"Exception creating time entry: {str(e)}"
            print(error_msg)
            return None, error_msg

    def update_time_entry(self, entry_id: int, update_data: dict, user_id: int = None) -> dict:
        """
        Update an existing time entry in Harvest

        Args:
            entry_id: ID of the time entry to update
            update_data: Dictionary containing fields to update (hours, notes, etc.)
            user_id: User ID for authentication

        Returns:
            Updated time entry data or None if failed
        """
        try:
            # Get user credentials
            user = User.query.get(user_id) if user_id else current_user
            if not user or not user.harvest_access_token:
                print(f"No Harvest credentials found for user {user_id}")
                return None

            headers = {
                'Authorization': f'Bearer {user.harvest_access_token}',
                'Harvest-Account-Id': str(user.harvest_account_id),
                'Content-Type': 'application/json'
            }

            url = f"{self.base_url}/time_entries/{entry_id}"

            print(f"🔄 Updating time entry {entry_id} with data: {update_data}")

            response = requests.patch(url, headers=headers, json=update_data)

            if response.status_code == 200:
                updated_entry = response.json()
                print(f"✅ Successfully updated time entry {entry_id}")
                return updated_entry
            else:
                print(f"❌ Failed to update time entry {entry_id}: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Exception updating time entry {entry_id}: {str(e)}")
            return None

    def delete_time_entry(self, entry_id: int, user_id: int = None) -> bool:
        """
        Delete a time entry from Harvest

        ⚠️  CRITICAL SECURITY REQUIREMENT ⚠️
        This method MUST ONLY delete time entries belonging to the specific user whose
        Harvest credentials are being used. Cross-user timesheet manipulation is STRICTLY PROHIBITED.

        Args:
            entry_id: ID of the time entry to delete
            user_id: User ID for authentication (REQUIRED - must match credential owner)

        Returns:
            True if successful, False otherwise
        """
        try:
            # 🔒 SECURITY CHECK: Verify user_id is provided
            if user_id is None:
                from flask import session
                user_id = session.get('user_id')
                if not user_id:
                    print("🚨 SECURITY VIOLATION: user_id is required for timesheet deletion")
                    return False

            # 🛡️ COMPREHENSIVE SAFETY CHECK: Multi-layer security validation
            user = User.query.get(user_id)
            if not user:
                print(f"🚨 SECURITY VIOLATION: User {user_id} not found")
                return False

            operation = f"DELETE_TIME_ENTRY: Entry ID {entry_id}"
            is_safe, safety_error, validation_results = harvest_safety.pre_operation_safety_check(
                user_id, user.email, operation
            )

            if not is_safe:
                print(f"🚨 SAFETY VALIDATION FAILED: {safety_error}")
                harvest_safety.log_safety_violation(user_id, operation, {
                    'error': safety_error,
                    'validation_results': validation_results,
                    'entry_id': entry_id
                })
                return False

            # 🔒 OWNERSHIP VERIFICATION: Ensure entry belongs to user
            ownership_valid, ownership_error = harvest_safety.validate_time_entry_ownership(entry_id, user_id)
            if not ownership_valid:
                print(f"🚨 OWNERSHIP VIOLATION: {ownership_error}")
                harvest_safety.log_safety_violation(user_id, operation, {
                    'error': ownership_error,
                    'entry_id': entry_id,
                    'violation_type': 'OWNERSHIP_VIOLATION'
                })
                return False

            # 📋 AUDIT LOG: Record validated deletion attempt
            print(f"🔍 AUDIT: Attempting to delete time entry ID {entry_id} for user_id {user_id}")

            headers = self._get_headers(user_id=user_id)

            response = requests.delete(
                f'{self.base_url}/time_entries/{entry_id}',
                headers=headers
            )

            if response.status_code == 200:
                # ✅ AUDIT LOG: Record successful deletion
                print(f"✅ AUDIT: Successfully deleted time entry {entry_id} for user_id {user_id}")
                return True
            else:
                print(f"❌ AUDIT: Failed to delete time entry {entry_id} for user_id {user_id}: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ AUDIT: Error deleting time entry {entry_id} for user_id {user_id}: {e}")
            return False

    def get_user_info(self) -> Optional[Dict]:
        """Get current user information from Harvest"""
        try:
            headers = self._get_headers()
            response = requests.get(f'{self.base_url}/users/me', headers=headers)
            
            if response.status_code == 200:
                user = response.json()
                return {
                    'id': user['id'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email': user['email'],
                    'is_admin': user.get('is_admin', False),
                    'is_project_manager': user.get('is_project_manager', False)
                }
            else:
                return None
                
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
