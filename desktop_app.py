"""
IG Growth Hub - Desktop Application Launcher
This is the main entry point for the desktop app.
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path

# Set up paths for frozen app (PyInstaller)
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).parent
else:
    # Running in development
    BASE_DIR = Path(__file__).parent
    APP_DIR = BASE_DIR

# Add src to path
sys.path.insert(0, str(BASE_DIR))

# Cloud API configuration (Railway deployment)
CLOUD_API_URL = os.environ.get('CLOUD_API_URL', 'https://instagram-automation-production-e9f1.up.railway.app')

def install_playwright_browsers():
    """Install Playwright browsers on first run."""
    import subprocess
    
    # Check if Chromium is already installed
    pw_browsers = Path.home() / '.cache' / 'ms-playwright'
    chromium_exists = pw_browsers.exists() and any(pw_browsers.glob('chromium-*'))
    
    if not chromium_exists:
        print("[Setup] Installing Chromium browser (first run only)...")
        try:
            subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], 
                         check=True, capture_output=True)
            print("[Setup] Chromium installed successfully!")
        except Exception as e:
            print(f"[Setup] Warning: Could not install Chromium: {e}")
            print("[Setup] Please run: playwright install chromium")

def start_flask_server():
    """Start the Flask server in background thread."""
    # Import here to avoid circular imports
    from app import app
    
    # Use waitress for production-quality serving on Windows
    try:
        from waitress import serve
        print("[Server] Starting IG Growth Hub on http://localhost:5000")
        serve(app, host='127.0.0.1', port=5000, threads=4)
    except ImportError:
        # Fallback to Flask dev server
        print("[Server] Starting IG Growth Hub on http://localhost:5000")
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def open_browser_delayed():
    """Open browser after server starts."""
    time.sleep(2)  # Wait for server to start
    webbrowser.open('http://localhost:5000')

def main():
    """Main entry point for desktop app."""
    print("=" * 50)
    print("  IG Growth Hub - Desktop Edition")
    print("=" * 50)
    print()
    
    # First run: Install Playwright browsers
    install_playwright_browsers()
    
    # Create data directories
    data_dir = APP_DIR / 'data'
    (data_dir / 'sessions').mkdir(parents=True, exist_ok=True)
    (data_dir / 'reports').mkdir(parents=True, exist_ok=True)
    (data_dir / 'profiles').mkdir(parents=True, exist_ok=True)
    (data_dir / 'tasks').mkdir(parents=True, exist_ok=True)
    
    # Start browser opening in background
    browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
    browser_thread.start()
    
    print("[*] Opening http://localhost:5000 in your browser...")
    print("[*] Keep this window open while using the app.")
    print("[*] Press Ctrl+C to stop the server.")
    print()
    
    # Start Flask server (blocks)
    try:
        start_flask_server()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        sys.exit(0)

if __name__ == '__main__':
    main()
