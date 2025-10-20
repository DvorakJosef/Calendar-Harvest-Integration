#!/usr/bin/env python3
"""
Minimal startup script that bypasses ALL security middleware
"""

import os
import sys

# Force environment variables
os.environ['PORT'] = '9000'
os.environ['FLASK_RUN_PORT'] = '9000'
os.environ['GOOGLE_REDIRECT_URI'] = 'http://127.0.0.1:9000/auth/callback'
os.environ['HARVEST_REDIRECT_URI'] = 'http://127.0.0.1:9000/auth/harvest/callback'

print("🚀 Starting MINIMAL Calendar-Harvest Integration...")
print("📍 URL: http://127.0.0.1:9000")
print("🔧 ALL SECURITY DISABLED for debugging")
print()

# Create a minimal Flask app without any security middleware
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
env = os.getenv('FLASK_ENV', 'development')
env_file = f'.env.{env}'
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded configuration from {env_file}")
else:
    load_dotenv('.env')
    print("Loaded configuration from .env")

# Import our custom modules
from models import db, User, ProjectMapping, UserConfig, ProcessingHistory
from google_calendar_service import GoogleCalendarService
from harvest_service import HarvestService
from mapping_engine import MappingEngine
from suggestion_engine import SuggestionEngine
from auth import auth_bp, login_required, get_current_user
from health_check import health_bp
from secrets_manager import get_flask_secret_key, get_database_url

# Create minimal app
app = Flask(__name__)

# Minimal configuration
app.config['SECRET_KEY'] = get_flask_secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# NO SECURITY MIDDLEWARE AT ALL
print("⚠️  CSRF Protection: DISABLED")
print("⚠️  Rate Limiting: DISABLED") 
print("⚠️  Security Headers: DISABLED")
print("⚠️  Input Validation: DISABLED")

# Initialize database
db.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)

# Initialize services
google_service = GoogleCalendarService()
harvest_service = HarvestService()
mapping_engine = MappingEngine()
suggestion_engine = SuggestionEngine()

print("✅ Minimal app configured")

# Add basic routes
@app.route('/')
def index():
    """Main dashboard page"""
    print(f"🌐 GET / - Session: {dict(session)}")
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('index.html')

@app.route('/setup')
@login_required
def setup():
    """Setup page for API credentials"""
    return render_template('setup.html')

# Add basic API endpoints for testing
@app.route('/api/google/status')
def google_status():
    """Google Calendar connection status"""
    print("🌐 GET /api/google/status")
    return jsonify({
        'success': True,
        'connected': False,
        'user_info': None,
        'needs_refresh': False
    })

@app.route('/api/harvest/status')
def harvest_status():
    """Harvest connection status"""
    print("🌐 GET /api/harvest/status")
    return jsonify({
        'success': True,
        'connected': False,
        'user_info': None
    })

@app.route('/api/harvest/oauth/status')
def harvest_oauth_status():
    """Harvest OAuth status"""
    print("🌐 GET /api/harvest/oauth/status")
    return jsonify({
        'success': True,
        'connected': False,
        'user_info': None
    })

# Add request logging
@app.before_request
def log_request():
    print(f"🌐 {request.method} {request.url}")
    print(f"📋 Headers: {dict(request.headers)}")

@app.after_request
def log_response(response):
    print(f"✅ {request.method} {request.url} -> {response.status_code}")
    if response.status_code >= 400:
        print(f"❌ Error: {response.get_data(as_text=True)[:200]}")
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("🎯 Starting minimal Flask server...")
    app.run(debug=True, port=9000, host='127.0.0.1')
