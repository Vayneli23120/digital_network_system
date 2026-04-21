"""
Tests for rate_limiter middleware
"""

import pytest
from app.middleware.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_allows_requests_within_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            allowed, remaining = limiter.is_allowed("1.2.3.4", "/test")
            assert allowed is True
            assert remaining == 4 - i

    def test_blocks_requests_over_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("1.2.3.4", "/test")

        allowed, remaining = limiter.is_allowed("1.2.3.4", "/test")
        assert allowed is False
        assert remaining == 0

    def test_different_clients_independent(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        # Client A hits limit
        limiter.is_allowed("1.1.1.1", "/test")
        limiter.is_allowed("1.1.1.1", "/test")
        allowed_a, _ = limiter.is_allowed("1.1.1.1", "/test")
        assert allowed_a is False

        # Client B should still work
        allowed_b, _ = limiter.is_allowed("2.2.2.2", "/test")
        assert allowed_b is True

    def test_different_paths_same_limit(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("1.2.3.4", "/api/a")
        limiter.is_allowed("1.2.3.4", "/api/b")
        allowed, _ = limiter.is_allowed("1.2.3.4", "/api/c")
        assert allowed is False  # Same client, all paths share limit

    def test_get_status(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        limiter.is_allowed("1.2.3.4", "/test")
        limiter.is_allowed("1.2.3.4", "/test2")

        status = limiter.get_status("1.2.3.4")
        assert status["client_ip"] == "1.2.3.4"
        assert status["requests_in_window"] == 2
        assert status["max_requests"] == 10
        assert status["remaining"] == 8

    def test_get_status_empty(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        status = limiter.get_status("new.client")
        assert status["requests_in_window"] == 0
        assert status["remaining"] == 10

    def test_default_limiter_exists(self):
        from app.middleware.rate_limiter import default_limiter, get_rate_limiter
        assert default_limiter is not None
        assert get_rate_limiter() is default_limiter
