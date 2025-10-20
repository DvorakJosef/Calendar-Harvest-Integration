#!/usr/bin/env python3
"""
Startup script for Calendar-Harvest Integration on port 8080
This bypasses any port conflicts on 5001
"""

import os
import sys

# Force environment variables
os.environ['PORT'] = '8080'
os.environ['FLASK_RUN_PORT'] = '8080'

# Update redirect URIs for the new port
os.environ['GOOGLE_REDIRECT_URI'] = 'http://127.0.0.1:8080/auth/callback'
os.environ['HARVEST_REDIRECT_URI'] = 'http://127.0.0.1:8080/auth/harvest/callback'

print("🚀 Starting Calendar-Harvest Integration on port 8080...")
print("📍 URL: http://127.0.0.1:8080")
print("🔧 Port 5001 conflict bypassed")
print()

# Import and start the app
from main import app

if __name__ == '__main__':
    with app.app_context():
        from models import db
        db.create_all()
    
    # Force port 8080
    app.run(debug=True, port=8080, host='127.0.0.1')
