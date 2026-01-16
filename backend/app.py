"""
IG Growth Hub - Flask Backend API
Main server handling login, analysis, and boost operations
"""

import os
import asyncio
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.seo.analyzer import analyze_profile
from src.rate_limiter import get_rate_limiter

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Global state
active_sessions = {}
boost_threads = {}


# ============================================
# STATIC FILE SERVING
# ============================================

@app.route('/')
def serve_index():
    """Serve the login page."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/dashboard.html')
def serve_dashboard():
    """Serve the dashboard page."""
    return send_from_directory(app.static_folder, 'dashboard.html')


@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files."""
    return send_from_directory(os.path.join(app.static_folder, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JS files."""
    return send_from_directory(os.path.join(app.static_folder, 'js'), filename)


# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/login', methods=['POST'])
def login():
    """
    Login endpoint - validates credentials and analyzes profile.
    In production, this would use Playwright to actually log in.
    For demo, we simulate the analysis.
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Username and password are required'
        }), 400
    
    try:
        # In production: Use Playwright to login and scrape profile
        # For now, generate demo data based on username
        profile = generate_demo_profile(username)
        
        # Analyze profile using SEO analyzer
        analysis = analyze_profile(profile)
        
        # Store session
        active_sessions[username] = {
            'logged_in': True,
            'profile': profile
        }
        
        return jsonify({
            'success': True,
            'profile': profile,
            'score': {
                'total': analysis['total'],
                'breakdown': {
                    k: {
                        'score': v['score'],
                        'max': v['max'],
                        'status': v['status']
                    } for k, v in analysis['breakdown'].items()
                }
            },
            'suggestions': analysis['suggestions']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get current user's profile data."""
    username = request.args.get('username')
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    return jsonify(active_sessions[username]['profile'])


@app.route('/api/score', methods=['GET'])
def get_score():
    """Get profile score breakdown."""
    username = request.args.get('username')
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    profile = active_sessions[username]['profile']
    analysis = analyze_profile(profile)
    
    return jsonify({
        'total': analysis['total'],
        'breakdown': analysis['breakdown']
    })


@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Get SEO improvement suggestions."""
    username = request.args.get('username')
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    profile = active_sessions[username]['profile']
    analysis = analyze_profile(profile)
    
    return jsonify({
        'suggestions': analysis['suggestions']
    })


@app.route('/api/boost/start', methods=['POST'])
def start_boost():
    """Start growth boost automation."""
    data = request.get_json()
    username = data.get('username')
    platform = data.get('platform', 'instagram')
    action = data.get('action', 'likes')
    intensity = data.get('intensity', 1)
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Check rate limits
    rate_limiter = get_rate_limiter()
    if not rate_limiter.can_perform_action(platform, action):
        remaining = rate_limiter.get_remaining(platform, action)
        return jsonify({
            'success': False,
            'error': 'Rate limit reached',
            'remaining': remaining
        }), 429
    
    # Start boost in background thread
    boost_id = f"{username}_{platform}_{action}"
    
    if boost_id in boost_threads and boost_threads[boost_id].is_alive():
        return jsonify({
            'success': False,
            'error': 'Boost already running'
        }), 400
    
    # Create boost thread
    thread = threading.Thread(
        target=run_boost,
        args=(username, platform, action, intensity)
    )
    thread.daemon = True
    thread.start()
    boost_threads[boost_id] = thread
    
    return jsonify({
        'success': True,
        'message': f'Started {action} boost on {platform}',
        'boost_id': boost_id
    })


@app.route('/api/boost/stop', methods=['POST'])
def stop_boost():
    """Stop running boost automation."""
    data = request.get_json()
    username = data.get('username')
    
    # Signal stop (in production, use proper thread signaling)
    boost_id = f"{username}_*"
    
    return jsonify({
        'success': True,
        'message': 'Boost stopping'
    })


@app.route('/api/boost/status', methods=['GET'])
def boost_status():
    """Get current boost status."""
    username = request.args.get('username')
    
    rate_limiter = get_rate_limiter()
    status = rate_limiter.get_status()
    
    # Check if any boosts running
    running = []
    for boost_id, thread in boost_threads.items():
        if username in boost_id and thread.is_alive():
            running.append(boost_id)
    
    return jsonify({
        'running': running,
        'limits': status
    })


@app.route('/api/limits', methods=['GET'])
def get_limits():
    """Get current rate limit status."""
    rate_limiter = get_rate_limiter()
    
    return jsonify({
        'instagram': {
            'likes': rate_limiter.get_remaining('instagram', 'likes'),
            'follows': rate_limiter.get_remaining('instagram', 'follows')
        },
        'threads': {
            'likes': rate_limiter.get_remaining('threads', 'likes'),
            'follows': rate_limiter.get_remaining('threads', 'follows')
        }
    })


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout and clear session."""
    data = request.get_json()
    username = data.get('username')
    
    if username in active_sessions:
        del active_sessions[username]
    
    return jsonify({'success': True})


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_demo_profile(username: str) -> dict:
    """Generate demo profile data for testing."""
    import random
    
    # Simulate different profile types
    profiles = {
        'optimized': {
            'bio': 'Fitness & lifestyle content\nHelping men stay lean & disciplined\nChennai 📍\n📩 contact@example.com',
            'name': f'{username.title()} | Fitness Creator',
            'posts': random.randint(50, 200),
            'followers': random.randint(5000, 50000),
            'following': random.randint(500, 2000),
            'has_highlights': True,
            'has_external_link': True,
            'captions': [
                'Full day fat loss routine for busy professionals. This workout helps burn fat without extreme cutting.',
                '5 habits that changed my fitness journey. Number 3 is often overlooked but crucial.',
                'Morning routine that keeps me consistent. Small steps lead to big changes.',
            ],
            'hashtags': [
                ['fitnesscreator', 'fitnessindia', 'workoutroutine', 'healthylifestyle', 'chennai'],
                ['morningroutine', 'fitnessjourney', 'lifestyle', 'motivation', 'india'],
            ]
        },
        'needs_work': {
            'bio': 'Content creator | DM for collabs',
            'name': username.title(),
            'posts': random.randint(10, 30),
            'followers': random.randint(500, 2000),
            'following': random.randint(800, 2000),
            'has_highlights': False,
            'has_external_link': False,
            'captions': [
                'Consistency is everything ❤️',
                '✨ Vibes ✨',
                'New post loading...',
            ],
            'hashtags': [
                ['love', 'instagood', 'photooftheday', 'beautiful', 'happy'],
                ['followme', 'like4like', 'follow4follow'],
            ]
        }
    }
    
    # Randomly select profile type (70% needs work for demo)
    profile_type = 'needs_work' if random.random() < 0.7 else 'optimized'
    template = profiles[profile_type]
    
    return {
        'username': username,
        'name': template['name'],
        'bio': template['bio'],
        'posts': template['posts'],
        'followers': template['followers'],
        'following': template['following'],
        'is_private': False,
        'has_profile_pic': True,
        'has_highlights': template['has_highlights'],
        'has_external_link': template['has_external_link'],
        'email': 'contact@example.com' if 'email' in template['bio'].lower() or '@' in template['bio'] else None,
        'captions': template['captions'],
        'hashtags': template['hashtags']
    }


def run_boost(username: str, platform: str, action: str, intensity: int):
    """
    Run boost automation in background.
    In production, this would use Playwright to perform actions.
    """
    import time
    from src.human_behavior import HumanBehavior
    
    rate_limiter = get_rate_limiter()
    behavior = HumanBehavior(intensity)
    
    # Calculate actions to perform
    actions_per_intensity = {1: 10, 2: 20, 3: 30}
    target_actions = actions_per_intensity.get(intensity, 10)
    
    completed = 0
    
    while completed < target_actions:
        # Check if we can perform action
        if not rate_limiter.can_perform_action(platform, action):
            print(f"Rate limit reached for {platform}/{action}")
            break
        
        # Simulate performing action
        time.sleep(behavior.get_session_length() / target_actions)
        
        # Record action
        rate_limiter.record_action(platform, action)
        completed += 1
        
        print(f"[{platform}] {action}: {completed}/{target_actions}")
        
        # Check if break needed
        if behavior.check_break_needed():
            print("Taking a break...")
            behavior.take_break()
    
    print(f"Boost complete: {completed} actions performed")


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("🔥 IG Growth Hub - Starting server...")
    print("📍 Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)
