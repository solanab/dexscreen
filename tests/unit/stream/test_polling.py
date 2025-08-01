"""
Test polling stream functionality
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from dexscreen.core.models import TokenPair
from dexscreen.stream.polling import PollingStream


class TestPollingStream:
    """Test PollingStream class"""

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client"""
        client = Mock()
        client.get_pair_by_pair_address_async = AsyncMock()
        return client

    def test_polling_stream_initialization(self, mock_http_client):
        """Test polling stream initialization"""
        stream = PollingStream(mock_http_client, interval=1.0)

        assert stream.dexscreener_client == mock_http_client
        assert stream.interval == 1.0
        assert stream.running is False
        assert len(stream.tasks) == 0
        assert len(stream.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, mock_http_client):
        """Test connection and disconnection"""
        stream = PollingStream(mock_http_client)

        # Connect
        await stream.connect()
        assert stream.running is True

        # Disconnect
        await stream.disconnect()
        assert stream.running is False

    @pytest.mark.asyncio
    async def test_subscribe_pairs_unsubscribe_pairs(self, mock_http_client):
        """Test subscription and unsubscription"""
        stream = PollingStream(mock_http_client)
        await stream.connect()

        callback = Mock()

        # Subscribe
        await stream.subscribe("ethereum", "0x123", callback)
        assert "ethereum:0x123" in stream.subscriptions
        assert callback in stream.subscriptions["ethereum:0x123"]

        # Unsubscribe
        await stream.unsubscribe("ethereum", "0x123", callback)
        assert "ethereum:0x123" not in stream.subscriptions

        await stream.disconnect()

    @pytest.mark.asyncio
    async def test_has_subscription(self, mock_http_client):
        """Test subscription status check"""
        stream = PollingStream(mock_http_client)
        await stream.connect()

        callback = Mock()

        # Initial no subscription
        assert stream.has_subscription("ethereum", "0x123") is False

        # After adding subscription
        await stream.subscribe("ethereum", "0x123", callback)
        assert stream.has_subscription("ethereum", "0x123") is True

        await stream.disconnect()

    @pytest.mark.asyncio
    async def test_emit_to_subscribers(self, mock_http_client, simple_test_pair_data):
        """Test emitting data to subscribers"""
        stream = PollingStream(mock_http_client)
        await stream.connect()

        # Set multiple callbacks
        callback1 = Mock()
        callback2 = Mock()
        async_callback = AsyncMock()

        await stream.subscribe("ethereum", "0x123", callback1)
        await stream.subscribe("ethereum", "0x123", callback2)
        await stream.subscribe("ethereum", "0x123", async_callback)

        # Emit data
        pair = TokenPair(**simple_test_pair_data)
        await stream._emit("ethereum", "0x123", pair)

        # Verify all callbacks were called
        callback1.assert_called_once_with(pair)
        callback2.assert_called_once_with(pair)
        async_callback.assert_called_once_with(pair)

        await stream.disconnect()

    @pytest.mark.asyncio
    async def test_change_detection(self, mock_http_client, simple_test_pair_data):
        """Test change detection"""
        stream = PollingStream(mock_http_client)

        pair1 = TokenPair(**simple_test_pair_data)

        # Always consider it changed for the first time
        assert stream._has_changed("ethereum:0x123", pair1) is True

        # After caching, the same data should not be considered changed
        stream._cache["ethereum:0x123"] = pair1
        assert stream._has_changed("ethereum:0x123", pair1) is False

        # Price change should be detected
        simple_test_pair_data["priceUsd"] = "101.0"
        pair2 = TokenPair(**simple_test_pair_data)
        assert stream._has_changed("ethereum:0x123", pair2) is True

    @pytest.mark.asyncio
    async def test_polling_task_creation(self, mock_http_client):
        """Test polling task creation"""
        stream = PollingStream(mock_http_client)
        await stream.connect()

        callback = Mock()

        # Subscribing should create a polling task - new implementation uses chain-specific tasks
        await stream.subscribe("ethereum", "0x123", callback)
        assert "ethereum" in stream._chain_tasks
        assert isinstance(stream._chain_tasks["ethereum"], asyncio.Task)

        # Unsubscribing should stop the task
        await stream.unsubscribe("ethereum", "0x123")
        # If this is the last subscription for the chain, the task will be removed
        if not stream._chain_subscriptions.get("ethereum"):
            assert "ethereum" not in stream._chain_tasks

        await stream.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_callbacks_same_pair(self, mock_http_client):
        """Test multiple callbacks for the same pair"""
        stream = PollingStream(mock_http_client)
        await stream.connect()

        callback1 = Mock()
        callback2 = Mock()

        # Add multiple callbacks
        await stream.subscribe("ethereum", "0x123", callback1)
        await stream.subscribe("ethereum", "0x123", callback2)

        # There should be only one polling task (one per chain)
        assert len(stream._chain_tasks) == 1
        assert "ethereum" in stream._chain_tasks

        # Both callbacks should be in the subscription list
        assert len(stream.subscriptions["ethereum:0x123"]) == 2

        await stream.disconnect()

    @pytest.mark.asyncio
    async def test_error_handling_in_callback(self, mock_http_client, simple_test_pair_data):
        """Test error handling in callback"""
        stream = PollingStream(mock_http_client)
        await stream.connect()

        # Create a callback that raises an exception
        def error_callback(pair):
            raise ValueError("Test error")

        # Create a normal callback
        normal_callback = Mock()

        await stream.subscribe("ethereum", "0x123", error_callback)
        await stream.subscribe("ethereum", "0x123", normal_callback)

        # Emit data
        pair = TokenPair(**simple_test_pair_data)
        await stream._emit("ethereum", "0x123", pair)

        # The normal callback should be called even if another callback fails
        normal_callback.assert_called_once_with(pair)

        await stream.disconnect()

    @pytest.mark.asyncio
    async def test_close_alias(self, mock_http_client):
        """Test close method alias"""
        stream = PollingStream(mock_http_client)
        await stream.connect()

        # close should be equivalent to disconnect
        await stream.close()
        assert stream.running is False
