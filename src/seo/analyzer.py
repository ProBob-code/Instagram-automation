"""
IG Growth Hub - SEO Profile Analyzer
Scores profiles based on discoverability best practices
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ProfileData:
    """Container for profile data."""
    username: str
    name: str
    bio: str
    posts_count: int
    followers_count: int
    following_count: int
    is_private: bool
    has_profile_pic: bool
    has_highlights: bool
    has_external_link: bool
    email_in_bio: Optional[str]
    recent_captions: List[str]
    recent_hashtags: List[List[str]]


class SEOAnalyzer:
    """
    Analyzes Instagram profiles for SEO optimization.
    Based on Creator Collab Process best practices.
    """
    
    # Scoring weights (out of 100)
    WEIGHTS = {
        'bio': 25,
        'name': 15,
        'content': 20,
        'hashtags': 15,
        'engagement': 15,
        'completeness': 10
    }
    
    # Niche keywords for detection
    NICHE_KEYWORDS = {
        'fitness': ['fitness', 'workout', 'gym', 'health', 'muscle', 'training', 'coach', 'fit', 'gains', 'exercise'],
        'lifestyle': ['lifestyle', 'life', 'daily', 'routine', 'living', 'vibes', 'aesthetic'],
        'fashion': ['fashion', 'style', 'outfit', 'ootd', 'clothing', 'wear', 'designer', 'streetwear'],
        'tech': ['tech', 'technology', 'developer', 'coding', 'programmer', 'software', 'startup'],
        'food': ['food', 'foodie', 'recipe', 'cooking', 'chef', 'eat', 'restaurant', 'cuisine'],
        'travel': ['travel', 'wanderlust', 'explore', 'adventure', 'trip', 'destination', 'journey'],
        'beauty': ['beauty', 'makeup', 'skincare', 'cosmetics', 'glam', 'mua', 'glow'],
        'business': ['entrepreneur', 'business', 'startup', 'founder', 'ceo', 'marketing', 'money'],
        'creator': ['creator', 'content', 'reels', 'influencer', 'blogger', 'vlogger']
    }
    
    def __init__(self):
        self.profile: Optional[ProfileData] = None
        self.scores: Dict[str, Dict] = {}
        self.suggestions: List[Dict] = []
        self.detected_niche: Optional[str] = None
    
    def analyze(self, profile: ProfileData) -> Dict:
        """
        Perform full analysis on a profile.
        Returns comprehensive score breakdown and suggestions.
        """
        self.profile = profile
        self.scores = {}
        self.suggestions = []
        
        # Detect niche from profile content
        self.detected_niche = self._detect_niche()
        
        # Calculate individual scores
        self.scores['bio'] = self._analyze_bio()
        self.scores['name'] = self._analyze_name()
        self.scores['content'] = self._analyze_content()
        self.scores['hashtags'] = self._analyze_hashtags()
        self.scores['engagement'] = self._analyze_engagement()
        self.scores['completeness'] = self._analyze_completeness()
        
        # Calculate total score
        total = sum(s['score'] for s in self.scores.values())
        
        return {
            'total': total,
            'breakdown': self.scores,
            'suggestions': self.suggestions,
            'detected_niche': self.detected_niche
        }
    
    def _detect_niche(self) -> Optional[str]:
        """Detect the profile's primary niche from bio and content."""
        text = f"{self.profile.bio} {self.profile.name}".lower()
        
        # Add caption text
        for caption in self.profile.recent_captions[:5]:
            text += f" {caption.lower()}"
        
        # Count keyword matches per niche
        niche_scores = {}
        for niche, keywords in self.NICHE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                niche_scores[niche] = score
        
        if niche_scores:
            return max(niche_scores, key=niche_scores.get)
        
        return None
    
    def _analyze_bio(self) -> Dict:
        """Analyze bio for SEO optimization."""
        bio = self.profile.bio
        max_score = self.WEIGHTS['bio']
        score = 0
        issues = []
        
        # Check bio length (ideal: 100-150 chars)
        bio_len = len(bio)
        if bio_len == 0:
            issues.append("Bio is empty")
        elif bio_len < 50:
            score += 2
            issues.append("Bio is too short")
        elif bio_len < 100:
            score += 4
            issues.append("Bio could be more descriptive")
        elif bio_len <= 150:
            score += 6
        else:
            score += 5  # Slightly penalize very long bios
        
        # Check for niche keywords
        has_niche_keywords = False
        for niche, keywords in self.NICHE_KEYWORDS.items():
            if any(kw in bio.lower() for kw in keywords):
                has_niche_keywords = True
                break
        
        if has_niche_keywords:
            score += 6
        else:
            issues.append("No niche keywords found in bio")
            self.suggestions.append({
                'category': 'BIO',
                'priority': 'high',
                'text': 'Add niche-specific keywords to your bio',
                'example': f'Instead of generic terms, include keywords like "{self._get_niche_examples()}"'
            })
        
        # Check for email
        if self.profile.email_in_bio:
            score += 5
        else:
            issues.append("No email in bio")
            self.suggestions.append({
                'category': 'BIO',
                'priority': 'medium',
                'text': 'Add a contact email to your bio',
                'example': 'Brands filter for creators with visible contact info: 📩 yourmail@gmail.com'
            })
        
        # Check for call-to-action
        cta_patterns = ['dm', 'message', 'contact', 'book', 'link', 'shop', 'follow']
        has_cta = any(cta in bio.lower() for cta in cta_patterns)
        if has_cta:
            score += 4
        else:
            issues.append("No clear call-to-action")
        
        # Check for location
        location_pattern = r'📍|🌍|🏠|based in|from|\b[A-Z][a-z]+,\s*[A-Z]{2}\b'
        if re.search(location_pattern, bio):
            score += 4
        else:
            issues.append("No location indicator")
            self.suggestions.append({
                'category': 'BIO',
                'priority': 'low',
                'text': 'Add your location to improve local discovery',
                'example': 'Chennai | Mumbai | NYC - helps brands find local creators'
            })
        
        # Determine status
        score_pct = score / max_score
        if score_pct >= 0.7:
            status = 'pass'
        elif score_pct >= 0.4:
            status = 'warn'
        else:
            status = 'fail'
        
        return {
            'score': score,
            'max': max_score,
            'status': status,
            'issues': issues
        }
    
    def _analyze_name(self) -> Dict:
        """Analyze name field for SEO."""
        name = self.profile.name
        max_score = self.WEIGHTS['name']
        score = 0
        issues = []
        
        if not name:
            return {'score': 0, 'max': max_score, 'status': 'fail', 'issues': ['Name field is empty']}
        
        # Check if name contains niche keywords
        has_niche = False
        for niche, keywords in self.NICHE_KEYWORDS.items():
            if any(kw in name.lower() for kw in keywords):
                has_niche = True
                break
        
        if has_niche:
            score += 8
        else:
            issues.append("Name field doesn't include niche keywords")
            self.suggestions.append({
                'category': 'NAME FIELD',
                'priority': 'high',
                'text': 'Optimize your name field for search',
                'example': f'Format: "YourName | {self._get_niche_title()}" - This boosts discoverability'
            })
        
        # Check format (Name | Niche is optimal)
        if '|' in name or '-' in name:
            score += 4
        else:
            issues.append("Consider using 'Name | Niche' format")
        
        # Check length (not too long)
        if len(name) <= 30:
            score += 3
        else:
            issues.append("Name might be too long")
        
        # Determine status
        score_pct = score / max_score
        if score_pct >= 0.7:
            status = 'pass'
        elif score_pct >= 0.4:
            status = 'warn'
        else:
            status = 'fail'
        
        return {
            'score': score,
            'max': max_score,
            'status': status,
            'issues': issues
        }
    
    def _analyze_content(self) -> Dict:
        """Analyze content consistency."""
        max_score = self.WEIGHTS['content']
        score = 0
        issues = []
        
        posts = self.profile.posts_count
        captions = self.profile.recent_captions
        
        # Check post count
        if posts >= 30:
            score += 5
        elif posts >= 15:
            score += 3
        else:
            issues.append("Low post count")
            self.suggestions.append({
                'category': 'CONTENT',
                'priority': 'medium',
                'text': 'Increase posting frequency',
                'example': 'Aim for 3-5 reels per week for 30+ days to show consistency'
            })
        
        # Check caption quality
        avg_caption_len = sum(len(c) for c in captions) / len(captions) if captions else 0
        
        if avg_caption_len > 100:
            score += 5
        elif avg_caption_len > 50:
            score += 3
        else:
            issues.append("Captions are too short")
            self.suggestions.append({
                'category': 'CAPTIONS',
                'priority': 'high',
                'text': 'Write SEO-friendly captions with descriptive hooks',
                'example': 'Instead of "Consistency ❤️", try "Full day routine for [goal] - This [benefit] helps you [result]"'
            })
        
        # Check for niche consistency in captions
        if captions and self.detected_niche:
            niche_keywords = self.NICHE_KEYWORDS.get(self.detected_niche, [])
            niche_mentions = sum(
                1 for caption in captions
                if any(kw in caption.lower() for kw in niche_keywords)
            )
            consistency_rate = niche_mentions / len(captions) if captions else 0
            
            if consistency_rate >= 0.6:
                score += 6
            elif consistency_rate >= 0.3:
                score += 3
            else:
                issues.append("Content not consistently niche-focused")
        
        # Check if captions start with hooks (not just emojis)
        hooks_count = 0
        for caption in captions[:5]:
            if caption and not caption[0] in '😀🎉❤️✨💪🔥':
                if len(caption.split()[0]) > 2:  # First word is substantial
                    hooks_count += 1
        
        if hooks_count >= 3:
            score += 4
        else:
            issues.append("Captions lack strong opening hooks")
        
        # Determine status
        score_pct = score / max_score
        if score_pct >= 0.7:
            status = 'pass'
        elif score_pct >= 0.4:
            status = 'warn'
        else:
            status = 'fail'
        
        return {
            'score': score,
            'max': max_score,
            'status': status,
            'issues': issues
        }
    
    def _analyze_hashtags(self) -> Dict:
        """Analyze hashtag strategy."""
        max_score = self.WEIGHTS['hashtags']
        score = 0
        issues = []
        
        all_hashtags = [h for tags in self.profile.recent_hashtags for h in tags]
        
        if not all_hashtags:
            return {
                'score': 0, 
                'max': max_score, 
                'status': 'fail', 
                'issues': ['No hashtags found in recent posts']
            }
        
        # Check average hashtag count per post
        avg_tags = len(all_hashtags) / len(self.profile.recent_hashtags) if self.profile.recent_hashtags else 0
        
        if 5 <= avg_tags <= 10:
            score += 5
        elif 3 <= avg_tags <= 15:
            score += 3
        else:
            issues.append("Hashtag count not optimal (aim for 5-10)")
        
        # Check for niche hashtags
        niche_tags = [h for h in all_hashtags if 'creator' in h.lower() or 'niche' in h.lower()]
        if len(niche_tags) >= 2:
            score += 4
        else:
            self.suggestions.append({
                'category': 'HASHTAGS',
                'priority': 'high',
                'text': 'Use the 3-2-1 hashtag formula',
                'example': '3 niche (#fitnesscreator), 2 broad (#reels), 1 location (#mumbai)'
            })
        
        # Check for location hashtags
        location_indicators = ['india', 'usa', 'uk', 'chennai', 'mumbai', 'delhi', 'bangalore', 'nyc', 'la']
        has_location = any(loc in h.lower() for h in all_hashtags for loc in location_indicators)
        
        if has_location:
            score += 3
        else:
            issues.append("No location-based hashtags")
        
        # Check for hashtag variety
        unique_tags = set(h.lower() for h in all_hashtags)
        variety_rate = len(unique_tags) / len(all_hashtags) if all_hashtags else 0
        
        if variety_rate >= 0.5:
            score += 3
        else:
            issues.append("Low hashtag variety - avoid repeating same tags")
        
        # Determine status
        score_pct = score / max_score
        if score_pct >= 0.7:
            status = 'pass'
        elif score_pct >= 0.4:
            status = 'warn'
        else:
            status = 'fail'
        
        return {
            'score': score,
            'max': max_score,
            'status': status,
            'issues': issues
        }
    
    def _analyze_engagement(self) -> Dict:
        """Analyze engagement metrics."""
        max_score = self.WEIGHTS['engagement']
        score = 0
        issues = []
        
        followers = self.profile.followers_count
        following = self.profile.following_count
        
        # Check follower/following ratio
        if followers > 0 and following > 0:
            ratio = followers / following
            
            if ratio >= 2:
                score += 6
            elif ratio >= 1:
                score += 4
            elif ratio >= 0.5:
                score += 2
            else:
                issues.append("Low follower/following ratio")
        
        # Check follower count (for reach potential)
        if followers >= 10000:
            score += 5
        elif followers >= 5000:
            score += 4
        elif followers >= 1000:
            score += 3
        elif followers >= 500:
            score += 2
        else:
            score += 1
            issues.append("Building follower base")
        
        # Check if not private
        if not self.profile.is_private:
            score += 4
        else:
            issues.append("Private account limits discovery")
            self.suggestions.append({
                'category': 'PROFILE',
                'priority': 'high',
                'text': 'Switch to public account',
                'example': 'Private accounts cannot be discovered by brands or appear in hashtag searches'
            })
        
        # Determine status
        score_pct = score / max_score
        if score_pct >= 0.7:
            status = 'pass'
        elif score_pct >= 0.4:
            status = 'warn'
        else:
            status = 'fail'
        
        return {
            'score': score,
            'max': max_score,
            'status': status,
            'issues': issues
        }
    
    def _analyze_completeness(self) -> Dict:
        """Analyze profile completeness."""
        max_score = self.WEIGHTS['completeness']
        score = 0
        issues = []
        
        # Profile picture
        if self.profile.has_profile_pic:
            score += 3
        else:
            issues.append("No profile picture")
        
        # Highlights
        if self.profile.has_highlights:
            score += 3
        else:
            issues.append("No story highlights")
        
        # External link
        if self.profile.has_external_link:
            score += 2
        else:
            issues.append("No external link")
        
        # Bio filled
        if len(self.profile.bio) > 20:
            score += 2
        else:
            issues.append("Bio incomplete")
        
        # Determine status
        score_pct = score / max_score
        if score_pct >= 0.7:
            status = 'pass'
        elif score_pct >= 0.4:
            status = 'warn'
        else:
            status = 'fail'
        
        return {
            'score': score,
            'max': max_score,
            'status': status,
            'issues': issues
        }
    
    def _get_niche_examples(self) -> str:
        """Get example keywords for detected or default niche."""
        niche = self.detected_niche or 'creator'
        keywords = self.NICHE_KEYWORDS.get(niche, self.NICHE_KEYWORDS['creator'])
        return ', '.join(keywords[:3])
    
    def _get_niche_title(self) -> str:
        """Get a title for the detected niche."""
        niche_titles = {
            'fitness': 'Fitness Creator',
            'lifestyle': 'Lifestyle Creator',
            'fashion': 'Fashion Creator',
            'tech': 'Tech Creator',
            'food': 'Food Creator',
            'travel': 'Travel Creator',
            'beauty': 'Beauty Creator',
            'business': 'Business Creator',
            'creator': 'Content Creator'
        }
        return niche_titles.get(self.detected_niche or 'creator', 'Content Creator')


def analyze_profile(profile_data: Dict) -> Dict:
    """
    Convenience function to analyze a profile from dict data.
    """
    profile = ProfileData(
        username=profile_data.get('username', ''),
        name=profile_data.get('name', ''),
        bio=profile_data.get('bio', ''),
        posts_count=profile_data.get('posts', 0),
        followers_count=profile_data.get('followers', 0),
        following_count=profile_data.get('following', 0),
        is_private=profile_data.get('is_private', False),
        has_profile_pic=profile_data.get('has_profile_pic', True),
        has_highlights=profile_data.get('has_highlights', False),
        has_external_link=profile_data.get('has_external_link', False),
        email_in_bio=profile_data.get('email', None),
        recent_captions=profile_data.get('captions', []),
        recent_hashtags=profile_data.get('hashtags', [])
    )
    
    analyzer = SEOAnalyzer()
    return analyzer.analyze(profile)
