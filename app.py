"""
IG Growth Hub - Flask Backend API
Main server handling login, analysis, and boost operations
"""

import os
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import asyncio
import random
from datetime import datetime

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.seo.analyzer import analyze_profile
from src.rate_limiter import get_rate_limiter

# Initialize Flask app
app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Global state
active_sessions = {}
boost_threads = {}

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)


def run_async_in_thread(coro):
    """Run an async coroutine in a separate thread with its own event loop."""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    future = executor.submit(run)
    return future.result(timeout=120)  # 2 minute timeout


# ============================================
# HEALTH CHECK FOR DOCKER/RAILWAY
# ============================================

@app.route('/health')
def health_check():
    """Health check endpoint for Docker/Railway deployment."""
    return jsonify({
        'status': 'healthy',
        'service': 'ig-growth-hub',
        'timestamp': datetime.utcnow().isoformat()
    })


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


@app.route('/api/profile-pic/<username>')
def serve_profile_pic(username):
    """Serve locally downloaded profile picture."""
    pics_dir = Path(__file__).parent / 'data' / 'profile_pics'
    
    # Try different extensions
    for ext in ['jpg', 'png', 'webp']:
        pic_path = pics_dir / f"{username}.{ext}"
        if pic_path.exists():
            return send_from_directory(pics_dir, f"{username}.{ext}")
    
    # Return placeholder if not found
    return jsonify({'error': 'Profile pic not found'}), 404


# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/login', methods=['POST'])
def login():
    """
    Login endpoint - authenticates with Instagram and scrapes real profile data.
    Uses Playwright for browser automation.
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
        print(f"[*] Starting login for {username}...")
        result = run_async_in_thread(async_login(username, password))
        return jsonify(result[0]), result[1]
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


async def async_login(username: str, password: str):
    """Async login and profile scraping."""
    global active_sessions
    
    # Import here to avoid issues at startup
    from src.browser import BrowserManager
    from src.instagram.auth import InstagramAuth
    from src.instagram.scraper import InstagramScraper
    
    browser = None
    
    try:
        # Create browser instance
        print(f"[*] Starting Chromium browser...")
        browser = BrowserManager(headless=True)  # Headless - completely invisible
        await browser.start(session_name=username)
        
        # Authenticate
        print(f"[*] Navigating to Instagram login...")
        auth = InstagramAuth(browser)
        success, message = await auth.login(username, password)
        
        if not success:
            if message == "2FA_REQUIRED":
                # Store partial session for 2FA completion
                active_sessions[username] = {
                    'logged_in': False,
                    'awaiting_2fa': True,
                    'browser': browser,
                    'auth': auth
                }
                return ({
                    'success': False,
                    'requires_2fa': True,
                    'message': 'Please enter your 2FA verification code'
                }, 200)
            else:
                # Login failed - close browser
                await browser.close(save_session=False)
                return ({
                    'success': False,
                    'error': message
                }, 401)
        
        # Login successful - scrape profile
        print(f"[*] Login successful! Scraping profile data...")
        scraper = InstagramScraper(browser)
        profile = await scraper.scrape_profile(username)
        
        # Analyze profile using SEO analyzer
        analysis = analyze_profile(profile)
        
        # Close browser and SAVE SESSION to disk (boost will load it fresh)
        print(f"[*] Saving session and closing browser...")
        await browser.close(save_session=True, session_name=username)
        
        # Store session data (browser is closed, boost creates fresh one)
        active_sessions[username] = {
            'logged_in': True,
            'profile': profile,
            'browser': None,  # Browser closed
            'auth': None
        }
        
        print(f"[*] Profile scraped successfully!")
        
        return ({
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
        }, 200)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        if browser:
            try:
                await browser.close(save_session=False)
            except:
                pass
        
        return ({
            'success': False,
            'error': str(e)
        }, 500)


@app.route('/api/submit-2fa', methods=['POST'])
def submit_2fa():
    """Submit 2FA verification code to complete login."""
    data = request.get_json()
    username = data.get('username', '').strip()
    code = data.get('code', '').strip()
    
    if not username or not code:
        return jsonify({
            'success': False,
            'error': 'Username and 2FA code are required'
        }), 400
    
    if username not in active_sessions:
        return jsonify({
            'success': False,
            'error': 'No pending 2FA session found'
        }), 404
    
    session = active_sessions[username]
    if not session.get('awaiting_2fa'):
        return jsonify({
            'success': False,
            'error': 'No 2FA required for this session'
        }), 400
    
    try:
        result = run_async_in_thread(async_submit_2fa(username, code))
        return jsonify(result[0]), result[1]
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


async def async_submit_2fa(username: str, code: str):
    """Async 2FA submission."""
    global active_sessions
    
    from src.instagram.scraper import InstagramScraper
    
    session = active_sessions[username]
    auth = session['auth']
    browser = session['browser']
    
    try:
        success, message = await auth.submit_2fa_code(code)
        
        if not success:
            return ({
                'success': False,
                'error': message
            }, 401)
        
        # 2FA successful - scrape profile
        print(f"[*] 2FA verified! Scraping profile data...")
        scraper = InstagramScraper(browser)
        profile = await scraper.scrape_profile(username)
        
        # Analyze profile
        analysis = analyze_profile(profile)
        
        # Update session
        active_sessions[username] = {
            'logged_in': True,
            'profile': profile,
            'browser': browser,
            'auth': auth
        }
        
        return ({
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
        }, 200)
        
    except Exception as e:
        return ({
            'success': False,
            'error': str(e)
        }, 500)


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get current user's profile data."""
    username = request.args.get('username')
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    return jsonify(active_sessions[username].get('profile', {}))


