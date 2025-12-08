"""
Role-Based Access Control System
Only authorized senior team members can access student records:
- Kayla, Abigail, and John (Wellbeing Officers)
- Course Lead access for attendance data
"""

import sqlite3
from functools import wraps
from flask import request, jsonify
import hashlib

DATABASE_PATH = 'user_data.db'

# Define authorized users and their roles
AUTHORIZED_USERS = {
    'kayla': {
        'password_hash': hashlib.sha256('kayla123'.encode()).hexdigest(),
        'role': 'wellbeing_officer',
        'name': 'Kayla',
        'permissions': ['view_stress', 'view_sleep', 'view_students', 'view_reports', 'view_notifications']
    },
    'abigail': {
        'password_hash': hashlib.sha256('abigail123'.encode()).hexdigest(),
        'role': 'wellbeing_officer',
        'name': 'Abigail',
        'permissions': ['view_stress', 'view_sleep', 'view_students', 'view_reports', 'view_notifications']
    },
    'john': {
        'password_hash': hashlib.sha256('john123'.encode()).hexdigest(),
        'role': 'wellbeing_officer',
        'name': 'John',
        'permissions': ['view_stress', 'view_sleep', 'view_students', 'view_reports', 'view_notifications']
    },
    'courselead': {
        'password_hash': hashlib.sha256('lead123'.encode()).hexdigest(),
        'role': 'course_lead',
        'name': 'Course Lead',
        'permissions': ['view_attendance', 'view_assignments', 'view_correlation', 'view_absent_students', 'view_notifications']
    },
    'admin': {
        'password_hash': hashlib.sha256('admin123'.encode()).hexdigest(),
        'role': 'admin',
        'name': 'Administrator',
        'permissions': ['all', 'manage_students', 'add_student', 'update_student', 'delete_student', 
                       'view_stress', 'view_sleep', 'view_students', 'view_reports', 'view_notifications',
                       'view_attendance', 'view_assignments', 'view_correlation', 'view_absent_students']
    }
}

# Session storage (in production, use Redis or database)
active_sessions = {}

def authenticate_user(username, password):
    """Authenticate user and return user info if valid"""
    username = username.lower()
    if username not in AUTHORIZED_USERS:
        return None
    
    user = AUTHORIZED_USERS[username]
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if user['password_hash'] == password_hash:
        return {
            'username': username,
            'name': user['name'],
            'role': user['role'],
            'permissions': user['permissions']
        }
    return None

def create_session(user_info):
    """Create a session token for authenticated user"""
    import secrets
    token = secrets.token_hex(32)
    active_sessions[token] = user_info
    return token

def get_user_from_token(token):
    """Get user info from session token"""
    return active_sessions.get(token)

def logout_user(token):
    """Remove user session"""
    if token in active_sessions:
        del active_sessions[token]
        return True
    return False

def require_auth(permission=None):
    """Decorator to require authentication and optionally check permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for token in header or query param
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                token = request.args.get('token', '')
            
            user = get_user_from_token(token)
            if not user:
                return jsonify({'error': 'Unauthorized. Please login first.'}), 401
            
            # Check permission if specified
            if permission and permission not in user['permissions'] and 'all' not in user['permissions']:
                return jsonify({'error': f'Access denied. You do not have {permission} permission.'}), 403
            
            # Add user to request context
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                token = request.args.get('token', '')
            
            user = get_user_from_token(token)
            if not user:
                return jsonify({'error': 'Unauthorized. Please login first.'}), 401
            
            if user['role'] not in roles and user['role'] != 'admin':
                return jsonify({'error': f'Access denied. Required role: {roles}'}), 403
            
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator
