import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from helpdesk_agent.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding-window rate limiter per user.
    
    Tracks timestamps of requests per user and enforces max_per_minute limit.
    
    Example:
        >>> rl = RateLimiter(max_per_minute=10)
        >>> for i in range(12):
        ...     allowed = rl.is_allowed("user123")
        ...     print(f"Request {i+1}: {'✅' if allowed else '❌'}")
        Request 1-10: ✅, Requests 11-12: ❌
    """
    
    def __init__(self, max_per_minute: int = 10):
        self.max_per_minute = max_per_minute
        self.calls: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """
        Check if user is allowed to make a request.
        
        Args:
            user_id: Unique identifier for the user (e.g., email, session ID)
        
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        window_start = now - 60  # Last 60 seconds
        
        # Clean up old timestamps (outside the 60-second window)
        self.calls[user_id] = [t for t in self.calls[user_id] if t > window_start]
        
        # Check if user exceeded limit
        if len(self.calls[user_id]) >= self.max_per_minute:
            # Calculate when they can retry
            oldest_in_window = min(self.calls[user_id]) if self.calls[user_id] else now
            retry_after = 60 - (now - oldest_in_window)
            logger.warning(
                f"Rate limit exceeded for user '{user_id}': {len(self.calls[user_id])}/{self.max_per_minute}. "
                f"Retry after {retry_after:.1f}s"
            )
            return False
        
        # Record this request
        self.calls[user_id].append(now)
        remaining = self.max_per_minute - len(self.calls[user_id])
        logger.debug(f"Rate limit for user '{user_id}': {remaining}/{self.max_per_minute} remaining")
        
        return True
    
    def get_remaining(self, user_id: str) -> int:
        """
        Get number of remaining requests allowed for the user in current window.
        """
        now = time.time()
        window_start = now - 60
        self.calls[user_id] = [t for t in self.calls[user_id] if t > window_start]
        
        return max(0, self.max_per_minute - len(self.calls[user_id]))
    
    def reset_user(self, user_id: str) -> None:
        """
        Reset rate limit for a specific user (useful for testing or admin override).
        """
        if user_id in self.calls:
            del self.calls[user_id]
            logger.info(f"Rate limit reset for user '{user_id}'")
    
    def get_stats(self, user_id: str) -> Dict[str, any]:
        """
        Get rate limit statistics for a user.
        """
        now = time.time()
        window_start = now - 60
        current_calls = [t for t in self.calls.get(user_id, []) if t > window_start]
        
        return {
            "requests_in_window": len(current_calls),
            "max_allowed": self.max_per_minute,
            "remaining": max(0, self.max_per_minute - len(current_calls)),
            "oldest_request": min(current_calls) if current_calls else None,
            "window_reset_in": 60 - (now - min(current_calls)) if current_calls else 0
        }


# Singleton instance
rate_limiter = RateLimiter(max_per_minute=settings.rate_limit_per_minute)