"""
Enhanced with realworld browser impersonation and custom configuration support
"""

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Literal, Optional, Union

import orjson
from curl_cffi.requests import AsyncSession, Session

from ..utils.browser_selector import get_random_browser
from ..utils.ratelimit import RateLimiter
from ..utils.retry import RetryConfig, RetryManager, RetryPresets
from .exceptions import (
    HttpConnectionError,
    HttpRequestError,
    HttpResponseParsingError,
    HttpSessionError,
    HttpTimeoutError,
)

logger = logging.getLogger(__name__)

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

        # Statistics
        self._stats = {
            "switches": 0,
            "failed_requests": 0,
            "successful_requests": 0,
            "last_switch": None,
            "retry_attempts": 0,
            "retry_successes": 0,
            "retry_failures": 0,
        }

    def _create_absolute_url(self, relative: str) -> str:
        base = self.base_url.rstrip("/")
        relative = relative.lstrip("/")
        return f"{base}/{relative}"

    async def _ensure_active_session(self) -> AsyncSession:
        """Ensure there's an active session"""
        async with self._switch_lock:
            # If primary session is not active, create it
            if self._primary_state != SessionState.ACTIVE and self._primary_session is None:
                self._primary_session = AsyncSession(**self.client_kwargs)
                # Warm up connection
                warmup_success = False
                try:
                    warmup_url = self._create_absolute_url(self.warmup_url)
                    response = await self._primary_session.get(warmup_url)
                    if response.status_code == 200:
                        warmup_success = True
                except Exception:
                    pass  # Warmup failure doesn't affect usage

                # Only activate if warmup succeeded
                if warmup_success:
                    self._primary_state = SessionState.ACTIVE
                else:
                    # Keep trying with the session even if warmup failed
                    # This maintains backward compatibility
                    self._primary_state = SessionState.ACTIVE

            if self._primary_session is None:
                raise RuntimeError("Failed to create primary session")
            return self._primary_session

    def _ensure_sync_session(self) -> Session:
        """Ensure there's a sync session"""
        with self._lock:
            if self._sync_primary is None:
                self._sync_primary = Session(**self.client_kwargs)
                # Warm up
                try:
                    warmup_url = self._create_absolute_url(self.warmup_url)
                    response = self._sync_primary.get(warmup_url)
                    # Check if warmup was successful
                    if response.status_code != 200:
                        pass  # Log warning in production
                except Exception:
                    pass

            return self._sync_primary

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

        with self._limiter:
            # Try session creation first
            try:
                session = self._ensure_sync_session()
            except Exception as e:
                raise HttpSessionError("Failed to create or access sync session", original_error=e) from e

            while True:
                try:
                    response = session.request(method, url, **kwargs)  # type: ignore
                    response.raise_for_status()

                    # Track success
                    with self._lock:
                        self._stats["successful_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_successes"] += 1

                    # Check if response is JSON
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            # Use orjson for better performance
                            return orjson.loads(response.content)
                        except Exception as e:
                            # Get response content as string for error reporting
                            content_preview = (
                                response.content[:200].decode("utf-8", errors="replace") if response.content else ""
                            )
                            # Parsing errors are not retryable
                            raise HttpResponseParsingError(
                                method, url, content_type, content_preview, original_error=e
                            ) from e
                    else:
                        # Non-JSON response (e.g., HTML error page) - this could be an API error
                        content_preview = (
                            response.content[:200].decode("utf-8", errors="replace") if response.content else ""
                        )
                        # Parsing errors are not retryable
                        raise HttpResponseParsingError(
                            method,
                            url,
                            content_type,
                            content_preview,
                            original_error=Exception(f"Expected JSON response but got {content_type}"),
                        )

                except HttpResponseParsingError:
                    # Re-raise parsing errors immediately (not retryable)
                    raise
                except Exception as e:
                    with self._lock:
                        self._stats["failed_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_attempts"] += 1

                    retry_manager.record_failure(e)

                    if retry_manager.should_retry(e):
                        logger.debug(
                            "Retrying sync request %s %s (attempt %d/%d): %s",
                            method,
                            url,
                            retry_manager.attempt,
                            self.retry_config.max_retries + 1,
                            str(e),
                        )
                        retry_manager.wait_sync()
                        continue
                    else:
                        # Not retryable or max retries exceeded - classify and raise final error
                        with self._lock:
                            if retry_manager.attempt > 0:
                                self._stats["retry_failures"] += 1

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

        async with self._limiter:
            while True:
                # Get active session for each attempt
                try:
                    session = await self._ensure_active_session()
                except Exception as e:
                    raise HttpSessionError("Failed to create or access async session", original_error=e) from e

                # Track active requests
                with self._lock:
                    self._primary_requests += 1

                try:
                    response = await session.request(method, url, **kwargs)  # type: ignore
                    response.raise_for_status()

                    # Track success
                    with self._lock:
                        self._stats["successful_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_successes"] += 1

                    # Parse response
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            # Use orjson for better performance
                            return orjson.loads(response.content)
                        except Exception as e:
                            # Get response content as string for error reporting
                            content_preview = (
                                response.content[:200].decode("utf-8", errors="replace") if response.content else ""
                            )
                            # Parsing errors are not retryable
                            raise HttpResponseParsingError(
                                method, url, content_type, content_preview, original_error=e
                            ) from e
                    else:
                        # Non-JSON response (e.g., HTML error page) - this could be an API error
                        content_preview = (
                            response.content[:200].decode("utf-8", errors="replace") if response.content else ""
                        )
                        # Parsing errors are not retryable
                        raise HttpResponseParsingError(
                            method,
                            url,
                            content_type,
                            content_preview,
                            original_error=Exception(f"Expected JSON response but got {content_type}"),
                        )

                except HttpResponseParsingError:
                    # Re-raise parsing errors immediately (not retryable)
                    with self._lock:
                        self._stats["failed_requests"] += 1
                    raise
                except Exception as e:
                    with self._lock:
                        self._stats["failed_requests"] += 1
                        if retry_manager.attempt > 0:
                            self._stats["retry_attempts"] += 1

                    retry_manager.record_failure(e)

                    if retry_manager.should_retry(e):
                        logger.debug(
                            "Retrying async request %s %s (attempt %d/%d): %s",
                            method,
                            url,
                            retry_manager.attempt,
                            self.retry_config.max_retries + 1,
                            str(e),
                        )

                        # Decrease request count before waiting
                        with self._lock:
                            self._primary_requests -= 1

                        await retry_manager.wait_async()
                        continue
                    else:
                        # Not retryable or max retries exceeded
                        with self._lock:
                            if retry_manager.attempt > 0:
                                self._stats["retry_failures"] += 1

                        # Try failover to secondary session if available (only on final failure)
                        if self._secondary_state == SessionState.ACTIVE:
                            try:
                                # Decrease primary request count before failover
                                with self._lock:
                                    self._primary_requests -= 1

                                return await self._failover_request(method, url, **kwargs)
                            except Exception as failover_error:
                                # If failover also fails, raise the original error with failover context
                                raise self._classify_async_error(method, url, e, kwargs) from failover_error

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
            try:
                with self._lock:
                    self._secondary_requests += 1

                response = await self._secondary_session.request(method, url, **kwargs)  # type: ignore
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        # Use orjson for better performance
                        return orjson.loads(response.content)
                    except Exception as e:
                        # Get response content as string for error reporting
                        content_preview = (
                            response.content[:200].decode("utf-8", errors="replace") if response.content else ""
                        )
                        raise HttpResponseParsingError(
                            method, url, content_type, content_preview, original_error=e
                        ) from e
                else:
                    # Non-JSON response (e.g., HTML error page) - this could be an API error
                    content_preview = (
                        response.content[:200].decode("utf-8", errors="replace") if response.content else ""
                    )
                    raise HttpResponseParsingError(
                        method,
                        url,
                        content_type,
                        content_preview,
                        original_error=Exception(f"Expected JSON response but got {content_type}"),
                    )

            except HttpResponseParsingError:
                # Re-raise our custom parsing errors as-is
                raise
            except Exception as e:
                # Classify and raise the failover error
                raise self._classify_async_error(method, url, e, kwargs) from e
            finally:
                with self._lock:
                    self._secondary_requests -= 1

        # No secondary session available
        raise HttpSessionError("No secondary session available for failover")

    async def _perform_switch(self):
        """Perform hot switch between sessions"""
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

        # 4. Async cleanup of old session
        if old_primary:
            asyncio.create_task(self._graceful_close_session(old_primary, lambda: self._secondary_requests))

    async def _graceful_close_session(self, session: AsyncSession, get_request_count):
        """Gracefully close session after requests complete"""
        # Wait for ongoing requests to complete (max 30 seconds)
        start_time = datetime.now()
        timeout = timedelta(seconds=30)

        while get_request_count() > 0:
            if datetime.now() - start_time > timeout:
                break

            await asyncio.sleep(0.1)

        # Close session
        with contextlib.suppress(Exception):
            await session.close()

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
        # Don't lock here - we want requests to continue
        # Prepare new config
        if replace:
            # Complete replacement
            config = new_kwargs.copy()
        else:
            # Merge with existing
            config = self.client_kwargs.copy()
            config.update(new_kwargs)

        # Handle special case: if proxy is None, remove it
        if "proxy" in new_kwargs and new_kwargs["proxy"] is None:
            config.pop("proxy", None)
            config.pop("proxies", None)

        if "impersonate" not in config:
            config["impersonate"] = get_random_browser()

        # Create new session (secondary) without blocking
        new_session = AsyncSession(**config)

        # Warm up new connection in background
        warmup_success = False
        try:
            warmup_url = self._create_absolute_url(self.warmup_url)
            response = await new_session.get(warmup_url)
            # Only consider warmup successful if we get 200 OK
            if response.status_code == 200:
                warmup_success = True
        except Exception:
            pass

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
        else:
            # Clean up failed session
            with contextlib.suppress(Exception):
                await new_session.close()

    def update_client_kwargs(self, new_kwargs: dict[str, Any], merge: bool = True):
        """
        Update client configuration at runtime.

        Args:
            new_kwargs: New configuration options to apply
            merge: If True, merge with existing kwargs. If False, replace entirely.

        Example:
            # Update proxy
            client.update_client_kwargs({"proxies": {"https": "http://new-proxy:8080"}})

            # Change impersonation
            client.update_client_kwargs({"impersonate": "safari184"})

            # Add custom headers
            client.update_client_kwargs({"headers": {"X-Custom": "value"}})

            # Replace all kwargs
            client.update_client_kwargs({
                "impersonate": "firefox135",
                "timeout": 30,
                "verify": False
            }, merge=False)
        """
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
        Get statistics.

        Returns:
            Statistics dictionary with switches, requests, etc.
        """
        with self._lock:
            return self._stats.copy()

    def update_retry_config(self, retry_config: RetryConfig):
        """
        Update retry configuration at runtime.

        Args:
            retry_config: New retry configuration
        """
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
            await asyncio.gather(*tasks, return_exceptions=True)
