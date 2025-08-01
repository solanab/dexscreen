import asyncio
import collections
import threading
import time
from collections import deque


class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""

    pass


class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self.calls: deque[float] = collections.deque()

        self.period = period
        self.max_calls = max_calls

        self.sync_lock = threading.Lock()
        self.async_lock = asyncio.Lock()

    def __enter__(self):
        with self.sync_lock:
            sleep_time = self.get_sleep_time()

            if sleep_time > 0:
                time.sleep(sleep_time)

            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.sync_lock:
            self._clear_calls()

    async def __aenter__(self):
        async with self.async_lock:
            sleep_time = self.get_sleep_time()

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self.async_lock:
            self._clear_calls()

    def get_sleep_time(self) -> float:
        if len(self.calls) >= self.max_calls:
            until = time.time() + self.period - self._timespan
            return until - time.time()

        return 0

    def _clear_calls(self):
        self.calls.append(time.time())

        while self._timespan >= self.period:
            self.calls.popleft()

    @property
    def _timespan(self) -> float:
        return self.calls[-1] - self.calls[0]
