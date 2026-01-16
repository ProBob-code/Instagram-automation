"""
IG Growth Hub - Browser Automation
Playwright-based browser control with anti-detection
"""

import random
import asyncio
from pathlib import Path
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """
    Manages browser instances with anti-detection measures.
    Uses Playwright for better stealth than Selenium.
    """
    
    def __init__(self, headless: bool = False, proxy: str = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Session storage path
        self.sessions_dir = Path(__file__).parent.parent / 'data' / 'sessions'
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
        
        # Viewport sizes
        self.viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
        ]
    
    async def start(self, session_name: str = 'default') -> Page:
        """Start browser with anti-detection measures."""
        self.playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        }
        
        if self.proxy:
            launch_options['proxy'] = {'server': self.proxy}
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Context options with anti-detection
        user_agent = random.choice(self.user_agents)
        viewport = random.choice(self.viewports)
        
        session_file = self.sessions_dir / f'{session_name}_state.json'
        
        context_options = {
            'user_agent': user_agent,
            'viewport': viewport,
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': ['geolocation'],
            'java_script_enabled': True,
        }
        
        # Load existing session if available
        if session_file.exists():
            context_options['storage_state'] = str(session_file)
        
        self.context = await self.browser.new_context(**context_options)
        
        # Add anti-detection scripts
        await self._add_stealth_scripts()
        
        self.page = await self.context.new_page()
        
        return self.page
    
    async def _add_stealth_scripts(self):
        """Add scripts to evade bot detection."""
        await self.context.add_init_script("""
            // Overwrite the 'webdriver' property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Overwrite the plugins property
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Overwrite the languages property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
    
    async def save_session(self, session_name: str = 'default'):
        """Save current session state."""
        if self.context:
            session_file = self.sessions_dir / f'{session_name}_state.json'
            await self.context.storage_state(path=str(session_file))
    
    async def close(self, save_session: bool = True, session_name: str = 'default'):
        """Close browser and optionally save session."""
        if save_session and self.context:
            await self.save_session(session_name)
        
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def navigate(self, url: str, wait_for: str = 'domcontentloaded', timeout: int = 30000):
        """Navigate to URL with human-like behavior."""
        if self.page:
            try:
                await self.page.goto(url, wait_until=wait_for, timeout=timeout)
            except Exception as e:
                print(f"[Browser] Navigation warning: {e}")
                # Continue anyway - page might still be usable
            await asyncio.sleep(random.uniform(1, 2))
    
    async def scroll(self, direction: str = 'down', amount: int = None):
        """Scroll with human-like behavior."""
        if not self.page:
            return
        
        if amount is None:
            amount = random.randint(200, 600)
        
        if direction == 'down':
            await self.page.mouse.wheel(0, amount)
        else:
            await self.page.mouse.wheel(0, -amount)
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
    
    async def click(self, selector: str, timeout: int = 10000):
        """Click element with human-like behavior."""
        if not self.page:
            return False
        
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                # Move mouse naturally before clicking
                box = await element.bounding_box()
                if box:
                    x = box['x'] + box['width'] / 2 + random.randint(-5, 5)
                    y = box['y'] + box['height'] / 2 + random.randint(-5, 5)
                    await self.page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                await element.click()
                return True
        except Exception as e:
            print(f"Click error: {e}")
        
        return False
    
    async def type_text(self, selector: str, text: str, human_like: bool = True):
        """Type text with human-like delays."""
        if not self.page:
            return False
        
        try:
            element = await self.page.wait_for_selector(selector)
            if element:
                await element.click()
                await asyncio.sleep(random.uniform(0.2, 0.5))
                
                if human_like:
                    for char in text:
                        await self.page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                else:
                    await element.fill(text)
                
                return True
        except Exception as e:
            print(f"Type error: {e}")
        
        return False
    
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element to appear."""
        if not self.page:
            return False
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except:
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """Get text content of element."""
        if not self.page:
            return None
        
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if element:
                return await element.text_content()
        except:
            pass
        
        return None
    
    async def screenshot(self, path: str):
        """Take screenshot."""
        if self.page:
            await self.page.screenshot(path=path)
    
    async def get_cookies(self) -> list:
        """Get all cookies."""
        if self.context:
            return await self.context.cookies()
        return []
    
    async def is_logged_in(self, platform: str = 'instagram') -> bool:
        """Check if currently logged in to platform."""
        if not self.page:
            return False
        
        if platform == 'instagram':
            # Check for elements that only appear when logged in
            try:
                await self.page.goto('https://www.instagram.com/')
                await asyncio.sleep(2)
                # Look for profile icon or home feed indicator
                logged_in = await self.page.query_selector('[aria-label="Home"]')
                return logged_in is not None
            except:
                return False
        
        return False


# Synchronous wrapper for easier use
class SyncBrowserManager:
    """Synchronous wrapper for BrowserManager."""
    
    def __init__(self, headless: bool = False, proxy: str = None):
        self.async_manager = BrowserManager(headless, proxy)
        self._loop = None
    
    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop
    
    def start(self, session_name: str = 'default'):
        return self._get_loop().run_until_complete(
            self.async_manager.start(session_name)
        )
    
    def close(self, save_session: bool = True, session_name: str = 'default'):
        return self._get_loop().run_until_complete(
            self.async_manager.close(save_session, session_name)
        )
    
    def navigate(self, url: str):
        return self._get_loop().run_until_complete(
            self.async_manager.navigate(url)
        )
    
    def click(self, selector: str):
        return self._get_loop().run_until_complete(
            self.async_manager.click(selector)
        )
    
    def type_text(self, selector: str, text: str):
        return self._get_loop().run_until_complete(
            self.async_manager.type_text(selector, text)
        )
    
    def scroll(self, direction: str = 'down'):
        return self._get_loop().run_until_complete(
            self.async_manager.scroll(direction)
        )
