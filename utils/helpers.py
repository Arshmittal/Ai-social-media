import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

def generate_content_id() -> str:
    """Generate unique content ID"""
    return f"content_{uuid.uuid4().hex[:8]}"

def generate_project_id() -> str:
    """Generate unique project ID"""
    return f"project_{uuid.uuid4().hex[:8]}"

def sanitize_content(content: str, platform: str) -> str:
    """Sanitize content for specific platform"""
    platform_configs = {
        'twitter': {'max_length': 280},
        'linkedin': {'max_length': 3000},
        'facebook': {'max_length': 2000},
        'instagram': {'max_length': 2200}
    }
    
    config = platform_configs.get(platform, {'max_length': 280})
    
    # Truncate if too long
    if len(content) > config['max_length']:
        content = content[:config['max_length'] - 3] + "..."
    
    return content

def extract_hashtags(content: str) -> List[str]:
    """Extract hashtags from content"""
    hashtag_pattern = r'#\w+'
    hashtags = re.findall(hashtag_pattern, content)
    return [tag.lower() for tag in hashtags]

def validate_schedule_time(schedule_time: str) -> bool:
    """Validate schedule time format"""
    try:
        datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def calculate_optimal_posting_time(platform: str, timezone: str = 'UTC') -> str:
    """Calculate optimal posting time for platform"""
    from config.settings import Config
    
    optimal_times = Config.PLATFORM_CONFIGS.get(platform, {}).get('optimal_posting_times', ['12:00'])
    
    # Simple logic to pick next available optimal time
    now = datetime.utcnow()
    
    for time_str in optimal_times:
        hour, minute = map(int, time_str.split(':'))
        optimal_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if optimal_time > now:
            return optimal_time.isoformat()
    
    # If no time today, schedule for tomorrow's first optimal time
    tomorrow = now + timedelta(days=1)
    hour, minute = map(int, optimal_times[0].split(':'))
    optimal_time = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    return optimal_time.isoformat()

def hash_content(content: str) -> str:
    """Generate hash for content deduplication"""
    return hashlib.md5(content.encode()).hexdigest()

def format_analytics_data(data: Dict) -> Dict:
    """Format analytics data for display"""
    formatted = {
        'engagement_rate': round(data.get('engagement_rate', 0), 2),
        'total_engagement': data.get('total_engagement', 0),
        'impressions': data.get('impressions', 0),
        'clicks': data.get('clicks', 0),
        'shares': data.get('shares', 0),
        'comments': data.get('comments', 0),
        'likes': data.get('likes', 0)
    }
    
    return formatted

def validate_platform_content(content: str, platform: str) -> Dict:
    """Validate content for platform requirements"""
    from config.settings import Config
    
    config = Config.PLATFORM_CONFIGS.get(platform, {})
    errors = []
    warnings = []
    
    # Length check
    if len(content) > config.get('max_length', 280):
        errors.append(f"Content exceeds {config['max_length']} character limit")
    
    # Hashtag check
    hashtags = extract_hashtags(content)
    max_hashtags = config.get('max_hashtags', 3)
    if len(hashtags) > max_hashtags:
        warnings.append(f"Too many hashtags ({len(hashtags)}), recommended: {max_hashtags}")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }