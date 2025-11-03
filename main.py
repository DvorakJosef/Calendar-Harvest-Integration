"""
Calendar to Harvest Timesheet Integration App
Main Flask application entry point
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from datetime import datetime, timedelta
import os
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
from validation import (
    validate_json, MappingSchema, ProcessingSchema, PatternRuleSchema,
    BulkAssignmentSchema, ImportDataSchema, validate_user_id,
    validate_date_range, validate_harvest_ids, SecurityValidationError
)
from secrets_manager import get_flask_secret_key, get_database_url, validate_configuration

app = Flask(__name__)

# Use secure secrets management
app.config['SECRET_KEY'] = get_flask_secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)

# Validate configuration on startup
config_validation = validate_configuration()

# Initialize database tables on app creation
with app.app_context():
    try:
        print(f"🗄️  Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        db.session.commit()  # Ensure changes are committed
        print("✅ Database tables created successfully")
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 Tables in database: {tables}")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        import traceback
        traceback.print_exc()
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

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Initialize CSRF protection (skip for desktop app)
if os.getenv('FLASK_ENV') != 'desktop':
    csrf = CSRFProtect(app)
else:
    print("🖥️  Desktop mode: CSRF protection disabled for PyWebView compatibility")

# Initialize rate limiting
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

# Initialize security headers (skip for desktop app)
if os.getenv('FLASK_ENV') != 'desktop':
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
        content_security_policy_nonce_in=[] if os.getenv('FLASK_ENV') == 'development' else ['script-src', 'style-src'],
        feature_policy={
            'geolocation': "'none'",
            'camera': "'none'",
            'microphone': "'none'"
        }
    )
else:
    print("🖥️  Desktop mode: Talisman security headers disabled for PyWebView compatibility")

# Make CSRF token available in templates
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)

# Initialize services
google_service = GoogleCalendarService()
harvest_service = HarvestService()
mapping_engine = MappingEngine()
suggestion_engine = SuggestionEngine()

# Initialize activity monitoring
try:
    from user_activity_monitor import activity_monitor, manual_log_activity
    MONITORING_ENABLED = True
    print("✅ User activity monitoring enabled")
except ImportError:
    MONITORING_ENABLED = False
    print("⚠️  User activity monitoring not available")

# Initialize preview mode for testing
PREVIEW_MODE = os.getenv('PREVIEW_MODE', 'false').lower() == 'true'
if PREVIEW_MODE:
    print("🔍 PREVIEW MODE ENABLED - All timesheet entries will require manual approval")
else:
    print("⚡ DIRECT MODE - Timesheet entries will be sent directly to Harvest")

# Security validation function
def validate_user_timesheet_access(user_id: int, operation: str) -> bool:
    """
    🔒 CRITICAL SECURITY FUNCTION
    Validates that timesheet operations are only performed for the authenticated user

    Args:
        user_id: ID of the user attempting the operation
        operation: Description of the operation being attempted

    Returns:
        True if operation is allowed, False otherwise
    """
    try:
        # Verify user is authenticated
        current_user = get_current_user()
        if not current_user:
            print(f"🚨 SECURITY VIOLATION: {operation} attempted without authentication")
            return False

        # Verify user_id matches authenticated user
        if current_user.id != user_id:
            print(f"🚨 SECURITY VIOLATION: {operation} attempted for user_id {user_id} by user {current_user.id}")
            if MONITORING_ENABLED:
                manual_log_activity(
                    current_user.id,
                    current_user.email,
                    f"SECURITY_VIOLATION_{operation}",
                    "security_check",
                    False,
                    {"attempted_user_id": user_id, "violation_type": "cross_user_access"}
                )
            return False

        # Verify user has Harvest credentials (OAuth or legacy)
        user_config = UserConfig.query.filter_by(user_id=user_id).first()
        if not user_config or not user_config.has_harvest_credentials():
            print(f"🚨 SECURITY VIOLATION: {operation} attempted without valid Harvest credentials for user_id {user_id}")
            return False

        # Log successful validation
        print(f"✅ SECURITY CHECK PASSED: {operation} authorized for user_id {user_id}")
        if MONITORING_ENABLED:
            manual_log_activity(
                user_id,
                current_user.email,
                f"SECURITY_CHECK_{operation}",
                "security_check",
                True
            )

        return True

    except Exception as e:
        print(f"🚨 SECURITY ERROR during validation: {e}")
        return False

@app.route('/')
def index():
    """Main dashboard page"""
    print(f"📍 Index route called")
    print(f"   Session keys: {list(session.keys())}")
    print(f"   user_id in session: {'user_id' in session}")

    # Check for token in query params (for PyWebView compatibility)
    token = request.args.get('token')
    if token and 'user_id' not in session:
        print(f"   Found token in query params, attempting to restore session...")
        user = User.query.filter_by(persistent_token=token).first()
        if user and user.is_active:
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = user.name
            session['persistent_token'] = user.persistent_token
            session.permanent = True
            user.last_login = datetime.utcnow()
            db.session.commit()
            print(f"   ✅ Session restored from token for user: {user.email}")
            # Redirect without token to clean up URL
            return redirect(url_for('index'))

    if 'user_id' in session:
        print(f"   user_id value: {session.get('user_id')}")
        print(f"   ✅ User authenticated, showing dashboard")
        return render_template('index.html')

    print(f"   ❌ No user_id in session, showing login page")
    return render_template('login.html')

@app.route('/api/auth/persistent-login', methods=['POST'])
def persistent_login():
    """Handle persistent login using stored token"""
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 400

        # Find user by persistent token
        user = User.query.filter_by(persistent_token=token).first()

        if not user or not user.is_active:
            print(f"❌ Invalid or inactive persistent token")
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        # Restore session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        session['persistent_token'] = user.persistent_token
        session.permanent = True

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        print(f"✅ Persistent login successful for user: {user.email}")

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name
            }
        })

    except Exception as e:
        print(f"❌ Persistent login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/get-persistent-token')
def get_persistent_token():
    """Get persistent token for currently logged in user"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'token': None}), 200

        user = User.query.get(user_id)
        if user and user.persistent_token:
            return jsonify({'token': user.persistent_token}), 200

        return jsonify({'token': None}), 200

    except Exception as e:
        print(f"❌ Error getting persistent token: {e}")
        return jsonify({'token': None}), 200

@app.route('/api/auth/verify-token', methods=['POST'])
def verify_token():
    """Verify persistent token and return user info"""
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'authenticated': False}), 200

        user = User.query.filter_by(persistent_token=token).first()

        if not user or not user.is_active:
            return jsonify({'authenticated': False}), 200

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'authenticated': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'picture': user.picture
            }
        }), 200

    except Exception as e:
        print(f"❌ Error verifying token: {e}")
        return jsonify({'authenticated': False}), 200

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        user = get_current_user()

        # Count active mappings for this user
        mappings_count = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).count()

        # Get last processing date
        last_processing = ProcessingHistory.query.filter_by(user_id=user.id).order_by(ProcessingHistory.processed_at.desc()).first()
        last_processed_date = last_processing.processed_at.strftime('%Y-%m-%d') if last_processing else None

        # Count total processed entries
        total_processed = ProcessingHistory.query.filter_by(user_id=user.id).count()

        return jsonify({
            'success': True,
            'mappings_count': mappings_count,
            'last_processed_date': last_processed_date,
            'total_processed': total_processed
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/setup')
@login_required
def setup():
    """Setup page for API credentials"""
    return render_template('setup.html')

@app.route('/preview')
@login_required
def preview():
    """Preview page for manual timesheet review"""
    return render_template('preview.html')

@app.route('/setup-wizard')
@login_required
def setup_wizard():
    """Redirect to setup page (wizard is now integrated there)"""
    return redirect(url_for('setup'))

@app.route('/init-db')
def init_database():
    """Initialize database tables (for production setup)"""
    try:
        # Create all tables
        db.create_all()
        return jsonify({
            'success': True,
            'message': 'Database tables created successfully'
        })
    except Exception as e:
        app.logger.error(f"Error initializing database: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/mappings')
@login_required
def mappings():
    """Project mappings configuration page"""
    user = get_current_user()
    mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
    return render_template('mappings.html', mappings=mappings)

@app.route('/process')
@login_required
def process():
    """Week selection and processing page"""
    return render_template('process.html')



@app.route('/api/google/auth')
def google_auth():
    """Initiate Google OAuth flow"""
    auth_url = google_service.get_auth_url()
    return redirect(auth_url)

@app.route('/api/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    code = request.args.get('code')
    if code:
        try:
            google_service.handle_callback(code)
            flash('Google Calendar connected successfully!', 'success')
        except Exception as e:
            flash(f'Error connecting to Google Calendar: {str(e)}', 'error')
    return redirect(url_for('setup'))

@app.route('/api/google/disconnect', methods=['POST'])
@login_required
def google_disconnect():
    """Disconnect Google Calendar and clear credentials"""
    try:
        from auth import get_current_user
        import requests

        user = get_current_user()
        if user:
            user_config = UserConfig.query.filter_by(user_id=user.id).first()
            if user_config:
                # Try to revoke the token from Google's servers first
                creds_dict = user_config.get_google_credentials()
                if creds_dict and creds_dict.get('token'):
                    try:
                        # Revoke the token from Google
                        revoke_url = f"https://oauth2.googleapis.com/revoke?token={creds_dict['token']}"
                        response = requests.post(revoke_url)
                        print(f"Google token revocation response: {response.status_code}")
                    except Exception as revoke_error:
                        print(f"Error revoking Google token: {revoke_error}")

                # Clear user's Google credentials from our database
                user_config.set_google_credentials(None)
                db.session.commit()

        return jsonify({'success': True, 'message': 'Google Calendar disconnected. Please re-authenticate.'})
    except Exception as e:
        print(f"Error disconnecting Google: {e}")
        return jsonify({'success': False, 'error': str(e)})









# API Status endpoints
@app.route('/api/google/status')
@login_required
def google_status():
    """Check Google Calendar connection status"""
    try:
        from auth import get_current_user
        user = get_current_user()

        if not user:
            return jsonify({'connected': False, 'error': 'User not authenticated'})

        user_config = UserConfig.query.filter_by(user_id=user.id).first()
        if not user_config:
            return jsonify({'connected': False, 'needs_refresh': False})

        creds_dict = user_config.get_google_credentials()
        if not creds_dict:
            return jsonify({'connected': False, 'needs_refresh': False})

        # Check if we have all required fields
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        missing_fields = [field for field in required_fields if not creds_dict.get(field)]

        if missing_fields:
            # We have some credentials but missing critical fields (especially refresh_token)
            needs_refresh = 'refresh_token' in missing_fields
            return jsonify({
                'connected': True,  # Partially connected
                'needs_refresh': needs_refresh,
                'user_info': {'email': user.email}
            })

        # Try to create credentials and test them
        from google.oauth2.credentials import Credentials
        credentials = Credentials(**creds_dict)

        return jsonify({
            'connected': True,
            'needs_refresh': False,
            'user_info': {'email': user.email}
        })

    except Exception as e:
        print(f"Error checking Google status: {e}")
        return jsonify({'connected': False, 'error': str(e)})

@app.route('/api/harvest/status')
@login_required
def harvest_status():
    """Check Harvest connection status"""
    try:
        is_connected = harvest_service.is_connected()
        user_info = harvest_service.get_user_info() if is_connected else None
        return jsonify({
            'connected': is_connected,
            'user_info': user_info
        })
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})

# Disconnect endpoints

@app.route('/api/harvest/disconnect', methods=['POST'])
@login_required
def harvest_disconnect():
    """Disconnect Harvest for current user only"""
    try:
        user = get_current_user()

        # Log the activity
        if MONITORING_ENABLED:
            manual_log_activity(user.id, user.email, "HARVEST_DISCONNECT", "/api/harvest/disconnect", True)

        user_config = UserConfig.query.filter_by(user_id=user.id).first()
        if user_config:
            # Clear OAuth credentials
            user_config.clear_harvest_oauth()
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        if MONITORING_ENABLED:
            manual_log_activity(user.id, user.email, "HARVEST_DISCONNECT", "/api/harvest/disconnect", False, {"error": str(e)})
        return jsonify({'success': False, 'error': str(e)})

# Harvest OAuth 2.0 Endpoints
@app.route('/auth/harvest')
@login_required
@limiter.limit("10 per minute")  # Limit OAuth attempts
def harvest_oauth_start():
    """Start Harvest OAuth 2.0 authentication flow"""
    try:
        user = get_current_user()

        from harvest_oauth import harvest_oauth

        if not harvest_oauth.is_configured():
            return jsonify({
                'success': False,
                'error': 'Harvest OAuth not configured. Please contact administrator.'
            }), 500

        # Generate authorization URL
        authorization_url, state = harvest_oauth.get_authorization_url(user.id)

        # Store state in session for verification
        session['harvest_oauth_state'] = state

        # Log the activity
        if MONITORING_ENABLED:
            manual_log_activity(user.id, user.email, "HARVEST_OAUTH_START", "/auth/harvest", True)

        # Redirect to Harvest for authorization
        return redirect(authorization_url)

    except Exception as e:
        if MONITORING_ENABLED:
            manual_log_activity(user.id, user.email, "HARVEST_OAUTH_START", "/auth/harvest", False, {"error": str(e)})
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/auth/harvest/callback')
@login_required
def harvest_oauth_callback():
    """Handle Harvest OAuth 2.0 callback"""
    try:
        user = get_current_user()

        # Get authorization code and state from callback
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        if error:
            print(f"❌ OAuth error: {error}")
            return redirect(url_for('setup') + f'?error=oauth_error&message={error}')

        if not code or not state:
            return redirect(url_for('setup') + '?error=missing_parameters')

        # Verify state parameter
        stored_state = session.get('harvest_oauth_state')
        if not stored_state or stored_state != state:
            print(f"❌ OAuth state mismatch: stored={stored_state}, received={state}")
            return redirect(url_for('setup') + '?error=state_mismatch')

        # Clear state from session
        session.pop('harvest_oauth_state', None)

        from harvest_oauth import harvest_oauth

        # Exchange code for token
        token_data, user_id = harvest_oauth.exchange_code_for_token(code, state)

        # Verify user_id matches current user
        if user_id != user.id:
            print(f"❌ User ID mismatch: expected={user.id}, received={user_id}")
            return redirect(url_for('setup') + '?error=user_mismatch')

        # Store token in user config
        user_config = UserConfig.query.filter_by(user_id=user.id).first()
        if not user_config:
            user_config = UserConfig(user_id=user.id)
            db.session.add(user_config)

        user_config.set_harvest_oauth_token(token_data)
        db.session.commit()

        # Log successful OAuth
        if MONITORING_ENABLED:
            manual_log_activity(
                user.id, user.email,
                "HARVEST_OAUTH_SUCCESS",
                "/auth/harvest/callback",
                True,
                {
                    "harvest_user_email": token_data.get('harvest_user_email'),
                    "harvest_account_name": token_data.get('harvest_account_name')
                }
            )

        print(f"✅ OAuth successful for user {user.email}")
        print(f"   Harvest User: {token_data.get('harvest_user_email')}")
        print(f"   Harvest Account: {token_data.get('harvest_account_name')}")

        return redirect(url_for('setup') + '?success=harvest_connected')

    except Exception as e:
        print(f"❌ OAuth callback error: {e}")
        if MONITORING_ENABLED:
            manual_log_activity(user.id, user.email, "HARVEST_OAUTH_CALLBACK", "/auth/harvest/callback", False, {"error": str(e)})
        return redirect(url_for('setup') + f'?error=oauth_failed&message={str(e)}')

@app.route('/api/harvest/oauth/status')
@login_required
def harvest_oauth_status():
    """Get Harvest OAuth status for current user"""
    try:
        user = get_current_user()
        user_config = UserConfig.query.filter_by(user_id=user.id).first()

        if not user_config:
            return jsonify({
                'success': True,
                'oauth_configured': False,
                'auth_method': None
            })

        oauth_configured = user_config.is_harvest_oauth_configured()
        auth_method = user_config.get_harvest_auth_method()

        response_data = {
            'success': True,
            'oauth_configured': oauth_configured,
            'auth_method': auth_method,
            'has_credentials': user_config.has_harvest_credentials()
        }

        if oauth_configured:
            response_data.update({
                'harvest_user_email': user_config.harvest_user_email,
                'harvest_account_name': user_config.harvest_account_name,
                'token_valid': user_config.is_harvest_token_valid()
            })

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/harvest/user-info')
@login_required
def harvest_user_info():
    """Get current Harvest user information for safety confirmation"""
    try:
        user = get_current_user()

        # Use the safety validator to get verified user info
        from harvest_safety_validator import harvest_safety
        is_valid, error, harvest_user = harvest_safety.validate_user_identity(user.id, user.email)

        if not is_valid:
            return jsonify({
                'success': False,
                'error': f'Cannot verify Harvest user identity: {error}'
            })

        # Get account info as well
        is_isolated, account_error, account_info = harvest_safety.validate_account_isolation(user.id)

        if not is_isolated:
            return jsonify({
                'success': False,
                'error': f'Cannot verify account isolation: {account_error}'
            })

        return jsonify({
            'success': True,
            'harvest_user': {
                'id': harvest_user.get('id'),
                'email': harvest_user.get('email'),
                'first_name': harvest_user.get('first_name'),
                'last_name': harvest_user.get('last_name'),
                'full_name': f"{harvest_user.get('first_name', '')} {harvest_user.get('last_name', '')}".strip()
            },
            'harvest_account': {
                'id': account_info.get('id'),
                'name': account_info.get('name'),
                'base_uri': account_info.get('base_uri')
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting Harvest user info: {str(e)}'
        })

# Harvest API endpoints
@app.route('/api/harvest/projects')
@login_required
def harvest_projects():
    """Get all Harvest projects"""
    try:
        user = get_current_user()
        projects = harvest_service.get_projects(user_id=user.id)

        # Get already mapped project-task combinations for this user
        mapped_combinations = set()
        existing_mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
        for mapping in existing_mappings:
            mapped_combinations.add((mapping.harvest_project_id, mapping.harvest_task_id))

        # Filter out projects that have all their tasks mapped
        available_projects = []
        for project in projects:
            # Get tasks for this project to check if any are available
            project_tasks = harvest_service.get_project_tasks(project['id'], user_id=user.id)
            available_tasks = [task for task in project_tasks
                             if (project['id'], task['id']) not in mapped_combinations]

            # Only include project if it has available tasks
            if available_tasks:
                available_projects.append(project)

        return jsonify({
            'success': True,
            'projects': available_projects,
            'mapped_combinations': list(mapped_combinations)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/harvest/projects/<int:project_id>/tasks')
@login_required
def harvest_project_tasks(project_id):
    """Get tasks for a specific project"""
    try:
        user = get_current_user()
        tasks = harvest_service.get_project_tasks(project_id, user_id=user.id)

        # Get already mapped project-task combinations for this user
        mapped_combinations = set()
        existing_mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
        for mapping in existing_mappings:
            mapped_combinations.add((mapping.harvest_project_id, mapping.harvest_task_id))

        # Filter out already mapped tasks for this project
        available_tasks = [task for task in tasks
                          if (project_id, task['id']) not in mapped_combinations]

        return jsonify({
            'success': True,
            'tasks': available_tasks,
            'mapped_tasks': [task_id for (proj_id, task_id) in mapped_combinations if proj_id == project_id]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Test route for debugging
@app.route('/api/test-post', methods=['POST'])
def test_post():
    """Test POST route"""
    return jsonify({'success': True, 'message': 'POST works'})

# Another test route
@app.route('/api/test-mapping-create', methods=['POST'])
def test_mapping_create():
    """Test mapping creation route"""
    return jsonify({'success': True, 'message': 'Mapping creation test works'})

# Mappings API endpoints
@app.route('/api/mappings', methods=['GET'])
@login_required
def get_mappings():
    """Get all project mappings"""
    try:
        user = get_current_user()
        mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
        return jsonify({
            'success': True,
            'mappings': [mapping.to_dict() for mapping in mappings]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mappings', methods=['POST'])
@login_required
def create_mapping():
    """Create a new project mapping"""
    try:
        user = get_current_user()
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['calendar_label', 'harvest_project_id', 'harvest_project_name', 'harvest_task_id', 'harvest_task_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        # Check if mapping already exists
        existing = ProjectMapping.query.filter_by(
            user_id=user.id,
            calendar_label=data['calendar_label'],
            is_active=True
        ).first()

        if existing:
            return jsonify({'success': False, 'error': f'Mapping for label "{data["calendar_label"]}" already exists'}), 400

        # Create new mapping
        mapping = ProjectMapping(
            user_id=user.id,
            calendar_label=data['calendar_label'],
            harvest_project_id=data['harvest_project_id'],
            harvest_project_name=data['harvest_project_name'],
            harvest_task_id=data['harvest_task_id'],
            harvest_task_name=data['harvest_task_name']
        )

        db.session.add(mapping)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Mapping created successfully'})

    except Exception as e:
        print(f"Error creating mapping: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mappings/<int:mapping_id>', methods=['DELETE'])
@login_required
def delete_mapping(mapping_id):
    """Delete a project mapping"""
    try:
        user = get_current_user()
        mapping = ProjectMapping.query.filter_by(id=mapping_id, user_id=user.id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404

        # If mapping is already inactive, just return success
        if not mapping.is_active:
            return jsonify({'success': True, 'message': 'Mapping was already deleted'})

        mapping.is_active = False
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/mappings/cleanup', methods=['POST'])
@login_required
def cleanup_mappings():
    """Clean up all mappings for the current user"""
    try:
        user = get_current_user()

        # Get all mappings for this user (active and inactive)
        all_mappings = ProjectMapping.query.filter_by(user_id=user.id).all()

        # Delete them completely from the database
        for mapping in all_mappings:
            db.session.delete(mapping)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Deleted {len(all_mappings)} mappings',
            'deleted_count': len(all_mappings)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Auto-suggestion API endpoints
@app.route('/api/suggestions/generate', methods=['POST'])
def generate_suggestions():
    """Generate auto-suggestions for calendar-to-project mappings"""
    try:
        data = request.get_json() or {}
        weeks_to_analyze = data.get('weeks', 4)

        # Check if both Google Calendar and Harvest are connected
        if not google_service.is_connected():
            return jsonify({
                'success': False,
                'error': 'Google Calendar not connected. Please connect your calendar first.'
            })

        if not harvest_service.is_connected():
            return jsonify({
                'success': False,
                'error': 'Harvest not connected. Please connect your Harvest account first.'
            })

        # Use enhanced suggestions if user has existing mappings
        user = get_current_user()
        existing_mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).count()
        if existing_mappings > 0:
            suggestions = suggestion_engine.get_enhanced_suggestions(weeks_to_analyze, user_id=user.id)
        else:
            suggestions = suggestion_engine.generate_suggestions(weeks_to_analyze, user_id=user.id)

        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'weeks_analyzed': weeks_to_analyze,
            'total_suggestions': len(suggestions)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/suggestions/apply', methods=['POST'])
def apply_suggestions():
    """Apply selected auto-suggestions as mappings"""
    try:
        data = request.get_json()
        suggestions_to_apply = data.get('suggestions', [])

        if not suggestions_to_apply:
            return jsonify({'success': False, 'error': 'No suggestions provided'})

        created_count = 0
        errors = []

        for suggestion in suggestions_to_apply:
            try:
                # Check if mapping already exists
                existing = ProjectMapping.query.filter_by(
                    calendar_label=suggestion['calendar_label'],
                    is_active=True
                ).first()

                if existing:
                    errors.append(f"Mapping for '{suggestion['calendar_label']}' already exists")
                    continue

                # Create new mapping
                mapping = ProjectMapping(
                    calendar_label=suggestion['calendar_label'],
                    harvest_project_id=suggestion['harvest_project_id'],
                    harvest_project_name=suggestion['harvest_project_name'],
                    harvest_task_id=suggestion['harvest_task_id'],
                    harvest_task_name=suggestion['harvest_task_name']
                )

                db.session.add(mapping)
                created_count += 1

            except Exception as e:
                errors.append(f"Error creating mapping for '{suggestion.get('calendar_label', 'unknown')}': {str(e)}")

        db.session.commit()

        return jsonify({
            'success': True,
            'created_count': created_count,
            'errors': errors
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/suggestions/insights')
def get_calendar_insights():
    """Get calendar analysis insights"""
    try:
        weeks_to_analyze = request.args.get('weeks', 8, type=int)

        if not google_service.is_connected():
            return jsonify({
                'success': False,
                'error': 'Google Calendar not connected'
            })

        insights = suggestion_engine.analyze_calendar_patterns(weeks_to_analyze)
        learning_data = suggestion_engine.learn_from_user_mappings()

        return jsonify({
            'success': True,
            'calendar_insights': insights,
            'mapping_insights': learning_data,
            'weeks_analyzed': weeks_to_analyze
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Calendar API endpoints
@app.route('/api/calendar/events')
@login_required
def calendar_events():
    """Get calendar events for a specific week"""
    try:
        user = get_current_user()
        week_start_str = request.args.get('week_start')
        if not week_start_str:
            return jsonify({'success': False, 'error': 'week_start parameter required'})

        from datetime import datetime, timedelta
        week_start = datetime.fromisoformat(week_start_str)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        events = google_service.get_calendar_events(week_start)

        # Server-side filtering to ensure only events from the requested week are returned
        filtered_events = []
        for event in events:
            if not event.get('start'):
                continue

            try:
                # Parse event start date
                if 'T' in event['start']:
                    event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                else:
                    event_start = datetime.fromisoformat(event['start'] + 'T00:00:00')

                # Check if event falls within the requested week
                if week_start.date() <= event_start.date() <= week_end.date():
                    # Add mapping information to events
                    mapping = mapping_engine.find_mapping_for_event(event, user.id)
                    event['mapping'] = mapping.calendar_label if mapping else None
                    filtered_events.append(event)
                else:
                    print(f"Filtering out event '{event.get('summary', 'Unknown')}' - date {event_start.date()} not in week {week_start.date()} to {week_end.date()}")

            except Exception as e:
                print(f"Error parsing event date for '{event.get('summary', 'Unknown')}': {e}")
                continue

        print(f"Returning {len(filtered_events)} events for week {week_start_str} (filtered from {len(events)} total)")
        return jsonify({'success': True, 'events': filtered_events, 'week_start': week_start_str})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/labels')
@login_required
def calendar_labels():
    """Get unique calendar event labels for mapping dropdown"""
    try:
        weeks = request.args.get('weeks', 12, type=int)
        min_frequency = request.args.get('min_frequency', 2, type=int)
        force_refresh = request.args.get('force_refresh', False, type=bool)
        user = get_current_user()

        if not google_service.is_connected():
            return jsonify({
                'success': False,
                'error': 'Google Calendar not connected. Please connect your calendar first.'
            })

        # Force refresh if requested (useful after label changes in Google Calendar)
        if force_refresh:
            print("🔄 Force refreshing calendar labels from Google Calendar...")

        labels = google_service.get_calendar_event_labels(weeks, min_frequency)

        # Get already mapped labels for this user
        mapped_labels = set()
        existing_mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
        for mapping in existing_mappings:
            mapped_labels.add(mapping.calendar_label)

        # Filter out already mapped labels
        available_labels = [label for label in labels if label['label'] not in mapped_labels]

        return jsonify({
            'success': True,
            'labels': available_labels,
            'weeks_analyzed': weeks,
            'total_labels': len(available_labels),
            'mapped_labels': list(mapped_labels)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Processing API endpoints
@app.route('/api/process/preview', methods=['POST'])
@login_required
def process_preview():
    """Generate timesheet preview for events"""
    try:
        user = get_current_user()
        data = request.get_json()
        week_start_str = data['week_start']
        events = data['events']
        show_all_events = data.get('show_all_events', False)

        from datetime import datetime
        week_start = datetime.fromisoformat(week_start_str).date()

        print(f"Preview: Week {week_start_str} -> {week_start}, {len(events)} events, show_all_events={show_all_events}")

        results = mapping_engine.process_events_for_week(events, week_start, user.id, show_all_events=show_all_events)

        # Individual entries - no grouping needed
        # Each calendar event creates exactly one timesheet entry
        timesheet_entries = results['timesheet_entries']

        print(f"Preview: {len(timesheet_entries)} individual timesheet entries generated")

        # Summary information
        summary_info = {
            'total_entries': len(timesheet_entries),
            'total_hours': sum(entry['hours'] for entry in timesheet_entries)
        }

        return jsonify({
            'success': True,
            'timesheet_entries': timesheet_entries,
            'summary_info': summary_info,
            'mapped_events': results['mapped_events'],
            'unmapped_events': results['unmapped_events'],
            'unmapped_events_details': results['unmapped_events_details'],
            'warnings': results['warnings']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})



@app.route('/api/process/execute', methods=['POST'])
@login_required
@limiter.limit("10 per minute")  # Strict limit on timesheet processing
@validate_json(ProcessingSchema)
def process_execute(validated_data):
    """Execute timesheet processing"""
    print("🚀 PROCESSING EXECUTE ENDPOINT HIT!")
    print(f"📥 Validated data: {validated_data}")
    print(f"📥 User ID: {session.get('user_id')}")
    print(f"📥 Timesheet entries count: {len(validated_data.get('timesheet_entries', []))}")
    try:
        user = get_current_user()

        # 🔒 CRITICAL SECURITY CHECK: Validate user can perform timesheet operations
        if not validate_user_timesheet_access(user.id, "TIMESHEET_PROCESSING"):
            return jsonify({
                'success': False,
                'error': 'SECURITY VIOLATION: Unauthorized timesheet access attempt'
            }), 403

        # Additional input validation
        validate_user_id(user.id)
        validate_date_range(validated_data['week_start'])

        timesheet_entries = validated_data['timesheet_entries']
        options = validated_data.get('options', {})

        # Use frontend's preview mode choice, fallback to global setting
        use_preview_mode = options.get('preview_mode', PREVIEW_MODE)
        print(f"📋 Preview mode: {use_preview_mode} (frontend: {options.get('preview_mode')}, global: {PREVIEW_MODE})")

        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        created_entries = []  # Track created entries with their details

        # Process individual entries - no grouping needed
        # Each calendar event creates exactly one timesheet entry
        print(f"Processing: Week {validated_data.get('week_start')}, {len(timesheet_entries)} individual entries")

        # Debug: Print the individual entries
        for entry in timesheet_entries:
            print(f"  Entry: {entry.get('event_summary', 'No summary')} - {entry['hours']}h on {entry['spent_date']}")

        for entry in timesheet_entries:
            try:
                if options.get('dry_run', False):
                    # Dry run - just count what would be created
                    created_count += 1
                    continue

                # Create the time entry in Harvest or Preview Mode
                # Handle both string and date objects for spent_date
                if isinstance(entry['spent_date'], str):
                    spent_date = datetime.fromisoformat(entry['spent_date']).date()
                else:
                    spent_date = entry['spent_date']

                # Use the notes from the individual entry (already contains event title)
                entry_notes = entry.get('notes', '')

                if use_preview_mode:
                    # 🔍 PREVIEW MODE: Store entry for manual review
                    from models import TimesheetPreview

                    preview_entry = TimesheetPreview(
                        user_id=user.id,
                        project_id=entry['project_id'],
                        project_name=entry.get('project_name', 'Unknown Project'),
                        task_id=entry['task_id'],
                        task_name=entry.get('task_name', 'Unknown Task'),
                        spent_date=spent_date,
                        hours=entry['hours'],
                        notes=entry_notes,
                        status='pending'
                    )

                    db.session.add(preview_entry)
                    db.session.commit()

                    print(f"📋 PREVIEW: Added entry for review - {entry.get('project_name', 'Unknown')} ({entry['hours']}h)")
                    created_count += 1  # Count as "created" for preview
                    result = {"id": f"preview_{preview_entry.id}", "preview": True}
                    error_msg = None
                else:
                    # ⚡ DIRECT MODE: Send directly to Harvest
                    result, error_msg = harvest_service.create_time_entry(
                        entry['project_id'],
                        entry['task_id'],
                        spent_date,
                        entry['hours'],
                        entry_notes,
                        force_overwrite=options.get('force_overwrite', False),
                        user_id=user.id
                    )

                if result:
                    created_count += 1

                    # Add to created entries list for frontend
                    created_entries.append({
                        'event_summary': entry.get('event_summary', 'Untitled Event'),
                        'hours': entry['hours'],
                        'project_name': entry.get('project_name', 'Unknown Project'),
                        'task_name': entry.get('task_name', 'Unknown Task'),
                        'spent_date': entry['spent_date'],
                        'notes': entry_notes,
                        'harvest_id': result.get('id')
                    })

                    # Record in processing history for this individual event
                    _ws = validated_data['week_start']
                    week_start_date = datetime.fromisoformat(_ws).date() if isinstance(_ws, str) else _ws
                    history = ProcessingHistory(
                        user_id=user.id,
                        week_start_date=week_start_date,
                        calendar_event_id=entry['event_id'],
                        calendar_event_summary=entry.get('event_summary', ''),
                        harvest_time_entry_id=result['id'],
                        harvest_project_id=entry['project_id'],
                        harvest_task_id=entry['task_id'],
                        hours_logged=entry['hours'],
                        status='success'
                    )
                    db.session.add(history)
                else:
                    skipped_count += 1
                    # Log the specific error for this individual entry
                    event_summary = entry.get('event_summary', 'Unknown event')
                    error_detail = f"Failed to create entry for '{event_summary}' ({entry['hours']}h on {spent_date})"
                    if error_msg:
                        error_detail += f": {error_msg}"
                    errors.append(error_detail)

                    # Record failed attempt in processing history for this individual event
                    _ws = validated_data['week_start']
                    week_start_date = datetime.fromisoformat(_ws).date() if isinstance(_ws, str) else _ws
                    history = ProcessingHistory(
                        user_id=user.id,
                        week_start_date=week_start_date,
                        calendar_event_id=entry['event_id'],
                        calendar_event_summary=entry.get('event_summary', ''),
                        harvest_project_id=entry['project_id'],
                        harvest_task_id=entry['task_id'],
                        hours_logged=entry['hours'],
                        status='error',
                        error_message=error_msg
                    )
                    db.session.add(history)

            except Exception as e:
                error_count += 1
                event_summary = entry.get('event_summary', 'Unknown event')
                errors.append(f"Error processing entry '{event_summary}': {str(e)}")

        db.session.commit()

        # Calculate total entries processed
        total_entries = created_count + skipped_count + error_count

        return jsonify({
            'success': True,
            'total_entries': total_entries,
            'successful_entries': created_count,
            'skipped_entries': skipped_count,
            'failed_entries': error_count,
            'errors': errors,
            'created_entries': created_entries,  # For calculating total hours
            # Keep the old field names for backward compatibility
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/debug/harvest-entries')
@login_required
def debug_harvest_entries():
    """Debug endpoint to see what entries exist in Harvest"""
    try:
        user = get_current_user()
        week_start = request.args.get('week_start')
        if not week_start:
            return jsonify({'error': 'week_start parameter required'}), 400

        start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=6)

        harvest_service = HarvestService()
        entries = harvest_service.get_time_entries(start_date, end_date, user_id=user.id)

        print(f"Fetching time entries for {start_date} to {end_date}")
        print(f"Found {len(entries)} entries")

        # Group entries by date for easier viewing
        entries_by_date = {}
        for entry in entries:
            date = entry['spent_date']
            if date not in entries_by_date:
                entries_by_date[date] = []
            entries_by_date[date].append(entry)

        return jsonify({
            'week_start': week_start,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'entries': entries,
            'entries_by_date': entries_by_date,
            'count': len(entries)
        })

    except Exception as e:
        print(f"Error in debug endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/delete-harvest-entries', methods=['POST'])
@login_required
@limiter.limit("5 per minute")  # Very strict limit on deletion
def debug_delete_harvest_entries():
    """Debug endpoint to delete specific Harvest entries"""
    try:
        user = get_current_user()
        data = request.get_json()
        week_start = data.get('week_start')
        if not week_start:
            return jsonify({'error': 'week_start parameter required'}), 400

        start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=6)

        harvest_service = HarvestService()
        entries = harvest_service.get_time_entries(start_date, end_date, user_id=user.id)

        deleted_count = 0
        errors = []

        for entry in entries:
            try:
                # Delete the entry
                headers = harvest_service._get_headers(user_id=user.id)
                response = requests.delete(
                    f'{harvest_service.base_url}/time_entries/{entry["id"]}',
                    headers=headers
                )

                if response.status_code == 200:
                    deleted_count += 1
                    print(f"Deleted entry {entry['id']} for {entry['spent_date']}")
                else:
                    error_msg = f"Failed to delete entry {entry['id']}: {response.status_code}"
                    errors.append(error_msg)
                    print(error_msg)

            except Exception as e:
                error_msg = f"Error deleting entry {entry['id']}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)

        return jsonify({
            'week_start': week_start,
            'total_entries': len(entries),
            'deleted_count': deleted_count,
            'errors': errors
        })

    except Exception as e:
        print(f"Error in delete endpoint: {e}")
        return jsonify({'error': str(e)}), 500







# Pattern Recognition API endpoints
@app.route('/api/pattern-suggestions', methods=['POST'])
@login_required
def get_pattern_suggestions():
    """Get pattern-based mapping suggestions for an event"""
    try:
        user = get_current_user()
        data = request.get_json()
        event = data.get('event')

        if not event:
            return jsonify({'success': False, 'error': 'Event data required'})

        # Get available projects
        harvest_service = HarvestService()
        available_projects = harvest_service.get_projects(user_id=user.id)

        # Get pattern suggestions
        mapping_engine = MappingEngine()
        suggestions = mapping_engine.get_pattern_suggestions(event, available_projects)

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analyze-patterns', methods=['POST'])
def analyze_event_patterns():
    """Analyze patterns in a calendar event"""
    try:
        data = request.get_json()
        event = data.get('event')

        if not event:
            return jsonify({'success': False, 'error': 'Event data required'})

        # Analyze patterns
        mapping_engine = MappingEngine()
        patterns = mapping_engine.analyze_event_patterns(event)

        return jsonify({
            'success': True,
            'patterns': patterns
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Bulk Mapping API endpoints
@app.route('/api/bulk-mapping/assign', methods=['POST'])
def bulk_assign_mappings():
    """Bulk assign mappings to multiple events"""
    try:
        data = request.get_json()
        assignments = data.get('assignments', [])
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from bulk_mapping import BulkMappingService
        bulk_service = BulkMappingService()

        results = bulk_service.bulk_assign_mappings(assignments, user_id)

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bulk-mapping/pattern-rules', methods=['GET'])
def get_pattern_rules():
    """Get all pattern rules for the current user"""
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from bulk_mapping import BulkMappingService
        bulk_service = BulkMappingService()

        rules = bulk_service.get_pattern_rules(user_id)

        return jsonify({
            'success': True,
            'rules': rules
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bulk-mapping/pattern-rules', methods=['POST'])
def create_pattern_rule():
    """Create a new pattern-based mapping rule"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from bulk_mapping import BulkMappingService
        bulk_service = BulkMappingService()

        result = bulk_service.create_pattern_rule(user_id, data)

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bulk-mapping/pattern-rules/<rule_id>', methods=['DELETE'])
def delete_pattern_rule(rule_id):
    """Delete a pattern rule"""
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from bulk_mapping import BulkMappingService
        bulk_service = BulkMappingService()

        result = bulk_service.delete_pattern_rule(user_id, rule_id)

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bulk-mapping/apply-rules', methods=['POST'])
def apply_pattern_rules():
    """Apply pattern rules to a list of events"""
    try:
        data = request.get_json()
        events = data.get('events', [])
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from bulk_mapping import BulkMappingService
        bulk_service = BulkMappingService()

        results = bulk_service.apply_pattern_rules(events, user_id)

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bulk-mapping/export', methods=['GET'])
def export_mappings():
    """Export user's mappings"""
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from bulk_mapping import BulkMappingService
        bulk_service = BulkMappingService()

        result = bulk_service.export_mappings(user_id)

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bulk-mapping/import', methods=['POST'])
def import_mappings():
    """Import mappings from JSON data"""
    try:
        data = request.get_json()
        import_data = data.get('import_data')
        merge_strategy = data.get('merge_strategy', 'update')
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        if not import_data:
            return jsonify({'success': False, 'error': 'Import data required'})

        from bulk_mapping import BulkMappingService
        bulk_service = BulkMappingService()

        results = bulk_service.import_mappings(import_data, user_id, merge_strategy)

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Setup Wizard API endpoints
@app.route('/api/setup-wizard/analyze', methods=['POST'])
def setup_wizard_analyze():
    """Analyze user's calendar for setup wizard"""
    try:
        data = request.get_json()
        weeks_to_analyze = data.get('weeks_to_analyze', 8)
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from setup_wizard import SetupWizard
        wizard = SetupWizard()

        result = wizard.analyze_user_calendar(user_id, weeks_to_analyze)

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/setup-wizard/create-mappings', methods=['POST'])
def setup_wizard_create_mappings():
    """Create mappings from setup wizard suggestions"""
    try:
        data = request.get_json()
        suggestions = data.get('suggestions', [])
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from setup_wizard import SetupWizard
        wizard = SetupWizard()

        results = wizard.create_mappings_from_suggestions(suggestions, user_id)

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/setup-wizard/status', methods=['GET'])
def setup_wizard_status():
    """Get onboarding status for current user"""
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})

        from setup_wizard import SetupWizard
        wizard = SetupWizard()

        result = wizard.get_onboarding_status(user_id)

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Preview Mode API Endpoints
@app.route('/api/preview/entries')
@login_required
def get_preview_entries():
    """Get pending preview entries for current user"""
    try:
        user = get_current_user()
        from models import TimesheetPreview

        status_filter = request.args.get('status', 'pending')

        query = TimesheetPreview.query.filter_by(user_id=user.id)
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)

        entries = query.order_by(TimesheetPreview.created_at.desc()).all()

        return jsonify({
            'success': True,
            'entries': [entry.to_dict() for entry in entries],
            'preview_mode': PREVIEW_MODE
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/preview/approve', methods=['POST'])
@login_required
def approve_preview_entries():
    """Approve or reject preview entries"""
    try:
        user = get_current_user()
        data = request.get_json()
        entry_ids = data.get('entry_ids', [])
        action = data.get('action', 'approve')  # approve or reject
        review_notes = data.get('notes', '')

        from models import TimesheetPreview

        updated_entries = []

        for entry_id in entry_ids:
            entry = TimesheetPreview.query.filter_by(
                id=entry_id,
                user_id=user.id,
                status='pending'
            ).first()

            if entry:
                entry.status = 'approved' if action == 'approve' else 'rejected'
                entry.approved_by = user.id
                entry.approved_at = datetime.utcnow()
                entry.review_notes = review_notes
                updated_entries.append(entry.to_dict())

        db.session.commit()

        return jsonify({
            'success': True,
            'updated_entries': updated_entries,
            'action': action
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/preview/execute', methods=['POST'])
@login_required
def execute_approved_entries():
    """Execute approved preview entries by sending them to Harvest"""
    try:
        user = get_current_user()

        # 🔒 CRITICAL SECURITY CHECK: Validate user can perform timesheet operations
        if not validate_user_timesheet_access(user.id, "PREVIEW_EXECUTION"):
            return jsonify({
                'success': False,
                'error': 'SECURITY VIOLATION: Unauthorized timesheet access attempt'
            }), 403

        from models import TimesheetPreview

        # Get approved entries
        approved_entries = TimesheetPreview.query.filter_by(
            user_id=user.id,
            status='approved'
        ).all()

        if not approved_entries:
            return jsonify({
                'success': True,
                'message': 'No approved entries to execute',
                'results': {'successful': 0, 'failed': 0, 'errors': []}
            })

        results = {
            'total_approved': len(approved_entries),
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        for entry in approved_entries:
            try:
                # Execute the actual Harvest API call
                result, error = harvest_service.create_time_entry(
                    project_id=entry.project_id,
                    task_id=entry.task_id,
                    spent_date=entry.spent_date,
                    hours=entry.hours,
                    notes=entry.notes or '',
                    user_id=user.id
                )

                if result:
                    entry.status = 'executed'
                    entry.harvest_entry_id = result['id']
                    entry.executed_at = datetime.utcnow()
                    results['successful'] += 1

                    print(f"✅ Executed preview entry: {entry.project_name} ({entry.hours}h)")

                    # Log the activity
                    if MONITORING_ENABLED:
                        manual_log_activity(
                            user.id, user.email,
                            "PREVIEW_ENTRY_EXECUTED",
                            "/api/preview/execute",
                            True,
                            {"preview_id": entry.id, "harvest_id": result['id']}
                        )
                else:
                    entry.status = 'failed'
                    entry.execution_error = error
                    results['failed'] += 1
                    results['errors'].append(f"Entry {entry.id}: {error}")

                    print(f"❌ Failed to execute preview entry {entry.id}: {error}")

            except Exception as e:
                entry.status = 'failed'
                entry.execution_error = str(e)
                results['failed'] += 1
                results['errors'].append(f"Entry {entry.id}: {str(e)}")

                print(f"❌ Exception executing preview entry {entry.id}: {str(e)}")

        db.session.commit()

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Desktop app update check endpoint
@app.route('/api/check-updates', methods=['GET'])
def check_updates():
    """Check for application updates (desktop app only)"""
    try:
        from desktop_updater import check_for_updates_background
        update_info = check_for_updates_background()
        return jsonify(update_info or {'available': False})
    except ImportError:
        # desktop_updater not available (web app mode)
        return jsonify({'available': False})
    except Exception as e:
        logger.error(f"Error checking updates: {e}")
        return jsonify({'available': False, 'error': str(e)})


if __name__ == '__main__':
    # Use environment variable for port, default to 5001
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port, host='127.0.0.1')
