"""
Google Calendar API integration service
Handles OAuth authentication and calendar event retrieval
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models import db, UserConfig


class GoogleCalendarService:
    """Service for interacting with Google Calendar API"""
    
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        self.redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/google/callback')
        self.client_id = os.environ.get('GOOGLE_CLIENT_ID')
        self.client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')

        # Cache for calendar labels to avoid repeated API calls
        self._labels_cache = None
        self._labels_cache_time = 0
        self._cache_duration = 300  # 5 minutes
        
        if not self.client_id or not self.client_secret:
            print("⚠️  Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")
            # Don't raise error during import, just warn
    
    def get_auth_url(self) -> str:
        """Generate Google OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return authorization_url
    
    def handle_callback(self, authorization_code: str) -> bool:
        """Handle OAuth callback and store credentials"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange authorization code for tokens
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Store credentials in database
            self._store_credentials(credentials)
            
            return True
            
        except Exception as e:
            print(f"Error handling OAuth callback: {e}")
            return False
    
    def _store_credentials(self, credentials: Credentials) -> None:
        """Store OAuth credentials in database"""
        try:
            # Get or create user config
            user_config = UserConfig.query.first()
            if not user_config:
                user_config = UserConfig()
                db.session.add(user_config)

            # Store credentials as JSON with all required fields
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri or 'https://oauth2.googleapis.com/token',
                'client_id': credentials.client_id or self.client_id,
                'client_secret': credentials.client_secret or self.client_secret,
                'scopes': credentials.scopes
            }

            # Ensure we have all required fields
            if not creds_dict['client_id']:
                creds_dict['client_id'] = self.client_id
            if not creds_dict['client_secret']:
                creds_dict['client_secret'] = self.client_secret
            if not creds_dict['token_uri']:
                creds_dict['token_uri'] = 'https://oauth2.googleapis.com/token'

            user_config.set_google_credentials(creds_dict)
            db.session.commit()
            print("Google credentials stored successfully")

        except Exception as e:
            print(f"Error storing credentials: {e}")
            db.session.rollback()

    def _store_credentials_for_user(self, credentials: Credentials, user_id: int) -> None:
        """Store OAuth credentials for a specific user"""
        try:
            # Get or create user config for this user
            user_config = UserConfig.query.filter_by(user_id=user_id).first()
            if not user_config:
                user_config = UserConfig(user_id=user_id)
                db.session.add(user_config)

            # Store credentials as JSON with all required fields
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri or 'https://oauth2.googleapis.com/token',
                'client_id': credentials.client_id or self.client_id,
                'client_secret': credentials.client_secret or self.client_secret,
                'scopes': credentials.scopes
            }

            # Ensure we have all required fields
            if not creds_dict['client_id']:
                creds_dict['client_id'] = self.client_id
            if not creds_dict['client_secret']:
                creds_dict['client_secret'] = self.client_secret
            if not creds_dict['token_uri']:
                creds_dict['token_uri'] = 'https://oauth2.googleapis.com/token'

            user_config.set_google_credentials(creds_dict)
            db.session.commit()
            print(f"Google credentials stored successfully for user {user_id}")

        except Exception as e:
            print(f"Error storing credentials for user {user_id}: {e}")
            db.session.rollback()

    def clear_credentials(self) -> None:
        """Clear stored credentials to force re-authentication"""
        try:
            user_config = UserConfig.query.first()
            if user_config:
                user_config.set_google_credentials(None)
                db.session.commit()
                print("Google credentials cleared. Re-authentication required.")
        except Exception as e:
            print(f"Error clearing credentials: {e}")
            db.session.rollback()
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Retrieve stored OAuth credentials for the current user"""
        try:
            from auth import get_current_user

            # Get current user from session
            user = get_current_user()
            if not user:
                return None

            # Get user's Google credentials from UserConfig
            user_config = UserConfig.query.filter_by(user_id=user.id).first()
            if not user_config:
                return None

            creds_dict = user_config.get_google_credentials()
            if not creds_dict:
                return None

            # Check if we have all required fields for token refresh
            required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
            missing_fields = [field for field in required_fields if not creds_dict.get(field)]

            if missing_fields:
                print(f"Missing credential fields: {missing_fields}. Re-authentication required.")
                return None

            credentials = Credentials(
                token=creds_dict.get('token'),
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict.get('token_uri'),
                client_id=creds_dict.get('client_id'),
                client_secret=creds_dict.get('client_secret'),
                scopes=creds_dict.get('scopes')
            )

            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                try:
                    print("Refreshing expired Google Calendar token...")
                    credentials.refresh(Request())
                    self._store_credentials_for_user(credentials, user.id)
                    print("Token refreshed successfully")
                except Exception as refresh_error:
                    print(f"Failed to refresh token: {refresh_error}")
                    return None

            return credentials

        except Exception as e:
            print(f"Error retrieving credentials: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Check if Google Calendar is connected and credentials are valid"""
        credentials = self._get_credentials()
        return credentials is not None and credentials.valid
    
    def get_calendar_events(self, week_start: datetime, calendar_id: str = 'primary') -> List[Dict]:
        """
        Fetch calendar events for a specific week
        
        Args:
            week_start: Start date of the week (Monday)
            calendar_id: Google Calendar ID (default: 'primary')
            
        Returns:
            List of calendar events with relevant information
        """
        credentials = self._get_credentials()
        if not credentials:
            raise ValueError("Google Calendar not connected. Please authenticate first.")
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate week end (Sunday)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            # Format dates for API (Google Calendar expects RFC3339 format with timezone)
            time_min = week_start.isoformat() + 'Z' if week_start.tzinfo is None else week_start.isoformat()
            time_max = week_end.isoformat() + 'Z' if week_end.tzinfo is None else week_end.isoformat()
            
            # Fetch events
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process and format events
            formatted_events = []
            for event in events:
                formatted_event = self._format_event(event)
                if formatted_event:
                    # Add label information like in get_events method
                    formatted_event['color_id'] = event.get('colorId')
                    formatted_event['extracted_label'] = self._extract_label_from_event(event)
                    formatted_events.append(formatted_event)

            return formatted_events
            
        except HttpError as error:
            print(f"Google Calendar API error: {error}")
            raise Exception(f"Failed to fetch calendar events: {error}")
    
    def _format_event(self, event: Dict) -> Optional[Dict]:
        """
        Format a Google Calendar event for our application

        Args:
            event: Raw event from Google Calendar API

        Returns:
            Formatted event dictionary or None if event should be skipped
        """
        # Skip cancelled events
        if event.get('status') == 'cancelled':
            print(f"Skipping cancelled event: {event.get('summary', 'Unknown')}")
            return None

        # Check user's attendance status early to skip declined events
        user_attendance_status = self._get_user_attendance_status(event)
        if user_attendance_status == 'declined':
            print(f"Skipping declined event: {event.get('summary', 'Unknown')}")
            return None

        # Handle different event types
        start = event.get('start', {})
        end = event.get('end', {})

        # Handle all-day events
        if 'dateTime' not in start or 'dateTime' not in end:
            # Check if it's an all-day event with 'date' field
            if 'date' in start and 'date' in end:
                # All-day event - assign default duration of 8 hours for work estimation
                start_time = datetime.fromisoformat(start['date'] + 'T09:00:00')
                end_time = datetime.fromisoformat(start['date'] + 'T17:00:00')
                duration = 8.0  # Default 8-hour workday for all-day events
                print(f"All-day event detected: {event.get('summary', 'Unknown')} - assigning 8h duration")
            else:
                # Event without proper time information - skip
                return None
        else:
            # Regular timed event
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))

            # Calculate duration in hours
            duration = (end_time - start_time).total_seconds() / 3600

            # Skip very short events (less than 5 minutes instead of 15)
            if duration < 0.083:  # 5 minutes = 0.083 hours
                print(f"Skipping very short event: {event.get('summary', 'Unknown')} ({duration:.2f}h)")
                return None
        
        # Detect if this is a recurring event
        is_recurring = False
        recurring_event_id = None
        recurrence_pattern = None

        # Check for recurring event indicators
        if 'recurringEventId' in event:
            is_recurring = True
            recurring_event_id = event['recurringEventId']
        elif 'recurrence' in event:
            is_recurring = True
            recurring_event_id = event.get('id')
            recurrence_pattern = self._parse_recurrence_pattern(event.get('recurrence', []))

        # Extract label and color information
        extracted_label = self._extract_label_from_event(event)
        color_id = event.get('colorId')

        # Google Calendar color mapping (matching your actual colors)
        label_colors = {
            'Finshape': '#7ae7bf',          # Sage (light green)
            'Osobní': '#dbadff',            # Grape (purple)
            'Grada': '#ff887c',             # Flamingo (light orange)
            'ČSAS Promise': '#fbd75b',      # Banana (yellow)
            'AI': '#ffb878',                # Tangerine (orange)
            'DP': '#e1e1e1',                # Graphite (dark gray)
            'ČSAS Kalendář': '#5484ed',     # Blueberry (blue)
            'Sales': '#51b749',             # Basil (green)
            'Buřinka': '#dc2127'            # Tomato (red)
        }

        label_color = label_colors.get(extracted_label, '#9fc6e7') if extracted_label else None

        return {
            'id': event.get('id'),
            'summary': event.get('summary', 'Untitled Event'),
            'description': event.get('description', ''),
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'duration': round(duration, 2),
            'location': event.get('location', ''),
            'attendees': [attendee.get('email') for attendee in event.get('attendees', [])],
            'creator': event.get('creator', {}).get('email', ''),
            'calendar_id': event.get('organizer', {}).get('email', 'primary'),
            'is_recurring': is_recurring,
            'recurring_event_id': recurring_event_id,
            'recurrence_pattern': recurrence_pattern,
            'attendance_status': user_attendance_status,
            'color_id': color_id,
            'extracted_label': extracted_label,
            'label_color': label_color
        }

    def _get_user_attendance_status(self, event: Dict) -> str:
        """
        Get the current user's attendance status for an event

        Args:
            event: Raw Google Calendar event

        Returns:
            Attendance status: 'accepted', 'declined', 'tentative', 'needsAction', or 'organizer'
        """
        try:
            # Get current user's email from credentials
            credentials = self._get_credentials()
            if not credentials:
                return 'unknown'

            # Build service to get user info
            from googleapiclient.discovery import build
            oauth2_service = build('oauth2', 'v2', credentials=credentials)
            user_info = oauth2_service.userinfo().get().execute()
            user_email = user_info.get('email', '').lower()

            # Check if user is the organizer
            organizer_email = event.get('organizer', {}).get('email', '').lower()
            if user_email == organizer_email:
                return 'organizer'

            # Check attendees list for user's response status
            attendees = event.get('attendees', [])
            for attendee in attendees:
                attendee_email = attendee.get('email', '').lower()
                if attendee_email == user_email:
                    return attendee.get('responseStatus', 'needsAction')

            # If user is not in attendees list but event exists in their calendar,
            # they're likely the organizer or it's accepted
            return 'accepted'

        except Exception as e:
            print(f"Error getting attendance status: {e}")
            return 'unknown'

    def _parse_recurrence_pattern(self, recurrence_rules: List[str]) -> str:
        """
        Parse Google Calendar recurrence rules into human-readable format

        Args:
            recurrence_rules: List of RRULE strings from Google Calendar

        Returns:
            Human-readable recurrence pattern description
        """
        if not recurrence_rules:
            return "Unknown pattern"

        try:
            # Parse the first RRULE (most common case)
            rrule = recurrence_rules[0]
            if not rrule.startswith('RRULE:'):
                return "Custom pattern"

            # Extract key components
            parts = rrule[6:].split(';')  # Remove 'RRULE:' prefix
            rule_dict = {}
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    rule_dict[key] = value

            freq = rule_dict.get('FREQ', '').lower()
            interval = int(rule_dict.get('INTERVAL', 1))
            byday = rule_dict.get('BYDAY', '')

            # Build human-readable description
            if freq == 'daily':
                if interval == 1:
                    return "Daily"
                else:
                    return f"Every {interval} days"
            elif freq == 'weekly':
                if interval == 1:
                    if byday:
                        days = self._format_weekdays(byday)
                        return f"Weekly on {days}"
                    return "Weekly"
                else:
                    return f"Every {interval} weeks"
            elif freq == 'monthly':
                if interval == 1:
                    return "Monthly"
                else:
                    return f"Every {interval} months"
            elif freq == 'yearly':
                return "Yearly"
            else:
                return "Custom pattern"

        except Exception:
            return "Custom pattern"

    def _format_weekdays(self, byday: str) -> str:
        """Format BYDAY values into readable weekday names"""
        day_map = {
            'MO': 'Monday', 'TU': 'Tuesday', 'WE': 'Wednesday',
            'TH': 'Thursday', 'FR': 'Friday', 'SA': 'Saturday', 'SU': 'Sunday'
        }

        days = byday.split(',')
        formatted_days = []
        for day in days:
            # Remove any numeric prefixes (e.g., '1MO' -> 'MO')
            clean_day = ''.join(c for c in day if c.isalpha())
            if clean_day in day_map:
                formatted_days.append(day_map[clean_day])

        if len(formatted_days) == 1:
            return formatted_days[0]
        elif len(formatted_days) == 2:
            return f"{formatted_days[0]} and {formatted_days[1]}"
        else:
            return ", ".join(formatted_days[:-1]) + f", and {formatted_days[-1]}"

    def get_user_info(self) -> Optional[Dict]:
        """Get basic user information from Google"""
        credentials = self._get_credentials()
        if not credentials:
            return None
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get primary calendar info which includes user email
            calendar = service.calendars().get(calendarId='primary').execute()
            
            return {
                'email': calendar.get('id'),
                'name': calendar.get('summary', 'Unknown User')
            }
            
        except HttpError as error:
            print(f"Error getting user info: {error}")
            return None

    def get_calendar_event_labels(self, weeks_to_analyze: int = 12, min_frequency: int = 2) -> List[Dict]:
        """
        Get actual Google Calendar labels (colored tags) and analyze their usage
        OPTIMIZED VERSION with CACHING - Single API call + 5-minute cache

        Args:
            weeks_to_analyze: Number of recent weeks to analyze for usage stats
            min_frequency: Minimum frequency for a label to be included

        Returns:
            List of label dictionaries with usage statistics
        """
        try:
            if not self.is_connected():
                return []

            # Check cache first
            current_time = time.time()
            if (self._labels_cache is not None and
                current_time - self._labels_cache_time < self._cache_duration):
                print(f"🚀 CACHE HIT: Returning cached calendar labels (age: {int(current_time - self._labels_cache_time)}s)")
                return self._labels_cache

            print(f"🔄 CACHE MISS: Fetching fresh calendar labels...")

            # Get predefined labels first (these are instant)
            predefined_labels = self._get_predefined_labels()

            # Get all events in ONE API call instead of multiple calls
            all_events = self._get_calendar_events_optimized(weeks_to_analyze)

            # Skip slow extracted labels for now - just use predefined + events analysis
            print(f"🔍 OPTIMIZED: Analyzing {len(all_events)} events for label usage...")

            # Analyze label usage with predefined labels
            label_usage = self._analyze_label_usage(predefined_labels, all_events, min_frequency)

            # Cache the results
            self._labels_cache = label_usage
            self._labels_cache_time = current_time
            print(f"💾 CACHED: Stored {len(label_usage)} labels in cache")

            return label_usage

        except Exception as e:
            print(f"Error extracting calendar labels: {e}")
            return []

    def _get_predefined_labels(self) -> List[Dict]:
        """Get the predefined calendar labels that the user has shown"""
        predefined_labels = [
            {'text': 'DP', 'color': '#e1e1e1', 'description': 'Direct People related events'},
            {'text': 'ČSAS Promise', 'color': '#fbd75b', 'description': 'ČSAS Promise project'},
            {'text': 'Finshape', 'color': '#7ae7bf', 'description': 'Finshape related events'},
            {'text': 'ČSAS Kalendář', 'color': '#5484ed', 'description': 'ČSAS Calendar events'},
            {'text': 'AI', 'color': '#ffb878', 'description': 'AI related events'},
            {'text': 'Sales', 'color': '#51b749', 'description': 'Sales activities'},
            {'text': 'Osobní', 'color': '#dbadff', 'description': 'Personal events'},
            {'text': 'Buřinka', 'color': '#dc2127', 'description': 'Buřinka project events'},
            {'text': 'Grada', 'color': '#ff887c', 'description': 'Grada Medica project'}
        ]

        # Convert to the expected format
        labels = []
        for label_info in predefined_labels:
            labels.append({
                'id': f"predefined_{label_info['text'].lower().replace(' ', '_')}",
                'text': label_info['text'],
                'color': label_info['color'],
                'description': label_info['description'],
                'type': 'predefined_label',
                'calendar_id': 'primary',
                'calendar_name': 'Primary'
            })

        return labels

    def _get_calendar_labels(self) -> List[Dict]:
        """Get all available calendar labels from Google Calendar"""
        try:
            credentials = self._get_credentials()
            if not credentials:
                return []

            service = build('calendar', 'v3', credentials=credentials)

            # Get the primary calendar to access its color definitions
            calendar = service.calendars().get(calendarId='primary').execute()

            # Get calendar list to see if there are multiple calendars with labels
            calendar_list = service.calendarList().list().execute()

            labels = []

            # Check each calendar for labels/colors
            for cal_item in calendar_list.get('items', []):
                cal_id = cal_item['id']

                # Get events with colorId to identify labels
                try:
                    events_result = service.events().list(
                        calendarId=cal_id,
                        maxResults=100,
                        singleEvents=True,
                        orderBy='startTime',
                        timeMin=(datetime.now() - timedelta(weeks=12)).isoformat() + 'Z'
                    ).execute()

                    events = events_result.get('items', [])

                    # Extract unique colorIds and their associated text
                    color_labels = {}
                    for event in events:
                        color_id = event.get('colorId')
                        if color_id:
                            # Try to extract label text from event summary or description
                            summary = event.get('summary', '')

                            # Look for label patterns in the summary
                            label_text = self._extract_label_from_event(event)
                            if label_text:
                                if color_id not in color_labels:
                                    color_labels[color_id] = {
                                        'texts': set(),
                                        'color_id': color_id,
                                        'calendar_id': cal_id,
                                        'calendar_name': cal_item.get('summary', 'Primary')
                                    }
                                color_labels[color_id]['texts'].add(label_text)

                    # Convert to label format
                    for color_id, data in color_labels.items():
                        for text in data['texts']:
                            labels.append({
                                'id': f"{cal_id}_{color_id}_{text}",
                                'text': text,
                                'color_id': color_id,
                                'calendar_id': cal_id,
                                'calendar_name': data['calendar_name'],
                                'type': 'calendar_label'
                            })

                except Exception as e:
                    print(f"Error processing calendar {cal_id}: {e}")
                    continue

            return labels

        except Exception as e:
            print(f"Error getting calendar labels: {e}")
            return []

    def _extract_label_from_event(self, event: Dict) -> Optional[str]:
        """Extract label text from calendar event based on color ID only"""
        color_id = event.get('colorId')

        # Color ID to label mapping based on your Google Calendar setup
        # Only use color-based mapping to avoid false positives from event titles
        color_to_label = {
            '2': 'Finshape',         # Sage (light green)
            '3': 'Osobní',           # Grape (purple)
            '4': 'Grada',            # Flamingo (light orange)
            '5': 'ČSAS Promise',     # Banana (yellow)
            '6': 'AI',               # Tangerine (orange)
            '8': 'DP',               # Graphite (dark gray)
            '9': 'ČSAS Kalendář',    # Blueberry (blue)
            '10': 'Sales',           # Basil (green)
            '11': 'Buřinka'          # Tomato (red)
        }

        # Only use color-based mapping to ensure accuracy
        if color_id and color_id in color_to_label:
            return color_to_label[color_id]

    def _get_calendar_events_optimized(self, weeks_to_analyze: int) -> List[Dict]:
        """
        OPTIMIZED: Get all calendar events in a single API call instead of multiple calls
        This reduces API calls from N weeks to 1 call, dramatically improving performance
        """
        try:
            credentials = self._get_credentials()
            if not credentials:
                return []

            service = build('calendar', 'v3', credentials=credentials)

            # Calculate date range for all weeks at once
            today = datetime.now()
            start_date = today - timedelta(weeks=weeks_to_analyze, days=today.weekday())
            end_date = today + timedelta(days=1)  # Include today

            # Format dates for API
            time_min = start_date.isoformat() + 'Z' if start_date.tzinfo is None else start_date.isoformat()
            time_max = end_date.isoformat() + 'Z' if end_date.tzinfo is None else end_date.isoformat()

            print(f"🚀 OPTIMIZED: Fetching {weeks_to_analyze} weeks of events in ONE API call...")

            # Single API call for all events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=2500  # Increased limit to handle more events
            ).execute()

            events = events_result.get('items', [])
            print(f"✅ OPTIMIZED: Retrieved {len(events)} events in single call")

            # Process events to include label information
            processed_events = []
            for event in events:
                processed_event = self._format_event(event)
                if processed_event:
                    # Add label information
                    processed_event['color_id'] = event.get('colorId')
                    processed_event['extracted_label'] = self._extract_label_from_event(event)
                    processed_events.append(processed_event)

            return processed_events

        except Exception as e:
            print(f"❌ Error in optimized event fetch: {e}")
            # Fallback to old method if needed
            return self._get_calendar_events_fallback(weeks_to_analyze)

    def _get_calendar_events_fallback(self, weeks_to_analyze: int) -> List[Dict]:
        """Fallback method using multiple API calls (slower but more reliable)"""
        all_events = []
        today = datetime.now()

        for week_offset in range(weeks_to_analyze):
            week_start = today - timedelta(weeks=week_offset, days=today.weekday())
            week_events = self._get_calendar_events_with_labels(week_start)
            all_events.extend(week_events)

        return all_events

    def _get_calendar_events_with_labels(self, week_start: datetime) -> List[Dict]:
        """Get calendar events with label information"""
        try:
            credentials = self._get_credentials()
            if not credentials:
                return []

            service = build('calendar', 'v3', credentials=credentials)

            # Calculate week end
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            # Format dates for API
            time_min = week_start.isoformat() + 'Z' if week_start.tzinfo is None else week_start.isoformat()
            time_max = week_end.isoformat() + 'Z' if week_end.tzinfo is None else week_end.isoformat()

            # Fetch events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100
            ).execute()

            events = events_result.get('items', [])

            # Process events to include label information
            processed_events = []
            for event in events:
                processed_event = self._format_event(event)
                if processed_event:
                    # Add label information
                    processed_event['color_id'] = event.get('colorId')
                    processed_event['extracted_label'] = self._extract_label_from_event(event)
                    processed_events.append(processed_event)

            return processed_events

        except Exception as e:
            print(f"Error fetching events with labels: {e}")
            return []

    def _analyze_label_usage(self, calendar_labels: List[Dict], events: List[Dict], min_frequency: int) -> List[Dict]:
        """Analyze how frequently each label is used"""
        from collections import defaultdict, Counter

        # Create a mapping of predefined labels
        predefined_labels = {label['text']: label for label in calendar_labels if label.get('type') == 'predefined_label'}

        # Count label usage
        label_usage = defaultdict(lambda: {
            'frequency': 0,
            'total_hours': 0,
            'sample_events': [],
            'color_id': None,
            'color': None,
            'description': None,
            'calendar_name': 'Primary',
            'type': 'extracted_label'
        })

        # Initialize predefined labels with zero usage
        for label_text, label_info in predefined_labels.items():
            label_usage[label_text].update({
                'color': label_info.get('color'),
                'description': label_info.get('description'),
                'type': 'predefined_label'
            })

        # Count by extracted labels and color IDs
        for event in events:
            duration = event.get('duration', 0)
            summary = event.get('summary', '')

            # Count by extracted label text
            extracted_label = event.get('extracted_label')
            if extracted_label:
                label_usage[extracted_label]['frequency'] += 1
                label_usage[extracted_label]['total_hours'] += duration
                label_usage[extracted_label]['sample_events'].append(summary)
                label_usage[extracted_label]['color_id'] = event.get('color_id')

                # If this matches a predefined label, mark it as such
                if extracted_label in predefined_labels:
                    label_usage[extracted_label]['type'] = 'predefined_label'

        # Convert to result format
        results = []

        # First add predefined labels (even with 0 frequency)
        for label_text, usage in label_usage.items():
            if usage['type'] == 'predefined_label':
                confidence = 1.0 if usage['frequency'] == 0 else min(usage['frequency'] / 10, 1.0)
                results.append({
                    'label': label_text,
                    'type': 'predefined_label',
                    'frequency': usage['frequency'],
                    'confidence': confidence,
                    'total_hours': usage['total_hours'],
                    'avg_duration': usage['total_hours'] / usage['frequency'] if usage['frequency'] > 0 else 0,
                    'sample_events': usage['sample_events'][:3],
                    'color': usage['color'],
                    'description': usage['description'],
                    'color_id': usage['color_id'],
                    'calendar_name': usage['calendar_name']
                })

        # Then add extracted labels that meet frequency requirement
        for label_text, usage in label_usage.items():
            if usage['type'] == 'extracted_label' and usage['frequency'] >= min_frequency:
                results.append({
                    'label': label_text,
                    'type': 'extracted_label',
                    'frequency': usage['frequency'],
                    'confidence': min(usage['frequency'] / 10, 1.0),
                    'total_hours': usage['total_hours'],
                    'avg_duration': usage['total_hours'] / usage['frequency'] if usage['frequency'] > 0 else 0,
                    'sample_events': usage['sample_events'][:3],
                    'color_id': usage['color_id'],
                    'calendar_name': usage['calendar_name']
                })

        # Sort predefined labels first, then by frequency
        results.sort(key=lambda x: (x['type'] != 'predefined_label', -x['frequency']))

        return results

    def _get_event_title_patterns(self, weeks_to_analyze: int, min_frequency: int) -> List[Dict]:
        """Fallback method to extract patterns from event titles if no labels found"""
        try:
            # Get events from recent weeks
            all_events = []
            today = datetime.now()

            for week_offset in range(weeks_to_analyze):
                week_start = today - timedelta(weeks=week_offset, days=today.weekday())
                week_events = self.get_calendar_events(week_start)
                all_events.extend(week_events)

            if not all_events:
                return []

            # Extract and analyze labels
            label_data = self._analyze_event_labels(all_events, min_frequency)

            return label_data

        except Exception as e:
            print(f"Error extracting event title patterns: {e}")
            return []

    def _analyze_event_labels(self, events: List[Dict], min_frequency: int) -> List[Dict]:
        """
        Analyze calendar events to extract meaningful labels

        Args:
            events: List of calendar events
            min_frequency: Minimum frequency for inclusion

        Returns:
            List of label data dictionaries
        """
        from collections import defaultdict, Counter
        import re

        # Track different types of labels
        exact_titles = Counter()  # Exact event titles
        keyword_patterns = Counter()  # Extracted keyword patterns
        prefix_patterns = Counter()  # Common prefixes

        # Sample events for each pattern
        title_samples = defaultdict(list)
        keyword_samples = defaultdict(list)
        prefix_samples = defaultdict(list)

        for event in events:
            title = event.get('summary', '').strip()
            if not title or len(title) < 3:
                continue

            # Track exact titles
            exact_titles[title] += 1
            title_samples[title].append(event)

            # Extract keyword patterns
            keywords = self._extract_meaningful_keywords(title)
            if keywords:
                keyword_pattern = ' '.join(keywords[:3])  # Top 3 keywords
                keyword_patterns[keyword_pattern] += 1
                keyword_samples[keyword_pattern].append(event)

            # Extract common prefixes (for recurring meetings)
            prefix = self._extract_common_prefix(title)
            if prefix and len(prefix) >= 4:
                prefix_patterns[prefix] += 1
                prefix_samples[prefix].append(event)

        # Compile results
        labels = []

        # Add frequent exact titles
        for title, count in exact_titles.most_common():
            if count >= min_frequency:
                labels.append({
                    'label': title,
                    'type': 'exact_title',
                    'frequency': count,
                    'confidence': min(count / 10, 1.0),  # Higher confidence for more frequent
                    'sample_events': [e.get('summary') for e in title_samples[title][:3]],
                    'total_hours': sum(e.get('duration', 0) for e in title_samples[title]),
                    'avg_duration': sum(e.get('duration', 0) for e in title_samples[title]) / count
                })

        # Add keyword patterns (avoid duplicates with exact titles)
        existing_labels = {label['label'].lower() for label in labels}
        for pattern, count in keyword_patterns.most_common():
            if count >= min_frequency and pattern.lower() not in existing_labels:
                labels.append({
                    'label': pattern,
                    'type': 'keyword_pattern',
                    'frequency': count,
                    'confidence': min(count / 15, 0.8),  # Slightly lower confidence
                    'sample_events': [e.get('summary') for e in keyword_samples[pattern][:3]],
                    'total_hours': sum(e.get('duration', 0) for e in keyword_samples[pattern]),
                    'avg_duration': sum(e.get('duration', 0) for e in keyword_samples[pattern]) / count
                })

        # Add prefix patterns (for recurring meetings)
        for prefix, count in prefix_patterns.most_common():
            if count >= min_frequency and prefix.lower() not in existing_labels:
                labels.append({
                    'label': prefix,
                    'type': 'prefix_pattern',
                    'frequency': count,
                    'confidence': min(count / 12, 0.9),
                    'sample_events': [e.get('summary') for e in prefix_samples[prefix][:3]],
                    'total_hours': sum(e.get('duration', 0) for e in prefix_samples[prefix]),
                    'avg_duration': sum(e.get('duration', 0) for e in prefix_samples[prefix]) / count
                })

        # Sort by frequency and confidence
        labels.sort(key=lambda x: (x['frequency'], x['confidence']), reverse=True)

        # Limit to top 50 labels to avoid overwhelming the UI
        return labels[:50]

    def _extract_meaningful_keywords(self, title: str) -> List[str]:
        """Extract meaningful keywords from event title"""
        import re

        # Clean the title
        title = title.lower()
        title = re.sub(r'[^\w\s]', ' ', title)  # Remove punctuation
        words = title.split()

        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }

        # Business-relevant keywords get priority
        business_keywords = {
            'meeting', 'call', 'sync', 'standup', 'review', 'planning',
            'development', 'dev', 'design', 'research', 'analysis', 'testing',
            'client', 'customer', 'project', 'task', 'demo', 'presentation',
            'training', 'workshop', 'interview', 'onboarding', 'admin'
        }

        keywords = []
        for word in words:
            if (len(word) > 2 and
                word not in stop_words and
                not word.isdigit()):
                keywords.append(word)

        # Prioritize business keywords
        business_kw = [kw for kw in keywords if kw in business_keywords]
        other_kw = [kw for kw in keywords if kw not in business_keywords]

        return business_kw + other_kw

    def _extract_common_prefix(self, title: str) -> str:
        """Extract common prefix from event title (useful for recurring meetings)"""
        import re

        # Look for patterns like "Team Meeting", "Client Call", etc.
        # Extract up to the first colon, dash, or common separator
        separators = [':', '-', '|', '–', '—', '(', '[']

        for sep in separators:
            if sep in title:
                prefix = title.split(sep)[0].strip()
                if len(prefix) >= 4:
                    return prefix

        # If no separator, look for common patterns
        words = title.split()
        if len(words) >= 2:
            # Return first 2-3 words for potential patterns
            if len(words) >= 3:
                return ' '.join(words[:3])
            else:
                return ' '.join(words[:2])

        return title if len(title) >= 4 else ''
