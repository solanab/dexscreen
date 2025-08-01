"""
Unit tests for batch query limits in DexscreenerClient
"""

import asyncio
from unittest.mock import patch

import pytest

from dexscreen.api.client import DexscreenerClient


class TestBatchLimits:
    """Test batch query limits for DexscreenerClient"""

    def test_get_pairs_by_pairs_addresses_single_batch(self, create_test_token_pair):
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
            addresses = [f"address{i}" for i in range(10)]
            result = client.get_pairs_by_pairs_addresses("solana", addresses)

            # Should make only one request
            assert mock_request.call_count == 1
            assert len(result) == 10

            # Check the URL contains all addresses
            call_args = mock_request.call_args[0]
            assert "latest/dex/pairs/solana/" in call_args[1]
            assert all(f"address{i}" in call_args[1] for i in range(10))

    def test_get_pairs_by_pairs_addresses_exceeds_limit(self, batch_test_addresses):
        """Test get_pairs_by_pairs_addresses with > 30 addresses raises ValueError"""
        client = DexscreenerClient()

        # Use more than 30 addresses from fixture
        addresses = batch_test_addresses["ethereum"][:40]  # 40 addresses

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            client.get_pairs_by_pairs_addresses("solana", addresses)

        assert "Maximum 30 pair addresses allowed, got 40" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_pairs_by_pairs_addresses_async_exceeds_limit(self):
        """Test async version raises ValueError with > 30 addresses"""
        client = DexscreenerClient()

        addresses = [f"address{i}" for i in range(35)]  # 35 addresses

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await client.get_pairs_by_pairs_addresses_async("solana", addresses)

        assert "Maximum 30 pair addresses allowed, got 35" in str(exc_info.value)

    def test_get_pairs_by_token_addresses_exceeds_limit(self):
        """Test get_pairs_by_token_addresses with > 30 tokens raises ValueError"""
        client = DexscreenerClient()

        # Send 100 token addresses
        addresses = [f"token{i}" for i in range(100)]

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            client.get_pairs_by_token_addresses("solana", addresses)

        assert "Maximum 30 token addresses allowed, got 100" in str(exc_info.value)

    def test_get_pairs_by_token_addresses_within_limit(self):
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
                "txns": {
                    "m5": {"buys": 10, "sells": 5},
                    "h1": {"buys": 100, "sells": 50},
                    "h6": {"buys": 600, "sells": 300},
                    "h24": {"buys": 2400, "sells": 1200},
                },
                "volume": {"m5": 1000.0, "h1": 5000.0, "h6": 30000.0, "h24": 120000.0},
                "priceChange": {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3},
            }
            for i in range(25)  # Less than 30 pairs
        ]

        with patch.object(client._client_300rpm, "request", return_value=mock_response) as mock_request:
            # Send 25 token addresses
            addresses = [f"token{i}" for i in range(25)]
            result = client.get_pairs_by_token_addresses("solana", addresses)

            # Should make only ONE request
            assert mock_request.call_count == 1
            assert len(result) == 25

            # Verify all 25 addresses were sent
            call_args = mock_request.call_args[0]
            assert "tokens/v1/solana/" in call_args[1]
            assert all(f"token{i}" in call_args[1] for i in range(25))

    def test_get_pairs_by_pairs_addresses_empty_list(self):
        """Test get_pairs_by_pairs_addresses with empty address list"""
        client = DexscreenerClient()

        result = client.get_pairs_by_pairs_addresses("solana", [])
        assert result == []

    def test_get_pairs_by_pairs_addresses_exactly_30(self):
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
                    "txns": {
                        "m5": {"buys": 10, "sells": 5},
                        "h1": {"buys": 100, "sells": 50},
                        "h6": {"buys": 600, "sells": 300},
                        "h24": {"buys": 2400, "sells": 1200},
                    },
                    "volume": {"m5": 1000.0, "h1": 5000.0, "h6": 30000.0, "h24": 120000.0},
                    "priceChange": {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3},
                }
                for i in range(30)
            ]
        }

        with patch.object(client._client_300rpm, "request", return_value=mock_response) as mock_request:
            addresses = [f"address{i}" for i in range(30)]
            result = client.get_pairs_by_pairs_addresses("solana", addresses)

            # Should make only one request
            assert mock_request.call_count == 1
            assert len(result) == 30


if __name__ == "__main__":
    # Run sync tests - Note: These would need proper fixture setup in real execution
    test = TestBatchLimits()
    # test.test_get_pairs_by_pairs_addresses_single_batch()  # Requires create_test_token_pair fixture
    # test.test_get_pairs_by_pairs_addresses_exceeds_limit()  # Requires batch_test_addresses fixture
    test.test_get_pairs_by_token_addresses_exceeds_limit()
    test.test_get_pairs_by_token_addresses_within_limit()
    test.test_get_pairs_by_pairs_addresses_empty_list()
    test.test_get_pairs_by_pairs_addresses_exactly_30()

    # Run async test
    asyncio.run(test.test_get_pairs_by_pairs_addresses_async_exceeds_limit())
