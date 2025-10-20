#!/usr/bin/env python3
"""
Test the EXACT configuration from main.py to find what causes 415 error
This copies the exact Flask app setup from main.py
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

# Import modules EXACTLY like main.py
from models import db, User, ProjectMapping, UserConfig, ProcessingHistory
from google_calendar_service import GoogleCalendarService
from harvest_service import HarvestService
from mapping_engine import MappingEngine
from suggestion_engine import SuggestionEngine
from auth import auth_bp, login_required, get_current_user
from health_check import health_bp
from validation import (
    validate_json, MappingSchema, ProcessingSchema, PatternRuleSchema,
    BulkAssignmentSchema, ImportDataSchema, validate_user_id,
    validate_date_range, validate_harvest_ids, SecurityValidationError
)
from secrets_manager import get_flask_secret_key, get_database_url, validate_configuration

print("🧪 CONFIG TESTER - Using EXACT main.py configuration...")
print("📍 URL: http://127.0.0.1:5555")

# Create Flask app EXACTLY like main.py
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
print("✅ Database initialized")

# Initialize CSRF protection EXACTLY like main.py
csrf = CSRFProtect(app)
print("✅ CSRF protection initialized")

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
print("✅ Rate limiting initialized")

# Initialize security headers EXACTLY like main.py
csp = {
    'default-src': "'self'",
    'script-src': [
        "'self'",
        "'unsafe-inline'",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com"
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",
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
print("✅ Talisman security headers initialized")

# Make CSRF token available in templates EXACTLY like main.py
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)
print("✅ CSRF context processor added")

# Register blueprints EXACTLY like main.py
app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)
print("✅ Blueprints registered")

# Initialize services EXACTLY like main.py
google_service = GoogleCalendarService()
harvest_service = HarvestService()
mapping_engine = MappingEngine()
suggestion_engine = SuggestionEngine()
print("✅ Services initialized")

# Initialize activity monitoring EXACTLY like main.py
try:
    from user_activity_monitor import activity_monitor, manual_log_activity
    MONITORING_ENABLED = True
    print("✅ User activity monitoring enabled")
except ImportError:
    MONITORING_ENABLED = False
    print("⚠️  User activity monitoring not available")

print("\n🎯 Configuration complete. Testing routes...")

# MINIMAL ROUTES - Just test basic functionality
@app.route('/')
def index():
    """Main page"""
    return """
    <html>
    <head><title>Config Tester</title></head>
    <body>
        <h1>🧪 Config Tester</h1>
        <p>Using EXACT main.py configuration</p>
        <p><a href="/test-api">Test API</a></p>
    </body>
    </html>
    """

@app.route('/test-api')
def test_api():
    """Test API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Config tester API working!',
        'csrf_enabled': app.config.get('WTF_CSRF_ENABLED', True),
        'testing_mode': app.config.get('TESTING', False)
    })

# Add request logging
@app.before_request
def log_request():
    print(f"🌐 {request.method} {request.url}")

@app.after_request
def log_response(response):
    print(f"✅ {request.method} {request.url} -> {response.status_code}")
    if response.status_code >= 400:
        print(f"❌ Error: {response.get_data(as_text=True)[:200]}")
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("🎯 Starting config tester on port 5555...")
    app.run(debug=True, port=5555, host='127.0.0.1')
