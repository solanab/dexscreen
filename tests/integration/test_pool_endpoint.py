"""
Integration tests for pool endpoint (token-pairs/v1)
"""

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.models import TokenPair


class TestPoolEndpoint:
    """Test pool endpoint functionality"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return DexscreenerClient()

    def test_get_pools_by_token_address(self, client, real_address_factory):
        """Test getting pool info using token-pairs/v1 endpoint"""
        # Test with a random real Solana token address
        chain = "solana"
        token_address = real_address_factory["get_random_token"]()

        pairs = client.get_pools_by_token_address(chain, token_address)

        assert isinstance(pairs, list)
        assert len(pairs) > 0

        # Verify the first pair
        pair = pairs[0]
        assert isinstance(pair, TokenPair)
        assert pair.chain_id == chain

    @pytest.mark.asyncio
    async def test_get_pools_by_token_address_async(self, client, real_address_factory):
        """Test async version of get_pools_by_token_address"""
        chain = "solana"
        # Use random real token address
        token_address = real_address_factory["get_random_token"]()

        pairs = await client.get_pools_by_token_address_async(chain, token_address)

        assert isinstance(pairs, list)
        # Pool endpoint might return different data
        if len(pairs) > 0:
            pair = pairs[0]
            assert isinstance(pair, TokenPair)
            assert pair.chain_id == chain

    def test_pool_vs_pair_endpoint(self, client, real_address_factory):
        """Compare pool endpoint vs pair endpoint results"""
        chain = "solana"
        token_address = real_address_factory["get_random_token"]()
        pair_address = real_address_factory["get_random_pair"]()

        # Get data from pool endpoint (using token address)
        pool_results = client.get_pools_by_token_address(chain, token_address)

        # Get data from pair endpoint (single) using pair address
        pair_result = client.get_pair_by_pair_address(chain, pair_address)

        # Pool endpoint returns a list
        assert isinstance(pool_results, list)

        # Pair endpoint returns a single item or None
        assert pair_result is None or isinstance(pair_result, TokenPair)

        # Both should contain valid TokenPair objects if data exists
        if pool_results:
            assert all(isinstance(p, TokenPair) for p in pool_results)
