"""
Rate Limiter for NeetResearch App.

Provides adaptive rate limiting to prevent 429 errors
when using multiple API keys on the free tier.
"""

import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class RateLimitState:
    """Tracks rate limit state for a single key."""
    request_times: List[float] = field(default_factory=list)
    backoff_until: float = 0
    total_requests: int = 0
    rate_limit_hits: int = 0


class AdaptiveRateLimiter:
    """
    Handles rate limits with automatic backoff and tracking.
    
    Features:
    - Per-key request tracking
    - Automatic wait when approaching limits
    - Backoff after rate limit errors
    - Statistics for monitoring
    """
    
    def __init__(self, requests_per_minute: int = 5):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per key (default: 5 for free tier)
        """
        self.rpm = requests_per_minute
        self.states: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._lock = asyncio.Lock()
    
    async def acquire(self, key: str) -> None:
        """
        Wait if necessary to stay within rate limits.
        
        Call this before making an API request with a specific key.
        
        Args:
            key: The API key being used (or key identifier)
        """
        async with self._lock:
            state = self.states[key]
            now = time.time()
            
            # Check if we're in backoff period
            if now < state.backoff_until:
                wait_time = state.backoff_until - now
                print(f"⏳ Key in backoff, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                now = time.time()
            
            # Clean old request times (older than 1 minute)
            state.request_times = [
                t for t in state.request_times 
                if now - t < 60
            ]
            
            # Check if at rate limit
            if len(state.request_times) >= self.rpm:
                oldest = state.request_times[0]
                wait_time = 60 - (now - oldest) + 1  # +1 for safety margin
                print(f"⏳ Rate limit reached ({self.rpm} RPM), waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                now = time.time()
                # Clean again after waiting
                state.request_times = [
                    t for t in state.request_times 
                    if now - t < 60
                ]
            
            # Record this request
            state.request_times.append(now)
            state.total_requests += 1
    
    def report_rate_limit(self, key: str, retry_after: int = 60) -> None:
        """
        Report that a rate limit error (429) was received.
        
        Call this when you get a rate limit error from the API.
        
        Args:
            key: The API key that hit the rate limit
            retry_after: Seconds to wait before using this key again
        """
        state = self.states[key]
        state.backoff_until = time.time() + retry_after
        state.rate_limit_hits += 1
        print(f"🚫 Rate limit hit for key, backing off for {retry_after}s")
    
    def get_stats(self, key: str = None) -> Dict:
        """
        Get rate limiting statistics.
        
        Args:
            key: Specific key to get stats for, or None for all keys
        
        Returns:
            Statistics dictionary
        """
        if key:
            state = self.states[key]
            return {
                "total_requests": state.total_requests,
                "rate_limit_hits": state.rate_limit_hits,
                "requests_last_minute": len([
                    t for t in state.request_times 
                    if time.time() - t < 60
                ]),
                "in_backoff": time.time() < state.backoff_until,
            }
        else:
            return {
                k[:8] + "...": self.get_stats(k) 
                for k in self.states.keys()
            }
    
    def reset(self, key: str = None) -> None:
        """
        Reset rate limit tracking.
        
        Args:
            key: Specific key to reset, or None for all keys
        """
        if key:
            self.states[key] = RateLimitState()
        else:
            self.states.clear()


# Global rate limiter instance
_rate_limiter: Optional[AdaptiveRateLimiter] = None


def get_rate_limiter() -> AdaptiveRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AdaptiveRateLimiter(requests_per_minute=5)
    return _rate_limiter


async def acquire_rate_limit(key: str) -> None:
    """Convenience function to acquire rate limit slot."""
    limiter = get_rate_limiter()
    await limiter.acquire(key)


def report_rate_limit_error(key: str, retry_after: int = 60) -> None:
    """Convenience function to report rate limit error."""
    limiter = get_rate_limiter()
    limiter.report_rate_limit(key, retry_after)
