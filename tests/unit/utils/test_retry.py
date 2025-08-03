"""
Tests for retry functionality
"""

import time
from unittest.mock import AsyncMock

import pytest

from dexscreen.utils.retry import (
    RetryConfig,
    RetryError,
    RetryManager,
    RetryPresets,
    calculate_delay,
    is_retryable,
    retry_async,
    retry_sync,
)


class TestRetryConfig:
    """Test retry configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True
        assert 429 in config.retryable_status_codes
        # Test that ConnectionError and OSError are in retryable exceptions
        assert ConnectionError in config.retryable_exceptions
        assert OSError in config.retryable_exceptions

    def test_custom_config(self):
        """Test custom configuration"""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            backoff_factor=1.5,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.backoff_factor == 1.5
        assert config.jitter is False

    def test_validation(self):
        """Test configuration validation"""
        # Test invalid values
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            RetryConfig(max_retries=-1)

        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryConfig(base_delay=0)

        with pytest.raises(ValueError, match="max_delay must be positive"):
            RetryConfig(max_delay=-1)

        with pytest.raises(ValueError, match="backoff_factor must be greater than 1"):
            RetryConfig(backoff_factor=1.0)


class TestCalculateDelay:
    """Test delay calculation"""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=10.0, jitter=False)

        delay0 = calculate_delay(0, config)
        delay1 = calculate_delay(1, config)
        delay2 = calculate_delay(2, config)

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

    def test_max_delay_cap(self):
        """Test max delay cap"""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=3.0, jitter=False)

        delay_large = calculate_delay(10, config)
        assert delay_large == 3.0

    def test_jitter(self):
        """Test jitter adds randomness"""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=10.0, jitter=True)

        # With jitter, delays should vary
        delays = [calculate_delay(1, config) for _ in range(10)]
        assert len(set(delays)) > 1  # Should have variation


class TestIsRetryable:
    """Test retryable condition checking"""

    def test_retryable_exceptions(self):
        """Test retryable exception types"""
        config = RetryConfig()

        assert is_retryable(ConnectionError("Connection failed"), config)
        assert is_retryable(TimeoutError("Request timed out"), config)
        assert is_retryable(OSError("Network error"), config)

    def test_non_retryable_exceptions(self):
        """Test non-retryable exception types"""
        config = RetryConfig()

        assert not is_retryable(ValueError("Invalid value"), config)
        assert not is_retryable(KeyError("Missing key"), config)

    def test_http_status_codes(self):
        """Test HTTP status code checking"""
        config = RetryConfig()

        # Mock response with retryable status
        class MockResponse:
            def __init__(self, status_code):
                self.status_code = status_code

        class MockError(Exception):
            def __init__(self, status_code):
                self.response = MockResponse(status_code)

        assert is_retryable(MockError(429), config)  # Too Many Requests
        assert is_retryable(MockError(500), config)  # Internal Server Error
        assert is_retryable(MockError(502), config)  # Bad Gateway
        assert not is_retryable(MockError(404), config)  # Not Found
        assert not is_retryable(MockError(400), config)  # Bad Request


class TestRetrySync:
    """Test synchronous retry decorator"""

    def test_success_on_first_try(self):
        """Test successful function on first attempt"""
        call_count = 0

        @retry_sync(RetryConfig(max_retries=3))
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_success_after_retries(self):
        """Test successful function after retries"""
        call_count = 0

        @retry_sync(RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = eventually_successful()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test function that fails after max retries"""
        call_count = 0

        @retry_sync(RetryConfig(max_retries=2, base_delay=0.01))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            always_fails()

        assert call_count == 3  # Original + 2 retries
        assert "failed after 3 attempts" in str(exc_info.value)
        assert isinstance(exc_info.value.original_exception, ConnectionError)

    def test_non_retryable_error(self):
        """Test non-retryable error is not retried"""
        call_count = 0

        @retry_sync(RetryConfig(max_retries=3))
        def non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(RetryError):
            non_retryable_error()

        assert call_count == 1  # No retries for non-retryable error


