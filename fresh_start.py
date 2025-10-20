#!/usr/bin/env python3
"""
Completely fresh Flask app that bypasses main.py entirely
This will help us isolate if the issue is in main.py or somewhere else
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

# Create completely fresh Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'fresh-test-key-12345'

print("🚀 Starting FRESH Flask app...")
print("📍 URL: http://127.0.0.1:8888")
print("🔧 NO imports from main.py")
print("🔧 NO security middleware")
print("🔧 NO custom modules")

# Basic routes
@app.route('/')
def index():
    """Main page"""
    print(f"🌐 GET / - Session: {dict(session)}")
    if 'user_id' not in session:
        return """
        <html>
        <head><title>Fresh Test App</title></head>
        <body>
            <h1>🎉 Fresh Flask App Working!</h1>
            <p>This proves Flask itself works fine.</p>
            <p><a href="/login">Go to Login</a></p>
            <p><a href="/setup">Go to Setup (will fail - no auth)</a></p>
            <p><a href="/test-api">Test API Endpoint</a></p>
        </body>
        </html>
        """
    return """
        <html>
        <head><title>Fresh Test App</title></head>
        <body>
            <h1>🎉 Logged In!</h1>
            <p>User ID: {}</p>
            <p><a href="/setup">Go to Setup</a></p>
            <p><a href="/logout">Logout</a></p>
        </body>
        </html>
        """.format(session['user_id'])

@app.route('/login')
def login():
    """Fake login"""
    session['user_id'] = 1
    session['user_email'] = 'test@example.com'
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/setup')
def setup():
    """Setup page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return """
    <html>
    <head>
        <title>Setup Page</title>
        <script>
            // Test the API endpoints
            function testAPIs() {
                console.log('Testing APIs...');
                
                fetch('/api/google/status')
                    .then(response => response.json())
                    .then(data => {
                        console.log('Google status:', data);
                        document.getElementById('google-status').innerHTML = 'Google: ' + JSON.stringify(data);
                    })
                    .catch(error => {
                        console.error('Google API error:', error);
                        document.getElementById('google-status').innerHTML = 'Google: ERROR - ' + error;
                    });
                
                fetch('/api/harvest/status')
                    .then(response => response.json())
                    .then(data => {
                        console.log('Harvest status:', data);
                        document.getElementById('harvest-status').innerHTML = 'Harvest: ' + JSON.stringify(data);
                    })
                    .catch(error => {
                        console.error('Harvest API error:', error);
                        document.getElementById('harvest-status').innerHTML = 'Harvest: ERROR - ' + error;
                    });
            }
            
            // Auto-test on page load
            window.onload = testAPIs;
        </script>
    </head>
    <body>
        <h1>🔧 Setup Page</h1>
        <p>This is a fresh setup page with API testing.</p>
        
        <h2>API Status Tests:</h2>
        <div id="google-status">Google: Testing...</div>
        <div id="harvest-status">Harvest: Testing...</div>
        
        <p><button onclick="testAPIs()">Refresh API Tests</button></p>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    """

@app.route('/test-api')
def test_api():
    """Test API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Fresh API endpoint working!',
        'timestamp': '2025-07-25'
    })

@app.route('/api/google/status')
def google_status():
    """Mock Google status"""
    print("🌐 GET /api/google/status")
    return jsonify({
        'connected': False,
        'user_info': None,
        'needs_refresh': False,
        'message': 'Fresh mock Google status'
    })

@app.route('/api/harvest/status')
def harvest_status():
    """Mock Harvest status"""
    print("🌐 GET /api/harvest/status")
    return jsonify({
        'connected': False,
        'user_info': None,
        'message': 'Fresh mock Harvest status'
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
    print("🎯 Starting fresh Flask server on port 8888...")
    app.run(debug=True, port=8888, host='127.0.0.1')
