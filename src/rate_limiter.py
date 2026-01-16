"""
IG Growth Hub - Rate Limiter
Tracks and enforces action limits to prevent account flags
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import threading


class RateLimiter:
    """
    Rate limiter that tracks actions across sessions.
    Persists data to disk for continuity.
    """
    
    def __init__(self, data_file: str = None):
        if data_file is None:
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            data_file = data_dir / 'rate_limits.json'
        
        self.data_file = Path(data_file)
        self.lock = threading.Lock()
        self.limits = self._load_limits()
        self._cleanup_old_entries()
    
    def _default_limits(self) -> Dict:
        """Default rate limit configuration."""
        return {
            'instagram': {
                'likes': {'per_hour': 30, 'per_day': 300},
                'follows': {'per_hour': 20, 'per_day': 150},
                'comments': {'per_hour': 10, 'per_day': 80},
                'profile_visits': {'per_hour': 50, 'per_day': 400}
            },
            'threads': {
                'likes': {'per_hour': 40, 'per_day': 400},
                'replies': {'per_hour': 20, 'per_day': 150},
                'follows': {'per_hour': 30, 'per_day': 200}
            }
        }
    
    def _load_limits(self) -> Dict:
        """Load rate limit data from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Ensure structure exists
                    if 'config' not in data:
                        data['config'] = self._default_limits()
                    if 'actions' not in data:
                        data['actions'] = {}
                    return data
            except (json.JSONDecodeError, IOError):
                pass
        
        return {
            'config': self._default_limits(),
            'actions': {}
        }
    
    def _save_limits(self):
        """Save rate limit data to file."""
        with self.lock:
            with open(self.data_file, 'w') as f:
                json.dump(self.limits, f, indent=2)
    
    def _cleanup_old_entries(self):
        """Remove action entries older than 24 hours."""
        cutoff = (datetime.now() - timedelta(hours=24)).timestamp()
        
        for platform in self.limits.get('actions', {}):
            for action_type in self.limits['actions'].get(platform, {}):
                timestamps = self.limits['actions'][platform][action_type]
                self.limits['actions'][platform][action_type] = [
                    ts for ts in timestamps if ts > cutoff
                ]
        
        self._save_limits()
    
    def record_action(self, platform: str, action_type: str):
        """Record that an action was taken."""
        with self.lock:
            if platform not in self.limits['actions']:
                self.limits['actions'][platform] = {}
            if action_type not in self.limits['actions'][platform]:
                self.limits['actions'][platform][action_type] = []
            
            self.limits['actions'][platform][action_type].append(time.time())
        
        self._save_limits()
    
    def get_counts(self, platform: str, action_type: str) -> Dict[str, int]:
        """Get current action counts for the last hour and day."""
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400
        
        timestamps = self.limits.get('actions', {}).get(platform, {}).get(action_type, [])
        
        hourly_count = sum(1 for ts in timestamps if ts > hour_ago)
        daily_count = sum(1 for ts in timestamps if ts > day_ago)
        
        return {
            'hourly': hourly_count,
            'daily': daily_count
        }
    
    def get_limits(self, platform: str, action_type: str) -> Dict[str, int]:
        """Get configured limits for an action type."""
        return self.limits.get('config', {}).get(platform, {}).get(action_type, {
            'per_hour': 30,
            'per_day': 300
        })
    
    def can_perform_action(self, platform: str, action_type: str) -> bool:
        """Check if an action can be performed without exceeding limits."""
        counts = self.get_counts(platform, action_type)
        limits = self.get_limits(platform, action_type)
        
        return (
            counts['hourly'] < limits.get('per_hour', 30) and
            counts['daily'] < limits.get('per_day', 300)
        )
    
    def get_remaining(self, platform: str, action_type: str) -> Dict[str, int]:
        """Get remaining actions allowed."""
        counts = self.get_counts(platform, action_type)
        limits = self.get_limits(platform, action_type)
        
        return {
            'hourly': max(0, limits.get('per_hour', 30) - counts['hourly']),
            'daily': max(0, limits.get('per_day', 300) - counts['daily'])
        }
    
    def get_wait_time(self, platform: str, action_type: str) -> Optional[int]:
        """
        Get seconds to wait before next action is allowed.
        Returns None if action is allowed now.
        """
        if self.can_perform_action(platform, action_type):
            return None
        
        now = time.time()
        hour_ago = now - 3600
        
        timestamps = self.limits.get('actions', {}).get(platform, {}).get(action_type, [])
        hourly_timestamps = [ts for ts in timestamps if ts > hour_ago]
        
        if hourly_timestamps:
            oldest_in_hour = min(hourly_timestamps)
            wait_time = int(oldest_in_hour + 3600 - now)
            return max(0, wait_time)
        
        return 0
    
    def get_status(self, platform: str = None) -> Dict:
        """Get full status of all rate limits."""
        platforms = [platform] if platform else ['instagram', 'threads']
        status = {}
        
        for p in platforms:
            status[p] = {}
            action_types = self.limits.get('config', {}).get(p, {}).keys()
            
            for action_type in action_types:
                counts = self.get_counts(p, action_type)
                limits = self.get_limits(p, action_type)
                remaining = self.get_remaining(p, action_type)
                
                status[p][action_type] = {
                    'used': counts,
                    'limits': limits,
                    'remaining': remaining,
                    'can_perform': self.can_perform_action(p, action_type)
                }
        
        return status
    
    def reset_daily(self, platform: str = None, action_type: str = None):
        """Reset daily counts (for testing or manual reset)."""
        with self.lock:
            if platform and action_type:
                if platform in self.limits['actions']:
                    if action_type in self.limits['actions'][platform]:
                        self.limits['actions'][platform][action_type] = []
            elif platform:
                self.limits['actions'][platform] = {}
            else:
                self.limits['actions'] = {}
        
        self._save_limits()


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
