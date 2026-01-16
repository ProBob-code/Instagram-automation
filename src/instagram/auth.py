"""
IG Growth Hub - Instagram Authentication
Handles login, session management, and 2FA
"""

import asyncio
import re
from pathlib import Path
from typing import Optional, Tuple
from ..browser import BrowserManager
from ..human_behavior import gaussian_delay


class InstagramAuth:
    """
    Handles Instagram authentication with session persistence.
    """
    
    INSTAGRAM_URL = 'https://www.instagram.com'
    LOGIN_URL = 'https://www.instagram.com/accounts/login/'
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.is_logged_in = False
        self.username = None
    
    async def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Login to Instagram.
        Returns (success, message) tuple.
        """
        self.username = username
        
        try:
            # Navigate to login page
            print(f"[Auth] Navigating to Instagram login page...")
            await self.browser.navigate(self.LOGIN_URL)
            await asyncio.sleep(gaussian_delay(3, 0.5, 2, 5))
            
            # Check if already logged in
            if await self._check_logged_in():
                self.is_logged_in = True
                print("[Auth] Already logged in from saved session!")
                return True, "Already logged in"
            
            # Enter username
            print(f"[Auth] Entering username: {username}")
            username_selector = 'input[name="username"]'
            if not await self.browser.wait_for_element(username_selector, timeout=15000):
                return False, "Login page not loaded - couldn't find username field"
            
            await self.browser.type_text(username_selector, username)
            await asyncio.sleep(gaussian_delay(0.8, 0.2, 0.5, 1.5))
            
            # Enter password
            print("[Auth] Entering password...")
            password_selector = 'input[name="password"]'
            await self.browser.type_text(password_selector, password)
            await asyncio.sleep(gaussian_delay(0.8, 0.2, 0.5, 1.5))
            
            # Click login button
            print("[Auth] Clicking login button...")
            login_button = 'button[type="submit"]'
            await self.browser.click(login_button)
            
            # Wait longer for login to process
            print("[Auth] Waiting for login to complete...")
            await asyncio.sleep(gaussian_delay(8, 2, 5, 12))
            
            # Check current URL to see where we are
            page = self.browser.page
            current_url = page.url if page else ""
            print(f"[Auth] Current URL after login attempt: {current_url}")
            
            # Check for 2FA
            if await self._check_2fa_required():
                print("[Auth] 2FA verification required")
                return False, "2FA_REQUIRED"
            
            # Check for error messages
            error = await self._check_login_error()
            if error:
                print(f"[Auth] Login error detected: {error}")
                return False, error
            
            # Try to dismiss popups multiple times
            print("[Auth] Checking for popups...")
            for _ in range(3):
                await self._dismiss_popups()
                await asyncio.sleep(1)
            
            # Wait a bit more and check again
            await asyncio.sleep(2)
            
            # Verify login successful
            if await self._check_logged_in():
                self.is_logged_in = True
                print("[Auth] Login successful!")
                await self.browser.save_session(username)
                return True, "Login successful"
            
            # If URL changed away from login page, we might be logged in
            if 'login' not in current_url.lower() and 'instagram.com' in current_url:
                print("[Auth] URL suggests login successful, proceeding...")
                self.is_logged_in = True
                await self.browser.save_session(username)
                return True, "Login successful"
            
            print("[Auth] Could not verify login success")
            return False, "Login failed - could not verify success. Check if browser shows Instagram home."
            
        except Exception as e:
            print(f"[Auth] Exception during login: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Login error: {str(e)}"
    
    async def _check_logged_in(self) -> bool:
        """Check if user is currently logged in."""
        page = self.browser.page
        if not page:
            return False
        
        try:
            # Look for elements that only appear when logged in
            selectors = [
                '[aria-label="Home"]',
                '[aria-label="New post"]',
                'svg[aria-label="Home"]'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    return True
            
            return False
        except:
            return False
    
    async def _check_2fa_required(self) -> bool:
        """Check if 2FA verification is required."""
        page = self.browser.page
        if not page:
            return False
        
        try:
            # Look for security code input
            selectors = [
                'input[name="verificationCode"]',
                'input[name="security_code"]',
                '[aria-label="Security Code"]'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    return True
            
            return False
        except:
            return False
    
    async def submit_2fa_code(self, code: str) -> Tuple[bool, str]:
        """Submit 2FA verification code."""
        try:
            code_selector = 'input[name="verificationCode"], input[name="security_code"]'
            await self.browser.type_text(code_selector, code)
            await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.3, 1))
            
            # Click confirm button
            confirm_button = 'button[type="button"]'
            await self.browser.click(confirm_button)
            await asyncio.sleep(gaussian_delay(3, 1, 2, 5))
            
            # Dismiss popups
            await self._dismiss_popups()
            
            if await self._check_logged_in():
                self.is_logged_in = True
                await self.browser.save_session(self.username)
                return True, "2FA verified"
            
            return False, "2FA verification failed"
            
        except Exception as e:
            return False, f"2FA error: {str(e)}"
    
    async def _check_login_error(self) -> Optional[str]:
        """Check for login error messages."""
        page = self.browser.page
        if not page:
            return None
        
        try:
            # Common error selectors
            error_selectors = [
                '[role="alert"]',
                '#slfErrorAlert',
                '.eiCW-'
            ]
            
            for selector in error_selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
            
            return None
        except:
            return None
    
    async def _dismiss_popups(self):
        """Dismiss common popups after login."""
        page = self.browser.page
        if not page:
            return
        
        try:
            # "Save Login Info" popup
            save_info_buttons = [
                'button:has-text("Not Now")',
                'button:has-text("Save Info")',
                '[role="button"]:has-text("Not Now")'
            ]
            
            for selector in save_info_buttons:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        await button.click()
                        await asyncio.sleep(1)
                except:
                    pass
            
            # "Turn on Notifications" popup
            notification_buttons = [
                'button:has-text("Not Now")',
                '[role="button"]:has-text("Not Now")'
            ]
            
            for selector in notification_buttons:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        await button.click()
                        await asyncio.sleep(1)
                except:
                    pass
                    
        except:
            pass
    
    async def logout(self) -> bool:
        """Logout from Instagram."""
        try:
            # Navigate to profile
            await self.browser.navigate(f'{self.INSTAGRAM_URL}/{self.username}/')
            await asyncio.sleep(gaussian_delay(2, 0.5, 1, 3))
            
            # Click settings menu
            settings_selector = '[aria-label="Settings"]'
            await self.browser.click(settings_selector)
            await asyncio.sleep(1)
            
            # Click logout
            logout_selector = 'button:has-text("Log Out"), [role="button"]:has-text("Log Out")'
            await self.browser.click(logout_selector)
            await asyncio.sleep(2)
            
            self.is_logged_in = False
            return True
            
        except Exception as e:
            print(f"Logout error: {e}")
            return False


class InstagramAuthSync:
    """Synchronous wrapper for InstagramAuth."""
    
    def __init__(self, browser_manager):
        from ..browser import SyncBrowserManager
        if isinstance(browser_manager, SyncBrowserManager):
            self.auth = InstagramAuth(browser_manager.async_manager)
            self._loop = browser_manager._get_loop()
        else:
            self.auth = InstagramAuth(browser_manager)
            self._loop = asyncio.new_event_loop()
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        return self._loop.run_until_complete(self.auth.login(username, password))
    
    def submit_2fa_code(self, code: str) -> Tuple[bool, str]:
        return self._loop.run_until_complete(self.auth.submit_2fa_code(code))
    
    def logout(self) -> bool:
        return self._loop.run_until_complete(self.auth.logout())
