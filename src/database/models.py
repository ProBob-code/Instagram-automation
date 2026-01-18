"""
IG Growth Hub - Database Models
User management, subscriptions, and usage tracking
"""

import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash
import enum

# Database URL from environment or default for local dev
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/ig_growth_hub.db')

# Handle Heroku/Railway postgres:// vs postgresql:// issue
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SubscriptionStatus(enum.Enum):
    """User subscription status"""
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class User(Base):
    """
    User account for IG Growth Hub
    Separate from Instagram credentials
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Subscription
    subscription_status = Column(String(20), default=SubscriptionStatus.TRIAL.value)
    trial_started_at = Column(DateTime, default=datetime.utcnow)
    trial_ends_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_ends_at = Column(DateTime, nullable=True)
    
    # Payment (Razorpay)
    razorpay_customer_id = Column(String(100), nullable=True)
    razorpay_subscription_id = Column(String(100), nullable=True)
    
    # Relationships
    instagram_accounts = relationship("InstagramAccount", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def is_trial_active(self) -> bool:
        """Check if user is in active trial period"""
        if self.subscription_status != SubscriptionStatus.TRIAL.value:
            return False
        return datetime.utcnow() < self.trial_ends_at
    
    def is_subscription_active(self) -> bool:
        """Check if user has active paid subscription"""
        if self.subscription_status != SubscriptionStatus.ACTIVE.value:
            return False
        if self.subscription_ends_at is None:
            return False
        return datetime.utcnow() < self.subscription_ends_at
    
    def can_access(self) -> bool:
        """Check if user can access the service"""
        return self.is_trial_active() or self.is_subscription_active()
    
    def days_remaining(self) -> int:
        """Get days remaining in trial or subscription"""
        if self.is_trial_active():
            delta = self.trial_ends_at - datetime.utcnow()
            return max(0, delta.days)
        elif self.is_subscription_active():
            delta = self.subscription_ends_at - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "subscription_status": self.subscription_status,
            "can_access": self.can_access(),
            "days_remaining": self.days_remaining(),
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "subscription_ends_at": self.subscription_ends_at.isoformat() if self.subscription_ends_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InstagramAccount(Base):
    """
    Linked Instagram accounts for a user
    Stores encrypted credentials for automation
    """
    __tablename__ = "instagram_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Instagram profile
    username = Column(String(100), nullable=False)
    # Note: In production, encrypt this with a proper encryption library
    encrypted_password = Column(Text, nullable=True)
    
    # Profile data (cached from Instagram)
    display_name = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    profile_pic_url = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_boost_at = Column(DateTime, nullable=True)
    
    # Profile score
    profile_score = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="instagram_accounts")
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "bio": self.bio,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "posts_count": self.posts_count,
            "profile_pic_url": self.profile_pic_url,
            "profile_score": self.profile_score,
            "is_active": self.is_active,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
        }


class UsageLog(Base):
    """
    Track daily usage for rate limiting and analytics
    """
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    date = Column(DateTime, default=datetime.utcnow)
    
    # Action counts
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    follows_count = Column(Integer, default=0)
    profile_visits_count = Column(Integer, default=0)
    
    # Boost sessions
    boost_sessions = Column(Integer, default=0)
    total_boost_minutes = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")
    
    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "follows_count": self.follows_count,
            "profile_visits_count": self.profile_visits_count,
            "boost_sessions": self.boost_sessions,
            "total_boost_minutes": self.total_boost_minutes,
        }


class Payment(Base):
    """
    Payment records for subscriptions
    """
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Razorpay details
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_signature = Column(String(255), nullable=True)
    
    # Payment info
    amount = Column(Integer, nullable=False)  # Amount in paise (300 INR = 30000)
    currency = Column(String(10), default="INR")
    status = Column(String(20), default="pending")  # pending, completed, failed, refunded
    
    # Subscription period this payment covers
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    
    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount / 100,  # Convert paise to rupees
            "currency": self.currency,
            "status": self.status,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "created_at": self.created_at.isoformat(),
        }


# Subscription plan configuration
SUBSCRIPTION_PLANS = {
    "monthly": {
        "name": "Monthly Plan",
        "price": 30000,  # 300 INR in paise
        "currency": "INR",
        "duration_days": 30,
        "features": [
            "Unlimited boost sessions",
            "AI-powered suggestions",
            "Profile analytics",
            "Priority support",
        ]
    }
}


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("[*] Database tables created successfully")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Run this file directly to create tables
    init_db()
