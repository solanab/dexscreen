"""
Dexscreen - Python SDK for DexScreener API

A modern, stable, and reliable Python SDK for DexScreener API with HTTP support.
"""

from .api.client import DexscreenerClient
from .core.exceptions import (
    # API errors
    APIError,
    APILimitError,
    AuthenticationError,
    # Configuration errors
    ConfigurationError,
    ConnectionError,
    DataFormatError,
    # Base exceptions
    DexscreenError,
    FilterConfigError,
    HttpConnectionError,
    # HTTP errors
    HttpError,
    HttpRequestError,
    HttpResponseParsingError,
    HttpSessionError,
    HttpTimeoutError,
    InvalidAddressError,
    InvalidChainError,
    InvalidConfigError,
    InvalidResponseError,
    MissingConfigError,
    MissingDataError,
    # Network errors
    NetworkError,
    ProxyError,
    RateLimitError,
    ServerError,
    StreamConnectionError,
    StreamDataError,
    # Streaming errors
    StreamError,
    StreamTimeoutError,
    SubscriptionError,
    TimeoutError,
    # Validation errors
    ValidationError,
    # Utility functions
    get_error_category,
    is_retryable_error,
    should_wait_before_retry,
)
from .core.models import (
    BaseToken,
    Liquidity,
    PairTransactionCounts,
    PriceChangePeriods,
    TokenPair,
    TransactionCount,
    VolumeChangePeriods,
)
from .utils.filters import FilterConfig, FilterPresets

__version__ = "1.0.0"
__all__ = [
    # API errors
    "APIError",
    "APILimitError",
    "AuthenticationError",
    # Core models and client
    "BaseToken",
    # Configuration errors
    "ConfigurationError",
    "ConnectionError",
    "DataFormatError",
    # Base exceptions
    "DexscreenError",
    "DexscreenerClient",
    "FilterConfig",
    "FilterConfigError",
    "FilterPresets",
    "HttpConnectionError",
    # HTTP errors
    "HttpError",
    "HttpRequestError",
    "HttpResponseParsingError",
    "HttpSessionError",
    "HttpTimeoutError",
    "InvalidAddressError",
    "InvalidChainError",
    "InvalidConfigError",
    "InvalidResponseError",
    "Liquidity",
    "MissingConfigError",
    "MissingDataError",
    # Network errors
    "NetworkError",
    "PairTransactionCounts",
    "PriceChangePeriods",
    "ProxyError",
    "RateLimitError",
    "ServerError",
    "StreamConnectionError",
    "StreamDataError",
    # Streaming errors
    "StreamError",
    "StreamTimeoutError",
    "SubscriptionError",
    "TimeoutError",
    "TokenPair",
    "TransactionCount",
    # Validation errors
    "ValidationError",
    "VolumeChangePeriods",
    # Utility functions
    "get_error_category",
    "is_retryable_error",
    "should_wait_before_retry",
]
