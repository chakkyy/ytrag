# tests/test_rate_limiter.py
"""Tests for adaptive rate limiter."""

import pytest
import time
from ytrag.rate_limiter import AdaptiveRateLimiter


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""

    def test_initial_sleep_is_base_value(self):
        """Should start with base sleep time."""
        limiter = AdaptiveRateLimiter(base_sleep=2.0)
        assert limiter.current_sleep == 2.0

    def test_on_rate_limit_doubles_sleep(self):
        """Should double sleep time on rate limit."""
        limiter = AdaptiveRateLimiter(base_sleep=2.0)
        limiter.on_rate_limit()
        assert limiter.current_sleep == 4.0

    def test_on_rate_limit_respects_max(self):
        """Should not exceed max sleep time."""
        limiter = AdaptiveRateLimiter(base_sleep=2.0, max_sleep=10.0)
        for _ in range(10):
            limiter.on_rate_limit()
        assert limiter.current_sleep == 10.0

    def test_on_success_decreases_after_backoff(self):
        """Should decrease sleep after backoff period ends."""
        limiter = AdaptiveRateLimiter(base_sleep=2.0, backoff_count=2)
        limiter.on_rate_limit()  # Sleep = 4, backoff_requests = 2

        limiter.on_success()  # backoff_requests = 1, sleep stays
        assert limiter.current_sleep == 4.0

        limiter.on_success()  # backoff_requests = 0, sleep stays
        assert limiter.current_sleep == 4.0

        limiter.on_success()  # Now decreases
        assert limiter.current_sleep < 4.0

    def test_on_success_returns_to_base(self):
        """Should eventually return to base sleep."""
        limiter = AdaptiveRateLimiter(base_sleep=2.0, backoff_count=1)
        limiter.on_rate_limit()  # Sleep = 4
        limiter.on_success()     # backoff done

        # Multiple successes should return to base
        for _ in range(20):
            limiter.on_success()

        assert limiter.current_sleep == 2.0

    def test_get_sleep_time_returns_current(self):
        """Should return current sleep time."""
        limiter = AdaptiveRateLimiter(base_sleep=3.0)
        assert limiter.get_sleep_time() == 3.0
