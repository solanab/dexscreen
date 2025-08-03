"""
Comprehensive exception hierarchy for the dexscreen project.

This module provides structured exceptions that allow for granular error handling
at different levels of the application. All exceptions preserve context and provide
meaningful error messages for debugging and monitoring.

Note: This module maintains backward compatibility with the original exception structure
while providing enhanced functionality for better error handling.
"""

import datetime as dt
from typing import Any, Optional, Union


class DexscreenError(Exception):
    """
    Base exception for all dexscreen-related errors.

    This is the root exception that all other dexscreen exceptions inherit from.
    Use this for broad exception handling when you want to catch any dexscreen error.

    Attributes:
        message: Human-readable error message
        context: Additional context information about the error
        timestamp: When the error occurred
        original_error: The original exception that caused this error (if any)

    Example:
        try:
            client.get_pair("invalid_address")
        except DexscreenError as e:
            logger.error(f"Dexscreen error: {e}")
            # This will catch any dexscreen-specific error
    """

    def __init__(
        self, message: str, context: Optional[dict[str, Any]] = None, original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = dt.datetime.now(dt.timezone.utc)
        self.original_error = original_error

    def __str__(self) -> str:
        base_message = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_message += f" (context: {context_str})"
        return base_message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.message}', context={self.context})"


# =============================================================================
# VALIDATION ERRORS (Backward Compatible)
# =============================================================================


class ValidationError(DexscreenError):
    """Base exception for input validation errors"""

    pass


class InvalidAddressError(ValidationError):
    """
    Raised when an invalid address is provided.

    Enhanced version that maintains backward compatibility while adding new features.

    Attributes:
        address: The invalid address
        reason: Reason why the address is invalid
        address_type: Type of address ("token", "pair", "contract", etc.)
        expected_format: Description of expected format
    """

    def __init__(
        self,
        address: str,
        reason: str = "Invalid address format",
        address_type: Optional[str] = None,
        expected_format: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        # Build context
        full_context = context or {}
        full_context.update({"address": address, "address_type": address_type, "expected_format": expected_format})

        super().__init__(f"{reason}: '{address}'", full_context, original_error)
        self.address = address
        self.reason = reason
        self.address_type = address_type
        self.expected_format = expected_format


class InvalidChainIdError(ValidationError):
    """
    Raised when an invalid chain ID is provided.

    Enhanced version with improved functionality.

    Attributes:
        chain_id: The invalid chain ID
        valid_chains: List of valid chain IDs
        supported_chains: Alias for valid_chains (for compatibility)
    """

    def __init__(
        self,
        chain_id: str,
        valid_chains: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.chain_id = chain_id
        self.valid_chains = valid_chains or []
        self.supported_chains = self.valid_chains  # Alias for compatibility

        # Build context
        full_context = context or {}
        full_context.update({"chain_id": chain_id, "valid_chains": self.valid_chains})

        if self.valid_chains:
            message = f"Invalid chain ID '{chain_id}'. Valid chains: {', '.join(self.valid_chains)}"
        else:
            message = f"Invalid chain ID '{chain_id}'"

        super().__init__(message, full_context, original_error)


# Alias for backward compatibility
InvalidChainError = InvalidChainIdError


class InvalidParameterError(ValidationError):
    """Raised when a parameter has an invalid value"""

    def __init__(
        self,
        parameter: str,
        value: Any,
        expected: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"parameter": parameter, "value": value, "expected": expected})

        super().__init__(f"Invalid {parameter}: {value}. Expected: {expected}", full_context, original_error)
        self.parameter = parameter
        self.value = value
        self.expected = expected


class InvalidRangeError(ValidationError):
    """Raised when a numeric parameter is outside valid range"""

    def __init__(
        self,
        parameter: str,
        value: Union[int, float],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.parameter = parameter
        self.value = value
        self.min_value = min_value
        self.max_value = max_value

        full_context = context or {}
        full_context.update({"parameter": parameter, "value": value, "min_value": min_value, "max_value": max_value})

        if min_value is not None and max_value is not None:
            message = f"Invalid {parameter}: {value}. Must be between {min_value} and {max_value}"
        elif min_value is not None:
            message = f"Invalid {parameter}: {value}. Must be >= {min_value}"
        elif max_value is not None:
            message = f"Invalid {parameter}: {value}. Must be <= {max_value}"
        else:
            message = f"Invalid {parameter}: {value}"

        super().__init__(message, full_context, original_error)


class InvalidTypeError(ValidationError):
    """Raised when a parameter has an incorrect type"""

    def __init__(
        self,
        parameter: str,
        value: Any,
        expected_type: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update(
            {
                "parameter": parameter,
                "value": value,
                "received_type": type(value).__name__,
                "expected_type": expected_type,
            }
        )

        super().__init__(
            f"Invalid type for {parameter}: {type(value).__name__}. Expected: {expected_type}",
            full_context,
            original_error,
        )
        self.parameter = parameter
        self.value = value
        self.expected_type = expected_type


class TooManyItemsError(ValidationError):
    """Raised when too many items are provided for a list parameter"""

    def __init__(
        self,
        parameter: str,
        count: int,
        max_allowed: int,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"parameter": parameter, "count": count, "max_allowed": max_allowed})

        super().__init__(f"Too many {parameter}: {count}. Maximum allowed: {max_allowed}", full_context, original_error)
        self.parameter = parameter
        self.count = count
        self.max_allowed = max_allowed


class EmptyListError(ValidationError):
    """Raised when an empty list is provided where items are required"""

    def __init__(
        self, parameter: str, context: Optional[dict[str, Any]] = None, original_error: Optional[Exception] = None
    ):
        full_context = context or {}
        full_context.update({"parameter": parameter})

        super().__init__(f"Empty {parameter} list. At least one item is required", full_context, original_error)
        self.parameter = parameter


class InvalidFilterError(ValidationError):
    """Raised when filter configuration is invalid"""

    def __init__(
        self,
        message: str,
        filter_type: Optional[str] = None,
        invalid_parameters: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"filter_type": filter_type, "invalid_parameters": invalid_parameters or []})

        super().__init__(f"Invalid filter configuration: {message}", full_context, original_error)
        self.filter_type = filter_type
        self.invalid_parameters = invalid_parameters or []


class InvalidIntervalError(ValidationError):
    """Raised when polling interval is invalid"""

    def __init__(
        self,
        interval: float,
        min_interval: float = 0.1,
        max_interval: float = 3600.0,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"interval": interval, "min_interval": min_interval, "max_interval": max_interval})

        super().__init__(
            f"Invalid interval: {interval}s. Must be between {min_interval}s and {max_interval}s",
            full_context,
            original_error,
        )
        self.interval = interval
        self.min_interval = min_interval
        self.max_interval = max_interval


class InvalidCallbackError(ValidationError):
    """Raised when callback function is invalid"""

    def __init__(
        self,
        callback: Any,
        reason: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"callback_type": type(callback).__name__, "reason": reason})

        super().__init__(f"Invalid callback: {reason}", full_context, original_error)
        self.callback = callback
        self.reason = reason


class InvalidUrlError(ValidationError):
    """Raised when URL format is invalid"""

    def __init__(
        self,
        url: str,
        reason: str = "Invalid URL format",
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"url": url, "reason": reason})

        super().__init__(f"{reason}: '{url}'", full_context, original_error)
        self.url = url
        self.reason = reason


class RateLimitConfigError(ValidationError):
    """Raised when rate limit configuration is invalid"""

    def __init__(
        self, message: str, context: Optional[dict[str, Any]] = None, original_error: Optional[Exception] = None
    ):
        super().__init__(f"Invalid rate limit configuration: {message}", context, original_error)


class HttpClientConfigError(ValidationError):
    """Raised when HTTP client configuration is invalid"""

    def __init__(
        self, message: str, context: Optional[dict[str, Any]] = None, original_error: Optional[Exception] = None
    ):
        super().__init__(f"Invalid HTTP client configuration: {message}", context, original_error)


# =============================================================================
# API ERRORS
# =============================================================================


class APIError(DexscreenError):
    """
    Base class for all API-related errors.

    Use this to catch any API-related issue, including rate limits,
    authentication, and invalid responses.
    """

    pass


