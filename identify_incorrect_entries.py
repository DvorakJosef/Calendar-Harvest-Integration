#!/usr/bin/env python3
"""
Identify Potentially Incorrect Harvest Entries
Helps identify timesheet entries that may belong to other users
"""

import sys
import os
from datetime import datetime, timedelta, date
import json
from collections import defaultdict

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import db, User, UserConfig, ProcessingHistory
from harvest_service import HarvestService

def analyze_harvest_entries_for_anomalies():
    """Analyze Harvest entries to identify potentially incorrect ones"""
    
    print("🔍 ANALYZING HARVEST ENTRIES FOR ANOMALIES")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Get your user info
            user = User.query.first()
            if not user:
                print("❌ No user found in database")
                return
            
            print(f"👤 Analyzing entries for: {user.email}")
            
            # Get Harvest entries for last 30 days
            harvest_service = HarvestService()
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            print(f"📅 Analyzing period: {start_date} to {end_date}")
            
            entries = harvest_service.get_time_entries(start_date, end_date, user_id=user.id)
            print(f"📊 Found {len(entries)} Harvest entries")
            
            if not entries:
                print("No entries to analyze")
                return
            
            # Analyze patterns
            analysis_results = {
                "total_entries": len(entries),
                "analysis_date": datetime.now().isoformat(),
                "suspicious_entries": [],
                "patterns": {},
                "recommendations": []
            }
            
            # Group entries by various criteria
            by_date = defaultdict(list)
            by_project = defaultdict(list)
            by_notes_pattern = defaultdict(list)
            by_hours = defaultdict(list)
            
            for entry in entries:
                entry_date = entry['spent_date']
                by_date[entry_date].append(entry)
                by_project[entry['project_name']].append(entry)
                
                # Analyze notes patterns
                notes = entry.get('notes', '').lower()
                if 'meeting' in notes:
                    by_notes_pattern['meetings'].append(entry)
                if 'call' in notes:
                    by_notes_pattern['calls'].append(entry)
                if 'sync' in notes:
                    by_notes_pattern['syncs'].append(entry)
                
                # Group by hours
                hours = entry['hours']
                if hours >= 8:
                    by_hours['full_day'].append(entry)
                elif hours >= 4:
                    by_hours['half_day'].append(entry)
                elif hours <= 0.5:
                    by_hours['short'].append(entry)
            
            print(f"\n📈 ENTRY PATTERNS:")
            print(f"   Entries across {len(by_date)} days")
            print(f"   Projects involved: {len(by_project)}")
            print(f"   Meeting entries: {len(by_notes_pattern.get('meetings', []))}")
            print(f"   Call entries: {len(by_notes_pattern.get('calls', []))}")
            print(f"   Full day entries (8+ hours): {len(by_hours.get('full_day', []))}")
            
            # Identify suspicious patterns
            print(f"\n🚨 SUSPICIOUS PATTERNS:")
            
            # Pattern 1: Days with unusually high hours
            high_hour_days = []
            for entry_date, day_entries in by_date.items():
                total_hours = sum(e['hours'] for e in day_entries)
                if total_hours > 12:  # More than 12 hours in a day
                    high_hour_days.append({
                        "date": entry_date,
                        "total_hours": total_hours,
                        "entries_count": len(day_entries),
                        "entries": day_entries
                    })
            
            if high_hour_days:
                print(f"   ⚠️  {len(high_hour_days)} days with >12 hours:")
                for day in high_hour_days[:5]:  # Show first 5
                    print(f"      {day['date']}: {day['total_hours']:.1f} hours ({day['entries_count']} entries)")
                analysis_results["suspicious_entries"].extend(high_hour_days)
            
            # Pattern 2: Entries with similar notes (potential bulk processing)
            notes_frequency = defaultdict(int)
            for entry in entries:
                notes = entry.get('notes', '').strip()
                if notes:
                    notes_frequency[notes] += 1
            
            duplicate_notes = {notes: count for notes, count in notes_frequency.items() if count > 5}
            if duplicate_notes:
                print(f"   ⚠️  Notes repeated >5 times:")
                for notes, count in list(duplicate_notes.items())[:3]:  # Show first 3
                    print(f"      '{notes[:50]}...': {count} times")
                analysis_results["patterns"]["duplicate_notes"] = duplicate_notes
            
            # Pattern 3: Projects with unusual activity
            project_hours = {}
            for project, project_entries in by_project.items():
                total_hours = sum(e['hours'] for e in project_entries)
                project_hours[project] = {
                    "total_hours": total_hours,
                    "entry_count": len(project_entries),
                    "avg_hours_per_entry": total_hours / len(project_entries)
                }
            
            # Sort by total hours
            top_projects = sorted(project_hours.items(), key=lambda x: x[1]['total_hours'], reverse=True)
            print(f"   📊 Top projects by hours:")
            for project, stats in top_projects[:5]:
                print(f"      {project}: {stats['total_hours']:.1f}h ({stats['entry_count']} entries)")
            
            # Pattern 4: Entries created in rapid succession
            entries_with_created_time = []
            for entry in entries:
                if 'created_at' in entry:
                    try:
                        created_time = datetime.fromisoformat(entry['created_at'].replace('Z', '+00:00'))
                        entries_with_created_time.append((created_time, entry))
                    except:
                        pass
            
            if len(entries_with_created_time) > 1:
                entries_with_created_time.sort(key=lambda x: x[0])
                rapid_creation_groups = []
                current_group = [entries_with_created_time[0]]
                
                for i in range(1, len(entries_with_created_time)):
                    time_diff = (entries_with_created_time[i][0] - entries_with_created_time[i-1][0]).total_seconds()
                    if time_diff < 30:  # Less than 30 seconds
                        current_group.append(entries_with_created_time[i])
                    else:
                        if len(current_group) > 3:
                            rapid_creation_groups.append(current_group)
                        current_group = [entries_with_created_time[i]]
                
                if len(current_group) > 3:
                    rapid_creation_groups.append(current_group)
                
                if rapid_creation_groups:
                    print(f"   ⚠️  {len(rapid_creation_groups)} groups of rapidly created entries:")
                    for i, group in enumerate(rapid_creation_groups[:3]):
                        print(f"      Group {i+1}: {len(group)} entries created within 30 seconds")
            
            # Generate recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            
            recommendations = []
            
            if high_hour_days:
                recommendations.append("Review days with >12 hours - these may include other people's work")
            
            if duplicate_notes:
                recommendations.append("Check entries with identical notes - may indicate bulk processing")
            
            if len(by_project) > 10:
                recommendations.append("Review project distribution - you may have entries for projects you don't work on")
            
            recommendations.extend([
                "Ask colleagues what calendar events they processed through the app",
                "Cross-reference your actual work with timesheet entries",
                "Look for meetings you didn't attend or projects you don't recognize",
                "Check entries on days when you were out of office"
            ])
            
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
            
            analysis_results["recommendations"] = recommendations
            
            # Save detailed analysis
            report_filename = f"harvest_entry_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            
            print(f"\n📄 Detailed analysis saved: {report_filename}")
            
            # Generate CSV for manual review
            csv_filename = f"harvest_entries_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(csv_filename, 'w') as f:
                f.write("Date,Hours,Project,Task,Notes,Suspicious\n")
                for entry in entries:
                    notes = entry.get('notes', '').replace('"', '""')  # Escape quotes
                    suspicious = "YES" if entry['hours'] > 8 or entry['spent_date'] in [d['date'] for d in high_hour_days] else "NO"
                    f.write(f'"{entry["spent_date"]}",{entry["hours"]},"{entry["project_name"]}","{entry.get("task_name", "")}","{notes}",{suspicious}\n')
            
            print(f"📊 CSV for manual review saved: {csv_filename}")
            
            return analysis_results
            
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            return None

if __name__ == "__main__":
    print("🔍 Starting Harvest Entry Analysis...")
    
    results = analyze_harvest_entries_for_anomalies()
    
    if results:
        print(f"\n🎯 NEXT STEPS:")
        print("1. Open the generated CSV file in Excel/Google Sheets")
        print("2. Review entries marked as 'Suspicious'")
        print("3. Cross-reference with your actual work calendar")
        print("4. Identify entries that don't match your work")
        print("5. Contact colleagues to confirm which entries belong to them")
        print("6. Plan to move incorrect entries to the right accounts")
        
        if results.get("suspicious_entries"):
            print(f"\n⚠️  Found {len(results['suspicious_entries'])} potentially suspicious patterns")
            print("   Focus your review on these first!")
    
    print("\n✅ Analysis completed!")
