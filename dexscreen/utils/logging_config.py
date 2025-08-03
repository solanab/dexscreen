"""
Enhanced logging utilities with correlation ID support and structured logging
"""

import logging
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import orjson

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class StructuredFormatter(logging.Formatter):
    """
    Structured logging formatter that includes correlation IDs and context
    """

    def __init__(self, include_correlation_id: bool = True, include_context: bool = True):
        """
        Initialize structured formatter.

        Args:
            include_correlation_id: Whether to include correlation ID in logs
            include_context: Whether to include additional context in logs
        """
        super().__init__()
        self.include_correlation_id = include_correlation_id
        self.include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data"""
        # Base log data
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if available
        if self.include_correlation_id:
            correlation_id = correlation_id_context.get()
            if correlation_id:
                log_data["correlation_id"] = correlation_id

        # Add thread/process info for debugging
        if record.thread:
            log_data["thread_id"] = record.thread
        if record.process:
            log_data["process_id"] = record.process

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra context from the log record
        if self.include_context and hasattr(record, "context"):
            log_data["context"] = record.context  # type: ignore[attr-defined]

        # Add any extra fields that were passed to the logger
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
                "context",
            }
        }
        if extra_fields:
            log_data["extra"] = extra_fields

        # Serialize to JSON for structured logging
        try:
            return orjson.dumps(log_data, option=orjson.OPT_APPEND_NEWLINE).decode()
        except (TypeError, ValueError):
            # Fallback to string representation if JSON serialization fails
            return str(log_data)


class ContextualLogger:
    """
    Logger wrapper that automatically includes context and correlation IDs
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize contextual logger.

        Args:
            logger: The underlying logger instance
        """
        self.logger = logger

    def _log_with_context(self, level: int, msg: str, *args, context: Optional[dict[str, Any]] = None, **kwargs):
        """Log message with context"""
        if context:
            # Add context as extra data to the log record
            extra = kwargs.get("extra", {})
            extra["context"] = context
            kwargs["extra"] = extra

        self.logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, context: Optional[dict[str, Any]] = None, **kwargs):
        """Log debug message with context"""
        self._log_with_context(logging.DEBUG, msg, *args, context=context, **kwargs)

    def info(self, msg: str, *args, context: Optional[dict[str, Any]] = None, **kwargs):
        """Log info message with context"""
        self._log_with_context(logging.INFO, msg, *args, context=context, **kwargs)

    def warning(self, msg: str, *args, context: Optional[dict[str, Any]] = None, **kwargs):
        """Log warning message with context"""
        self._log_with_context(logging.WARNING, msg, *args, context=context, **kwargs)

    def error(self, msg: str, *args, context: Optional[dict[str, Any]] = None, **kwargs):
        """Log error message with context"""
        self._log_with_context(logging.ERROR, msg, *args, context=context, **kwargs)

    def critical(self, msg: str, *args, context: Optional[dict[str, Any]] = None, **kwargs):
        """Log critical message with context"""
        self._log_with_context(logging.CRITICAL, msg, *args, context=context, **kwargs)

    def exception(self, msg: str, *args, context: Optional[dict[str, Any]] = None, **kwargs):
        """Log exception message with context"""
        kwargs["exc_info"] = True
        self._log_with_context(logging.ERROR, msg, *args, context=context, **kwargs)


def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context"""
    correlation_id_context.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context"""
    return correlation_id_context.get()


def with_correlation_id(correlation_id: Optional[str] = None) -> Callable[[F], F]:
    """
    Decorator to automatically set correlation ID for function execution.

    Args:
        correlation_id: Specific correlation ID to use, or None to generate one

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate or use provided correlation ID
            corr_id = correlation_id or generate_correlation_id()

            # Set correlation ID in context
            token = correlation_id_context.set(corr_id)
            try:
                return func(*args, **kwargs)
            finally:
                # Reset correlation ID context
                correlation_id_context.reset(token)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate or use provided correlation ID
            corr_id = correlation_id or generate_correlation_id()

            # Set correlation ID in context
            token = correlation_id_context.set(corr_id)
            try:
                return await func(*args, **kwargs)
            finally:
                # Reset correlation ID context
                correlation_id_context.reset(token)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return wrapper  # type: ignore

    return decorator