class RateLimitError(APIError):
    """
    Raised when API rate limits are exceeded.

    Attributes:
        retry_after: Number of seconds to wait before retrying (if known)
        limit_type: Type of rate limit ("requests_per_minute", "requests_per_second", etc.)
        current_count: Current number of requests made (if available)
        limit: Maximum allowed requests (if available)
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        limit_type: Optional[str] = None,
        current_count: Optional[int] = None,
        limit: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update(
            {"retry_after": retry_after, "limit_type": limit_type, "current_count": current_count, "limit": limit}
        )

        super().__init__(message, full_context, original_error)
        self.retry_after = retry_after
        self.limit_type = limit_type
        self.current_count = current_count
        self.limit = limit


class AuthenticationError(APIError):
    """Raised when API authentication fails"""

    pass


class InvalidResponseError(APIError):
    """
    Raised when the API returns an invalid or unexpected response.

    Attributes:
        response_data: The actual response data received
        expected_format: Description of what was expected
        status_code: HTTP status code (if available)
    """

    def __init__(
        self,
        message: str,
        response_data: Any = None,
        expected_format: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update(
            {"response_data": response_data, "expected_format": expected_format, "status_code": status_code}
        )

        super().__init__(message, full_context, original_error)
        self.response_data = response_data
        self.expected_format = expected_format
        self.status_code = status_code


class APILimitError(APIError):
    """
    Raised when API limits are exceeded (different from rate limiting).

    Attributes:
        limit_type: Type of limit exceeded ("max_addresses", "payload_size", etc.)
        current_value: Current value that exceeded the limit
        max_allowed: Maximum allowed value
    """

    def __init__(
        self,
        message: str,
        limit_type: Optional[str] = None,
        current_value: Optional[Union[int, float]] = None,
        max_allowed: Optional[Union[int, float]] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"limit_type": limit_type, "current_value": current_value, "max_allowed": max_allowed})

        super().__init__(message, full_context, original_error)
        self.limit_type = limit_type
        self.current_value = current_value
        self.max_allowed = max_allowed


class ServerError(APIError):
    """
    Raised when the API server encounters an internal error.

    Attributes:
        status_code: HTTP status code
        retry_recommended: Whether retrying the request is recommended
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_recommended: bool = True,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"status_code": status_code, "retry_recommended": retry_recommended})

        super().__init__(message, full_context, original_error)
        self.status_code = status_code
        self.retry_recommended = retry_recommended


# =============================================================================
# HTTP CLIENT EXCEPTIONS (Enhanced Backward Compatible)
# =============================================================================


class HttpError(DexscreenError):
    """Base exception for HTTP-related errors"""

    pass


class HttpRequestError(HttpError):
    """Raised when an HTTP request fails"""

    def __init__(
        self,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        full_context = context or {}
        full_context.update({"method": method, "url": url, "status_code": status_code, "response_text": response_text})

        # Build error message
        message = f"HTTP {method} request to '{url}' failed"
        if status_code:
            message += f" with status {status_code}"
        if response_text and len(response_text) < 200:
            message += f": {response_text}"
        if original_error:
            message += f" (original error: {type(original_error).__name__}: {original_error})"

        super().__init__(message, full_context, original_error)
        self.method = method
        self.url = url
        self.status_code = status_code
        self.response_text = response_text


class HttpTimeoutError(HttpError):
    """Raised when an HTTP request times out"""

    def __init__(
        self,
        method: str,
        url: str,
        timeout: float,
        original_error: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        full_context = context or {}
        full_context.update({"method": method, "url": url, "timeout": timeout})

        message = f"HTTP {method} request to '{url}' timed out after {timeout}s"
        if original_error:
            message += f" (original error: {type(original_error).__name__}: {original_error})"

        super().__init__(message, full_context, original_error)
        self.method = method
        self.url = url
        self.timeout = timeout


class HttpConnectionError(HttpError):
    """Raised when unable to establish HTTP connection"""

    def __init__(
        self,
        method: str,
        url: str,
        original_error: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        full_context = context or {}
        full_context.update({"method": method, "url": url})

        message = f"Failed to connect for HTTP {method} request to '{url}'"
        if original_error:
            message += f" (original error: {type(original_error).__name__}: {original_error})"

        super().__init__(message, full_context, original_error)
        self.method = method
        self.url = url


class HttpResponseParsingError(HttpError):
    """Raised when unable to parse HTTP response (e.g., invalid JSON)"""

    def __init__(
        self,
        method: str,
        url: str,
        content_type: Optional[str] = None,
        response_content: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        full_context = context or {}
        full_context.update(
            {"method": method, "url": url, "content_type": content_type, "response_content": response_content}
        )

        message = f"Failed to parse response from HTTP {method} request to '{url}'"
        if content_type:
            message += f" (content-type: {content_type})"
        if original_error:
            message += f" (original error: {type(original_error).__name__}: {original_error})"

        super().__init__(message, full_context, original_error)
        self.method = method
        self.url = url
        self.content_type = content_type
        self.response_content = response_content


class HttpSessionError(HttpError):
    """Raised when HTTP session creation or management fails"""

    def __init__(
        self, message: str, original_error: Optional[Exception] = None, context: Optional[dict[str, Any]] = None
    ):
        full_context = context or {}

        if original_error:
            message += f" (original error: {type(original_error).__name__}: {original_error})"

        super().__init__(message, full_context, original_error)


# =============================================================================
# NETWORK ERRORS
# =============================================================================


class NetworkError(DexscreenError):
    """Base class for all network-related errors"""

    pass


class ConnectionError(NetworkError):
    """
    Raised when connection to the API server fails.

    Attributes:
        endpoint: The endpoint that failed to connect
        timeout: Connection timeout value (if applicable)
    """

    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"endpoint": endpoint, "timeout": timeout})

        super().__init__(message, full_context, original_error)
        self.endpoint = endpoint
        self.timeout = timeout


class TimeoutError(NetworkError):
    """
    Raised when a request times out.

    Attributes:
        timeout_duration: How long the request waited before timing out
        operation_type: Type of operation that timed out ("request", "connection", etc.)
    """

    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"timeout_duration": timeout_duration, "operation_type": operation_type})

        super().__init__(message, full_context, original_error)
        self.timeout_duration = timeout_duration
        self.operation_type = operation_type


