# access.py

from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

login_manager = LoginManager()

# Define available roles and their descriptions
AVAILABLE_ROLES = {
    'admin': 'Full system access',
    'manager': 'Access to dashboards and reports',
    'warping': 'Access to warping operations',
    'sizing': 'Access to sizing operations',
    'production': 'Access to production data',
    'qc': 'Access to quality control operations',
    'viewer': 'View-only access to data',
    'grey_dispatch': 'Access to grey dispatch operations'
}

# Failed login attempt tracking
failed_attempts = {}
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 minutes

class User(UserMixin):
    def __init__(self, user_id, username, password_hash, roles):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.roles = roles

    @staticmethod
    def get(user_id):
        try:
            users = load_access_users()
            user_data = next((user for user in users if str(user.get('id')) == str(user_id)), None)
            if user_data:
                return User(
                    user_id=user_data['id'],
                    username=user_data['username'],
                    password_hash=user_data['password'],
                    roles=user_data.get('roles', [])
                )
        except Exception as e:
            logger.error(f"Error in User.get: {e}")
        return None

    @staticmethod
    def get_by_username(username):
        try:
            users = load_access_users()
            user_data = next((user for user in users if user['username'] == username), None)
            if user_data:
                return User(
                    user_id=user_data['id'],
                    username=user_data['username'],
                    password_hash=user_data['password'],
                    roles=user_data.get('roles', [])
                )
        except Exception as e:
            logger.error(f"Error in User.get_by_username: {e}")
        return None

def get_data_dir():
    """Get the data directory path with proper error handling"""
    try:
        # First try to get the directory from the current file's location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(os.path.dirname(current_dir), 'data')

        # If that doesn't exist, try the current working directory
        if not os.path.exists(data_dir):
            data_dir = os.path.join(os.getcwd(), 'data')

        # Create the directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        return data_dir
    except Exception as e:
        logger.error(f"Error getting data directory: {e}")
        # Fall back to current directory/data if all else fails
        return os.path.join(os.getcwd(), 'data')

def load_access_users():
    """Load access users with proper error handling"""
    try:
        data_dir = get_data_dir()
        user_file = os.path.join(data_dir, 'access_users.json')

        if not os.path.exists(user_file):
            return []

        with open(user_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading access users: {e}")
        return []

def save_access_users(users):
    """Save access users with proper error handling"""
    try:
        data_dir = get_data_dir()
        user_file = os.path.join(data_dir, 'access_users.json')

        # Create directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        with open(user_file, 'w') as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving access users: {e}")
        raise

def init_access_users():
    """Initialize access users with proper error handling"""
    try:
        data_dir = get_data_dir()
        user_file = os.path.join(data_dir, 'access_users.json')

        if not os.path.exists(user_file):
            users = [{
                'id': 1,
                'username': 'admin',
                'password': generate_password_hash('admin123'),
                'roles': ['admin'],
                'created_at': datetime.now().isoformat()
            }]
            save_access_users(users)
            logger.info("Created initial admin user")
    except Exception as e:
        logger.error(f"Error initializing access users: {e}")

def check_failed_attempts(username):
    """Check if user is locked out due to failed attempts"""
    if username in failed_attempts:
        attempts = failed_attempts[username]
        if attempts['count'] >= MAX_ATTEMPTS:
            if (datetime.now() - attempts['last_attempt']).total_seconds() < LOCKOUT_TIME:
                return False, f"Account is locked. Please try again in {LOCKOUT_TIME//60} minutes"
            else:
                failed_attempts.pop(username)  # Reset after lockout period
    return True, ""

def record_failed_attempt(username):
    """Record a failed login attempt"""
    if username not in failed_attempts:
        failed_attempts[username] = {'count': 1, 'last_attempt': datetime.now()}
    else:
        failed_attempts[username]['count'] += 1
        failed_attempts[username]['last_attempt'] = datetime.now()

def reset_failed_attempts(username):
    """Reset failed attempts after successful login"""
    if username in failed_attempts:
        failed_attempts.pop(username)

def roles_required(*roles):
    """Role-based access control decorator"""
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            try:
                if not current_user.is_authenticated:
                    return login_manager.unauthorized()

                if not hasattr(current_user, 'roles'):
                    logger.error("User object missing roles attribute")
                    return "Access Denied: User roles not found", 403

                if 'admin' in current_user.roles:
                    return fn(*args, **kwargs)

                user_roles = set(current_user.roles)
                required_roles = set(roles)

                if not required_roles.intersection(user_roles):
                    logger.warning(f"Access denied for user {current_user.username}. Required roles: {required_roles}, User roles: {user_roles}")
                    return "Access Denied: Insufficient permissions", 403

                return fn(*args, **kwargs)

            except Exception as e:
                logger.error(f"Error in roles_required decorator: {e}")
                return "Internal Server Error", 500

        return decorated_view
    return wrapper

def setup_access_management(app):
    """Set up access management with proper error handling"""
    try:
        login_manager.init_app(app)
        login_manager.login_view = 'login'
        login_manager.login_message = 'Please log in to access this page.'

        # Initialize session handling
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

        @login_manager.user_loader
        def load_user(user_id):
            return User.get(user_id)

        # Ensure data directory exists
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)

        # Initialize users file if needed
        init_access_users()

    except Exception as e:
        logger.error(f"Error setting up access management: {e}")
        raise

