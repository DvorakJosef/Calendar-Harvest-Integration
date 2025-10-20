#!/usr/bin/env python3
"""
Debug startup script with verbose logging
"""

import os
import sys
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Force environment variables
os.environ['PORT'] = '9999'
os.environ['FLASK_RUN_PORT'] = '9999'
os.environ['GOOGLE_REDIRECT_URI'] = 'http://127.0.0.1:9999/auth/callback'
os.environ['HARVEST_REDIRECT_URI'] = 'http://127.0.0.1:9999/auth/harvest/callback'

print("🚀 Starting Calendar-Harvest Integration with DEBUG logging...")
print("📍 URL: http://127.0.0.1:9999")
print("🔍 Debug mode: ON")
print("📝 All API calls will be logged")
print()

# Import and start the app
from main import app

# NUCLEAR OPTION: Remove ALL middleware and extensions
print("🔧 NUCLEAR DEBUGGING: Removing ALL middleware...")

# Clear ALL Flask extensions
app.extensions.clear()

# Clear ALL blueprints
app.blueprints.clear()

# Reset Flask configuration to minimal
app.config.clear()
app.config['SECRET_KEY'] = 'debug-key-123'
app.config['TESTING'] = True

# Clear any registered functions
app.before_request_funcs.clear()
app.after_request_funcs.clear()
app.teardown_request_funcs.clear()
app.teardown_appcontext_funcs.clear()

print("🔧 ALL middleware and extensions removed")

# OVERRIDE THE INDEX ROUTE TO BYPASS TEMPLATE RENDERING
@app.route('/', methods=['GET'])
def debug_index():
    """Debug index route that bypasses template rendering"""
    print("🎯 DEBUG: Index route called directly")
    return """
    <html>
    <head><title>Debug Index</title></head>
    <body>
        <h1>🎯 DEBUG INDEX ROUTE</h1>
        <p>This bypasses template rendering completely.</p>
        <p>If you see this, the route works but templates don't.</p>
        <p>All blueprints have been removed.</p>
    </body>
    </html>
    """

# Disable rate limiting temporarily
print("🔧 Disabling rate limiting for debugging...")
if hasattr(app, 'limiter'):
    delattr(app, 'limiter')
app.extensions.pop('limiter', None)

# Add detailed request logging middleware
@app.before_request
def log_request_info():
    from flask import request
    print(f"\n🌐 === REQUEST START ===")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Path: {request.path}")
    print(f"Endpoint: {request.endpoint}")
    print(f"Content-Type: {request.content_type}")
    print(f"Headers: {dict(request.headers)}")
    if request.json:
        print(f"📦 JSON data: {request.json}")
    if request.form:
        print(f"📝 Form data: {dict(request.form)}")
    if request.args:
        print(f"🔗 Query args: {dict(request.args)}")

@app.after_request
def log_response_info(response):
    from flask import request
    print(f"✅ Response: {response.status_code}")
    if response.status_code >= 400:
        print(f"❌ Error response: {response.get_data(as_text=True)[:500]}")
    print(f"🌐 === REQUEST END ===\n")
    return response

if __name__ == '__main__':
    with app.app_context():
        from models import db
        db.create_all()
    
    print("🎯 Starting Flask server...")
    app.run(debug=True, port=9999, host='127.0.0.1')
