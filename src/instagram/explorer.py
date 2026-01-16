"""
IG Growth Hub - Instagram Explorer
Discovers real posts and accounts via search bar and hashtag pages.
Uses XPath-based selectors for reliable interaction.
"""

import asyncio
import random
import re
from typing import Dict, List, Optional, Tuple
from ..browser import BrowserManager
from ..human_behavior import gaussian_delay


class InstagramExplorer:
    """
    Discovers real posts and accounts for interaction.
    Uses Instagram's search bar to find top hashtags, then collects posts/reels.
    """
    
    INSTAGRAM_URL = 'https://www.instagram.com'
    
    # XPath selectors (from user's inspection)
    # Search input field
    SEARCH_INPUT_XPATH = '//input[@placeholder="Search"]'
    # Suggestion popup container (appears after typing)
    SUGGESTION_POPUP_XPATH = '//*[@id[starts-with(., "mount_0_0_")]]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/div/div/div[2]/div/div/div/div[2]/div/div/div[2]/div'
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def search_hashtags(self, keyword: str, limit: int = 3) -> List[Dict]:
        """
        Search for a hashtag and ignore specific suggestions.
        """
        page = self.browser.page
        print(f"[Explorer] Searching for hashtag: {keyword}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Navigate to home if first attempt or if retrying
                if attempt > 0:
                    print(f"[Explorer] Retry attempt {attempt+1}/{max_retries} for search...")
                    await self.browser.navigate(self.INSTAGRAM_URL, wait_for='domcontentloaded')
                    await asyncio.sleep(5)
                elif page.url != self.INSTAGRAM_URL and 'instagram.com' not in page.url:
                    print(f"[Explorer] Navigating to Instagram home...")
                    await self.browser.navigate(self.INSTAGRAM_URL, wait_for='domcontentloaded')
                    await asyncio.sleep(gaussian_delay(3, 0.5, 2, 4))
                
                # Dismiss any popups by pressing Escape
                print(f"[Explorer] Dismissing any popups...")
                try:
                    await page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
                except:
                    pass
                
                # Click on the Search link in sidebar to open search panel
                print(f"[Explorer] Opening search panel...")
                search_link = await page.query_selector('a[href*="search"], svg[aria-label="Search"]')
                if search_link:
                    parent = await search_link.evaluate_handle('el => el.closest("a") || el.parentElement')
                    if parent:
                        await parent.click()
                    else:
                        await search_link.click()
                    await asyncio.sleep(gaussian_delay(1.5, 0.3, 1, 2))
                
                # Find the search input
                print(f"[Explorer] Looking for search input...")
                search_input = None
                
                # Try multiple selectors
                selectors = [
                    'input[placeholder="Search"]',
                    'input[aria-label="Search input"]',
                    f'xpath={self.SEARCH_INPUT_XPATH}'
                ]
                
                for sel in selectors:
                    try:
                        search_input = await page.query_selector(sel)
                        if search_input:
                            print(f"[Explorer] Found search input with: {sel}")
                            break
                    except:
                        continue
                
                if not search_input:
                    print("[Explorer] Could not find search input. Retrying...")
                    continue
                
                # Click on input and type the hashtag
                print(f"[Explorer] Typing search query: #{keyword}")
                await search_input.click()
                await asyncio.sleep(0.5)
                await search_input.fill(f'#{keyword}')
                
                # Wait for suggestion popup to appear
                print(f"[Explorer] Waiting for suggestions...")
                await asyncio.sleep(gaussian_delay(2.5, 0.5, 2, 4))
                
                # Get all suggestion items from the popup
                # Each suggestion is typically an <a> tag with href containing /explore/tags/
                suggestion_items = await page.query_selector_all('a[href*="/explore/tags/"]')
                
                if not suggestion_items:
                    # Try alternative: get all items in the suggestion div
                    suggestion_items = await page.query_selector_all(f'xpath={self.SUGGESTION_POPUP_XPATH}//a')
                
                print(f"[Explorer] Found {len(suggestion_items)} suggestion items")
                
                results = []
                for item in suggestion_items[:10]:  # Check up to 10
                    try:
                        href = await item.get_attribute('href')
                        if not href or '/explore/tags/' not in href:
                            continue
                        
                        # Get full text content
                        text_content = await item.text_content()
                        
                        # Extract hashtag name from href
                        hashtag_match = re.search(r'/explore/tags/([^/]+)/?', href)
                        if not hashtag_match:
                            continue
                        
                        hashtag_name = hashtag_match.group(1)
                        
                        # Extract post count from text (e.g., "549M posts", "5.8K posts")
                        post_count = 0
                        count_match = re.search(r'([\d.,]+)\s*([KMB]?)\s*posts?', text_content, re.IGNORECASE)
                        if count_match:
                            num_str = count_match.group(1).replace(',', '').replace('.', '')
                            # Handle decimal like 5.8M
                            if '.' in count_match.group(1):
                                num = float(count_match.group(1).replace(',', ''))
                            else:
                                num = float(num_str)
                            
                            multiplier = count_match.group(2).upper()
                            if multiplier == 'K':
                                post_count = int(num * 1000)
                            elif multiplier == 'M':
                                post_count = int(num * 1000000)
                            elif multiplier == 'B':
                                post_count = int(num * 1000000000)
                            else:
                                post_count = int(num)
                        
                        results.append({
                            'name': hashtag_name,
                            'post_count': post_count,
                            'url': f"{self.INSTAGRAM_URL}{href}" if not href.startswith('http') else href,
                            'element': item  # Store element reference for clicking
                        })
                        
                        print(f"[Explorer] Found: #{hashtag_name} ({post_count:,} posts)")
                        
                    except Exception as e:
                        print(f"[Explorer] Error parsing suggestion: {e}")
                        continue
                
                if not results:
                     print("[Explorer] No results parsed.")
                     continue

                # Sort by post count descending and keep top results
                results.sort(key=lambda x: x['post_count'], reverse=True)
                top_results = results[:limit]
                
                top_names = [f"#{r['name']} ({r['post_count']:,})" for r in top_results]
                print(f"[Explorer] Top {limit} hashtags: {top_names}")
                return top_results
                
            except Exception as e:
                print(f"[Explorer] Error searching hashtags (attempt {attempt+1}): {e}")
                import traceback
                traceback.print_exc()
                if attempt == max_retries - 1:
                    return []
                await asyncio.sleep(2)
        
        return []
    
    async def click_hashtag_and_collect(self, hashtag_info: Dict, post_count: int = 5) -> Dict[str, List[Dict]]:
        """
        Click on a hashtag from search results and collect posts/reels.
        
        Args:
            hashtag_info: Dict from search_hashtags with 'url'
            post_count: Number of posts/reels to collect
            
        Returns:
            Dict with 'posts' and 'reels' lists
        """
        page = self.browser.page
        collected = {'posts': [], 'reels': []}
        
        try:
            # Always use URL navigation (element gets detached after page navigation)
            hashtag_name = hashtag_info.get('name', 'unknown')
            url = hashtag_info.get('url', f"{self.INSTAGRAM_URL}/explore/tags/{hashtag_name}/")
            
            print(f"[Explorer] Navigating to #{hashtag_name}...")
            await self.browser.navigate(url, wait_for='domcontentloaded')
            await asyncio.sleep(gaussian_delay(3, 0.5, 2, 4))
            
            # Collect posts from the hashtag page
            collected = await self._collect_from_current_page(post_count)
            
            return collected
            
        except Exception as e:
            print(f"[Explorer] Error collecting from hashtag: {e}")
            import traceback
            traceback.print_exc()
            return collected
    
    async def _collect_from_current_page(self, count: int = 5) -> Dict[str, List[Dict]]:
        """
        Collect posts and reels from the current hashtag page.
        """
        page = self.browser.page
        collected = {'posts': [], 'reels': []}
        seen_urls = set()
        
        scroll_count = 0
        max_scrolls = 25
        
        while (len(collected['posts']) < count or len(collected['reels']) < count) and scroll_count < max_scrolls:
            # Find all post/reel links on the page
            items = await page.query_selector_all('a[href*="/p/"], a[href*="/reel/"]')
            
            for item in items:
                try:
                    href = await item.get_attribute('href')
                    if not href or href in seen_urls:
                        continue
                    
                    seen_urls.add(href)
                    full_url = href if href.startswith('http') else f"{self.INSTAGRAM_URL}{href}"
                    
                    # Determine type
                    if '/reel/' in href:
                        item_type = 'reel'
                    else:
                        item_type = 'post'
                    
                    # Check for reel/video icon overlay
                    try:
                        reel_icon = await item.query_selector('svg[aria-label*="Reel"], svg[aria-label*="Video"], svg[aria-label*="Clip"]')
                        if reel_icon:
                            item_type = 'reel'
                    except:
                        pass
                    
                    entry = {
                        'url': full_url,
                        'type': item_type,
                        'username': ''  # Will be extracted when visiting
                    }
                    
                    if item_type == 'reel' and len(collected['reels']) < count:
                        collected['reels'].append(entry)
                    elif item_type == 'post' and len(collected['posts']) < count:
                        collected['posts'].append(entry)
                    
                except Exception as e:
                    continue
            
            # Check if we have enough
            if len(collected['posts']) >= count and len(collected['reels']) >= count:
                break
            
            # Scroll to load more
            scroll_amount = random.randint(400, 700)
            await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            scroll_count += 1
            await asyncio.sleep(gaussian_delay(1.5, 0.5, 1, 2.5))
        
        print(f"[Explorer] Collected: {len(collected['posts'])} posts, {len(collected['reels'])} reels")
        return collected
    
    async def get_post_details(self, post_url: str) -> Optional[Dict]:
        """
        Extracts details from a post (username, timestamp, like count, caption).
        """
        page = self.browser.page
        print(f"[Explorer] Getting details for {post_url}...")
        try:
            # Navigate if not already there
            if page.url != post_url:
                await page.goto(post_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)  # Wait for page to fully load

            details = {'url': post_url}

            # 1. USERNAME EXTRACTION (Multiple robust methods)
            username = None
            
            # Method 0: User's specific CSS selector (HIGHEST PRIORITY)
            try:
                # Generalized CSS - targets the username span in post header
                user_css = 'section main div div div div div div div div span span span div a div div span'
                el = await page.query_selector(user_css)
                if el:
                    text = await el.text_content()
                    if text and len(text) >= 2:
                        username = text.strip()
                        print(f"[Explorer] Username from user CSS: @{username}")
            except: pass
            
            # Method 1: Check Page Title (Most reliable for posts)
            # Format: "Name (@username) • Instagram photos and videos"
            if not username:
                try:
                    await page.wait_for_timeout(500)  # Brief wait for title to update
                    title = await page.title()
                    if title and '(@' in title:
                        match = re.search(r'\(@([a-zA-Z0-9_.]+)\)', title)
                        if match:
                            username = match.group(1)
                            print(f"[Explorer] Username from title: @{username}")
                except: pass

            # Method 2: Header profile link (Inside article header)
            if not username:
                try:
                    header_links = await page.query_selector_all('article header a[href^="/"]')
                    for link in header_links:
                        href = await link.get_attribute('href')
                        if href:
                            parts = href.strip('/').split('/')
                            # Profile links are single-part: /username/
                            if len(parts) == 1 and parts[0] and parts[0] not in ['explore', 'reels', 'p', 'direct', 'stories']:
                                username = parts[0]
                                print(f"[Explorer] Username from header link: @{username}")
                                break
                except: pass

            # Method 3: Meta tag og:title
            if not username:
                try:
                    meta = await page.query_selector('meta[property="og:title"]')
                    if meta:
                        content = await meta.get_attribute('content')
                        if content and '(@' in content:
                            match = re.search(r'\(@([a-zA-Z0-9_.]+)\)', content)
                            if match:
                                username = match.group(1)
                                print(f"[Explorer] Username from meta: @{username}")
                except: pass
            
            # Method 4: Look for visible username text in header
            if not username:
                try:
                    # Find any span or div with text that looks like a username in header
                    header_el = await page.query_selector('article header')
                    if header_el:
                        header_text = await header_el.text_content()
                        # First word is usually the display name or username
                        words = header_text.split()
                        for word in words[:3]:  # Check first 3 words
                            cleaned = re.sub(r'[^a-zA-Z0-9_.]', '', word)
                            if len(cleaned) >= 2 and len(cleaned) <= 30:
                                username = cleaned
                                print(f"[Explorer] Username from header text: @{username}")
                                break
                except: pass

            # Method 5: Extract from any profile link on page via JavaScript
            if not username:
                try:
                    username = await page.evaluate('''() => {
                        // Look for profile links in article
                        const links = document.querySelectorAll('article a[href^="/"]');
                        for (const link of links) {
                            const href = link.getAttribute('href');
                            const parts = href.replace(/^\\/|\\/$/, '').split('/');
                            // Single-segment paths are usernames (excluding known paths)
                            if (parts.length === 1 && parts[0].length > 0) {
                                const excluded = ['explore', 'reels', 'p', 'direct', 'stories', 'accounts', 'about'];
                                if (!excluded.includes(parts[0]) && /^[a-zA-Z0-9_.]+$/.test(parts[0])) {
                                    return parts[0];
                                }
                            }
                        }
                        return null;
                    }''')
                    if username:
                        print(f"[Explorer] Username from JS scan: @{username}")
                except: pass

            # Method 6: Check for canonical URL in page head
            if not username:
                try:
                    canonical = await page.query_selector('link[rel="canonical"]')
                    if canonical:
                        href = await canonical.get_attribute('href')
                        if href and '/p/' in href:
                            # Pattern: https://www.instagram.com/p/ABC123/
                            # The username is NOT in /p/ URLs, but sometimes in og:description
                            pass
                    # Try og:description: "X likes, Y comments - username on Instagram..."
                    og_desc = await page.query_selector('meta[property="og:description"]')
                    if og_desc:
                        desc = await og_desc.get_attribute('content')
                        if desc and ' - ' in desc and ' on Instagram' in desc:
                            # Extract part between last " - " and " on Instagram"
                            match = re.search(r' - ([a-zA-Z0-9_.]+) on Instagram', desc)
                            if match:
                                username = match.group(1)
                                print(f"[Explorer] Username from og:description: @{username}")
                except: pass

            # Fallback: Set to 'unknown' if all methods fail
            if not username:
                username = 'unknown'
                print(f"[Explorer] Could not extract username, using 'unknown'")
            
            # Check if we can like (heart icon not filled)
            can_like = False
            try:
                like_btn = await page.query_selector('svg[aria-label="Like"]')
                can_like = like_btn is not None
            except:
                pass
            
            # Extract timestamp
            timestamp_val = None
            try:
                # User's path for timestamp: //*[@id="mount_0_0_..."]/ ... /div/div/a/span/time
                # Generalized:
                time_el = await page.query_selector('article time')
                if time_el:
                    # Get datetime attribute (ISO format)
                    dt_str = await time_el.get_attribute('datetime')
                    if dt_str:
                         from datetime import datetime
                         # Parse ISO format (e.g. 2023-10-27T10:00:00.000Z)
                         # Simple parse since format is usually consistent
                         timestamp_val = dt_str
            except:
                pass
            
            # Extract like count
            like_count = 0
            try:
                # Look for "X likes"
                # Often in: article section div div a span or similar
                like_selectors = [
                    'article section div div span a span', # "liked by X and others"
                    'a[href*="liked_by"] span',
                    'span:has-text("likes")'
                ]
                
                for sel in like_selectors:
                     els = await page.query_selector_all(sel)
                     for el in els:
                         txt = await el.text_content()
                         if txt and ('likes' in txt or 'like' in txt or any(c.isdigit() for c in txt)):
                             # Parse number
                             clean_txt = txt.lower().replace('likes', '').replace('like', '').replace(',','').strip()
                             try:
                                 if 'k' in clean_txt:
                                     like_count = int(float(clean_txt.replace('k','')) * 1000)
                                 elif 'm' in clean_txt:
                                     like_count = int(float(clean_txt.replace('m','')) * 1000000)
                                 else:
                                     like_count = int(clean_txt)
                                 if like_count > 0:
                                     break
                             except:
                                 pass
                     if like_count > 0:
                         break
            except:
                 pass

            return {
                'url': post_url,
                'username': username,
                'can_like': can_like,
                'type': 'reel' if '/reel/' in post_url else 'post',
                'timestamp': timestamp_val,
                'like_count': like_count
            }
            
        except Exception as e:
            print(f"[Explorer] Error getting post details: {e}")
            return None
    
    async def _gentle_scroll(self, times: int = 2):
        """Scroll naturally to load more content."""
        page = self.browser.page
        
        for _ in range(times):
            scroll_amount = random.randint(400, 700)
            await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 2))
    
    # Legacy method for compatibility
    async def discover_posts_by_hashtag(self, hashtag: str, limit: int = 10) -> List[Dict]:
        """
        Legacy method - now uses click_hashtag_and_collect internally.
        """
        result = await self._collect_from_current_page(count=limit)
        return result.get('posts', [])
    
    # Method kept for compatibility
    async def collect_posts_from_hashtag(
        self, 
        hashtag: str, 
        count: int = 5, 
        content_type: str = 'all'
    ) -> Dict[str, List[Dict]]:
        """
        Navigate to hashtag page and collect posts/reels.
        """
        page = self.browser.page
        
        try:
            # Navigate to hashtag page
            hashtag_clean = hashtag.replace('#', '').strip().lower()
            url = f"{self.INSTAGRAM_URL}/explore/tags/{hashtag_clean}/"
            print(f"[Explorer] Navigating to hashtag page: #{hashtag_clean}")
            
            await self.browser.navigate(url, wait_for='domcontentloaded')
            await asyncio.sleep(gaussian_delay(3, 1, 2, 4))
            
            # Collect from the page
            return await self._collect_from_current_page(count)
            
        except Exception as e:
            print(f"[Explorer] Error collecting from #{hashtag}: {e}")
            return {'posts': [], 'reels': []}

    async def get_posts_from_hashtag(self, hashtag: str, count: int = 5) -> List[str]:
        """
        Wrapper to get a simple list of URLs (Posts + Reels) from a hashtag.
        """
        collected = await self.collect_posts_from_hashtag(hashtag, count)
        
        # Merge urls
        urls = []
        for p in collected.get('posts', []):
            if p.get('url'): urls.append(p['url'])
        for r in collected.get('reels', []):
            if r.get('url'): urls.append(r['url'])
            
        print(f"[Explorer] Flattened {len(urls)} URLs from hashtag #{hashtag}")
        return urls

    async def get_profile_followers_count(self, username: str) -> int:
        """
        Quickly check a user's follower count.
        """
        try:
             # We reuse the scraper's logic but kept minimal for speed
             # Navigate to profile
             url = f"{self.INSTAGRAM_URL}/{username}/"
             await self.browser.navigate(url, wait_for='domcontentloaded')
             await asyncio.sleep(gaussian_delay(2, 0.5, 1, 3))
             
             # Extract from meta description (fastest)
             meta = await self.browser.page.query_selector('meta[name="description"]')
             count = 0
             if meta:
                 content = await meta.get_attribute('content')
                 if content:
                     # "1.2K Followers, ..."
                     match = re.search(r'([\d,\.]+[KMB]?)\s*Followers', content, re.IGNORECASE)
                     if match:
                         num_str = match.group(1).replace(',', '').strip().upper()
                         if 'K' in num_str:
                             count = int(float(num_str.replace('K', '')) * 1000)
                         elif 'M' in num_str:
                             count = int(float(num_str.replace('M', '')) * 1000000)
                         else:
                             count = int(float(num_str))
             return count
        except:
            return 0
