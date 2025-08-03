"""
Comprehensive tests for DexscreenerClient subscription and streaming methods
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.exceptions import InvalidFilterError
from dexscreen.utils.filters import FilterConfig


class TestSubscriptionMethods:
    """Test subscription methods with comprehensive coverage"""

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_pairs_no_filter(self, mock_polling_stream_class):
        """Test subscribe_pairs with filter=False"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        callback_called = []

        def callback(pair):
            callback_called.append(pair)

        await client.subscribe_pairs(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=False, interval=0.5
        )

        # Verify subscription was added
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        sub_info = client._active_subscriptions["ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        assert sub_info["filter"] is False
        assert sub_info["filter_config"] is None
        assert sub_info["interval"] == 0.5

        # Verify stream was created and subscribed
        mock_polling_stream_class.assert_called_once()
        mock_stream.connect.assert_called_once()
        mock_stream.subscribe.assert_called_once()

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_pairs_default_filter(self, mock_polling_stream_class):
        """Test subscribe_pairs with filter=True (default)"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        callback_called = []

        def callback(pair):
            callback_called.append(pair)

        await client.subscribe_pairs(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=True, interval=0.3
        )

        # Verify subscription was added with default filter
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        sub_info = client._active_subscriptions["ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        assert sub_info["filter"] is True
        assert sub_info["filter_config"] is not None
        assert isinstance(sub_info["filter_config"], FilterConfig)
        assert sub_info["interval"] == 0.3

        # Verify filter was created
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._filters

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_pairs_custom_filter_config(self, mock_polling_stream_class):
        """Test subscribe_pairs with custom FilterConfig"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        custom_filter = FilterConfig(price_change_threshold=0.05)

        def callback(pair):
            pass

        await client.subscribe_pairs(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=custom_filter, interval=0.1
        )

        # Verify subscription was added with custom filter
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        sub_info = client._active_subscriptions["ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        assert sub_info["filter"] == custom_filter
        assert sub_info["filter_config"] == custom_filter
        assert sub_info["interval"] == 0.1

    @pytest.mark.asyncio
    async def test_subscribe_pairs_invalid_filter_type(self):
        """Test subscribe_pairs with invalid filter type"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        # Test with string filter (invalid)
        with pytest.raises(InvalidFilterError, match="Must be bool or FilterConfig"):
            await client.subscribe_pairs(
                "ethereum",
                ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
                callback,
                filter="invalid",  # type: ignore
            )

        # Test with int filter (invalid)
        with pytest.raises(InvalidFilterError, match="Must be bool or FilterConfig"):
            await client.subscribe_pairs(
                "ethereum",
                ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
                callback,
                filter=123,  # type: ignore
            )

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_pairs_multiple_addresses(self, mock_polling_stream_class):
        """Test subscribe_pairs with multiple pair addresses"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()

        def callback(pair):
            pass

        await client.subscribe_pairs(
            "ethereum",
            ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],
            callback,
            filter=False,
        )

        # Verify both subscriptions were added
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        assert "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" in client._active_subscriptions

        # Verify subscribe was called for each pair
        assert mock_stream.subscribe.call_count == 2

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_pairs_reuse_existing_stream(self, mock_polling_stream_class):
        """Test subscribe_pairs reuses existing stream"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()

        def callback(pair):
            pass

        # First subscription
        await client.subscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=False)

        # Second subscription should reuse the same stream
        await client.subscribe_pairs("ethereum", ["0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"], callback, filter=False)

        # Stream should only be created once
        mock_polling_stream_class.assert_called_once()
        # But connect should only be called once
        mock_stream.connect.assert_called_once()
        # Subscribe should be called twice
        assert mock_stream.subscribe.call_count == 2

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_tokens_no_filter(self, mock_polling_stream_class):
        """Test subscribe_tokens with filter=False"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe_token = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()

        def callback(pairs):
            pass

        await client.subscribe_tokens(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=False, interval=0.4
        )

        # Verify subscription was added
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        sub_info = client._active_subscriptions["token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        assert sub_info["type"] == "token"
        assert sub_info["filter"] is False
        assert sub_info["filter_config"] is None
        assert sub_info["interval"] == 0.4

        # Verify stream methods were called
        mock_stream.connect.assert_called_once()
        mock_stream.subscribe_token.assert_called_once()

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_tokens_default_filter(self, mock_polling_stream_class):
        """Test subscribe_tokens with filter=True (default)"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe_token = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()

        def callback(pairs):
            pass

        await client.subscribe_tokens("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=True)

        # Verify subscription was added with default filter
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        sub_info = client._active_subscriptions["token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        assert sub_info["filter"] is True
        assert sub_info["filter_config"] is not None
        assert isinstance(sub_info["filter_config"], FilterConfig)

        # Verify filter was created
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._filters

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_tokens_custom_filter_config(self, mock_polling_stream_class):
        """Test subscribe_tokens with custom FilterConfig"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe_token = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        # Use a valid percentage value (0.1 = 10% change threshold)
        custom_filter = FilterConfig(volume_change_threshold=0.1)

        def callback(pairs):
            pass

        await client.subscribe_tokens(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=custom_filter
        )

        # Verify subscription was added with custom filter
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        sub_info = client._active_subscriptions["token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        assert sub_info["filter"] == custom_filter
        assert sub_info["filter_config"] == custom_filter

    @pytest.mark.asyncio
    async def test_subscribe_tokens_invalid_filter_type(self):
        """Test subscribe_tokens with invalid filter type"""
        client = DexscreenerClient()

        def callback(pairs):
            pass

        # Test with int filter (invalid)
        with pytest.raises(InvalidFilterError, match="Must be bool or FilterConfig"):
            await client.subscribe_tokens(
                "ethereum",
                ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
                callback,
                filter=123,  # type: ignore
            )

        # Test with string filter (invalid)
        with pytest.raises(InvalidFilterError, match="Must be bool or FilterConfig"):
            await client.subscribe_tokens(
                "ethereum",
                ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
                callback,
                filter="invalid",  # type: ignore
            )

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_subscribe_tokens_multiple_addresses(self, mock_polling_stream_class):
        """Test subscribe_tokens with multiple token addresses"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe_token = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()

        def callback(pairs):
            pass

        await client.subscribe_tokens(
            "ethereum",
            ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],
            callback,
            filter=False,
        )

        # Verify both subscriptions were added
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        assert "token:ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" in client._active_subscriptions

        # Verify subscribe_token was called for each token
        assert mock_stream.subscribe_token.call_count == 2


class TestUnsubscriptionMethods:
    """Test unsubscription methods"""

    @pytest.mark.asyncio
    async def test_unsubscribe_pairs_success(self):
        """Test successful unsubscribe_pairs"""
        client = DexscreenerClient()

        # Set up mock subscription and stream
        mock_stream = Mock()
        mock_stream.has_subscription = Mock(return_value=True)
        mock_stream.unsubscribe = AsyncMock()
        client._http_stream = mock_stream

        # Add mock subscription
        subscription_key = "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": None,
            "interval": 0.2,
        }

        # Add mock filter
        mock_filter = Mock()
        mock_filter.reset = Mock()
        client._filters[subscription_key] = mock_filter

        # Unsubscribe
        await client.unsubscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        # Verify subscription was removed
        assert subscription_key not in client._active_subscriptions
        assert subscription_key not in client._filters

        # Verify stream methods were called
        mock_stream.has_subscription.assert_called_once_with("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
        mock_stream.unsubscribe.assert_called_once_with("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
        mock_filter.reset.assert_called_once_with(subscription_key)

    @pytest.mark.asyncio
    async def test_unsubscribe_pairs_no_subscription(self):
        """Test unsubscribe_pairs with no existing subscription"""
        client = DexscreenerClient()

        # Should not raise error
        await client.unsubscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        # No subscriptions should exist
        assert len(client._active_subscriptions) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_pairs_no_stream_subscription(self):
        """Test unsubscribe_pairs when stream has no subscription"""
        client = DexscreenerClient()

        # Set up mock stream that has no subscription
        mock_stream = Mock()
        mock_stream.has_subscription = Mock(return_value=False)
        mock_stream.unsubscribe = AsyncMock()
        client._http_stream = mock_stream

        # Add mock subscription
        subscription_key = "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        client._active_subscriptions[subscription_key] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": None,
            "interval": 0.2,
        }

        # Unsubscribe
        await client.unsubscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        # Verify subscription was removed
        assert subscription_key not in client._active_subscriptions

        # Verify stream unsubscribe was not called
        mock_stream.unsubscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_pairs_multiple_addresses(self):
        """Test unsubscribe_pairs with multiple addresses"""
        client = DexscreenerClient()

        # Set up mock stream
        mock_stream = Mock()
        mock_stream.has_subscription = Mock(return_value=True)
        mock_stream.unsubscribe = AsyncMock()
        client._http_stream = mock_stream

        # Add mock subscriptions
        for addr in ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]:
            subscription_key = f"ethereum:{addr}"
            client._active_subscriptions[subscription_key] = {
                "chain": "ethereum",
                "pair_address": addr,
                "callback": lambda x: None,
                "filter": True,
                "filter_config": None,
                "interval": 0.2,
            }

            mock_filter = Mock()
            mock_filter.reset = Mock()
            client._filters[subscription_key] = mock_filter

        # Unsubscribe both
        await client.unsubscribe_pairs(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]
        )

        # Verify both subscriptions were removed
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" not in client._active_subscriptions
        assert "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" not in client._active_subscriptions
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" not in client._filters
        assert "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" not in client._filters

        # Verify unsubscribe was called twice
        assert mock_stream.unsubscribe.call_count == 2

    @pytest.mark.asyncio
    async def test_unsubscribe_tokens_success(self):
        """Test successful unsubscribe_tokens"""
        client = DexscreenerClient()

        # Set up mock stream
        mock_stream = Mock()
        mock_stream.has_token_subscription = Mock(return_value=True)
        mock_stream.unsubscribe_token = AsyncMock()
        client._http_stream = mock_stream

        # Add mock subscription
        subscription_key = "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        client._active_subscriptions[subscription_key] = {
            "type": "token",
            "chain": "ethereum",
            "token_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": None,
            "interval": 0.2,
        }

        # Add mock filter
        mock_filter = Mock()
        mock_filter.reset = Mock()
        client._filters[subscription_key] = mock_filter

        # Unsubscribe
        await client.unsubscribe_tokens("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        # Verify subscription was removed
        assert subscription_key not in client._active_subscriptions
        assert subscription_key not in client._filters

        # Verify stream methods were called
        mock_stream.has_token_subscription.assert_called_once_with(
            "ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )
        mock_stream.unsubscribe_token.assert_called_once_with("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
        mock_filter.reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_tokens_no_subscription(self):
        """Test unsubscribe_tokens with no existing subscription"""
        client = DexscreenerClient()

        # Should not raise error
        await client.unsubscribe_tokens("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        # No subscriptions should exist
        assert len(client._active_subscriptions) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_tokens_no_stream_subscription(self):
        """Test unsubscribe_tokens when stream has no subscription"""
        client = DexscreenerClient()

        # Set up mock stream that has no token subscription
        mock_stream = Mock()
        mock_stream.has_token_subscription = Mock(return_value=False)
        mock_stream.unsubscribe_token = AsyncMock()
        client._http_stream = mock_stream

        # Add mock subscription
        subscription_key = "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        client._active_subscriptions[subscription_key] = {
            "type": "token",
            "chain": "ethereum",
            "token_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "filter_config": None,
            "interval": 0.2,
        }

        # Unsubscribe
        await client.unsubscribe_tokens("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        # Verify subscription was removed
        assert subscription_key not in client._active_subscriptions

        # Verify stream unsubscribe was not called
        mock_stream.unsubscribe_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_tokens_multiple_addresses(self):
        """Test unsubscribe_tokens with multiple addresses"""
        client = DexscreenerClient()

        # Set up mock stream
        mock_stream = Mock()
        mock_stream.has_token_subscription = Mock(return_value=True)
        mock_stream.unsubscribe_token = AsyncMock()
        client._http_stream = mock_stream

        # Add mock subscriptions
        for addr in ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]:
            subscription_key = f"token:ethereum:{addr}"
            client._active_subscriptions[subscription_key] = {
                "type": "token",
                "chain": "ethereum",
                "token_address": addr,
                "callback": lambda x: None,
                "filter": True,
                "filter_config": None,
                "interval": 0.2,
            }

            mock_filter = Mock()
            mock_filter.reset = Mock()
            client._filters[subscription_key] = mock_filter

        # Unsubscribe both
        await client.unsubscribe_tokens(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]
        )

        # Verify both subscriptions were removed
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" not in client._active_subscriptions
        assert "token:ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" not in client._active_subscriptions
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" not in client._filters
        assert "token:ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" not in client._filters

        # Verify unsubscribe_token was called twice
        assert mock_stream.unsubscribe_token.call_count == 2


class TestStreamLifecycleManagement:
    """Test stream lifecycle management"""

    @pytest.mark.asyncio
    async def test_close_streams_with_active_stream(self):
        """Test close_streams with active stream"""
        client = DexscreenerClient()

        # Set up mock stream
        mock_stream = Mock()
        mock_stream.close = AsyncMock()
        client._http_stream = mock_stream

        # Add mock subscriptions
        client._active_subscriptions["test1"] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        }
        client._active_subscriptions["test2"] = {
            "type": "token",
            "chain": "ethereum",
            "token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        }

        # Add mock filters
        mock_filter1 = Mock()
        mock_filter1.reset = Mock()
        mock_filter2 = Mock()
        mock_filter2.reset = Mock()
        client._filters["test1"] = mock_filter1
        client._filters["test2"] = mock_filter2

        # Close streams
        await client.close_streams()

        # Verify stream was closed
        mock_stream.close.assert_called_once()
        assert client._http_stream is None

        # Verify subscriptions and filters were cleared
        assert len(client._active_subscriptions) == 0
        assert len(client._filters) == 0

        # Verify filters were reset
        mock_filter1.reset.assert_called_once()
        mock_filter2.reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_streams_no_active_stream(self):
        """Test close_streams with no active stream"""
        client = DexscreenerClient()

        # Add mock subscriptions and filters
        client._active_subscriptions["test"] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        }
        mock_filter = Mock()
        mock_filter.reset = Mock()
        client._filters["test"] = mock_filter

        # Close streams (no active stream)
        await client.close_streams()

        # Verify subscriptions and filters were still cleared
        assert len(client._active_subscriptions) == 0
        assert len(client._filters) == 0
        mock_filter.reset.assert_called_once()

    def test_get_active_subscriptions_empty(self):
        """Test get_active_subscriptions with no subscriptions"""
        client = DexscreenerClient()
        result = client.get_active_subscriptions()
        assert result == []

    def test_get_active_subscriptions_pair_subscriptions(self):
        """Test get_active_subscriptions with pair subscriptions"""
        client = DexscreenerClient()

        # Add pair subscriptions
        client._active_subscriptions["ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "interval": 0.2,
        }
        client._active_subscriptions["solana:So11111111111111111111111111111111111111112"] = {
            "chain": "solana",
            "pair_address": "So11111111111111111111111111111111111111112",
            "callback": lambda x: None,
            "filter": False,
            "interval": 0.5,
        }

        result = client.get_active_subscriptions()

        assert len(result) == 2

        # Check first subscription
        sub1 = next(s for s in result if s["pair_address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
        assert sub1["type"] == "pair"
        assert sub1["chain"] == "ethereum"
        assert sub1["filter"] is True
        assert sub1["interval"] == 0.2

        # Check second subscription
        sub2 = next(s for s in result if s["pair_address"] == "So11111111111111111111111111111111111111112")
        assert sub2["type"] == "pair"
        assert sub2["chain"] == "solana"
        assert sub2["filter"] is False
        assert sub2["interval"] == 0.5

    def test_get_active_subscriptions_token_subscriptions(self):
        """Test get_active_subscriptions with token subscriptions"""
        client = DexscreenerClient()

        # Add token subscriptions
        client._active_subscriptions["token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"] = {
            "type": "token",
            "chain": "ethereum",
            "token_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "interval": 0.3,
        }
        client._active_subscriptions["token:solana:So11111111111111111111111111111111111111112"] = {
            "type": "token",
            "chain": "solana",
            "token_address": "So11111111111111111111111111111111111111112",
            "callback": lambda x: None,
            "filter": False,
            "interval": 0.1,
        }

        result = client.get_active_subscriptions()

        assert len(result) == 2

        # Check first subscription
        sub1 = next(s for s in result if s["token_address"] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
        assert sub1["type"] == "token"
        assert sub1["chain"] == "ethereum"
        assert sub1["filter"] is True
        assert sub1["interval"] == 0.3

        # Check second subscription
        sub2 = next(s for s in result if s["token_address"] == "So11111111111111111111111111111111111111112")
        assert sub2["type"] == "token"
        assert sub2["chain"] == "solana"
        assert sub2["filter"] is False
        assert sub2["interval"] == 0.1

    def test_get_active_subscriptions_mixed_subscriptions(self):
        """Test get_active_subscriptions with mixed subscription types"""
        client = DexscreenerClient()

        # Add mixed subscriptions
        client._active_subscriptions["ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"] = {
            "chain": "ethereum",
            "pair_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "callback": lambda x: None,
            "filter": True,
            "interval": 0.2,
        }
        client._active_subscriptions["token:solana:So11111111111111111111111111111111111111112"] = {
            "type": "token",
            "chain": "solana",
            "token_address": "So11111111111111111111111111111111111111112",
            "callback": lambda x: None,
            "filter": False,
            "interval": 0.4,
        }

        result = client.get_active_subscriptions()

        assert len(result) == 2

        # Should have one of each type
        types = [s["type"] for s in result]
        assert "pair" in types
        assert "token" in types


class TestFilterCallbacks:
    """Test filter callback handling"""

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_filtered_callback_sync_function(self, mock_polling_stream_class):
        """Test filtered callback with sync callback function"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        callback_calls = []

        def sync_callback(pair):
            callback_calls.append(pair)

        await client.subscribe_pairs(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], sync_callback, filter=True
        )

        # Verify subscription setup
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._filters

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_filtered_callback_async_function(self, mock_polling_stream_class):
        """Test filtered callback with async callback function"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        callback_calls = []

        async def async_callback(pair):
            callback_calls.append(pair)

        await client.subscribe_pairs(
            "ethereum",
            ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
            async_callback,  # type: ignore[arg-type]
            filter=True,
        )

        # Verify subscription setup
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        assert "ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._filters

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_token_filtered_callback_sync_function(self, mock_polling_stream_class):
        """Test token filtered callback with sync callback function"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe_token = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        callback_calls = []

        def sync_callback(pairs):
            callback_calls.append(pairs)

        await client.subscribe_tokens(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], sync_callback, filter=True
        )

        # Verify subscription setup
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._filters

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.PollingStream")
    async def test_token_filtered_callback_async_function(self, mock_polling_stream_class):
        """Test token filtered callback with async callback function"""
        mock_stream = Mock()
        mock_stream.connect = AsyncMock()
        mock_stream.subscribe_token = AsyncMock()
        mock_polling_stream_class.return_value = mock_stream

        client = DexscreenerClient()
        callback_calls = []

        async def async_callback(pairs):
            callback_calls.append(pairs)

        await client.subscribe_tokens(
            "ethereum",
            ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
            async_callback,  # type: ignore[arg-type]
            filter=True,
        )

        # Verify subscription setup
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._active_subscriptions
        assert "token:ethereum:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640" in client._filters
