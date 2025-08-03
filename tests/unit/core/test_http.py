"""
Test HTTP client functionality
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen.core.exceptions import (
    HttpConnectionError,
    HttpResponseParsingError,
    HttpSessionError,
    HttpTimeoutError,
)
from dexscreen.core.http import HttpClientCffi


class TestHttpClientCffi:
    """Test HttpClientCffi class"""

    def test_client_initialization(self):
        """Test client initialization"""
        client = HttpClientCffi(calls=60, period=60)

        assert client.base_url == "https://api.dexscreener.com/"
        assert hasattr(client, "_limiter")

    def test_client_with_custom_config(self):
        """Test custom configuration"""
        custom_kwargs = {"timeout": 30, "impersonate": "chrome120", "verify": False}

        client = HttpClientCffi(calls=100, period=60, base_url="https://custom.api.com", client_kwargs=custom_kwargs)

        assert client.base_url == "https://custom.api.com"
        assert client.client_kwargs["timeout"] == 30
        assert client.client_kwargs["impersonate"] == "chrome120"
        assert client.client_kwargs["verify"] is False

    @patch("dexscreen.utils.browser_selector.get_random_browser", return_value="chrome")
    @patch("dexscreen.core.http.Session")
    def test_sync_request(self, mock_session_class, mock_browser, mock_http_session):
        """Test synchronous request"""
        # Set specific response
        mock_response = Mock()
        mock_response.content = b'{"pair": {"priceUsd": "100.0"}}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.status_code = 200
        mock_http_session.request.return_value = mock_response
        mock_session_class.return_value = mock_http_session

        # Create client and send request
        client = HttpClientCffi(calls=60, period=60)
        result = client.request("GET", "dex/pairs/ethereum/0x123")
        # Verify call
        assert result == {"pair": {"priceUsd": "100.0"}}
        mock_http_session.request.assert_called_once()
        call_args = mock_http_session.request.call_args
        assert call_args[0][0] == "GET"
        assert "https://api.dexscreener.com/dex/pairs/ethereum/0x123" in call_args[0][1]

    @patch("dexscreen.core.http.Session")
    def test_sync_request_with_params(self, mock_session_class, mock_http_session):
        """Test synchronous request with parameters"""
        mock_response = Mock()
        mock_response.content = b'{"results": []}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_http_session.request.return_value = mock_response
        mock_session_class.return_value = mock_http_session

        client = HttpClientCffi(calls=60, period=60)
        params = {"q": "USDC", "limit": 10}
        client.request("GET", "dex/search", params=params)

        # Verify parameter passing
        call_kwargs = mock_http_session.request.call_args[1]
        assert call_kwargs.get("params") == params

    @patch("dexscreen.core.http.Session")
    @patch("time.sleep")
    def test_sync_request_rate_limit(self, mock_sleep, mock_session_class):
        """Test synchronous request rate limiting"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b'{"data": "test"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create client, set a very low rate limit
        client = HttpClientCffi(calls=1, period=60)

        # The first request should succeed
        result1 = client.request("GET", "test")
        assert result1 == {"data": "test"}

        # The second request should trigger a delay (not an exception)
        result2 = client.request("GET", "test")
        assert result2 == {"data": "test"}
        # Verify that sleep was called (rate limiting)
        mock_sleep.assert_called()

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_async_request(self, mock_async_session_class):
        """Test asynchronous request"""
        # Set mock
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        # Set content for orjson parsing
        mock_response.content = b'{"pair": {"priceUsd": "200.0"}}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_async_session_class.return_value = mock_session
        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.raise_for_status = AsyncMock()
        mock_session.get.return_value = mock_warmup_response

        # Create client and send asynchronous request
        client = HttpClientCffi(calls=60, period=60)
        result = await client.request_async("GET", "dex/pairs/ethereum/0x4567890123456789012345678901234567890123")

        # Verify call
        assert result == {"pair": {"priceUsd": "200.0"}}
        mock_session.request.assert_called_once()

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_async_request_error_handling(self, mock_async_session_class):
        """Test asynchronous request error handling - now raises exceptions"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = Exception("Network error")
        mock_async_session_class.return_value = mock_session
        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.raise_for_status = AsyncMock()
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)

        # Now raises HttpConnectionError instead of returning None (since "Network error" matches connection pattern)
        with pytest.raises(HttpConnectionError) as exc_info:
            await client.request_async("GET", "test")

        assert "Network error" in str(exc_info.value)
        assert exc_info.value.method == "GET"
        assert "test" in exc_info.value.url

    @pytest.mark.asyncio
    async def test_async_request_concurrent(self):
        """Test concurrent asynchronous requests"""
        with patch("dexscreen.core.http.AsyncSession") as mock_async_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()

            # Simulate delayed response
            async def delayed_response(*args, **kwargs):
                await asyncio.sleep(0.1)
                return mock_response

            # Set content for orjson parsing
            mock_response.content = b'{"data": "concurrent"}'
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_session.request.side_effect = delayed_response

            # Mock warmup response
            mock_warmup_response = AsyncMock()
            mock_warmup_response.raise_for_status = AsyncMock()
            mock_session.get.return_value = mock_warmup_response

            mock_async_session_class.return_value = mock_session

            client = HttpClientCffi(calls=60, period=60)

            # Send multiple requests concurrently
            tasks = [client.request_async("GET", f"test/{i}") for i in range(5)]

            results = await asyncio.gather(*tasks)

            # Verify all requests succeeded
            assert len(results) == 5
            assert all(r == {"data": "concurrent"} for r in results)
            assert mock_session.request.call_count == 5

    def test_browser_impersonation(self):
        """Test browser impersonation functionality"""
        # Test different browser impersonation options
        browsers = ["chrome136", "firefox135", "safari184", "chrome131"]

        for browser in browsers:
            client = HttpClientCffi(calls=60, period=60, client_kwargs={"impersonate": browser})
            assert client.client_kwargs["impersonate"] == browser

    @patch("dexscreen.core.http.Session")
    def test_request_headers(self, mock_session_class):
        """Test request header setting"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b'{"success": true}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Custom headers
        custom_headers = {"User-Agent": "CustomBot/1.0", "X-Custom-Header": "test-value"}

        client = HttpClientCffi(calls=60, period=60, client_kwargs={"headers": custom_headers})

        client.request("GET", "test")

        # Session is created with client_kwargs which includes headers

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_http_timeout_error(self, mock_async_session_class):
        """Test HTTP timeout error handling"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = Exception("Request timed out")
        mock_async_session_class.return_value = mock_session
        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpTimeoutError) as exc_info:
            await client.request_async("GET", "test", timeout=30)

        assert exc_info.value.method == "GET"
        assert exc_info.value.timeout == 30
        assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_http_connection_error(self, mock_async_session_class):
        """Test HTTP connection error handling"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = Exception("Connection failed")
        mock_async_session_class.return_value = mock_session
        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpConnectionError) as exc_info:
            await client.request_async("GET", "test")

        assert exc_info.value.method == "GET"
        assert "Connection failed" in str(exc_info.value)

    def test_multiple_timeouts_configuration(self):
        """Test different timeout configurations work correctly"""
        # Test with various timeout values
        timeout_values = [5, 10, 15, 30, 60]

        for timeout_val in timeout_values:
            client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": timeout_val})
            assert client.client_kwargs["timeout"] == timeout_val

    def test_timeout_configuration_merge(self):
        """Test that timeout configuration merges correctly with other client_kwargs"""
        client_kwargs = {"timeout": 25, "impersonate": "chrome136", "verify": False, "headers": {"User-Agent": "test"}}

        client = HttpClientCffi(calls=60, period=60, client_kwargs=client_kwargs)

        # Verify all kwargs are preserved including timeout
        assert client.client_kwargs["timeout"] == 25
        assert client.client_kwargs["impersonate"] == "chrome136"
        assert client.client_kwargs["verify"] is False
        assert "User-Agent" in client.client_kwargs["headers"]

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_http_response_parsing_error(self, mock_async_session_class):
        """Test HTTP response parsing error handling"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"invalid": json}'  # Invalid JSON
        mock_session.request.return_value = mock_response
        mock_async_session_class.return_value = mock_session
        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpResponseParsingError) as exc_info:
            await client.request_async("GET", "test")

        assert exc_info.value.method == "GET"
        assert exc_info.value.content_type == "application/json"

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_non_json_response_error(self, mock_async_session_class):
        """Test non-JSON response handling"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b"<html>Error page</html>"
        mock_session.request.return_value = mock_response
        mock_async_session_class.return_value = mock_session
        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpResponseParsingError) as exc_info:
            await client.request_async("GET", "test")

        assert exc_info.value.method == "GET"
        assert exc_info.value.content_type == "text/html"
        assert "Expected JSON response" in str(exc_info.value)

    @patch("dexscreen.core.http.Session")
    def test_sync_request_error_handling(self, mock_session_class):
        """Test synchronous request error handling"""
        mock_session = Mock()
        mock_session.request.side_effect = Exception("Network error")
        mock_session_class.return_value = mock_session

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpConnectionError) as exc_info:
            client.request("GET", "test")

        assert "Network error" in str(exc_info.value)
        assert exc_info.value.method == "GET"

    @patch("dexscreen.core.http.Session")
    def test_sync_timeout_error(self, mock_session_class):
        """Test synchronous timeout error handling"""
        mock_session = Mock()
        mock_session.request.side_effect = Exception("Request timeout")
        mock_session_class.return_value = mock_session

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpTimeoutError) as exc_info:
            client.request("GET", "test", timeout=15)

        assert exc_info.value.method == "GET"
        assert exc_info.value.timeout == 15

    def test_default_timeout_is_10_seconds(self):
        """Test that default timeout is 10 seconds when not specified"""
        client = HttpClientCffi(calls=60, period=60)

        # Check that default timeout is set in client_kwargs
        assert "timeout" in client.client_kwargs
        assert client.client_kwargs["timeout"] == 10

    def test_user_timeout_overrides_default(self):
        """Test that user-provided timeout overrides default"""
        custom_timeout = 25
        client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": custom_timeout})

        # Check that user timeout overrides default
        assert client.client_kwargs["timeout"] == custom_timeout

    @patch("dexscreen.core.http.Session")
    def test_default_timeout_propagates_to_session(self, mock_session_class):
        """Test that default timeout is passed to curl_cffi Session"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HttpClientCffi(calls=60, period=60)
        client.request("GET", "test")

        # Verify Session was created with default timeout
        mock_session_class.assert_called_once()
        call_kwargs = mock_session_class.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == 10

    @patch("dexscreen.core.http.Session")
    def test_custom_timeout_propagates_to_session(self, mock_session_class):
        """Test that custom timeout is passed to curl_cffi Session"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        custom_timeout = 30
        client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": custom_timeout})
        client.request("GET", "test")

        # Verify Session was created with custom timeout
        mock_session_class.assert_called_once()
        call_kwargs = mock_session_class.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == custom_timeout

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_default_timeout_propagates_to_async_session(self, mock_async_session_class):
        """Test that default timeout is passed to curl_cffi AsyncSession"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_async_session_class.return_value = mock_session

        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.raise_for_status = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)
        await client.request_async("GET", "test")

        # Verify AsyncSession was created with default timeout
        mock_async_session_class.assert_called_once()
        call_kwargs = mock_async_session_class.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == 10

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_custom_timeout_propagates_to_async_session(self, mock_async_session_class):
        """Test that custom timeout is passed to curl_cffi AsyncSession"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_async_session_class.return_value = mock_session

        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.raise_for_status = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        custom_timeout = 45
        client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": custom_timeout})
        await client.request_async("GET", "test")

        # Verify AsyncSession was created with custom timeout
        mock_async_session_class.assert_called_once()
        call_kwargs = mock_async_session_class.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == custom_timeout

    @patch("dexscreen.core.http.Session")
    def test_timeout_value_in_request_kwargs(self, mock_session_class):
        """Test that timeout value is correctly passed in request call"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HttpClientCffi(calls=60, period=60)
        specific_timeout = 20
        client.request("GET", "test", timeout=specific_timeout)

        # Verify request was called with timeout
        mock_session.request.assert_called_once()
        call_kwargs = mock_session.request.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == specific_timeout

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_timeout_value_in_async_request_kwargs(self, mock_async_session_class):
        """Test that timeout value is correctly passed in async request call"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_async_session_class.return_value = mock_session

        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.raise_for_status = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)
        specific_timeout = 35
        await client.request_async("GET", "test", timeout=specific_timeout)

        # Verify request was called with timeout
        mock_session.request.assert_called_once()
        call_kwargs = mock_session.request.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == specific_timeout

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_session_creation_error(self, mock_async_session_class):
        """Test session creation error handling"""
        # Mock the _ensure_active_session to raise an error
        client = HttpClientCffi(calls=60, period=60)

        # Directly patch the _ensure_active_session method
        with patch.object(client, "_ensure_active_session", side_effect=Exception("Session creation failed")):
            with pytest.raises(HttpSessionError) as exc_info:
                await client.request_async("GET", "test")

            assert "Session creation failed" in str(exc_info.value)

    def test_timeout_with_no_client_kwargs(self):
        """Test that default timeout is applied when no client_kwargs provided"""
        client = HttpClientCffi(calls=60, period=60)

        # Default timeout should be set
        assert "timeout" in client.client_kwargs
        assert client.client_kwargs["timeout"] == 10

    def test_timeout_with_empty_client_kwargs(self):
        """Test that default timeout is applied when empty client_kwargs provided"""
        client = HttpClientCffi(calls=60, period=60, client_kwargs={})

        # Default timeout should be set
        assert "timeout" in client.client_kwargs
        assert client.client_kwargs["timeout"] == 10

    def test_timeout_preserves_other_defaults(self):
        """Test that setting timeout doesn't interfere with other defaults"""
        client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": 20})

        # Should have timeout and impersonate (default)
        assert client.client_kwargs["timeout"] == 20
        assert "impersonate" in client.client_kwargs  # Browser impersonation should still be set
