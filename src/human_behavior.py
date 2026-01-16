"""
IG Growth Hub - Human Behavior Simulation
Implements human-like patterns to avoid detection
"""

import random
import time
import math


def gaussian_delay(mean: float = 3.0, std: float = 1.0, min_val: float = 1.0, max_val: float = 8.0) -> float:
    """
    Generate a random delay using Gaussian distribution.
    More human-like than fixed delays.
    """
    delay = random.gauss(mean, std)
    return max(min_val, min(delay, max_val))


def random_delay(min_seconds: float = 1.0, max_seconds: float = 5.0) -> float:
    """Generate a random delay within a range."""
    return random.uniform(min_seconds, max_seconds)


def action_cooldown(action_type: str, intensity: int = 1) -> float:
    """
    Get cooldown time based on action type and intensity.
    Lower intensity = longer cooldowns (safer)
    """
    base_cooldowns = {
        'like': (45, 90),
        'follow': (60, 120),
        'comment': (90, 180),
        'profile_visit': (20, 40),
        'scroll': (1, 3)
    }
    
    min_cd, max_cd = base_cooldowns.get(action_type, (30, 60))
    
    # Adjust based on intensity (1=conservative, 2=moderate, 3=aggressive)
    intensity_multiplier = {1: 1.5, 2: 1.0, 3: 0.7}
    multiplier = intensity_multiplier.get(intensity, 1.0)
    
    delay = random.uniform(min_cd * multiplier, max_cd * multiplier)
    return delay


def simulate_reading_time(text_length: int) -> float:
    """
    Simulate human reading time based on text length.
    Average reading speed: ~200-250 wpm, ~5 chars per word
    """
    words = text_length / 5
    reading_speed = random.uniform(180, 280)  # words per minute
    base_time = (words / reading_speed) * 60  # seconds
    
    # Add some randomness
    return base_time + gaussian_delay(1.0, 0.5, 0.5, 3.0)


def generate_scroll_pattern() -> list:
    """
    Generate a human-like scroll pattern.
    Returns list of (scroll_amount, pause_time) tuples.
    """
    patterns = []
    total_scroll = random.randint(3, 8)
    
    for i in range(total_scroll):
        # Scroll amount varies (not uniform)
        scroll_amount = random.randint(200, 600)
        
        # Occasionally pause longer (simulating reading)
        if random.random() < 0.3:
            pause = gaussian_delay(2.0, 0.8, 1.0, 5.0)
        else:
            pause = gaussian_delay(0.8, 0.3, 0.3, 2.0)
        
        patterns.append((scroll_amount, pause))
    
    return patterns


def simulate_mouse_movement(start_x: int, start_y: int, end_x: int, end_y: int) -> list:
    """
    Generate human-like mouse movement path.
    Uses Bezier curve for natural movement.
    """
    points = []
    
    # Control points for Bezier curve
    cp1_x = start_x + random.randint(-50, 50) + (end_x - start_x) * 0.3
    cp1_y = start_y + random.randint(-50, 50) + (end_y - start_y) * 0.3
    cp2_x = start_x + random.randint(-50, 50) + (end_x - start_x) * 0.7
    cp2_y = start_y + random.randint(-50, 50) + (end_y - start_y) * 0.7
    
    # Generate points along the curve
    steps = random.randint(20, 40)
    for i in range(steps + 1):
        t = i / steps
        
        # Cubic Bezier formula
        x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
        y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
        
        points.append((int(x), int(y)))
    
    return points


def should_take_break(actions_count: int, session_minutes: int) -> bool:
    """
    Determine if the bot should take a break.
    Humans don't engage continuously for hours.
    """
    # Take break after certain number of actions
    if actions_count > 0 and actions_count % random.randint(15, 25) == 0:
        return True
    
    # Take break after certain time
    if session_minutes > 0 and session_minutes % random.randint(20, 35) == 0:
        return True
    
    # Random break (5% chance)
    if random.random() < 0.05:
        return True
    
    return False


def get_break_duration() -> float:
    """Get duration of break in seconds."""
    # Short break (1-3 min) or long break (5-10 min)
    if random.random() < 0.7:
        return random.uniform(60, 180)
    else:
        return random.uniform(300, 600)


def randomize_session_length() -> int:
    """
    Get a human-like session length in minutes.
    Most sessions are 15-45 minutes.
    """
    return random.randint(15, 45)


def add_typo_simulation(text: str, error_rate: float = 0.02) -> list:
    """
    Simulate typing with occasional typos and corrections.
    Returns list of actions (type char, backspace, etc.)
    """
    actions = []
    
    for char in text:
        # Occasionally make a typo
        if random.random() < error_rate:
            # Type wrong character
            wrong_char = chr(ord(char) + random.choice([-1, 1]))
            actions.append(('type', wrong_char))
            actions.append(('delay', gaussian_delay(0.3, 0.1, 0.1, 0.5)))
            actions.append(('backspace', 1))
            actions.append(('delay', gaussian_delay(0.2, 0.1, 0.1, 0.3)))
        
        actions.append(('type', char))
        actions.append(('delay', gaussian_delay(0.08, 0.03, 0.03, 0.2)))
    
    return actions


class HumanBehavior:
    """Main class for human behavior simulation."""
    
    def __init__(self, intensity: int = 1):
        self.intensity = intensity
        self.actions_count = 0
        self.session_start = time.time()
    
    def wait(self, action_type: str = 'default'):
        """Wait with human-like delay."""
        delay = action_cooldown(action_type, self.intensity)
        time.sleep(delay)
    
    def short_wait(self):
        """Short random wait."""
        time.sleep(gaussian_delay(1.0, 0.5, 0.5, 2.0))
    
    def record_action(self):
        """Record an action was taken."""
        self.actions_count += 1
    
    def check_break_needed(self) -> bool:
        """Check if break is needed."""
        session_minutes = int((time.time() - self.session_start) / 60)
        return should_take_break(self.actions_count, session_minutes)
    
    def take_break(self):
        """Take a break."""
        duration = get_break_duration()
        time.sleep(duration)
    
    def get_scroll_pattern(self) -> list:
        """Get scroll pattern."""
        return generate_scroll_pattern()
    
    def get_session_length(self) -> int:
        """Get recommended session length in minutes."""
        return randomize_session_length()
