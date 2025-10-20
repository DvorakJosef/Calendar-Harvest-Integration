"""
Auto-suggestion engine for mapping calendar events to Harvest projects
Uses intelligent text analysis and pattern recognition
"""

import re
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import difflib

from models import ProjectMapping, ProcessingHistory
from google_calendar_service import GoogleCalendarService
from harvest_service import HarvestService


class SuggestionEngine:
    """Engine for automatically suggesting calendar-to-project mappings"""
    
    def __init__(self):
        self.google_service = GoogleCalendarService()
        self.harvest_service = HarvestService()
        
        # Common business keywords and their weights
        self.business_keywords = {
            'meeting': 2.0, 'call': 2.0, 'sync': 1.5, 'standup': 1.5,
            'review': 1.8, 'planning': 2.0, 'development': 2.5, 'dev': 2.5,
            'design': 2.0, 'research': 1.8, 'analysis': 1.8, 'testing': 2.0,
            'client': 2.5, 'customer': 2.5, 'project': 2.0, 'task': 1.5,
            'demo': 2.0, 'presentation': 1.8, 'training': 1.5, 'workshop': 1.8,
            'interview': 2.0, 'onboarding': 1.5, 'admin': 1.0, 'lunch': 0.5
        }
    
    def generate_suggestions(self, weeks_to_analyze: int = 4, user_id: int = None) -> List[Dict]:
        """
        Generate mapping suggestions based on calendar labels and Harvest projects

        Args:
            weeks_to_analyze: Number of recent weeks to analyze
            user_id: ID of the user to generate suggestions for

        Returns:
            List of suggestion dictionaries
        """
        try:
            # Get calendar labels with usage statistics for this user
            calendar_labels = self.google_service.get_calendar_event_labels(weeks_to_analyze, min_frequency=1, user_id=user_id)

            if not calendar_labels:
                return []

            # Get Harvest projects
            harvest_projects = self.harvest_service.get_projects()

            if not harvest_projects:
                return []

            # Filter for labels that have actual usage and aren't already mapped
            active_labels = [label for label in calendar_labels
                           if label['frequency'] > 0 and label['type'] == 'predefined_label']

            # Check which labels are already mapped
            existing_mappings = ProjectMapping.query.filter_by(is_active=True).all()
            mapped_labels = {mapping.calendar_label.lower() for mapping in existing_mappings}

            # Filter out already mapped labels
            unmapped_labels = [label for label in active_labels
                             if label['label'].lower() not in mapped_labels]



            # Generate suggestions by matching labels to projects
            suggestions = []

            for label in unmapped_labels:
                try:
                    best_matches = self._find_best_project_matches_for_label(label, harvest_projects)

                    for match in best_matches:
                        suggestion = {
                            'calendar_label': label['label'],
                            'harvest_project_id': match['project']['id'],
                            'harvest_project_name': match['project']['name'],
                            'harvest_task_id': match.get('task', {}).get('id') if match.get('task') else None,
                            'harvest_task_name': match.get('task', {}).get('name') if match.get('task') else 'General',
                            'harvest_client_name': match['project'].get('client', {}).get('name', 'No Client'),
                            'confidence': match['confidence'],
                            'reasoning': match['reasoning'],
                            'frequency': label['frequency'],
                            'total_hours': label['total_hours'],
                            'avg_duration': label['avg_duration'],
                            'sample_events': label['sample_events'][:3],
                            'label_color': label.get('color'),
                            'label_description': label.get('description')
                        }
                        suggestions.append(suggestion)
                except Exception as e:
                    print(f"Error processing label '{label.get('label', 'unknown')}': {e}")
                    continue

            # Add some manual high-confidence suggestions for perfect matches
            manual_suggestions = self._get_manual_suggestions(unmapped_labels, harvest_projects)
            suggestions.extend(manual_suggestions)

            # Sort by confidence and frequency
            suggestions.sort(key=lambda x: (x['confidence'], x['frequency']), reverse=True)

            # Limit to top suggestions to avoid overwhelming the user
            return suggestions[:10]

        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return []
    
    def _get_recent_calendar_events(self, weeks: int) -> List[Dict]:
        """Get calendar events from recent weeks"""
        try:
            if not self.google_service.is_connected():
                return []
            
            events = []
            today = datetime.now()
            
            for week_offset in range(weeks):
                week_start = today - timedelta(weeks=week_offset, days=today.weekday())
                week_events = self.google_service.get_calendar_events(week_start)
                events.extend(week_events)
            
            return events
            
        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            return []

    def _find_best_project_matches_for_label(self, label: Dict, harvest_projects: List[Dict]) -> List[Dict]:
        """
        Find the best Harvest project matches for a calendar label

        Args:
            label: Calendar label dictionary
            harvest_projects: List of Harvest projects

        Returns:
            List of match dictionaries with confidence scores
        """
        try:
            label_text = label['label'].lower()
            matches = []



            # Define label-to-project mapping rules
            label_mappings = {
                'dp': ['direct people', 'dp', 'people'],
                'čsas promise': ['čsas', 'promise', 'česká spořitelna'],
                'finshape': ['finshape', 'fin shape'],
                'čsas kalendář': ['čsas', 'kalendář', 'calendar', 'česká spořitelna'],
                'čsas ai research': ['čsas', 'ai research', 'research', 'česká spořitelna'],
                'ai': ['ai', 'artificial intelligence', 'machine learning', 'ml'],
                'elena': ['elena'],
                'sales': ['sales', 'prodej', 'obchod'],
                'osobní': ['personal', 'osobní', 'private'],
                'linet': ['linet'],
                'grada': ['grada', 'medica', 'grada medica']
            }

            # Get keywords for this label
            label_keywords = label_mappings.get(label_text, [label_text])

            # Score each project
            for project in harvest_projects:
                project_name = (project.get('name') or '').lower()
                client_name = (project.get('client', {}).get('name') or '').lower()
                project_code = (project.get('code') or '').lower()

                # Calculate match score
                score = 0
                reasoning_parts = []

                # Check for exact matches
                for keyword in label_keywords:
                    if keyword in project_name:
                        score += 1.0
                        reasoning_parts.append(f"'{keyword}' found in project name")
                    elif keyword in client_name:
                        score += 0.8
                        reasoning_parts.append(f"'{keyword}' found in client name")
                    elif keyword in project_code:
                        score += 0.6
                        reasoning_parts.append(f"'{keyword}' found in project code")

                # Special scoring for common patterns
                if label_text == 'ai' and any(term in project_name for term in ['ai', 'artificial', 'intelligence', 'machine', 'learning']):
                    score += 0.5
                    reasoning_parts.append("AI-related project detected")

                if label_text in ['čsas promise', 'čsas kalendář', 'čsas ai research'] and 'čsas' in client_name:
                    score += 0.7
                    reasoning_parts.append("ČSAS client match")

                # Normalize score to confidence (0-1)
                confidence = min(score / len(label_keywords), 1.0)

                if confidence > 0.2:  # Only include reasonable matches
                    # Get default task for the project
                    tasks = project.get('task_assignments', [])
                    default_task = tasks[0] if tasks else None

                    matches.append({
                        'project': project,
                        'task': default_task,
                        'confidence': confidence,
                        'reasoning': '; '.join(reasoning_parts) if reasoning_parts else f"Partial match with '{label_text}'"
                    })

            # Sort by confidence and return top matches
            matches.sort(key=lambda x: x['confidence'], reverse=True)
            return matches[:3]  # Return top 3 matches

        except Exception as e:
            print(f"Error finding project matches for label: {e}")
            return []

    def _get_manual_suggestions(self, unmapped_labels: List[Dict], harvest_projects: List[Dict]) -> List[Dict]:
        """
        Generate manual high-confidence suggestions for obvious matches
        """
        manual_suggestions = []

        # Create a mapping of project names to projects for easy lookup
        project_lookup = {}
        for project in harvest_projects:
            name = (project.get('name') or '').lower()
            if name:
                project_lookup[name] = project

        # Define obvious matches
        obvious_matches = {
            'ai': 'ai',
            'elena': 'elena',
            'sales': 'sales',
            'finshape': 'finshape'
        }

        for label in unmapped_labels:
            label_text = label['label'].lower()

            if label_text in obvious_matches:
                project_name = obvious_matches[label_text]
                if project_name in project_lookup:
                    project = project_lookup[project_name]

                    # Get default task
                    tasks = project.get('task_assignments', [])
                    default_task = tasks[0] if tasks else None

                    suggestion = {
                        'calendar_label': label['label'],
                        'harvest_project_id': project['id'],
                        'harvest_project_name': project['name'],
                        'harvest_task_id': default_task.get('id') if default_task else None,
                        'harvest_task_name': default_task.get('name') if default_task else 'General',
                        'harvest_client_name': project.get('client', {}).get('name', 'No Client'),
                        'confidence': 0.95,  # High confidence for exact matches
                        'reasoning': f"Exact match: '{label['label']}' → '{project['name']}'",
                        'frequency': label['frequency'],
                        'total_hours': label['total_hours'],
                        'avg_duration': label['avg_duration'],
                        'sample_events': label['sample_events'][:3],
                        'label_color': label.get('color'),
                        'label_description': label.get('description')
                    }
                    manual_suggestions.append(suggestion)


        return manual_suggestions
    
    def _extract_event_patterns(self, events: List[Dict]) -> List[Dict]:
        """Extract patterns from calendar events"""
        # Group events by similar titles/keywords
        pattern_groups = defaultdict(list)
        
        for event in events:
            # Extract meaningful keywords from event title
            keywords = self._extract_keywords(event['summary'])
            
            # Create a pattern key based on keywords
            pattern_key = self._create_pattern_key(keywords)
            
            if pattern_key:
                pattern_groups[pattern_key].append(event)
        
        # Convert to pattern objects with statistics
        patterns = []
        for pattern_key, group_events in pattern_groups.items():
            if len(group_events) >= 2:  # Only consider patterns that appear multiple times
                pattern = {
                    'label': pattern_key,
                    'count': len(group_events),
                    'sample_events': [e['summary'] for e in group_events],
                    'keywords': self._extract_keywords(pattern_key),
                    'total_hours': sum(e['duration'] for e in group_events),
                    'avg_duration': sum(e['duration'] for e in group_events) / len(group_events)
                }
                patterns.append(pattern)
        
        # Sort by frequency and total hours
        patterns.sort(key=lambda x: (x['count'], x['total_hours']), reverse=True)
        
        return patterns
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return []
        
        # Clean and normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        words = text.split()
        
        # Filter out common stop words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        keywords = []
        for word in words:
            if len(word) > 2 and word not in stop_words:
                keywords.append(word)
        
        return keywords
    
    def _create_pattern_key(self, keywords: List[str]) -> Optional[str]:
        """Create a pattern key from keywords"""
        if not keywords:
            return None
        
        # Score keywords based on business relevance
        scored_keywords = []
        for keyword in keywords:
            score = self.business_keywords.get(keyword, 1.0)
            scored_keywords.append((keyword, score))
        
        # Sort by score and take top keywords
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        top_keywords = [kw[0] for kw in scored_keywords[:3]]  # Take top 3 keywords
        
        if not top_keywords:
            return None
        
        return ' '.join(top_keywords)
    
    def _find_best_project_matches(self, pattern: Dict, projects: List[Dict]) -> List[Dict]:
        """Find best matching Harvest projects for a pattern"""
        matches = []
        
        for project in projects:
            # Calculate similarity scores
            name_similarity = self._calculate_text_similarity(
                pattern['label'], 
                project['name']
            )
            
            client_similarity = self._calculate_text_similarity(
                pattern['label'], 
                project.get('client_name', '')
            )
            
            keyword_similarity = self._calculate_keyword_similarity(
                pattern['keywords'],
                self._extract_keywords(f"{project['name']} {project.get('client_name', '')}")
            )
            
            # Combined confidence score
            confidence = max(name_similarity, client_similarity) * 0.6 + keyword_similarity * 0.4
            
            # Boost confidence for high-frequency patterns
            frequency_boost = min(pattern['count'] / 10, 0.2)  # Up to 20% boost
            confidence += frequency_boost
            
            # Get best task for this project
            best_task = self._find_best_task_for_project(pattern, project['id'])
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                pattern, project, confidence, name_similarity, 
                client_similarity, keyword_similarity
            )
            
            match = {
                'project': project,
                'task': best_task,
                'confidence': min(confidence, 1.0),  # Cap at 100%
                'reasoning': reasoning
            }
            matches.append(match)
        
        # Sort by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches[:3]  # Return top 3 matches
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        if not text1 or not text2:
            return 0.0
        
        # Use difflib for sequence matching
        similarity = difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        # Also check for substring matches
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        if text1_lower in text2_lower or text2_lower in text1_lower:
            similarity = max(similarity, 0.7)
        
        return similarity
    
    def _calculate_keyword_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """Calculate similarity between two sets of keywords"""
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if not union:
            return 0.0
        
        # Jaccard similarity
        jaccard = len(intersection) / len(union)
        
        # Boost for exact keyword matches
        exact_matches = len(intersection)
        exact_boost = min(exact_matches * 0.2, 0.4)
        
        return min(jaccard + exact_boost, 1.0)
    
    def _find_best_task_for_project(self, pattern: Dict, project_id: int) -> Optional[Dict]:
        """Find the best task within a project for the given pattern"""
        try:
            tasks = self.harvest_service.get_project_tasks(project_id)
            
            if not tasks:
                return None
            
            # Score tasks based on pattern keywords
            best_task = None
            best_score = 0
            
            for task in tasks:
                score = self._calculate_text_similarity(pattern['label'], task['name'])
                
                # Boost for common task types
                task_name_lower = task['name'].lower()
                if any(keyword in task_name_lower for keyword in pattern['keywords']):
                    score += 0.3
                
                if score > best_score:
                    best_score = score
                    best_task = task
            
            return best_task if best_score > 0.2 else tasks[0]  # Return best or first task
            
        except Exception:
            return None
    
    def _generate_reasoning(self, pattern: Dict, project: Dict, confidence: float,
                          name_sim: float, client_sim: float, keyword_sim: float) -> str:
        """Generate human-readable reasoning for the suggestion"""
        reasons = []
        
        if name_sim > 0.5:
            reasons.append(f"Project name '{project['name']}' matches pattern keywords")
        
        if client_sim > 0.5:
            reasons.append(f"Client name '{project.get('client_name', '')}' matches pattern")
        
        if keyword_sim > 0.4:
            reasons.append("Strong keyword overlap between events and project")
        
        if pattern['count'] > 5:
            reasons.append(f"High frequency pattern ({pattern['count']} events)")
        
        if pattern['total_hours'] > 10:
            reasons.append(f"Significant time investment ({pattern['total_hours']:.1f} hours)")
        
        if not reasons:
            reasons.append("Basic text similarity match")
        
        return "; ".join(reasons)
    
    def _deduplicate_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """Remove duplicate suggestions and keep the best ones"""
        seen_labels = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            label = suggestion['calendar_label']
            if label not in seen_labels:
                seen_labels.add(label)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions

    def learn_from_user_mappings(self, user_id: int) -> Dict:
        """
        Learn from existing user mappings to improve future suggestions

        Args:
            user_id: ID of the user to learn from

        Returns:
            Dictionary with learning insights
        """
        try:
            # Get existing mappings for this user only
            existing_mappings = ProjectMapping.query.filter_by(user_id=user_id, is_active=True).all()

            if not existing_mappings:
                return {'insights': [], 'patterns': []}

            # Analyze patterns in user's existing mappings
            label_patterns = []
            project_preferences = defaultdict(int)
            keyword_project_associations = defaultdict(lambda: defaultdict(int))

            for mapping in existing_mappings:
                # Extract keywords from calendar labels
                keywords = self._extract_keywords(mapping.calendar_label)

                # Track project preferences
                project_preferences[mapping.harvest_project_id] += 1

                # Track keyword-project associations
                for keyword in keywords:
                    keyword_project_associations[keyword][mapping.harvest_project_id] += 1

                label_patterns.append({
                    'label': mapping.calendar_label,
                    'keywords': keywords,
                    'project_id': mapping.harvest_project_id,
                    'project_name': mapping.harvest_project_name
                })

            # Generate insights
            insights = []

            # Most used projects
            top_projects = sorted(project_preferences.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_projects:
                insights.append(f"Most frequently mapped projects: {', '.join([str(p[0]) for p in top_projects])}")

            # Strong keyword associations
            strong_associations = []
            for keyword, projects in keyword_project_associations.items():
                if len(projects) == 1 and list(projects.values())[0] > 1:
                    project_id = list(projects.keys())[0]
                    strong_associations.append((keyword, project_id))

            if strong_associations:
                insights.append(f"Strong keyword-project associations found for {len(strong_associations)} keywords")

            return {
                'insights': insights,
                'patterns': label_patterns,
                'keyword_associations': dict(keyword_project_associations),
                'project_preferences': dict(project_preferences)
            }

        except Exception as e:
            print(f"Error learning from user mappings: {e}")
            return {'insights': [], 'patterns': []}

    def get_enhanced_suggestions(self, weeks_to_analyze: int = 4, user_id: int = None) -> List[Dict]:
        """
        Generate enhanced suggestions using machine learning from user patterns

        Args:
            weeks_to_analyze: Number of recent weeks to analyze
            user_id: ID of the user to generate suggestions for

        Returns:
            List of enhanced suggestion dictionaries
        """
        try:
            # Get base suggestions
            base_suggestions = self.generate_suggestions(weeks_to_analyze, user_id=user_id)

            # Learn from existing user mappings for this user only
            learning_data = self.learn_from_user_mappings(user_id)

            # Enhance suggestions with learned patterns
            enhanced_suggestions = []

            for suggestion in base_suggestions:
                enhanced_suggestion = suggestion.copy()

                # Boost confidence based on user patterns
                confidence_boost = 0

                # Check if this label has been used before with this project
                label_text = suggestion['calendar_label'].lower()
                project_id = suggestion['harvest_project_id']

                # Boost for frequently used projects
                project_frequency = learning_data.get('project_preferences', {}).get(
                    project_id, 0
                )
                if project_frequency > 0:
                    confidence_boost += min(project_frequency * 0.1, 0.2)

                # Check for similar label patterns in user's history
                for pattern in learning_data.get('patterns', []):
                    pattern_label = pattern.get('label', '').lower()
                    if pattern_label == label_text and pattern.get('project_id') == project_id:
                        confidence_boost += 0.3  # Strong boost for exact label-project match
                        break
                    elif any(word in pattern_label for word in label_text.split()):
                        confidence_boost += 0.1  # Smaller boost for partial matches

                # Apply confidence boost
                enhanced_suggestion['confidence'] = min(
                    suggestion['confidence'] + confidence_boost, 1.0
                )

                # Add learning-based reasoning
                if confidence_boost > 0:
                    learning_reasons = []
                    if project_frequency > 0:
                        learning_reasons.append(f"frequently used project ({project_frequency} existing mappings)")

                    if learning_reasons:
                        enhanced_suggestion['reasoning'] += f"; {'; '.join(learning_reasons)}"

                enhanced_suggestions.append(enhanced_suggestion)

            # Re-sort by enhanced confidence
            enhanced_suggestions.sort(key=lambda x: (x['confidence'], x['frequency']), reverse=True)

            return enhanced_suggestions

        except Exception as e:
            print(f"Error generating enhanced suggestions: {e}")
            # Fallback to base suggestions
            return self.generate_suggestions(weeks_to_analyze)

    def analyze_calendar_patterns(self, weeks_to_analyze: int = 8) -> Dict:
        """
        Analyze calendar patterns to provide insights about time allocation

        Args:
            weeks_to_analyze: Number of weeks to analyze

        Returns:
            Dictionary with calendar analysis insights
        """
        try:
            events = self._get_recent_calendar_events(weeks_to_analyze)

            if not events:
                return {'insights': [], 'patterns': {}}

            # Analyze patterns
            patterns = {
                'total_events': len(events),
                'total_hours': sum(e['duration'] for e in events),
                'avg_event_duration': sum(e['duration'] for e in events) / len(events),
                'events_by_day': defaultdict(int),
                'events_by_hour': defaultdict(int),
                'common_keywords': Counter(),
                'long_events': [],
                'recurring_patterns': []
            }

            for event in events:
                # Parse event start time
                if isinstance(event['start'], str):
                    start_time = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                else:
                    start_time = event['start']

                # Day of week analysis
                day_name = start_time.strftime('%A')
                patterns['events_by_day'][day_name] += 1

                # Hour of day analysis
                hour = start_time.hour
                patterns['events_by_hour'][hour] += 1

                # Keyword analysis
                keywords = self._extract_keywords(event['summary'])
                for keyword in keywords:
                    patterns['common_keywords'][keyword] += 1

                # Long events (>2 hours)
                if event['duration'] > 2:
                    patterns['long_events'].append({
                        'summary': event['summary'],
                        'duration': event['duration']
                    })

            # Generate insights
            insights = []

            # Busiest day
            if patterns['events_by_day']:
                busiest_day = max(patterns['events_by_day'].items(), key=lambda x: x[1])
                insights.append(f"Busiest day: {busiest_day[0]} ({busiest_day[1]} events)")

            # Peak hours
            if patterns['events_by_hour']:
                peak_hour = max(patterns['events_by_hour'].items(), key=lambda x: x[1])
                insights.append(f"Peak meeting hour: {peak_hour[0]}:00 ({peak_hour[1]} events)")

            # Most common keywords
            top_keywords = patterns['common_keywords'].most_common(5)
            if top_keywords:
                keyword_list = [f"{kw[0]} ({kw[1]})" for kw in top_keywords]
                insights.append(f"Most common keywords: {', '.join(keyword_list)}")

            # Time allocation
            avg_hours_per_week = patterns['total_hours'] / weeks_to_analyze
            insights.append(f"Average meeting time: {avg_hours_per_week:.1f} hours/week")

            return {
                'insights': insights,
                'patterns': patterns,
                'weeks_analyzed': weeks_to_analyze
            }

        except Exception as e:
            print(f"Error analyzing calendar patterns: {e}")
            return {'insights': [], 'patterns': {}}