class TestRetryAsync:
    """Test asynchronous retry decorator"""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Test successful async function on first attempt"""
        call_count = 0

        @retry_async(RetryConfig(max_retries=3))
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test successful async function after retries"""
        call_count = 0

        @retry_async(RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
        async def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = await eventually_successful()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test async function that fails after max retries"""
        call_count = 0

        @retry_async(RetryConfig(max_retries=2, base_delay=0.01))
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            await always_fails()

        assert call_count == 3  # Original + 2 retries
        assert "failed after 3 attempts" in str(exc_info.value)


class TestRetryManager:
    """Test retry manager"""

    def test_should_retry(self):
        """Test retry decision logic"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        # Initially should not retry (no attempts made)
        assert manager.attempt == 0

        # First failure - should retry
        manager.record_failure(ConnectionError("Network error"))
        assert manager.attempt == 1
        assert manager.should_retry(ConnectionError("Network error"))

        # More failures within limit
        manager.record_failure(ConnectionError("Network error"))
        assert manager.attempt == 2
        assert manager.should_retry(ConnectionError("Network error"))

        manager.record_failure(ConnectionError("Network error"))
        assert manager.attempt == 3
        assert not manager.should_retry(ConnectionError("Network error"))  # Now at max_retries, can't retry

        # Exceeded max retries
        manager.record_failure(ConnectionError("Network error"))
        assert manager.attempt == 4
        assert not manager.should_retry(ConnectionError("Network error"))

    def test_non_retryable_error(self):
        """Test non-retryable errors"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        manager.record_failure(ValueError("Not retryable"))
        assert not manager.should_retry(ValueError("Not retryable"))

    def test_calculate_delay(self):
        """Test delay calculation"""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, jitter=False)
        manager = RetryManager(config)

        manager.record_failure(ConnectionError("Error"))
        delay = manager.calculate_delay()
        assert delay == 1.0  # First retry delay

    @pytest.mark.asyncio
    async def test_wait_async(self):
        """Test async wait"""
        config = RetryConfig(base_delay=0.01, jitter=False)
        manager = RetryManager(config)

        manager.record_failure(ConnectionError("Error"))

        start_time = time.time()
        await manager.wait_async()
        elapsed = time.time() - start_time

        # Should wait approximately the calculated delay
        assert 0.005 <= elapsed <= 0.05  # Allow some tolerance

    def test_wait_sync(self):
        """Test sync wait"""
        config = RetryConfig(base_delay=0.01, jitter=False)
        manager = RetryManager(config)

        manager.record_failure(ConnectionError("Error"))

        start_time = time.time()
        manager.wait_sync()
        elapsed = time.time() - start_time

        # Should wait approximately the calculated delay
        assert 0.005 <= elapsed <= 0.05  # Allow some tolerance

    def test_raise_if_exhausted(self):
        """Test raising error when retries exhausted"""
        config = RetryConfig(max_retries=1)
        manager = RetryManager(config)

        manager.record_failure(ConnectionError("Error"))
        manager.record_failure(ConnectionError("Error"))

        with pytest.raises(RetryError) as exc_info:
            manager.raise_if_exhausted("Test operation")

        assert "Test operation failed after 2 attempts" in str(exc_info.value)


class TestRetryPresets:
    """Test retry presets"""

    def test_network_operations(self):
        """Test network operations preset"""
        config = RetryPresets.network_operations()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_factor == 2.0

    def test_api_calls(self):
        """Test API calls preset"""
        config = RetryPresets.api_calls()
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.backoff_factor == 1.5

    def test_aggressive(self):
        """Test aggressive preset"""
        config = RetryPresets.aggressive()
        assert config.max_retries == 10
        assert config.base_delay == 0.1
        assert config.max_delay == 120.0
        assert config.backoff_factor == 1.8

    def test_rate_limit_heavy(self):
        """Test rate limit heavy preset"""
        config = RetryPresets.rate_limit_heavy()
        assert config.max_retries == 8
        assert config.base_delay == 2.0
        assert config.max_delay == 300.0
        assert config.backoff_factor == 2.5
        assert 429 in config.retryable_status_codes


class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_http_client_retry_integration(self):
        """Test retry integration with HTTP client"""
        from dexscreen.core.http import HttpClientCffi
        from dexscreen.utils.retry import RetryPresets

        # Create client with aggressive retry config
        client = HttpClientCffi(calls=10, period=60, retry_config=RetryPresets.network_operations())

        # Verify retry config is set
        assert client.retry_config.max_retries == 3
        assert client.retry_config.base_delay == 1.0

        # Test updating retry config
        new_config = RetryPresets.aggressive()
        client.update_retry_config(new_config)
        assert client.retry_config.max_retries == 10

        await client.close()

    @pytest.mark.asyncio
    async def test_polling_stream_retry_integration(self):
        """Test retry integration with polling stream"""
        from dexscreen.stream.polling import PollingStream
        from dexscreen.utils.retry import RetryPresets

        # Mock client
        mock_client = AsyncMock()

        # Create polling stream with retry config
        stream = PollingStream(mock_client, interval=1.0, retry_config=RetryPresets.api_calls())

        # Verify retry config is set
        assert stream.retry_config.max_retries == 5
        assert stream.retry_config.base_delay == 0.5

        await stream.close()
