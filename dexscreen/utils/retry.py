"""
Retry mechanism with exponential backoff for network operations
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import curl_cffi.requests.exceptions

# Type variables for generic function decorators
F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_factor: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add random jitter to prevent thundering herd
    retryable_status_codes: set[int] = field(
        default_factory=lambda: {
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
            520,  # Web Server Returned an Unknown Error
            521,  # Web Server Is Down
            522,  # Connection Timed Out
            523,  # Origin Is Unreachable
            524,  # A Timeout Occurred
        }
    )
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (
            # Network-related exceptions
            curl_cffi.requests.exceptions.ConnectionError,
            curl_cffi.requests.exceptions.Timeout,
            curl_cffi.requests.exceptions.ReadTimeout,
            curl_cffi.requests.exceptions.ConnectTimeout,
            # OS-level network errors
            OSError,
            ConnectionError,
            TimeoutError,
        )
    )

    def __post_init__(self):
        """Validate configuration"""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.backoff_factor <= 1:
            raise ValueError("backoff_factor must be greater than 1")


class RetryError(Exception):
    """Raised when all retry attempts have been exhausted"""

    def __init__(self, message: str, original_exception: Exception, attempts: int):
        super().__init__(message)
        self.original_exception = original_exception
        self.attempts = attempts


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for exponential backoff with optional jitter.

    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Calculate exponential delay
    delay = min(config.base_delay * (config.backoff_factor**attempt), config.max_delay)

    # Add jitter if enabled
    if config.jitter:
        # Add random jitter up to 25% of the delay
        jitter = delay * 0.25 * random.random()
        delay += jitter

    return delay


def is_retryable(exception: Exception, config: RetryConfig) -> bool:
    """
    Determine if an exception is retryable based on configuration.

    Args:
        exception: The exception to check
        config: Retry configuration

    Returns:
        True if the exception should trigger a retry
    """
    # Check if it's a retryable exception type
    if isinstance(exception, config.retryable_exceptions):
        return True

    # Check if it's an HTTP response with retryable status code
    if hasattr(exception, "response") and hasattr(exception.response, "status_code"):  # type: ignore[attr-defined]
        return exception.response.status_code in config.retryable_status_codes  # type: ignore[attr-defined]

    # Check for curl_cffi specific status codes
    try:
        if (
            hasattr(curl_cffi.requests.exceptions, "HTTPError")
            and isinstance(exception, curl_cffi.requests.exceptions.HTTPError)
            and hasattr(exception, "response")
            and exception.response is not None
            and hasattr(exception.response, "status_code")
        ):
            return exception.response.status_code in config.retryable_status_codes
    except AttributeError:
        # curl_cffi.requests.exceptions.HTTPError doesn't exist, skip this check
        pass

    return False


def retry_sync(config: Optional[RetryConfig] = None):
    """
    Decorator for synchronous functions with retry logic.

    Args:
        config: Retry configuration. If None, uses default RetryConfig.

    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Log successful retry if this wasn't the first attempt
                    if attempt > 0:
                        logger.info("Function %s succeeded after %d retries", func.__name__, attempt)

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    if attempt < config.max_retries and is_retryable(e, config):
                        delay = calculate_delay(attempt, config)

                        logger.warning(
                            "Function %s failed (attempt %d/%d): %s. Retrying in %.2f seconds",
                            func.__name__,
                            attempt + 1,
                            config.max_retries + 1,
                            str(e),
                            delay,
                        )

                        time.sleep(delay)
                    else:
                        # Not retryable or max retries exceeded
                        break

            # All retries exhausted
            error_msg = f"Function {func.__name__} failed after {config.max_retries + 1} attempts"
            if last_exception:
                logger.error("%s. Last error: %s", error_msg, str(last_exception))
                raise RetryError(error_msg, last_exception, config.max_retries + 1)
            else:
                # This should never happen, but handle it gracefully
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        return wrapper  # type: ignore[return-value]

    return decorator


