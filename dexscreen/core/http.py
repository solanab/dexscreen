"""
Enhanced HTTP client with structured logging and error context preservation
"""

import asyncio
import contextlib
import time
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Literal, Optional, Union

import orjson
from curl_cffi.requests import AsyncSession, Session

from ..utils.browser_selector import get_random_browser
from ..utils.logging_config import generate_correlation_id, get_contextual_logger, with_correlation_id
from ..utils.ratelimit import RateLimiter
from ..utils.retry import RetryConfig, RetryManager, RetryPresets
from .exceptions import (
    HttpConnectionError,
    HttpRequestError,
    HttpResponseParsingError,
    HttpSessionError,
    HttpTimeoutError,
)

# Type alias for HTTP methods
HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "TRACE"]


class SessionState(Enum):
    """Session state"""

    ACTIVE = "active"  # Active, accepting new requests
    DRAINING = "draining"  # Draining, not accepting new requests
    STANDBY = "standby"  # Standby, ready to take over
    CLOSED = "closed"  # Closed


class HttpClientCffi:
    """HTTP client with curl_cffi for bypassing anti-bot measures

    Features:
    - Session reuse for better performance (avoid TLS handshake)
    - Zero-downtime configuration updates
    - Graceful session switching
    - Automatic connection warm-up
    - Enhanced structured logging with correlation IDs
    - Request/response tracking and error context preservation
    """

    def __init__(
        self,
        calls: int,
        period: int,
        base_url: str = "https://api.dexscreener.com/",
        client_kwargs: Optional[dict[str, Any]] = None,
        warmup_url: str = "/latest/dex/tokens/solana?limit=1",
        retry_config: Optional[RetryConfig] = None,
    ):
        """
        Initialize HTTP client with rate limiting and browser impersonation.

        Args:
            calls: Maximum number of calls allowed
            period: Time period in seconds
            base_url: Base URL for API requests
            client_kwargs: Optional kwargs to pass to curl_cffi Session/AsyncSession.
                Common options include:
                - impersonate: Browser to impersonate (default: "realworld")
                - proxies: Proxy configuration
                - timeout: Request timeout (default: 10 seconds)
                - headers: Additional headers
                - verify: SSL verification
            warmup_url: URL path for warming up new sessions
            retry_config: Retry configuration for network operations.
                If None, uses default API-optimized retry settings.
        """
        self._limiter = RateLimiter(calls, period)
        self.base_url = base_url
        self.warmup_url = warmup_url

        # Setup retry configuration
        self.retry_config = retry_config or RetryPresets.api_calls()

        # Setup client kwargs with defaults
        self.client_kwargs = client_kwargs or {}

        # Set default timeout if not specified
        if "timeout" not in self.client_kwargs:
            self.client_kwargs["timeout"] = 10

        # Use our custom realworld browser selection if not specified
        if "impersonate" not in self.client_kwargs:
            self.client_kwargs["impersonate"] = get_random_browser()

        # Thread lock for safe updates
        self._lock = Lock()

        # Session management
        # Primary session
        self._primary_session: Optional[AsyncSession] = None
        self._primary_state = SessionState.CLOSED
        self._primary_requests = 0  # Active request count

        # Secondary session for hot switching
        self._secondary_session: Optional[AsyncSession] = None
        self._secondary_state = SessionState.CLOSED
        self._secondary_requests = 0

        # Sync sessions
        self._sync_primary: Optional[Session] = None
        self._sync_secondary: Optional[Session] = None

        # Async lock for session switching
        self._switch_lock = asyncio.Lock()

        # Enhanced statistics with timing data
        self._stats = {
            "switches": 0,
            "failed_requests": 0,
            "successful_requests": 0,
            "last_switch": None,
            "retry_attempts": 0,
            "retry_successes": 0,
            "retry_failures": 0,
            "total_requests": 0,
            "average_response_time": 0.0,
            "min_response_time": float("inf"),
            "max_response_time": 0.0,
        }

        # Enhanced logging
        self.logger = get_contextual_logger(__name__)

    def _create_absolute_url(self, relative: str) -> str:
        base = self.base_url.rstrip("/")
        relative = relative.lstrip("/")
        return f"{base}/{relative}"

    def _update_response_time_stats(self, duration: float):
        """Update response time statistics"""
        with self._lock:
            self._stats["total_requests"] += 1
            # Update running average response time
            total_requests = self._stats["total_requests"]
            current_avg = self._stats["average_response_time"]
            self._stats["average_response_time"] = (current_avg * (total_requests - 1) + duration) / total_requests
            # Update min/max
            self._stats["min_response_time"] = min(self._stats["min_response_time"], duration)
            self._stats["max_response_time"] = max(self._stats["max_response_time"], duration)

    def _parse_json_response(
        self,
        response: Any,
        method: str,
        url: str,
        context: dict[str, Any]
    ) -> Union[list, dict, None]:
        """Parse JSON response with proper error handling and logging"""
        content_type = response.headers.get("content-type", "")

        if "application/json" not in content_type:
            # Non-JSON response
            content_preview = (
                response.content[:200].decode("utf-8", errors="replace")
                if response.content else ""
            )

            parse_context = context.copy()
            parse_context.update({
                "expected_json": True,
                "received_content_type": content_type,
                "content_preview": content_preview,
            })

            self.logger.warning("Received non-JSON response when JSON expected", context=parse_context)

            raise HttpResponseParsingError(
                method,
                url,
                content_type,
                content_preview,
                original_error=Exception(f"Expected JSON response but got {content_type}")
            )

        try:
            return orjson.loads(response.content)
        except Exception as e:
            content_preview = (
                response.content[:200].decode("utf-8", errors="replace")
                if response.content else ""
            )

            parse_context = context.copy()
            parse_context.update({
                "parse_error": str(e),
                "content_preview": content_preview,
            })

            self.logger.error(
                "Failed to parse JSON response: %s",
                str(e),
                context=parse_context,
                exc_info=True
            )

            raise HttpResponseParsingError(
                method, url, content_type, content_preview, original_error=e
            ) from e

    async def _ensure_active_session(self) -> AsyncSession:
        """Ensure there's an active session"""
        async with self._switch_lock:
            # Create primary session if it doesn't exist
            if self._primary_session is None:
                session_context = {
                    "operation": "create_session",
                    "session_type": "primary_async",
                    "browser": self.client_kwargs.get("impersonate", "unknown"),
                }

                self.logger.debug("Creating new async session", context=session_context)

                try:
                    self._primary_session = AsyncSession(**self.client_kwargs)

                    # Warm up connection
                    warmup_start = time.time()
                    try:
                        warmup_url = self._create_absolute_url(self.warmup_url)
                        response = await self._primary_session.get(warmup_url)
                        if response.status_code == 200:
                            warmup_duration = time.time() - warmup_start

                            session_context.update(
                                {
                                    "warmup_success": True,
                                    "warmup_time_ms": round(warmup_duration * 1000, 2),
                                    "warmup_status": response.status_code,
                                }
                            )

                            self.logger.debug("Session warmup successful", context=session_context)
                    except Exception as e:
                        warmup_duration = time.time() - warmup_start
                        session_context.update(
                            {
                                "warmup_success": False,
                                "warmup_time_ms": round(warmup_duration * 1000, 2),
                                "warmup_error": str(e),
                            }
                        )

                        self.logger.warning("Session warmup failed", context=session_context)

                    # Always activate the session (warmup is optional)
                    self._primary_state = SessionState.ACTIVE

                except Exception as e:
                    session_context.update(
                        {
                            "creation_error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )

                    self.logger.error(
                        "Failed to create async session: %s", str(e), context=session_context, exc_info=True
                    )
                    raise

            if self._primary_session is None:
                raise RuntimeError("Failed to create primary session")
            return self._primary_session

    def _ensure_sync_session(self) -> Session:
        """Ensure there's a sync session"""
        with self._lock:
            if self._sync_primary is None:
                session_context = {
                    "operation": "create_session",
                    "session_type": "primary_sync",
                    "browser": self.client_kwargs.get("impersonate", "unknown"),
                }

                self.logger.debug("Creating new sync session", context=session_context)

                try:
                    self._sync_primary = Session(**self.client_kwargs)

                    # Warm up
                    warmup_start = time.time()
                    try:
                        warmup_url = self._create_absolute_url(self.warmup_url)
                        response = self._sync_primary.get(warmup_url)
                        warmup_duration = time.time() - warmup_start

                        if response.status_code == 200:
                            session_context.update(
                                {
                                    "warmup_success": True,
                                    "warmup_time_ms": round(warmup_duration * 1000, 2),
                                    "warmup_status": response.status_code,
                                }
                            )

                            self.logger.debug("Sync session warmup successful", context=session_context)
                        else:
                            session_context.update(
                                {
                                    "warmup_success": False,
                                    "warmup_time_ms": round(warmup_duration * 1000, 2),
                                    "warmup_status": response.status_code,
                                }
                            )

                            self.logger.warning("Sync session warmup returned non-200", context=session_context)

                    except Exception as e:
                        warmup_duration = time.time() - warmup_start
                        session_context.update(
                            {
                                "warmup_success": False,
                                "warmup_time_ms": round(warmup_duration * 1000, 2),
                                "warmup_error": str(e),
                            }
                        )

                        self.logger.warning("Sync session warmup failed", context=session_context)

                except Exception as e:
                    session_context.update(
                        {
                            "creation_error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )

                    self.logger.error(
                        "Failed to create sync session: %s", str(e), context=session_context, exc_info=True
                    )
                    raise

            return self._sync_primary

    @with_correlation_id()
    def request(self, method: HttpMethod, url: str, **kwargs) -> Union[list, dict, None]:
        """
        Synchronous request with rate limiting, retry logic, and browser impersonation.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Relative URL path
            **kwargs: Additional request kwargs

        Returns:
            Parsed JSON response

        Raises:
            HttpConnectionError: When unable to establish connection (after retries)
            HttpTimeoutError: When request times out (after retries)
            HttpRequestError: When request fails with HTTP error status (after retries)
            HttpResponseParsingError: When response parsing fails
            HttpSessionError: When session creation fails
        """
        url = self._create_absolute_url(url)
        retry_manager = RetryManager(self.retry_config)
        request_start = time.time()

        request_context = {
            "method": method,
            "url": url,
            "has_kwargs": bool(kwargs),
            "request_id": generate_correlation_id()[:8],
            "session_type": "sync",
        }

        self.logger.debug("Starting sync HTTP request", context=request_context)

        with self._limiter:
            # Try session creation first
            try:
                session = self._ensure_sync_session()
            except Exception as e:
                error_context = request_context.copy()
                error_context.update(
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                )

                self.logger.error("Failed to create sync session: %s", str(e), context=error_context, exc_info=True)
                raise HttpSessionError("Failed to create or access sync session", original_error=e) from e

            while True:
                try:
                    response = session.request(method, url, **kwargs)  # type: ignore
                    response.raise_for_status()

                    request_duration = time.time() - request_start
                    self._update_response_time_stats(request_duration)

                    # Track success
                    with self._lock:
                        self._stats["successful_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_successes"] += 1

                    # Log successful response
                    response_context = request_context.copy()
                    response_context.update(
                        {
                            "status_code": response.status_code,
                            "response_time_ms": round(request_duration * 1000, 2),
                            "content_type": response.headers.get("content-type", "unknown"),
                            "content_length": len(response.content) if response.content else 0,
                            "retry_attempt": retry_manager.attempt,
                            "success": True,
                        }
                    )

                    self.logger.debug("Sync HTTP request completed successfully", context=response_context)

                    # Parse JSON response
                    return self._parse_json_response(response, method, url, response_context)

                except HttpResponseParsingError:
                    # Re-raise parsing errors immediately (not retryable)
                    raise
                except Exception as e:
                    request_duration = time.time() - request_start

                    with self._lock:
                        self._stats["failed_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_attempts"] += 1

                    # Create error context
                    error_context = request_context.copy()
                    error_context.update(
                        {
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "response_time_ms": round(request_duration * 1000, 2),
                            "retry_attempt": retry_manager.attempt,
                        }
                    )

                    # Add response details if available
                    if hasattr(e, "response"):
                        response = e.response  # type: ignore
                        if response is not None:
                            error_context.update(
                                {
                                    "status_code": response.status_code,
                                    "response_headers": dict(response.headers),
                                }
                            )

                    retry_manager.record_failure(e)

                    if retry_manager.should_retry(e):
                        retry_context = error_context.copy()
                        retry_context.update(
                            {
                                "will_retry": True,
                                "max_retries": self.retry_config.max_retries,
                                "retry_delay_ms": round(retry_manager.calculate_delay() * 1000, 2),
                            }
                        )

                        self.logger.warning(
                            "Retrying sync request %s %s (attempt %d/%d): %s",
                            method,
                            url,
                            retry_manager.attempt,
                            self.retry_config.max_retries + 1,
                            str(e),
                            context=retry_context,
                        )
                        retry_manager.wait_sync()
                        continue
                    else:
                        # Not retryable or max retries exceeded - classify and raise final error
                        final_error_context = error_context.copy()
                        final_error_context.update(
                            {
                                "final_failure": True,
                                "total_retry_attempts": retry_manager.attempt,
                                "is_retryable": retry_manager.should_retry(e)
                                if retry_manager.attempt < self.retry_config.max_retries
                                else False,
                            }
                        )

                        with self._lock:
                            if retry_manager.attempt > 0:
                                self._stats["retry_failures"] += 1

                        self.logger.error(
                            "Sync HTTP request failed permanently: %s",
                            str(e),
                            context=final_error_context,
                            exc_info=True,
                        )

                        # Classify the error type for final exception
                        error_msg = str(e).lower()
                        if "timeout" in error_msg or "timed out" in error_msg:
                            # Extract timeout value if available from kwargs
                            timeout = kwargs.get("timeout", "unknown")
                            raise HttpTimeoutError(method, url, timeout, original_error=e) from e
                        elif "connection" in error_msg or "resolve" in error_msg or "network" in error_msg:
                            raise HttpConnectionError(method, url, original_error=e) from e
                        else:
                            # Get status code if available
                            status_code = None
                            response_text = None
                            if hasattr(e, "response"):
                                response = e.response  # type: ignore
                                if response and hasattr(response, "status_code"):
                                    status_code = response.status_code
                                if response and hasattr(response, "content"):
                                    response_text = response.content[:200].decode("utf-8", errors="replace")
                            raise HttpRequestError(method, url, status_code, response_text, original_error=e) from e

    @with_correlation_id()
    async def request_async(self, method: HttpMethod, url: str, **kwargs) -> Union[list, dict, None]:
        """
        Asynchronous request with rate limiting, retry logic, and browser impersonation.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Relative URL path
            **kwargs: Additional request kwargs

        Returns:
            Parsed JSON response

        Raises:
            HttpConnectionError: When unable to establish connection (after retries)
            HttpTimeoutError: When request times out (after retries)
            HttpRequestError: When request fails with HTTP error status (after retries)
            HttpResponseParsingError: When response parsing fails
            HttpSessionError: When session creation fails
        """
        url = self._create_absolute_url(url)
        retry_manager = RetryManager(self.retry_config)
        request_start = time.time()

        request_context = {
            "method": method,
            "url": url,
            "has_kwargs": bool(kwargs),
            "request_id": generate_correlation_id()[:8],
            "session_type": "async",
        }

        self.logger.debug("Starting async HTTP request", context=request_context)

        async with self._limiter:
            while True:
                # Get active session for each attempt
                try:
                    session = await self._ensure_active_session()
                except Exception as e:
                    error_context = request_context.copy()
                    error_context.update(
                        {
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        }
                    )

                    self.logger.error(
                        "Failed to create async session: %s", str(e), context=error_context, exc_info=True
                    )
                    raise HttpSessionError("Failed to create or access async session", original_error=e) from e

                # Track active requests
                with self._lock:
                    self._primary_requests += 1

                try:
                    response = await session.request(method, url, **kwargs)  # type: ignore
                    response.raise_for_status()

                    request_duration = time.time() - request_start
                    self._update_response_time_stats(request_duration)

                    # Track success
                    with self._lock:
                        self._stats["successful_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_successes"] += 1

                    # Log successful response
                    response_context = request_context.copy()
                    response_context.update(
                        {
                            "status_code": response.status_code,
                            "response_time_ms": round(request_duration * 1000, 2),
                            "content_type": response.headers.get("content-type", "unknown"),
                            "content_length": len(response.content) if response.content else 0,
                            "retry_attempt": retry_manager.attempt,
                            "session_state": self._primary_state.value,
                            "success": True,
                        }
                    )

                    self.logger.debug("Async HTTP request completed successfully", context=response_context)

                    # Parse JSON response
                    return self._parse_json_response(response, method, url, response_context)

                except HttpResponseParsingError:
                    # Re-raise parsing errors immediately (not retryable)
                    with self._lock:
                        self._stats["failed_requests"] += 1
                    raise
                except Exception as e:
                    request_duration = time.time() - request_start

                    with self._lock:
                        self._stats["failed_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_attempts"] += 1

                    # Create error context
                    error_context = request_context.copy()
                    error_context.update(
                        {
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "response_time_ms": round(request_duration * 1000, 2),
                            "retry_attempt": retry_manager.attempt,
                            "session_state": self._primary_state.value,
                        }
                    )

                    # Add response details if available
                    if hasattr(e, "response"):
                        response = e.response  # type: ignore
                        if response is not None:
                            error_context.update(
                                {
                                    "status_code": response.status_code,
                                    "response_headers": dict(response.headers),
                                }
                            )

                    self.logger.error("Async HTTP request failed: %s", str(e), context=error_context, exc_info=True)

                    retry_manager.record_failure(e)

                    if retry_manager.should_retry(e):
                        retry_context = error_context.copy()
                        retry_context.update(
                            {
                                "will_retry": True,
                                "max_retries": self.retry_config.max_retries,
                                "retry_delay_ms": round(retry_manager.calculate_delay() * 1000, 2),
                            }
                        )

                        self.logger.warning(
                            "Retrying async request %s %s (attempt %d/%d): %s",
                            method,
                            url,
                            retry_manager.attempt,
                            self.retry_config.max_retries + 1,
                            str(e),
                            context=retry_context,
                        )

                        # Decrease request count before waiting
                        with self._lock:
                            self._primary_requests -= 1

                        await retry_manager.wait_async()
                        continue
                    else:
                        # Not retryable or max retries exceeded
                        final_error_context = error_context.copy()
                        final_error_context.update(
                            {
                                "final_failure": True,
                                "total_retry_attempts": retry_manager.attempt,
                                "is_retryable": retry_manager.should_retry(e)
                                if retry_manager.attempt < self.retry_config.max_retries
                                else False,
                            }
                        )

                        with self._lock:
                            if retry_manager.attempt > 0:
                                self._stats["retry_failures"] += 1

                        self.logger.error(
                            "Async HTTP request failed permanently: %s",
                            str(e),
                            context=final_error_context,
                            exc_info=True,
                        )

                        # Try failover to secondary session if available (only on final failure)
                        if self._secondary_state == SessionState.ACTIVE:
                            self.logger.info("Attempting failover to secondary session", context=final_error_context)
                            try:
                                # Decrease primary request count before failover
                                with self._lock:
                                    self._primary_requests -= 1

                                return await self._failover_request(method, url, **kwargs)
                            except Exception as failover_error:
                                failover_context = final_error_context.copy()
                                failover_context.update(
                                    {
                                        "failover_error_type": type(failover_error).__name__,
                                        "failover_error_message": str(failover_error),
                                    }
                                )

                                self.logger.error(
                                    "Failover attempt also failed: %s",
                                    str(failover_error),
                                    context=failover_context,
                                    exc_info=True,
                                )

                                # If failover also fails, raise the original error with failover context
                                raise self._classify_async_error(method, url, e, kwargs) from e

                        # No failover available or didn't work, classify the error
                        raise self._classify_async_error(method, url, e, kwargs) from e

                finally:
                    # Decrease request count (only if we're not retrying)
                    if not (retry_manager.last_exception and retry_manager.should_retry(retry_manager.last_exception)):
                        with self._lock:
                            self._primary_requests -= 1

    def _classify_async_error(self, method: str, url: str, error: Exception, kwargs: dict) -> Exception:
        """Classify an async error into appropriate HTTP exception type"""
        error_msg = str(error).lower()
        if "timeout" in error_msg or "timed out" in error_msg:
            # Extract timeout value if available from kwargs
            timeout = kwargs.get("timeout", "unknown")
            return HttpTimeoutError(method, url, timeout, original_error=error)
        elif "connection" in error_msg or "resolve" in error_msg or "network" in error_msg:
            return HttpConnectionError(method, url, original_error=error)
        else:
            # Get status code if available
            status_code = None
            response_text = None
            if hasattr(error, "response"):
                response = error.response  # type: ignore
                if response and hasattr(response, "status_code"):
                    status_code = response.status_code
                if response and hasattr(response, "content"):
                    response_text = response.content[:200].decode("utf-8", errors="replace")
            return HttpRequestError(method, url, status_code, response_text, original_error=error)

    async def _failover_request(self, method: HttpMethod, url: str, **kwargs) -> Union[list, dict, None]:
        """Failover to secondary session - raises exceptions instead of returning None"""
        if self._secondary_session and self._secondary_state == SessionState.ACTIVE:
            failover_start = time.time()

            failover_context = {
                "method": method,
                "url": url,
                "failover_attempt": True,
                "request_id": generate_correlation_id()[:8],
            }

            self.logger.info("Executing async failover request", context=failover_context)

            try:
                with self._lock:
                    self._secondary_requests += 1

                response = await self._secondary_session.request(method, url, **kwargs)  # type: ignore
                response.raise_for_status()

                failover_duration = time.time() - failover_start

                failover_context.update(
                    {
                        "status_code": response.status_code,
                        "response_time_ms": round(failover_duration * 1000, 2),
                        "content_type": response.headers.get("content-type", "unknown"),
                        "success": True,
                    }
                )

                self.logger.info("Async failover request succeeded", context=failover_context)

                # Parse JSON response
                return self._parse_json_response(response, method, url, failover_context)

            except HttpResponseParsingError:
                # Re-raise our custom parsing errors as-is
                raise
            except Exception as e:
                failover_duration = time.time() - failover_start

                error_context = failover_context.copy()
                error_context.update(
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "response_time_ms": round(failover_duration * 1000, 2),
                        "success": False,
                    }
                )

                self.logger.error("Async failover request failed: %s", str(e), context=error_context, exc_info=True)

                # Classify and raise the failover error
                raise self._classify_async_error(method, url, e, kwargs) from e
            finally:
                with self._lock:
                    self._secondary_requests -= 1

        # No secondary session available
        raise HttpSessionError("No secondary session available for failover")

    async def _perform_switch(self):
        """Perform hot switch between sessions"""
        switch_context = {
            "operation": "session_switch",
            "primary_state": self._primary_state.value,
            "secondary_state": self._secondary_state.value,
            "primary_requests": self._primary_requests,
            "secondary_requests": self._secondary_requests,
        }

        self.logger.info("Starting session switch", context=switch_context)

        # 1. Promote secondary to active
        self._secondary_state = SessionState.ACTIVE

        # 2. Mark primary as draining
        if self._primary_state == SessionState.ACTIVE:
            self._primary_state = SessionState.DRAINING

        # 3. Swap references
        old_primary = self._primary_session
        old_primary_requests = self._primary_requests

        self._primary_session = self._secondary_session
        self._primary_requests = self._secondary_requests
        self._primary_state = SessionState.ACTIVE

        self._secondary_session = old_primary
        self._secondary_requests = old_primary_requests
        self._secondary_state = SessionState.DRAINING

        switch_context.update(
            {
                "switch_completed": True,
                "new_primary_state": self._primary_state.value,
                "new_secondary_state": self._secondary_state.value,
            }
        )

        self.logger.info("Session switch completed", context=switch_context)

        # 4. Async cleanup of old session
        if old_primary:
            asyncio.create_task(self._graceful_close_session(old_primary, lambda: self._secondary_requests))

    async def _graceful_close_session(self, session: AsyncSession, get_request_count):
        """Gracefully close session after requests complete"""
        close_context = {
            "operation": "graceful_close",
            "initial_request_count": get_request_count(),
        }

        self.logger.debug("Starting graceful session close", context=close_context)

        # Wait for ongoing requests to complete (max 30 seconds)
        start_time = datetime.now()
        timeout = timedelta(seconds=30)

        while get_request_count() > 0:
            if datetime.now() - start_time > timeout:
                close_context.update(
                    {
                        "timeout_reached": True,
                        "remaining_requests": get_request_count(),
                    }
                )

                self.logger.warning("Session close timeout reached", context=close_context)
                break

            await asyncio.sleep(0.1)

        # Close session
        try:
            await session.close()
            close_context.update({"close_successful": True})
            self.logger.debug("Session closed successfully", context=close_context)
        except Exception as e:
            close_context.update(
                {
                    "close_successful": False,
                    "close_error": str(e),
                }
            )
            self.logger.warning("Error during session close", context=close_context)

    def set_impersonate(self, browser: str):
        """
        Change browser impersonation.

        NOTE: This method only updates the configuration for future requests.
        It does NOT trigger a hot-switch of existing sessions.
        Use update_config() for hot-switching with zero downtime.

        Args:
            browser: Browser to impersonate. Options include:
                - "chrome136", "chrome134", etc.: Specific Chrome versions
                - "safari180", "safari184", etc.: Specific Safari versions
                - "firefox133", "firefox135", etc.: Specific Firefox versions
                Note: "realworld" is replaced by our custom browser selector
        """
        config_context = {
            "operation": "set_impersonate",
            "old_browser": self.client_kwargs.get("impersonate", "unknown"),
            "new_browser": browser,
        }

        self.logger.info("Updating browser impersonation", context=config_context)

        # Update client kwargs for future sessions
        with self._lock:
            self.client_kwargs["impersonate"] = browser

    async def update_config(self, new_kwargs: dict[str, Any], replace: bool = False):
        """
        Hot update configuration with zero downtime.
        Creates new session with new config and gracefully switches.

        Args:
            new_kwargs: New configuration options
            replace: If True, replace entire config. If False (default), merge with existing.
        """
        config_context = {
            "operation": "config_update",
            "replace_mode": replace,
            "new_config_keys": list(new_kwargs.keys()),
        }

        self.logger.info("Starting configuration update", context=config_context)

        # Don't lock here - we want requests to continue
        # Prepare new config
        if replace:
            # Complete replacement
            config = new_kwargs.copy()
        else:
            # Merge with existing
            config = self.client_kwargs.copy()
            config.update(new_kwargs)

        # Remove proxy if explicitly set to None
        if "proxies" in new_kwargs and new_kwargs["proxies"] is None:
            config.pop("proxies", None)

        if "impersonate" not in config:
            config["impersonate"] = get_random_browser()

        # Create new session (secondary) without blocking
        try:
            new_session = AsyncSession(**config)

            self.logger.debug("Created new session for config update", context=config_context)
        except Exception as e:
            error_context = config_context.copy()
            error_context.update(
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )

            self.logger.error(
                "Failed to create new session during config update: %s", str(e), context=error_context, exc_info=True
            )
            return

        # Warm up new connection in background
        warmup_start = time.time()
        warmup_success = False
        try:
            warmup_url = self._create_absolute_url(self.warmup_url)
            response = await new_session.get(warmup_url)
            warmup_duration = time.time() - warmup_start

            # Only consider warmup successful if we get 200 OK
            if response.status_code == 200:
                warmup_success = True

                warmup_context = config_context.copy()
                warmup_context.update(
                    {
                        "warmup_success": True,
                        "warmup_time_ms": round(warmup_duration * 1000, 2),
                        "warmup_status": response.status_code,
                    }
                )

                self.logger.debug("Session warmup successful during config update", context=warmup_context)
            else:
                self.logger.warning(
                    "Session warmup returned non-200 status during config update: %d",
                    response.status_code,
                    context=config_context,
                )

        except Exception as e:
            warmup_duration = time.time() - warmup_start

            warmup_context = config_context.copy()
            warmup_context.update(
                {
                    "warmup_success": False,
                    "warmup_time_ms": round(warmup_duration * 1000, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )

            self.logger.warning("Session warmup failed during config update: %s", str(e), context=warmup_context)

        # Only proceed with switch if warmup was successful
        if warmup_success:
            # Now acquire lock for the actual switch
            async with self._switch_lock:
                # Store the new session
                self._secondary_session = new_session
                self._secondary_state = SessionState.STANDBY

                # Perform switch
                await self._perform_switch()

                # Update config
                self.client_kwargs = config

                # Statistics
                with self._lock:
                    self._stats["switches"] += 1
                    self._stats["last_switch"] = datetime.now()

                switch_context = config_context.copy()
                switch_context.update(
                    {
                        "switch_successful": True,
                        "total_switches": self._stats["switches"],
                    }
                )

                self.logger.info("Configuration update and session switch completed", context=switch_context)
        else:
            # Clean up failed session
            with contextlib.suppress(Exception):
                await new_session.close()

            self.logger.error("Configuration update failed due to warmup failure", context=config_context)

    def update_client_kwargs(self, new_kwargs: dict[str, Any], merge: bool = True):
        """
        Update client configuration at runtime.

        Args:
            new_kwargs: New configuration options to apply
            merge: If True, merge with existing kwargs. If False, replace entirely.
        """
        config_context = {
            "operation": "update_client_kwargs",
            "merge_mode": merge,
            "new_config_keys": list(new_kwargs.keys()),
        }

        self.logger.debug("Updating client kwargs", context=config_context)

        with self._lock:
            if merge:
                self.client_kwargs.update(new_kwargs)
            else:
                self.client_kwargs = new_kwargs.copy()

            # Ensure we have browser impersonation
            if "impersonate" not in self.client_kwargs:
                self.client_kwargs["impersonate"] = get_random_browser()

    def get_current_config(self) -> dict[str, Any]:
        """
        Get a copy of current client configuration.

        Returns:
            Current client_kwargs dictionary
        """
        with self._lock:
            return self.client_kwargs.copy()

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics including enhanced timing metrics.

        Returns:
            Statistics dictionary with switches, requests, timing data, etc.
        """
        with self._lock:
            stats = self._stats.copy()
            # Calculate additional metrics
            if stats["total_requests"] > 0:
                stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
                stats["failure_rate"] = stats["failed_requests"] / stats["total_requests"]
                if stats["retry_attempts"] > 0:
                    stats["retry_success_rate"] = stats["retry_successes"] / stats["retry_attempts"]
                else:
                    stats["retry_success_rate"] = 0.0
            else:
                stats["success_rate"] = 0.0
                stats["failure_rate"] = 0.0
                stats["retry_success_rate"] = 0.0

            return stats

    def update_retry_config(self, retry_config: RetryConfig):
        """
        Update retry configuration at runtime.

        Args:
            retry_config: New retry configuration
        """
        config_context = {
            "operation": "update_retry_config",
            "max_retries": retry_config.max_retries,
            "base_delay": retry_config.base_delay,
        }

        self.logger.debug("Updating retry configuration", context=config_context)

        with self._lock:
            self.retry_config = retry_config

    def get_retry_config(self) -> RetryConfig:
        """
        Get current retry configuration.

        Returns:
            Current retry configuration
        """
        with self._lock:
            return self.retry_config

    async def close(self):
        """
        Close all sessions gracefully.
        """
        close_context = {
            "operation": "close_all_sessions",
            "primary_state": self._primary_state.value if self._primary_state else "none",
            "secondary_state": self._secondary_state.value if self._secondary_state else "none",
        }

        self.logger.info("Closing all HTTP sessions", context=close_context)

        tasks = []

        if self._primary_session:
            tasks.append(self._primary_session.close())

        if self._secondary_session:
            tasks.append(self._secondary_session.close())

        if self._sync_primary:
            self._sync_primary.close()

        if self._sync_secondary:
            self._sync_secondary.close()

        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
                close_context.update({"async_close_successful": "true"})
            except Exception as e:
                close_context.update(
                    {
                        "async_close_successful": "false",
                        "close_error": str(e),
                    }
                )

        self.logger.info("HTTP sessions closed", context=close_context)
