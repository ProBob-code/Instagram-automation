"""
IG Growth Hub - Configuration Management
Handles all configuration and environment variables
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
SESSIONS_DIR = DATA_DIR / 'sessions'

# Ensure directories exist
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Instagram Configuration
class InstagramConfig:
    USERNAME = os.getenv('IG_USERNAME', '')
    PASSWORD = os.getenv('IG_PASSWORD', '')
    
    # Rate Limits (per hour / per day)
    RATE_LIMITS = {
        'likes': {'per_hour': 30, 'per_day': 300, 'cooldown_min': 45, 'cooldown_max': 90},
        'follows': {'per_hour': 20, 'per_day': 150, 'cooldown_min': 60, 'cooldown_max': 120},
        'comments': {'per_hour': 10, 'per_day': 80, 'cooldown_min': 90, 'cooldown_max': 180},
        'dms': {'per_hour': 15, 'per_day': 100, 'cooldown_min': 60, 'cooldown_max': 120},
        'profile_visits': {'per_hour': 50, 'per_day': 400, 'cooldown_min': 20, 'cooldown_max': 40}
    }

# Threads Configuration
class ThreadsConfig:
    # Uses same credentials as Instagram
    RATE_LIMITS = {
        'likes': {'per_hour': 40, 'per_day': 400, 'cooldown_min': 30, 'cooldown_max': 60},
        'replies': {'per_hour': 20, 'per_day': 150, 'cooldown_min': 60, 'cooldown_max': 120},
        'follows': {'per_hour': 30, 'per_day': 200, 'cooldown_min': 45, 'cooldown_max': 90}
    }

# Browser Configuration
class BrowserConfig:
    HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'
    PROXY_URL = os.getenv('PROXY_URL', '')
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    VIEWPORT_SIZES = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900)
    ]

# SEO Scoring Weights
class SEOConfig:
    SCORE_WEIGHTS = {
        'bio': 25,
        'name': 15,
        'content': 20,
        'hashtags': 15,
        'engagement': 15,
        'completeness': 10
    }
    
    # Keywords that indicate niche presence
    NICHE_KEYWORDS = {
        'fitness': ['fitness', 'workout', 'gym', 'health', 'muscle', 'training', 'coach', 'fit'],
        'lifestyle': ['lifestyle', 'life', 'daily', 'routine', 'living', 'vibes'],
        'fashion': ['fashion', 'style', 'outfit', 'ootd', 'clothing', 'wear', 'designer'],
        'tech': ['tech', 'technology', 'developer', 'coding', 'programmer', 'software'],
        'food': ['food', 'foodie', 'recipe', 'cooking', 'chef', 'eat', 'restaurant'],
        'travel': ['travel', 'wanderlust', 'explore', 'adventure', 'trip', 'destination'],
        'beauty': ['beauty', 'makeup', 'skincare', 'cosmetics', 'glam', 'mua'],
        'business': ['entrepreneur', 'business', 'startup', 'founder', 'ceo', 'marketing']
    }

# Hashtag Templates by Niche
class HashtagConfig:
    TEMPLATES = {
        'fitness': {
            'niche': ['fitnesscreator', 'fitnesscoach', 'fitnesstips', 'workoutroutine'],
            'broad': ['fitnessmotivation', 'healthylifestyle', 'fitnessjourney'],
            'location': ['fitnessindia', 'fitnessusa', 'fitnesspakistan']
        },
        'lifestyle': {
            'niche': ['lifestylecreator', 'lifestyleblogger', 'dailylife'],
            'broad': ['lifestyle', 'lifestylephotography', 'lifestyleinspo'],
            'location': ['lifestyleindia', 'lifestyleusa']
        },
        'tech': {
            'niche': ['techcreator', 'techreviewer', 'techtips'],
            'broad': ['technology', 'technews', 'techworld'],
            'location': ['techindia', 'techstartup']
        },
        'default': {
            'niche': ['contentcreator', 'creator', 'reelscreator'],
            'broad': ['reels', 'trending', 'viral'],
            'location': ['india', 'usa', 'global']
        }
    }

# Server Configuration
class ServerConfig:
    HOST = os.getenv('SERVER_HOST', '127.0.0.1')
    PORT = int(os.getenv('SERVER_PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'ig-growth-hub-secret-key-change-in-production')
