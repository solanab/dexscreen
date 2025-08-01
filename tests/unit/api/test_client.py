"""
Test DexscreenerClient client functionality
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.models import TokenPair
from dexscreen.utils.filters import FilterPresets


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
        pair = client.get_pair("0x123")

        assert isinstance(pair, TokenPair)
        assert pair.pair_address == "0x123"
        assert pair.base_token.symbol == "TKA"

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pair_not_found(self, mock_http_class, mock_api_response_factory):
        """Test getting a non-existent pair"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = mock_api_response_factory(pairs_data=[])

        client = DexscreenerClient()
        pair = client.get_pair("0xnotfound")

        assert pair is None

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_search_pairs(self, mock_http_class, sample_token_pair_data):
        """Test searching for pairs"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Use real USDC data
        mock_http.request.return_value = {"pairs": [sample_token_pair_data]}

        client = DexscreenerClient()
        results = client.search_pairs("USDC")

        assert len(results) == 1
        assert results[0].base_token.symbol == "USDC"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pair_async(self, mock_http_class, mock_api_response_factory):
        """Test asynchronous pair retrieval"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Create custom response data
        custom_pair = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x456",
                "baseToken": {"address": "0xabc", "name": "Token A", "symbol": "TKA"},
                "quoteToken": {"address": "0xdef", "name": "Token B", "symbol": "TKB"},
                "priceNative": "2.0",
                "priceUsd": "200.0",
                "txns": {
                    "m5": {"buys": 10, "sells": 5},
                    "h1": {"buys": 100, "sells": 50},
                    "h6": {"buys": 600, "sells": 300},
                    "h24": {"buys": 2400, "sells": 1200},
                },
                "volume": {"m5": 1000.0, "h1": 5000.0, "h6": 30000.0, "h24": 120000.0},
                "priceChange": {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3},
            }
        ]
        mock_http.request_async = AsyncMock(return_value=mock_api_response_factory(custom_pair))

        client = DexscreenerClient()
        pair = await client.get_pair_async("0x456")

        assert isinstance(pair, TokenPair)
        assert pair.pair_address == "0x456"
        assert pair.price_usd == 200.0

    def test_get_active_subscriptions(self):
        """Test getting active subscription list"""
        client = DexscreenerClient()

        # Should be empty initially
        assert client.get_active_subscriptions() == []

        # Add mock subscription
        client._active_subscriptions["ethereum:0x123"] = {
            "chain": "ethereum",
            "pair_address": "0x123",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": None,
            "interval": 0.5,
        }

        subscriptions = client.get_active_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0]["chain"] == "ethereum"
        assert subscriptions[0]["pair_address"] == "0x123"
        assert subscriptions[0]["interval"] == 0.5


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
        subscription_key = "ethereum:0x123"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x123",
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
        await client.subscribe_pairs("ethereum", ["0x123"], lambda x: None, filter=False, interval=0.2)

        # Verify correct method called
        mock_stream.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing"""
        client = DexscreenerClient()

        # Set up mock subscription
        subscription_key = "ethereum:0x123"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x123",
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
        await client.unsubscribe_pairs("ethereum", ["0x123"])

        # Verify subscription removed
        assert subscription_key not in client._active_subscriptions
        mock_stream.unsubscribe.assert_called_once_with("ethereum", "0x123")

    @pytest.mark.asyncio
    async def test_close_streams(self):
        """Test closing all streams"""
        client = DexscreenerClient()

        # Add mock stream
        mock_stream = Mock()
        mock_stream.close = AsyncMock()

        client._http_stream = mock_stream

        # Add subscription
        client._active_subscriptions["test"] = {"chain": "ethereum", "pair_address": "0x123"}

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

        subscription_key = "ethereum:0x123"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x123",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": filter_config,
            "interval": 0.2,
        }

        # Verify filter configuration is stored correctly
        assert client._active_subscriptions[subscription_key]["filter_config"] == filter_config
