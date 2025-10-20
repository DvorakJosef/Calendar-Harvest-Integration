#!/usr/bin/env python3
"""
Prevention Options for Calendar-Harvest Integration
Multiple security and testing approaches to prevent future incidents
"""

import sys
import os
from datetime import datetime, date
import json
from typing import Dict, List, Optional

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import db, User, UserConfig
from harvest_service import HarvestService

class PreviewMode:
    """
    Manual Review System - Preview timesheet entries before sending to Harvest
    """
    
    def __init__(self):
        self.preview_entries = []
        self.preview_file = "timesheet_preview.json"
    
    def add_preview_entry(self, user_id: int, user_email: str, entry_data: Dict):
        """Add an entry to preview queue"""
        
        preview_entry = {
            "preview_id": f"preview_{len(self.preview_entries) + 1}",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "harvest_entry": entry_data,
            "status": "PENDING_REVIEW",
            "approved": False,
            "notes": ""
        }
        
        self.preview_entries.append(preview_entry)
        self._save_preview_file()
        
        print(f"📋 PREVIEW: Added entry for review - {entry_data['project_name']} ({entry_data['hours']}h)")
        return preview_entry["preview_id"]
    
    def _save_preview_file(self):
        """Save preview entries to file"""
        try:
            with open(self.preview_file, 'w') as f:
                json.dump(self.preview_entries, f, indent=2)
        except Exception as e:
            print(f"Error saving preview file: {e}")
    
    def load_preview_entries(self):
        """Load preview entries from file"""
        try:
            if os.path.exists(self.preview_file):
                with open(self.preview_file, 'r') as f:
                    self.preview_entries = json.load(f)
        except Exception as e:
            print(f"Error loading preview file: {e}")
    
    def get_pending_reviews(self, user_id: int = None) -> List[Dict]:
        """Get entries pending review"""
        pending = [e for e in self.preview_entries if e["status"] == "PENDING_REVIEW"]
        
        if user_id:
            pending = [e for e in pending if e["user_id"] == user_id]
        
        return pending
    
    def approve_entry(self, preview_id: str, approved: bool, notes: str = ""):
        """Approve or reject a preview entry"""
        
        for entry in self.preview_entries:
            if entry["preview_id"] == preview_id:
                entry["approved"] = approved
                entry["status"] = "APPROVED" if approved else "REJECTED"
                entry["notes"] = notes
                entry["reviewed_at"] = datetime.now().isoformat()
                break
        
        self._save_preview_file()
        return approved
    
    def execute_approved_entries(self, user_id: int) -> Dict:
        """Execute all approved entries for a user"""
        
        approved_entries = [e for e in self.preview_entries 
                          if e["user_id"] == user_id and e["status"] == "APPROVED"]
        
        results = {
            "total_approved": len(approved_entries),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        harvest_service = HarvestService()
        
        for entry in approved_entries:
            try:
                harvest_entry = entry["harvest_entry"]
                
                # Execute the actual Harvest API call
                result, error = harvest_service.create_time_entry(
                    project_id=harvest_entry["project_id"],
                    task_id=harvest_entry["task_id"],
                    spent_date=date.fromisoformat(harvest_entry["spent_date"]),
                    hours=harvest_entry["hours"],
                    notes=harvest_entry["notes"],
                    user_id=user_id
                )
                
                if result:
                    entry["status"] = "EXECUTED"
                    entry["harvest_id"] = result["id"]
                    entry["executed_at"] = datetime.now().isoformat()
                    results["successful"] += 1
                    print(f"✅ Executed: {harvest_entry['project_name']} ({harvest_entry['hours']}h)")
                else:
                    entry["status"] = "FAILED"
                    entry["error"] = error
                    results["failed"] += 1
                    results["errors"].append(f"Failed to create entry: {error}")
                    print(f"❌ Failed: {harvest_entry['project_name']} - {error}")
                
            except Exception as e:
                entry["status"] = "FAILED"
                entry["error"] = str(e)
                results["failed"] += 1
                results["errors"].append(f"Exception: {str(e)}")
                print(f"❌ Exception: {str(e)}")
        
        self._save_preview_file()
        return results

def analyze_oauth2_benefits():
    """Analyze benefits of switching to OAuth 2 for Harvest authentication"""
    
    print("🔐 HARVEST OAUTH 2 ANALYSIS")
    print("=" * 50)
    
    oauth2_analysis = {
        "current_method": "Personal Access Token",
        "proposed_method": "OAuth 2.0",
        "benefits": [
            {
                "benefit": "Individual User Authentication",
                "description": "Each user authenticates with their own Harvest account",
                "security_impact": "CRITICAL - Eliminates shared credentials",
                "implementation": "Users log in with their own Harvest credentials"
            },
            {
                "benefit": "Automatic User Isolation",
                "description": "OAuth tokens are tied to specific Harvest users",
                "security_impact": "HIGH - Impossible to access wrong account",
                "implementation": "Token automatically identifies the correct Harvest user"
            },
            {
                "benefit": "Revocable Access",
                "description": "Users can revoke app access from their Harvest account",
                "security_impact": "MEDIUM - Better access control",
                "implementation": "Standard OAuth revocation process"
            },
            {
                "benefit": "Audit Trail",
                "description": "Harvest logs show which user authorized each action",
                "security_impact": "HIGH - Complete accountability",
                "implementation": "Built into Harvest's OAuth system"
            },
            {
                "benefit": "No Shared Secrets",
                "description": "No need to share personal access tokens",
                "security_impact": "CRITICAL - Eliminates credential sharing",
                "implementation": "Each user has their own OAuth flow"
            }
        ],
        "implementation_steps": [
            "Register OAuth application with Harvest",
            "Implement OAuth 2.0 flow in the application",
            "Update user authentication to use OAuth tokens",
            "Migrate existing users to OAuth authentication",
            "Remove personal access token support"
        ],
        "security_improvements": [
            "✅ Each user authenticates individually",
            "✅ Impossible to use wrong credentials",
            "✅ Built-in user isolation",
            "✅ Revocable access control",
            "✅ Complete audit trail",
            "✅ No credential sharing possible"
        ]
    }
    
    print("📊 CURRENT vs PROPOSED:")
    print(f"   Current: {oauth2_analysis['current_method']}")
    print(f"   Proposed: {oauth2_analysis['proposed_method']}")
    
    print("\n🎯 KEY BENEFITS:")
    for i, benefit in enumerate(oauth2_analysis["benefits"], 1):
        print(f"   {i}. {benefit['benefit']}")
        print(f"      Impact: {benefit['security_impact']}")
        print(f"      Details: {benefit['description']}")
        print()
    
    print("🔒 SECURITY IMPROVEMENTS:")
    for improvement in oauth2_analysis["security_improvements"]:
        print(f"   {improvement}")
    
    return oauth2_analysis

def create_testing_framework():
    """Create comprehensive testing framework for user isolation"""
    
    print("\n🧪 TESTING FRAMEWORK FOR USER ISOLATION")
    print("=" * 50)
    
    testing_framework = {
        "test_categories": [
            {
                "category": "Authentication Testing",
                "tests": [
                    "Verify each user can only access their own data",
                    "Test cross-user access attempts are blocked",
                    "Validate session isolation between users",
                    "Confirm logout clears user context properly"
                ]
            },
            {
                "category": "Timesheet Operation Testing",
                "tests": [
                    "Verify timesheet entries are created in correct account",
                    "Test that user A cannot create entries for user B",
                    "Validate Harvest API calls use correct credentials",
                    "Confirm entry ownership matches authenticated user"
                ]
            },
            {
                "category": "Data Isolation Testing",
                "tests": [
                    "Verify database queries filter by user_id",
                    "Test that users cannot see each other's data",
                    "Validate suggestion engine uses only user's data",
                    "Confirm project mappings are user-specific"
                ]
            },
            {
                "category": "Preview Mode Testing",
                "tests": [
                    "Verify preview entries are user-isolated",
                    "Test approval workflow works correctly",
                    "Validate execution only processes approved entries",
                    "Confirm preview data matches actual execution"
                ]
            }
        ],
        "automated_tests": [
            "Unit tests for user isolation functions",
            "Integration tests for multi-user scenarios",
            "API tests for cross-user access prevention",
            "End-to-end tests for complete workflows"
        ],
        "manual_tests": [
            "Multi-user login testing",
            "Cross-browser session isolation",
            "Harvest account verification",
            "Preview mode validation"
        ]
    }
    
    print("📋 TEST CATEGORIES:")
    for category in testing_framework["test_categories"]:
        print(f"\n   {category['category']}:")
        for test in category["tests"]:
            print(f"      - {test}")
    
    return testing_framework

def generate_prevention_recommendations():
    """Generate comprehensive prevention recommendations"""
    
    print("\n🛡️ COMPREHENSIVE PREVENTION RECOMMENDATIONS")
    print("=" * 60)
    
    recommendations = {
        "immediate_actions": [
            {
                "priority": "CRITICAL",
                "action": "Implement Preview Mode",
                "description": "Add manual review step before sending to Harvest",
                "timeline": "This week",
                "effort": "Medium"
            },
            {
                "priority": "HIGH",
                "action": "Switch to OAuth 2.0",
                "description": "Replace personal access tokens with OAuth authentication",
                "timeline": "Next 2 weeks",
                "effort": "High"
            },
            {
                "priority": "HIGH",
                "action": "Implement User Registration",
                "description": "Force each user to create their own account",
                "timeline": "Next week",
                "effort": "Medium"
            }
        ],
        "medium_term_actions": [
            {
                "priority": "MEDIUM",
                "action": "Comprehensive Testing Suite",
                "description": "Automated tests for user isolation",
                "timeline": "Next month",
                "effort": "High"
            },
            {
                "priority": "MEDIUM",
                "action": "Enhanced Monitoring",
                "description": "Real-time alerts for security violations",
                "timeline": "Next 2 weeks",
                "effort": "Medium"
            },
            {
                "priority": "LOW",
                "action": "Security Audit Schedule",
                "description": "Regular security reviews",
                "timeline": "Ongoing",
                "effort": "Low"
            }
        ],
        "technical_implementations": [
            "Preview mode with manual approval",
            "OAuth 2.0 authentication flow",
            "Individual user registration system",
            "Enhanced user isolation testing",
            "Real-time security monitoring",
            "Comprehensive audit logging"
        ]
    }
    
    print("🚨 IMMEDIATE ACTIONS (This Week):")
    for action in recommendations["immediate_actions"]:
        print(f"   {action['priority']}: {action['action']}")
        print(f"      {action['description']}")
        print(f"      Timeline: {action['timeline']} | Effort: {action['effort']}")
        print()
    
    print("📅 MEDIUM-TERM ACTIONS:")
    for action in recommendations["medium_term_actions"]:
        print(f"   {action['priority']}: {action['action']}")
        print(f"      {action['description']}")
        print(f"      Timeline: {action['timeline']} | Effort: {action['effort']}")
        print()
    
    return recommendations

if __name__ == "__main__":
    print("🛡️ PREVENTION OPTIONS ANALYSIS")
    print("=" * 60)
    
    # 1. Analyze OAuth 2 benefits
    oauth_analysis = analyze_oauth2_benefits()
    
    # 2. Create testing framework
    testing_framework = create_testing_framework()
    
    # 3. Generate recommendations
    recommendations = generate_prevention_recommendations()
    
    # 4. Test preview mode
    print("\n🧪 TESTING PREVIEW MODE:")
    preview = PreviewMode()
    
    # Simulate adding a preview entry
    test_entry = {
        "project_id": 12345,
        "project_name": "Test Project",
        "task_id": 67890,
        "task_name": "Development",
        "spent_date": "2025-07-16",
        "hours": 2.5,
        "notes": "Test entry for preview mode"
    }
    
    preview_id = preview.add_preview_entry(1, "test@example.com", test_entry)
    print(f"   Created preview entry: {preview_id}")
    
    pending = preview.get_pending_reviews(1)
    print(f"   Pending reviews: {len(pending)}")
    
    print("\n✅ Prevention options analysis completed!")
    print("\n🎯 NEXT STEPS:")
    print("1. Implement preview mode for manual review")
    print("2. Switch to OAuth 2.0 authentication")
    print("3. Create individual user registration")
    print("4. Implement comprehensive testing")
    print("5. Deploy enhanced monitoring")