def retry_async(config: Optional[RetryConfig] = None):
    """
    Decorator for asynchronous functions with retry logic.

    Args:
        config: Retry configuration. If None, uses default RetryConfig.

    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: AsyncF) -> AsyncF:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    # Log successful retry if this wasn't the first attempt
                    if attempt > 0:
                        logger.info("Function %s succeeded after %d retries", func.__name__, attempt)

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    if attempt < config.max_retries and is_retryable(e, config):
                        delay = calculate_delay(attempt, config)

                        logger.warning(
                            "Function %s failed (attempt %d/%d): %s. Retrying in %.2f seconds",
                            func.__name__,
                            attempt + 1,
                            config.max_retries + 1,
                            str(e),
                            delay,
                        )

                        await asyncio.sleep(delay)
                    else:
                        # Not retryable or max retries exceeded
                        break

            # All retries exhausted
            error_msg = f"Function {func.__name__} failed after {config.max_retries + 1} attempts"
            if last_exception:
                logger.error("%s. Last error: %s", error_msg, str(last_exception))
                raise RetryError(error_msg, last_exception, config.max_retries + 1)
            else:
                # This should never happen, but handle it gracefully
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        return wrapper  # type: ignore[return-value]

    return decorator


class RetryManager:
    """
    Context manager for manual retry operations.
    Useful when you need fine-grained control over retry logic.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_exception: Optional[Exception] = None

    def should_retry(self, exception: Exception) -> bool:
        """Check if we should retry given an exception"""
        if self.attempt >= self.config.max_retries:
            return False
        return is_retryable(exception, self.config)

    def record_failure(self, exception: Exception):
        """Record a failure and prepare for potential retry"""
        self.last_exception = exception
        self.attempt += 1

    def calculate_delay(self) -> float:
        """Calculate delay for current attempt"""
        return calculate_delay(self.attempt - 1, self.config)

    def wait_sync(self):
        """Wait synchronously for the calculated delay"""
        if self.last_exception and self.should_retry(self.last_exception):
            delay = self.calculate_delay()
            logger.warning(
                "Retrying after %.2f seconds (attempt %d/%d): %s",
                delay,
                self.attempt,
                self.config.max_retries + 1,
                str(self.last_exception),
            )
            time.sleep(delay)

    async def wait_async(self):
        """Wait asynchronously for the calculated delay"""
        if self.last_exception and self.should_retry(self.last_exception):
            delay = self.calculate_delay()
            logger.warning(
                "Retrying after %.2f seconds (attempt %d/%d): %s",
                delay,
                self.attempt,
                self.config.max_retries + 1,
                str(self.last_exception),
            )
            await asyncio.sleep(delay)

    def raise_if_exhausted(self, operation_name: str = "Operation"):
        """Raise RetryError if all retries are exhausted"""
        if self.attempt > self.config.max_retries and self.last_exception:
            error_msg = f"{operation_name} failed after {self.attempt} attempts"
            logger.error("%s. Last error: %s", error_msg, str(self.last_exception))
            raise RetryError(error_msg, self.last_exception, self.attempt)


# Predefined retry configurations for common scenarios
class RetryPresets:
    """Predefined retry configurations for common use cases"""

    @staticmethod
    def network_operations() -> RetryConfig:
        """Conservative retry for network operations"""
        return RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0, backoff_factor=2.0, jitter=True)

    @staticmethod
    def api_calls() -> RetryConfig:
        """Moderate retry for API calls"""
        return RetryConfig(max_retries=5, base_delay=0.5, max_delay=60.0, backoff_factor=1.5, jitter=True)

    @staticmethod
    def aggressive() -> RetryConfig:
        """Aggressive retry for critical operations"""
        return RetryConfig(max_retries=10, base_delay=0.1, max_delay=120.0, backoff_factor=1.8, jitter=True)

    @staticmethod
    def rate_limit_heavy() -> RetryConfig:
        """Retry configuration optimized for rate-limited APIs"""
        return RetryConfig(
            max_retries=8,
            base_delay=2.0,
            max_delay=300.0,  # 5 minutes max
            backoff_factor=2.5,
            jitter=True,
            retryable_status_codes={429, 500, 502, 503, 504},  # Focus on rate limits and server errors
        )
