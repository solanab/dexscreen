"""
Test rate limiter functionality
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from dexscreen.utils.ratelimit import RateLimiter


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(max_calls=10, period=60)

        assert limiter.max_calls == 10
        assert limiter.period == 60
        assert len(limiter.calls) == 0

    def test_rate_limiter_allow_initial_calls(self):
        """Test initial calls allowed"""
        limiter = RateLimiter(max_calls=5, period=60)

        # First 5 calls should be allowed
        for _i in range(5):
            with limiter:
                pass  # The context manager handles recording calls

    @patch("time.sleep")
    def test_rate_limiter_block_excess_calls(self, mock_sleep):
        """Test calls exceeding limit are blocked"""
        limiter = RateLimiter(max_calls=3, period=60)

        # Record 3 calls
        for _i in range(3):
            with limiter:
                pass

        # The 4th call should trigger a delay
        with limiter:
            pass

        # Verify that sleep was called (indicating rate limiting is in effect)
        mock_sleep.assert_called()

    def test_rate_limiter_time_window(self):
        """Test time window sliding"""
        limiter = RateLimiter(max_calls=2, period=1)  # Max 2 calls within 1 second

        # Record 2 calls
        with limiter:
            pass
        with limiter:
            pass

        # Check if waiting is needed
        sleep_time = limiter.get_sleep_time()
        assert sleep_time > 0

        # Wait beyond the time window to let old calls expire
        time.sleep(1.1)

        # Make a new call now, which will clean up expired calls
        with limiter:
            pass

        # After the call, there should be only 1 call in the window, so no wait is needed
        sleep_time = limiter.get_sleep_time()
        assert sleep_time == 0

    def test_rate_limiter_sliding_window(self):
        """Test sliding window mechanism"""
        limiter = RateLimiter(max_calls=3, period=3)  # Max 3 calls within 3 seconds

        # Record calls at different time points
        with limiter:
            pass  # t=0
        time.sleep(1)
        with limiter:
            pass  # t=1
        time.sleep(1)
        with limiter:
            pass  # t=2

        # At t=2, there are 3 calls in the window, should need to wait
        sleep_time = limiter.get_sleep_time()
        assert sleep_time > 0

        # Wait until t=3.1, the first call should expire (from t=0 to t=3.1 is over 3 seconds)
        time.sleep(1.1)

        # Make a new call, which will trigger cleanup and remove expired calls
        with limiter:
            pass

        # Now there should be only 3 calls in the window (t=1, t=2, t=3.1), can call again
        sleep_time = limiter.get_sleep_time()
        assert sleep_time == 0

    def test_sync_context_manager(self):
        """Test synchronous context manager"""
        limiter = RateLimiter(max_calls=2, period=60)

        # First 2 calls should succeed
        with limiter:
            pass
        with limiter:
            pass

        # Verify calls are recorded
        assert len(limiter.calls) == 2

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test asynchronous context manager"""
        limiter = RateLimiter(max_calls=2, period=1)

        # Quickly record 2 calls
        async with limiter:
            pass
        async with limiter:
            pass

        # The 3rd call should wait
        start_time = asyncio.get_event_loop().time()
        async with limiter:
            pass
        end_time = asyncio.get_event_loop().time()

        # Should have waited some time (but not necessarily a full second, due to sliding window)
        assert end_time > start_time
