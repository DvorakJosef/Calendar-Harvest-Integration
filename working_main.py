#!/usr/bin/env python3
"""
Working version of main.py that doesn't import the corrupted main.py
This recreates the main app functionality without the corruption
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

# Import modules individually (not from main.py)
from models import db, User, ProjectMapping, UserConfig, ProcessingHistory
from auth import auth_bp, login_required, get_current_user
from health_check import health_bp
from secrets_manager import get_flask_secret_key, get_database_url

print("🚀 Starting WORKING Calendar-Harvest Integration...")
print("📍 URL: http://127.0.0.1:5001")
print("✅ NOT importing from main.py")

# Create fresh Flask app
app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = get_flask_secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Initialize database
db.init_app(app)
print("✅ Database initialized")

# Add CSRF context processor for templates
@app.context_processor
def inject_csrf_token():
    """Make CSRF token available in templates"""
    try:
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    except:
        # If CSRF is not available, return empty function
        return dict(csrf_token=lambda: '')

print("✅ CSRF context processor added")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)
print("✅ Blueprints registered")

# Basic routes
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
    # Debug: Always show what user ID we have
    user = get_current_user()
    from models import UserConfig
    user_config = UserConfig.query.filter_by(user_id=user.id).first()
    print(f"🔍 DEBUG: App user {user.id} has stored Harvest user ID: {user_config.harvest_user_id if user_config else 'None'}")

    # Fix: Update incorrect harvest_user_id if needed
    if user_config and user_config.harvest_user_id == 1154003:
        print(f"🔧 FIXING: Updating incorrect Harvest user ID from {user_config.harvest_user_id} to 1459331")
        user_config.harvest_user_id = 1459331
        db.session.commit()
        print("✅ Fixed Harvest user ID!")
    elif user_config and user_config.harvest_user_id != 1459331:
        print(f"🔧 FIXING: Updating Harvest user ID from {user_config.harvest_user_id} to 1459331")
        user_config.harvest_user_id = 1459331
        db.session.commit()
        print("✅ Fixed Harvest user ID!")

    return render_template('process.html')

@app.route('/preview')
@login_required
def preview():
    """Preview page for manual timesheet review"""
    return render_template('preview.html')

# Add missing routes that templates expect
@app.route('/api/google/auth')
def google_auth():
    """Initiate Google OAuth flow"""
    return redirect(url_for('auth.login'))

@app.route('/auth/harvest')
@login_required
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

        # Redirect to Harvest for authorization
        return redirect(authorization_url)

    except Exception as e:
        print(f"Error starting Harvest OAuth: {e}")
        return redirect(url_for('setup') + f'?error=oauth_failed&message={str(e)}')

@app.route('/auth/harvest/callback')
@login_required
def harvest_oauth_callback():
    """Handle Harvest OAuth 2.0 callback"""
    try:
        user = get_current_user()

        # Get authorization code and state from callback
        code = request.args.get('code')
        state = request.args.get('state')

        if not code:
            return redirect(url_for('setup') + '?error=no_code')

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
            return redirect(url_for('setup') + '?error=user_mismatch')

        # Save OAuth token to user config
        user_config = UserConfig.query.filter_by(user_id=user.id).first()
        if not user_config:
            user_config = UserConfig(user_id=user.id)
            db.session.add(user_config)

        print(f"🔍 DEBUG: About to store OAuth token for user {user.id}")
        print(f"🔍 DEBUG: Token data contains harvest_user_id: {token_data.get('harvest_user_id')}")

        user_config.set_harvest_oauth_token(token_data)

        print(f"🔍 DEBUG: After setting token, user_config.harvest_user_id = {user_config.harvest_user_id}")

        # Force a flush and commit
        db.session.flush()
        db.session.commit()

        # Also update directly with SQL to ensure it's saved
        import sqlite3
        conn = sqlite3.connect('calendar_harvest.db')
        cursor = conn.cursor()

        # Update the record directly
        cursor.execute("""
            UPDATE user_config
            SET harvest_user_id = ?,
                harvest_user_email = ?,
                harvest_oauth_token = ?,
                harvest_account_name = ?
            WHERE user_id = ?
        """, (
            token_data.get('harvest_user_id'),
            token_data.get('harvest_user_email'),
            user_config.harvest_oauth_token,
            token_data.get('harvest_account_name'),
            user.id
        ))
        conn.commit()

        # Verify it was saved
        cursor.execute("SELECT harvest_user_id, harvest_user_email, harvest_oauth_token IS NOT NULL FROM user_config WHERE user_id = ?", (user.id,))
        raw_result = cursor.fetchone()
        conn.close()

        print(f"🔍 DEBUG: After direct SQL update = {raw_result}")

        print(f"✅ Harvest OAuth successful for user {user.email}")
        return redirect(url_for('setup') + '?success=harvest_connected')

    except Exception as e:
        print(f"❌ OAuth callback error: {e}")
        return redirect(url_for('setup') + f'?error=oauth_failed&message={str(e)}')

# API endpoints for setup page
@app.route('/api/google/status')
@login_required
def google_status():
    """Google Calendar connection status"""
    try:
        from google_calendar_service import GoogleCalendarService
        google_service = GoogleCalendarService()
        
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
            needs_refresh = 'refresh_token' in missing_fields
            return jsonify({
                'connected': True,
                'needs_refresh': needs_refresh,
                'user_info': {'email': user.email}
            })

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
    """Harvest connection status"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'connected': False, 'error': 'User not authenticated'})

        user_config = UserConfig.query.filter_by(user_id=user.id).first()

        if not user_config:
            return jsonify({'connected': False, 'debug': 'No user config found'})

        # Check if user has any Harvest authentication
        has_oauth = bool(user_config.harvest_oauth_token)
        has_legacy = bool(user_config.harvest_access_token)

        connected = has_oauth or has_legacy

        response_data = {
            'connected': connected
        }

        if connected and user_config.harvest_user_email:
            response_data['user_info'] = {
                'email': user_config.harvest_user_email,
                'account_name': user_config.harvest_account_name
            }

        if connected and user_config.harvest_user_email:
            response_data['user_info'] = {
                'email': user_config.harvest_user_email,
                'account_name': user_config.harvest_account_name
            }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error checking Harvest status: {e}")
        return jsonify({'connected': False, 'error': str(e)})

