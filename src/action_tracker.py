"""
IG Growth Hub - Action Tracker
Tracks all boost actions with detailed reporting
"""

import uuid
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from threading import Lock


@dataclass
class ActionLog:
    """Single action log entry."""
    timestamp: str
    action_type: str  # like, follow, comment, view
    target_type: str  # post, reel, story, profile
    target_url: str
    target_username: str
    content: str  # comment text if applicable
    status: str  # success, failed, skipped
    reason: Optional[str] = None  # Reason for skip/failure


class ActionTracker:
    """
    Tracks all boost session actions with progress and detailed reports.
    Thread-safe for use with Flask.
    """
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / 'data' / 'tasks'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, dict] = {}
        self._lock = Lock()
    
    def create_task(
        self,
        username: str,
        action_types: List[str],
        platform: str,
        intensity: int,
        target_count: int
    ) -> str:
        """
        Create a new boost task and return task ID.
        
        Args:
            username: Instagram username
            action_types: List of actions ['likes', 'follows', 'comments', 'views']
            platform: 'instagram', 'threads', or 'both'
            intensity: 1-3 (conservative to aggressive)
            target_count: Total actions to perform
            
        Returns:
            task_id: Unique task identifier
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        task = {
            'task_id': task_id,
            'username': username,
            'platform': platform,
            'action_types': action_types,
            'intensity': intensity,
            'target_count': target_count,
            'completed_count': 0,
            'status': 'running',  # running, paused, completed, failed
            'status_message': 'Initializing boost...',  # Live status for frontend
            'extraction_phase': True,  # True during collection, False during actions
            'extraction_progress': 0,  # 0-100 percentage during extraction
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'actions': []
        }
        
        with self._lock:
            self.tasks[task_id] = task
            self._save_task(task_id)
        
        print(f"[Tracker] Created task {task_id} for {username}")
        return task_id
    
    def update_status_message(self, task_id: str, message: str):
        """Update the live status message for a task."""
        if task_id in self.tasks:
            with self._lock:
                self.tasks[task_id]['status_message'] = message
                self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
                self._save_task(task_id)
    
    def update_extraction_progress(self, task_id: str, progress: int, phase: bool = True):
        """Update the extraction progress (0-100) and phase flag."""
        if task_id in self.tasks:
            with self._lock:
                self.tasks[task_id]['extraction_progress'] = min(100, max(0, progress))
                self.tasks[task_id]['extraction_phase'] = phase
                self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
                self._save_task(task_id)
    
    def log_action(
        self,
        task_id: str,
        action_type: str,
        target_type: str,
        target_url: str,
        target_username: str,
        content: str = '',
        status: str = 'success',
        reason: str = None
    ) -> bool:
        """
        Log a single action to the task.
        
        Returns:
            bool: True if logged successfully
        """
        if task_id not in self.tasks:
            print(f"[Tracker] Task {task_id} not found")
            return False
        
        action = ActionLog(
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            target_type=target_type,
            target_url=target_url,
            target_username=target_username,
            content=content,
            status=status,
            reason=reason
        )
        
        with self._lock:
            task = self.tasks[task_id]
            task['actions'].append(asdict(action))
            if status == 'success':
                task['completed_count'] += 1
            task['updated_at'] = datetime.now().isoformat()
            self._save_task(task_id)
        
        print(f"[Tracker] Logged {action_type} on {target_type} -> @{target_username} ({status})")
        return True

    def log_skip(
        self,
        task_id: str,
        action_type: str,
        target_url: str,
        target_username: str,
        reason: str
    ) -> bool:
        """Helper to log a skipped action."""
        return self.log_action(
            task_id=task_id,
            action_type=action_type,
            target_type='post',  # Generic default
            target_url=target_url,
            target_username=target_username,
            status='skipped',
            reason=reason
        )
    
    def get_analytics(self, username: str) -> Dict:
        """
        Aggregate analytics data for a specific user from all past tasks.
        
        Returns:
            Dict containing activity stats, growth predictions, and impact metrics.
        """
        # Load all reports for this user
        reports_dir = Path(__file__).parent.parent / 'data' / 'reports'
        user_reports = []
        
        if reports_dir.exists():
            for report_file in reports_dir.glob('boost_report_*.json'):
                try:
                    with open(report_file, 'r') as f:
                        data = json.load(f)
                        if data.get('username') == username:
                            user_reports.append(data)
                except:
                    continue
        
        # Add current running tasks
        for task in self.tasks.values():
            if task.get('username') == username:
                user_reports.append(task)
        
        # Aggregate Data
        total_actions = 0
        total_success = 0
        total_skipped = 0
        
        actions_by_date = {}
        skips_by_reason = {}
        
        for report in user_reports:
            for action in report.get('actions', []):
                # Basic Stats
                total_actions += 1
                if action.get('status') == 'success':
                    total_success += 1
                elif action.get('status') == 'skipped':
                    total_skipped += 1
                    reason = action.get('reason', 'Unknown')
                    skips_by_reason[reason] = skips_by_reason.get(reason, 0) + 1
                
                # Date Aggregation
                ts = action.get('timestamp')
                if ts:
                    date_str = ts.split('T')[0]
                    if date_str not in actions_by_date:
                        actions_by_date[date_str] = {'success': 0, 'skipped': 0, 'failed': 0}
                    
                    status = action.get('status', 'failed')
                    if status in actions_by_date[date_str]:
                        actions_by_date[date_str][status] += 1
        
        # Sort dates
        sorted_dates = sorted(actions_by_date.keys())
        activity_chart = {
            'labels': sorted_dates[-7:], # Last 7 active days
            'success': [actions_by_date[d]['success'] for d in sorted_dates[-7:]],
            'skipped': [actions_by_date[d]['skipped'] for d in sorted_dates[-7:]]
        }
        
        # Predictions (Improved calculation)
        # - Daily average actions
        # - Success rate
        # - Estimated follow-back rate: ~3-5% for likes, higher for follows
        # - Projection based on recent activity (last 3 days)
        
        days_active = len(sorted_dates) if sorted_dates else 1
        daily_avg_success = round(total_success / max(days_active, 1), 1)
        success_rate = round((total_success / max(total_actions, 1)) * 100, 1)
        
        # Calculate last 3 days average for more recent projection
        recent_3_days = sorted_dates[-3:] if len(sorted_dates) >= 3 else sorted_dates
        recent_success = sum(actions_by_date[d]['success'] for d in recent_3_days)
        recent_daily_avg = round(recent_success / max(len(recent_3_days), 1), 1)
        
        # Follow-back rate assumptions:
        # - Likes to accounts < 10k followers: ~3-5% follow back
        # - We use 3% as a conservative estimate
        follow_back_rate = 0.03
        est_followers_gained = int(total_success * follow_back_rate)
        weekly_projection = int(recent_daily_avg * 7 * follow_back_rate)
        
        # Generate insight text
        if total_success == 0:
            future_scope = "Start boosting to see predictions."
            insight = "No activity yet"
        elif days_active == 1:
            future_scope = f"You performed {total_success} successful interactions today. Keep going!"
            insight = f"First day! {success_rate}% success rate"
        else:
            future_scope = f"At ~{recent_daily_avg} likes/day, you could gain ~{weekly_projection} followers this week."
            insight = f"Avg. {daily_avg_success}/day over {days_active} days"
        
        # Generate dynamic growth tips based on data
        growth_tips = []
        
        if total_actions == 0:
            growth_tips = [
                {"icon": "🚀", "tip": "Start your first boost to begin growing!", "type": "action"},
                {"icon": "🎯", "tip": "Target 3-5 hashtags relevant to your niche", "type": "strategy"},
                {"icon": "⏰", "tip": "Best time to boost: 9-11 AM and 7-9 PM", "type": "timing"}
            ]
        else:
            # Success rate tips
            if success_rate >= 80:
                growth_tips.append({"icon": "🏆", "tip": f"Excellent {success_rate}% success rate! You're targeting the right audience.", "type": "praise"})
            elif success_rate >= 50:
                growth_tips.append({"icon": "📈", "tip": f"{success_rate}% success rate. Try targeting smaller accounts (< 5k followers) for better engagement.", "type": "improve"})
            else:
                growth_tips.append({"icon": "💡", "tip": "Focus on niche-specific hashtags with 10k-100k posts for better targeting.", "type": "improve"})
            
            # Consistency tips
            if days_active >= 7:
                growth_tips.append({"icon": "🔥", "tip": f"{days_active} days streak! Consistency is key to algorithm favor.", "type": "praise"})
            elif days_active >= 3:
                growth_tips.append({"icon": "📅", "tip": f"Nice {days_active}-day streak! Keep boosting daily for best results.", "type": "encourage"})
            else:
                growth_tips.append({"icon": "⚡", "tip": "Boost daily for 7+ days to see significant follower growth.", "type": "action"})
            
            # Volume tips
            if daily_avg_success >= 20:
                growth_tips.append({"icon": "🎉", "tip": f"Great volume! {daily_avg_success} likes/day puts you on track for ~{weekly_projection * 4} monthly followers.", "type": "praise"})
            elif daily_avg_success >= 10:
                growth_tips.append({"icon": "📊", "tip": f"Good pace at {daily_avg_success}/day. Increase intensity for faster growth.", "type": "encourage"})
            else:
                growth_tips.append({"icon": "🚀", "tip": "Increase to 15-20 likes/day for optimal growth without triggering limits.", "type": "action"})
            
            # Engagement quality tip
            if est_followers_gained > 0:
                growth_tips.append({"icon": "👥", "tip": f"Estimated {est_followers_gained} new followers from your engagement. Quality > quantity!", "type": "insight"})
        
        return {
            'total_actions': total_actions,
            'total_success': total_success,
            'total_skipped': total_skipped,
            'skips_by_reason': skips_by_reason,
            'activity_chart': activity_chart,
            'growth_tips': growth_tips,
            'predictions': {
                'est_followers_gained': est_followers_gained,
                'weekly_projection': weekly_projection,
                'conversion_rate': f"{follow_back_rate * 100}%",
                'success_rate': f"{success_rate}%",
                'daily_avg_success': daily_avg_success,
                'days_active': days_active,
                'future_scope': future_scope,
                'insight': insight
            }
        }
    
    def get_progress(self, task_id: str) -> Optional[Dict]:
        """
        Get real-time progress of a task.
        
        Returns:
            Dict with completed, total, percentage, status, recent_actions, and limits
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        completed = task['completed_count']
        total = task['target_count']
        percentage = round((completed / total) * 100, 1) if total > 0 else 0
        
        # Get last 5 actions for live feed
        recent_actions = task['actions'][-5:] if task['actions'] else []
        
        # Add rate limit status
        from .rate_limiter import get_rate_limiter
        rl = get_rate_limiter()
        limits_status = rl.get_status(task['platform'])
        
        return {
            'task_id': task_id,
            'status': task['status'],
            'status_message': task.get('status_message', ''),
            'completed': completed,
            'total': total,
            'percentage': percentage,
            'recent_actions': recent_actions,
            'action_types': task['action_types'],
            'platform': task['platform'],
            'limits': limits_status.get(task['platform'], {})
        }
    
    def get_report(self, task_id: str) -> Optional[Dict]:
        """
        Get detailed report of all actions in a task.
        
        Returns:
            Full task data including all actions
        """
        if task_id not in self.tasks:
            # Try to load from file
            task = self._load_task(task_id)
            if task:
                return task
            return None
        
        return self.tasks[task_id]
    
    def complete_task(self, task_id: str, status: str = 'completed'):
        """Mark a task as completed."""
        if task_id in self.tasks:
            with self._lock:
                self.tasks[task_id]['status'] = status
                self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
                self._save_task(task_id)
            print(f"[Tracker] Task {task_id} marked as {status}")
    
    def pause_task(self, task_id: str):
        """Pause a running task."""
        self.complete_task(task_id, 'paused')
    
    def _save_task(self, task_id: str):
        """Save task to JSON file for persistence."""
        if task_id in self.tasks:
            file_path = self.data_dir / f"{task_id}.json"
            with open(file_path, 'w') as f:
                json.dump(self.tasks[task_id], f, indent=2)
    
    def save_report(self, task_id: str) -> Optional[str]:
        """
        Save a completed boost report to the reports folder.
        
        Returns:
            Path to the saved report file, or None if saving failed
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        # Create reports directory
        reports_dir = Path(__file__).parent.parent / 'data' / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename: boost_report_uuid_timestamp.json
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"boost_report_{task_id}_{timestamp}.json"
        filepath = reports_dir / filename
        
        # Prepare report data
        report = {
            'task_id': task_id,
            'username': task.get('username'),
            'platform': task.get('platform'),
            'status': task.get('status'),
            'action_types': task.get('action_types'),
            'intensity': task.get('intensity'),
            'created_at': task.get('created_at'),
            'completed_at': datetime.now().isoformat(),
            'total_actions': task.get('completed_count', 0),
            'target_count': task.get('target_count', 0),
            'actions': task.get('actions', []),
            'summary': self._generate_summary(task)
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"[Tracker] Report saved to: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"[Tracker] Failed to save report: {e}")
            return None
    
    def _generate_summary(self, task: Dict) -> Dict:
        """Generate summary statistics for a task."""
        actions = task.get('actions', [])
        successful = len([a for a in actions if a.get('status') == 'success'])
        
        # Count by type
        by_type = {}
        for action in actions:
            action_type = action.get('action_type', 'unknown')
            by_type[action_type] = by_type.get(action_type, 0) + 1
        
        # Calculate duration
        duration_seconds = 0
        if task.get('created_at') and task.get('updated_at'):
            try:
                start = datetime.fromisoformat(task['created_at'])
                end = datetime.fromisoformat(task['updated_at'])
                duration_seconds = (end - start).total_seconds()
            except:
                pass
        
        return {
            'total_actions': len(actions),
            'successful': successful,
            'by_type': by_type,
            'duration_seconds': duration_seconds
        }
    
    def _load_task(self, task_id: str) -> Optional[Dict]:
        """Load task from JSON file."""
        file_path = self.data_dir / f"{task_id}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def get_summary_stats(self, task_id: str) -> Dict:
        """Get summary statistics for a task."""
        task = self.get_report(task_id)
        if not task:
            return {}
        
        # Count by action type
        action_counts = {}
        for action in task.get('actions', []):
            atype = action['action_type']
            action_counts[atype] = action_counts.get(atype, 0) + 1
        
        # Count successful vs failed
        success_count = sum(1 for a in task.get('actions', []) if a['status'] == 'success')
        failed_count = sum(1 for a in task.get('actions', []) if a['status'] == 'failed')
        
        return {
            'total_actions': len(task.get('actions', [])),
            'successful': success_count,
            'failed': failed_count,
            'by_type': action_counts,
            'duration_seconds': self._calculate_duration(task)
        }
    
    def _calculate_duration(self, task: Dict) -> int:
        """Calculate task duration in seconds."""
        try:
            created = datetime.fromisoformat(task['created_at'])
            updated = datetime.fromisoformat(task['updated_at'])
            return int((updated - created).total_seconds())
        except:
            return 0


# Global tracker instance
_tracker_instance = None

def get_tracker() -> ActionTracker:
    """Get the global ActionTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ActionTracker()
    return _tracker_instance
