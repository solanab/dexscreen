"""
API response format validation tests
Validate that actual API returned data structure matches our model definitions
"""

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.models import TokenInfo, TokenPair


@pytest.mark.usefixtures("enable_integration_tests")
class TestAPIResponseFormat:
    """Test API response format"""

    @pytest.fixture
    def client(self):
        """Create client instance"""
        return DexscreenerClient(impersonate="chrome136")

    def test_get_pair_response_format(self, client):
        """Test get_pair returned data format"""
        # Use a well-known trading pair
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        if pair is None:
            pytest.skip("API did not return data, possibly a network issue")

        # Validate return type
        assert isinstance(pair, TokenPair)

        # Validate required fields
        assert pair.chain_id is not None
        assert pair.dex_id is not None
        assert pair.url is not None
        assert pair.pair_address is not None

        # Validate token information
        assert pair.base_token is not None
        assert pair.base_token.address is not None
        assert pair.base_token.symbol is not None

        assert pair.quote_token is not None
        assert pair.quote_token.address is not None
        assert pair.quote_token.symbol is not None

        # Validate price information
        assert pair.price_native is not None
        assert pair.price_usd is not None
        assert isinstance(pair.price_usd, (int, float))

        # Validate transaction statistics
        assert pair.transactions is not None
        assert pair.transactions.m5 is not None
        assert pair.transactions.h1 is not None
        assert pair.transactions.h6 is not None
        assert pair.transactions.h24 is not None

        # Validate volume
        assert pair.volume is not None
        assert isinstance(pair.volume.h24, (int, float))

        # Validate price changes
        assert pair.price_change is not None
        assert isinstance(pair.price_change.h24, (int, float))

    def test_get_pairs_by_pairs_addresses_response_format(self, client):
        """Test get_pairs_by_pairs_addresses returned data format"""
        pairs = client.get_pairs_by_pairs_addresses("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        if not pairs:
            pytest.skip("API did not return data")

        # Validate return type
        assert isinstance(pairs, list)
        assert len(pairs) > 0

        # Validate each trading pair
        for pair in pairs:
            assert isinstance(pair, TokenPair)
            assert pair.chain_id == "ethereum"

    def test_search_pairs_response_format(self, client):
        """Test search_pairs returned data format"""
        results = client.search_pairs("USDC")

        if not results:
            pytest.skip("Search did not return results")

        # Validate return type
        assert isinstance(results, list)

        # Validate first few results
        for _i, pair in enumerate(results[:3]):
            assert isinstance(pair, TokenPair)

    def test_get_latest_token_profiles_format(self, client):
        """Test get_latest_token_profiles returned data format"""
        profiles = client.get_latest_token_profiles()

        if not profiles:
            pytest.skip("API did not return token profiles")

        # Validate return type
        assert isinstance(profiles, list)

        # Validate first profile
        profile = profiles[0]
        assert isinstance(profile, TokenInfo)
        assert profile.chain_id is not None
        assert profile.token_address is not None
        assert profile.url is not None

    @pytest.mark.asyncio
    async def test_async_methods_format(self, client):
        """Test async methods return format"""
        # Test async get_pair
        pair = await client.get_pair_async("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        if pair:
            assert isinstance(pair, TokenPair)

    def test_optional_fields_handling(self, client):
        """Test optional fields handling"""
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        if not pair:
            pytest.skip("API did not return data")

        # These fields may be None

        # Should not error even if None
        if pair.liquidity:
            assert hasattr(pair.liquidity, "usd")
            assert hasattr(pair.liquidity, "base")
            assert hasattr(pair.liquidity, "quote")


class TestDataConsistency:
    """Test data consistency"""

    @pytest.fixture
    def client(self):
        return DexscreenerClient()

    def test_price_consistency(self, client):
        """Test price data consistency"""
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        if not pair:
            pytest.skip("API did not return data")

        # Price should be positive
        assert pair.price_usd > 0
        assert float(pair.price_native) > 0

        # Volume should be non-negative
        assert pair.volume.h24 >= 0
        assert pair.volume.h6 >= 0
        assert pair.volume.h1 >= 0
        assert pair.volume.m5 >= 0

        # Time period relationships should be reasonable
        # 24-hour volume should be >= 6-hour volume
        if pair.volume.h24 > 0 and pair.volume.h6 > 0:
            assert pair.volume.h24 >= pair.volume.h6

    def test_transaction_count_consistency(self, client):
        """Test transaction count consistency"""
        pair = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        if not pair or not pair.transactions:
            pytest.skip("API did not return transaction data")

        # Transaction count should be non-negative integers
        assert pair.transactions.h24.buys >= 0
        assert pair.transactions.h24.sells >= 0

        # 24-hour transaction count should be >= 6-hour transaction count
        if pair.transactions.h24.buys > 0 and pair.transactions.h6.buys > 0:
            assert pair.transactions.h24.buys >= pair.transactions.h6.buys
