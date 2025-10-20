"""
Guided Setup Wizard for Calendar-Harvest Integration
Provides onboarding flow with calendar analysis and quick mapping creation
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re

from google_calendar_service import GoogleCalendarService
from harvest_service import HarvestService
from pattern_recognition import PatternRecognitionEngine
from models import ProjectMapping, db

class SetupWizard:
    """Guided setup wizard for new users"""
    
    def __init__(self):
        self.pattern_engine = PatternRecognitionEngine()
    
    def analyze_user_calendar(self, user_id: int, weeks_to_analyze: int = 8) -> Dict:
        """
        Analyze user's calendar to detect patterns and suggest mappings
        
        Args:
            user_id: ID of the user
            weeks_to_analyze: Number of weeks to analyze
            
        Returns:
            Dictionary with analysis results and suggestions
        """
        try:
            calendar_service = GoogleCalendarService()
            
            if not calendar_service.is_connected():
                return {'success': False, 'error': 'Calendar not connected'}
            
            # Get events from recent weeks
            all_events = []
            today = datetime.now()

            for week_offset in range(weeks_to_analyze):
                week_start = today - timedelta(weeks=week_offset, days=today.weekday())
                week_events = calendar_service.get_calendar_events(week_start)

                if isinstance(week_events, list):
                    all_events.extend(week_events)
            
            if not all_events:
                return {
                    'success': True,
                    'total_events': 0,
                    'suggestions': [],
                    'patterns': {},
                    'message': 'No calendar events found in the analyzed period'
                }
            
            # Analyze patterns
            analysis = self._analyze_calendar_patterns(all_events)
            
            # Get Harvest projects for suggestions
            harvest_service = HarvestService()
            harvest_projects = harvest_service.get_projects()

            if not harvest_projects:
                return {'success': False, 'error': 'Failed to load Harvest projects'}

            # harvest_projects is already a list of projects
            
            # Generate mapping suggestions
            suggestions = self._generate_mapping_suggestions(analysis, harvest_projects)
            
            return {
                'success': True,
                'total_events': len(all_events),
                'analyzed_weeks': weeks_to_analyze,
                'patterns': analysis,
                'suggestions': suggestions,
                'harvest_projects': harvest_projects
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _analyze_calendar_patterns(self, events: List[Dict]) -> Dict:
        """Analyze patterns in calendar events"""
        patterns = {
            'event_summaries': Counter(),
            'keywords': Counter(),
            'companies': Counter(),
            'meeting_types': Counter(),
            'time_patterns': Counter(),
            'attendee_domains': Counter(),
            'locations': Counter(),
            'durations': [],
            'frequent_events': [],
            'suggested_labels': []
        }
        
        for event in events:
            try:
                # Validate event is a dictionary
                if not isinstance(event, dict):
                    continue

                # Analyze with pattern recognition engine
                event_patterns = self.pattern_engine.analyze_event_patterns(event)

                # Count event summaries
                summary = event.get('summary', '').strip()
                if summary:
                    patterns['event_summaries'][summary] += 1

                # Extract keywords
                keywords = event_patterns.get('extracted_keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        patterns['keywords'][keyword] += 1

                # Count companies
                companies = event_patterns.get('company', [])
                if isinstance(companies, list):
                    for company in companies:
                        if isinstance(company, dict) and 'company' in company:
                            patterns['companies'][company['company']] += 1

                # Count meeting types
                meeting_types = event_patterns.get('meeting_type', [])
                if isinstance(meeting_types, list):
                    for meeting_type in meeting_types:
                        if isinstance(meeting_type, dict) and 'type' in meeting_type:
                            patterns['meeting_types'][meeting_type['type']] += 1

                # Time patterns
                time_pattern_data = event_patterns.get('time_pattern', {})
                if isinstance(time_pattern_data, dict):
                    time_pattern = time_pattern_data.get('pattern', 'unknown')
                    patterns['time_patterns'][time_pattern] += 1

                    # Duration
                    duration = time_pattern_data.get('duration', 0)
                    if duration > 0:
                        patterns['durations'].append(duration)

                # Attendee domains
                attendees_pattern = event_patterns.get('attendees_pattern', {})
                if isinstance(attendees_pattern, dict) and attendees_pattern.get('primary_domain'):
                    patterns['attendee_domains'][attendees_pattern['primary_domain']] += 1

                # Locations
                location_pattern = event_patterns.get('location_pattern', {})
                if isinstance(location_pattern, dict) and location_pattern.get('pattern') != 'no_location':
                    patterns['locations'][location_pattern['pattern']] += 1

            except Exception as e:
                continue
        
        # Find frequent events (potential recurring patterns)
        frequent_events = []
        for summary, count in patterns['event_summaries'].most_common(10):
            if count >= 3:  # Appears at least 3 times
                frequent_events.append({
                    'summary': summary,
                    'frequency': count,
                    'suggested_label': self._suggest_label_from_summary(summary)
                })
        
        patterns['frequent_events'] = frequent_events
        
        # Generate suggested labels from analysis
        patterns['suggested_labels'] = self._generate_suggested_labels(patterns)
        
        return patterns
    
    def _suggest_label_from_summary(self, summary: str) -> str:
        """Suggest a label from event summary"""
        # Remove common meeting words
        words_to_remove = ['meeting', 'call', 'sync', 'standup', 'review', 'discussion']
        
        words = summary.lower().split()
        filtered_words = [word for word in words if word not in words_to_remove and len(word) > 2]
        
        if filtered_words:
            # Return first meaningful word, capitalized
            return filtered_words[0].capitalize()
        else:
            # Fallback to first word of original summary
            return summary.split()[0] if summary.split() else 'Event'
    
    def _generate_suggested_labels(self, patterns: Dict) -> List[Dict]:
        """Generate suggested labels from pattern analysis"""
        suggestions = []
        
        # From companies
        for company, count in patterns['companies'].most_common(5):
            if count >= 2:
                suggestions.append({
                    'label': company.upper(),
                    'reason': f'Company mentioned in {count} events',
                    'confidence': min(count / 10, 1.0),
                    'type': 'company'
                })
        
        # From keywords
        for keyword, count in patterns['keywords'].most_common(5):
            if count >= 3 and len(keyword) > 3:
                suggestions.append({
                    'label': keyword.capitalize(),
                    'reason': f'Keyword appears in {count} events',
                    'confidence': min(count / 15, 1.0),
                    'type': 'keyword'
                })
        
        # From meeting types
        for meeting_type, count in patterns['meeting_types'].most_common(3):
            if count >= 2:
                suggestions.append({
                    'label': meeting_type.replace('_', ' ').title(),
                    'reason': f'Meeting type appears {count} times',
                    'confidence': min(count / 8, 1.0),
                    'type': 'meeting_type'
                })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return suggestions[:8]  # Top 8 suggestions
    
    def _generate_mapping_suggestions(self, patterns: Dict, harvest_projects: List[Dict]) -> List[Dict]:
        """Generate mapping suggestions based on patterns and available projects"""
        suggestions = []
        
        # Create project name lookup
        project_lookup = {project['name'].lower(): project for project in harvest_projects}
        
        # Suggest mappings for frequent events
        for frequent_event in patterns['frequent_events']:
            summary = frequent_event['summary'].lower()
            suggested_label = frequent_event['suggested_label']
            
            # Try to match with project names
            best_match = None
            best_score = 0
            
            for project_name, project in project_lookup.items():
                # Calculate similarity score
                score = self._calculate_similarity_score(summary, project_name)
                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = project
            
            if best_match:
                suggestions.append({
                    'type': 'frequent_event',
                    'calendar_label': suggested_label,
                    'event_summary': frequent_event['summary'],
                    'frequency': frequent_event['frequency'],
                    'suggested_project': best_match,
                    'confidence': best_score,
                    'reason': f'Event appears {frequent_event["frequency"]} times, matches project "{best_match["name"]}"'
                })
        
        # Suggest mappings for company patterns
        for company, count in patterns['companies'].most_common(5):
            if count >= 2:
                # Look for projects that might match this company
                company_lower = company.lower()
                
                for project in harvest_projects:
                    project_name_lower = project['name'].lower()
                    if (company_lower in project_name_lower or 
                        any(word in project_name_lower for word in company_lower.split())):
                        
                        suggestions.append({
                            'type': 'company_pattern',
                            'calendar_label': company.upper(),
                            'suggested_project': project,
                            'frequency': count,
                            'confidence': 0.8,
                            'reason': f'Company "{company}" mentioned {count} times, matches project "{project["name"]}"'
                        })
                        break
        
        # Remove duplicates and sort by confidence
        seen_projects = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            project_id = suggestion['suggested_project']['id']
            if project_id not in seen_projects:
                seen_projects.add(project_id)
                unique_suggestions.append(suggestion)
        
        unique_suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return unique_suggestions[:6]  # Top 6 suggestions
    
    def _calculate_similarity_score(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two text strings"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def create_mappings_from_suggestions(self, suggestions: List[Dict], user_id: int) -> Dict:
        """Create mappings from approved suggestions"""
        results = {
            'total_suggestions': len(suggestions),
            'created': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            for suggestion in suggestions:
                if not suggestion.get('approved', False):
                    continue
                
                calendar_label = suggestion.get('calendar_label')
                project = suggestion.get('suggested_project')
                task_id = suggestion.get('selected_task_id')
                task_name = suggestion.get('selected_task_name')
                
                if not all([calendar_label, project, task_id, task_name]):
                    results['failed'] += 1
                    results['errors'].append(f'Missing data for suggestion: {calendar_label}')
                    continue
                
                # Check if mapping already exists
                existing = ProjectMapping.query.filter_by(
                    user_id=user_id,
                    calendar_label=calendar_label
                ).first()
                
                if existing:
                    # Update existing mapping
                    existing.harvest_project_id = project['id']
                    existing.harvest_project_name = project['name']
                    existing.harvest_task_id = task_id
                    existing.harvest_task_name = task_name
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new mapping
                    mapping = ProjectMapping(
                        user_id=user_id,
                        calendar_label=calendar_label,
                        harvest_project_id=project['id'],
                        harvest_project_name=project['name'],
                        harvest_task_id=task_id,
                        harvest_task_name=task_name
                    )
                    
                    db.session.add(mapping)
                
                results['created'] += 1
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            results['errors'].append(str(e))
        
        return results
    
    def get_onboarding_status(self, user_id: int) -> Dict:
        """Get onboarding status for a user"""
        try:
            # Check if user has any mappings
            mapping_count = ProjectMapping.query.filter_by(
                user_id=user_id,
                is_active=True
            ).count()
            
            # Check calendar connection
            calendar_service = GoogleCalendarService()
            calendar_connected = calendar_service.is_connected()
            
            # Check Harvest connection
            harvest_service = HarvestService()
            harvest_projects = harvest_service.get_projects()
            harvest_connected = len(harvest_projects) > 0
            
            return {
                'success': True,
                'calendar_connected': calendar_connected,
                'harvest_connected': harvest_connected,
                'mapping_count': mapping_count,
                'needs_setup': mapping_count == 0,
                'setup_complete': mapping_count > 0 and calendar_connected and harvest_connected
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