@app.route('/api/score', methods=['GET'])
def get_score():
    """Get profile score breakdown."""
    username = request.args.get('username')
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    profile = active_sessions[username].get('profile', {})
    if profile:
        analysis = analyze_profile(profile)
        return jsonify({
            'total': analysis['total'],
            'breakdown': analysis['breakdown']
        })
    
    return jsonify({'error': 'No profile data'}), 404


@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Get SEO improvement suggestions."""
    username = request.args.get('username')
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    profile = active_sessions[username].get('profile', {})
    if profile:
        analysis = analyze_profile(profile)
        return jsonify({
            'suggestions': analysis['suggestions']
        })
    
    return jsonify({'error': 'No profile data'}), 404


@app.route('/api/ai/suggestions', methods=['GET'])
def get_ai_suggestions():
    """Get AI-generated copy-paste ready suggestions using Groq."""
    from src.ai_assistant import get_ai_assistant
    
    username = request.args.get('username')
    suggestion_type = request.args.get('type', 'bio')  # bio, caption, hashtag
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    profile = active_sessions[username].get('profile', {})
    if not profile:
        return jsonify({'error': 'No profile data'}), 404
    
    ai = get_ai_assistant()
    
    try:
        if suggestion_type == 'bio':
            suggestions = ai.generate_bio_suggestions(profile)
            return jsonify({'type': 'bio', 'suggestions': suggestions})
        
        elif suggestion_type == 'caption':
            topic = request.args.get('topic', '')
            suggestions = ai.generate_caption_suggestions(profile, topic)
            return jsonify({'type': 'caption', 'suggestions': suggestions})
        
        elif suggestion_type == 'hashtag':
            strategy = ai.generate_hashtag_strategy(profile)
            return jsonify({'type': 'hashtag', 'strategy': strategy})
        
        else:
            return jsonify({'error': 'Invalid type'}), 400
            
    except Exception as e:
        print(f"[AI] Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/boost/start', methods=['POST'])
def start_boost():
    """Start growth boost automation with task tracking."""
    from src.action_tracker import get_tracker
    
    data = request.get_json()
    username = data.get('username')
    platform = data.get('platform', 'instagram')
    action_types = data.get('actions', ['likes'])  # Now supports multiple: ['likes', 'follows', 'comments', 'views']
    intensity = data.get('intensity', 1)
    comment_templates = data.get('comment_templates', [])  # Random comments for comment action
    target_hashtags = data.get('target_hashtags', []) # Frontend keywords
    
    if username not in active_sessions:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Check rate limits for each action
    rate_limiter = get_rate_limiter()
    for action in action_types:
        if not rate_limiter.can_perform_action(platform, action):
            remaining = rate_limiter.get_remaining(platform, action)
            return jsonify({
                'success': False,
                'error': f'Rate limit reached for {action}',
                'remaining': remaining
            }), 429
    
    # Calculate target actions based on intensity
    actions_per_intensity = {1: 10, 2: 20, 3: 30}
    target_count = actions_per_intensity.get(intensity, 10) * len(action_types)
    
    # Create task with tracker
    tracker = get_tracker()
    task_id = tracker.create_task(
        username=username,
        action_types=action_types,
        platform=platform,
        intensity=intensity,
        target_count=target_count
    )
    
    # Store comment templates in session for boost thread to use
    active_sessions[username]['comment_templates'] = comment_templates
    active_sessions[username]['current_task_id'] = task_id
    
    # Start boost in background thread
    if task_id in boost_threads and boost_threads[task_id].is_alive():
        return jsonify({
            'success': False,
            'error': 'Boost already running'
        }), 400
    
    # Create boost thread with all parameters
    thread = threading.Thread(
        target=run_boost,
        args=(username, platform, action_types, intensity, task_id, comment_templates, target_hashtags)
    )
    thread.daemon = True
    thread.start()
    boost_threads[task_id] = thread
    
    return jsonify({
        'success': True,
        'message': f'Started boost on {platform}',
        'task_id': task_id,
        'target_count': target_count,
        'action_types': action_types
    })


@app.route('/api/boost/stop', methods=['POST'])
def stop_boost():
    """Stop running boost automation."""
    from src.action_tracker import get_tracker
    
    data = request.get_json()
    username = data.get('username')
    task_id = data.get('task_id')
    
    if task_id:
        tracker = get_tracker()
        tracker.pause_task(task_id)
        
        # Save report for whatever was done before stopping
        report_path = tracker.save_report(task_id)
        print(f"[Boost] Stopped. Partial report saved: {report_path}")
    
    return jsonify({
        'success': True,
        'message': 'Boost stopped',
        'report_saved': True if task_id else False
    })


@app.route('/api/boost/progress/<task_id>', methods=['GET'])
def get_boost_progress(task_id):
    """Get real-time progress of a boost task."""
    from src.action_tracker import get_tracker
    
    tracker = get_tracker()
    progress = tracker.get_progress(task_id)
    
    if not progress:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(progress)


@app.route('/api/boost/report/<task_id>', methods=['GET'])
def get_boost_report(task_id):
    """Get detailed report of all actions in a boost task."""
    from src.action_tracker import get_tracker
    
    tracker = get_tracker()
    report = tracker.get_report(task_id)
    
    if not report:
        return jsonify({'error': 'Task not found'}), 404
    
    # Add summary stats
    summary = tracker.get_summary_stats(task_id)
    report['summary'] = summary
    
    return jsonify(report)


@app.route('/api/reports', methods=['GET'])
def list_reports():
    """List all saved boost reports."""
    from pathlib import Path
    import json
    
    reports_dir = Path(__file__).parent / 'data' / 'reports'
    reports = []
    
    if reports_dir.exists():
        for report_file in reports_dir.glob('boost_report_*.json'):
            try:
                with open(report_file, 'r') as f:
                    data = json.load(f)
                    summary = data.get('summary', {})
                    total = summary.get('total_actions', data.get('total_actions', 0))
                    success = summary.get('successful', 0)
                    skipped = total - success
                    
                    reports.append({
                        'filename': report_file.name,
                        'task_id': data.get('task_id', ''),
                        'username': data.get('username', ''),
                        'platform': data.get('platform', ''),
                        'status': data.get('status', ''),
                        'total_actions': total,
                        'successful_actions': success,
                        'skipped_actions': skipped,
                        'created_at': data.get('created_at', ''),
                        'completed_at': data.get('completed_at', ''),
                        'action_types': data.get('action_types', [])
                    })
            except:
                continue
    
    # Sort by created_at date descending (newest first)
    reports.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return jsonify({'reports': reports})


@app.route('/api/reports/<filename>', methods=['GET'])
def get_report_file(filename):
    """Get a specific report file."""
    from pathlib import Path
    import json
    
    reports_dir = Path(__file__).parent / 'data' / 'reports'
    report_path = reports_dir / filename
    
    if report_path.exists() and report_path.suffix == '.json':
        try:
            with open(report_path, 'r') as f:
                return jsonify(json.load(f))
        except:
            return jsonify({'error': 'Failed to read report'}), 500
    
    return jsonify({'error': 'Report not found'}), 404


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get aggregated analytics data for the user."""
    from src.action_tracker import get_tracker
    
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Username required'}), 400
        
    tracker = get_tracker()
    try:
        analytics = tracker.get_analytics(username)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/boost/status', methods=['GET'])
