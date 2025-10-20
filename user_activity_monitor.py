#!/usr/bin/env python3
"""
User Activity Monitor for Calendar-Harvest Integration
Tracks user actions and detects potential security issues
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from dataclasses import dataclass, asdict
from flask import request, session, g

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db

@dataclass
class UserActivity:
    """User activity record"""
    user_id: int
    user_email: str
    action: str
    endpoint: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    success: bool
    details: Dict = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class ActivityMonitor:
    """Monitor and log user activities"""
    
    def __init__(self):
        self.activities: List[UserActivity] = []
        self.log_file = "user_activity.log"
        self.alert_file = "security_alerts.log"
    
    def log_activity(self, user_id: int, user_email: str, action: str, 
                    endpoint: str, success: bool = True, details: Dict = None):
        """Log user activity"""
        
        activity = UserActivity(
            user_id=user_id,
            user_email=user_email,
            action=action,
            endpoint=endpoint,
            timestamp=datetime.utcnow(),
            ip_address=request.remote_addr if request else "unknown",
            user_agent=request.headers.get('User-Agent', 'unknown') if request else "unknown",
            success=success,
            details=details or {}
        )
        
        self.activities.append(activity)
        self._write_to_log(activity)
        self._check_for_alerts(activity)
    
    def _write_to_log(self, activity: UserActivity):
        """Write activity to log file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(activity.to_dict()) + '\n')
        except Exception as e:
            print(f"Error writing to activity log: {e}")
    
    def _check_for_alerts(self, activity: UserActivity):
        """Check for suspicious activity patterns"""
        
        alerts = []
        
        # Check for rapid successive actions (potential automation/attack)
        recent_activities = [a for a in self.activities 
                           if a.user_id == activity.user_id 
                           and (activity.timestamp - a.timestamp).total_seconds() < 60]
        
        if len(recent_activities) > 10:
            alerts.append({
                "type": "RAPID_ACTIONS",
                "message": f"User {activity.user_email} performed {len(recent_activities)} actions in 1 minute",
                "severity": "MEDIUM"
            })
        
        # Check for failed authentication attempts
        if not activity.success and "auth" in activity.action.lower():
            recent_failures = [a for a in self.activities 
                             if a.user_id == activity.user_id 
                             and not a.success
                             and "auth" in a.action.lower()
                             and (activity.timestamp - a.timestamp).total_seconds() < 300]
            
            if len(recent_failures) > 3:
                alerts.append({
                    "type": "MULTIPLE_AUTH_FAILURES",
                    "message": f"User {activity.user_email} had {len(recent_failures)} auth failures in 5 minutes",
                    "severity": "HIGH"
                })
        
        # Check for cross-user data access attempts
        if "user_id" in str(activity.details) and activity.details:
            accessed_user_id = activity.details.get("accessed_user_id")
            if accessed_user_id and accessed_user_id != activity.user_id:
                alerts.append({
                    "type": "CROSS_USER_ACCESS",
                    "message": f"User {activity.user_email} (ID: {activity.user_id}) accessed data for user ID: {accessed_user_id}",
                    "severity": "CRITICAL"
                })
        
        # Write alerts to alert log
        for alert in alerts:
            self._write_alert(activity, alert)
    
    def _write_alert(self, activity: UserActivity, alert: Dict):
        """Write security alert to alert log"""
        try:
            alert_record = {
                "timestamp": activity.timestamp.isoformat(),
                "user_id": activity.user_id,
                "user_email": activity.user_email,
                "activity": activity.to_dict(),
                "alert": alert
            }
            
            with open(self.alert_file, 'a') as f:
                f.write(json.dumps(alert_record) + '\n')
                
            print(f"🚨 SECURITY ALERT: {alert['type']} - {alert['message']}")
            
        except Exception as e:
            print(f"Error writing security alert: {e}")
    
    def get_user_activity_summary(self, user_id: int, days: int = 7) -> Dict:
        """Get activity summary for a user"""
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        user_activities = [a for a in self.activities 
                          if a.user_id == user_id and a.timestamp > cutoff]
        
        if not user_activities:
            return {"message": "No recent activity found"}
        
        # Group by action
        action_counts = {}
        for activity in user_activities:
            action_counts[activity.action] = action_counts.get(activity.action, 0) + 1
        
        # Group by day
        daily_counts = {}
        for activity in user_activities:
            day = activity.timestamp.date().isoformat()
            daily_counts[day] = daily_counts.get(day, 0) + 1
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_activities": len(user_activities),
            "action_breakdown": action_counts,
            "daily_breakdown": daily_counts,
            "first_activity": min(user_activities, key=lambda a: a.timestamp).timestamp.isoformat(),
            "last_activity": max(user_activities, key=lambda a: a.timestamp).timestamp.isoformat()
        }
    
    def detect_anomalies(self) -> List[Dict]:
        """Detect anomalous user behavior patterns"""
        
        anomalies = []
        
        # Check for users with no recent activity but existing data
        from models import User, ProcessingHistory
        
        try:
            with app.app_context():
                users = User.query.all()
                
                for user in users:
                    # Check if user has processing history but no recent activity
                    has_history = ProcessingHistory.query.filter_by(user_id=user.id).first() is not None
                    
                    recent_activity = any(a.user_id == user.id 
                                        for a in self.activities 
                                        if (datetime.utcnow() - a.timestamp).days < 7)
                    
                    if has_history and not recent_activity:
                        anomalies.append({
                            "type": "INACTIVE_USER_WITH_DATA",
                            "user_id": user.id,
                            "user_email": user.email,
                            "message": f"User has processing history but no recent activity"
                        })
        
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
        
        return anomalies

# Global activity monitor instance
activity_monitor = ActivityMonitor()

def track_user_action(action: str, success: bool = True, details: Dict = None):
    """Decorator/function to track user actions"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Get user info from session
                user_id = session.get('user_id')
                user_email = session.get('user_email', 'unknown')
                endpoint = request.endpoint if request else func.__name__
                
                if user_id:
                    # Execute the function
                    try:
                        result = func(*args, **kwargs)
                        activity_monitor.log_activity(
                            user_id=user_id,
                            user_email=user_email,
                            action=action,
                            endpoint=endpoint,
                            success=True,
                            details=details
                        )
                        return result
                    except Exception as e:
                        activity_monitor.log_activity(
                            user_id=user_id,
                            user_email=user_email,
                            action=action,
                            endpoint=endpoint,
                            success=False,
                            details={"error": str(e)}
                        )
                        raise
                else:
                    # No user session - still execute but don't log
                    return func(*args, **kwargs)
                    
            except Exception as e:
                print(f"Error in activity tracking: {e}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def manual_log_activity(user_id: int, user_email: str, action: str, 
                       endpoint: str, success: bool = True, details: Dict = None):
    """Manually log an activity (for use in existing code)"""
    activity_monitor.log_activity(user_id, user_email, action, endpoint, success, details)

if __name__ == "__main__":
    # Test the monitoring system
    print("🔍 Testing User Activity Monitor...")
    
    # Simulate some activities
    test_activities = [
        (1, "user1@example.com", "LOGIN", "/auth/login", True),
        (1, "user1@example.com", "VIEW_DASHBOARD", "/", True),
        (1, "user1@example.com", "PROCESS_EVENTS", "/api/process", True),
        (2, "user2@example.com", "LOGIN", "/auth/login", True),
        (2, "user2@example.com", "VIEW_MAPPINGS", "/mappings", True),
    ]
    
    for user_id, email, action, endpoint, success in test_activities:
        activity_monitor.log_activity(user_id, email, action, endpoint, success)
    
    # Get summary
    summary = activity_monitor.get_user_activity_summary(1)
    print(f"📊 User 1 activity summary: {json.dumps(summary, indent=2)}")
    
    # Check for anomalies
    anomalies = activity_monitor.detect_anomalies()
    print(f"⚠️  Detected {len(anomalies)} anomalies")
    
    print("✅ Activity monitor test completed!")
