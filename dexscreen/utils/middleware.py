"""
Middleware utilities for request tracking and correlation ID propagation
"""

import inspect
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from .logging_config import (
    generate_correlation_id,
    get_contextual_logger,
    get_correlation_id,
    set_correlation_id,
    with_correlation_id,
)

F = TypeVar("F", bound=Callable[..., Any])


class RequestTracker:
    """Tracks request lifecycle and propagates correlation IDs"""

    def __init__(self):
        self.contextual_logger = get_contextual_logger(__name__)
        self.active_requests: dict[str, dict[str, Any]] = {}

    def start_request(self, operation: str, context: Optional[dict[str, Any]] = None) -> str:
        """Start tracking a new request and return correlation ID"""
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)

        request_info = {
            "operation": operation,
            "correlation_id": correlation_id,
            "start_time": time.time(),
            "context": context or {},
            "status": "active",
        }

        self.active_requests[correlation_id] = request_info

        track_context = {
            "operation": "request_start",
            "correlation_id": correlation_id,
            "tracked_operation": operation,
            "active_requests_count": len(self.active_requests),
            **request_info["context"],
        }

        self.contextual_logger.info("Starting request tracking for %s", operation, context=track_context)

        return correlation_id

    def end_request(
        self,
        correlation_id: Optional[str] = None,
        status: str = "completed",
        result_context: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """End request tracking and return request info"""
        if correlation_id is None:
            correlation_id = get_correlation_id()

        if not correlation_id or correlation_id not in self.active_requests:
            self.contextual_logger.warning(
                "Attempted to end request tracking with unknown correlation ID: %s",
                correlation_id,
                context={"operation": "request_end_unknown", "correlation_id": correlation_id},
            )
            return None

        request_info = self.active_requests.pop(correlation_id)
        request_info["end_time"] = time.time()
        request_info["duration"] = request_info["end_time"] - request_info["start_time"]
        request_info["status"] = status
        request_info["result_context"] = result_context or {}

        track_context = {
            "operation": "request_end",
            "correlation_id": correlation_id,
            "tracked_operation": request_info["operation"],
            "duration": request_info["duration"],
            "status": status,
            "active_requests_count": len(self.active_requests),
            **request_info["context"],
            **request_info["result_context"],
        }

        log_level = "info" if status == "completed" else "warning" if status == "failed" else "error"
        log_method = getattr(self.contextual_logger, log_level)

        log_method(
            "Completed request tracking for %s (%.3fs, %s)",
            request_info["operation"],
            request_info["duration"],
            status,
            context=track_context,
        )

        return request_info

    def get_active_requests(self) -> dict[str, dict[str, Any]]:
        """Get all currently active requests"""
        return self.active_requests.copy()

    def log_active_requests(self):
        """Log information about currently active requests"""
        if not self.active_requests:
            self.contextual_logger.debug("No active requests", context={"operation": "active_requests_check"})
            return

        current_time = time.time()
        requests_info = []

        for correlation_id, info in self.active_requests.items():
            duration = current_time - info["start_time"]
            requests_info.append(
                {
                    "correlation_id": correlation_id,
                    "operation": info["operation"],
                    "duration": duration,
                }
            )

        active_context = {
            "operation": "active_requests_summary",
            "active_count": len(self.active_requests),
            "requests": requests_info,
        }

        self.contextual_logger.info(
            "%d active requests currently being tracked", len(self.active_requests), context=active_context
        )


# Global request tracker instance
_request_tracker = RequestTracker()


def track_request(operation: str, include_args: bool = False, include_result: bool = False):
    """
    Decorator to automatically track request lifecycle with correlation IDs.

    Args:
        operation: Name of the operation being tracked
        include_args: Whether to include function arguments in context
        include_result: Whether to include function result in context
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Build context
            context: dict[str, Any] = {"function_name": func.__name__}
            if include_args:
                context["args"] = _sanitize_args(args, kwargs)

            # Start tracking
            correlation_id = _request_tracker.start_request(operation, context)

            try:
                result = func(*args, **kwargs)

                # Build result context
                result_context = {}
                if include_result:
                    result_context["result"] = _sanitize_result(result)

                _request_tracker.end_request(correlation_id, "completed", result_context)
                return result

            except Exception as e:
                error_context = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                _request_tracker.end_request(correlation_id, "failed", error_context)
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build context
            context: dict[str, Any] = {"function_name": func.__name__}
            if include_args:
                context["args"] = _sanitize_args(args, kwargs)

            # Start tracking
            correlation_id = _request_tracker.start_request(operation, context)

            try:
                result = await func(*args, **kwargs)

                # Build result context
                result_context = {}
                if include_result:
                    result_context["result"] = _sanitize_result(result)

                _request_tracker.end_request(correlation_id, "completed", result_context)
                return result

            except Exception as e:
                error_context = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                _request_tracker.end_request(correlation_id, "failed", error_context)
                raise

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def _sanitize_args(args: tuple, kwargs: dict) -> dict[str, Any]:
    """Sanitize function arguments for logging"""
    sanitized = {}

    # Limit args to first 3 to avoid log bloat
    if args:
        sanitized["positional"] = [_sanitize_value(arg) for arg in args[:3]]
        if len(args) > 3:
            sanitized["positional_truncated"] = len(args)

    # Sanitize kwargs
    if kwargs:
        sanitized["keyword"] = {k: _sanitize_value(v) for k, v in list(kwargs.items())[:5]}
        if len(kwargs) > 5:
            sanitized["keyword_truncated"] = len(kwargs)

    return sanitized


def _sanitize_value(value: Any) -> Any:
    """Sanitize a single value for logging"""
    if isinstance(value, str):
        # Truncate long strings
        return value[:100] + "..." if len(value) > 100 else value
    elif isinstance(value, (list, tuple)):
        # Show length for collections
        return f"<{type(value).__name__} of {len(value)} items>"
    elif isinstance(value, dict):
        return f"<dict with {len(value)} keys>"
    elif hasattr(value, "__dict__"):
        # Object with attributes
        return f"<{type(value).__name__} instance>"
    else:
        return value


def _sanitize_result(result: Any) -> Any:
    """Sanitize function result for logging"""
    if isinstance(result, (list, tuple)):
        return {"type": type(result).__name__, "length": len(result)}
    elif isinstance(result, dict):
        return {"type": "dict", "keys": len(result)}
    elif hasattr(result, "__dict__"):
        return {"type": type(result).__name__}
    else:
        return _sanitize_value(result)


class CorrelationMiddleware:
    """Middleware for automatic correlation ID management in HTTP requests"""

    def __init__(self):
        self.contextual_logger = get_contextual_logger(__name__)

    def wrap_http_client(self, client_class):
        """Wrap an HTTP client class to add correlation ID headers"""
        original_request = client_class.request
        original_request_async = getattr(client_class, "request_async", None)

        @with_correlation_id()
        def wrapped_request(self, method, url, **kwargs):
            correlation_id = get_correlation_id()
            if correlation_id:
                # Add correlation ID to headers
                headers = kwargs.get("headers", {})
                headers["X-Correlation-ID"] = correlation_id
                kwargs["headers"] = headers

                middleware_context = {
                    "operation": "http_request_correlation",
                    "method": method,
                    "url": url[:100] + "..." if len(url) > 100 else url,
                    "correlation_id": correlation_id,
                    "has_existing_headers": bool(kwargs.get("headers", {})),
                }

                self.contextual_logger.debug(
                    "Adding correlation ID to HTTP %s request", method, context=middleware_context
                )

            return original_request(self, method, url, **kwargs)

        if original_request_async:

            @with_correlation_id()
            async def wrapped_request_async(self, method, url, **kwargs):
                correlation_id = get_correlation_id()
                if correlation_id:
                    # Add correlation ID to headers
                    headers = kwargs.get("headers", {})
                    headers["X-Correlation-ID"] = correlation_id
                    kwargs["headers"] = headers

                    middleware_context = {
                        "operation": "async_http_request_correlation",
                        "method": method,
                        "url": url[:100] + "..." if len(url) > 100 else url,
                        "correlation_id": correlation_id,
                        "has_existing_headers": bool(kwargs.get("headers", {})),
                    }

                    self.contextual_logger.debug(
                        "Adding correlation ID to async HTTP %s request", method, context=middleware_context
                    )

                return await original_request_async(self, method, url, **kwargs)

            client_class.request_async = wrapped_request_async

        client_class.request = wrapped_request
        return client_class


# Global middleware instance
_correlation_middleware = CorrelationMiddleware()


def get_request_tracker() -> RequestTracker:
    """Get the global request tracker instance"""
    return _request_tracker


def get_correlation_middleware() -> CorrelationMiddleware:
    """Get the global correlation middleware instance"""
    return _correlation_middleware


def auto_track_requests(operation_prefix: str = "api"):
    """
    Class decorator to automatically add request tracking to all public methods.

    Args:
        operation_prefix: Prefix for operation names (method names will be appended)
    """

    def decorator(cls):
        for attr_name in dir(cls):
            if not attr_name.startswith("_"):  # Only public methods
                attr = getattr(cls, attr_name)
                if callable(attr):
                    operation_name = f"{operation_prefix}_{attr_name}"
                    tracked_method = track_request(operation_name)(attr)
                    setattr(cls, attr_name, tracked_method)
        return cls

    return decorator
