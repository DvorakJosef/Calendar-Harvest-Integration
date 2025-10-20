"""
Health check endpoints for the Calendar-Harvest Integration app.
Used by Google App Engine for liveness and readiness checks.
"""

from flask import Blueprint, jsonify
import sqlite3
import os
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'calendar-harvest-integration'
    }), 200

@health_bp.route('/health/detailed')
def detailed_health_check():
    """Detailed health check with database connectivity."""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'calendar-harvest-integration',
        'checks': {}
    }
    
    # Check database connectivity
    try:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///calendar_harvest.db')
        
        if database_url.startswith('sqlite'):
            # SQLite check
            db_path = database_url.replace('sqlite:///', '')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.execute('SELECT 1')
                conn.close()
                health_status['checks']['database'] = 'healthy'
            else:
                health_status['checks']['database'] = 'database_file_not_found'
                health_status['status'] = 'degraded'
        else:
            # PostgreSQL check (for production)
            # Note: This would require psycopg2 for full implementation
            health_status['checks']['database'] = 'not_implemented'
            
    except Exception as e:
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check environment configuration
    required_env_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        health_status['checks']['environment'] = f'missing_vars: {missing_vars}'
        health_status['status'] = 'unhealthy'
    else:
        health_status['checks']['environment'] = 'healthy'
    
    # Return appropriate status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return jsonify(health_status), status_code

@health_bp.route('/readiness')
def readiness_check():
    """Readiness check for Kubernetes/App Engine."""
    return health_check()

@health_bp.route('/liveness')
def liveness_check():
    """Liveness check for Kubernetes/App Engine."""
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
