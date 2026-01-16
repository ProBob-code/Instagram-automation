"""
IG Growth Hub - Instagram Profile Scraper
Extracts real profile data using Playwright
"""

import asyncio
import re
import aiohttp
from pathlib import Path
from typing import Dict, List, Optional
from ..browser import BrowserManager
from ..human_behavior import gaussian_delay


class InstagramScraper:
    """
    Scrapes Instagram profile data for analysis.
    Extracts bio, stats, captions, and hashtags.
    """
    
    INSTAGRAM_URL = 'https://www.instagram.com'
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        # Setup profile pics directory
        self.pics_dir = Path(__file__).parent.parent.parent / 'data' / 'profile_pics'
        self.pics_dir.mkdir(parents=True, exist_ok=True)
    
    async def scrape_profile(self, username: str) -> Dict:
        """
        Scrape complete profile data for analysis.
        
        Returns dict with:
        - username, name, bio
        - posts, followers, following counts
        - profile completeness indicators
        - recent captions and hashtags
        """
        try:
            # Navigate to profile page
            profile_url = f'{self.INSTAGRAM_URL}/{username}/'
            print(f"[Scraper] Navigating to profile: {profile_url}")
            await self.browser.navigate(profile_url, wait_for='domcontentloaded')
            await asyncio.sleep(gaussian_delay(3, 0.5, 2, 4))
            
            # Extract profile info
            profile_info = await self._extract_profile_info(username)
            
            # Get recent posts and extract captions/hashtags
            post_urls = await self._get_recent_post_urls(limit=6)
            
            if post_urls:
                captions_data = await self._scrape_post_captions(post_urls[:6])
                profile_info['captions'] = captions_data['captions']
                profile_info['hashtags'] = captions_data['hashtags']
            else:
                profile_info['captions'] = []
                profile_info['hashtags'] = []
            
            return profile_info
            
        except Exception as e:
            print(f"Scraping error: {e}")
            raise
    
    async def _extract_profile_info(self, username: str) -> Dict:
        """Extract basic profile information from profile page."""
        page = self.browser.page
        
        profile = {
            'username': username,
            'name': '',
            'bio': '',
            'profile_pic_url': '',
            'posts': 0,
            'followers': 0,
            'following': 0,
            'is_private': False,
            'has_profile_pic': True,
            'has_highlights': False,
            'has_external_link': False,
            'email': None,
            'captions': [],
            'hashtags': []
        }
        
        try:
            # Wait for profile content to load
            await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 2))
            
            # Extract profile picture URL
            print("[Scraper] Extracting profile picture...")
            pic_selectors = [
                'header img[alt*="profile picture"]',
                'header img[data-testid="user-avatar"]',
                'header canvas + img',
                'img[alt*="profile"]'
            ]
            for selector in pic_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        src = await element.get_attribute('src')
                        if src and src.startswith('http'):
                            profile['profile_pic_url'] = src
                            print(f"[Scraper] Found profile pic: {src[:50]}...")
                            break
                except:
                    continue
            
            # Fallback: try meta og:image
            if not profile['profile_pic_url']:
                try:
                    meta = await page.query_selector('meta[property="og:image"]')
                    if meta:
                        content = await meta.get_attribute('content')
                        if content:
                            profile['profile_pic_url'] = content
                except:
                    pass
            
            # Download profile pic to local storage
            if profile['profile_pic_url']:
                try:
                    local_pic = await self._download_profile_pic(username, profile['profile_pic_url'])
                    if local_pic:
                        profile['profile_pic_local'] = local_pic
                        print(f"[Scraper] Downloaded profile pic to: {local_pic}")
                except Exception as e:
                    print(f"[Scraper] Failed to download profile pic: {e}")
            
            # Extract name (display name)
            name_selectors = [
                'header section span',
                'header h2',
                '[class*="x1lliihq"]'  # Instagram's obfuscated class
            ]
            for selector in name_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and text.strip() and text.strip() != username:
                            profile['name'] = text.strip()
                            break
                except:
                    continue
            
            # Extract bio
            bio_selectors = [
                'header section > div > span',
                'header section div span[dir="auto"]',
                '[class*="-vDQh"]'  # Common bio class pattern
            ]
            for selector in bio_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and len(text) > 10 and '\n' in text or len(text) > 50:
                            profile['bio'] = text.strip()
                            break
                    if profile['bio']:
                        break
                except:
                    continue
            
            # Alternative bio extraction using meta description
            if not profile['bio']:
                try:
                    meta = await page.query_selector('meta[name="description"]')
                    if meta:
                        content = await meta.get_attribute('content')
                        if content and ':' in content:
                            # Format: "X Followers, Y Following, Z Posts - See Instagram photos..."
                            # Extract bio portion after the dash
                            parts = content.split(' - ')
                            if len(parts) > 1:
                                bio_part = parts[1].replace('See Instagram photos and videos from', '').strip()
                                if bio_part and len(bio_part) > 5:
                                    profile['bio'] = bio_part
                except:
                    pass
            
            # Extract stats (posts, followers, following)
            stats = await self._extract_stats(page)
            profile.update(stats)
            
            # Check for highlights
            highlights_selectors = [
                '[aria-label*="Highlight"]',
                'div[class*="x1n2onr6"] > div > ul',  # Highlights container
                'canvas[class*=""]'  # Highlight story rings
            ]
            for selector in highlights_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        profile['has_highlights'] = True
                        break
                except:
                    continue
            
            # Check for external link
            link_selectors = [
                'a[href*="l.instagram.com"]',
                'header a[rel="me nofollow noopener"]',
                '[class*="x1lliihq"] a[target="_blank"]'
            ]
            for selector in link_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        profile['has_external_link'] = True
                        break
                except:
                    continue
            
            # Extract email from bio
            if profile['bio']:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', profile['bio'])
                if email_match:
                    profile['email'] = email_match.group()
            
            # Check if private
            try:
                private_text = await page.query_selector('text="This account is private"')
                if private_text:
                    profile['is_private'] = True
            except:
                pass
            
            return profile
            
        except Exception as e:
            print(f"Profile extraction error: {e}")
            return profile
    
    async def _extract_stats(self, page) -> Dict:
        """Extract follower/following/posts counts."""
        stats = {'posts': 0, 'followers': 0, 'following': 0}
        
        try:
            # Try to get stats from meta description first (most reliable)
            meta = await page.query_selector('meta[name="description"]')
            if meta:
                content = await meta.get_attribute('content')
                if content:
                    # Parse "X Followers, Y Following, Z Posts"
                    followers_match = re.search(r'([\d,\.]+[KMB]?)\s*Followers', content, re.IGNORECASE)
                    following_match = re.search(r'([\d,\.]+[KMB]?)\s*Following', content, re.IGNORECASE)
                    posts_match = re.search(r'([\d,\.]+[KMB]?)\s*Posts', content, re.IGNORECASE)
                    
                    if followers_match:
                        stats['followers'] = self._parse_count(followers_match.group(1))
                    if following_match:
                        stats['following'] = self._parse_count(following_match.group(1))
                    if posts_match:
                        stats['posts'] = self._parse_count(posts_match.group(1))
                    
                    if stats['followers'] > 0:
                        return stats
            
            # Fallback: try to extract from page elements
            stat_selectors = [
                'header section ul li',
                'header ul li span',
                '[class*="x78zum5"] span'
            ]
            
            for selector in stat_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    texts = []
                    for el in elements:
                        text = await el.text_content()
                        if text:
                            texts.append(text.strip())
                    
                    # Look for patterns like "123 posts", "1.2K followers"
                    for text in texts:
                        if 'post' in text.lower():
                            num = re.search(r'([\d,\.]+[KMB]?)', text)
                            if num:
                                stats['posts'] = self._parse_count(num.group(1))
                        elif 'follower' in text.lower():
                            num = re.search(r'([\d,\.]+[KMB]?)', text)
                            if num:
                                stats['followers'] = self._parse_count(num.group(1))
                        elif 'following' in text.lower():
                            num = re.search(r'([\d,\.]+[KMB]?)', text)
                            if num:
                                stats['following'] = self._parse_count(num.group(1))
                except:
                    continue
            
            return stats
            
        except Exception as e:
            print(f"Stats extraction error: {e}")
            return stats
    
    def _parse_count(self, text: str) -> int:
        """Parse follower count string like '1.2K' or '1,234' to int."""
        if not text:
            return 0
        
        text = text.strip().upper().replace(',', '')
        
        try:
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            elif 'B' in text:
                return int(float(text.replace('B', '')) * 1000000000)
            else:
                return int(float(text))
        except:
            return 0
    
    async def _download_profile_pic(self, username: str, url: str) -> Optional[str]:
        """Download profile picture to local storage."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Determine file extension
                        content_type = response.headers.get('Content-Type', '')
                        ext = 'jpg'
                        if 'png' in content_type:
                            ext = 'png'
                        elif 'webp' in content_type:
                            ext = 'webp'
                        
                        # Save to file
                        filename = f"{username}.{ext}"
                        filepath = self.pics_dir / filename
                        
                        content = await response.read()
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        return f"/api/profile-pic/{username}"
        except Exception as e:
            print(f"[Scraper] Profile pic download error: {e}")
        return None
    
    async def _get_recent_post_urls(self, limit: int = 6) -> List[str]:
        """Get URLs of recent posts from profile grid."""
        page = self.browser.page
        post_urls = []
        
        try:
            # Wait for posts grid to load
            await asyncio.sleep(gaussian_delay(1, 0.3, 0.5, 1.5))
            
            # Find post links in grid
            post_selectors = [
                'article a[href*="/p/"]',
                'main article a[href*="/p/"]',
                'a[href*="/p/"][role="link"]'
            ]
            
            for selector in post_selectors:
                try:
                    links = await page.query_selector_all(selector)
                    for link in links[:limit]:
                        href = await link.get_attribute('href')
                        if href and '/p/' in href:
                            if not href.startswith('http'):
                                href = f'{self.INSTAGRAM_URL}{href}'
                            if href not in post_urls:
                                post_urls.append(href)
                    
                    if post_urls:
                        break
                except:
                    continue
            
            return post_urls[:limit]
            
        except Exception as e:
            print(f"Post URL extraction error: {e}")
            return []
    
    async def _scrape_post_captions(self, post_urls: List[str]) -> Dict:
        """Scrape captions and hashtags from posts."""
        captions = []
        all_hashtags = []
        
        for url in post_urls:
            try:
                await self.browser.navigate(url, wait_for='domcontentloaded')
                await asyncio.sleep(gaussian_delay(2, 0.5, 1.5, 3))
                
                page = self.browser.page
                caption = ''
                
                # Try to extract caption
                caption_selectors = [
                    'article div[class*="C4VMK"] span',
                    'article h1 + div span',
                    'article span[dir="auto"]',
                    '[class*="_a9zs"] span'
                ]
                
                for selector in caption_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            text = await element.text_content()
                            if text and len(text) > 20:
                                caption = text.strip()
                                break
                        if caption:
                            break
                    except:
                        continue
                
                # Alternative: try meta description
                if not caption:
                    try:
                        meta = await page.query_selector('meta[property="og:description"]')
                        if meta:
                            content = await meta.get_attribute('content')
                            if content and len(content) > 10:
                                caption = content.strip()
                    except:
                        pass
                
                if caption:
                    captions.append(caption)
                    
                    # Extract hashtags from caption
                    hashtags = re.findall(r'#(\w+)', caption)
                    if hashtags:
                        all_hashtags.append(hashtags)
                
                # Small delay between posts
                await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.3, 1))
                
            except Exception as e:
                print(f"Caption extraction error for {url}: {e}")
                continue
        
        return {
            'captions': captions,
            'hashtags': all_hashtags
        }


class InstagramScraperSync:
    """Synchronous wrapper for InstagramScraper."""
    
    def __init__(self, browser_manager):
        from ..browser import SyncBrowserManager
        if isinstance(browser_manager, SyncBrowserManager):
            self.scraper = InstagramScraper(browser_manager.async_manager)
            self._loop = browser_manager._get_loop()
        else:
            self.scraper = InstagramScraper(browser_manager)
            self._loop = asyncio.new_event_loop()
    
    def scrape_profile(self, username: str) -> Dict:
        return self._loop.run_until_complete(self.scraper.scrape_profile(username))
