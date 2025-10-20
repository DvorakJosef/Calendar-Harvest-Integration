"""
Database models for Calendar-Harvest integration
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    """User model for multi-user support with Google OAuth"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    picture = db.Column(db.String(500))  # Profile picture URL
    domain = db.Column(db.String(255))  # Google Workspace domain
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    project_mappings = db.relationship('ProjectMapping', backref='user', lazy=True, cascade='all, delete-orphan')
    user_configs = db.relationship('UserConfig', backref='user', lazy=True, cascade='all, delete-orphan')
    processing_history = db.relationship('ProcessingHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    recurring_mappings = db.relationship('RecurringEventMapping', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self):
        return {
            'id': self.id,
            'google_id': self.google_id,
            'email': self.email,
            'name': self.name,
            'picture': self.picture,
            'domain': self.domain,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat(),
            'is_active': self.is_active
        }

class ProjectMapping(db.Model):
    """Maps calendar event labels to Harvest projects and tasks"""
    __tablename__ = 'project_mappings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    calendar_label = db.Column(db.String(255), nullable=False)
    harvest_project_id = db.Column(db.Integer, nullable=False)
    harvest_project_name = db.Column(db.String(255), nullable=False)
    harvest_task_id = db.Column(db.Integer, nullable=False)
    harvest_task_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<ProjectMapping {self.calendar_label} -> {self.harvest_project_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'calendar_label': self.calendar_label,
            'harvest_project_id': self.harvest_project_id,
            'harvest_project_name': self.harvest_project_name,
            'harvest_task_id': self.harvest_task_id,
            'harvest_task_name': self.harvest_task_name,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class UserConfig(db.Model):
    """Stores user configuration and API credentials"""
    __tablename__ = 'user_config'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    google_credentials = db.Column(db.Text)  # JSON string of OAuth credentials

    # Legacy fields kept for database compatibility but not used
    harvest_access_token = db.Column(db.String(255))  # DEPRECATED - OAuth only
    harvest_account_id = db.Column(db.String(255))    # Still used for OAuth account ID

    # New Harvest OAuth 2.0 Authentication
    harvest_oauth_token = db.Column(db.Text)  # JSON string of OAuth token data
    harvest_refresh_token = db.Column(db.String(255))
    harvest_token_expires_at = db.Column(db.DateTime)
    harvest_user_id = db.Column(db.Integer)  # Harvest user ID
    harvest_user_email = db.Column(db.String(255))  # Harvest user email
    harvest_account_name = db.Column(db.String(255))  # Harvest account name

    default_task_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_google_credentials(self, credentials_dict):
        """Store Google OAuth credentials as JSON"""
        self.google_credentials = json.dumps(credentials_dict)
    
    def get_google_credentials(self):
        """Retrieve Google OAuth credentials as dict"""
        if self.google_credentials:
            return json.loads(self.google_credentials)
        return None

    def set_harvest_oauth_token(self, token_data):
        """Store Harvest OAuth token data as JSON"""
        self.harvest_oauth_token = json.dumps(token_data)

        # Extract and store key fields for easy access
        if 'refresh_token' in token_data:
            self.harvest_refresh_token = token_data['refresh_token']

        if 'expires_at' in token_data:
            from datetime import datetime
            self.harvest_token_expires_at = datetime.fromtimestamp(token_data['expires_at'])

        if 'harvest_user_id' in token_data:
            self.harvest_user_id = token_data['harvest_user_id']

        if 'harvest_user_email' in token_data:
            self.harvest_user_email = token_data['harvest_user_email']

        if 'harvest_account_name' in token_data:
            self.harvest_account_name = token_data['harvest_account_name']

        # Update harvest_account_id for compatibility
        if 'harvest_account_id' in token_data:
            self.harvest_account_id = str(token_data['harvest_account_id'])

    def get_harvest_oauth_token(self):
        """Retrieve Harvest OAuth token data as dict"""
        if self.harvest_oauth_token:
            return json.loads(self.harvest_oauth_token)
        return None

    def is_harvest_oauth_configured(self):
        """Check if user has Harvest OAuth configured"""
        return bool(self.harvest_oauth_token and self.harvest_user_id)

    def is_harvest_token_valid(self):
        """Check if Harvest OAuth token is still valid"""
        if not self.harvest_oauth_token:
            return False

        # Check expiration if available
        if self.harvest_token_expires_at:
            from datetime import datetime
            if datetime.utcnow() >= self.harvest_token_expires_at:
                return False

        return True

    def has_harvest_credentials(self):
        """Check if user has Harvest OAuth credentials"""
        return self.is_harvest_oauth_configured()

    def get_harvest_auth_method(self):
        """Get the current Harvest authentication method (OAuth only)"""
        if self.is_harvest_oauth_configured():
            return 'oauth'
        else:
            return None

    def clear_harvest_oauth(self):
        """Clear all Harvest OAuth data"""
        self.harvest_oauth_token = None
        self.harvest_refresh_token = None
        self.harvest_token_expires_at = None
        self.harvest_user_id = None
        self.harvest_user_email = None
        self.harvest_account_name = None

    def __repr__(self):
        return f'<UserConfig {self.id}>'

class ProcessingHistory(db.Model):
    """Tracks processed calendar events to prevent duplicates"""
    __tablename__ = 'processing_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    week_start_date = db.Column(db.Date, nullable=False)
    calendar_event_id = db.Column(db.String(255), nullable=False)
    calendar_event_summary = db.Column(db.String(500))
    harvest_time_entry_id = db.Column(db.Integer)
    harvest_project_id = db.Column(db.Integer)
    harvest_task_id = db.Column(db.Integer)
    hours_logged = db.Column(db.Float)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='success')  # success, error, skipped
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ProcessingHistory {self.calendar_event_id} -> {self.harvest_time_entry_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'week_start_date': self.week_start_date.isoformat(),
            'calendar_event_id': self.calendar_event_id,
            'calendar_event_summary': self.calendar_event_summary,
            'harvest_time_entry_id': self.harvest_time_entry_id,
            'harvest_project_id': self.harvest_project_id,
            'harvest_task_id': self.harvest_task_id,
            'hours_logged': self.hours_logged,
            'processed_at': self.processed_at.isoformat(),
            'status': self.status,
            'error_message': self.error_message
        }

class RecurringEventMapping(db.Model):
    """Store permanent mappings for recurring events"""
    __tablename__ = 'recurring_event_mappings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recurring_event_id = db.Column(db.String(255), nullable=False)  # Base recurring event ID (unique per user)
    event_summary = db.Column(db.String(500), nullable=False)  # Event title for display
    event_pattern = db.Column(db.String(1000))  # Recurrence pattern description
    harvest_project_id = db.Column(db.Integer, nullable=False)
    harvest_project_name = db.Column(db.String(255), nullable=False)
    harvest_task_id = db.Column(db.Integer, nullable=False)
    harvest_task_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Unique constraint per user
    __table_args__ = (db.UniqueConstraint('user_id', 'recurring_event_id', name='_user_recurring_event_uc'),)

    def __repr__(self):
        return f'<RecurringEventMapping {self.event_summary} -> {self.harvest_project_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'recurring_event_id': self.recurring_event_id,
            'event_summary': self.event_summary,
            'event_pattern': self.event_pattern,
            'harvest_project_id': self.harvest_project_id,
            'harvest_project_name': self.harvest_project_name,
            'harvest_task_id': self.harvest_task_id,
            'harvest_task_name': self.harvest_task_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }

