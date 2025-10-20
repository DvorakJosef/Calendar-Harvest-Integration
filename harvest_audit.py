#!/usr/bin/env python3
"""
Harvest Account Audit Script
Checks for timesheet entries that may have been created under wrong accounts
"""

import sys
import os
from datetime import datetime, timedelta, date
import json
from typing import Dict, List, Optional

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import db, User, UserConfig, ProcessingHistory
from harvest_service import HarvestService

def audit_harvest_entries():
    """Audit Harvest entries for all users to detect anomalies"""
    
    print("🕐 HARVEST TIMESHEET AUDIT")
    print("=" * 50)
    
    audit_results = {
        "audit_timestamp": datetime.now().isoformat(),
        "users_audited": 0,
        "total_entries_found": 0,
        "potential_issues": [],
        "user_summaries": []
    }
    
    with app.app_context():
        try:
            users = User.query.all()
            audit_results["users_audited"] = len(users)
            
            print(f"📊 Auditing {len(users)} users...")
            
            # Define audit period (last 60 days to catch recent issues)
            end_date = date.today()
            start_date = end_date - timedelta(days=60)
            
            print(f"📅 Audit period: {start_date} to {end_date}")
            print()
            
            for user in users:
                print(f"👤 Auditing user: {user.email} (ID: {user.id})")
                
                user_summary = {
                    "user_id": user.id,
                    "user_email": user.email,
                    "has_harvest_config": False,
                    "harvest_entries": 0,
                    "app_processing_history": 0,
                    "date_range": None,
                    "suspicious_patterns": []
                }
                
                # Check if user has Harvest OAuth configuration
                user_config = UserConfig.query.filter_by(user_id=user.id).first()
                if not user_config or not user_config.is_harvest_oauth_configured():
                    print("   ❌ No Harvest OAuth credentials configured")
                    user_summary["has_harvest_config"] = False
                    audit_results["user_summaries"].append(user_summary)
                    continue
                
                user_summary["has_harvest_config"] = True
                print("   ✅ Harvest credentials found")
                
                # Get app processing history
                processing_history = ProcessingHistory.query.filter_by(user_id=user.id).all()
                user_summary["app_processing_history"] = len(processing_history)
                print(f"   📈 App processing history: {len(processing_history)} entries")
                
                if processing_history:
                    earliest_processing = min(h.processed_at for h in processing_history).date()
                    latest_processing = max(h.processed_at for h in processing_history).date()
                    print(f"   📅 App usage period: {earliest_processing} to {latest_processing}")
                
                # Get Harvest entries
                try:
                    harvest_service = HarvestService()
                    entries = harvest_service.get_time_entries(start_date, end_date, user_id=user.id)
                    user_summary["harvest_entries"] = len(entries)
                    
                    print(f"   ⏰ Harvest entries found: {len(entries)}")
                    audit_results["total_entries_found"] += len(entries)
                    
                    if entries:
                        # Analyze entry patterns
                        entry_dates = [e['spent_date'] for e in entries]
                        earliest_entry = min(entry_dates)
                        latest_entry = max(entry_dates)
                        user_summary["date_range"] = f"{earliest_entry} to {latest_entry}"
                        
                        print(f"   📊 Entry date range: {earliest_entry} to {latest_entry}")
                        
                        # Check for suspicious patterns
                        suspicious_patterns = analyze_entry_patterns(entries, processing_history, user)
                        user_summary["suspicious_patterns"] = suspicious_patterns
                        
                        if suspicious_patterns:
                            print(f"   ⚠️  Found {len(suspicious_patterns)} suspicious patterns:")
                            for pattern in suspicious_patterns:
                                print(f"      - {pattern['type']}: {pattern['description']}")
                                audit_results["potential_issues"].append({
                                    "user_id": user.id,
                                    "user_email": user.email,
                                    "issue": pattern
                                })
                        
                        # Show recent entries sample
                        recent_entries = sorted(entries, key=lambda e: e['spent_date'], reverse=True)[:5]
                        print(f"   📋 Recent entries sample:")
                        for entry in recent_entries:
                            print(f"      {entry['spent_date']}: {entry['hours']}h - {entry['project_name']} ({entry.get('notes', 'No notes')[:50]})")
                    
                except Exception as e:
                    print(f"   ❌ Error accessing Harvest: {e}")
                    user_summary["error"] = str(e)
                
                audit_results["user_summaries"].append(user_summary)
                print()
            
            # Generate summary report
            print("=" * 50)
            print("📋 AUDIT SUMMARY")
            print("=" * 50)
            
            print(f"Users audited: {audit_results['users_audited']}")
            print(f"Total Harvest entries found: {audit_results['total_entries_found']}")
            print(f"Potential issues detected: {len(audit_results['potential_issues'])}")
            
            if audit_results["potential_issues"]:
                print("\n🚨 POTENTIAL ISSUES:")
                for issue in audit_results["potential_issues"]:
                    print(f"   User: {issue['user_email']}")
                    print(f"   Issue: {issue['issue']['type']} - {issue['issue']['description']}")
                    print()
            
            # Save audit report
            report_filename = f"harvest_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, 'w') as f:
                json.dump(audit_results, f, indent=2)
            
            print(f"📄 Detailed audit report saved: {report_filename}")
            
            return audit_results
            
        except Exception as e:
            print(f"❌ Error during Harvest audit: {e}")
            return None

