"""Test batch polling optimization"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from dexscreen.stream.polling import PollingStream


class TestBatchPolling:
    """Test batch polling functionality"""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client"""
        client = Mock()
        client.get_pairs_by_pairs_addresses_async = AsyncMock()
        return client

    @pytest.fixture
    def polling_stream(self, mock_client):
        """Create a polling stream instance"""
        return PollingStream(mock_client, interval=0.1, filter_changes=False)

    async def test_batch_query_same_chain(self, polling_stream, mock_client, create_test_token_pair):
        """Test batch query on the same chain"""
        # Mock API return
        mock_pairs = [
            create_test_token_pair("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "USDC", "WETH", "1.0"),
            create_test_token_pair("ethereum", "0x11b815efb8f581194ae79006d24e0d814b7697f6", "WETH", "USDT", "3500"),
        ]
        mock_client.get_pairs_by_pairs_addresses_async.return_value = mock_pairs

        # Subscription callbacks
        updates1 = []
        updates2 = []

        async def callback1(pair):
            updates1.append(pair)

        async def callback2(pair):
            updates2.append(pair)

        # Start polling stream
        await polling_stream.connect()

        # Subscribe to two Ethereum token pairs
        await polling_stream.subscribe("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", callback1)
        await polling_stream.subscribe("ethereum", "0x11b815efb8f581194ae79006d24e0d814b7697f6", callback2)

        # Wait for some updates
        await asyncio.sleep(0.3)

        # Verify batch API was called
        assert mock_client.get_pairs_by_pairs_addresses_async.called

        # Verify correct parameters were used (batch query)
        call_args = mock_client.get_pairs_by_pairs_addresses_async.call_args
        assert call_args[0][0] == "ethereum"  # chain
        assert set(call_args[0][1]) == {
            "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "0x11b815efb8f581194ae79006d24e0d814b7697f6",
        }

        # Verify callbacks received updates
        assert len(updates1) > 0
        assert len(updates2) > 0
        assert updates1[0].price_usd == 1.0
        assert updates2[0].price_usd == 3500

        # Clean up
        await polling_stream.disconnect()

    async def test_dynamic_add_remove(self, polling_stream, mock_client, create_test_token_pair):
        """Test dynamic addition and removal of token pairs"""
        # Mock API return
        mock_client.get_pairs_by_pairs_addresses_async.return_value = [
            create_test_token_pair("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "USDC", "WETH", "1.0")
        ]

        await polling_stream.connect()

        # Add the first token pair
        await polling_stream.subscribe("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", lambda p: None)

        # Wait and verify
        await asyncio.sleep(0.15)
        assert "ethereum" in polling_stream._chain_subscriptions
        assert len(polling_stream._chain_subscriptions["ethereum"]) == 1

        # Add the second token pair to the same chain
        await polling_stream.subscribe("ethereum", "0x11b815efb8f581194ae79006d24e0d814b7697f6", lambda p: None)

        # Verify both addresses are subscribed
        assert len(polling_stream._chain_subscriptions["ethereum"]) == 2

        # Remove one token pair
        await polling_stream.unsubscribe("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        # Verify only one remains
        assert len(polling_stream._chain_subscriptions["ethereum"]) == 1
        assert "0x11b815efb8f581194ae79006d24e0d814b7697f6" in polling_stream._chain_subscriptions["ethereum"]

        # Remove the last one
        await polling_stream.unsubscribe("ethereum", "0x11b815efb8f581194ae79006d24e0d814b7697f6")

        # Verify the chain is cleaned up
        assert "ethereum" not in polling_stream._chain_subscriptions

        await polling_stream.disconnect()

    async def test_multiple_chains(self, polling_stream, mock_client, create_test_token_pair):
        """Test independent batch queries for multiple chains"""

        # Set different return values for different chains
        async def mock_get_pairs(chain, addresses):
            if chain == "ethereum":
                return [create_test_token_pair("ethereum", addresses[0], "Token", "WETH", "1")]
            elif chain == "bsc":
                return [create_test_token_pair("bsc", addresses[0], "Token", "WBNB", "2")]

        mock_client.get_pairs_by_pairs_addresses_async.side_effect = mock_get_pairs

        await polling_stream.connect()

        eth_updates = []
        bsc_updates = []

        # Subscribe to token pairs on different chains
        await polling_stream.subscribe("ethereum", "0xaaa", lambda p: eth_updates.append(p))
        await polling_stream.subscribe("bsc", "0xbbb", lambda p: bsc_updates.append(p))

        # Wait for updates
        await asyncio.sleep(0.3)

        # Verify both chains have independent batch queries
        assert mock_client.get_pairs_by_pairs_addresses_async.call_count >= 2

        # Verify each chain received the correct updates
        assert len(eth_updates) > 0
        assert len(bsc_updates) > 0
        assert eth_updates[0].chain_id == "ethereum"
        assert bsc_updates[0].chain_id == "bsc"

        await polling_stream.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
