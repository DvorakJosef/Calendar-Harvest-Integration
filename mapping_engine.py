"""
Mapping engine for matching calendar events to Harvest projects
"""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from collections import defaultdict

from models import ProjectMapping, ProcessingHistory, RecurringEventMapping
from pattern_recognition import PatternRecognitionEngine


class MappingEngine:
    """Engine for mapping calendar events to Harvest projects and tasks"""

    def __init__(self):
        self.mappings_cache = {}  # Cache per user
        self.cache_timestamp = {}
        self.pattern_engine = PatternRecognitionEngine()
    
    def get_mappings(self, user_id: int, force_refresh: bool = False) -> List[ProjectMapping]:
        """
        Get all active project mappings for a user, with caching

        Args:
            user_id: ID of the user
            force_refresh: Force refresh of the cache

        Returns:
            List of active ProjectMapping objects for the user
        """
        now = datetime.utcnow()

        # Use cache if it's less than 5 minutes old
        if (not force_refresh and
            user_id in self.mappings_cache and
            user_id in self.cache_timestamp and
            (now - self.cache_timestamp[user_id]).total_seconds() < 300):
            return self.mappings_cache[user_id]

        # Refresh cache
        self.mappings_cache[user_id] = ProjectMapping.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        self.cache_timestamp[user_id] = now

        return self.mappings_cache[user_id]
    
    def find_mapping_for_event(self, event: Dict, user_id: int) -> Optional[ProjectMapping]:
        """
        Find the best matching project mapping for a calendar event

        Args:
            event: Calendar event dictionary
            user_id: ID of the user

        Returns:
            ProjectMapping object if found, None otherwise
        """
        # First, check for permanent recurring event mappings
        if event.get('is_recurring') and event.get('recurring_event_id'):
            recurring_mapping = RecurringEventMapping.query.filter_by(
                user_id=user_id,
                recurring_event_id=event['recurring_event_id'],
                is_active=True
            ).first()

            if recurring_mapping:
                # Convert RecurringEventMapping to ProjectMapping-like object
                return self._create_project_mapping_from_recurring(recurring_mapping)

        mappings = self.get_mappings(user_id)

        if not mappings:
            return None

        # Then, try to match by extracted label (from color or other methods)
        extracted_label = event.get('extracted_label')
        if extracted_label:
            for mapping in mappings:
                if mapping.calendar_label.lower() == extracted_label.lower():
                    return mapping

        # Try enhanced pattern recognition
        patterns = self.pattern_engine.analyze_event_patterns(event)

        # Check for company/client pattern matches
        for company_pattern in patterns.get('company', []):
            company = company_pattern['company']
            for mapping in mappings:
                if company.lower() in mapping.calendar_label.lower():
                    return mapping

        # Then try traditional text-based matching
        event_summary = event.get('summary', '').lower()
        event_description = event.get('description', '').lower()
        event_location = event.get('location', '').lower()

        # Combine all searchable text
        searchable_text = f"{event_summary} {event_description} {event_location}".strip()

        if not searchable_text:
            return None

        # Find mappings that match
        matching_mappings = []

        for mapping in mappings:
            label = mapping.calendar_label.lower()

            # Check for exact matches first
            if label in searchable_text:
                # Calculate match score based on position and length
                score = self._calculate_match_score(searchable_text, label)
                matching_mappings.append((mapping, score))

        # Return the best match (highest score)
        if matching_mappings:
            matching_mappings.sort(key=lambda x: x[1], reverse=True)
            return matching_mappings[0][0]

        return None
    
    def _calculate_match_score(self, text: str, label: str) -> float:
        """
        Calculate a match score for a label in text
        Higher scores indicate better matches
        
        Args:
            text: The text to search in
            label: The label to search for
            
        Returns:
            Match score (higher is better)
        """
        score = 0.0
        
        # Base score for finding the label
        score += 1.0
        
        # Bonus for exact word matches
        words = text.split()
        label_words = label.split()
        
        for label_word in label_words:
            if label_word in words:
                score += 0.5
        
        # Bonus for label at the beginning of text
        if text.startswith(label):
            score += 0.3
        
        # Bonus for longer matches
        score += len(label) * 0.01
        
        # Penalty for partial word matches
        if not any(label_word in words for label_word in label_words):
            score -= 0.2
        
        return score

    def get_pattern_suggestions(self, event: Dict, available_projects: List[Dict]) -> List[Dict]:
        """
        Get pattern-based mapping suggestions for an event

        Args:
            event: Calendar event dictionary
            available_projects: List of available Harvest projects

        Returns:
            List of suggested mappings with confidence scores
        """
        return self.pattern_engine.suggest_mapping(event, available_projects)

    def learn_from_mapping(self, event: Dict, mapping: Dict):
        """
        Learn patterns from a successful mapping

        Args:
            event: Calendar event dictionary
            mapping: Applied mapping dictionary
        """
        self.pattern_engine.learn_from_mapping(event, mapping)

    def analyze_event_patterns(self, event: Dict) -> Dict:
        """
        Analyze patterns in a calendar event

        Args:
            event: Calendar event dictionary

        Returns:
            Dictionary with detected patterns and confidence scores
        """
        return self.pattern_engine.analyze_event_patterns(event)

    def process_events_for_week(self, events: List[Dict], week_start: date, user_id: int, show_all_events: bool = False) -> Dict:
        """
        Process a list of calendar events and generate timesheet entries

        Args:
            events: List of calendar event dictionaries
            week_start: Start date of the week being processed
            user_id: ID of the user
            show_all_events: If True, include already processed events in the preview

        Returns:
            Dictionary with processing results
        """
        results = {
            'total_events': len(events),
            'mapped_events': 0,
            'unmapped_events': 0,
            'unmapped_events_details': [],
            'timesheet_entries': [],
            'errors': [],
            'warnings': []
        }
        
        # Check for already processed events (unless show_all_events is True)
        processed_event_ids = set()
        if not show_all_events:
            processed_event_ids = self._get_processed_event_ids(week_start, user_id)

        for event in events:
            event_id = event.get('id')

            # Skip if already processed (unless show_all_events is True)
            if event_id in processed_event_ids:
                results['warnings'].append(f"Event '{event.get('summary')}' already processed")
                continue

            # Find mapping for this event
            mapping = self.find_mapping_for_event(event, user_id)
            
            if mapping:
                results['mapped_events'] += 1

                # Create timesheet entry (skip multi-day events)
                entry = self._create_timesheet_entry(event, mapping)
                if entry is not None:
                    results['timesheet_entries'].append(entry)

                    # Learn from successful mapping
                    mapping_dict = {
                        'harvest_project_name': mapping.harvest_project_name,
                        'harvest_task_name': mapping.harvest_task_name
                    }
                    self.learn_from_mapping(event, mapping_dict)

            else:
                results['unmapped_events'] += 1

                # Add pattern analysis to unmapped events
                event_with_patterns = event.copy()
                event_with_patterns['pattern_analysis'] = self.analyze_event_patterns(event)

                results['unmapped_events_details'].append(event_with_patterns)
                results['warnings'].append(f"No mapping found for event: '{event.get('summary')}'")

        # Apply parallel meeting logic and attendance filtering
        results = self._process_parallel_meetings_and_attendance(results, events, user_id)

        return results

    def _process_parallel_meetings_and_attendance(self, results: Dict, events: List[Dict], user_id: int) -> Dict:
        """
        Process parallel meetings and filter by attendance status

        Args:
            results: Current processing results
            events: List of all calendar events
            user_id: ID of the user

        Returns:
            Updated results with parallel meeting logic applied
        """
        # Filter out declined/rejected meetings
        filtered_entries = []
        for entry in results['timesheet_entries']:
            # Find the original event for this entry
            original_event = None
            for event in events:
                if event.get('id') == entry.get('event_id'):
                    original_event = event
                    break

            if original_event:
                attendance_status = original_event.get('attendance_status', 'accepted')
                # Skip declined meetings
                if attendance_status == 'declined':
                    results['warnings'].append(f"Skipped declined meeting: '{original_event.get('summary')}'")
                    continue

            filtered_entries.append(entry)

        # Update the entries list
        results['timesheet_entries'] = filtered_entries

        # Note: Multi-day events are now excluded in _create_timesheet_entry
        # Parallel meeting logic removed for simplicity

        return results















    def _create_project_mapping_from_recurring(self, recurring_mapping: RecurringEventMapping) -> ProjectMapping:
        """
        Create a ProjectMapping-like object from a RecurringEventMapping

        Args:
            recurring_mapping: RecurringEventMapping object

        Returns:
            ProjectMapping object with data from recurring mapping
        """
        # Create a temporary ProjectMapping object with the recurring mapping data
        mapping = ProjectMapping()
        mapping.id = f"recurring_{recurring_mapping.id}"
        mapping.calendar_label = recurring_mapping.event_summary
        mapping.harvest_project_id = recurring_mapping.harvest_project_id
        mapping.harvest_project_name = recurring_mapping.harvest_project_name
        mapping.harvest_task_id = recurring_mapping.harvest_task_id
        mapping.harvest_task_name = recurring_mapping.harvest_task_name
        mapping.is_active = recurring_mapping.is_active
        mapping.created_at = recurring_mapping.created_at
        mapping.updated_at = recurring_mapping.updated_at

        return mapping

    def _get_processed_event_ids(self, week_start: date, user_id: int) -> set:
        """Get set of event IDs that have already been processed for this week by this user"""
        processed = ProcessingHistory.query.filter_by(
            week_start_date=week_start,
            user_id=user_id
        ).all()
        return {p.calendar_event_id for p in processed}
    
    def _create_timesheet_entry(self, event: Dict, mapping: ProjectMapping) -> Dict:
        """
        Create a timesheet entry dictionary from an event and mapping

        Args:
            event: Calendar event dictionary
            mapping: ProjectMapping object

        Returns:
            Timesheet entry dictionary or None if event should be skipped
        """
        from datetime import datetime

        # Extract start and end times
        if isinstance(event['start'], str):
            event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        else:
            event_start = event['start']

        if isinstance(event['end'], str):
            event_end = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
        else:
            event_end = event['end']

        # Skip multi-day events (events that span more than one calendar day)
        if event_start.date() != event_end.date():
            return None

        event_date = event_start.date()

        # Calculate hours (round up to nearest 30 minutes)
        hours = event['duration']
        import math
        hours = math.ceil(hours * 2) / 2  # Round up to nearest 0.5

        # Create notes from event details
        notes = self._generate_notes(event)

        return {
            'event_id': event['id'],
            'event_summary': event['summary'],
            'spent_date': event_date.isoformat(),
            'project_id': mapping.harvest_project_id,
            'project_name': mapping.harvest_project_name,
            'task_id': mapping.harvest_task_id,
            'task_name': mapping.harvest_task_name,
            'hours': hours,
            'notes': notes,
            'mapping_label': mapping.calendar_label,
            'event_start': event['start'],
            'event_end': event['end']
        }
    
    def _generate_notes(self, event: Dict) -> str:
        """
        Generate notes for a timesheet entry based on calendar event
        
        Args:
            event: Calendar event dictionary
            
        Returns:
            Notes string
        """
        notes_parts = []
        
        # Add event summary
        summary = event.get('summary', '')
        if summary:
            notes_parts.append(summary)
        
        # Add description if different from summary
        description = event.get('description', '').strip()
        if description and description.lower() != summary.lower():
            # Limit description length
            if len(description) > 200:
                description = description[:197] + '...'
            notes_parts.append(description)
        
        # Add location if present
        location = event.get('location', '').strip()
        if location:
            notes_parts.append(f"Location: {location}")
        
        # Add attendees if present (limit to first few)
        attendees = event.get('attendees', [])
        if attendees:
            attendee_count = len(attendees)
            if attendee_count <= 3:
                attendee_list = ', '.join(attendees)
                notes_parts.append(f"Attendees: {attendee_list}")
            else:
                notes_parts.append(f"Meeting with {attendee_count} attendees")
        
        # Add time information
        from datetime import datetime
        if isinstance(event['start'], str):
            start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
        else:
            start_dt = event['start']
            end_dt = event['end']

        start_time = start_dt.strftime('%H:%M')
        end_time = end_dt.strftime('%H:%M')
        notes_parts.append(f"Time: {start_time}-{end_time}")
        
        return ' | '.join(notes_parts)
    
    def validate_mapping(self, calendar_label: str, harvest_project_id: int,
                        harvest_task_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Validate a project mapping before saving

        Args:
            calendar_label: Calendar event label to match
            harvest_project_id: Harvest project ID
            harvest_task_id: Harvest task ID
            user_id: ID of the user

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if label is not empty
        if not calendar_label or not calendar_label.strip():
            return False, "Calendar label cannot be empty"

        # Check if label is too short
        if len(calendar_label.strip()) < 2:
            return False, "Calendar label must be at least 2 characters long"

        # Check if mapping already exists for this user
        existing = ProjectMapping.query.filter_by(
            user_id=user_id,
            calendar_label=calendar_label.strip(),
            is_active=True
        ).first()
        
        if existing:
            return False, f"Mapping for label '{calendar_label}' already exists"
        
        # Check if project and task IDs are valid
        if not harvest_project_id or not harvest_task_id:
            return False, "Both project and task must be selected"
        
        return True, ""
    
    def create_mapping(self, calendar_label: str, harvest_project_id: int,
                      harvest_project_name: str, harvest_task_id: int,
                      harvest_task_name: str, user_id: int) -> Tuple[bool, str]:
        """
        Create a new project mapping

        Args:
            calendar_label: Calendar event label to match
            harvest_project_id: Harvest project ID
            harvest_project_name: Harvest project name
            harvest_task_id: Harvest task ID
            harvest_task_name: Harvest task name
            user_id: ID of the user

        Returns:
            Tuple of (success, message)
        """
        # Validate the mapping
        is_valid, error_message = self.validate_mapping(
            calendar_label, harvest_project_id, harvest_task_id, user_id
        )
        
        if not is_valid:
            return False, error_message
        
        try:
            # Create new mapping
            mapping = ProjectMapping(
                user_id=user_id,
                calendar_label=calendar_label.strip(),
                harvest_project_id=harvest_project_id,
                harvest_project_name=harvest_project_name,
                harvest_task_id=harvest_task_id,
                harvest_task_name=harvest_task_name
            )

            from models import db
            db.session.add(mapping)
            db.session.commit()

            # Clear cache for this user
            if user_id in self.mappings_cache:
                del self.mappings_cache[user_id]
            
            return True, "Mapping created successfully"
            
        except Exception as e:
            return False, f"Error creating mapping: {str(e)}"
