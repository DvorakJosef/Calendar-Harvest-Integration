"""
Enhanced Pattern Recognition Engine for Calendar Events
Automatically detects company names, meeting types, and client patterns
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json

class PatternRecognitionEngine:
    """Advanced pattern recognition for calendar events"""
    
    def __init__(self):
        # Common company/client patterns
        self.company_patterns = {
            'čsas': ['čsas', 'csas', 'česká spořitelna', 'ceska sporitelna'],
            'finshape': ['finshape', 'fin shape'],
            'dp': ['dp', 'direct people', 'directpeople'],
            'grada': ['grada', 'grada medica'],
            'osobní': ['osobní', 'osobni', 'personal', 'private']
        }
        
        # Meeting type patterns
        self.meeting_types = {
            'standup': ['standup', 'stand-up', 'daily', 'scrum'],
            'review': ['review', 'retrospective', 'retro', 'demo'],
            'planning': ['planning', 'plan', 'sprint planning'],
            'meeting': ['meeting', 'call', 'discussion', 'sync'],
            'workshop': ['workshop', 'training', 'session'],
            'interview': ['interview', 'pohovor', 'recruitment'],
            'lunch': ['lunch', 'oběd', 'obed', 'jídlo'],
            'break': ['break', 'pauza', 'coffee', 'káva']
        }
        
        # Common project indicators
        self.project_indicators = {
            'development': ['dev', 'development', 'coding', 'programming'],
            'research': ['research', 'analysis', 'study', 'investigation'],
            'management': ['management', 'admin', 'coordination'],
            'sales': ['sales', 'business', 'commercial', 'client'],
            'marketing': ['marketing', 'promotion', 'campaign']
        }
        
        # Learned patterns cache
        self.learned_patterns = {}
        self.pattern_confidence = {}
    
    def analyze_event_patterns(self, event: Dict) -> Dict:
        """
        Analyze an event and extract all possible patterns

        Args:
            event: Calendar event dictionary

        Returns:
            Dictionary with detected patterns and confidence scores
        """
        try:
            # Validate input
            if not isinstance(event, dict):
                return self._get_empty_patterns()

            text = self._extract_searchable_text(event)

            patterns = {
                'company': self._detect_company_patterns(text),
                'meeting_type': self._detect_meeting_type(text),
                'project_type': self._detect_project_type(text),
                'attendees_pattern': self._analyze_attendees(event),
                'time_pattern': self._analyze_time_pattern(event),
                'location_pattern': self._analyze_location(event),
                'extracted_keywords': self._extract_keywords(text),
                'confidence_score': 0.0
            }

            # Calculate overall confidence
            patterns['confidence_score'] = self._calculate_confidence(patterns)

            return patterns

        except Exception as e:
            return self._get_empty_patterns()

    def _get_empty_patterns(self) -> Dict:
        """Return empty patterns structure"""
        return {
            'company': [],
            'meeting_type': [],
            'project_type': [],
            'attendees_pattern': {'count': 0, 'domains': [], 'pattern': 'no_attendees'},
            'time_pattern': {'pattern': 'unknown'},
            'location_pattern': {'pattern': 'no_location'},
            'extracted_keywords': [],
            'confidence_score': 0.0
        }
    
    def _extract_searchable_text(self, event: Dict) -> str:
        """Extract all searchable text from event"""
        try:
            if not isinstance(event, dict):
                return ""

            parts = []

            summary = event.get('summary')
            if summary and isinstance(summary, str):
                parts.append(summary)

            description = event.get('description')
            if description and isinstance(description, str):
                parts.append(description)

            location = event.get('location')
            if location and isinstance(location, str):
                parts.append(location)

            return ' '.join(parts).lower()

        except Exception as e:
            return ""
    
    def _detect_company_patterns(self, text: str) -> List[Dict]:
        """Detect company/client patterns in text"""
        detected = []
        
        for company, patterns in self.company_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    confidence = len(pattern) / len(text) * 2  # Longer matches = higher confidence
                    confidence = min(confidence, 1.0)
                    
                    detected.append({
                        'company': company,
                        'pattern': pattern,
                        'confidence': confidence,
                        'position': text.find(pattern)
                    })
        
        # Sort by confidence
        detected.sort(key=lambda x: x['confidence'], reverse=True)
        return detected
    
    def _detect_meeting_type(self, text: str) -> List[Dict]:
        """Detect meeting type patterns"""
        detected = []
        
        for meeting_type, patterns in self.meeting_types.items():
            for pattern in patterns:
                if pattern in text:
                    confidence = 0.8 if text.startswith(pattern) else 0.6
                    
                    detected.append({
                        'type': meeting_type,
                        'pattern': pattern,
                        'confidence': confidence,
                        'position': text.find(pattern)
                    })
        
        detected.sort(key=lambda x: x['confidence'], reverse=True)
        return detected
    
    def _detect_project_type(self, text: str) -> List[Dict]:
        """Detect project type indicators"""
        detected = []
        
        for project_type, patterns in self.project_indicators.items():
            for pattern in patterns:
                if pattern in text:
                    confidence = 0.7
                    
                    detected.append({
                        'type': project_type,
                        'pattern': pattern,
                        'confidence': confidence,
                        'position': text.find(pattern)
                    })
        
        detected.sort(key=lambda x: x['confidence'], reverse=True)
        return detected
    
    def _analyze_attendees(self, event: Dict) -> Dict:
        """Analyze attendee patterns"""
        attendees = event.get('attendees', [])

        if not attendees:
            return {'count': 0, 'domains': [], 'pattern': 'no_attendees'}

        domains = []
        for attendee in attendees:
            # Handle both string and dict formats for attendees
            if isinstance(attendee, dict):
                email = attendee.get('email', '')
            else:
                # Already formatted as email string
                email = attendee

            if '@' in email:
                domain = email.split('@')[1].lower()
                domains.append(domain)

        domain_counts = Counter(domains)

        return {
            'count': len(attendees),
            'domains': list(domain_counts.keys()),
            'primary_domain': domain_counts.most_common(1)[0][0] if domain_counts else None,
            'pattern': 'internal' if len(set(domains)) == 1 else 'mixed'
        }
    
    def _analyze_time_pattern(self, event: Dict) -> Dict:
        """Analyze time-based patterns"""
        start = event.get('start')
        end = event.get('end')

        if not start or not end:
            return {'pattern': 'unknown'}

        try:
            # Handle both string and dict formats for start/end times
            if isinstance(start, dict):
                # Google Calendar API format: {'dateTime': '2023-...'}
                start_str = start.get('dateTime', '')
                end_str = end.get('dateTime', '')
            else:
                # Already formatted as ISO string
                start_str = start
                end_str = end

            if not start_str or not end_str:
                return {'pattern': 'unknown'}

            # Parse datetime strings
            start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))

            duration = (end_dt - start_dt).total_seconds() / 3600  # hours
            hour = start_dt.hour

            # Classify time patterns
            if hour < 9:
                time_pattern = 'early_morning'
            elif hour < 12:
                time_pattern = 'morning'
            elif hour < 14:
                time_pattern = 'lunch_time'
            elif hour < 17:
                time_pattern = 'afternoon'
            else:
                time_pattern = 'evening'

            return {
                'pattern': time_pattern,
                'duration': duration,
                'start_hour': hour,
                'is_long': duration > 2,
                'is_short': duration < 0.5
            }

        except Exception as e:
            return {'pattern': 'unknown'}
    
    def _analyze_location(self, event: Dict) -> Dict:
        """Analyze location patterns"""
        location = event.get('location', '').lower()
        
        if not location:
            return {'pattern': 'no_location'}
        
        # Common location patterns
        if any(word in location for word in ['zoom', 'teams', 'meet', 'webex', 'skype']):
            return {'pattern': 'online', 'platform': location}
        elif any(word in location for word in ['office', 'kancelář', 'workplace']):
            return {'pattern': 'office', 'location': location}
        elif any(word in location for word in ['home', 'doma', 'remote']):
            return {'pattern': 'remote', 'location': location}
        else:
            return {'pattern': 'physical', 'location': location}
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common words
        stop_words = {
            'meeting', 'call', 'with', 'and', 'the', 'for', 'in', 'on', 'at', 'to',
            'schůze', 'hovor', 's', 'a', 'v', 'na', 'do', 'ze', 'pro'
        }
        
        # Extract words (3+ characters, not stop words)
        words = re.findall(r'\b\w{3,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Return most frequent keywords
        return list(Counter(keywords).keys())[:5]
    
    def _calculate_confidence(self, patterns: Dict) -> float:
        """Calculate overall confidence score for pattern detection"""
        confidence = 0.0
        
        # Company patterns contribute most
        if patterns['company']:
            confidence += patterns['company'][0]['confidence'] * 0.4
        
        # Meeting type patterns
        if patterns['meeting_type']:
            confidence += patterns['meeting_type'][0]['confidence'] * 0.3
        
        # Attendee patterns
        if patterns['attendees_pattern']['count'] > 1:
            confidence += 0.2
        
        # Time and location patterns
        if patterns['time_pattern']['pattern'] != 'unknown':
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def learn_from_mapping(self, event: Dict, mapping: Dict):
        """Learn patterns from successful mappings"""
        patterns = self.analyze_event_patterns(event)
        
        # Store learned association
        project_name = mapping.get('harvest_project_name', '').lower()
        
        if project_name not in self.learned_patterns:
            self.learned_patterns[project_name] = {
                'keywords': Counter(),
                'companies': Counter(),
                'meeting_types': Counter(),
                'time_patterns': Counter(),
                'total_mappings': 0
            }
        
        learned = self.learned_patterns[project_name]
        learned['total_mappings'] += 1
        
        # Learn from detected patterns
        for keyword in patterns['extracted_keywords']:
            learned['keywords'][keyword] += 1
        
        for company in patterns['company']:
            learned['companies'][company['company']] += 1
        
        for meeting_type in patterns['meeting_type']:
            learned['meeting_types'][meeting_type['type']] += 1
        
        learned['time_patterns'][patterns['time_pattern']['pattern']] += 1
    
    def suggest_mapping(self, event: Dict, available_projects: List[Dict]) -> List[Dict]:
        """Suggest mappings based on learned patterns"""
        patterns = self.analyze_event_patterns(event)
        suggestions = []
        
        for project in available_projects:
            project_name = project.get('name', '').lower()
            score = self._calculate_mapping_score(patterns, project_name)
            
            if score > 0.3:  # Minimum threshold
                suggestions.append({
                    'project': project,
                    'score': score,
                    'reasons': self._get_suggestion_reasons(patterns, project_name)
                })
        
        # Sort by score
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:3]  # Top 3 suggestions
    
    def _calculate_mapping_score(self, patterns: Dict, project_name: str) -> float:
        """Calculate mapping score for a project"""
        if project_name not in self.learned_patterns:
            return 0.0
        
        learned = self.learned_patterns[project_name]
        score = 0.0
        
        # Score based on keyword matches
        for keyword in patterns['extracted_keywords']:
            if keyword in learned['keywords']:
                frequency = learned['keywords'][keyword]
                score += (frequency / learned['total_mappings']) * 0.4
        
        # Score based on company matches
        for company in patterns['company']:
            if company['company'] in learned['companies']:
                frequency = learned['companies'][company['company']]
                score += (frequency / learned['total_mappings']) * 0.3
        
        # Score based on meeting type matches
        for meeting_type in patterns['meeting_type']:
            if meeting_type['type'] in learned['meeting_types']:
                frequency = learned['meeting_types'][meeting_type['type']]
                score += (frequency / learned['total_mappings']) * 0.2
        
        # Score based on time pattern matches
        time_pattern = patterns['time_pattern']['pattern']
        if time_pattern in learned['time_patterns']:
            frequency = learned['time_patterns'][time_pattern]
            score += (frequency / learned['total_mappings']) * 0.1
        
        return min(score, 1.0)
    
    def _get_suggestion_reasons(self, patterns: Dict, project_name: str) -> List[str]:
        """Get human-readable reasons for suggestion"""
        reasons = []
        
        if project_name not in self.learned_patterns:
            return reasons
        
        learned = self.learned_patterns[project_name]
        
        # Check keyword matches
        for keyword in patterns['extracted_keywords']:
            if keyword in learned['keywords'] and learned['keywords'][keyword] > 1:
                reasons.append(f"Contains keyword '{keyword}' (used {learned['keywords'][keyword]} times)")
        
        # Check company matches
        for company in patterns['company']:
            if company['company'] in learned['companies']:
                count = learned['companies'][company['company']]
                reasons.append(f"Related to {company['company']} (mapped {count} times)")
        
        return reasons[:3]  # Top 3 reasons