class ProxyError(NetworkError):
    """
    Raised when proxy-related errors occur.

    Attributes:
        proxy_url: The proxy URL that caused the error
        proxy_type: Type of proxy ("http", "socks5", etc.)
    """

    def __init__(
        self,
        message: str,
        proxy_url: Optional[str] = None,
        proxy_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"proxy_url": proxy_url, "proxy_type": proxy_type})

        super().__init__(message, full_context, original_error)
        self.proxy_url = proxy_url
        self.proxy_type = proxy_type


# =============================================================================
# DATA VALIDATION ERRORS (Additional)
# =============================================================================


class DataFormatError(ValidationError):
    """
    Raised when data doesn't match expected format.

    Attributes:
        field_name: Name of the field with invalid format
        received_value: The actual value received
        expected_type: Expected data type or format
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        received_value: Any = None,
        expected_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update(
            {"field_name": field_name, "received_value": received_value, "expected_type": expected_type}
        )

        super().__init__(message, full_context, original_error)
        self.field_name = field_name
        self.received_value = received_value
        self.expected_type = expected_type


class MissingDataError(ValidationError):
    """
    Raised when required data is missing.

    Attributes:
        missing_fields: List of missing required fields
        data_source: Source of the data ("api_response", "user_input", etc.)
    """

    def __init__(
        self,
        message: str,
        missing_fields: Optional[list[str]] = None,
        data_source: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"missing_fields": missing_fields or [], "data_source": data_source})

        super().__init__(message, full_context, original_error)
        self.missing_fields = missing_fields or []
        self.data_source = data_source


# =============================================================================
# STREAMING ERRORS
# =============================================================================


class StreamError(DexscreenError):
    """Base class for all streaming/WebSocket-related errors"""

    pass


class StreamConnectionError(StreamError):
    """
    Raised when WebSocket/streaming connection fails.

    Attributes:
        stream_url: The streaming endpoint URL
        reconnect_attempts: Number of reconnection attempts made
        max_reconnect_attempts: Maximum allowed reconnection attempts
    """

    def __init__(
        self,
        message: str,
        stream_url: Optional[str] = None,
        reconnect_attempts: Optional[int] = None,
        max_reconnect_attempts: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update(
            {
                "stream_url": stream_url,
                "reconnect_attempts": reconnect_attempts,
                "max_reconnect_attempts": max_reconnect_attempts,
            }
        )

        super().__init__(message, full_context, original_error)
        self.stream_url = stream_url
        self.reconnect_attempts = reconnect_attempts
        self.max_reconnect_attempts = max_reconnect_attempts


class StreamTimeoutError(StreamError):
    """
    Raised when streaming operations timeout.

    Attributes:
        timeout_duration: How long the operation waited before timing out
        operation: The operation that timed out ("subscribe", "unsubscribe", "message", etc.)
    """

    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"timeout_duration": timeout_duration, "operation": operation})

        super().__init__(message, full_context, original_error)
        self.timeout_duration = timeout_duration
        self.operation = operation


class SubscriptionError(StreamError):
    """
    Raised when subscription operations fail.

    Attributes:
        subscription_id: ID of the failed subscription
        subscription_type: Type of subscription ("pair", "token", etc.)
        operation: The operation that failed ("subscribe", "unsubscribe", "update", etc.)
    """

    def __init__(
        self,
        message: str,
        subscription_id: Optional[str] = None,
        subscription_type: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update(
            {"subscription_id": subscription_id, "subscription_type": subscription_type, "operation": operation}
        )

        super().__init__(message, full_context, original_error)
        self.subscription_id = subscription_id
        self.subscription_type = subscription_type
        self.operation = operation


class StreamDataError(StreamError):
    """
    Raised when streaming data is invalid or corrupted.

    Attributes:
        data_type: Type of data that was invalid ("pair_update", "token_data", etc.)
        raw_data: The raw data that caused the error
    """

    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        raw_data: Any = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"data_type": data_type, "raw_data": raw_data})

        super().__init__(message, full_context, original_error)
        self.data_type = data_type
        self.raw_data = raw_data


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================


class ConfigurationError(DexscreenError):
    """Base class for all configuration-related errors"""

    pass


class InvalidConfigError(ConfigurationError):
    """
    Raised when configuration parameters are invalid.

    Attributes:
        config_key: The configuration key that's invalid
        config_value: The invalid configuration value
        expected_values: List of expected/valid values (if applicable)
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Any = None,
        expected_values: Optional[list] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update(
            {"config_key": config_key, "config_value": config_value, "expected_values": expected_values}
        )

        super().__init__(message, full_context, original_error)
        self.config_key = config_key
        self.config_value = config_value
        self.expected_values = expected_values


