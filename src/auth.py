"""
IG Growth Hub - User Authentication System
Handles registration, login, JWT tokens, and session management
"""

import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

# JWT Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
JWT_ALGORITHM = 'HS256'


def generate_token(user_id: int, email: str) -> str:
    """
    Generate JWT token for authenticated user
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token
    Returns payload if valid, raises exception otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def get_token_from_request():
    """
    Extract JWT token from request headers
    Supports: Authorization: Bearer <token>
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def auth_required(f):
    """
    Decorator to require authentication for routes
    Adds 'current_user' to kwargs
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        try:
            payload = decode_token(token)
            # Add user info to request context
            request.current_user_id = payload['user_id']
            request.current_user_email = payload['email']
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'code': 'INVALID_TOKEN'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated


def subscription_required(f):
    """
    Decorator to require active subscription (or trial) for routes
    Must be used after @auth_required
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from src.database import User, SessionLocal
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == request.current_user_id).first()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found',
                    'code': 'USER_NOT_FOUND'
                }), 404
            
            if not user.can_access():
                return jsonify({
                    'success': False,
                    'error': 'Subscription expired. Please upgrade to continue.',
                    'code': 'SUBSCRIPTION_EXPIRED',
                    'subscription_status': user.subscription_status,
                    'trial_ended': not user.is_trial_active()
                }), 403
            
            # Add full user object to request
            request.current_user = user
            
        finally:
            db.close()
        
        return f(*args, **kwargs)
    
    return decorated


# ============================================
# AUTH API ROUTES (to be registered with Flask app)
# ============================================

def register_auth_routes(app):
    """
    Register authentication routes with Flask app
    """
    from src.database import User, SessionLocal
    
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        """
        Register a new user account
        Body: { email, password, full_name? }
        """
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        # Validation
        if not email or '@' not in email:
            return jsonify({'success': False, 'error': 'Valid email required'}), 400
        
        if len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400
        
        db = SessionLocal()
        try:
            # Check if email exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return jsonify({'success': False, 'error': 'Email already registered'}), 400
            
            # Create user with 30-day trial
            user = User(
                email=email,
                full_name=full_name if full_name else None,
                trial_started_at=datetime.utcnow(),
                trial_ends_at=datetime.utcnow() + timedelta(days=30)
            )
            user.set_password(password)
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Generate token
            token = generate_token(user.id, user.email)
            
            return jsonify({
                'success': True,
                'message': 'Account created! You have 30 days free trial.',
                'token': token,
                'user': user.to_dict()
            })
            
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/auth/login', methods=['POST'])
    def auth_login():
        """
        Login with email and password
        Body: { email, password }
        """
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user or not user.check_password(password):
                return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
            
            if not user.is_active:
                return jsonify({'success': False, 'error': 'Account is disabled'}), 403
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            # Generate token
            token = generate_token(user.id, user.email)
            
            return jsonify({
                'success': True,
                'token': token,
                'user': user.to_dict()
            })
            
        finally:
            db.close()
    
    @app.route('/api/auth/me', methods=['GET'])
    @auth_required
    def get_current_user():
        """
        Get current user profile
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == request.current_user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            return jsonify({
                'success': True,
                'user': user.to_dict()
            })
            
        finally:
            db.close()
    
    @app.route('/api/auth/subscription-status', methods=['GET'])
    @auth_required
    def get_subscription_status():
        """
        Get detailed subscription status for payment page
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == request.current_user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            return jsonify({
                'success': True,
                'subscription': {
                    'status': user.subscription_status,
                    'can_access': user.can_access(),
                    'is_trial': user.is_trial_active(),
                    'is_subscribed': user.is_subscription_active(),
                    'days_remaining': user.days_remaining(),
                    'trial_ends_at': user.trial_ends_at.isoformat() if user.trial_ends_at else None,
                    'subscription_ends_at': user.subscription_ends_at.isoformat() if user.subscription_ends_at else None,
                }
            })
            
        finally:
            db.close()
    
    print("[*] Auth routes registered")
