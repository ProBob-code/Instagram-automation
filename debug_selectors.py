
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.browser import BrowserManager
from src.instagram.auth import InstagramAuth as InstagramLogin
from src.instagram.explorer import InstagramExplorer
from src.instagram.actions import InstagramActions

# Test Config
TARGET_HASHTAG = "coding" # Use a popular tag to ensure content
USERNAME = "b.o.b.jacob"

async def run_debug():
    print("=== STARTING DEBUG SESSION ===")
    
    # Init
    browser = BrowserManager()
    await browser.start(session_name=USERNAME)
    page = browser.page
    
    try:
        # Check login
        login = InstagramLogin(browser)
        # Assuming already logged in or session saved. 
        # If not, we might need manual login or use existing session.
        await page.goto("https://www.instagram.com/")
        await asyncio.sleep(5)
        
        # Check if logged in
        if await page.query_selector("input[name='username']"):
             print("Not logged in. Please log in manually in the browser window within 30 seconds.")
             await asyncio.sleep(30)
        
        explorer = InstagramExplorer(browser)
        
        # 1. Test Collection
        print(f"\n[1] Testing Collection from #{TARGET_HASHTAG}...")
        urls = await explorer.get_posts_from_hashtag(TARGET_HASHTAG, 5)
        print(f"Collected {len(urls)} URLs.")
        print(urls)
        
        if not urls:
            print("ERROR: No URLs collected.")
            return

        # 2. Test Extraction on First 3
        print(f"\n[2] Testing details extraction on 3 posts...")
        for url in urls[:3]:
            print(f"\n--- Analyzing {url} ---")
            details = await explorer.get_post_details(url)
            print("EXTRACTED DETAILS:")
            print(f"Username: '{details.get('username')}'")
            print(f"Timestamp: '{details.get('timestamp')}'")
            print(f"Like Count (Post): {details.get('like_count')}")
            
            # Check date parsing logic
            ts = details.get('timestamp')
            if ts:
                try:
                    post_date = ts.split('T')[0]
                    from datetime import datetime
                    today = datetime.utcnow().strftime('%Y-%m-%d')
                    print(f"Date Parsed: {post_date} (Today is {today}) -> Match? {post_date == today}")
                except:
                    print("Date Parse Failed")
            else:
                 print("Date Extraction Failed (None)")

        # 3. Test Like Selector (Dry Run) on First Post
        print(f"\n[3] Testing Like Button Selector on {urls[0]}...")
        await page.goto(urls[0])
        await asyncio.sleep(2)
        
        # Existing Selector from actions.py
        target_d = "M16.792 3.904A4.989 4.989 0 0 1 21.5 9.122c0 3.072-2.652 4.959-5.197 7.222-2.512 2.243-3.865 3.469-4.303 3.752-.477-.309-2.143-1.823-4.303-3.752C5.141 14.072 2.5 12.167 2.5 9.122a4.989 4.989 0 0 1 4.708-5.218 4.21 4.21 0 0 1 3.675 1.941c.84 1.175.98 1.763 1.12 1.763s.278-.588 1.11-1.766a4.17 4.17 0 0 1 3.679-1.938m0-2a6.04 6.04 0 0 0-4.797 2.127 6.052 6.052 0 0 0-4.787-2.127A6.985 6.985 0 0 0 .5 9.122c0 3.61 2.55 5.827 5.015 7.97.283.246.569.494.853.747l1.027.918a44.998 44.998 0 0 0 3.518 3.018 2 2 0 0 0 2.174 0 45.263 45.263 0 0 0 3.626-3.115l.922-.824c.293-.26.59-.519.885-.774 2.334-2.025 4.98-4.32 4.98-7.94a6.985 6.985 0 0 0-6.708-7.218Z"
        svg_selector = f'xpath=//*[local-name()="svg"]/*[local-name()="path" and @d="{target_d}"]'
        
        el = await page.query_selector(svg_selector)
        if el:
            print("SUCCESS: Found SVG by user path!")
        else:
            print("FAIL: Could not find SVG by user path.")
            # Dump page content for analysis (first 500 chars of body)
            # content = await page.content()
            # print(f"Page Content Snippet: {content[:500]}")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n=== DEBUG END ===")
        # await browser.close() # Keep open to inspect if needed

if __name__ == "__main__":
    asyncio.run(run_debug())
