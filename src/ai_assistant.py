"""
IG Growth Hub - AI Suggestions using Groq API
Generates SEO-optimized content suggestions for Instagram profiles.
"""

from groq import Groq
from typing import Dict, List, Optional
import httpx
import time
import os

# Groq API configuration - uses environment variable
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
MAX_RETRIES = 3


# SEO Best Practices Context (from Creator Collab Process)
SEO_CONTEXT = """
Instagram SEO Best Practices:

BIO OPTIMIZATION:
- Include primary keyword/niche in first line
- Use searchable terms that describe what you do
- Include a clear call-to-action (CTA)
- Add relevant emojis to break up text
- Include location if relevant for local business
- Maximum 150 characters

NAME FIELD SEO:
- Use your name + primary keyword (e.g., "John | Food Photographer")
- This field is searchable, use it strategically
- Maximum 30 characters

CONTENT CONSISTENCY:
- Post at least 3-5 times per week
- Maintain consistent visual theme/aesthetic
- Use 3-5 relevant hashtags per post (not 30!)
- Mix content types: photos, reels, carousels

HASHTAG STRATEGY:
- Use a mix: 2 niche-specific, 2 medium (50K-500K posts), 1 broad
- Avoid banned or spammy hashtags
- Research competitors' hashtags
- Create a branded hashtag

ENGAGEMENT OPTIMIZATION:
- Reply to comments within first hour
- Use questions in captions to drive engagement
- Include save-worthy content (tutorials, tips, infographics)
- Post when your audience is most active
"""


class AIAssistant:
    """Generates AI-powered content suggestions using Groq."""
    
    def __init__(self):
        # Create httpx client with longer timeout and SSL workaround for Windows
        http_client = httpx.Client(timeout=60.0, verify=False)
        self.client = Groq(api_key=GROQ_API_KEY, http_client=http_client)
    
    def _call_with_retry(self, messages, temperature=0.8, max_tokens=1024):
        """Call Groq API with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[AI] Attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise e
        return None
    
    def generate_bio_suggestions(self, profile: Dict) -> List[Dict]:
        """
        Generate optimized bio suggestions based on current profile.
        
        Args:
            profile: Dict with username, bio, full_name, etc.
            
        Returns:
            List of suggestion dicts with 'original', 'suggested', 'reason'
        """
        current_bio = profile.get('bio', '') or 'No bio set'
        username = profile.get('username', '')
        full_name = profile.get('full_name', '')
        
        prompt = f"""
{SEO_CONTEXT}

Current Instagram Profile:
- Username: @{username}
- Name: {full_name}
- Current Bio: {current_bio}

Based on Instagram SEO best practices, generate 3 optimized bio suggestions that:
1. Include a clear CTA
2. Use searchable keywords
3. Have engaging emojis
4. Stay within 150 characters

Format each suggestion as:
BIO [number]:
[Your exact bio text here - ready to copy-paste]
WHY: [One sentence explaining the improvement]

Only output the bios, nothing else.
"""
        
        try:
            result = self._call_with_retry(
                messages=[
                    {"role": "system", "content": "You are an Instagram SEO expert. Give actionable, copy-paste ready suggestions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1024
            )
            
            if result:
                return self._parse_bio_suggestions(result, current_bio)
            return []
            
        except Exception as e:
            print(f"[AI] Error generating bio suggestions: {e}")
            # Return fallback suggestions when API is unavailable
            return self._get_fallback_bio_suggestions(current_bio, username)
    
    def _get_fallback_bio_suggestions(self, current_bio: str, username: str) -> List[Dict]:
        """Return pre-made suggestions when API is unavailable."""
        return [
            {
                'original': current_bio,
                'suggested': f"📸 Content Creator | Sharing what I love\n✨ DM for collabs\n📍 Link below 👇",
                'reason': "Clear niche, CTA, and emoji-enhanced for better visibility"
            },
            {
                'original': current_bio,
                'suggested': f"🎯 {username.replace('.', ' ').title()} | Creating daily\n💡 Tips & tricks in stories\n🔗 Shop my picks ↓",
                'reason': "Personal branding with searchable keywords"
            },
            {
                'original': current_bio,
                'suggested': "🌟 Living life one post at a time\n📩 Business: DM or email\n🔥 New content weekly!",
                'reason': "Lifestyle-focused with clear contact info"
            }
        ]
    
    def generate_caption_suggestions(self, profile: Dict, topic: str = None) -> List[Dict]:
        """Generate engaging caption templates."""
        username = profile.get('username', '')
        niche = self._guess_niche(profile)
        
        prompt = f"""
{SEO_CONTEXT}

Create 3 engaging Instagram caption templates for @{username} in the {niche} niche.
{f'Topic: {topic}' if topic else ''}

Each caption should:
1. Have a strong hook in first line
2. Include a call-to-action
3. Have 3-5 strategic hashtags
4. Be ready to copy-paste

