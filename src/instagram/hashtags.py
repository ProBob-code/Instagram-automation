"""
IG Growth Hub - Instagram Hashtag Engagement
Handles hashtag exploration and liking posts
"""

import asyncio
import random
from typing import List, Dict, Optional
from ..browser import BrowserManager
from ..human_behavior import HumanBehavior, gaussian_delay
from ..rate_limiter import get_rate_limiter


class HashtagEngagement:
    """
    Handles hashtag exploration and engagement.
    Implements human-like patterns for safety.
    """
    
    EXPLORE_URL = 'https://www.instagram.com/explore/tags/{hashtag}/'
    
    def __init__(self, browser: BrowserManager, intensity: int = 1):
        self.browser = browser
        self.behavior = HumanBehavior(intensity)
        self.rate_limiter = get_rate_limiter()
        self.stats = {
            'posts_viewed': 0,
            'posts_liked': 0,
            'hashtags_visited': 0
        }
    
    async def engage_hashtag(self, hashtag: str, max_likes: int = 10) -> Dict:
        """
        Engage with posts under a specific hashtag.
        Returns stats about engagement.
        """
        result = {
            'hashtag': hashtag,
            'posts_found': 0,
            'posts_liked': 0,
            'posts_skipped': 0,
            'errors': []
        }
        
        try:
            # Navigate to hashtag page
            url = self.EXPLORE_URL.format(hashtag=hashtag.replace('#', ''))
            await self.browser.navigate(url)
            await asyncio.sleep(gaussian_delay(2, 0.5, 1.5, 4))
            
            self.stats['hashtags_visited'] += 1
            
            # Scroll to load posts
            for _ in range(random.randint(2, 4)):
                await self.browser.scroll('down')
                await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 2))
            
            # Get post links
            posts = await self._get_post_links()
            result['posts_found'] = len(posts)
            
            if not posts:
                result['errors'].append('No posts found')
                return result
            
            # Engage with posts
            likes_done = 0
            for post_url in posts[:max_likes * 2]:  # Get more than needed in case of skips
                if likes_done >= max_likes:
                    break
                
                # Check rate limits
                if not self.rate_limiter.can_perform_action('instagram', 'likes'):
                    result['errors'].append('Rate limit reached')
                    break
                
                # Visit and potentially like post
                liked = await self._engage_post(post_url)
                
                if liked:
                    likes_done += 1
                    result['posts_liked'] += 1
                    self.stats['posts_liked'] += 1
                    self.rate_limiter.record_action('instagram', 'likes')
                else:
                    result['posts_skipped'] += 1
                
                self.stats['posts_viewed'] += 1
                
                # Human-like delay between posts
                await asyncio.sleep(self.behavior.wait('like'))
                
                # Check if break needed
                if self.behavior.check_break_needed():
                    await asyncio.sleep(gaussian_delay(30, 10, 15, 60))
            
            return result
            
        except Exception as e:
            result['errors'].append(str(e))
            return result
    
    async def _get_post_links(self) -> List[str]:
        """Extract post links from hashtag page."""
        page = self.browser.page
        if not page:
            return []
        
        try:
            # Get all post links
            links = await page.query_selector_all('a[href*="/p/"]')
            
            hrefs = []
            for link in links:
                href = await link.get_attribute('href')
                if href and '/p/' in href:
                    full_url = f'https://www.instagram.com{href}' if href.startswith('/') else href
                    if full_url not in hrefs:
                        hrefs.append(full_url)
            
            # Shuffle to avoid patterns
            random.shuffle(hrefs)
            
            return hrefs[:30]  # Limit to 30 posts
            
        except Exception as e:
            print(f"Error getting posts: {e}")
            return []
    
    async def _engage_post(self, post_url: str) -> bool:
        """
        Visit a post and like it if not already liked.
        Returns True if liked, False if skipped.
        """
        try:
            await self.browser.navigate(post_url)
            await asyncio.sleep(gaussian_delay(1.5, 0.5, 1, 3))
            
            page = self.browser.page
            if not page:
                return False
            
            # Check if already liked
            like_button = await page.query_selector('svg[aria-label="Like"]')
            unlike_button = await page.query_selector('svg[aria-label="Unlike"]')
            
            if unlike_button:
                # Already liked, skip
                return False
            
            if not like_button:
                # Can't find like button
                return False
            
            # Scroll to like button area (simulates reading)
            await self.browser.scroll('down', random.randint(100, 200))
            await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 2))
            
            # Click like
            parent = await like_button.query_selector('xpath=ancestor::button')
            if parent:
                await parent.click()
            else:
                await like_button.click()
            
            await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.3, 1))
            
            return True
            
        except Exception as e:
            print(f"Error engaging post: {e}")
            return False
    
    async def run_session(self, hashtags: List[str], likes_per_tag: int = 10) -> Dict:
        """
        Run a full engagement session across multiple hashtags.
        """
        session_stats = {
            'hashtags_processed': 0,
            'total_likes': 0,
            'total_posts_viewed': 0,
            'results': []
        }
        
        session_length = self.behavior.get_session_length()
        
        for hashtag in hashtags:
            # Check if session should end
            if not self.rate_limiter.can_perform_action('instagram', 'likes'):
                break
            
            result = await self.engage_hashtag(hashtag, likes_per_tag)
            session_stats['results'].append(result)
            session_stats['hashtags_processed'] += 1
            session_stats['total_likes'] += result['posts_liked']
            session_stats['total_posts_viewed'] += result['posts_found']
            
            # Delay between hashtags
            await asyncio.sleep(gaussian_delay(30, 10, 15, 60))
        
        return session_stats
    
    def get_stats(self) -> Dict:
        """Get current session statistics."""
        return self.stats.copy()


class HashtagEngagementSync:
    """Synchronous wrapper for HashtagEngagement."""
    
    def __init__(self, browser_manager, intensity: int = 1):
        from ..browser import SyncBrowserManager
        if isinstance(browser_manager, SyncBrowserManager):
            self.engagement = HashtagEngagement(browser_manager.async_manager, intensity)
            self._loop = browser_manager._get_loop()
        else:
            self.engagement = HashtagEngagement(browser_manager, intensity)
            self._loop = asyncio.new_event_loop()
    
    def engage_hashtag(self, hashtag: str, max_likes: int = 10) -> Dict:
        return self._loop.run_until_complete(
            self.engagement.engage_hashtag(hashtag, max_likes)
        )
    
    def run_session(self, hashtags: List[str], likes_per_tag: int = 10) -> Dict:
        return self._loop.run_until_complete(
            self.engagement.run_session(hashtags, likes_per_tag)
        )
    
    def get_stats(self) -> Dict:
        return self.engagement.get_stats()
