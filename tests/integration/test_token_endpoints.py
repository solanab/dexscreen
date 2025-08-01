"""
Integration tests for token endpoints with chain parameter
"""

import asyncio

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.models import TokenPair


class TestTokenEndpoints:
    """Test token-specific endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return DexscreenerClient()

    def test_get_pairs_by_token_address(self, client, real_address_factory):
        """Test getting pairs for a single token on a specific chain"""
        # Test with a random token on Solana
        chain = "solana"
        token_address = real_address_factory["get_specific_token"](chain, "usdc")

        pairs = client.get_pairs_by_token_address(chain, token_address)

        assert isinstance(pairs, list)
        assert len(pairs) > 0

        # Verify the first pair
        pair = pairs[0]
        assert isinstance(pair, TokenPair)
        assert pair.chain_id == chain

        # Check that the token appears in either base or quote
        token_found = (
            pair.base_token.address.lower() == token_address.lower()
            or pair.quote_token.address.lower() == token_address.lower()
        )
        assert token_found

    def test_get_pairs_by_token_addresses(self, client, real_address_factory):
        """Test getting pairs for multiple tokens on a specific chain"""
        chain = "solana"
        # Use specific tokens that are known to have pairs
        usdc_address = real_address_factory["get_specific_token"](chain, "usdc")
        sol_address = real_address_factory["get_specific_token"](chain, "sol")
        tokens = [usdc_address, sol_address]

        pairs = client.get_pairs_by_token_addresses(chain, tokens)

        assert isinstance(pairs, list)
        assert len(pairs) > 0

        # Verify we get pairs for at least one of the tokens
        # Note: We check for at least one because the API might return up to 30 pairs total
        token_addresses = [t.lower() for t in tokens]
        found_tokens = set()

        for pair in pairs:
            if pair.base_token.address.lower() in token_addresses:
                found_tokens.add(pair.base_token.address.lower())
            if pair.quote_token.address.lower() in token_addresses:
                found_tokens.add(pair.quote_token.address.lower())

        # We should find pairs for both tokens since USDC and SOL are very active
        assert len(found_tokens) >= 2, f"Expected pairs for both tokens, but only found pairs for: {found_tokens}"

        # Check for duplicates
        pair_keys = [f"{p.chain_id}:{p.pair_address}" for p in pairs]
        assert len(pair_keys) == len(set(pair_keys)), "Found duplicate pairs"

    @pytest.mark.asyncio
    async def test_get_pairs_by_token_address_async(self, client, real_address_factory):
        """Test async version of get_pairs_by_token_address"""
        chain = "solana"
        token_address = real_address_factory["get_random_token"](chain)

        pairs = await client.get_pairs_by_token_address_async(chain, token_address)

        assert isinstance(pairs, list)
        # Should have pairs for active tokens
        if len(pairs) > 0:
            pair = pairs[0]
            assert isinstance(pair, TokenPair)
            assert pair.chain_id == chain

    @pytest.mark.asyncio
    async def test_subscribe_tokens(self, client, real_address_factory):
        """Test token subscription with chain parameter"""
        chain = "solana"
        token_address = real_address_factory["get_specific_token"](chain, "sol")

        updates = []

        async def callback(pairs):
            updates.append(pairs)

        # Subscribe to token
        await client.subscribe_tokens(chain, [token_address], callback=callback, interval=1.0)

        # Wait for some updates
        await asyncio.sleep(3)

        # Unsubscribe
        await client.unsubscribe_tokens(chain, [token_address])
        await client.close_streams()

        # Verify we got updates
        assert len(updates) > 0

        # Check the update format
        first_update = updates[0]
        assert isinstance(first_update, list)
        assert len(first_update) > 0
        assert all(isinstance(p, TokenPair) for p in first_update)

    def test_cross_chain_token_comparison(self, client, real_address_factory):
        """Test getting the same token (USDC) across different chains"""
        # Focus on Solana for now since we have verified addresses
        usdc_addresses = {
            "solana": real_address_factory["get_specific_token"]("solana", "usdc"),
        }

        results = {}

        for chain, address in usdc_addresses.items():
            try:
                pairs = client.get_pairs_by_token_address(chain, address)
                results[chain] = len(pairs)
            except Exception as e:
                results[chain] = f"Error: {e}"

        # We should get some results
        successful_chains = [c for c, r in results.items() if isinstance(r, int) and r > 0]
        assert len(successful_chains) > 0, f"No successful queries. Results: {results}"

        # Solana should typically have the most pairs
        if "solana" in successful_chains:
            assert results["solana"] > 0

    def test_invalid_chain(self, client):
        """Test handling of invalid chain"""
        # The API might return empty list or handle invalid chains gracefully
        # Let's just test that it doesn't crash
        result = client.get_pairs_by_token_address("invalid_chain", "some_address")

        # Should return empty list for invalid chain
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_active_subscriptions_with_token(self, client, real_address_factory):
        """Test that token subscriptions appear in active subscriptions"""
        chain = "solana"
        token_address = real_address_factory["get_random_token"](chain)

        # Subscribe to a token
        await client.subscribe_tokens(chain, [token_address], callback=lambda pairs: None, interval=5.0)

        # Check active subscriptions
        active = client.get_active_subscriptions()

        # Find our token subscription
        token_subs = [s for s in active if s.get("type") == "token"]
        assert len(token_subs) > 0

        # Verify the subscription details
        sub = token_subs[0]
        assert sub["chain"] == chain
        assert sub["token_address"] == token_address
        assert sub["interval"] == 5.0

        # Clean up
        await client.unsubscribe_tokens(chain, [token_address])
        await client.close_streams()