Format:
CAPTION [number]:
[Full caption text with hashtags]
WHY: [Why this works]
"""
        
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a social media copywriter. Create viral, engaging content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_completion_tokens=1500
            )
            
            return self._parse_caption_suggestions(response.choices[0].message.content)
            
        except Exception as e:
            print(f"[AI] Error generating captions: {e}")
            return []
    
    def generate_hashtag_strategy(self, profile: Dict) -> Dict:
        """Generate personalized hashtag recommendations."""
        username = profile.get('username', '')
        bio = profile.get('bio', '')
        niche = self._guess_niche(profile)
        
        prompt = f"""
{SEO_CONTEXT}

Profile: @{username}
Bio: {bio}
Niche: {niche}

Create a hashtag strategy with:
1. 5 niche-specific hashtags (under 100K posts)
2. 5 medium hashtags (100K-500K posts)  
3. 3 broad hashtags (500K+ posts)
4. 1 branded hashtag suggestion

Format exactly as:
NICHE: #hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5
MEDIUM: #hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5
BROAD: #hashtag1 #hashtag2 #hashtag3
BRANDED: #YourBrandedHashtag

Ready to copy-paste, no explanations.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are an Instagram hashtag strategist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_completion_tokens=500
            )
            
            return self._parse_hashtag_strategy(response.choices[0].message.content)
            
        except Exception as e:
            print(f"[AI] Error generating hashtags: {e}")
            return {}
    
    def _guess_niche(self, profile: Dict) -> str:
        """Guess the profile's niche from bio and username."""
        bio = (profile.get('bio', '') or '').lower()
        username = (profile.get('username', '') or '').lower()
        
        niches = {
            'food': ['food', 'cook', 'recipe', 'chef', 'eat', 'yum', 'foodie'],
            'fitness': ['fit', 'gym', 'workout', 'health', 'muscle', 'train'],
            'travel': ['travel', 'explore', 'adventure', 'wander', 'nomad'],
            'fashion': ['fashion', 'style', 'outfit', 'wear', 'dress', 'model'],
            'photography': ['photo', 'camera', 'shoot', 'lens', 'portrait'],
            'tech': ['tech', 'code', 'dev', 'app', 'software', 'digital'],
            'beauty': ['beauty', 'makeup', 'skin', 'glow', 'cosmetic'],
            'music': ['music', 'song', 'artist', 'band', 'producer', 'dj'],
            'lifestyle': ['life', 'daily', 'vlog', 'content', 'creator']
        }
        
        combined = f"{bio} {username}"
        for niche, keywords in niches.items():
            if any(kw in combined for kw in keywords):
                return niche
        
        return 'lifestyle'
    
    def _parse_bio_suggestions(self, text: str, original: str) -> List[Dict]:
        """Parse bio suggestions from AI response."""
        suggestions = []
        lines = text.strip().split('\n')
        
        current_bio = None
        current_reason = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('BIO'):
                if current_bio and current_reason:
                    suggestions.append({
                        'original': original,
                        'suggested': current_bio,
                        'reason': current_reason
                    })
                current_bio = None
                current_reason = None
            elif line.startswith('WHY:'):
                current_reason = line[4:].strip()
            elif line and not line.startswith('BIO'):
                if current_bio is None:
                    current_bio = line
                elif current_reason is None:
                    current_bio += ' ' + line
        
        # Don't forget the last one
        if current_bio and current_reason:
            suggestions.append({
                'original': original,
                'suggested': current_bio,
                'reason': current_reason
            })
        
        return suggestions[:3]  # Max 3
    
    def _parse_caption_suggestions(self, text: str) -> List[Dict]:
        """Parse caption suggestions from AI response."""
        suggestions = []
        parts = text.split('CAPTION')
        
        for part in parts[1:]:  # Skip first empty part
            lines = part.strip().split('\n')
            caption_lines = []
            reason = ''
            
            for line in lines:
                if line.startswith('WHY:'):
                    reason = line[4:].strip()
                elif line.strip() and not line.startswith('['):
                    caption_lines.append(line.strip())
            
            if caption_lines:
                suggestions.append({
                    'caption': '\n'.join(caption_lines),
                    'reason': reason
                })
        
        return suggestions[:3]
    
    def _parse_hashtag_strategy(self, text: str) -> Dict:
        """Parse hashtag strategy from AI response."""
        result = {
            'niche': [],
            'medium': [],
            'broad': [],
            'branded': ''
        }
        
        for line in text.strip().split('\n'):
            line = line.strip()
            if line.startswith('NICHE:'):
                result['niche'] = line[6:].strip().split()
            elif line.startswith('MEDIUM:'):
                result['medium'] = line[7:].strip().split()
            elif line.startswith('BROAD:'):
                result['broad'] = line[6:].strip().split()
            elif line.startswith('BRANDED:'):
                result['branded'] = line[8:].strip()
        
        return result


# Singleton instance
_ai_assistant = None

def get_ai_assistant() -> AIAssistant:
    global _ai_assistant
    if _ai_assistant is None:
        _ai_assistant = AIAssistant()
    return _ai_assistant
