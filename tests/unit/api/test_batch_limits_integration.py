"""
Unit tests for batch query limits in DexscreenerClient.

These tests verify the batching behavior and limit enforcement without making actual API calls.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen.api.client import DexscreenerClient
from dexscreen.core.exceptions import TooManyItemsError


class TestBatchLimits:
    """Test batch limit enforcement for various endpoints"""

    @pytest.fixture
    def valid_pair_data(self):
        """Create valid TokenPair data"""
        return {
            "chainId": "solana",
            "dexId": "raydium",
            "url": "https://dexscreener.com/solana/pair123",
            "pairAddress": "pair123",
            "baseToken": {
                "address": "tokenA",
                "name": "Token A",
                "symbol": "TOKA",
            },
            "quoteToken": {
                "address": "tokenB",
                "name": "Token B",
                "symbol": "TOKB",
            },
            "priceNative": 1.5,
            "priceUsd": 2.0,
            "txns": {
                "m5": {"buys": 10, "sells": 5},
                "h1": {"buys": 100, "sells": 50},
                "h6": {"buys": 600, "sells": 300},
                "h24": {"buys": 2400, "sells": 1200},
            },
            "volume": {"m5": 1000.0, "h1": 5000.0, "h6": 30000.0, "h24": 120000.0},
            "priceChange": {"m5": 0.1, "h1": 0.5, "h6": 1.0, "h24": 2.0},
        }

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client"""
        mock = Mock()
        mock.request = Mock(return_value={"pairs": []})
        mock.request_async = AsyncMock(return_value={"pairs": []})
        return mock

    @pytest.fixture
    def client(self, mock_http_client):
        """Create client with mocked HTTP clients"""
        client = DexscreenerClient()
        # Patch both rate-limited clients
        client._client_60rpm = mock_http_client
        client._client_300rpm = mock_http_client
        return client

    @patch("dexscreen.core.validators.validate_address")
    def test_pair_endpoint_batching(self, mock_validate_address, client, valid_pair_data):
        """Test that pair endpoint correctly enforces 30 pair limit"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        # Test addresses - mix of real and fake addresses
        real_pairs = [
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv",
            "7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX",
        ]

        # Generate 35 addresses (mix real and fake)
        addresses = real_pairs + [f"FakeAddress{i:040d}" for i in range(32)]

        # This should raise TooManyItemsError since we're exceeding 30 addresses
        with pytest.raises(TooManyItemsError) as exc_info:
            client.get_pairs_by_pairs_addresses("solana", addresses)

        assert "Too many pair_addresses: 35. Maximum allowed: 30" in str(exc_info.value)

        # Test with 30 addresses (within limit)
        addresses_30 = addresses[:30]

        # Mock response with some fake pairs
        mock_pairs = []
        for _i, addr in enumerate(real_pairs[:2]):
            pair_data = valid_pair_data.copy()
            pair_data["pairAddress"] = addr
            mock_pairs.append(pair_data)

        client._client_300rpm.request.return_value = {"pairs": mock_pairs}

        pairs = client.get_pairs_by_pairs_addresses("solana", addresses_30)
        assert len(pairs) == 2  # Should get back the mocked pairs
        assert client._client_300rpm.request.called

    @patch("dexscreen.core.validators.validate_address")
    def test_token_endpoint_batching(self, mock_validate_address, client, valid_pair_data):
        """Test that token endpoint enforces 30 token limit"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        # Use 50 token addresses
        tokens = [
            "So11111111111111111111111111111111111111112",  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
            "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # POPCAT
        ] + [f"FakeToken{i:040d}" for i in range(45)]

        # This should raise TooManyItemsError since we're exceeding 30 tokens
        with pytest.raises(TooManyItemsError) as exc_info:
            client.get_pairs_by_token_addresses("solana", tokens)

        assert "Too many token_addresses: 50. Maximum allowed: 30" in str(exc_info.value)

        # Test with 1 token (uses different code path)
        client._client_300rpm.request.return_value = [valid_pair_data]

        single_pairs = client.get_pairs_by_token_addresses("solana", [tokens[0]])
        assert len(single_pairs) == 1

    @patch("dexscreen.core.validators.validate_address")
    def test_exact_30_pairs(self, mock_validate_address, client, valid_pair_data):
        """Test with exactly 30 pair addresses"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        # Use some real pair addresses
        addresses = [
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv",
        ] + [f"FakeAddress{i:040d}" for i in range(28)]

        # Mock response
        mock_pairs = []
        for addr in addresses[:2]:
            pair_data = valid_pair_data.copy()
            pair_data["pairAddress"] = addr
            mock_pairs.append(pair_data)

        client._client_300rpm.request.return_value = {"pairs": mock_pairs}

        pairs = client.get_pairs_by_pairs_addresses("solana", addresses[:30])

        # Should get back the mocked pairs
        assert len(pairs) == 2
        assert pairs[0].pair_address == addresses[0]
        assert pairs[1].pair_address == addresses[1]

    def test_empty_addresses(self, client):
        """Test with empty address lists"""
        # Empty list should return empty result without making API call
        pairs = client.get_pairs_by_pairs_addresses("solana", [])
        assert pairs == []
        assert not client._client_300rpm.request.called

        # Reset mock
        client._client_300rpm.request.reset_mock()

        tokens = client.get_pairs_by_token_addresses("solana", [])
        assert tokens == []
        assert not client._client_300rpm.request.called

    @pytest.mark.asyncio
    @patch("dexscreen.core.validators.validate_address")
    async def test_pair_endpoint_batching_async(self, mock_validate_address, client):
        """Test async version of pair endpoint batch limits"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        # Generate 35 addresses
        addresses = [f"Address{i:040d}" for i in range(35)]

        # Should raise TooManyItemsError for > 30 addresses
        with pytest.raises(TooManyItemsError) as exc_info:
            await client.get_pairs_by_pairs_addresses_async("solana", addresses)

        assert "Too many pair_addresses: 35. Maximum allowed: 30" in str(exc_info.value)

        # Test with 30 addresses (within limit)
        client._client_300rpm.request_async.return_value = {"pairs": []}
        pairs = await client.get_pairs_by_pairs_addresses_async("solana", addresses[:30])
        assert pairs == []

    @pytest.mark.asyncio
    @patch("dexscreen.core.validators.validate_address")
    async def test_token_endpoint_batching_async(self, mock_validate_address, client):
        """Test async version of token endpoint batch limits"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        # Use 50 token addresses
        tokens = [f"Token{i:040d}" for i in range(50)]

        # Should raise TooManyItemsError for > 30 tokens
        with pytest.raises(TooManyItemsError) as exc_info:
            await client.get_pairs_by_token_addresses_async("solana", tokens)

        assert "Too many token_addresses: 50. Maximum allowed: 30" in str(exc_info.value)

    @patch("dexscreen.core.validators.validate_address")
    def test_30_tokens_within_limit(self, mock_validate_address, client, valid_pair_data):
        """Test with exactly 30 token addresses"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        tokens = [f"Token{i:040d}" for i in range(30)]

        # Mock response for multiple tokens (returns array directly)
        mock_pairs = []
        for i in range(5):
            pair_data = valid_pair_data.copy()
            pair_data["pairAddress"] = f"pair{i}"
            pair_data["baseToken"]["symbol"] = f"TOKEN{i}"
            mock_pairs.append(pair_data)

        client._client_300rpm.request.return_value = mock_pairs

        pairs = client.get_pairs_by_token_addresses("solana", tokens)
        assert len(pairs) == 5
        assert client._client_300rpm.request.called

        # Verify the correct endpoint was called
        call_args = client._client_300rpm.request.call_args
        assert call_args[0][0] == "GET"
        assert "tokens/v1/solana/" in call_args[0][1]
        assert all(token in call_args[0][1] for token in tokens)

    @patch("dexscreen.core.validators.validate_address")
    def test_exact_31_pairs_exceeds_limit(self, mock_validate_address, client):
        """Test that exactly 31 pairs triggers the limit error"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        addresses = [f"Address{i:040d}" for i in range(31)]

        with pytest.raises(TooManyItemsError) as exc_info:
            client.get_pairs_by_pairs_addresses("ethereum", addresses)

        assert "Too many pair_addresses: 31. Maximum allowed: 30" in str(exc_info.value)
        assert exc_info.value.count == 31
        assert exc_info.value.max_allowed == 30

    def test_invalid_chain_validation_happens_first(self, client):
        """Test that chain validation happens before batch limit check"""
        # Even with too many addresses, invalid chain should be caught first
        addresses = [f"Address{i:040d}" for i in range(35)]

        # InvalidChainIdError should be raised before TooManyItemsError
        from dexscreen.core.exceptions import InvalidChainIdError

        with pytest.raises(InvalidChainIdError):
            client.get_pairs_by_pairs_addresses("invalid_chain", addresses)

    @patch("dexscreen.core.validators.validate_address")
    def test_pairs_endpoint_deduplication(self, mock_validate_address, client, valid_pair_data):
        """Test that token endpoint deduplicates pairs"""
        # Make validate_address return the input unchanged
        mock_validate_address.side_effect = lambda x, *args: x

        # Create duplicate pair data
        pair1 = valid_pair_data.copy()
        pair1["pairAddress"] = "pair123"
        pair1["chainId"] = "solana"

        pair2 = valid_pair_data.copy()
        pair2["pairAddress"] = "pair123"  # Same pair address
        pair2["chainId"] = "solana"  # Same chain

        pair3 = valid_pair_data.copy()
        pair3["pairAddress"] = "pair456"  # Different pair
        pair3["chainId"] = "solana"

        # Mock response with duplicates
        client._client_300rpm.request.return_value = [pair1, pair2, pair3]

        pairs = client.get_pairs_by_token_addresses(
            "solana", ["token0000000000000000000000000000000000001", "token0000000000000000000000000000000000002"]
        )

        # Should only get 2 unique pairs
        assert len(pairs) == 2
        pair_addresses = [p.pair_address for p in pairs]
        assert "pair123" in pair_addresses
        assert "pair456" in pair_addresses
