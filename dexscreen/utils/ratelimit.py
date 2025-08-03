import asyncio
import collections
import threading
import time
from collections import deque
from typing import Any

from .logging_config import get_contextual_logger, with_correlation_id


class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self.calls: deque[float] = collections.deque()

        self.period = period
        self.max_calls = max_calls

        self.sync_lock = threading.Lock()
        self.async_lock = asyncio.Lock()

        # Enhanced logging
        self.contextual_logger = get_contextual_logger(__name__)

        # Rate limiting statistics
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "total_wait_time": 0.0,
            "max_wait_time": 0.0,
            "average_wait_time": 0.0,
            "calls_in_current_window": 0,
            "window_start_time": None,
        }

        init_context = {
            "max_calls": max_calls,
            "period": period,
            "rate_per_second": max_calls / period,
        }

        self.contextual_logger.debug("RateLimiter initialized", context=init_context)

    @with_correlation_id()
    def __enter__(self):
        with self.sync_lock:
            self.stats["total_requests"] += 1
            sleep_time = self.get_sleep_time()

            rate_limit_context = {
                "operation": "sync_rate_limit_enter",
                "sleep_time": sleep_time,
                "calls_in_window": len(self.calls),
                "max_calls": self.max_calls,
                "period": self.period,
                "will_block": sleep_time > 0,
            }

            if sleep_time > 0:
                self.stats["blocked_requests"] += 1
                self.stats["total_wait_time"] += sleep_time
                self.stats["max_wait_time"] = max(self.stats["max_wait_time"], sleep_time)

                # Update average wait time
                if self.stats["blocked_requests"] > 0:
                    self.stats["average_wait_time"] = self.stats["total_wait_time"] / self.stats["blocked_requests"]

                rate_limit_context["blocking_duration"] = sleep_time

                self.contextual_logger.warning(
                    "Rate limit exceeded, sleeping for %.3fs (calls: %d/%d)",
                    sleep_time,
                    len(self.calls),
                    self.max_calls,
                    context=rate_limit_context,
                )

                start_time = time.time()
                time.sleep(sleep_time)
                actual_sleep = time.time() - start_time

                if abs(actual_sleep - sleep_time) > 0.1:  # More than 100ms difference
                    self.contextual_logger.debug(
                        "Sleep time deviation: expected %.3fs, actual %.3fs",
                        sleep_time,
                        actual_sleep,
                        context={"expected_sleep": sleep_time, "actual_sleep": actual_sleep},
                    )
            else:
                self.contextual_logger.debug("Rate limit check passed", context=rate_limit_context)

            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.sync_lock:
            self._clear_calls()

            # Update current window stats
            self.stats["calls_in_current_window"] = len(self.calls)
            if self.calls and self.stats["window_start_time"] is None:
                self.stats["window_start_time"] = self.calls[0]

    @with_correlation_id()
    async def __aenter__(self):
        async with self.async_lock:
            self.stats["total_requests"] += 1
            sleep_time = self.get_sleep_time()

            rate_limit_context = {
                "operation": "async_rate_limit_enter",
                "sleep_time": sleep_time,
                "calls_in_window": len(self.calls),
                "max_calls": self.max_calls,
                "period": self.period,
                "will_block": sleep_time > 0,
            }

            if sleep_time > 0:
                self.stats["blocked_requests"] += 1
                self.stats["total_wait_time"] += sleep_time
                self.stats["max_wait_time"] = max(self.stats["max_wait_time"], sleep_time)

                # Update average wait time
                if self.stats["blocked_requests"] > 0:
                    self.stats["average_wait_time"] = self.stats["total_wait_time"] / self.stats["blocked_requests"]

                rate_limit_context["blocking_duration"] = sleep_time

                self.contextual_logger.warning(
                    "Async rate limit exceeded, sleeping for %.3fs (calls: %d/%d)",
                    sleep_time,
                    len(self.calls),
                    self.max_calls,
                    context=rate_limit_context,
                )

                start_time = time.time()
                await asyncio.sleep(sleep_time)
                actual_sleep = time.time() - start_time

                if abs(actual_sleep - sleep_time) > 0.1:  # More than 100ms difference
                    self.contextual_logger.debug(
                        "Async sleep time deviation: expected %.3fs, actual %.3fs",
                        sleep_time,
                        actual_sleep,
                        context={"expected_sleep": sleep_time, "actual_sleep": actual_sleep},
                    )
            else:
                self.contextual_logger.debug("Async rate limit check passed", context=rate_limit_context)

            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self.async_lock:
            self._clear_calls()

            # Update current window stats
            self.stats["calls_in_current_window"] = len(self.calls)
            if self.calls and self.stats["window_start_time"] is None:
                self.stats["window_start_time"] = self.calls[0]

    def get_sleep_time(self) -> float:
        """Calculate how long to sleep before allowing the next call"""
        if len(self.calls) >= self.max_calls:
            until = time.time() + self.period - self._timespan
            sleep_time = until - time.time()

            # Log when rate limit calculations result in significant wait times
            if sleep_time > 1.0:  # More than 1 second
                sleep_context = {
                    "operation": "calculate_sleep_time",
                    "calculated_sleep": sleep_time,
                    "calls_in_window": len(self.calls),
                    "window_timespan": self._timespan,
                    "max_calls": self.max_calls,
                    "period": self.period,
                    "utilization_percent": (len(self.calls) / self.max_calls) * 100,
                }

                self.contextual_logger.debug(
                    "Rate limit calculation: need to sleep %.3fs (window %.1f%% full)",
                    sleep_time,
                    sleep_context["utilization_percent"],
                    context=sleep_context,
                )

            return max(0, sleep_time)  # Ensure non-negative

        return 0

    def _clear_calls(self):
        """Add current call and remove expired calls from the sliding window"""
        current_time = time.time()
        calls_before = len(self.calls)

        self.calls.append(current_time)

        # Remove expired calls
        while len(self.calls) > 1 and self._timespan >= self.period:
            self.calls.popleft()

        calls_after = len(self.calls)
        expired_calls = calls_before + 1 - calls_after  # +1 for the new call we just added

        if expired_calls > 0:
            clear_context = {
                "operation": "clear_expired_calls",
                "expired_calls": expired_calls,
                "calls_remaining": calls_after,
                "window_timespan": self._timespan if len(self.calls) > 1 else 0,
                "current_utilization": (calls_after / self.max_calls) * 100,
            }

            self.contextual_logger.debug(
                "Cleared %d expired calls, %d calls remaining (%.1f%% capacity)",
                expired_calls,
                calls_after,
                clear_context["current_utilization"],
                context=clear_context,
            )

    @property
    def _timespan(self) -> float:
        """Get the time span of the current sliding window"""
        if len(self.calls) < 2:
            return 0
        return self.calls[-1] - self.calls[0]

    def get_rate_limit_stats(self) -> dict[str, Any]:
        """Get comprehensive rate limiting statistics"""
        time.time()

        # Calculate current rate
        current_rate = 0.0
        if len(self.calls) > 1:
            window_duration = min(self._timespan, self.period)
            if window_duration > 0:
                current_rate = len(self.calls) / window_duration

        stats = self.stats.copy()
        stats.update(
            {
                "current_calls_in_window": len(self.calls),
                "current_window_timespan": self._timespan,
                "current_rate_per_second": current_rate,
                "configured_max_rate": self.max_calls / self.period,
                "capacity_utilization_percent": (len(self.calls) / self.max_calls) * 100,
                "next_sleep_time": self.get_sleep_time(),
                "is_rate_limited": len(self.calls) >= self.max_calls,
                "efficiency_ratio": (self.stats["total_requests"] - self.stats["blocked_requests"])
                / max(1, self.stats["total_requests"]),
            }
        )

        return stats

    def log_stats(self, operation: str = "rate_limit_stats"):
        """Log current rate limiting statistics"""
        stats = self.get_rate_limit_stats()

        stats_context = {"operation": operation, **stats}

        self.contextual_logger.info(
            "Rate limiter stats: %d/%d requests, %.1f%% blocked, %.3fs avg wait",
            stats["total_requests"],
            stats["max_calls"],
            (stats["blocked_requests"] / max(1, stats["total_requests"])) * 100,
            stats["average_wait_time"],
            context=stats_context,
        )
