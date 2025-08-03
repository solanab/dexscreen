"""
Comprehensive tests for timeout functionality in the dexscreen project.

Tests cover:
- Default timeout values
- User-provided timeout overrides
- Timeout propagation through the system
- Both sync and async scenarios
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.exceptions import HttpTimeoutError
from dexscreen.core.http import HttpClientCffi


class TestTimeoutDefaults:
    """Test default timeout behavior"""

    def test_http_client_default_timeout(self):
        """Test HttpClientCffi sets default timeout of 10 seconds"""
        client = HttpClientCffi(calls=60, period=60)
        assert client.client_kwargs["timeout"] == 10

    def test_http_client_default_timeout_with_empty_kwargs(self):
        """Test HttpClientCffi sets default timeout even with empty client_kwargs"""
        client = HttpClientCffi(calls=60, period=60, client_kwargs={})
        assert client.client_kwargs["timeout"] == 10

    def test_dexscreener_client_default_timeout(self):
        """Test DexscreenerClient propagates default timeout to HTTP clients"""
        client = DexscreenerClient()

        # Both internal HTTP clients should have default timeout
        assert client._client_60rpm.client_kwargs["timeout"] == 10
        assert client._client_300rpm.client_kwargs["timeout"] == 10

    def test_dexscreener_client_default_timeout_with_empty_kwargs(self):
        """Test DexscreenerClient default timeout with empty client_kwargs"""
        client = DexscreenerClient(client_kwargs={})

        assert client._client_60rpm.client_kwargs["timeout"] == 10
        assert client._client_300rpm.client_kwargs["timeout"] == 10


class TestTimeoutOverrides:
    """Test timeout override behavior"""

    def test_http_client_custom_timeout(self):
        """Test HttpClientCffi respects user-provided timeout"""
        custom_timeout = 25
        client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": custom_timeout})
        assert client.client_kwargs["timeout"] == custom_timeout

    def test_dexscreener_client_custom_timeout(self):
        """Test DexscreenerClient respects user-provided timeout"""
        custom_timeout = 30
        client = DexscreenerClient(client_kwargs={"timeout": custom_timeout})

        assert client._client_60rpm.client_kwargs["timeout"] == custom_timeout
        assert client._client_300rpm.client_kwargs["timeout"] == custom_timeout

    def test_timeout_override_preserves_other_settings(self):
        """Test that timeout override doesn't interfere with other settings"""
        kwargs = {"timeout": 20, "impersonate": "chrome136", "verify": False, "headers": {"User-Agent": "test"}}

        client = DexscreenerClient(client_kwargs=kwargs)

        # All settings should be preserved
        assert client._client_60rpm.client_kwargs["timeout"] == 20
        assert client._client_60rpm.client_kwargs["impersonate"] == "chrome136"
        assert client._client_60rpm.client_kwargs["verify"] is False
        assert "User-Agent" in client._client_60rpm.client_kwargs["headers"]

    def test_timeout_override_with_various_types(self):
        """Test timeout override with different value types"""
        # Integer timeout
        client1 = DexscreenerClient(client_kwargs={"timeout": 15})
        assert client1._client_60rpm.client_kwargs["timeout"] == 15
        assert isinstance(client1._client_60rpm.client_kwargs["timeout"], int)

        # Float timeout
        client2 = DexscreenerClient(client_kwargs={"timeout": 12.5})
        assert client2._client_60rpm.client_kwargs["timeout"] == 12.5
        assert isinstance(client2._client_60rpm.client_kwargs["timeout"], float)


