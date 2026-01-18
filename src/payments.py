"""
IG Growth Hub - Razorpay Payment Integration
Handles subscription payments (₹300/month)
"""

import os
import hmac
import hashlib
from datetime import datetime, timedelta
from flask import request, jsonify

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')

# Subscription price in paise (₹300 = 30000 paise)
SUBSCRIPTION_PRICE = 30000
SUBSCRIPTION_CURRENCY = 'INR'
SUBSCRIPTION_DURATION_DAYS = 30


def get_razorpay_client():
    """
    Get Razorpay client instance
    Requires: pip install razorpay
    """
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise ValueError("Razorpay API keys not configured")
    
    import razorpay
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verify Razorpay payment signature
    """
    body = f"{order_id}|{payment_id}"
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


def register_payment_routes(app):
    """
    Register payment routes with Flask app
    """
    from src.auth import auth_required
    from src.database import User, Payment, SessionLocal, SubscriptionStatus
    
    @app.route('/api/payments/create-order', methods=['POST'])
    @auth_required
    def create_payment_order():
        """
        Create Razorpay order for subscription payment
        """
        try:
            client = get_razorpay_client()
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        
        try:
            # Create Razorpay order
            order_data = {
                'amount': SUBSCRIPTION_PRICE,
                'currency': SUBSCRIPTION_CURRENCY,
                'receipt': f"user_{request.current_user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                'notes': {
                    'user_id': str(request.current_user_id),
                    'plan': 'monthly'
                }
            }
            
            order = client.order.create(data=order_data)
            
            # Save pending payment record
            db = SessionLocal()
            try:
                payment = Payment(
                    user_id=request.current_user_id,
                    razorpay_order_id=order['id'],
                    amount=SUBSCRIPTION_PRICE,
                    currency=SUBSCRIPTION_CURRENCY,
                    status='pending'
                )
                db.add(payment)
                db.commit()
            finally:
                db.close()
            
            return jsonify({
                'success': True,
                'order': {
                    'id': order['id'],
                    'amount': SUBSCRIPTION_PRICE,
                    'currency': SUBSCRIPTION_CURRENCY
                },
                'razorpay_key': RAZORPAY_KEY_ID,
                'prefill': {
                    'email': request.current_user_email
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/payments/verify', methods=['POST'])
    @auth_required
    def verify_payment():
        """
        Verify payment after Razorpay checkout completion
        Body: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
        """
        data = request.get_json()
        
        order_id = data.get('razorpay_order_id')
        payment_id = data.get('razorpay_payment_id')
        signature = data.get('razorpay_signature')
        
        if not all([order_id, payment_id, signature]):
            return jsonify({'success': False, 'error': 'Missing payment details'}), 400
        
        # Verify signature
        if not verify_payment_signature(order_id, payment_id, signature):
            return jsonify({'success': False, 'error': 'Invalid payment signature'}), 400
        
        db = SessionLocal()
        try:
            # Update payment record
            payment = db.query(Payment).filter(
                Payment.razorpay_order_id == order_id,
                Payment.user_id == request.current_user_id
            ).first()
            
            if not payment:
                return jsonify({'success': False, 'error': 'Payment not found'}), 404
            
            now = datetime.utcnow()
            payment.razorpay_payment_id = payment_id
            payment.razorpay_signature = signature
            payment.status = 'completed'
            payment.completed_at = now
            payment.period_start = now
            payment.period_end = now + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
            
            # Update user subscription
            user = db.query(User).filter(User.id == request.current_user_id).first()
            user.subscription_status = SubscriptionStatus.ACTIVE.value
            user.subscription_started_at = now
            user.subscription_ends_at = payment.period_end
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Payment successful! Subscription activated.',
                'subscription': {
                    'status': 'active',
                    'ends_at': payment.period_end.isoformat(),
                    'days_remaining': SUBSCRIPTION_DURATION_DAYS
                }
            })
            
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()
    
    @app.route('/api/payments/history', methods=['GET'])
    @auth_required
    def payment_history():
        """
        Get user's payment history
        """
        db = SessionLocal()
        try:
            payments = db.query(Payment).filter(
                Payment.user_id == request.current_user_id
            ).order_by(Payment.created_at.desc()).all()
            
            return jsonify({
                'success': True,
                'payments': [p.to_dict() for p in payments]
            })
            
        finally:
            db.close()
    
    @app.route('/api/payments/config', methods=['GET'])
    def get_payment_config():
        """
        Get payment configuration for frontend
        """
        return jsonify({
            'success': True,
            'config': {
                'price': SUBSCRIPTION_PRICE / 100,  # Convert to rupees
                'currency': SUBSCRIPTION_CURRENCY,
                'duration_days': SUBSCRIPTION_DURATION_DAYS,
                'razorpay_key': RAZORPAY_KEY_ID
            }
        })
    
    print("[*] Payment routes registered")