@app.route('/api/harvest/oauth/status')
@login_required
def harvest_oauth_status():
    """Harvest OAuth status"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'connected': False, 'error': 'User not authenticated'})
            
        user_config = UserConfig.query.filter_by(user_id=user.id).first()

        if not user_config:
            return jsonify({
                'success': True,
                'oauth_configured': False,
                'auth_method': None
            })

        # Check OAuth configuration
        oauth_configured = bool(user_config.harvest_oauth_access_token)
        
        response_data = {
            'success': True,
            'oauth_configured': oauth_configured,
            'auth_method': 'oauth' if oauth_configured else 'legacy',
            'harvest_user_email': user_config.harvest_user_email,
            'harvest_account_name': user_config.harvest_account_name,
            'token_valid': user_config.is_harvest_token_valid()
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error checking Harvest OAuth status: {e}")
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

@app.route('/api/harvest/time-entries')
@login_required
def get_harvest_time_entries():
    """Get time entries from Harvest for a date range"""
    try:
        user = get_current_user()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': 'start_date and end_date parameters are required'
            })

        # Parse dates
        from datetime import datetime
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
            })

        # Initialize Harvest service
        from harvest_service import HarvestService
        harvest_service = HarvestService()

        # Fix: Update incorrect harvest_user_id if needed
        from models import UserConfig
        user_config = UserConfig.query.filter_by(user_id=user.id).first()
        if user_config and user_config.harvest_user_id == 1154003:
            print(f"🔧 FIXING: Updating incorrect Harvest user ID from {user_config.harvest_user_id} to 1459331")
            user_config.harvest_user_id = 1459331
            db.session.commit()
            print("✅ Fixed Harvest user ID!")

        # Get entries from Harvest
        entries = harvest_service.get_time_entries(start_date_obj, end_date_obj, user_id=user.id)

        return jsonify({
            'success': True,
            'entries': entries,
            'count': len(entries),
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching time entries: {str(e)}'
        })

# Harvest API endpoints for mappings page
@app.route('/api/harvest/projects')
@login_required
def harvest_projects():
    """Get all Harvest projects"""
    try:
        user = get_current_user()
        from harvest_service import HarvestService
        harvest_service = HarvestService()

        projects = harvest_service.get_projects(user_id=user.id)

        # TEMPORARILY DISABLED FILTERING - SHOW ALL PROJECTS FOR DEBUGGING
        print(f"DEBUG: Found {len(projects)} projects from Harvest API:")
        for p in projects:
            print(f"  - {p['name']} (ID: {p['id']}) - Client: {p['client_name']}")

        return jsonify({
            'success': True,
            'projects': projects,  # Return ALL projects without filtering
            'mapped_combinations': []  # Empty for now
        })
    except Exception as e:
        print(f"Error getting Harvest projects: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/harvest/projects/<int:project_id>/tasks')
@login_required
def harvest_project_tasks(project_id):
    """Get tasks for a specific project"""
    try:
        user = get_current_user()
        from harvest_service import HarvestService
        harvest_service = HarvestService()

        tasks = harvest_service.get_project_tasks(project_id, user_id=user.id)

        # Get already mapped project-task combinations for this user
        mapped_combinations = set()
        existing_mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
        for mapping in existing_mappings:
            mapped_combinations.add((mapping.harvest_project_id, mapping.harvest_task_id))

        # Filter out already mapped tasks for this project
        available_tasks = [task for task in tasks
                          if (project_id, task['id']) not in mapped_combinations]

        return jsonify({'success': True, 'tasks': available_tasks})
    except Exception as e:
        print(f"Error getting project tasks: {e}")
        return jsonify({'success': False, 'error': str(e)})

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
        print(f"Error getting mappings: {e}")
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

        # Soft delete by setting is_active to False
        mapping.is_active = False
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error deleting mapping: {e}")
        return jsonify({'success': False, 'error': str(e)})


# OAuth status endpoints for setup page



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

# Calendar events endpoint for Process page
@app.route('/api/calendar/events')
@login_required
def calendar_events():
    """Get calendar events for processing"""
    try:
        user = get_current_user()

        # Get date range from query parameters
        week_start = request.args.get('week_start')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # If week_start is provided, calculate end date (week_start + 6 days)
        if week_start:
            from datetime import datetime, timedelta
            start_date = week_start
            start_dt = datetime.strptime(week_start, '%Y-%m-%d')
            end_dt = start_dt + timedelta(days=6)
            end_date = end_dt.strftime('%Y-%m-%d')
        elif not start_date or not end_date:
            return jsonify({'success': False, 'error': 'week_start or both start_date and end_date are required'})

        from google_calendar_service import GoogleCalendarService
        google_service = GoogleCalendarService()

        # Get events from Google Calendar
        from datetime import datetime
        week_start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        events = google_service.get_calendar_events(week_start=week_start_dt)

        return jsonify({
            'success': True,
            'events': events,
            'count': len(events) if events else 0
        })

    except Exception as e:
        print(f"Error getting calendar events: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/harvest/disconnect', methods=['POST'])
@login_required
def harvest_disconnect():
    """Disconnect Harvest account"""
    try:
        user = get_current_user()
        user_config = UserConfig.query.filter_by(user_id=user.id).first()

        if user_config:
            # Clear Harvest OAuth tokens
            user_config.clear_harvest_oauth()
            db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error disconnecting Harvest: {e}")
        return jsonify({'success': False, 'error': str(e)})


# Calendar API endpoints for mappings page
@app.route('/api/calendar/labels')
@login_required
def calendar_labels():
    """Get calendar event labels/summaries for mapping suggestions"""
    try:
        weeks = request.args.get('weeks', 12, type=int)
        min_frequency = request.args.get('min_frequency', 2, type=int)

        user = get_current_user()

        # Get calendar events from recent weeks
        from datetime import datetime, timedelta
        from google_calendar_service import GoogleCalendarService

        google_service = GoogleCalendarService()
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        events = google_service.get_calendar_events(week_start=start_date)

        # Count calendar labels (not event summaries)
        from collections import Counter
        label_counts = Counter()

        for event in events:
            # Use the extracted_label field which contains the actual calendar label
            extracted_label = event.get('extracted_label')
            if extracted_label:
                label_counts[extracted_label] += 1

        # Google Calendar color mapping (matching your actual colors)
        label_colors = {
            'Finshape': '#7ae7bf',          # Sage (light green)
            'Osobní': '#dbadff',            # Grape (purple)
            'Grada': '#ff887c',             # Flamingo (light orange)
            'ČSAS Promise': '#fbd75b',      # Banana (yellow)
            'AI': '#ffb878',                # Tangerine (orange)
            'DP': '#e1e1e1',                # Graphite (dark gray)
            'ČSAS Kalendář': '#5484ed',     # Blueberry (blue)
            'Sales': '#51b749',             # Basil (green)
            'Buřinka': '#dc2127'            # Tomato (red)
        }

        # Get already mapped labels for this user
        existing_mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).all()
        mapped_labels = {mapping.calendar_label for mapping in existing_mappings}

        # Show ALL labels (remove frequency restriction), exclude already mapped labels, and add color information
        frequent_labels = [
            {
                'label': label,
                'count': count,
                'color': label_colors.get(label, '#9fc6e7')  # Default to light blue
            }
            for label, count in label_counts.items()
            if label not in mapped_labels  # Only exclude already mapped labels
        ]

        # Also add any predefined labels that haven't been used recently but aren't mapped yet
        for predefined_label in label_colors.keys():
            if predefined_label not in mapped_labels and predefined_label not in [item['label'] for item in frequent_labels]:
                frequent_labels.append({
                    'label': predefined_label,
                    'count': 0,  # No recent usage
                    'color': label_colors[predefined_label]
                })

        # Sort by frequency (labels with usage first, then alphabetically)
        frequent_labels.sort(key=lambda x: (-x['count'], x['label']))

        return jsonify({
            'success': True,
            'labels': frequent_labels[:50]  # Limit to top 50
        })

    except Exception as e:
        print(f"Error getting calendar labels: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/bulk-mapping/pattern-rules')
@login_required
def pattern_rules():
    """Get pattern-based mapping rules"""
    try:
        user = get_current_user()

        # For now, return empty rules (can be enhanced later)
        return jsonify({
            'success': True,
            'rules': []
        })

    except Exception as e:
        print(f"Error getting pattern rules: {e}")
        return jsonify({'success': False, 'error': str(e)})



# Dashboard API endpoints
@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        user = get_current_user()

        # Get basic stats from database
        total_mappings = ProjectMapping.query.filter_by(user_id=user.id, is_active=True).count()

        # Simple stats for now (we can enhance later)
        return jsonify({
            'success': True,
            'mappings_count': total_mappings,
            'recent_entries': 0,  # Will implement when we have timesheet tracking
            'total_hours': 0.0,   # Will implement when we have timesheet tracking
            'last_processed_date': None
        })

    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
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

        from datetime import datetime
        week_start = datetime.fromisoformat(week_start_str).date()

        print(f"Preview: Week {week_start_str} -> {week_start}, {len(events)} events")

        # Import mapping engine
        from mapping_engine import MappingEngine
        mapping_engine = MappingEngine()

        results = mapping_engine.process_events_for_week(events, week_start, user.id)

        # Add grouping information
        timesheet_entries = results['timesheet_entries']

        # Group entries by date for better display
        from collections import defaultdict
        grouped_entries = defaultdict(list)
        for entry in timesheet_entries:
            entry_date = entry.get('spent_date', '')
            grouped_entries[entry_date].append(entry)

        # Convert to list of groups
        entry_groups = []
        for date, entries in sorted(grouped_entries.items()):
            total_hours = sum(float(entry.get('hours', 0)) for entry in entries)
            entry_groups.append({
                'date': date,
                'entries': entries,
                'total_hours': round(total_hours, 2)
            })

        return jsonify({
            'success': True,
            'timesheet_entries': results['timesheet_entries'],
            'entry_groups': entry_groups,
            'mapped_events': results['mapped_events'],
            'unmapped_events': results['unmapped_events'],
            'unmapped_events_details': results['unmapped_events_details'],
            'warnings': results['warnings']
        })

    except Exception as e:
        print(f"Error generating preview: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/process/execute', methods=['POST'])
@login_required
def process_execute():
    """Execute timesheet processing and submit to Harvest"""
    from datetime import datetime, timedelta
    print("🚀 PROCESSING EXECUTE ENDPOINT CALLED")
    try:
        user = get_current_user()
        print(f"👤 User: {user.id} ({user.email})")
        data = request.get_json()
        print(f"📦 Request data keys: {list(data.keys()) if data else 'None'}")

        # Get the timesheet entries from the request
        timesheet_entries = data.get('timesheet_entries', [])
        print(f"📊 Received {len(timesheet_entries)} timesheet entries to process")

        if not timesheet_entries:
            return jsonify({'success': False, 'error': 'No timesheet entries to process'})

        print(f"Execute: Processing {len(timesheet_entries)} timesheet entries for user {user.id}")

        # Debug: Log all entries being processed
        print("🔍 DETAILED ENTRY ANALYSIS:")
        total_hours_preview = 0
        for i, entry in enumerate(timesheet_entries):
            total_hours_preview += entry['hours']
            print(f"  {i+1}. {entry['event_summary']} | {entry['spent_date']} | {entry['hours']}h | Project: {entry['project_name']} | Task: {entry['task_name']}")
        print(f"📊 PREVIEW TOTALS: {len(timesheet_entries)} entries, {total_hours_preview} hours")

        # Initialize Harvest service
        from harvest_service import HarvestService
        harvest_service = HarvestService()

        # Clear any existing API logs
        harvest_service.clear_api_log()

        # Check if Harvest is connected
        if not harvest_service.is_connected(user_id=user.id):
            return jsonify({
                'success': False,
                'error': 'Harvest not connected. Please connect your Harvest account first.'
            })

        # Process each timesheet entry
        results = {
            'success': True,
            'total_entries': len(timesheet_entries),
            'successful_entries': 0,
            'skipped_entries': 0,
            'failed_entries': 0,
            'errors': [],
            'created_entries': [],
            'api_log': []  # Add API log tracking
        }

        # Add initial request to API log
        results['api_log'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'REQUEST',
            'method': 'POST',
            'url': '/api/process/execute',
            'status': 'RECEIVED',
            'data': {
                'week_start': data.get('week_start'),
                'timesheet_entries_count': len(timesheet_entries),
                'options': data.get('options', {})
            }
        })

        for i, entry in enumerate(timesheet_entries):
            print(f"\n🔄 Processing entry {i+1}/{len(timesheet_entries)}: {entry['event_summary']} ({entry['hours']}h) - Project: {entry['project_id']}, Task: {entry['task_id']}")
            try:
                # Convert spent_date string to date object if needed
                if isinstance(entry['spent_date'], str):
                    spent_date = datetime.fromisoformat(entry['spent_date']).date()
                else:
                    spent_date = entry['spent_date']

                # Create time entry in Harvest (returns tuple: result, error)
                harvest_entry, error = harvest_service.create_time_entry(
                    project_id=entry['project_id'],
                    task_id=entry['task_id'],
                    spent_date=spent_date,
                    hours=entry['hours'],
                    notes=entry['notes'],
                    user_id=user.id
                )

                if harvest_entry and not error:
                    results['successful_entries'] += 1
                    results['created_entries'].append({
                        'event_summary': entry['event_summary'],
                        'project_name': entry['project_name'],
                        'task_name': entry['task_name'],
                        'hours': entry['hours'],
                        'spent_date': entry['spent_date'],
                        'harvest_id': harvest_entry.get('id')
                    })
                    print(f"✅ Created Harvest entry: {entry['event_summary']} - {entry['hours']}h")

                    # 📋 LOG TO PROCESSING HISTORY
                    try:
                        from models import ProcessingHistory

                        # Determine week start date (Monday of the week containing spent_date)
                        week_start = spent_date - timedelta(days=spent_date.weekday())

                        processing_entry = ProcessingHistory(
                            user_id=user.id,
                            week_start_date=week_start,
                            calendar_event_id=entry.get('event_id', f"manual_{harvest_entry.get('id')}"),
                            calendar_event_summary=entry['event_summary'],
                            harvest_time_entry_id=harvest_entry.get('id'),
                            harvest_project_id=entry['project_id'],
                            harvest_task_id=entry['task_id'],
                            hours_logged=entry['hours'],
                            processed_at=datetime.utcnow(),
                            status='success'
                        )

                        db.session.add(processing_entry)
                        db.session.commit()

                        print(f"📋 LOGGED: Entry {harvest_entry.get('id')} logged to processing history")

                    except Exception as log_error:
                        print(f"⚠️ Warning: Failed to log to processing history: {log_error}")
                        # Don't fail the entire operation if logging fails
                else:
                    # Check if this is an "already exists" error (should be skipped, not failed)
                    if error and "already exists" in error:
                        results['skipped_entries'] += 1
                        print(f"⏭️ Skipped existing entry: {entry['event_summary']} - {error}")

                        # 📋 LOG SKIPPED ENTRY TO PROCESSING HISTORY
                        try:
                            from models import ProcessingHistory

                            # Determine week start date (Monday of the week containing spent_date)
                            week_start = spent_date - timedelta(days=spent_date.weekday())

                            processing_entry = ProcessingHistory(
                                user_id=user.id,
                                week_start_date=week_start,
                                calendar_event_id=entry.get('event_id', f"skipped_{int(datetime.utcnow().timestamp())}"),
                                calendar_event_summary=entry['event_summary'],
                                harvest_time_entry_id=None,  # Entry already exists
                                harvest_project_id=entry['project_id'],
                                harvest_task_id=entry['task_id'],
                                hours_logged=entry['hours'],
                                processed_at=datetime.utcnow(),
                                status='skipped',
                                error_message=error
                            )

                            db.session.add(processing_entry)
                            db.session.commit()

                            print(f"📋 LOGGED: Skipped entry logged to processing history")

                        except Exception as log_error:
                            print(f"⚠️ Warning: Failed to log skip to processing history: {log_error}")
                            # Don't fail the entire operation if logging fails
                    else:
                        results['failed_entries'] += 1
                        error_msg = error or f"Failed to create entry for: {entry['event_summary']}"
                        results['errors'].append(error_msg)
                        print(f"❌ Failed to create entry: {entry['event_summary']} - {error_msg}")

                        # 📋 LOG FAILED ENTRY TO PROCESSING HISTORY
                        try:
                            from models import ProcessingHistory

                            # Determine week start date (Monday of the week containing spent_date)
                            week_start = spent_date - timedelta(days=spent_date.weekday())

                            processing_entry = ProcessingHistory(
                                user_id=user.id,
                                week_start_date=week_start,
                                calendar_event_id=entry.get('event_id', f"failed_{int(datetime.utcnow().timestamp())}"),
                                calendar_event_summary=entry['event_summary'],
                                harvest_time_entry_id=None,  # No entry created
                                harvest_project_id=entry['project_id'],
                                harvest_task_id=entry['task_id'],
                                hours_logged=entry['hours'],
                                processed_at=datetime.utcnow(),
                                status='error',
                                error_message=error_msg
                            )

                            db.session.add(processing_entry)
                            db.session.commit()

                            print(f"📋 LOGGED: Failed entry logged to processing history")

                        except Exception as log_error:
                            print(f"⚠️ Warning: Failed to log error to processing history: {log_error}")
                            # Don't fail the entire operation if logging fails

            except Exception as entry_error:
                results['failed_entries'] += 1
                error_msg = f"Error processing '{entry['event_summary']}': {str(entry_error)}"
                results['errors'].append(error_msg)
                print(f"❌ {error_msg}")

        # Update success status based on results
        # Consider it successful if we processed all entries without unexpected errors
        results['success'] = results['failed_entries'] == 0

        print(f"Execute complete: {results['successful_entries']} created, {results['skipped_entries']} skipped, {results['failed_entries']} failed out of {results['total_entries']} total entries")

        # Debug: Show actual totals
        actual_hours_created = sum(entry['hours'] for entry in results['created_entries'])
        print(f"📊 ACTUAL RESULTS: {results['successful_entries']} entries created, {actual_hours_created} hours")

        if results['skipped_entries'] > 0:
            print(f"⏭️ SKIPPED ENTRIES: {results['skipped_entries']} entries (already existed)")

        if results['failed_entries'] > 0:
            print(f"❌ FAILED ENTRIES: {results['failed_entries']} entries")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")

        # Collect API logs from HarvestService
        harvest_api_logs = harvest_service.get_api_log()
        results['api_log'].extend(harvest_api_logs)

        # Add final response log
        results['api_log'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'RESPONSE',
            'method': 'POST',
            'url': '/api/process/execute',
            'status': 'SUCCESS' if results['success'] else 'PARTIAL_SUCCESS',
            'status_code': 200,
            'data': {
                'success': results['success'],
                'total_entries': results['total_entries'],
                'successful_entries': results['successful_entries'],
                'skipped_entries': results['skipped_entries'],
                'failed_entries': results['failed_entries'],
                'errors_count': len(results['errors'])
            }
        })

        return jsonify(results)

    except Exception as e:
        print(f"Error executing timesheet processing: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to process timesheets: {str(e)}'
        })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    print("🎯 Starting working Flask server on port 5001...")
    app.run(debug=True, port=5001, host='127.0.0.1')
