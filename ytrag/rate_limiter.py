# ytrag/rate_limiter.py
"""Adaptive rate limiter for YouTube API requests."""

import time


class AdaptiveRateLimiter:
    """
    Rate limiter that adapts to YouTube's rate limiting.

    Behavior:
    - Starts with base_sleep between requests
    - On 429 error: doubles sleep, maintains for backoff_count requests
    - On success after backoff: gradually decreases back to base
    """

    def __init__(
        self,
        base_sleep: float = 2.0,
        max_sleep: float = 30.0,
        backoff_count: int = 3,
        decay_rate: float = 0.5,
    ):
        self.base_sleep = base_sleep
        self.max_sleep = max_sleep
        self.backoff_count = backoff_count
        self.decay_rate = decay_rate

        self.current_sleep = base_sleep
        self.backoff_requests = 0

    def on_rate_limit(self) -> None:
        """Call when YouTube returns 429. Doubles sleep time."""
        self.current_sleep = min(self.current_sleep * 2, self.max_sleep)
        self.backoff_requests = self.backoff_count

    def on_success(self) -> None:
        """Call after successful request. Gradually decreases sleep."""
        if self.backoff_requests > 0:
            self.backoff_requests -= 1
        else:
            self.current_sleep = max(
                self.base_sleep,
                self.current_sleep - self.decay_rate
            )

    def get_sleep_time(self) -> float:
        """Get current sleep time."""
        return self.current_sleep

    def wait(self) -> None:
        """Sleep for the current interval."""
        time.sleep(self.current_sleep)