class MissingConfigError(ConfigurationError):
    """
    Raised when required configuration is missing.

    Attributes:
        required_configs: List of missing required configuration keys
        config_source: Source where config should be provided ("env", "kwargs", "file", etc.)
    """

    def __init__(
        self,
        message: str,
        required_configs: Optional[list[str]] = None,
        config_source: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"required_configs": required_configs or [], "config_source": config_source})

        super().__init__(message, full_context, original_error)
        self.required_configs = required_configs or []
        self.config_source = config_source


class FilterConfigError(ConfigurationError):
    """
    Raised when filter configuration is invalid.

    This is an alias for InvalidFilterError for better categorization.
    """

    def __init__(
        self,
        message: str,
        filter_type: Optional[str] = None,
        invalid_parameters: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        full_context = context or {}
        full_context.update({"filter_type": filter_type, "invalid_parameters": invalid_parameters or []})

        super().__init__(f"Invalid filter configuration: {message}", full_context, original_error)
        self.filter_type = filter_type
        self.invalid_parameters = invalid_parameters or []


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error suggests that retrying might succeed
    """
    retryable_types = (
        TimeoutError,
        ConnectionError,
        ServerError,
        StreamConnectionError,
        StreamTimeoutError,
        HttpTimeoutError,
        HttpConnectionError,
    )

    if isinstance(error, retryable_types):
        return True

    if isinstance(error, ServerError) and error.retry_recommended:
        return True

    return isinstance(error, RateLimitError)  # Can retry after waiting


def should_wait_before_retry(error: Exception) -> Optional[float]:
    """
    Get recommended wait time before retrying an error.

    Args:
        error: The exception to check

    Returns:
        Number of seconds to wait, or None if no specific wait time is recommended
    """
    if isinstance(error, RateLimitError) and error.retry_after:
        return error.retry_after

    if isinstance(error, (TimeoutError, HttpTimeoutError)):
        return 1.0  # Short wait for timeouts

    if isinstance(error, (ConnectionError, HttpConnectionError)):
        return 2.0  # Longer wait for connection issues

    if isinstance(error, ServerError):
        return 5.0  # Even longer wait for server errors

    return None


def get_error_category(error: Exception) -> str:
    """
    Get the category of an error for monitoring/logging purposes.

    Args:
        error: The exception to categorize

    Returns:
        String category of the error
    """
    if isinstance(error, APIError):
        return "api"
    elif isinstance(error, NetworkError):
        return "network"
    elif isinstance(error, ValidationError):
        return "validation"
    elif isinstance(error, StreamError):
        return "streaming"
    elif isinstance(error, ConfigurationError):
        return "configuration"
    elif isinstance(error, HttpError):
        return "http"
    elif isinstance(error, DexscreenError):
        return "dexscreen"
    else:
        return "unknown"
