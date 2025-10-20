#!/usr/bin/env python3
"""
Script to add grouping information to the process_preview function
"""

def fix_main_py():
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Find the process_preview function and replace the return statement
    old_return = '''        results = mapping_engine.process_events_for_week(events, week_start, user.id)

        return jsonify({
            'success': True,
            'timesheet_entries': results['timesheet_entries'],
            'mapped_events': results['mapped_events'],
            'unmapped_events': results['unmapped_events'],
            'unmapped_events_details': results['unmapped_events_details'],
            'warnings': results['warnings']
        })'''
    
    new_return = '''        results = mapping_engine.process_events_for_week(events, week_start, user.id)

        # Add grouping information
        timesheet_entries = results['timesheet_entries']
        
        # Group entries by project_id, task_id, and spent_date to show how they'll be combined
        grouped_entries = {}
        for entry in timesheet_entries:
            key = (entry['project_id'], entry['task_id'], entry['spent_date'])
            if key not in grouped_entries:
                grouped_entries[key] = {
                    'project_id': entry['project_id'],
                    'project_name': entry['project_name'],
                    'task_id': entry['task_id'],
                    'task_name': entry['task_name'],
                    'spent_date': entry['spent_date'],
                    'hours': 0,
                    'event_count': 0,
                    'event_summaries': []
                }
            
            grouped_entries[key]['hours'] += entry['hours']
            grouped_entries[key]['event_count'] += 1
            grouped_entries[key]['event_summaries'].append(entry['event_summary'])

        # Convert to list and add grouping info
        final_entries = list(grouped_entries.values())
        
        # Add grouping summary
        grouping_info = {
            'original_entries': len(timesheet_entries),
            'grouped_entries': len(final_entries),
            'total_hours': sum(entry['hours'] for entry in final_entries)
        }

        return jsonify({
            'success': True,
            'timesheet_entries': final_entries,  # Use grouped entries
            'original_timesheet_entries': timesheet_entries,  # Keep original for reference
            'grouping_info': grouping_info,
            'mapped_events': results['mapped_events'],
            'unmapped_events': results['unmapped_events'],
            'unmapped_events_details': results['unmapped_events_details'],
            'warnings': results['warnings']
        })'''
    
    if old_return in content:
        content = content.replace(old_return, new_return)
        
        with open('main.py', 'w') as f:
            f.write(content)
        
        print("✅ Successfully updated main.py with grouping information")
        return True
    else:
        print("❌ Could not find the target code in main.py")
        return False

if __name__ == "__main__":
    fix_main_py()
