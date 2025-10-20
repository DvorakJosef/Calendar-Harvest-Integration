#!/usr/bin/env python3
"""
Security Audit Script for Calendar-Harvest Integration
Investigates potential cross-user data access and timesheet manipulation
"""

import sys
import os
from datetime import datetime, timedelta, date
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import db, User, UserConfig, ProjectMapping, ProcessingHistory
from harvest_service import HarvestService

def audit_user_data():
    """Audit user data for potential cross-contamination"""
    
    print("🔍 SECURITY AUDIT: Calendar-Harvest Integration")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            print(f"\n📊 Found {len(users)} users in database:")
            
            for i, user in enumerate(users, 1):
                print(f"   {i}. {user.email} (ID: {user.id}) - Created: {user.created_at}")
                
                # Check user config
                user_config = UserConfig.query.filter_by(user_id=user.id).first()
                if user_config:
                    has_google = bool(user_config.google_credentials)
                    has_harvest = user_config.is_harvest_oauth_configured()
                    print(f"      Google: {'✅' if has_google else '❌'} | Harvest OAuth: {'✅' if has_harvest else '❌'}")
                else:
                    print(f"      No configuration found")
            
            print("\n" + "=" * 60)
            
            # Audit timesheet entries for each user
            print("\n🕐 TIMESHEET AUDIT:")
            
            for user in users:
                print(f"\n👤 User: {user.email}")
                
                # Check if user has Harvest OAuth credentials
                user_config = UserConfig.query.filter_by(user_id=user.id).first()
                if not user_config or not user_config.is_harvest_oauth_configured():
                    print("   ❌ No Harvest OAuth credentials - skipping")
                    continue
                
                # Get processing history
                history = ProcessingHistory.query.filter_by(user_id=user.id).all()
                print(f"   📈 Processing history: {len(history)} entries")
                
                if history:
                    latest = max(history, key=lambda h: h.processed_at)
                    earliest = min(history, key=lambda h: h.processed_at)
                    print(f"   📅 Date range: {earliest.processed_at.date()} to {latest.processed_at.date()}")
                
                # Check recent Harvest entries
                try:
                    harvest_service = HarvestService()
                    
                    # Get entries from last 30 days
                    end_date = date.today()
                    start_date = end_date - timedelta(days=30)
                    
                    entries = harvest_service.get_time_entries(start_date, end_date, user_id=user.id)
                    print(f"   ⏰ Harvest entries (last 30 days): {len(entries)}")
                    
                    if entries:
                        # Group by date
                        by_date = {}
                        for entry in entries:
                            entry_date = entry['spent_date']
                            if entry_date not in by_date:
                                by_date[entry_date] = []
                            by_date[entry_date].append(entry)
                        
                        print(f"   📊 Entries across {len(by_date)} days")
                        
                        # Show recent entries
                        recent_dates = sorted(by_date.keys(), reverse=True)[:5]
                        for entry_date in recent_dates:
                            day_entries = by_date[entry_date]
                            total_hours = sum(e['hours'] for e in day_entries)
                            print(f"      {entry_date}: {len(day_entries)} entries, {total_hours:.1f} hours")
                
                except Exception as e:
                    print(f"   ❌ Error checking Harvest entries: {e}")
                
                # Check project mappings
                mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
                print(f"   🗂️  Active mappings: {len(mappings)}")
                
                print()
            
            print("=" * 60)
            
            # Check for potential issues
            print("\n🚨 POTENTIAL ISSUES ANALYSIS:")
            
            # Check if first user has most data (potential victim of bug)
            if users:
                first_user = users[0]
                first_user_history = ProcessingHistory.query.filter_by(user_id=first_user.id).count()
                first_user_mappings = ProjectMapping.query.filter_by(user_id=first_user.id).count()
                
                print(f"\n📊 First user analysis ({first_user.email}):")
                print(f"   Processing history: {first_user_history} entries")
                print(f"   Project mappings: {first_user_mappings} mappings")
                
                # Check if other users have suspiciously low data
                other_users_data = []
                for user in users[1:]:
                    history_count = ProcessingHistory.query.filter_by(user_id=user.id).count()
                    mapping_count = ProjectMapping.query.filter_by(user_id=user.id).count()
                    other_users_data.append((user.email, history_count, mapping_count))
                
                if other_users_data:
                    print(f"\n📊 Other users data:")
                    for email, history, mappings in other_users_data:
                        print(f"   {email}: {history} history, {mappings} mappings")
                
                # Flag potential issues
                if first_user_history > 0 and all(data[1] == 0 for data in other_users_data):
                    print(f"\n⚠️  POTENTIAL ISSUE: Only first user has processing history")
                    print(f"   This suggests the bug may have affected data isolation")
                
            print("\n✅ Security audit completed!")
            
        except Exception as e:
            print(f"❌ Error during audit: {e}")
            return False
    
    return True

def generate_incident_report():
    """Generate detailed incident report"""
    
    print("\n📋 GENERATING INCIDENT REPORT...")
    
    report = {
        "incident_id": f"SEC-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "severity": "HIGH",
        "status": "RESOLVED",
        "summary": "Cross-user data access due to missing user_id filtering",
        "affected_systems": ["Calendar-Harvest Integration"],
        "timeline": [],
        "impact_assessment": {},
        "remediation_actions": [],
        "recommendations": []
    }
    
    with app.app_context():
        # Get user statistics
        users = User.query.all()
        report["impact_assessment"]["total_users"] = len(users)
        
        # Get processing statistics
        total_processing = ProcessingHistory.query.count()
        report["impact_assessment"]["total_processing_entries"] = total_processing
        
        # Get mapping statistics
        total_mappings = ProjectMapping.query.count()
        report["impact_assessment"]["total_mappings"] = total_mappings
    
    # Add timeline
    report["timeline"] = [
        {
            "time": "2025-07-16 16:00:00",
            "event": "User reports colleagues' timesheets being manipulated"
        },
        {
            "time": "2025-07-16 17:00:00", 
            "event": "Security investigation initiated"
        },
        {
            "time": "2025-07-16 18:00:00",
            "event": "Critical bugs identified in user isolation"
        },
        {
            "time": "2025-07-16 19:00:00",
            "event": "Security fixes implemented and deployed"
        }
    ]
    
    # Add remediation actions
    report["remediation_actions"] = [
        "Fixed harvest_disconnect() to use current user's config",
        "Added @login_required to missing endpoints",
        "Fixed suggestion engine to use only current user's data",
        "Added proper user_id filtering throughout application",
        "Deployed fixes to production immediately"
    ]
    
    # Add recommendations
    report["recommendations"] = [
        "Implement comprehensive audit logging",
        "Add automated testing for user isolation",
        "Regular security code reviews",
        "Monitor user activity patterns",
        "Implement data access controls"
    ]
    
    # Save report
    report_file = f"incident_report_{report['incident_id']}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Incident report saved: {report_file}")
    return report

if __name__ == "__main__":
    print("🔒 Starting Security Audit...")
    
    # Run audit
    audit_success = audit_user_data()
    
    if audit_success:
        # Generate incident report
        report = generate_incident_report()
        
        print("\n🎯 NEXT STEPS:")
        print("1. Review the audit results above")
        print("2. Check Harvest accounts for any incorrect entries")
        print("3. Communicate with affected colleagues")
        print("4. Monitor application logs for unusual activity")
        print("5. Consider implementing additional monitoring")
        
    else:
        print("❌ Audit failed - check database connection and configuration")
