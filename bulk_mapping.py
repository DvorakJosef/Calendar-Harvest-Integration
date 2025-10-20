"""
Bulk Mapping Tools for Calendar-Harvest Integration
Provides bulk assignment, pattern-based rules, and import/export functionality
"""

import json
import re
from typing import List, Dict, Optional, Set
from datetime import datetime
from models import ProjectMapping, db

class BulkMappingService:
    """Service for bulk mapping operations"""
    
    def __init__(self):
        self.pattern_rules = []
        self.bulk_operations = []
    
    def create_pattern_rule(self, user_id: int, rule_data: Dict) -> Dict:
        """
        Create a pattern-based mapping rule
        
        Args:
            user_id: ID of the user
            rule_data: Rule configuration
            
        Returns:
            Result dictionary with success status
        """
        try:
            rule = {
                'id': f"rule_{datetime.utcnow().timestamp()}",
                'user_id': user_id,
                'name': rule_data.get('name'),
                'pattern_type': rule_data.get('pattern_type'),  # 'contains', 'starts_with', 'regex'
                'pattern_value': rule_data.get('pattern_value'),
                'harvest_project_id': rule_data.get('harvest_project_id'),
                'harvest_project_name': rule_data.get('harvest_project_name'),
                'harvest_task_id': rule_data.get('harvest_task_id'),
                'harvest_task_name': rule_data.get('harvest_task_name'),
                'apply_to': rule_data.get('apply_to', 'summary'),  # 'summary', 'description', 'location', 'all'
                'case_sensitive': rule_data.get('case_sensitive', False),
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'applied_count': 0
            }
            
            # Validate pattern
            if rule['pattern_type'] == 'regex':
                try:
                    re.compile(rule['pattern_value'])
                except re.error as e:
                    return {'success': False, 'error': f'Invalid regex pattern: {e}'}
            
            # Store rule (in a real implementation, this would be in database)
            self.pattern_rules.append(rule)
            
            return {'success': True, 'rule': rule}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def apply_pattern_rules(self, events: List[Dict], user_id: int) -> Dict:
        """
        Apply pattern rules to a list of events
        
        Args:
            events: List of calendar events
            user_id: ID of the user
            
        Returns:
            Dictionary with application results
        """
        results = {
            'total_events': len(events),
            'rules_applied': 0,
            'mappings_created': 0,
            'mappings_updated': 0,
            'errors': [],
            'applied_rules': []
        }
        
        # Get user's active rules
        user_rules = [rule for rule in self.pattern_rules 
                     if rule['user_id'] == user_id and rule['is_active']]
        
        for event in events:
            for rule in user_rules:
                if self._event_matches_rule(event, rule):
                    # Create or update mapping
                    mapping_result = self._create_mapping_from_rule(event, rule, user_id)
                    
                    if mapping_result['success']:
                        if mapping_result['created']:
                            results['mappings_created'] += 1
                        else:
                            results['mappings_updated'] += 1
                        
                        results['rules_applied'] += 1
                        rule['applied_count'] += 1
                        
                        if rule['id'] not in [r['rule_id'] for r in results['applied_rules']]:
                            results['applied_rules'].append({
                                'rule_id': rule['id'],
                                'rule_name': rule['name'],
                                'applications': 1
                            })
                        else:
                            # Increment application count
                            for applied_rule in results['applied_rules']:
                                if applied_rule['rule_id'] == rule['id']:
                                    applied_rule['applications'] += 1
                                    break
                    else:
                        results['errors'].append(mapping_result['error'])
        
        return results
    
    def _event_matches_rule(self, event: Dict, rule: Dict) -> bool:
        """Check if an event matches a pattern rule"""
        # Get text to search in
        text_sources = {
            'summary': event.get('summary', ''),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'all': f"{event.get('summary', '')} {event.get('description', '')} {event.get('location', '')}"
        }
        
        search_text = text_sources.get(rule['apply_to'], '')
        
        if not rule['case_sensitive']:
            search_text = search_text.lower()
            pattern_value = rule['pattern_value'].lower()
        else:
            pattern_value = rule['pattern_value']
        
        # Apply pattern matching
        if rule['pattern_type'] == 'contains':
            return pattern_value in search_text
        elif rule['pattern_type'] == 'starts_with':
            return search_text.startswith(pattern_value)
        elif rule['pattern_type'] == 'regex':
            try:
                flags = 0 if rule['case_sensitive'] else re.IGNORECASE
                return bool(re.search(pattern_value, search_text, flags))
            except re.error:
                return False
        
        return False
    
    def _create_mapping_from_rule(self, event: Dict, rule: Dict, user_id: int) -> Dict:
        """Create a mapping from a pattern rule"""
        try:
            # Extract label from event (use summary as default)
            calendar_label = event.get('summary', '').strip()
            
            if not calendar_label:
                return {'success': False, 'error': 'Event has no summary for label'}
            
            # Check if mapping already exists
            existing = ProjectMapping.query.filter_by(
                user_id=user_id,
                calendar_label=calendar_label
            ).first()
            
            if existing:
                # Update existing mapping
                existing.harvest_project_id = rule['harvest_project_id']
                existing.harvest_project_name = rule['harvest_project_name']
                existing.harvest_task_id = rule['harvest_task_id']
                existing.harvest_task_name = rule['harvest_task_name']
                existing.updated_at = datetime.utcnow()
                
                db.session.commit()
                return {'success': True, 'created': False, 'mapping': existing}
            else:
                # Create new mapping
                mapping = ProjectMapping(
                    user_id=user_id,
                    calendar_label=calendar_label,
                    harvest_project_id=rule['harvest_project_id'],
                    harvest_project_name=rule['harvest_project_name'],
                    harvest_task_id=rule['harvest_task_id'],
                    harvest_task_name=rule['harvest_task_name']
                )
                
                db.session.add(mapping)
                db.session.commit()
                return {'success': True, 'created': True, 'mapping': mapping}
                
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def bulk_assign_mappings(self, assignments: List[Dict], user_id: int) -> Dict:
        """
        Bulk assign mappings to multiple events
        
        Args:
            assignments: List of assignment dictionaries
            user_id: ID of the user
            
        Returns:
            Dictionary with assignment results
        """
        results = {
            'total_assignments': len(assignments),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'created_mappings': []
        }
        
        try:
            for assignment in assignments:
                event = assignment.get('event')
                project_id = assignment.get('harvest_project_id')
                project_name = assignment.get('harvest_project_name')
                task_id = assignment.get('harvest_task_id')
                task_name = assignment.get('harvest_task_name')
                
                if not all([event, project_id, project_name, task_id, task_name]):
                    results['failed'] += 1
                    results['errors'].append('Missing required assignment data')
                    continue
                
                # Create mapping
                calendar_label = event.get('summary', '').strip()
                
                if not calendar_label:
                    results['failed'] += 1
                    results['errors'].append(f'Event has no summary: {event.get("id")}')
                    continue
                
                # Check if mapping exists
                existing = ProjectMapping.query.filter_by(
                    user_id=user_id,
                    calendar_label=calendar_label
                ).first()
                
                if existing:
                    # Update existing
                    existing.harvest_project_id = project_id
                    existing.harvest_project_name = project_name
                    existing.harvest_task_id = task_id
                    existing.harvest_task_name = task_name
                    existing.updated_at = datetime.utcnow()
                    
                    results['created_mappings'].append({
                        'calendar_label': calendar_label,
                        'project_name': project_name,
                        'task_name': task_name,
                        'action': 'updated'
                    })
                else:
                    # Create new
                    mapping = ProjectMapping(
                        user_id=user_id,
                        calendar_label=calendar_label,
                        harvest_project_id=project_id,
                        harvest_project_name=project_name,
                        harvest_task_id=task_id,
                        harvest_task_name=task_name
                    )
                    
                    db.session.add(mapping)
                    
                    results['created_mappings'].append({
                        'calendar_label': calendar_label,
                        'project_name': project_name,
                        'task_name': task_name,
                        'action': 'created'
                    })
                
                results['successful'] += 1
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            results['errors'].append(str(e))
        
        return results
    
    def export_mappings(self, user_id: int) -> Dict:
        """Export user's mappings to JSON format"""
        try:
            mappings = ProjectMapping.query.filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            export_data = {
                'export_date': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'mappings': []
            }
            
            for mapping in mappings:
                export_data['mappings'].append({
                    'calendar_label': mapping.calendar_label,
                    'harvest_project_id': mapping.harvest_project_id,
                    'harvest_project_name': mapping.harvest_project_name,
                    'harvest_task_id': mapping.harvest_task_id,
                    'harvest_task_name': mapping.harvest_task_name,
                    'created_at': mapping.created_at.isoformat() if mapping.created_at else None,
                    'updated_at': mapping.updated_at.isoformat() if mapping.updated_at else None
                })
            
            return {'success': True, 'data': export_data}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def import_mappings(self, import_data: Dict, user_id: int, merge_strategy: str = 'update') -> Dict:
        """
        Import mappings from JSON data
        
        Args:
            import_data: JSON data with mappings
            user_id: ID of the user
            merge_strategy: 'update', 'skip', 'replace'
            
        Returns:
            Dictionary with import results
        """
        results = {
            'total_mappings': 0,
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        try:
            mappings_data = import_data.get('mappings', [])
            results['total_mappings'] = len(mappings_data)
            
            for mapping_data in mappings_data:
                calendar_label = mapping_data.get('calendar_label')
                
                if not calendar_label:
                    results['errors'].append('Missing calendar_label in mapping data')
                    continue
                
                # Check if mapping exists
                existing = ProjectMapping.query.filter_by(
                    user_id=user_id,
                    calendar_label=calendar_label
                ).first()
                
                if existing:
                    if merge_strategy == 'skip':
                        results['skipped'] += 1
                        continue
                    elif merge_strategy == 'update':
                        # Update existing mapping
                        existing.harvest_project_id = mapping_data.get('harvest_project_id')
                        existing.harvest_project_name = mapping_data.get('harvest_project_name')
                        existing.harvest_task_id = mapping_data.get('harvest_task_id')
                        existing.harvest_task_name = mapping_data.get('harvest_task_name')
                        existing.updated_at = datetime.utcnow()
                        results['updated'] += 1
                else:
                    # Create new mapping
                    mapping = ProjectMapping(
                        user_id=user_id,
                        calendar_label=calendar_label,
                        harvest_project_id=mapping_data.get('harvest_project_id'),
                        harvest_project_name=mapping_data.get('harvest_project_name'),
                        harvest_task_id=mapping_data.get('harvest_task_id'),
                        harvest_task_name=mapping_data.get('harvest_task_name')
                    )
                    
                    db.session.add(mapping)
                    results['imported'] += 1
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            results['errors'].append(str(e))
        
        return results
    
    def get_pattern_rules(self, user_id: int) -> List[Dict]:
        """Get all pattern rules for a user"""
        return [rule for rule in self.pattern_rules if rule['user_id'] == user_id]
    
    def delete_pattern_rule(self, user_id: int, rule_id: str) -> Dict:
        """Delete a pattern rule"""
        try:
            for i, rule in enumerate(self.pattern_rules):
                if rule['id'] == rule_id and rule['user_id'] == user_id:
                    del self.pattern_rules[i]
                    return {'success': True}
            
            return {'success': False, 'error': 'Rule not found'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
