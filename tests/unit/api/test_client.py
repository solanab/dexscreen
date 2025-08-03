"""
Test DexscreenerClient client functionality
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.models import TokenPair
from dexscreen.utils.filters import FilterPresets


def create_mock_api_response_factory():
    """Helper function to create mock API response factory"""
    transaction_stats_data = {
        "m5": {"buys": 10, "sells": 5},
        "h1": {"buys": 100, "sells": 50},
        "h6": {"buys": 600, "sells": 300},
        "h24": {"buys": 2400, "sells": 1200},
    }
    volume_data = {"m5": 50000.0, "h1": 250000.0, "h6": 1500000.0, "h24": 6000000.0}
    price_change_data = {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3}

    def _create_response(pairs_data=None, num_pairs=1, chain_id="ethereum", base_address=None, quote_address=None):
        if pairs_data is not None:
            return {"pairs": pairs_data}

        generated_pairs = []
        for i in range(num_pairs):
            base_addr = base_address or f"0x{(i + 1) * 111:040x}"
            quote_addr = quote_address or f"0x{(i + 1) * 222:040x}"
            pair_addr = f"0x{(i + 1) * 333:040x}"

            pair_data = {
                "chainId": chain_id,
                "dexId": "uniswap" if chain_id == "ethereum" else "raydium" if chain_id == "solana" else "pancakeswap",
                "url": f"https://test.com/{pair_addr}",
                "pairAddress": pair_addr,
                "baseToken": {"address": base_addr, "name": f"Token A{i + 1}", "symbol": f"TKA{i + 1}"},
                "quoteToken": {"address": quote_addr, "name": f"Token B{i + 1}", "symbol": f"TKB{i + 1}"},
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
            generated_pairs.append(pair_data)

        return {"pairs": generated_pairs}

    return _create_response


class TestDexscreenerClient:
    """Test DexscreenerClient class"""

    def test_client_initialization(self):
        """Test client initialization"""
        # Default initialization
        client1 = DexscreenerClient()
        assert hasattr(client1, "_client_60rpm")
        assert hasattr(client1, "_client_300rpm")
        assert hasattr(client1, "_http_stream")
        assert hasattr(client1, "_active_subscriptions")
        assert hasattr(client1, "_filters")

        # Custom initialization
        client2 = DexscreenerClient(impersonate="chrome136", client_kwargs={"timeout": 60})
        assert client2.client_kwargs["timeout"] == 60

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair(self, mock_http_class, mock_api_response_factory):
        """Test getting a single pair"""
        # Set up mock
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = mock_api_response_factory()

        client = DexscreenerClient()
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert isinstance(pair, TokenPair)
        assert pair.pair_address == f"0x{1 * 333:040x}"
        assert pair.base_token.symbol == "TKA1"

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_not_found(self, mock_http_class, mock_api_response_factory):
        """Test getting a non-existent pair"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = mock_api_response_factory(pairs_data=[])

        client = DexscreenerClient()
        pair = client.get_pair("0x1234567890123456789012345678901234567890")

        assert pair is None

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_search_pairs(self, mock_http_class, mock_api_response_factory):
        """Test searching for pairs"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Use mock factory
        mock_http.request.return_value = mock_api_response_factory()

        client = DexscreenerClient()
        results = client.search_pairs("USDC")

        assert len(results) == 1
        assert results[0].base_token.symbol == "TKA1"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pair_async(self, mock_http_class, mock_api_response_factory):
        """Test asynchronous pair retrieval"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Create custom response data
        mock_http.request_async = AsyncMock(
            return_value=mock_api_response_factory(
                chain_id="ethereum",
                base_address="0x1111111111111111111111111111111111111111",
                quote_address="0x2222222222222222222222222222222222222222",
            )
        )

        client = DexscreenerClient()
        pair = await client.get_pair_async("0x1234567890123456789012345678901234567890")

        assert isinstance(pair, TokenPair)
        assert pair.pair_address == f"0x{1 * 333:040x}"  # Generated address
        assert pair.price_usd == 100.0

    def test_get_active_subscriptions(self):
        """Test getting active subscription list"""
        client = DexscreenerClient()

        # Should be empty initially
        assert client.get_active_subscriptions() == []

        # Add mock subscription
        client._active_subscriptions["ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": None,
            "interval": 0.5,
        }

        subscriptions = client.get_active_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0]["chain"] == "ethereum"
        assert subscriptions[0]["pair_address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        assert subscriptions[0]["interval"] == 0.5

    def test_client_default_timeout(self):
        """Test client uses default timeout of 10 seconds"""
        client = DexscreenerClient()

        # Both HTTP clients should have default timeout
        assert client._client_60rpm.client_kwargs["timeout"] == 10
        assert client._client_300rpm.client_kwargs["timeout"] == 10

    def test_client_custom_timeout(self):
        """Test client respects custom timeout"""
        custom_timeout = 25
        client = DexscreenerClient(client_kwargs={"timeout": custom_timeout})

        # Both HTTP clients should use custom timeout
        assert client._client_60rpm.client_kwargs["timeout"] == custom_timeout
        assert client._client_300rpm.client_kwargs["timeout"] == custom_timeout

    def test_client_timeout_override(self):
        """Test that user timeout overrides default"""
        # Test various timeout values
        timeout_values = [5, 15, 30, 45, 60]

        for timeout_val in timeout_values:
            client = DexscreenerClient(client_kwargs={"timeout": timeout_val})
            assert client._client_60rpm.client_kwargs["timeout"] == timeout_val
            assert client._client_300rpm.client_kwargs["timeout"] == timeout_val

    def test_client_timeout_with_other_kwargs(self):
        """Test timeout works with other client_kwargs"""
        client_kwargs = {"timeout": 20, "impersonate": "firefox135", "verify": False, "headers": {"X-Custom": "test"}}

        client = DexscreenerClient(client_kwargs=client_kwargs)

        # Verify all kwargs are preserved
        assert client._client_60rpm.client_kwargs["timeout"] == 20
        assert client._client_60rpm.client_kwargs["impersonate"] == "firefox135"
        assert client._client_60rpm.client_kwargs["verify"] is False
        assert "X-Custom" in client._client_60rpm.client_kwargs["headers"]

        # Same for 300rpm client
        assert client._client_300rpm.client_kwargs["timeout"] == 20
        assert client._client_300rpm.client_kwargs["impersonate"] == "firefox135"

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_timeout_propagation_in_requests(self, mock_http_class, mock_api_response_factory):
        """Test that timeout is properly passed to HTTP requests"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = mock_api_response_factory()

        custom_timeout = 35
        DexscreenerClient(client_kwargs={"timeout": custom_timeout})

        # Verify HTTP clients were created with custom timeout
        assert mock_http_class.call_count == 2  # Two HTTP clients created

        # Check that both clients were created with the timeout
        for call in mock_http_class.call_args_list:
            client_kwargs = call[1]["client_kwargs"]
            assert "timeout" in client_kwargs
            assert client_kwargs["timeout"] == custom_timeout

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_timeout_propagation_in_async_requests(self, mock_http_class, mock_api_response_factory):
        """Test that timeout is properly passed to async HTTP requests"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=mock_api_response_factory())

        custom_timeout = 40
        client = DexscreenerClient(client_kwargs={"timeout": custom_timeout})

        await client.get_pair_async("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        # Verify HTTP clients were created with custom timeout
        assert mock_http_class.call_count == 2  # Two HTTP clients created

        # Check that both clients were created with the timeout
        for call in mock_http_class.call_args_list:
            client_kwargs = call[1]["client_kwargs"]
            assert "timeout" in client_kwargs
            assert client_kwargs["timeout"] == custom_timeout

    def test_timeout_configuration_consistency(self):
        """Test that timeout configuration is consistent across all HTTP clients"""
        timeout_values = [5, 10, 15, 30, 45, 60]

        for timeout_val in timeout_values:
            client = DexscreenerClient(client_kwargs={"timeout": timeout_val})

            # Both HTTP clients should have the same timeout
            assert client._client_60rpm.client_kwargs["timeout"] == timeout_val
            assert client._client_300rpm.client_kwargs["timeout"] == timeout_val

            # Verify timeout is exactly what was set
            assert client._client_60rpm.client_kwargs["timeout"] == client._client_300rpm.client_kwargs["timeout"]

    def test_timeout_edge_cases(self):
        """Test timeout configuration edge cases"""
        # Test very small timeout
        client1 = DexscreenerClient(client_kwargs={"timeout": 1})
        assert client1._client_60rpm.client_kwargs["timeout"] == 1

        # Test large timeout
        client2 = DexscreenerClient(client_kwargs={"timeout": 300})
        assert client2._client_60rpm.client_kwargs["timeout"] == 300

        # Test float timeout
        client3 = DexscreenerClient(client_kwargs={"timeout": 10.5})
        assert client3._client_60rpm.client_kwargs["timeout"] == 10.5

    def test_comprehensive_timeout_scenarios(self):
        """Test comprehensive timeout scenarios covering various use cases"""
        scenarios = [
            # (description, client_kwargs, expected_timeout)
            ("Default timeout", {}, 10),
            ("Custom integer timeout", {"timeout": 25}, 25),
            ("Custom float timeout", {"timeout": 30.5}, 30.5),
            ("Timeout with other kwargs", {"timeout": 15, "verify": False}, 15),
            ("Small timeout", {"timeout": 1}, 1),
            ("Large timeout", {"timeout": 120}, 120),
        ]

        for description, client_kwargs, expected_timeout in scenarios:
            client = DexscreenerClient(client_kwargs=client_kwargs)

            # Both HTTP clients should have expected timeout
            assert client._client_60rpm.client_kwargs["timeout"] == expected_timeout, f"Failed for {description}"
            assert client._client_300rpm.client_kwargs["timeout"] == expected_timeout, f"Failed for {description}"

            # Verify timeout type is preserved
            assert isinstance(client._client_60rpm.client_kwargs["timeout"], type(expected_timeout)), (
                f"Type mismatch for {description}"
            )


class TestSubscriptionMethods:
    """Test subscription-related methods"""

    @pytest.mark.asyncio
    async def test_subscribe_with_filter(self):
        """Test subscribing with a filter"""
        client = DexscreenerClient()
        callback_called = False

        async def callback(pair):
            nonlocal callback_called
            callback_called = True

        # Set up subscription (without actually running)
        subscription_key = "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": callback,
            "filter": True,
            "filter_config": None,
            "interval": 0.2,
        }

        # Verify subscription added
        assert subscription_key in client._active_subscriptions
        assert client._active_subscriptions[subscription_key]["filter"] is True

    @pytest.mark.asyncio
    async def test_subscribe_without_filter(self):
        """Test subscribing without a filter"""
        client = DexscreenerClient()

        # Mock HTTP stream
        mock_stream = Mock()
        mock_stream.subscribe = AsyncMock()
        mock_stream.connect = AsyncMock()
        client._http_stream = mock_stream

        # Set up subscription without a filter
        await client.subscribe_pairs(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], lambda x: None, filter=False, interval=0.2
        )

        # Verify correct method called
        mock_stream.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing"""
        client = DexscreenerClient()

        # Set up mock subscription
        subscription_key = "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": None,
            "interval": 0.2,
        }

        # Mock HTTP stream
        mock_stream = Mock()
        mock_stream.has_subscription.return_value = True
        mock_stream.unsubscribe = AsyncMock()
        client._http_stream = mock_stream

        # Unsubscribe
        await client.unsubscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        # Verify subscription removed
        assert subscription_key not in client._active_subscriptions
        mock_stream.unsubscribe.assert_called_once_with("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

    @pytest.mark.asyncio
    async def test_close_streams(self):
        """Test closing all streams"""
        client = DexscreenerClient()

        # Add mock stream
        mock_stream = Mock()
        mock_stream.close = AsyncMock()

        client._http_stream = mock_stream

        # Add subscription
        client._active_subscriptions["test"] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        }

        # Close all streams
        await client.close_streams()

        # Verify streams closed
        mock_stream.close.assert_called_once()
        assert client._http_stream is None
        assert len(client._active_subscriptions) == 0


class TestFilterIntegration:
    """Test filter integration"""

    @pytest.mark.asyncio
    async def test_subscribe_with_custom_filter_config(self):
        """Test subscribing with a custom filter configuration"""
        client = DexscreenerClient()

        # Use preset filter configuration
        filter_config = FilterPresets.significant_price_changes(0.05)

        subscription_key = "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": filter_config,
            "interval": 0.2,
        }

        # Verify filter configuration is stored correctly
        assert client._active_subscriptions[subscription_key]["filter_config"] == filter_config


class TestDexscreenerClientComprehensive:
    """Comprehensive tests for all DexscreenerClient methods"""

    # ========== Single Query Methods Tests ==========

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_exact_match(self, mock_http_class, mock_api_response_factory):
        """Test get_pair with exact address match"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Create response with exact matching address
        mock_http.request.return_value = mock_api_response_factory(
            chain_id="ethereum",
            base_address="0xabc0000000000000000000000000000000000000",
            quote_address="0xdef0000000000000000000000000000000000000",
        )

        client = DexscreenerClient()
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert isinstance(pair, TokenPair)
        assert pair.pair_address == f"0x{1 * 333:040x}"
        mock_http.request.assert_called_once_with(
            "GET", "latest/dex/search?q=0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_first_result_fallback(self, mock_http_class, mock_api_response_factory):
        """Test get_pair returns first result when no exact match"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Create response with no exact match but has results
        mock_http.request.return_value = mock_api_response_factory(
            chain_id="ethereum",
            base_address="0xabc0000000000000000000000000000000000000",
            quote_address="0xdef0000000000000000000000000000000000000",
        )

        client = DexscreenerClient()
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert isinstance(pair, TokenPair)
        assert pair.pair_address == f"0x{1 * 333:040x}"  # Gets first result

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_none_response(self, mock_http_class):
        """Test get_pair with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert pair is None

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_invalid_response(self, mock_http_class):
        """Test get_pair with invalid response format"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"invalid": "response"}

        client = DexscreenerClient()
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert pair is None

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pair_async_exact_match(self, mock_http_class):
        """Test async get_pair with exact address match"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_api_response_factory = create_mock_api_response_factory()
        mock_http.request_async = AsyncMock(
            return_value=mock_api_response_factory(
                chain_id="ethereum",
                base_address="0xabc0000000000000000000000000000000000000",
                quote_address="0xdef0000000000000000000000000000000000000",
            )
        )

        client = DexscreenerClient()
        pair = await client.get_pair_async("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert isinstance(pair, TokenPair)
        assert pair.pair_address == f"0x{1 * 333:040x}"
        mock_http.request_async.assert_called_once_with(
            "GET", "latest/dex/search?q=0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pair_async_none_response(self, mock_http_class):
        """Test async get_pair with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        pair = await client.get_pair_async("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert pair is None

    def test_get_pairs_by_pairs_addresses_empty_list(self):
        """Test get_pairs_by_pairs_addresses with empty list"""
        client = DexscreenerClient()
        result = client.get_pairs_by_pairs_addresses("ethereum", [])
        assert result == []

    def test_get_pairs_by_pairs_addresses_exceeds_limit(self):
        """Test get_pairs_by_pairs_addresses exceeds limit"""
        client = DexscreenerClient()
        # Create 31 addresses (exceeds MAX_PAIRS_PER_REQUEST of 30)
        addresses = [f"0x{i:040x}" for i in range(31)]

        from dexscreen.core.exceptions import TooManyItemsError

        with pytest.raises(TooManyItemsError) as exc_info:
            client.get_pairs_by_pairs_addresses("ethereum", addresses)

        assert "Too many pair_addresses: 31. Maximum allowed: 30" in str(exc_info.value)

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_pairs_addresses_success(self, mock_http_class, mock_api_response_factory):
        """Test successful get_pairs_by_pairs_addresses"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_http.request.return_value = mock_api_response_factory(
            chain_id="ethereum",
            base_address="0xabc0000000000000000000000000000000000000",
            quote_address="0xdef0000000000000000000000000000000000000",
        )

        client = DexscreenerClient()
        result = client.get_pairs_by_pairs_addresses("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == f"0x{1 * 333:040x}"
        mock_http.request.assert_called_once_with(
            "GET", "latest/dex/pairs/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_pairs_addresses_none_response(self, mock_http_class):
        """Test get_pairs_by_pairs_addresses with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_pairs_by_pairs_addresses("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        assert result == []

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_pairs_addresses_no_pairs(self, mock_http_class):
        """Test get_pairs_by_pairs_addresses with no pairs in response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"pairs": None}

        client = DexscreenerClient()
        result = client.get_pairs_by_pairs_addresses("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        assert result == []

    @pytest.mark.asyncio
    async def test_get_pairs_by_pairs_addresses_async_empty_list(self):
        """Test async get_pairs_by_pairs_addresses with empty list"""
        client = DexscreenerClient()
        result = await client.get_pairs_by_pairs_addresses_async("ethereum", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_pairs_by_pairs_addresses_async_exceeds_limit(self):
        """Test async get_pairs_by_pairs_addresses exceeds limit"""
        client = DexscreenerClient()
        addresses = [f"0x{i:040x}" for i in range(31)]

        from dexscreen.core.exceptions import TooManyItemsError

        with pytest.raises(TooManyItemsError) as exc_info:
            await client.get_pairs_by_pairs_addresses_async("ethereum", addresses)

        assert "Too many pair_addresses: 31. Maximum allowed: 30" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pairs_by_pairs_addresses_async_success(self, mock_http_class):
        """Test successful async get_pairs_by_pairs_addresses"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_api_response_factory = create_mock_api_response_factory()
        mock_http.request_async = AsyncMock(
            return_value=mock_api_response_factory(
                chain_id="ethereum",
                base_address="0xabc0000000000000000000000000000000000000",
                quote_address="0xdef0000000000000000000000000000000000000",
            )
        )

        client = DexscreenerClient()
        result = await client.get_pairs_by_pairs_addresses_async(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        )

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == f"0x{1 * 333:040x}"

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_by_pair_address_success(self, mock_http_class, mock_api_response_factory):
        """Test successful get_pair_by_pair_address"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_http.request.return_value = mock_api_response_factory(
            chain_id="ethereum",
            base_address="0xabc0000000000000000000000000000000000000",
            quote_address="0xdef0000000000000000000000000000000000000",
        )

        client = DexscreenerClient()
        result = client.get_pair_by_pair_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert isinstance(result, TokenPair)
        assert result.pair_address == f"0x{1 * 333:040x}"

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_by_pair_address_not_found(self, mock_http_class):
        """Test get_pair_by_pair_address when pair not found"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"pairs": []}

        client = DexscreenerClient()
        result = client.get_pair_by_pair_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result is None

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pair_by_pair_address_async_success(self, mock_http_class):
        """Test successful async get_pair_by_pair_address"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_api_response_factory = create_mock_api_response_factory()
        mock_http.request_async = AsyncMock(
            return_value=mock_api_response_factory(
                chain_id="ethereum",
                base_address="0xabc0000000000000000000000000000000000000",
                quote_address="0xdef0000000000000000000000000000000000000",
            )
        )

        client = DexscreenerClient()
        result = await client.get_pair_by_pair_address_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert isinstance(result, TokenPair)
        assert result.pair_address == f"0x{1 * 333:040x}"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pair_by_pair_address_async_not_found(self, mock_http_class):
        """Test async get_pair_by_pair_address when pair not found"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value={"pairs": []})

        client = DexscreenerClient()
        result = await client.get_pair_by_pair_address_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result is None
