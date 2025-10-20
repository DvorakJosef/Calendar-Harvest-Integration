#!/usr/bin/env python3
"""
Systematic import tester to find which import causes the 415 error
We'll add imports one by one from main.py
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv

# Load environment variables
env = os.getenv('FLASK_ENV', 'development')
env_file = f'.env.{env}'
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded configuration from {env_file}")

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'import-test-key-12345'

print("🧪 IMPORT TESTER - Adding imports step by step...")
print("📍 URL: http://127.0.0.1:7777")

# STEP 1: Add Flask-WTF imports
try:
    from flask_wtf.csrf import CSRFProtect
    print("✅ STEP 1: Flask-WTF imported successfully")
except Exception as e:
    print(f"❌ STEP 1: Flask-WTF import error: {e}")

# STEP 2: Add Flask-Limiter imports  
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    print("✅ STEP 2: Flask-Limiter imported successfully")
except Exception as e:
    print(f"❌ STEP 2: Flask-Limiter import error: {e}")

# STEP 3: Add Flask-Talisman imports
try:
    from flask_talisman import Talisman
    print("✅ STEP 3: Flask-Talisman imported successfully")
except Exception as e:
    print(f"❌ STEP 3: Flask-Talisman import error: {e}")

# STEP 4: Add models import
try:
    from models import db, User, ProjectMapping, UserConfig, ProcessingHistory
    print("✅ STEP 4: Models imported successfully")
except Exception as e:
    print(f"❌ STEP 4: Models import error: {e}")

# STEP 5: Add secrets manager import
try:
    from secrets_manager import get_flask_secret_key, get_database_url, validate_configuration
    print("✅ STEP 5: Secrets manager imported successfully")
except Exception as e:
    print(f"❌ STEP 5: Secrets manager import error: {e}")

# STEP 6: Add validation import (SUSPECT!)
try:
    from validation import (
        validate_json, MappingSchema, ProcessingSchema, PatternRuleSchema,
        BulkAssignmentSchema, ImportDataSchema, validate_user_id,
        validate_date_range, validate_harvest_ids, SecurityValidationError
    )
    print("✅ STEP 6: Validation module imported successfully")
except Exception as e:
    print(f"❌ STEP 6: Validation module import error: {e}")

# STEP 7: Add auth import
try:
    from auth import auth_bp, login_required, get_current_user
    print("✅ STEP 7: Auth module imported successfully")
except Exception as e:
    print(f"❌ STEP 7: Auth module import error: {e}")

# STEP 8: Add health check import
try:
    from health_check import health_bp
    print("✅ STEP 8: Health check imported successfully")
except Exception as e:
    print(f"❌ STEP 8: Health check import error: {e}")

# STEP 9: Add service imports
try:
    from google_calendar_service import GoogleCalendarService
    from harvest_service import HarvestService
    from mapping_engine import MappingEngine
    from suggestion_engine import SuggestionEngine
    print("✅ STEP 9: Service classes imported successfully")
except Exception as e:
    print(f"❌ STEP 9: Service classes import error: {e}")

# STEP 10: Add user activity monitor import
try:
    from user_activity_monitor import activity_monitor, manual_log_activity
    print("✅ STEP 10: User activity monitor imported successfully")
except Exception as e:
    print(f"❌ STEP 10: User activity monitor import error: {e}")

print("\n🎯 All imports completed. Testing basic routes...")

# Basic routes
@app.route('/')
def index():
    """Main page"""
    return """
    <html>
    <head><title>Import Tester</title></head>
    <body>
        <h1>🧪 Import Tester</h1>
        <p>If you see this, all imports are working!</p>
        <p><a href="/test-api">Test API</a></p>
    </body>
    </html>
    """

@app.route('/test-api')
def test_api():
    """Test API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Import tester API working!',
        'all_imports': 'successful'
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
    print("🎯 Starting import tester on port 7777...")
    app.run(debug=True, port=7777, host='127.0.0.1')