class TestTimeoutPropagation:
    """Test timeout propagation through the system"""

    @patch("dexscreen.core.http.Session")
    def test_sync_session_creation_with_default_timeout(self, mock_session_class):
        """Test that sync Session is created with default timeout"""
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
        assert call_kwargs["timeout"] == 10

    @patch("dexscreen.core.http.Session")
    def test_sync_session_creation_with_custom_timeout(self, mock_session_class):
        """Test that sync Session is created with custom timeout"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        custom_timeout = 35
        client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": custom_timeout})
        client.request("GET", "test")

        # Verify Session was created with custom timeout
        mock_session_class.assert_called_once()
        call_kwargs = mock_session_class.call_args[1]
        assert call_kwargs["timeout"] == custom_timeout

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_async_session_creation_with_default_timeout(self, mock_async_session_class):
        """Test that async AsyncSession is created with default timeout"""
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
        assert call_kwargs["timeout"] == 10

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_async_session_creation_with_custom_timeout(self, mock_async_session_class):
        """Test that async AsyncSession is created with custom timeout"""
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

        custom_timeout = 40
        client = HttpClientCffi(calls=60, period=60, client_kwargs={"timeout": custom_timeout})
        await client.request_async("GET", "test")

        # Verify AsyncSession was created with custom timeout
        mock_async_session_class.assert_called_once()
        call_kwargs = mock_async_session_class.call_args[1]
        assert call_kwargs["timeout"] == custom_timeout

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_dexscreener_client_timeout_propagation(self, mock_http_class):
        """Test that DexscreenerClient passes timeout to HttpClientCffi instances"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        custom_timeout = 22
        DexscreenerClient(client_kwargs={"timeout": custom_timeout})

        # Both HTTP clients should be created with custom timeout
        assert mock_http_class.call_count == 2
        for call in mock_http_class.call_args_list:
            client_kwargs = call[1]["client_kwargs"]
            assert client_kwargs["timeout"] == custom_timeout


class TestTimeoutInRequests:
    """Test timeout behavior in actual requests"""

    @patch("dexscreen.core.http.Session")
    def test_sync_request_timeout_passed_correctly(self, mock_session_class):
        """Test that timeout is passed to sync request call"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b'{"test": "data"}'
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HttpClientCffi(calls=60, period=60)
        specific_timeout = 18
        client.request("GET", "test", timeout=specific_timeout)

        # Verify request was called with specific timeout
        mock_session.request.assert_called_once()
        call_kwargs = mock_session.request.call_args[1]
        assert call_kwargs["timeout"] == specific_timeout

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_async_request_timeout_passed_correctly(self, mock_async_session_class):
        """Test that timeout is passed to async request call"""
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
        specific_timeout = 28
        await client.request_async("GET", "test", timeout=specific_timeout)

        # Verify request was called with specific timeout
        mock_session.request.assert_called_once()
        call_kwargs = mock_session.request.call_args[1]
        assert call_kwargs["timeout"] == specific_timeout


class TestTimeoutErrorHandling:
    """Test timeout error handling"""

    @patch("dexscreen.core.http.Session")
    def test_sync_timeout_error_raises_correctly(self, mock_session_class):
        """Test that sync timeout errors are handled correctly"""
        mock_session = Mock()
        mock_session.request.side_effect = Exception("Request timeout")
        mock_session_class.return_value = mock_session

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpTimeoutError) as exc_info:
            client.request("GET", "test", timeout=15)

        assert exc_info.value.method == "GET"
        assert exc_info.value.timeout == 15
        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("dexscreen.core.http.AsyncSession")
    async def test_async_timeout_error_raises_correctly(self, mock_async_session_class):
        """Test that async timeout errors are handled correctly"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = Exception("Request timed out")
        mock_async_session_class.return_value = mock_session

        # Mock warmup response
        mock_warmup_response = AsyncMock()
        mock_warmup_response.status_code = 200
        mock_session.get.return_value = mock_warmup_response

        client = HttpClientCffi(calls=60, period=60)

        with pytest.raises(HttpTimeoutError) as exc_info:
            await client.request_async("GET", "test", timeout=25)

        assert exc_info.value.method == "GET"
        assert exc_info.value.timeout == 25
        assert "timed out" in str(exc_info.value).lower()


