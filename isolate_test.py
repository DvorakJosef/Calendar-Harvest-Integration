#!/usr/bin/env python3
"""
Test script to isolate which import is causing the 415 error
"""

import os
from flask import Flask, render_template

# Set environment
os.environ['PORT'] = '9002'
os.environ['FLASK_RUN_PORT'] = '9002'
os.environ['GOOGLE_REDIRECT_URI'] = 'http://127.0.0.1:9002/auth/callback'
os.environ['HARVEST_REDIRECT_URI'] = 'http://127.0.0.1:9002/auth/harvest/callback'

# Load environment variables
from dotenv import load_dotenv
env = os.getenv('FLASK_ENV', 'development')
env_file = f'.env.{env}'
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded configuration from {env_file}")

app = Flask(__name__)

# Basic configuration
from secrets_manager import get_flask_secret_key, get_database_url
app.config['SECRET_KEY'] = get_flask_secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add session configuration like main app
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

print("✅ Basic Flask app created")

# Test 1: Add database
try:
    from models import db
    db.init_app(app)
    print("✅ Database initialized")
except Exception as e:
    print(f"❌ Database error: {e}")

# Test 2: Add CSRF (this might be the culprit)
try:
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect(app)
    print("✅ CSRF initialized")
except Exception as e:
    print(f"❌ CSRF error: {e}")

# Test 3: Add Rate Limiting (another suspect)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from flask import session
    
    def get_user_id():
        return session.get('user_id', get_remote_address())
    
    limiter = Limiter(
        app=app,
        key_func=get_user_id,
        default_limits=["1000 per hour", "100 per minute"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    print("✅ Rate limiting initialized")
except Exception as e:
    print(f"❌ Rate limiting error: {e}")

# Test 4: Add Talisman (security headers)
try:
    from flask_talisman import Talisman
    csp = {
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"]
    }
    talisman = Talisman(
        app,
        force_https=False,
        content_security_policy=csp
    )
    print("✅ Talisman initialized")
except Exception as e:
    print(f"❌ Talisman error: {e}")

# Test 5: Add User Activity Monitor
try:
    from user_activity_monitor import activity_monitor, manual_log_activity
    print("✅ User activity monitoring initialized")
except Exception as e:
    print(f"❌ User activity monitoring error: {e}")

# Test 6: Add Blueprints (SUSPECT!)
try:
    from auth import auth_bp
    from health_check import health_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp)
    print("✅ Blueprints registered")
except Exception as e:
    print(f"❌ Blueprint error: {e}")

# Test 7: Add Service Classes (SUSPECT!)
try:
    from google_calendar_service import GoogleCalendarService
    from harvest_service import HarvestService
    from mapping_engine import MappingEngine
    from suggestion_engine import SuggestionEngine

    google_service = GoogleCalendarService()
    harvest_service = HarvestService()
    mapping_engine = MappingEngine()
    suggestion_engine = SuggestionEngine()
    print("✅ Services initialized")
except Exception as e:
    print(f"❌ Services error: {e}")

# Test 8: Add CSRF Context Processor (SUSPECT!)
try:
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    print("✅ CSRF context processor added")
except Exception as e:
    print(f"❌ CSRF context processor error: {e}")

@app.route('/')
def index():
    return "<h1>Isolation Test</h1><p>If you see this, the current configuration works!</p>"

@app.route('/test')
def test():
    return render_template('login.html')

if __name__ == '__main__':
    print("🧪 Starting isolation test on port 9002...")
    print("📍 URL: http://127.0.0.1:9002")
    app.run(debug=True, port=9002, host='127.0.0.1')
