#!/usr/bin/env python3
"""
Minimal version of main.py to isolate the 415 error
This copies the exact structure of main.py but with minimal routes
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables EXACTLY like main.py
env = os.getenv('FLASK_ENV', 'development')
env_file = f'.env.{env}'
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded configuration from {env_file}")
else:
    load_dotenv('.env')
    print("Loaded configuration from .env")

# Import modules EXACTLY like main.py with error handling
try:
    from models import db, User, ProjectMapping, UserConfig, ProcessingHistory
    print("✅ Models imported")
except Exception as e:
    print(f"❌ Models import error: {e}")

try:
    from google_calendar_service import GoogleCalendarService
    print("✅ Google Calendar service imported")
except Exception as e:
    print(f"❌ Google Calendar service error: {e}")

try:
    from harvest_service import HarvestService
    print("✅ Harvest service imported")
except Exception as e:
    print(f"❌ Harvest service error: {e}")

try:
    from mapping_engine import MappingEngine
    print("✅ Mapping engine imported")
except Exception as e:
    print(f"❌ Mapping engine error: {e}")

try:
    from suggestion_engine import SuggestionEngine
    print("✅ Suggestion engine imported")
except Exception as e:
    print(f"❌ Suggestion engine error: {e}")

try:
    from auth import auth_bp, login_required, get_current_user
    print("✅ Auth module imported")
except Exception as e:
    print(f"❌ Auth module error: {e}")

try:
    from health_check import health_bp
    print("✅ Health check imported")
except Exception as e:
    print(f"❌ Health check error: {e}")

try:
    from validation import (
        validate_json, MappingSchema, ProcessingSchema, PatternRuleSchema,
        BulkAssignmentSchema, ImportDataSchema, validate_user_id,
        validate_date_range, validate_harvest_ids, SecurityValidationError
    )
    print("✅ Validation module imported")
except Exception as e:
    print(f"❌ Validation module error: {e}")

try:
    from secrets_manager import get_flask_secret_key, get_database_url, validate_configuration
    print("✅ Secrets manager imported")
except Exception as e:
    print(f"❌ Secrets manager error: {e}")

app = Flask(__name__)

# EXACT configuration from main.py
app.config['SECRET_KEY'] = get_flask_secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Validate configuration EXACTLY like main.py
config_validation = validate_configuration()
if not config_validation['valid']:
    print("⚠️  Configuration validation warnings:")
    if config_validation['missing_secrets']:
        print(f"   Missing secrets: {config_validation['missing_secrets']}")
    if config_validation['weak_secrets']:
        print(f"   Weak secrets: {config_validation['weak_secrets']}")
    if os.getenv('FLASK_ENV') == 'production':
        print("🚨 Production deployment with invalid configuration!")
else:
    print("✅ Configuration validation passed")

print(f"🔐 Using Secret Manager: {config_validation['using_secret_manager']}")

# Session configuration EXACTLY like main.py
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Initialize database EXACTLY like main.py
db.init_app(app)

# Initialize CSRF protection EXACTLY like main.py
csrf = CSRFProtect(app)

# Initialize rate limiting EXACTLY like main.py
def get_user_id():
    """Get user ID for rate limiting"""
    return session.get('user_id', get_remote_address())

limiter = Limiter(
    app=app,
    key_func=get_user_id,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Initialize security headers EXACTLY like main.py
csp = {
    'default-src': "'self'",
    'script-src': [
        "'self'",
        "'unsafe-inline'",  # Needed for Bootstrap and inline scripts
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com"
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",  # Needed for Bootstrap and inline styles
        "https://cdn.jsdelivr.net",
        "https://fonts.googleapis.com"
    ],
    'font-src': [
        "'self'",
        "https://cdn.jsdelivr.net",
        "https://fonts.gstatic.com"
    ],
    'img-src': [
        "'self'",
        "data:",
        "https:"
    ],
    'connect-src': [
        "'self'",
        "https://accounts.google.com",
        "https://oauth2.googleapis.com",
        "https://www.googleapis.com",
        "https://id.getharvest.com",
        "https://api.harvestapp.com"
    ]
}

talisman = Talisman(
    app,
    force_https=os.getenv('FLASK_ENV') == 'production',
    strict_transport_security=True,
    content_security_policy=csp,
    content_security_policy_nonce_in=['script-src', 'style-src'],
    feature_policy={
        'geolocation': "'none'",
        'camera': "'none'",
        'microphone': "'none'"
    }
)

# Make CSRF token available in templates EXACTLY like main.py
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)

# Register blueprints EXACTLY like main.py
app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)

# Initialize services EXACTLY like main.py
google_service = GoogleCalendarService()
harvest_service = HarvestService()
mapping_engine = MappingEngine()
suggestion_engine = SuggestionEngine()

# Initialize activity monitoring EXACTLY like main.py
try:
    from user_activity_monitor import activity_monitor, manual_log_activity
    MONITORING_ENABLED = True
    print("✅ User activity monitoring enabled")
except ImportError:
    MONITORING_ENABLED = False
    print("⚠️  User activity monitoring not available")

# MINIMAL ROUTES - Just the basic ones
@app.route('/')
def index():
    """Main dashboard page"""
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('index.html')

@app.route('/setup')
@login_required
def setup():
    """Setup page for API credentials"""
    return render_template('setup.html')

@app.route('/mappings')
@login_required
def mappings():
    """Project mappings configuration page"""
    return render_template('mappings.html', mappings=[])

@app.route('/process')
@login_required
def process():
    """Week selection and processing page"""
    return render_template('process.html')

@app.route('/preview')
@login_required
def preview():
    """Preview page for manual timesheet review"""
    return render_template('preview.html')

# Add basic API endpoints
@app.route('/api/google/status')
def google_status():
    """Google Calendar connection status"""
    return jsonify({
        'connected': False,
        'user_info': None,
        'needs_refresh': False
    })

@app.route('/api/harvest/status')
def harvest_status():
    """Harvest connection status"""
    return jsonify({
        'connected': False,
        'user_info': None
    })

@app.route('/api/harvest/oauth/status')
def harvest_oauth_status():
    """Harvest OAuth status"""
    return jsonify({
        'connected': False,
        'user_info': None
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Force port 9003 to avoid conflicts
    port = 9003
    print(f"🎯 Starting minimal main app on port {port}...")
    app.run(debug=True, port=port, host='127.0.0.1')
