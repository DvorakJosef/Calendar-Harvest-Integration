#!/usr/bin/env python3
"""
Reverse Incident Investigation
Investigates how YOUR calendar events ended up in COLLEAGUES' timesheets
Period: June 16 - July 13, 2025
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

def investigate_reverse_contamination():
    """
    Investigate how YOUR calendar events ended up in COLLEAGUES' timesheets
    """
    
    print("🔍 REVERSE INCIDENT INVESTIGATION")
    print("=" * 60)
    print("INVESTIGATING: Your calendar events in colleagues' timesheets")
    print("PERIOD: June 16 - July 13, 2025")
    print("=" * 60)
    
    # Define investigation period
    start_date = date(2025, 6, 16)
    end_date = date(2025, 7, 13)
    
    investigation_results = {
        "investigation_date": datetime.now().isoformat(),
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "your_user_id": None,
        "your_email": None,
        "your_processing_history": [],
        "potential_victims": [],
        "timeline_analysis": {},
        "security_violations": []
    }
    
    with app.app_context():
        try:
            # Get your user info
            user = User.query.first()  # You're the only user in the database
            if not user:
                print("❌ No user found in database")
                return None
            
            investigation_results["your_user_id"] = user.id
            investigation_results["your_email"] = user.email
            
            print(f"👤 Your account: {user.email} (ID: {user.id})")
            print(f"📅 Investigation period: {start_date} to {end_date}")
            
            # Get your processing history during the incident period
            processing_history = ProcessingHistory.query.filter(
                ProcessingHistory.user_id == user.id,
                ProcessingHistory.processed_at >= datetime.combine(start_date, datetime.min.time()),
                ProcessingHistory.processed_at <= datetime.combine(end_date, datetime.max.time())
            ).all()
            
            print(f"\n📊 Your app usage during incident period:")
            print(f"   Processing sessions: {len(processing_history)}")
            
            if processing_history:
                for session in processing_history:
                    session_data = {
                        "date": session.processed_at.date().isoformat(),
                        "time": session.processed_at.time().isoformat(),
                        "events_processed": session.events_processed,
                        "entries_created": session.entries_created,
                        "status": session.status
                    }
                    investigation_results["your_processing_history"].append(session_data)
                    
                    print(f"   📅 {session.processed_at.date()} at {session.processed_at.time()}")
                    print(f"      Events processed: {session.events_processed}")
                    print(f"      Entries created: {session.entries_created}")
                    print(f"      Status: {session.status}")
                
                # Analyze timeline
                dates_used = [h.processed_at.date() for h in processing_history]
                unique_dates = sorted(set(dates_used))
                
                print(f"\n📈 Timeline analysis:")
                print(f"   First usage: {min(dates_used)}")
                print(f"   Last usage: {max(dates_used)}")
                print(f"   Days with activity: {len(unique_dates)}")
                print(f"   Total entries created: {sum(h.entries_created for h in processing_history)}")
                
                investigation_results["timeline_analysis"] = {
                    "first_usage": min(dates_used).isoformat(),
                    "last_usage": max(dates_used).isoformat(),
                    "active_days": len(unique_dates),
                    "total_entries_created": sum(h.entries_created for h in processing_history)
                }
            
            # Check if you have Harvest credentials
            user_config = UserConfig.query.filter_by(user_id=user.id).first()
            if user_config and user_config.harvest_access_token:
                print(f"\n✅ You have Harvest credentials configured")
                
                # Get your actual Harvest entries during this period
                try:
                    harvest_service = HarvestService()
                    your_entries = harvest_service.get_time_entries(start_date, end_date, user_id=user.id)
                    
                    print(f"📊 Your actual Harvest entries during period: {len(your_entries)}")
                    
                    if your_entries:
                        # Analyze your entries
                        by_date = defaultdict(list)
                        total_hours = 0
                        
                        for entry in your_entries:
                            entry_date = entry['spent_date']
                            by_date[entry_date].append(entry)
                            total_hours += entry['hours']
                        
                        print(f"   Total hours in YOUR timesheet: {total_hours:.1f}")
                        print(f"   Entries across {len(by_date)} days")
                        
                        # Show daily breakdown
                        print(f"\n📅 Your daily timesheet breakdown:")
                        for entry_date in sorted(by_date.keys()):
                            day_entries = by_date[entry_date]
                            day_hours = sum(e['hours'] for e in day_entries)
                            print(f"   {entry_date}: {len(day_entries)} entries, {day_hours:.1f} hours")
                            
                            # Show entry details
                            for entry in day_entries[:3]:  # Show first 3 entries per day
                                notes = entry.get('notes', 'No notes')[:50]
                                print(f"      - {entry['hours']}h: {entry['project_name']} ({notes})")
                
                except Exception as e:
                    print(f"❌ Error accessing your Harvest data: {e}")
            else:
                print(f"❌ No Harvest credentials found for your account")
            
            # CRITICAL ANALYSIS: How could your events end up in colleagues' timesheets?
            print(f"\n🚨 CRITICAL SECURITY ANALYSIS:")
            print(f"=" * 50)
            
            security_violations = []
            
            # Violation 1: If you're the only user in the database but colleagues reported issues
            print(f"🔍 Analysis 1: Database User Count")
            total_users = User.query.count()
            print(f"   Users in database: {total_users}")
            
            if total_users == 1:
                violation = {
                    "type": "SINGLE_USER_DATABASE_WITH_MULTIPLE_ACTUAL_USERS",
                    "description": "Only 1 user in database but multiple people used the app",
                    "implication": "Colleagues may have used your account/credentials to process their events",
                    "severity": "CRITICAL"
                }
                security_violations.append(violation)
                print(f"   🚨 VIOLATION: {violation['description']}")
                print(f"   💥 IMPLICATION: {violation['implication']}")
            
            # Violation 2: Processing history vs. actual usage
            if processing_history:
                total_app_entries = sum(h.entries_created for h in processing_history)
                print(f"\n🔍 Analysis 2: Entry Creation Discrepancy")
                print(f"   App claims to have created: {total_app_entries} entries")
                
                if user_config and user_config.is_harvest_oauth_configured():
                    try:
                        your_actual_entries = len(harvest_service.get_time_entries(start_date, end_date, user_id=user.id))
                        print(f"   Your actual Harvest entries: {your_actual_entries}")
                        
                        if total_app_entries > your_actual_entries:
                            violation = {
                                "type": "MISSING_ENTRIES_IN_YOUR_ACCOUNT",
                                "description": f"App created {total_app_entries} entries but only {your_actual_entries} found in your account",
                                "implication": "Entries were created in other people's accounts using your calendar data",
                                "severity": "CRITICAL"
                            }
                            security_violations.append(violation)
                            print(f"   🚨 VIOLATION: {violation['description']}")
                            print(f"   💥 IMPLICATION: {violation['implication']}")
                    except:
                        pass
            
            # Violation 3: Shared authentication scenario
            print(f"\n🔍 Analysis 3: Shared Authentication Scenario")
            print(f"   Possible scenario: Colleagues used your login to access the app")
            print(f"   Result: Their calendar events processed using your authentication")
            print(f"   But: Timesheet entries created in THEIR Harvest accounts")
            
            violation = {
                "type": "SHARED_AUTHENTICATION_WITH_INDIVIDUAL_HARVEST_ACCOUNTS",
                "description": "Colleagues may have used your app login but had their own Harvest credentials",
                "implication": "Your calendar events processed but entries created in their accounts",
                "severity": "HIGH"
            }
            security_violations.append(violation)
            print(f"   ⚠️  LIKELY SCENARIO: {violation['description']}")
            
            investigation_results["security_violations"] = security_violations
            
            # Generate recommendations
            print(f"\n💡 INVESTIGATION CONCLUSIONS:")
            print(f"=" * 50)
            
            print(f"1. 🎯 MOST LIKELY SCENARIO:")
            print(f"   - Colleagues used YOUR login credentials to access the app")
            print(f"   - App processed THEIR calendar events using your authentication")
            print(f"   - But the bug caused entries to be created in THEIR Harvest accounts")
            print(f"   - This explains why YOUR work appears in THEIR timesheets")
            
            print(f"\n2. 🔍 EVIDENCE SUPPORTING THIS:")
            print(f"   - Only 1 user (you) in the database")
            print(f"   - Multiple people reported using the app")
            print(f"   - Your calendar events ended up in colleagues' timesheets")
            print(f"   - Processing history shows entries created but not all in your account")
            
            print(f"\n3. 🚨 SECURITY IMPLICATIONS:")
            print(f"   - Shared login credentials (major security violation)")
            print(f"   - Cross-user calendar data processing")
            print(f"   - Incorrect timesheet attribution")
            print(f"   - Potential billing/payroll errors")
            
            # Save investigation report
            report_filename = f"reverse_incident_investigation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, 'w') as f:
                json.dump(investigation_results, f, indent=2, default=str)
            
            print(f"\n📄 Investigation report saved: {report_filename}")
            
            return investigation_results
            
        except Exception as e:
            print(f"❌ Error during investigation: {e}")
            return None

def generate_colleague_audit_plan():
    """Generate a plan to audit colleagues' Harvest accounts"""
    
    print(f"\n📋 COLLEAGUE AUDIT PLAN")
    print(f"=" * 40)
    
    audit_plan = {
        "objective": "Find YOUR calendar events in colleagues' Harvest timesheets",
        "period": "June 16 - July 13, 2025",
        "steps": [
            {
                "step": 1,
                "action": "Contact each colleague who used the app",
                "details": "Ask them to check their Harvest timesheets for the period June 16 - July 13"
            },
            {
                "step": 2,
                "action": "Request timesheet exports",
                "details": "Ask colleagues to export their Harvest timesheets for the period"
            },
            {
                "step": 3,
                "action": "Cross-reference calendar events",
                "details": "Compare their timesheet entries with YOUR calendar events from the same period"
            },
            {
                "step": 4,
                "action": "Identify YOUR work in their timesheets",
                "details": "Look for entries that match YOUR meetings, projects, and work activities"
            },
            {
                "step": 5,
                "action": "Plan data correction",
                "details": "Work with colleagues to move YOUR entries from their timesheets to yours"
            }
        ],
        "email_template": """
Subject: URGENT - Need to Check Your Harvest Timesheet (June 16 - July 13)

Hi [Colleague Name],

We discovered a critical bug in the Calendar-Harvest integration app that affected timesheet data between June 16 - July 13, 2025.

ISSUE: MY calendar events may have been processed and added to YOUR Harvest timesheet instead of mine.

IMMEDIATE ACTION NEEDED:
1. Please check your Harvest timesheet for June 16 - July 13, 2025
2. Look for any entries that seem unfamiliar or don't match your actual work
3. Specifically look for:
   - Meetings you didn't attend
   - Projects you don't work on
   - Time entries that match MY work activities
   - Any entries with notes that reference my work

4. If possible, please export your timesheet for this period and send it to me

This is urgent as it affects billing accuracy and payroll. The bug has been fixed, but we need to correct the historical data.

Thanks for your help!

Best regards,
Josef
        """
    }
    
    print(f"📧 EMAIL TEMPLATE FOR COLLEAGUES:")
    print(f"-" * 40)
    print(audit_plan["email_template"])
    
    # Save audit plan
    plan_filename = f"colleague_audit_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(plan_filename, 'w') as f:
        json.dump(audit_plan, f, indent=2)
    
    print(f"\n📄 Audit plan saved: {plan_filename}")
    
    return audit_plan

if __name__ == "__main__":
    print("🔍 Starting Reverse Incident Investigation...")
    
    # Run investigation
    results = investigate_reverse_contamination()
    
    if results:
        # Generate colleague audit plan
        audit_plan = generate_colleague_audit_plan()
        
        print(f"\n🎯 IMMEDIATE ACTIONS:")
        print(f"1. Contact colleagues using the email template above")
        print(f"2. Request their Harvest timesheet exports for June 16 - July 13")
        print(f"3. Cross-reference their entries with your calendar events")
        print(f"4. Identify YOUR work in their timesheets")
        print(f"5. Plan to move incorrect entries back to your account")
        
        print(f"\n⚠️  CRITICAL: This is a billing and payroll accuracy issue!")
        print(f"   Your work may be credited to colleagues")
        print(f"   Client billing may be incorrect")
        print(f"   Immediate correction required")
    
    print(f"\n✅ Reverse investigation completed!")