def analyze_entry_patterns(entries: List[Dict], processing_history: List, user) -> List[Dict]:
    """Analyze Harvest entries for suspicious patterns"""
    
    patterns = []
    
    if not entries:
        return patterns
    
    # Pattern 1: Entries created outside of app usage periods
    if processing_history:
        app_dates = set(h.processed_at.date() for h in processing_history)
        entry_dates = set(e['spent_date'] for e in entries if isinstance(e['spent_date'], str))
        entry_dates = set(datetime.fromisoformat(d).date() if isinstance(d, str) else d for d in entry_dates)
        
        entries_without_app_usage = entry_dates - app_dates
        if entries_without_app_usage:
            patterns.append({
                "type": "ENTRIES_WITHOUT_APP_USAGE",
                "description": f"Found {len(entries_without_app_usage)} dates with Harvest entries but no app processing",
                "details": {"dates": [d.isoformat() for d in entries_without_app_usage]}
            })
    
    # Pattern 2: Unusually high number of entries for user activity level
    if len(entries) > 50 and len(processing_history) < 10:
        patterns.append({
            "type": "HIGH_ENTRIES_LOW_APP_USAGE",
            "description": f"User has {len(entries)} Harvest entries but only {len(processing_history)} app processing records",
            "details": {"harvest_entries": len(entries), "app_processing": len(processing_history)}
        })
    
    # Pattern 3: Entries with suspicious timing (created very quickly)
    entry_times = []
    for entry in entries:
        if 'created_at' in entry:
            try:
                created_time = datetime.fromisoformat(entry['created_at'].replace('Z', '+00:00'))
                entry_times.append(created_time)
            except:
                pass
    
    if len(entry_times) > 1:
        entry_times.sort()
        rapid_entries = 0
        for i in range(1, len(entry_times)):
            time_diff = (entry_times[i] - entry_times[i-1]).total_seconds()
            if time_diff < 10:  # Less than 10 seconds between entries
                rapid_entries += 1
        
        if rapid_entries > 5:
            patterns.append({
                "type": "RAPID_ENTRY_CREATION",
                "description": f"Found {rapid_entries} entries created within 10 seconds of each other",
                "details": {"rapid_entries_count": rapid_entries}
            })
    
    # Pattern 4: Entries with identical notes (potential bulk creation)
    notes_count = {}
    for entry in entries:
        notes = entry.get('notes', '').strip()
        if notes:
            notes_count[notes] = notes_count.get(notes, 0) + 1
    
    duplicate_notes = {notes: count for notes, count in notes_count.items() if count > 5}
    if duplicate_notes:
        patterns.append({
            "type": "DUPLICATE_NOTES",
            "description": f"Found entries with identical notes repeated multiple times",
            "details": {"duplicate_notes": duplicate_notes}
        })
    
    return patterns

def check_cross_user_contamination():
    """Check if entries might have been created under wrong user accounts"""
    
    print("\n🔍 CHECKING FOR CROSS-USER CONTAMINATION")
    print("=" * 50)
    
    with app.app_context():
        try:
            users = User.query.all()
            
            # Get the first user (most likely to be affected by the bug)
            if not users:
                print("❌ No users found")
                return
            
            first_user = users[0]
            print(f"🎯 Analyzing first user (most likely affected): {first_user.email}")
            
            # Check if first user has disproportionate amount of data
            first_user_processing = ProcessingHistory.query.filter_by(user_id=first_user.id).count()
            
            other_users_processing = []
            for user in users[1:]:
                count = ProcessingHistory.query.filter_by(user_id=user.id).count()
                other_users_processing.append((user.email, count))
            
            print(f"📊 First user processing history: {first_user_processing}")
            print(f"📊 Other users processing history:")
            for email, count in other_users_processing:
                print(f"   {email}: {count}")
            
            # Check for suspicious pattern
            if first_user_processing > 0 and all(count == 0 for _, count in other_users_processing):
                print("\n⚠️  SUSPICIOUS PATTERN DETECTED:")
                print("   Only the first user has processing history")
                print("   This suggests the user isolation bug may have affected data")
                print("   Recommendation: Check if other users' calendar events were processed under first user's account")
            
            return {
                "first_user_email": first_user.email,
                "first_user_processing": first_user_processing,
                "other_users_processing": other_users_processing,
                "suspicious_pattern": first_user_processing > 0 and all(count == 0 for _, count in other_users_processing)
            }
            
        except Exception as e:
            print(f"❌ Error checking cross-user contamination: {e}")
            return None

if __name__ == "__main__":
    print("🔒 Starting Harvest Account Audit...")
    
    # Run main audit
    audit_results = audit_harvest_entries()
    
    # Check for cross-user contamination
    contamination_check = check_cross_user_contamination()
    
    print("\n🎯 RECOMMENDATIONS:")
    print("1. Review the audit results above for any suspicious patterns")
    print("2. Check with colleagues about any unexpected timesheet entries")
    print("3. Verify that entries match actual work performed")
    print("4. Consider reverting any incorrect entries in Harvest")
    print("5. Monitor future app usage for proper user isolation")
    
    if audit_results and audit_results.get("potential_issues"):
        print(f"\n⚠️  Found {len(audit_results['potential_issues'])} potential issues - review the detailed report")
    
    if contamination_check and contamination_check.get("suspicious_pattern"):
        print("\n🚨 CRITICAL: Suspicious cross-user pattern detected - immediate investigation recommended")
    
    print("\n✅ Harvest audit completed!")