def boost_status():
    """Get current boost status."""
    from src.action_tracker import get_tracker
    
    username = request.args.get('username')
    
    rate_limiter = get_rate_limiter()
    tracker = get_tracker()
    
    # Get current task if any
    current_task = None
    if username in active_sessions:
        task_id = active_sessions[username].get('current_task_id')
        if task_id:
            current_task = tracker.get_progress(task_id)
    
    # Check if any boosts running
    running = []
    for boost_id, thread in boost_threads.items():
        if thread.is_alive():
            running.append(boost_id)
    
    return jsonify({
        'running': running,
        'current_task': current_task,
        'limits': rate_limiter.get_status()
    })


@app.route('/api/rate-limits/<platform>', methods=['GET'])
def get_rate_limits(platform):
    """Get current rate limits and usage for a platform."""
    rl = get_rate_limiter()
    status = rl.get_status(platform)
    return jsonify(status.get(platform, {}))


@app.route('/api/limits', methods=['GET'])
def get_limits():
    """Get full rate limit status for all platforms."""
    rate_limiter = get_rate_limiter()
    return jsonify(rate_limiter.get_status())


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout and clear session."""
    data = request.get_json()
    username = data.get('username')
    
    # Close browser if open
    if username in active_sessions:
        session = active_sessions[username]
        browser = session.get('browser')
        if browser:
            try:
                run_async_in_thread(browser.close(save_session=True, session_name=username))
            except:
                pass
        del active_sessions[username]
    
    return jsonify({'success': True})


# ============================================
# HELPER FUNCTIONS
# ============================================

def run_boost(username: str, platform: str, action_types: list, intensity: int, task_id: str, comment_templates: list, target_hashtags: list = None):
    """
    Run REAL boost automation with action tracking.
    Uses actual Instagram interactions via browser automation.
    """
    import sys
    import time
    import random
    import asyncio
    from src.human_behavior import HumanBehavior
    from src.action_tracker import get_tracker
    from src.browser import BrowserManager
    from src.instagram.explorer import InstagramExplorer
    from src.instagram.actions import InstagramActions
    
    rate_limiter = get_rate_limiter()
    behavior = HumanBehavior(intensity)
    tracker = get_tracker()
    
    # Intensity controls target actions PER HASHTAG:
    # User requested: 10 likes per hashtag (so 2 hashtags = 20 likes)
    likes_per_hashtag = 10
    
    print(f"[Boost] Starting boost {task_id}: {action_types} on {platform}", flush=True)
    
    # Use provided hashtags/keywords, fallback to config file if empty
    if not target_hashtags:
        print("[Boost] No frontend keywords provided, checking config file...")
        config_path = Path(__file__).parent / 'data' / 'target_hashtags.txt'
        target_hashtags = []
        if config_path.exists():
            with open(config_path, 'r') as f:
                for line in f:
                    tag = line.strip()
                    if tag and not tag.startswith('#'):
                        target_hashtags.append(tag)
    
    # Ensure strict limit
    target_hashtags = target_hashtags[:10]
    print(f"[Boost] Target keywords/hashtags: {target_hashtags}")

    async def run_real_boost():
                line = line.strip()
                if line and not line.startswith('#'):
                    target_hashtags.append(line.replace('#', ''))
    
    # Fallback hashtags if config is empty
    if not target_hashtags:
        target_hashtags = ['photography', 'lifestyle', 'motivation']
    
    # Limit to 3 hashtags per session
    target_hashtags = target_hashtags[:3]
    print(f"[Boost] Target hashtags from config: {target_hashtags}")
    
    async def run_real_boost():
        # ALWAYS create fresh browser for boost - login browser connection dies after async task
        print(f"[Boost] Starting fresh browser session...", flush=True)
        browser = BrowserManager(headless=False)  # VISIBLE for debugging - set to True to hide
        
        try:
            # Start browser with saved session (from login)
            await browser.start(session_name=username)
            await browser.navigate('https://www.instagram.com/', wait_for='domcontentloaded')
            await asyncio.sleep(3)
            print(f"[Boost] Browser started, loaded saved session", flush=True)
        except Exception as e:
            print(f"[Boost] Failed to start browser: {e}", flush=True)
            tracker.complete_task(task_id, 'failed')
            return
        
        try:
            # Initialize explorer and actions
            explorer = InstagramExplorer(browser)
            actions = InstagramActions(browser)
            
            # Use intensity to determine delays (SAFER ranges to avoid detection)
            # 1-2: Relaxed (30-45s) - safest
            # 3: Normal (20-35s)
            # 4-5: Aggressive (15-25s) - still safe but faster
            if intensity <= 2:
                wait_min, wait_max = 30, 45
            elif intensity >= 4:
                wait_min, wait_max = 15, 25
            else:
                wait_min, wait_max = 20, 35
            
            # Store all collected posts and reels for later processing
            all_posts = []
            all_reels = []
            
            # STEP 1: For each keyword, search and find top 2 hashtags
            print(f"[Boost] Searching for top hashtags from keywords: {target_hashtags}")
            tracker.update_status_message(task_id, f"🔍 Searching for hashtags from {len(target_hashtags)} keywords...")
            tracker.update_extraction_progress(task_id, 5, phase=True)
            
            total_steps = len(target_hashtags) * 2  # 2 hashtags per keyword
            current_step = 0
            
            for keyword in target_hashtags:
                print(f"[Boost] Searching for hashtags related to: {keyword}")
                tracker.update_status_message(task_id, f"🔍 Searching: #{keyword}...")
                
                # Check if task was paused/stopped
                progress = tracker.get_progress(task_id)
                if progress and progress.get('status') in ['paused', 'failed']:
                    return
                
                try:
                    # Search and get top 2 hashtags by post count
                    top_hashtags = await explorer.search_hashtags(keyword, limit=2)
                    
                    if not top_hashtags:
                        print(f"[Boost] No hashtags found for keyword: {keyword}")
                        continue
                    
                    print(f"[Boost] Top hashtags for '{keyword}': {[h['name'] for h in top_hashtags]}")
                    
                    # STEP 2: Collect posts and reels from each top hashtag by clicking on it
                    for hashtag_info in top_hashtags:
                        hashtag_name = hashtag_info['name']
                        current_step += 1
                        
                        # Calculate extraction progress (0-80% for collection, 80-100% for liking)
                        extraction_percent = int((current_step / max(total_steps, 1)) * 80)
                        tracker.update_extraction_progress(task_id, extraction_percent, phase=True)
                        tracker.update_status_message(task_id, f"📥 Collecting from #{hashtag_name}... ({extraction_percent}%)")
                        
                        # Check rate limits before collecting
                        if not rate_limiter.can_perform_action(platform, 'likes'):
                            print(f"[Boost] Daily rate limit reached. Stopping.")
                            tracker.complete_task(task_id, 'completed')
                            return
                        
                        # Click on the hashtag and collect posts/reels
                        collected = await explorer.click_hashtag_and_collect(
                            hashtag_info, 
                            post_count=max(20, likes_per_hashtag * 4) # Request buffer for filtering
                        )
                        
                        # Add to our lists
                        all_posts.extend(collected.get('posts', []))
                        all_reels.extend(collected.get('reels', []))
                        
                        print(f"[Boost] Total collected so far: {len(all_posts)} posts, {len(all_reels)} reels")
                        
                        # Small delay between hashtags
                        await asyncio.sleep(random.uniform(2, 5))
                
                except Exception as e:
                    print(f"[Boost] Error processing keyword '{keyword}': {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Calculate target: 10 likes per hashtag
            num_hashtags = len(target_hashtags) if target_hashtags else 1
            target_count = likes_per_hashtag * num_hashtags
            
            # Combine posts and reels into one list for processing
            all_content = all_posts + all_reels
            random.shuffle(all_content)  # Mix posts and reels
            
            tracker.tasks[task_id]['target_count'] = target_count
            tracker._save_task(task_id)
            
            # Mark extraction phase complete
            tracker.update_extraction_progress(task_id, 100, phase=False)
            
            print(f"[Boost] Collection complete. {len(all_posts)} posts, {len(all_reels)} reels. Target: {target_count} likes.", flush=True)
            tracker.update_status_message(task_id, f"✅ Collected {len(all_content)} items. Liking {target_count}...")
            
            # Initialize counter
            successful_actions = 0
            views_count = 0  # Track reel views separately
            
            # STEP 3: Like all collected content (posts + reels)
            for i, content in enumerate(all_content):
                # Check if task was paused/stopped
                progress = tracker.get_progress(task_id)
                if progress and progress.get('status') in ['paused', 'failed']:
                    return
                
                # Check rate limits
                if not rate_limiter.can_perform_action(platform, 'likes'):
                    print(f"[Boost] Daily rate limit reached. Stopping.")
                    tracker.update_status_message(task_id, "Daily rate limit reached.")
                    tracker.complete_task(task_id, 'completed')
                    tracker.update_extraction_progress(task_id, 100, phase=False)
                    return
                
                content_type = content.get('type', 'post')
                content_url = content['url']
                is_reel = content_type == 'reel' or '/reel/' in content_url
                
                try:
                    # Get content details with retry on connection errors
                    details = None
                    for retry in range(2):
                        try:
                            details = await explorer.get_post_details(content_url)
                            if details:
                                break
                        except Exception as nav_err:
                            if 'ERR_CONNECTION' in str(nav_err) or 'ERR_EMPTY_RESPONSE' in str(nav_err):
                                backoff = (retry + 1) * 15
                                print(f"[Boost] ⚠️ Connection blocked, waiting {backoff}s...", flush=True)
                                tracker.update_status_message(task_id, f"⚠️ Rate limit, cooling down...")
                                await asyncio.sleep(backoff)
                            else:
                                break
                    
                    if not details:
                        print(f"[Boost] ⏭️ Skipping - could not load details", flush=True)
                        continue
                    
                    content_username = details.get('username', 'unknown')
                    
                    # --- SKIP LOGIC ---
                    # Step 1: Check likes FIRST - skip if > 1,000
                    like_count = details.get('like_count', 0)
                    if like_count > 1000:
                        print(f"[Boost] ⏭️ Skipping ({like_count} likes > 1k)", flush=True)
                        tracker.log_skip(task_id, 'likes', content_url, content_username, f"Too many likes ({like_count})")
                        continue
                    
                    # Step 2: Check followers - skip if > 5,000
                    followers = 0
                    if content_username and content_username != 'unknown':
                        print(f"[Boost] 🕵️ Checking @{content_username}...", flush=True)
                        tracker.update_status_message(task_id, f"🕵️ Checking @{content_username}...")
                        
                        followers = await explorer.get_profile_followers_count(content_username)
                        print(f"[Boost] @{content_username} has {followers} followers", flush=True)
                        
                        if followers > 5000:
                            print(f"[Boost] ⏭️ Skipping ({followers} followers > 5k)", flush=True)
                            tracker.log_skip(task_id, 'likes', content_url, content_username, f"Too many followers ({followers})")
                            continue
                        
                        # Navigate back to content
                        tracker.update_status_message(task_id, f"✅ @{content_username} qualifies!")
                        await browser.navigate(content_url, wait_for='domcontentloaded')
                        await asyncio.sleep(random.uniform(1.5, 3))
                    
                    print(f"[Boost] ✅ Qualifies: {like_count} likes, {followers} followers", flush=True)
                    
                    # --- REEL VIEW LOGIC ---
                    if is_reel:
                        # View reel for 5 seconds (counts as a view)
                        print(f"[Boost] 👁️ Viewing reel for 5s...", flush=True)
                        tracker.update_status_message(task_id, f"👁️ Viewing reel by @{content_username}...")
                        await asyncio.sleep(5)  # 5 seconds = counts as view
                        views_count += 1
                        rate_limiter.record_action(platform, 'views')
                        tracker.log_action(task_id, 'views', 'reel', content_url, content_username, '', 'success')
                        print(f"[Boost] 👁️ VIEW counted ({views_count} total views)", flush=True)
                    
                    # --- LIKE LOGIC ---
                    if 'likes' in action_types:
                        if tracker.get_progress(task_id).get('status') in ['paused', 'stopped']:
                            print("[Boost] 🛑 Stop signal received.")
                            break
                        
                        tracker.update_status_message(task_id, f"❤️ Liking {'reel' if is_reel else 'post'} by @{content_username}...")
                        
                        if not details.get('can_like', True):
                            tracker.log_skip(task_id, 'likes', content_url, content_username, "Already liked")
                            continue
                        
                        success = await actions.like_post()
                        if success:
                            successful_actions += 1
                            emoji = "🎬" if is_reel else "❤️"
                            print(f"[Boost] {emoji} LIKED ({successful_actions}/{target_count}): @{content_username} - {content_url}", flush=True)
                            tracker.log_action(task_id, 'likes', 'reel' if is_reel else 'post', content_url, content_username, '', 'success')
                            rate_limiter.record_action(platform, 'likes')
                        else:
                            print(f"[Boost] ❌ Failed to like {content_url}")
                            tracker.log_action(task_id, 'likes', 'reel' if is_reel else 'post', content_url, content_username, '', 'failed')
                    
                    # Update progress
                    progress_pct = int((successful_actions / max(target_count, 1)) * 100)
                    tracker.update_extraction_progress(task_id, min(progress_pct, 99), phase=False)
                    
                    # Check target reached
                    if successful_actions >= target_count:
                        print(f"[Boost] 🎉 Target reached! {successful_actions} likes, {views_count} views")
                        break
                    
                    # Wait before next content
                    delay = random.uniform(wait_min, wait_max)
                    print(f"[Boost] Waiting {int(delay)}s before next...")
                    await asyncio.sleep(delay)

            # END OF BOOST LOOP (Posts)
                    
                    # Perform follow action if selected
                    if 'follows' in action_types and post_username and rate_limiter.can_perform_action(platform, 'follows'):
                        result = await actions.follow_user(username=post_username)
                        if result.get('success'):
                            tracker.log_action(
                                task_id=task_id,
                                action_type='follows',
                                target_type='profile',
                                target_url=f"https://instagram.com/{post_username}",
                                target_username=post_username,
                                content='',
                                status='success'
                            )
                            rate_limiter.record_action(platform, 'follows')
                            print(f"[Boost] ➕ FOLLOWED: @{post_username}")
                    
                    # Perform comment action if selected
                    if 'comments' in action_types and comment_templates and rate_limiter.can_perform_action(platform, 'comments'):
                        comment = random.choice(comment_templates)
                        result = await actions.comment_on_post(comment)
                        if result.get('success'):
                            tracker.log_action(
                                task_id=task_id,
                                action_type='comments',
                                target_type=post['type'],
                                target_url=post['url'],
                                target_username=post_username,
                                content=comment,
                                status='success'
                            )
                            rate_limiter.record_action(platform, 'comments')
                            print(f"[Boost] 💬 COMMENTED on @{post_username}")
                    
                    # Short pause between posts (already handled by wait_min/wait_max)
                    # No behavioral breaks - just continue to next post
                
                except Exception as e:
                    print(f"[Boost] Error processing content: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Print final stats
            print(f"[Boost] 📊 Final: {successful_actions} likes, {views_count} views")

            # Mark task as completed and save report
            tracker.update_extraction_progress(task_id, 100, phase=False)
            tracker.complete_task(task_id, 'completed')
            tracker.update_status_message(task_id, "✅ Boost completed! Generating report...")
            report_path = tracker.save_report(task_id)
            print(f"[Boost] Task {task_id} completed! Report: {report_path}")
            
        except Exception as e:
            print(f"[Boost] Error in task {task_id}: {e}")
            import traceback
            traceback.print_exc()
            tracker.complete_task(task_id, 'failed')
            
        finally:
            try:
                await browser.close(save_session=True, session_name=username)
            except:
                pass
    
    # Run the async boost in a new event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_real_boost())
    except Exception as e:
        print(f"[Boost] Event loop error: {e}")
        tracker.complete_task(task_id, 'failed')
    finally:
        try:
            loop.close()
        except:
            pass


# ============================================
# MAIN
# ============================================

def init_app():
    """Initialize app with database and routes."""
    # Initialize database
    from src.database import init_db
    init_db()
    
    # Register auth routes
    from src.auth import register_auth_routes
    register_auth_routes(app)
    
    # Register payment routes
    from src.payments import register_payment_routes
    register_payment_routes(app)
    
    print("[*] All routes registered successfully")


if __name__ == '__main__':
    print("[*] IG Growth Hub - Starting server...")
    
    # Initialize app
    init_app()
    
    # Get port from environment (Railway sets this)
    port = int(os.getenv('PORT', 5000))
    
    print(f"[*] Open http://localhost:{port} in your browser")
    print("[*] A Chromium browser will open when you log in")
    # Disable reloader to prevent issues with async
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