class TestTimeoutConsistency:
    """Test timeout consistency across different scenarios"""

    def test_multiple_clients_independent_timeouts(self):
        """Test that multiple client instances have independent timeout configurations"""
        client1 = DexscreenerClient(client_kwargs={"timeout": 10})
        client2 = DexscreenerClient(client_kwargs={"timeout": 20})
        client3 = DexscreenerClient()  # Default timeout

        # Each client should have its own timeout configuration
        assert client1._client_60rpm.client_kwargs["timeout"] == 10
        assert client2._client_60rpm.client_kwargs["timeout"] == 20
        assert client3._client_60rpm.client_kwargs["timeout"] == 10  # Default

        # Verify they don't interfere with each other
        assert client1._client_60rpm.client_kwargs["timeout"] != client2._client_60rpm.client_kwargs["timeout"]
        assert client1._client_60rpm.client_kwargs["timeout"] == client3._client_60rpm.client_kwargs["timeout"]

    def test_timeout_consistency_within_client(self):
        """Test that timeout is consistent across HTTP clients within same DexscreenerClient"""
        for timeout_val in [5, 10, 15, 30, 60]:
            client = DexscreenerClient(client_kwargs={"timeout": timeout_val})

            # Both HTTP clients should have the same timeout
            assert client._client_60rpm.client_kwargs["timeout"] == timeout_val
            assert client._client_300rpm.client_kwargs["timeout"] == timeout_val

            # Verify timeout is exactly what was set
            assert client._client_60rpm.client_kwargs["timeout"] == client._client_300rpm.client_kwargs["timeout"]

    def test_timeout_edge_cases(self):
        """Test timeout with edge case values"""
        edge_cases = [
            (1, "Very small timeout"),
            (300, "Large timeout"),
            (10.5, "Float timeout"),
            (0.5, "Sub-second timeout"),
        ]

        for timeout_val, description in edge_cases:
            client = DexscreenerClient(client_kwargs={"timeout": timeout_val})
            assert client._client_60rpm.client_kwargs["timeout"] == timeout_val, f"Failed for {description}"
            assert isinstance(client._client_60rpm.client_kwargs["timeout"], type(timeout_val)), (
                f"Type mismatch for {description}"
            )


class TestTimeoutCompatibility:
    """Test timeout compatibility with other features"""

    def test_timeout_with_browser_impersonation(self):
        """Test that timeout works correctly with browser impersonation"""
        client = DexscreenerClient(impersonate="chrome136", client_kwargs={"timeout": 15})

        # Should have both timeout and impersonation
        assert client._client_60rpm.client_kwargs["timeout"] == 15
        assert client._client_60rpm.client_kwargs["impersonate"] == "chrome136"

    def test_timeout_with_various_client_kwargs(self):
        """Test timeout compatibility with various other client_kwargs"""
        kwargs = {"timeout": 25, "verify": False, "headers": {"X-Test": "value"}, "impersonate": "firefox135"}

        client = DexscreenerClient(client_kwargs=kwargs)

        # All kwargs should be preserved
        http_client = client._client_60rpm
        assert http_client.client_kwargs["timeout"] == 25
        assert http_client.client_kwargs["verify"] is False
        assert "X-Test" in http_client.client_kwargs["headers"]
        assert http_client.client_kwargs["impersonate"] == "firefox135"

    def test_default_timeout_doesnt_override_existing_configs(self):
        """Test that default timeout doesn't interfere with existing configurations"""
        # Create client with only impersonate
        client1 = DexscreenerClient(client_kwargs={"impersonate": "safari184"})
        assert client1._client_60rpm.client_kwargs["timeout"] == 10  # Default
        assert client1._client_60rpm.client_kwargs["impersonate"] == "safari184"

        # Create client with verify setting
        client2 = DexscreenerClient(client_kwargs={"verify": False})
        assert client2._client_60rpm.client_kwargs["timeout"] == 10  # Default
        assert client2._client_60rpm.client_kwargs["verify"] is False