def init_access_routes(app):
    """Initialize access routes with proper error handling"""
    try:
        @app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')

                # Check for account lockout
                can_attempt, message = check_failed_attempts(username)
                if not can_attempt:
                    flash(message, 'error')
                    return redirect(url_for('login'))

                user = User.get_by_username(username)
                if user and check_password_hash(user.password_hash, password):
                    login_user(user)
                    reset_failed_attempts(username)
                    session.permanent = True
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('index'))

                record_failed_attempt(username)
                flash('Invalid username or password', 'error')

            return render_template('login.html')

        @app.route('/logout')
        @login_required
        def logout():
            logout_user()
            return redirect(url_for('login'))

        @app.route('/access/manage', methods=['GET', 'POST'])
        @login_required
        @roles_required('admin')
        def manage_access():
            try:
                if request.method == 'POST':
                    username = request.form.get('username')
                    password = request.form.get('password')
                    roles = request.form.getlist('roles')

                    # Validate input
                    if not username or not password:
                        flash('Username and password are required', 'error')
                        return redirect(url_for('manage_access'))

                    # Load existing users
                    users = load_access_users()

                    # Check for duplicate username
                    if any(user['username'] == username for user in users):
                        flash('Username already exists', 'error')
                        return redirect(url_for('manage_access'))

                    # Create new user
                    new_user = {
                        'id': len(users) + 1,
                        'username': username,
                        'password': generate_password_hash(password),
                        'roles': roles,
                        'created_at': datetime.now().isoformat()
                    }

                    # Save updated users list
                    users.append(new_user)
                    save_access_users(users)

                    flash('User added successfully', 'success')
                    return redirect(url_for('manage_access'))

                # GET request - display users
                users = load_access_users()
                return render_template(
                    'manage_access.html',
                    users=users,
                    available_roles=AVAILABLE_ROLES
                )

            except Exception as e:
                logger.error(f"Error in manage_access route: {e}")
                flash('An error occurred while managing access', 'error')
                return redirect(url_for('index'))

        @app.route('/access/users/<username>', methods=['DELETE'])
        @login_required
        @roles_required('admin')
        def delete_user(username):
            try:
                if username == 'admin':
                    return jsonify({'success': False, 'message': 'Cannot delete admin user'}), 400

                users = load_access_users()
                original_count = len(users)
                users = [user for user in users if user['username'] != username]

                if len(users) == original_count:
                    return jsonify({'success': False, 'message': 'User not found'}), 404

                save_access_users(users)
                return jsonify({'success': True, 'message': 'User deleted successfully'})

            except Exception as e:
                logger.error(f"Error deleting user: {e}")
                return jsonify({'success': False, 'message': 'Internal server error'}), 500

        @app.route('/access/users/<username>/roles', methods=['PUT'])
        @login_required
        @roles_required('admin')
        def update_user_roles(username):
            try:
                if username == 'admin':
                    return jsonify({'success': False, 'message': 'Cannot modify admin roles'}), 400

                roles = request.json.get('roles', [])
                users = load_access_users()

                user_index = next((index for index, user in enumerate(users)
                                if user['username'] == username), None)

                if user_index is None:
                    return jsonify({'success': False, 'message': 'User not found'}), 404

                users[user_index]['roles'] = roles
                save_access_users(users)

                return jsonify({'success': True, 'message': 'Roles updated successfully'})

            except Exception as e:
                logger.error(f"Error updating user roles: {e}")
                return jsonify({'success': False, 'message': 'Internal server error'}), 500

        @app.before_request
        def before_request():
            if current_user.is_authenticated:
                session.permanent = True
                current_time = datetime.now()
                last_active = session.get('last_active')

                if last_active:
                    last_active = datetime.fromisoformat(last_active)
                    if (current_time - last_active).total_seconds() > 18000:  # 300 minutes
                        logout_user()
                        flash('Your session has expired. Please login again.', 'info')
                        return redirect(url_for('login'))

                session['last_active'] = current_time.isoformat()

    except Exception as e:
        logger.error(f"Error initializing access routes: {e}")
        raise