def setup_structured_logging(
    level: int = logging.INFO,
    use_structured_format: bool = True,
    include_correlation_id: bool = True,
    include_context: bool = True,
) -> None:
    """
    Setup structured logging for the entire application.

    Args:
        level: Logging level
        use_structured_format: Whether to use structured JSON format
        include_correlation_id: Whether to include correlation IDs
        include_context: Whether to include context in logs
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Set formatter
    if use_structured_format:
        formatter = StructuredFormatter(include_correlation_id=include_correlation_id, include_context=include_context)
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_contextual_logger(name: str) -> ContextualLogger:
    """
    Get a contextual logger for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Contextual logger instance
    """
    logger = logging.getLogger(name)
    return ContextualLogger(logger)


def log_function_call(
    logger: Optional[ContextualLogger] = None,
    log_args: bool = False,
    log_result: bool = False,
    log_level: int = logging.DEBUG,
    mask_sensitive: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to log function calls with context.

    Args:
        logger: Logger to use (defaults to logger for function's module)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        log_level: Logging level to use
        mask_sensitive: Whether to mask sensitive data in logs

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        # Get logger if not provided
        func_logger = logger or get_contextual_logger(func.__module__)

        @wraps(func)
        def wrapper(*args, **kwargs):
            function_name = func.__name__
            context: dict[str, Any] = {"function": function_name, "module": func.__module__}

            # Log function arguments if requested
            if log_args:
                safe_args = _mask_sensitive_data(args) if mask_sensitive else args
                safe_kwargs = _mask_sensitive_data(kwargs) if mask_sensitive else kwargs
                context["args"] = safe_args
                context["kwargs"] = safe_kwargs

            func_logger._log_with_context(log_level, "Function %s called", function_name, context=context)

            try:
                result = func(*args, **kwargs)

                # Log result if requested
                if log_result:
                    safe_result = _mask_sensitive_data(result) if mask_sensitive else result
                    context["result"] = safe_result

                func_logger._log_with_context(
                    log_level, "Function %s completed successfully", function_name, context=context
                )

                return result

            except Exception as e:
                error_context = context.copy()
                error_context.update({"error_type": type(e).__name__, "error_message": str(e)})

                func_logger._log_with_context(
                    logging.ERROR,
                    "Function %s failed with %s: %s",
                    function_name,
                    type(e).__name__,
                    str(e),
                    context=error_context,
                    exc_info=True,
                )
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            function_name = func.__name__
            context: dict[str, Any] = {"function": function_name, "module": func.__module__}

            # Log function arguments if requested
            if log_args:
                safe_args = _mask_sensitive_data(args) if mask_sensitive else args
                safe_kwargs = _mask_sensitive_data(kwargs) if mask_sensitive else kwargs
                context["args"] = safe_args
                context["kwargs"] = safe_kwargs

            func_logger._log_with_context(log_level, "Async function %s called", function_name, context=context)

            try:
                result = await func(*args, **kwargs)

                # Log result if requested
                if log_result:
                    safe_result = _mask_sensitive_data(result) if mask_sensitive else result
                    context["result"] = safe_result

                func_logger._log_with_context(
                    log_level, "Async function %s completed successfully", function_name, context=context
                )

                return result

            except Exception as e:
                error_context = context.copy()
                error_context.update({"error_type": type(e).__name__, "error_message": str(e)})

                func_logger._log_with_context(
                    logging.ERROR,
                    "Async function %s failed with %s: %s",
                    function_name,
                    type(e).__name__,
                    str(e),
                    context=error_context,
                    exc_info=True,
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return wrapper  # type: ignore

    return decorator


def _mask_sensitive_data(data: Any) -> Any:
    """
    Mask sensitive data in logs to prevent credential leakage.

    Args:
        data: Data to mask

    Returns:
        Masked data
    """
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if any(
                sensitive in key.lower() for sensitive in ["password", "token", "secret", "key", "auth", "credential"]
            ):
                masked[key] = "***MASKED***"
            else:
                masked[key] = _mask_sensitive_data(value)
        return masked
    elif isinstance(data, (list, tuple)):
        return type(data)(_mask_sensitive_data(item) for item in data)
    elif isinstance(data, str) and len(data) > 20:
        # Mask long strings that might contain tokens
        return f"{data[:8]}***MASKED***{data[-4:]}"
    else:
        return data
