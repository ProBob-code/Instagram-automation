"""
IG Growth Hub - Threads Authentication
Handles Threads login via Instagram credentials
"""

import asyncio
from typing import Tuple
from ..browser import BrowserManager
from ..human_behavior import gaussian_delay


class ThreadsAuth:
    """
    Handles Threads authentication.
    Uses Instagram credentials since Threads is linked to Instagram.
    """
    
    THREADS_URL = 'https://www.threads.net'
    LOGIN_URL = 'https://www.threads.net/login'
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.is_logged_in = False
        self.username = None
    
    async def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Login to Threads using Instagram credentials.
        Returns (success, message) tuple.
        """
        self.username = username
        
        try:
            # Navigate to Threads login
            await self.browser.navigate(self.LOGIN_URL)
            await asyncio.sleep(gaussian_delay(2, 0.5, 1, 4))
            
            # Check if already logged in
            if await self._check_logged_in():
                self.is_logged_in = True
                return True, "Already logged in"
            
            # Click "Log in with Instagram" button
            ig_login_button = 'button:has-text("Log in with Instagram"), [role="button"]:has-text("Continue with Instagram")'
            await self.browser.click(ig_login_button)
            await asyncio.sleep(gaussian_delay(2, 0.5, 1, 3))
            
            # Enter username
            username_selector = 'input[name="username"], input[aria-label="Username"]'
            if await self.browser.wait_for_element(username_selector, timeout=5000):
                await self.browser.type_text(username_selector, username)
                await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.3, 1))
            
            # Enter password
            password_selector = 'input[name="password"], input[aria-label="Password"]'
            await self.browser.type_text(password_selector, password)
            await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.3, 1))
            
            # Click login button
            login_button = 'button[type="submit"], button:has-text("Log in")'
            await self.browser.click(login_button)
            await asyncio.sleep(gaussian_delay(4, 1, 2, 6))
            
            # Dismiss any popups
            await self._dismiss_popups()
            
            # Verify login
            if await self._check_logged_in():
                self.is_logged_in = True
                await self.browser.save_session(f'threads_{username}')
                return True, "Login successful"
            
            return False, "Login failed"
            
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    async def login_if_instagram_session_exists(self) -> Tuple[bool, str]:
        """
        Try to login using existing Instagram session.
        Faster if user already logged into Instagram.
        """
        try:
            await self.browser.navigate(self.THREADS_URL)
            await asyncio.sleep(gaussian_delay(3, 1, 2, 5))
            
            if await self._check_logged_in():
                self.is_logged_in = True
                return True, "Logged in via Instagram session"
            
            return False, "No active session"
            
        except Exception as e:
            return False, f"Session check error: {str(e)}"
    
    async def _check_logged_in(self) -> bool:
        """Check if user is currently logged in to Threads."""
        page = self.browser.page
        if not page:
            return False
        
        try:
            # Look for elements that only appear when logged in
            selectors = [
                '[aria-label="Home"]',
                '[aria-label="Create"]',
                '[aria-label="Profile"]',
                'svg[aria-label="Home"]'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    return True
            
            # Check URL - if on feed, user is logged in
            url = page.url
            if '/home' in url or '/@' in url:
                return True
            
            return False
        except:
            return False
    
    async def _dismiss_popups(self):
        """Dismiss common popups after login."""
        page = self.browser.page
        if not page:
            return
        
        try:
            popup_buttons = [
                'button:has-text("Not Now")',
                'button:has-text("Skip")',
                'button:has-text("Maybe Later")',
                '[role="button"]:has-text("Not Now")'
            ]
            
            for selector in popup_buttons:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        await button.click()
                        await asyncio.sleep(1)
                except:
                    pass
        except:
            pass


class ThreadsAuthSync:
    """Synchronous wrapper for ThreadsAuth."""
    
    def __init__(self, browser_manager):
        from ..browser import SyncBrowserManager
        if isinstance(browser_manager, SyncBrowserManager):
            self.auth = ThreadsAuth(browser_manager.async_manager)
            self._loop = browser_manager._get_loop()
        else:
            self.auth = ThreadsAuth(browser_manager)
            self._loop = asyncio.new_event_loop()
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        return self._loop.run_until_complete(self.auth.login(username, password))
    
    def login_if_instagram_session_exists(self) -> Tuple[bool, str]:
        return self._loop.run_until_complete(self.auth.login_if_instagram_session_exists())
