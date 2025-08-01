"""
简化的模型测试
"""

from dexscreen.core.models import BaseToken, Liquidity, TokenInfo, TokenPair, TransactionCount


class TestModels:
    """测试数据模型"""

    def test_base_token(self):
        """测试 BaseToken 模型"""
        token = BaseToken(address="0x1234567890123456789012345678901234567890", name="Test Token", symbol="TEST")

        assert token.address == "0x1234567890123456789012345678901234567890"
        assert token.name == "Test Token"
        assert token.symbol == "TEST"

    def test_token_info(self):
        """测试 TokenInfo 模型"""
        info = TokenInfo(
            chainId="ethereum",
            tokenAddress="0x1234567890123456789012345678901234567890",
            url="https://dexscreener.com/ethereum/0x1234567890123456789012345678901234567890",
            totalAmount=1000000.0,
        )

        assert info.chain_id == "ethereum"
        assert info.token_address == "0x1234567890123456789012345678901234567890"

    def test_liquidity(self):
        """测试 Liquidity 模型"""
        liquidity = Liquidity(usd=1000000.50, base=500.25, quote=2000.75)

        assert liquidity.usd == 1000000.50
        assert liquidity.base == 500.25
        assert liquidity.quote == 2000.75

    def test_transaction_count(self):
        """测试 TransactionCount 模型"""
        count = TransactionCount(buys=100, sells=80)

        assert count.buys == 100
        assert count.sells == 80

    def test_token_pair_minimal(self):
        """测试 TokenPair 最小必需字段"""
        # 创建最小的有效 TokenPair
        pair_data = {
            "chainId": "ethereum",
            "dexId": "uniswap",
            "url": "https://dexscreener.com/ethereum/test",
            "pairAddress": "0x123",
            "baseToken": {"address": "0xabc", "name": "Token A", "symbol": "TKA"},
            "quoteToken": {"address": "0xdef", "name": "Token B", "symbol": "TKB"},
            "priceNative": "1.5",
            "priceUsd": "3000",
            "txns": {
                "m5": {"buys": 10, "sells": 5},
                "h1": {"buys": 100, "sells": 50},
                "h6": {"buys": 600, "sells": 300},
                "h24": {"buys": 2400, "sells": 1200},
            },
            "volume": {"h24": 1000000, "h6": 250000, "h1": 50000, "m5": 5000},
            "priceChange": {"h24": 10.5, "h6": 5.2, "h1": 1.1, "m5": 0.5},
        }

        pair = TokenPair(**pair_data)

        assert pair.chain_id == "ethereum"
        assert pair.dex_id == "uniswap"
        assert pair.base_token.symbol == "TKA"
        assert pair.quote_token.symbol == "TKB"
        assert pair.price_usd == 3000.0
