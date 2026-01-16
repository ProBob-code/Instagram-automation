"""
IG Growth Hub - Instagram Actions
Performs real actions like liking, following, commenting on Instagram.
"""

import asyncio
import random
from typing import Dict, Optional
from ..browser import BrowserManager
from ..human_behavior import gaussian_delay


class InstagramActions:
    """
    Performs real Instagram actions: like, follow, comment, view reels.
    Uses Playwright for browser automation.
    """
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
    
    async def like_post(self) -> Dict:
        """
        Like the currently viewed post using robust JS-based methods.
        Returns {'success': True} or {'success': False, 'error': '...'}
        """
        page = self.browser.page
        
        try:
            # Wait for content to stabilize
            await asyncio.sleep(2)
            
            # Check if already liked
            unlike_btn = await page.query_selector('svg[aria-label="Unlike"]')
            if unlike_btn:
                return {'success': True, 'already_liked': True}
            
            # MANDATORY VERIFICATION HELPER
            async def verify_liked():
                await asyncio.sleep(2)
                # Check for "Unlike" aria-label or red heart fill
                unlike_btn = await page.query_selector('svg[aria-label="Unlike"]')
                if unlike_btn:
                    return True
                # Check if the SVG path changed to the filled heart (Instagram sometimes delays label update)
                # Filled heart path usually starts with 'M1 7.66c0 4.575 3.899 9.086 9.987 12.934.338.203.74.406 1.013.406s.675-.203...'
                # But checking the label is usually enough if we wait.
                return False

            # METHOD 0: User-provided Specific Selectors (High Priority)
            try:
                # 1. User's XPath
                user_xpath = '/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/section/main/div/div[1]/div/div[2]/div/div[3]/section/div[1]/span[1]/div/div/div/span/svg'
                # 2. User's CSS (Generalized from dynamic mount ID)
                user_css = 'div[id^="mount_0_0_"] section > main > div > div section div.x6s0dn4.x78zum5 span.x1qfufaz svg'
                
                for selector in [f'xpath={user_xpath}', user_css]:
                    el = await page.query_selector(selector)
                    if el:
                        # Find the parent button/div to click
                        clickable = await el.evaluate_handle('el => el.closest("div[role=\'button\']") || el.closest("span") || el.parentElement')
                        if clickable:
                            await clickable.as_element().click()
                            if await verify_liked():
                                print(f"[Actions] Successfully liked using user selector: {selector[:30]}...")
                                return {'success': True, 'method': 'user_selector'}
            except: pass

            # METHOD 1: Scoped JS-based Click (Reliable for posts/reels)
            try:
                liked = await page.evaluate('''() => {
                    const svgs = document.querySelectorAll('svg[aria-label="Like"]');
                    for (const svg of svgs) {
                        if (svg.closest('ul')) continue; // Skip comments
                        const section = svg.closest('section');
                        const article = svg.closest('article');
                        if (section && article) {
                            let parent = svg.closest('div[role="button"]') || svg.closest('span') || svg.parentElement;
                            if (parent) { parent.click(); return true; }
                        }
                    }
                    return false;
                }''')
                if liked and await verify_liked():
                    print("[Actions] Liked via scoped JS verification pass")
                    return {'success': True, 'method': 'js_click_scoped'}
            except: pass

            # METHOD 2: Double-click media
            try:
                media = await page.query_selector('article div[role="button"] img, article video, article ._aagv img')
                if media:
                    await media.dblclick()
                    if await verify_liked():
                        print("[Actions] Liked via double-click")
                        return {'success': True, 'method': 'double_click'}
            except: pass

            return {'success': False, 'error': 'All like methods failed or could not be verified'}
            
        except Exception as e:
            print(f"[Actions] Like error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def follow_user(self, username: str = None) -> Dict:
        """
        Follow the user of the currently viewed post or navigate to their profile.
        """
        page = self.browser.page
        
        try:
            # Find the follow button
            follow_selectors = [
                'button:has-text("Follow")',
                '[aria-label="Follow"]',
                'header button:has-text("Follow")'
            ]
            
            for selector in follow_selectors:
                try:
                    follow_btn = await page.query_selector(selector)
                    if follow_btn:
                        text = await follow_btn.text_content()
                        # Make sure it says "Follow" not "Following"
                        if text and 'Following' not in text:
                            await follow_btn.click()
                            await asyncio.sleep(gaussian_delay(1.5, 0.5, 1, 2.5))
                            return {'success': True}
                except:
                    continue
            
            return {'success': False, 'error': 'Follow button not found'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def comment_on_post(self, comment_text: str) -> Dict:
        """
        Add a comment to the currently viewed post.
        """
        page = self.browser.page
        
        try:
            # Find comment input
            comment_selectors = [
                'textarea[placeholder*="comment"]',
                'textarea[aria-label*="comment"]',
                'form textarea'
            ]
            
            comment_input = None
            for selector in comment_selectors:
                try:
                    comment_input = await page.query_selector(selector)
                    if comment_input:
                        break
                except:
                    continue
            
            if not comment_input:
                return {'success': False, 'error': 'Comment input not found'}
            
            # Click to focus and type comment
            await comment_input.click()
            await asyncio.sleep(0.5)
            await comment_input.fill(comment_text)
            await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 1.5))
            
            # Find and click post button
            post_btn = await page.query_selector('button:has-text("Post")')
            if post_btn:
                await post_btn.click()
                await asyncio.sleep(gaussian_delay(2, 0.5, 1.5, 3))
                return {'success': True}
            else:
                return {'success': False, 'error': 'Post button not found'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def view_reel(self, reel_url: str = None) -> Dict:
        """
        View a reel (watch for a few seconds).
        If reel_url is provided, navigate to it first.
        """
        page = self.browser.page
        
        try:
            if reel_url:
                await self.browser.navigate(reel_url, wait_for='domcontentloaded')
                await asyncio.sleep(gaussian_delay(2, 0.5, 1.5, 3))
            
            # Watch the reel for 5-15 seconds (simulating real viewing)
            watch_time = random.uniform(5, 15)
            print(f"[Actions] Watching reel for {watch_time:.0f}s...")
            await asyncio.sleep(watch_time)
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