class TimesheetPreview(db.Model):
    """Store timesheet entries for manual review before sending to Harvest"""
    __tablename__ = 'timesheet_preview'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Timesheet entry data
    project_id = db.Column(db.Integer, nullable=False)
    project_name = db.Column(db.String(255), nullable=False)
    task_id = db.Column(db.Integer, nullable=False)
    task_name = db.Column(db.String(255), nullable=False)
    spent_date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)

    # Review status
    status = db.Column(db.String(50), nullable=False, default='pending')  # pending, approved, rejected, executed
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)

    # Execution tracking
    harvest_entry_id = db.Column(db.Integer)
    executed_at = db.Column(db.DateTime)
    execution_error = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('preview_entries', lazy=True))
    approver = db.relationship('User', foreign_keys=[approved_by])

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'project_id': self.project_id,
            'project_name': self.project_name,
            'task_id': self.task_id,
            'task_name': self.task_name,
            'spent_date': self.spent_date.isoformat() if self.spent_date else None,
            'hours': self.hours,
            'notes': self.notes,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'review_notes': self.review_notes,
            'harvest_entry_id': self.harvest_entry_id,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_error': self.execution_error
        }

    def __repr__(self):
        return f'<TimesheetPreview {self.id}: {self.project_name} ({self.hours}h) - {self.status}>'
