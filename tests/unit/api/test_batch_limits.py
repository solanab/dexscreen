"""
Unit tests for batch query limits in DexscreenerClient
"""

from unittest.mock import patch

import pytest

from dexscreen.api.client import DexscreenerClient


class TestBatchLimits:
    """Test batch query limits for DexscreenerClient"""

    def test_get_pairs_by_pairs_addresses_single_batch(self, create_test_token_pair, batch_test_addresses_by_chain):
        """Test get_pairs_by_pairs_addresses with <= 30 addresses"""
        client = DexscreenerClient()

        # Mock response with complete structure using factory
        mock_response = {
            "pairs": [
                create_test_token_pair("solana", f"pair{i}", "TEST", "SOL", "100.0").model_dump(by_alias=True)
                for i in range(10)
            ]
        }

        with patch.object(client._client_300rpm, "request", return_value=mock_response) as mock_request:
            # Use proper test addresses from fixture
            addresses = batch_test_addresses_by_chain["solana"][:10]
            result = client.get_pairs_by_pairs_addresses("solana", addresses)

            # Should make only one request
            assert mock_request.call_count == 1
            assert len(result) == 10

            # Check the URL contains all addresses
            call_args = mock_request.call_args[0]
            assert "latest/dex/pairs/solana/" in call_args[1]
            # Check that the addresses from the fixture are in the URL
            for addr in addresses:
                assert addr in call_args[1]

    def test_get_pairs_by_pairs_addresses_exceeds_limit(self, batch_test_addresses_by_chain):
        """Test get_pairs_by_pairs_addresses with > 30 addresses raises ValueError"""
        client = DexscreenerClient()

        # Use more than 30 addresses from fixture
        addresses = batch_test_addresses_by_chain["ethereum"][:40]  # 40 addresses

        # Should raise TooManyItemsError (more specific than ValueError)
        from dexscreen.core.exceptions import TooManyItemsError

        with pytest.raises(TooManyItemsError) as exc_info:
            client.get_pairs_by_pairs_addresses("solana", addresses)

        assert "Too many pair_addresses: 40. Maximum allowed: 30" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_pairs_by_pairs_addresses_async_exceeds_limit(self, batch_test_addresses_by_chain):
        """Test async version raises TooManyItemsError with > 30 addresses"""
        client = DexscreenerClient()

        addresses = batch_test_addresses_by_chain["ethereum"][:35]  # 35 addresses

        # Should raise TooManyItemsError
        from dexscreen.core.exceptions import TooManyItemsError

        with pytest.raises(TooManyItemsError) as exc_info:
            await client.get_pairs_by_pairs_addresses_async("solana", addresses)

        assert "Too many pair_addresses: 35. Maximum allowed: 30" in str(exc_info.value)

    def test_get_pairs_by_token_addresses_exceeds_limit(self, batch_test_addresses_by_chain):
        """Test get_pairs_by_token_addresses with > 30 tokens raises TooManyItemsError"""
        client = DexscreenerClient()

        # Send 100 token addresses - use valid Solana addresses from fixture
        addresses = batch_test_addresses_by_chain["solana"][:100]

        # Should raise TooManyItemsError
        from dexscreen.core.exceptions import TooManyItemsError

        with pytest.raises(TooManyItemsError) as exc_info:
            client.get_pairs_by_token_addresses("solana", addresses)

        assert "Too many token_addresses: 100. Maximum allowed: 30" in str(exc_info.value)

    def test_get_pairs_by_token_addresses_within_limit(
        self, transaction_stats_data, volume_data, price_change_data, batch_test_addresses_by_chain
    ):
        """Test get_pairs_by_token_addresses with <= 30 tokens works"""
        client = DexscreenerClient()

        # Mock response - API returns max 30 pairs regardless of input
        mock_response = [
            {
                "pairAddress": f"pair{i}",
                "chainId": "solana",
                "dexId": "raydium",
                "url": "https://dexscreener.com/solana/pair",
                "baseToken": {"address": "0xbase", "name": "Test Token", "symbol": "TEST"},
                "quoteToken": {"address": "0xquote", "name": "Solana", "symbol": "SOL"},
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
            for i in range(25)  # Less than 30 pairs
        ]

        with patch.object(client._client_300rpm, "request", return_value=mock_response) as mock_request:
            # Send 25 token addresses - use valid Solana addresses from fixture
            addresses = batch_test_addresses_by_chain["solana"][:25]
            result = client.get_pairs_by_token_addresses("solana", addresses)

            # Should make only ONE request
            assert mock_request.call_count == 1
            assert len(result) == 25

            # Verify all 25 addresses were sent
            call_args = mock_request.call_args[0]
            assert "tokens/v1/solana/" in call_args[1]
            assert all(addr in call_args[1] for addr in addresses)

    def test_get_pairs_by_pairs_addresses_empty_list(self):
        """Test get_pairs_by_pairs_addresses with empty address list"""
        client = DexscreenerClient()

        result = client.get_pairs_by_pairs_addresses("solana", [])
        assert result == []

    def test_get_pairs_by_pairs_addresses_exactly_30(
        self, batch_test_addresses_by_chain, transaction_stats_data, volume_data, price_change_data
    ):
        """Test get_pairs_by_pairs_addresses with exactly 30 addresses"""
        client = DexscreenerClient()

        mock_response = {
            "pairs": [
                {
                    "pairAddress": f"pair{i}",
                    "chainId": "solana",
                    "dexId": "raydium",
                    "url": "https://dexscreener.com/solana/pair",
                    "baseToken": {"address": "0xbase", "name": "Test Token", "symbol": "TEST"},
                    "quoteToken": {"address": "0xquote", "name": "Solana", "symbol": "SOL"},
                    "priceNative": "1.0",
                    "priceUsd": "100.0",
                    "txns": transaction_stats_data,
                    "volume": volume_data,
                    "priceChange": price_change_data,
                }
                for i in range(30)
            ]
        }

        with patch.object(client._client_300rpm, "request", return_value=mock_response) as mock_request:
            # Use valid addresses from fixture
            addresses = batch_test_addresses_by_chain["solana"][:30]
            result = client.get_pairs_by_pairs_addresses("solana", addresses)

            # Should make only one request
            assert mock_request.call_count == 1
            assert len(result) == 30


if __name__ == "__main__":
    # Run all tests using pytest
    # This ensures proper fixture injection and test discovery
    import sys

    # Run specific test methods if needed
    test_methods = [
        "test_batch_limits.py::TestBatchLimits::test_get_pairs_by_pairs_addresses_single_batch",
        "test_batch_limits.py::TestBatchLimits::test_get_pairs_by_pairs_addresses_exceeds_limit",
        "test_batch_limits.py::TestBatchLimits::test_get_pairs_by_pairs_addresses_async_exceeds_limit",
        "test_batch_limits.py::TestBatchLimits::test_get_pairs_by_token_addresses_exceeds_limit",
        "test_batch_limits.py::TestBatchLimits::test_get_pairs_by_token_addresses_within_limit",
        "test_batch_limits.py::TestBatchLimits::test_get_pairs_by_pairs_addresses_empty_list",
        "test_batch_limits.py::TestBatchLimits::test_get_pairs_by_pairs_addresses_exactly_30",
    ]

    # Run all tests in this file with pytest
    exit_code = pytest.main([__file__, "-v", "-s"])

    # Alternative: Run specific tests
    # exit_code = pytest.main([__file__ + "::" + method for method in test_methods] + ["-v", "-s"])

    sys.exit(exit_code)
