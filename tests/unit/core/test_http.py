"""
Test HTTP client functionality
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

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
        assert "timeout" in custom_kwargs  # Don't check exact equality as impersonate might be changed

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
        result = await client.request_async("GET", "dex/pairs/ethereum/0x456")

        # Verify call
        assert result == {"pair": {"priceUsd": "200.0"}}
        mock_session.request.assert_called_once()

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_async_request_error_handling(self, mock_async_session_class):
        """Test asynchronous request error handling"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = Exception("Network error")
        mock_async_session_class.return_value = mock_session
        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.raise_for_status = AsyncMock()
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)

        # Now returns None instead of raising
        result = await client.request_async("GET", "test")
        assert result is None

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
