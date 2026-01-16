"""
IG Growth Hub - Threads Engagement
Handles Threads interaction automation
"""

import asyncio
import random
from typing import List, Dict, Optional
from ..browser import BrowserManager
from ..human_behavior import HumanBehavior, gaussian_delay
from ..rate_limiter import get_rate_limiter


class ThreadsEngagement:
    """
    Handles Threads engagement automation.
    Implements human-like patterns for safety.
    """
    
    THREADS_URL = 'https://www.threads.net'
    SEARCH_URL = 'https://www.threads.net/search'
    
    def __init__(self, browser: BrowserManager, intensity: int = 1):
        self.browser = browser
        self.behavior = HumanBehavior(intensity)
        self.rate_limiter = get_rate_limiter()
        self.stats = {
            'threads_viewed': 0,
            'threads_liked': 0,
            'threads_replied': 0,
            'profiles_visited': 0
        }
    
    async def engage_feed(self, max_likes: int = 20) -> Dict:
        """
        Engage with threads in the home feed.
        Returns engagement statistics.
        """
        result = {
            'threads_viewed': 0,
            'threads_liked': 0,
            'threads_skipped': 0,
            'errors': []
        }
        
        try:
            # Navigate to feed
            await self.browser.navigate(self.THREADS_URL)
            await asyncio.sleep(gaussian_delay(2, 0.5, 1, 3))
            
            likes_done = 0
            scroll_count = 0
            max_scrolls = 15
            
            while likes_done < max_likes and scroll_count < max_scrolls:
                # Check rate limits
                if not self.rate_limiter.can_perform_action('threads', 'likes'):
                    result['errors'].append('Rate limit reached')
                    break
                
                # Find like buttons on visible threads
                like_buttons = await self._get_unliked_threads()
                
                for button in like_buttons[:3]:  # Process a few per scroll
                    if likes_done >= max_likes:
                        break
                    
                    try:
                        # Simulate reading before liking
                        await asyncio.sleep(gaussian_delay(1.5, 0.5, 1, 3))
                        
                        await button.click()
                        likes_done += 1
                        result['threads_liked'] += 1
                        self.stats['threads_liked'] += 1
                        self.rate_limiter.record_action('threads', 'likes')
                        
                        await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.3, 1))
                        
                    except Exception as e:
                        result['threads_skipped'] += 1
                
                # Scroll to load more
                await self.browser.scroll('down')
                scroll_count += 1
                result['threads_viewed'] += 3  # Approximate threads per scroll
                
                await asyncio.sleep(gaussian_delay(2, 0.5, 1, 4))
                
                # Check if break needed
                if self.behavior.check_break_needed():
                    await asyncio.sleep(gaussian_delay(30, 10, 15, 60))
            
            return result
            
        except Exception as e:
            result['errors'].append(str(e))
            return result
    
    async def _get_unliked_threads(self) -> List:
        """Get like buttons for threads not yet liked."""
        page = self.browser.page
        if not page:
            return []
        
        try:
            # Find all like buttons that aren't already liked
            buttons = await page.query_selector_all('svg[aria-label="Like"]')
            
            clickable_buttons = []
            for button in buttons:
                parent = await button.query_selector('xpath=ancestor::div[@role="button"]')
                if parent:
                    clickable_buttons.append(parent)
                else:
                    clickable_buttons.append(button)
            
            return clickable_buttons[:10]  # Limit
            
        except Exception as e:
            print(f"Error finding threads: {e}")
            return []
    
    async def search_and_engage(self, query: str, max_likes: int = 10) -> Dict:
        """
        Search for threads and engage with results.
        """
        result = {
            'query': query,
            'threads_found': 0,
            'threads_liked': 0,
            'errors': []
        }
        
        try:
            # Navigate to search
            await self.browser.navigate(f'{self.SEARCH_URL}?q={query}')
            await asyncio.sleep(gaussian_delay(2, 0.5, 1, 3))
            
            # Scroll to load results
            for _ in range(random.randint(2, 4)):
                await self.browser.scroll('down')
                await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 2))
            
            # Engage with results
            likes_done = 0
            like_buttons = await self._get_unliked_threads()
            result['threads_found'] = len(like_buttons)
            
            for button in like_buttons:
                if likes_done >= max_likes:
                    break
                
                if not self.rate_limiter.can_perform_action('threads', 'likes'):
                    break
                
                try:
                    await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 2))
                    await button.click()
                    likes_done += 1
                    result['threads_liked'] += 1
                    self.rate_limiter.record_action('threads', 'likes')
                except:
                    pass
            
            return result
            
        except Exception as e:
            result['errors'].append(str(e))
            return result
    
    async def follow_from_thread(self, max_follows: int = 5) -> Dict:
        """
        Follow users from threads in the feed.
        """
        result = {
            'profiles_visited': 0,
            'follows_done': 0,
            'errors': []
        }
        
        try:
            # Navigate to feed
            await self.browser.navigate(self.THREADS_URL)
            await asyncio.sleep(gaussian_delay(2, 0.5, 1, 3))
            
            page = self.browser.page
            if not page:
                return result
            
            follows_done = 0
            
            # Find follow buttons
            follow_buttons = await page.query_selector_all('button:has-text("Follow"):not(:has-text("Following"))')
            
            for button in follow_buttons:
                if follows_done >= max_follows:
                    break
                
                if not self.rate_limiter.can_perform_action('threads', 'follows'):
                    result['errors'].append('Rate limit reached')
                    break
                
                try:
                    await asyncio.sleep(gaussian_delay(1.5, 0.5, 1, 3))
                    await button.click()
                    follows_done += 1
                    result['follows_done'] += 1
                    self.rate_limiter.record_action('threads', 'follows')
                    
                    await asyncio.sleep(gaussian_delay(2, 0.5, 1, 4))
                except:
                    pass
            
            return result
            
        except Exception as e:
            result['errors'].append(str(e))
            return result
    
    async def run_session(self, actions: List[str] = None) -> Dict:
        """
        Run a full engagement session on Threads.
        """
        if actions is None:
            actions = ['feed_likes']
        
        session_stats = {
            'actions_performed': [],
            'total_likes': 0,
            'total_follows': 0
        }
        
        for action in actions:
            if action == 'feed_likes':
                result = await self.engage_feed(max_likes=15)
                session_stats['total_likes'] += result['threads_liked']
                session_stats['actions_performed'].append({
                    'action': 'feed_likes',
                    'result': result
                })
            
            elif action == 'follows':
                result = await self.follow_from_thread(max_follows=5)
                session_stats['total_follows'] += result['follows_done']
                session_stats['actions_performed'].append({
                    'action': 'follows',
                    'result': result
                })
            
            # Delay between action types
            await asyncio.sleep(gaussian_delay(30, 10, 15, 60))
        
        return session_stats
    
    def get_stats(self) -> Dict:
        """Get current session statistics."""
        return self.stats.copy()


class ThreadsEngagementSync:
    """Synchronous wrapper for ThreadsEngagement."""
    
    def __init__(self, browser_manager, intensity: int = 1):
        from ..browser import SyncBrowserManager
        if isinstance(browser_manager, SyncBrowserManager):
            self.engagement = ThreadsEngagement(browser_manager.async_manager, intensity)
            self._loop = browser_manager._get_loop()
        else:
            self.engagement = ThreadsEngagement(browser_manager, intensity)
            self._loop = asyncio.new_event_loop()
    
    def engage_feed(self, max_likes: int = 20) -> Dict:
        return self._loop.run_until_complete(self.engagement.engage_feed(max_likes))
    
    def search_and_engage(self, query: str, max_likes: int = 10) -> Dict:
        return self._loop.run_until_complete(self.engagement.search_and_engage(query, max_likes))
    
    def run_session(self, actions: List[str] = None) -> Dict:
        return self._loop.run_until_complete(self.engagement.run_session(actions))
    
    def get_stats(self) -> Dict:
        return self.engagement.get_stats()
