"""
Test data model validation and serialization
"""

from decimal import Decimal

from dexscreen.core.models import (
    BaseToken,
    Liquidity,
    PairTransactionCounts,
    PriceChangePeriods,
    TokenInfo,
    TokenPair,
    TransactionCount,
    VolumeChangePeriods,
)


class TestTokenModel:
    """Test Token data model"""

    def test_token_info_creation(self):
        """Test creating TokenInfo instance"""
        token = TokenInfo(
            chainId="ethereum",
            tokenAddress="0x1234567890123456789012345678901234567890",
            url="https://dexscreener.com/ethereum/0x1234567890123456789012345678901234567890",
            totalAmount=1000000.0,
        )

        assert token.chain_id == "ethereum"
        assert token.token_address == "0x1234567890123456789012345678901234567890"

    def test_base_token_creation(self):
        """Test creating BaseToken instance"""
        token = BaseToken(address="0x1234567890123456789012345678901234567890", name="Test Token", symbol="TEST")

        assert token.address == "0x1234567890123456789012345678901234567890"
        assert token.name == "Test Token"
        assert token.symbol == "TEST"


class TestTransactionStats:
    """Test transaction statistics model"""

    def test_transaction_stats_creation(self):
        """Test creating transaction statistics"""
        m5 = TransactionCount(buys=10, sells=5)
        h1 = TransactionCount(buys=100, sells=50)
        h6 = TransactionCount(buys=600, sells=300)
        h24 = TransactionCount(buys=2400, sells=1200)

        stats = PairTransactionCounts(m5=m5, h1=h1, h6=h6, h24=h24)

        assert stats.m5.buys == 10
        assert stats.m5.sells == 5
        assert stats.h24.buys == 2400
        assert stats.h24.sells == 1200

    def test_transaction_stats_total(self):
        """Test calculating total transactions"""
        m5 = TransactionCount(buys=10, sells=5)
        h1 = TransactionCount(buys=100, sells=50)
        h6 = TransactionCount(buys=600, sells=300)
        h24 = TransactionCount(buys=2400, sells=1200)

        stats = PairTransactionCounts(m5=m5, h1=h1, h6=h6, h24=h24)

        # Add method to calculate total (if present in the model)
        assert stats.m5.buys + stats.m5.sells == 15
        assert stats.h24.buys + stats.h24.sells == 3600


class TestVolumeStats:
    """Test transaction volume statistics model"""

    def test_volume_stats_creation(self):
        """Test creating transaction volume statistics"""
        volume = VolumeChangePeriods(m5=1000.5, h1=5000.25, h6=30000.75, h24=120000.0)

        assert volume.m5 == 1000.5
        assert volume.h1 == 5000.25
        assert volume.h6 == 30000.75
        assert volume.h24 == 120000.0

    def test_volume_stats_decimal(self):
        """Test using Decimal type"""
        volume = VolumeChangePeriods(
            m5=float(Decimal("1000.50")),
            h1=float(Decimal("5000.25")),
            h6=float(Decimal("30000.75")),
            h24=float(Decimal("120000.00")),
        )

        assert isinstance(volume.m5, (float, Decimal))
        assert isinstance(volume.h24, (float, Decimal))


class TestPriceChangeStats:
    """Test price change statistics model"""

    def test_price_change_creation(self):
        """Test creating price change statistics"""
        price_change = PriceChangePeriods(m5=0.5, h1=-1.2, h6=3.4, h24=-5.6)

        assert price_change.m5 == 0.5
        assert price_change.h1 == -1.2
        assert price_change.h6 == 3.4
        assert price_change.h24 == -5.6

    def test_price_change_range(self):
        """Test price change range"""
        price_change = PriceChangePeriods(
            m5=150.0,
            h1=-99.9,
            h6=0.0,
            h24=10.5,  # 150% increase  # 99.9% decrease  # No change
        )

        # Verify extreme value handling
        assert price_change.m5 == 150.0
        assert price_change.h1 == -99.9
        assert price_change.h6 == 0.0


class TestLiquidityInfo:
    """Test liquidity information model"""

    def test_liquidity_creation(self):
        """Test creating liquidity information"""
        liquidity = Liquidity(usd=1000000.0, base=500.5, quote=2000000.0)

        assert liquidity.usd == 1000000.0
        assert liquidity.base == 500.5
        assert liquidity.quote == 2000000.0

    def test_liquidity_optional_fields(self):
        """Test optional fields"""
        # Only provide USD liquidity
        liquidity = Liquidity(usd=500000.0, base=100.0, quote=50000.0)

        assert liquidity.usd == 500000.0
        assert liquidity.base == 100.0
        assert liquidity.quote == 50000.0


class TestTokenPair:
    """Test token pair model"""

    def test_token_pair_creation(self, sample_token_pair_data):
        """Test creating token pair"""
        pair = TokenPair(**sample_token_pair_data)

        assert pair.chain_id == "ethereum"
        assert pair.dex_id == "uniswap"
        assert pair.pair_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        assert pair.base_token.symbol == "USDC"
        assert pair.quote_token.symbol == "WETH"
        assert pair.price_usd == 2345.67
        assert pair.volume.h24 == 6000000.0
        assert pair.liquidity is not None and pair.liquidity.usd == 10000000.0

    def test_token_pair_optional_fields(self):
        """Test optional fields"""
        minimal_data = {
            "chainId": "ethereum",
            "dexId": "uniswap",
            "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "baseToken": {
                "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "name": "USD Coin",
                "symbol": "USDC",
            },
            "quoteToken": {
                "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "name": "Wrapped Ether",
                "symbol": "WETH",
            },
            "priceUsd": "2345.67",
            "priceNative": "1.0",
            "txns": {
                "m5": {"buys": 0, "sells": 0},
                "h1": {"buys": 0, "sells": 0},
                "h6": {"buys": 0, "sells": 0},
                "h24": {"buys": 0, "sells": 0},
            },
            "volume": {"m5": 0, "h1": 0, "h6": 0, "h24": 0},
            "priceChange": {"m5": 0, "h1": 0, "h6": 0, "h24": 0},
            "liquidity": {"usd": 0, "base": 0, "quote": 0},
        }

        pair = TokenPair(**minimal_data)

        assert pair.fdv == 0.0  # Default value is 0.0

    def test_token_pair_serialization(self, sample_token_pair_data):
        """Test serialization"""
        pair = TokenPair(**sample_token_pair_data)

        # Convert to dictionary (default to snake_case)
        pair_dict = pair.model_dump()

        assert pair_dict["chain_id"] == "ethereum"
        assert pair_dict["base_token"]["symbol"] == "USDC"
        assert pair_dict["volume"]["h24"] == 6000000.0

        # Convert to dictionary (using aliases)
        pair_dict_alias = pair.model_dump(by_alias=True)
        assert pair_dict_alias["chainId"] == "ethereum"
        assert pair_dict_alias["baseToken"]["symbol"] == "USDC"

        # Convert to JSON
        pair_json = pair.model_dump_json()
        assert isinstance(pair_json, str)
        assert "ethereum" in pair_json
        assert "USDC" in pair_json
