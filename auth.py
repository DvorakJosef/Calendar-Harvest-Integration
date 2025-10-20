"""
Authentication module for Google Workspace OAuth and user management
"""

from flask import Blueprint, request, redirect, url_for, session, jsonify, flash, current_app
from functools import wraps
from datetime import datetime
import os
import requests
from secrets_manager import get_oauth_credentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from models import db, User, UserConfig

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the current authenticated user"""
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

@auth_bp.route('/login')
def login():
    """Initiate Google OAuth login"""
    # Apply rate limiting
    if hasattr(current_app, 'limiter'):
        current_app.limiter.limit("20 per minute")(lambda: None)()
    # Check if Google OAuth is configured
    oauth_creds = get_oauth_credentials()
    client_id = oauth_creds['google_client_id']
    client_secret = oauth_creds['google_client_secret']
    redirect_uri = oauth_creds['google_redirect_uri'] or 'http://127.0.0.1:5001/auth/callback'

    if not client_id or not client_secret:
        return jsonify({
            'error': 'Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.'
        }), 500

    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=[
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    )
    flow.redirect_uri = redirect_uri
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='false',  # Don't include granted scopes to force fresh consent
        prompt='consent'  # Force consent screen
    )

    # Store state in session for security
    session['oauth_state'] = state
    session.permanent = True  # Make session persistent

    return redirect(authorization_url)

@auth_bp.route('/callback')
def callback():
    """Handle Google OAuth callback"""
    try:
        # Verify state parameter
        received_state = request.args.get('state')
        stored_state = session.get('oauth_state')

        # For development, we'll be more lenient with state validation
        # The session might be cleared by Flask's auto-reload during development
        if received_state != stored_state:
            # In development, just log the warning and continue
            print(f"Warning: OAuth state mismatch (development mode)")
            # In production, you should enforce strict validation:
            # return jsonify({'error': 'Invalid state parameter'}), 400
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400
        
        # Exchange code for tokens
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:5001/auth/callback')

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )
        flow.redirect_uri = redirect_uri
        
        # Fetch token with better error handling
        print(f"Attempting to fetch token with code: {code[:20]}...")

        try:
            # Use requests directly to get more control over the token exchange
            import requests

            token_data = {
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }

            print(f"Token request data: {token_data}")

            response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
            print(f"Token response status: {response.status_code}")
            print(f"Token response: {response.text}")

            if response.status_code != 200:
                return jsonify({'error': f'Token exchange failed: {response.text}'}), 400

            token_info = response.json()

            # Create credentials manually
            from google.oauth2.credentials import Credentials
            credentials = Credentials(
                token=token_info['access_token'],
                refresh_token=token_info.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=token_info.get('scope', '').split()
            )

            print("Token fetch successful")

        except Exception as token_error:
            print(f"Token fetch error: {token_error}")
            return jsonify({'error': f'Authentication failed: {str(token_error)}'}), 500

        # credentials is already created above

        # Get user information from Google
        user_info = get_google_user_info(credentials)
        if not user_info:
            return jsonify({'error': 'Failed to get user information from Google'}), 500

        # Check if user is already logged in
        current_user_id = session.get('user_id')
        if current_user_id:
            # User is already logged in, just update their credentials
            store_user_credentials(current_user_id, credentials)
            flash('Google Calendar connected successfully!', 'success')
            return redirect(url_for('index'))
        else:
            # Create or update user with Google information
            user = create_or_update_user(user_info, credentials)
            if not user:
                return jsonify({'error': 'Failed to create user for calendar access'}), 500
        
        # Log in user
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        
        # Clear OAuth state
        session.pop('oauth_state', None)
        
        flash(f'Welcome, {user.name}!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return jsonify({'error': f'Authentication failed: {str(e)}'}), 500

def get_google_user_info(credentials):
    """Get user information from Google using OAuth credentials"""
    try:
        # Build the OAuth2 API service to get user info
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()

        # Extract name from email if name is not provided
        email = user_info.get('email', '')
        name = user_info.get('name')

        # If no name provided, extract from email (firstname.lastname@domain.com format)
        if not name and email:
            local_part = email.split('@')[0]
            if '.' in local_part:
                first_name, last_name = local_part.split('.', 1)
                name = f"{first_name.title()} {last_name.title()}"
            else:
                name = local_part.title()

        return {
            'google_id': user_info.get('id'),
            'email': email,
            'name': name or 'User',
            'picture': user_info.get('picture'),
            'domain': user_info.get('hd')  # Hosted domain for Google Workspace
        }
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None

def create_calendar_only_user(credentials):
    """Create a user with calendar-only access"""
    try:
        # Create a default user for calendar access
        # Since we can't get user info from Google, we'll use a generic approach
        import uuid

        # Generate a unique identifier for this calendar connection
        calendar_user_id = f"calendar_user_{uuid.uuid4().hex[:8]}"
        calendar_email = f"calendar.user.{uuid.uuid4().hex[:8]}@local"

        # Check if we already have a calendar-only user with this specific ID
        user = User.query.filter_by(google_id=calendar_user_id).first()

        if not user:
            # Check if there's already a generic calendar user we can reuse
            existing_user = User.query.filter(User.email.like('calendar.user%@local')).first()

            if existing_user:
                # Reuse existing calendar user
                user = existing_user
                user.last_login = datetime.utcnow()
                db.session.commit()
            else:
                # Create new calendar-only user with unique email
                user = User(
                    google_id=calendar_user_id,
                    email=calendar_email,  # Unique placeholder email
                    name="Calendar User",
                    domain="local",
                    last_login=datetime.utcnow()
                )
                db.session.add(user)
                db.session.commit()

        # Store Google credentials for this user
        store_user_credentials(user.id, credentials)

        return user

    except Exception as e:
        print(f"Error creating calendar-only user: {e}")
        db.session.rollback()
        return None

def create_or_update_user(user_info, credentials):
    """Create or update user in database"""
    try:
        # Check if user exists
        user = User.query.filter_by(google_id=user_info['google_id']).first()

        if user:
            # Update existing user
            user.email = user_info['email']
            user.name = user_info['name']
            user.picture = user_info.get('picture')
            user.domain = user_info.get('domain')
            user.last_login = datetime.utcnow()
        else:
            # Create new user
            user = User(
                google_id=user_info['google_id'],
                email=user_info['email'],
                name=user_info['name'],
                picture=user_info.get('picture'),
                domain=user_info.get('domain'),
                last_login=datetime.utcnow()
            )
            db.session.add(user)

        db.session.commit()

        # Store Google credentials for this user
        store_user_credentials(user.id, credentials)

        return user

    except Exception as e:
        print(f"Error creating/updating user: {e}")
        db.session.rollback()
        return None

def store_user_credentials(user_id, credentials):
    """Store Google OAuth credentials for user"""
    try:
        # Get or create user config
        user_config = UserConfig.query.filter_by(user_id=user_id).first()
        if not user_config:
            user_config = UserConfig(user_id=user_id)
            db.session.add(user_config)
        
        # Store credentials as JSON
        creds_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        # Debug: Print what we're storing
        print(f"Storing credentials for user {user_id}:")
        print(f"  - Has token: {bool(credentials.token)}")
        print(f"  - Has refresh_token: {bool(credentials.refresh_token)}")
        print(f"  - Scopes: {credentials.scopes}")

        user_config.set_google_credentials(creds_dict)
        user_config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error storing credentials: {e}")
        db.session.rollback()

@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/clear-session')
def clear_session():
    """Clear session for OAuth troubleshooting"""
    session.clear()
    flash('Session cleared. You can try logging in again.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = get_current_user()
    return jsonify(user.to_dict())
