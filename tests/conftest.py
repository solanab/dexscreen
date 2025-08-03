"""
pytest configuration file
Provides test fixtures and configuration

Organization structure:
1. Infrastructure configuration - Test environment setup
2. Test Data - Static test data
3. Mock Object Factories - Create mock objects without preset behavior
4. Mock Behavior Presets - Mocks with specific behaviors
5. Data Factories - Dynamically create test data
6. Integration Test Config
"""

import asyncio

import pytest

# ========== 1. Infrastructure Configuration ==========


@pytest.fixture
def event_loop():
    """Create event loop for async testing"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ========== 2. Test Data (Test Data - Pure Data) ==========


@pytest.fixture
def sample_token_pair_data():
    """Provide sample token pair data"""
    return {
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
            "m5": {"buys": 10, "sells": 5},
            "h1": {"buys": 100, "sells": 50},
            "h6": {"buys": 600, "sells": 300},
            "h24": {"buys": 2400, "sells": 1200},
        },
        "volume": {"m5": 50000.0, "h1": 250000.0, "h6": 1500000.0, "h24": 6000000.0},
        "priceChange": {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3},
        "liquidity": {"usd": 10000000.0, "base": 4265.5, "quote": 5000000.0},
        "fdv": 50000000.0,
    }


@pytest.fixture
def mock_http_response():
    """Provide mock HTTP response"""
    return {
        "schemaVersion": "1.0.0",
        "pair": {
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
            "priceNative": "0.0004265",
            "priceUsd": "2345.67",
            "txns": {
                "m5": {"buys": 10, "sells": 5},
                "h1": {"buys": 100, "sells": 50},
                "h6": {"buys": 600, "sells": 300},
                "h24": {"buys": 2400, "sells": 1200},
            },
            "volume": {"m5": 50000, "h1": 250000, "h6": 1500000, "h24": 6000000},
            "priceChange": {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3},
            "liquidity": {"usd": 10000000, "base": 4265.5, "quote": 5000000},
            "fdv": 50000000,
            "pairCreatedAt": 1625097600000,
            "info": {
                "imageUrl": "https://assets.dexscreen.com/tokens/ethereum/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.png",
                "websites": [{"label": "Website", "url": "https://www.circle.com/usdc"}],
                "socials": [{"type": "twitter", "url": "https://twitter.com/circlepay"}],
            },
        },
    }


@pytest.fixture
def mock_polling_update():
    """Provide mock polling update data"""
    return {
        "type": "pair",
        "pair": {
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
            "priceUsd": "2346.00",
            "priceNative": "0.0004266",
            "txns": {
                "m5": {"buys": 11, "sells": 6},
                "h1": {"buys": 101, "sells": 51},
                "h6": {"buys": 601, "sells": 301},
                "h24": {"buys": 2401, "sells": 1201},
            },
            "volume": {"m5": 51000, "h1": 251000, "h6": 1510000, "h24": 6010000},
            "priceChange": {"m5": 0.6, "h1": -0.1, "h6": 1.6, "h24": -2.2},
            "liquidity": {"usd": 10010000, "base": 4266, "quote": 5001000},
        },
    }


@pytest.fixture
def base_token_data():
    """Provide base token data"""
    return {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "name": "USD Coin", "symbol": "USDC"}


@pytest.fixture
def quote_token_data():
    """Provide quote token data"""
    return {"address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "name": "Wrapped Ether", "symbol": "WETH"}


@pytest.fixture
def transaction_stats_data():
    """Provide transaction statistics data"""
    return {
        "m5": {"buys": 10, "sells": 5},
        "h1": {"buys": 100, "sells": 50},
        "h6": {"buys": 600, "sells": 300},
        "h24": {"buys": 2400, "sells": 1200},
    }


@pytest.fixture
def volume_data():
    """Provide volume data"""
    return {"m5": 50000.0, "h1": 250000.0, "h6": 1500000.0, "h24": 6000000.0}


@pytest.fixture
def price_change_data():
    """Provide price change data"""
    return {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3}


@pytest.fixture
def liquidity_data():
    """Provide liquidity data"""
    return {"usd": 10000000.0, "base": 4265.5, "quote": 5000000.0}


@pytest.fixture
def minimal_pair_data(base_token_data, quote_token_data):
    """Provide minimal token pair data (required fields only)"""
    return {
        "chainId": "ethereum",
        "dexId": "uniswap",
        "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        "baseToken": base_token_data,
        "quoteToken": quote_token_data,
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


# ========== 3. Mock Object Factories (Mock Factories - No Behavior) ==========


@pytest.fixture
def mock_client():
    """Provide basic mock DexscreenerClient - no preset behavior"""
    from unittest.mock import Mock

    from dexscreen import DexscreenerClient

    # Only create mock, don't set any behavior
    client = Mock(spec=DexscreenerClient)
    return client


@pytest.fixture
def mock_http_client():
    """Provide basic mock HTTP client - no preset behavior"""
    from unittest.mock import AsyncMock, Mock

    client = Mock()
    # Only ensure methods exist, don't set return values
    client.request = Mock()
    client.request_async = AsyncMock()
    client.get_pair_by_pair_address_async = AsyncMock()
    return client


@pytest.fixture
def mock_client_factory():
    """Mock client factory - for creating multiple independent mocks"""
    from unittest.mock import Mock

    from dexscreen import DexscreenerClient

    def _create():
        return Mock(spec=DexscreenerClient)

    return _create


# ========== 5. Data Factories (Data Factories) ==========


@pytest.fixture
def mock_api_response_factory(transaction_stats_data, volume_data, price_change_data):
    """
    API response data factory - dynamically create API response data

    Usage:
    1. Default response: response = factory()
    2. Custom response: response = factory([{...custom pair data...}])
    3. Parameterized response: response = factory(num_pairs=2, chain_id="solana", base_address="0x1230000000000000000000000000000000000000", quote_address="0x4567890123456789012345678901234567890123")
    """

    def _create_response(pairs_data=None, num_pairs=1, chain_id="ethereum", base_address=None, quote_address=None):
        if pairs_data is not None:
            # Use provided pairs_data (backward compatibility)
            return {"pairs": pairs_data}

        # Generate pairs based on parameters
        generated_pairs = []
        for i in range(num_pairs):
            base_addr = base_address or f"0x{(i + 1) * 111:040x}"
            quote_addr = quote_address or f"0x{(i + 1) * 222:040x}"
            pair_addr = f"0x{(i + 1) * 333:040x}"

            pair_data = {
                "chainId": chain_id,
                "dexId": "uniswap" if chain_id == "ethereum" else "raydium" if chain_id == "solana" else "pancakeswap",
                "url": f"https://test.com/{pair_addr}",
                "pairAddress": pair_addr,
                "baseToken": {"address": base_addr, "name": f"Token A{i + 1}", "symbol": f"TKA{i + 1}"},
                "quoteToken": {"address": quote_addr, "name": f"Token B{i + 1}", "symbol": f"TKB{i + 1}"},
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
            generated_pairs.append(pair_data)

        return {"pairs": generated_pairs}

    return _create_response


@pytest.fixture
def common_test_addresses():
    """Provide common test addresses"""
    return {
        "ethereum": {
            "usdc_weth_pair": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
            "usdc_token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "weth_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        },
        "solana": {
            "jupiter_token": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "sol_token": "So11111111111111111111111111111111111111112",
            "usdc_token": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        },
    }


@pytest.fixture
def real_solana_token_addresses():
    # Active Solana 32 token addresses (found via search API)
    return {
        "tokens": [
            "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # POPCAT
            "F6qoefQq4iCBLoNZ34RjEqHjHkD8vtmoRSdw9Nd55J1k",  # SHIB
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "31k88G5Mq7ptbRDf3AM13HAq6wRQHXHikR8hik7wPygk",  # GP
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # JitoSOL
            "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # RAY
            "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",  # WIF
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
            "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",  # JTO
            "HhJpBhRRn4g56VsyLuT8DL5Bv31HkXqsrahTTUCZeZg4",  # $MYRO
            "6MQpbiTC2YcogidTmKqMLK82qvE9z5QEm7EP3AEDpump",  # MASK
            "EkM5JPDagT71XDZCjdnz45PUHbNPBdNL45N2NKCHbyGR",  # PEPE
            "9TY6DUg1VSssYH5tFE95qoq5hnAGFak4w3cn72sJNCoV",  # DOGE
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  # JUP
            "9Vo93nxu8gpY5i54sB3okxCqCTou4Asxg817A63B1GPf",  # Doge
            "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",  # PYTH
            "B5WTLaRwaUQpKk7ir1wniNB6m5o8GgMrimhKMYan2R6B",  # Pepe
            "Dn4noZ5jgGfkntzcQSUZ8czkreiZ1ForXYoV2H8Dm7S1",  # USDT
            "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5",  # MEW
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
            "So11111111111111111111111111111111111111112",  # SOL
            "ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82",  # BOME
            "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",  # ORCA
            "ATLASXmbPQxBUYbxPsV97usA3fPQYEqzQBUHgiFCUsXx",  # ATLAS
            "METAewgxyPbgwsseH8T16a39CQ5VyVxZi9zXiDPY18m",  # META
            "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # WETH
            "AGFEad2et2ZJif9jaGpdMixQqvW5i81aBdvKe7PHNfz3",  # FTT
            "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",  # SRM
            "4ENNdRkWNf1SxmYpzZawG9Q7WUncBzBrrp7ghyCX7Pmp",  # GMT token
            "CWE8jPTUYhdCTZYWPTe1o5DFqfdjzWKc9WKz6rSjQUdG",  # LINK
            "Saber2gLauYim4Mvftnrasomsv6NvAuncvMEZwcLpD1",  # SBR
        ],
    }


@pytest.fixture
def real_solana_pairs_addresses():
    # Active 36 Solana pair addresses (found via search API)
    return {
        "pairs": [
            "739FaSK16AUx5gBXjxoweJF71ioQHQmWm1x3pickfLjT",  # Doge/USDC - $307M liquidity
            "879F697iuDJGMevRkRcnW21fcXiAeLJK1ffsw2ATebce",  # MEW/SOL - $31M liquidity
            "DSUvc5qf5LJHHV5e2tD184ixotSnCnwj7i4jJa4Xsrmt",  # BOME/SOL - $28M liquidity
            "EP2ib6dYdEeqD8MfE2ezHCxX3kP3K2eLKkirfPm5eyMx",  # $WIF/SOL - $15M liquidity
            "FRhB8L7Y9Qq41qZXYLtC2nw8An1RJfLLxRF2x9RwLLMo",  # POPCAT/SOL - $11M liquidity
            "HcjZvfeSNJbNkfLD4eEcRBr96AD3w1GpmMppaeRZf7ur",  # mSOL/SOL - $10M liquidity
            "AVs9TA4nWDzfPJE9gGVNJMVhcQy3V9PGazuz33BfG2RA",  # RAY/SOL - $9M liquidity
            "2AXXcN6oN9bBT5owwmTH53C7QHUXvhLeu718Kqt8rvY2",  # RAY/SOL - $7M liquidity
            "6UmmUiYoBjSrhakAobJw8BvkmJtDVxaeBtbt7rxWo1mg",  # RAY/USDC - $7M liquidity
            "G2FiE1yn9N9ZJx5e1E2LxxMnHvb1H3hCuHLPfKJ98smA",  # JTO/JitoSOL - $5M liquidity
            "9vNKzrrHAjqjuTGLjCBo9Ai4edMYgP9dsG4tFZ2hF251",  # GP/USDC - $4M liquidity
            "3ne4mWqdYuNiYrYZC9TrA3FcfuFdErghH97vNPbjicr1",  # Bonk/SOL - $3M liquidity
            "EowpY5U8gXssLrsQ5zxchWtHtbvdiAyvXKQ7Wk4mNfTt",  # MEW/SOL - $2M liquidity
            "DVa7Qmb5ct9RCpaU7UTpSaf3GVMYz17vNVU67XpdCRut",  # RAY/USDT - $1M liquidity
            "76KUM4kqR9CP193ir9wksgNu5m1tRxPikfHdPaNhKwiY",  # PEPE/USDC - $1M liquidity
            "C1MgLojNLWBKADvu9BHdtgzz1oZX4dZ5zGdGcgvvW8Wz",  # JUP/SOL - $1M liquidity
            "5WGYajM1xtLy3QrLHGSX4YPwsso3jrjEsbU1VivUErzk",  # $MYRO/USDC - $1M liquidity
            "5zpyutJu9ee6jFymDGoK7F6S5Kczqtc9FomP3ueKuyA9",  # Bonk/SOL - $1M liquidity
            "HBS7a3br8GMMWuqVa7VB3SMFa7xVi1tSFdoF5w4ZZ3kS",  # POPCAT/USDC - $1M liquidity
            "AqJ5JYNb7ApkJwvbuXxPnTtKeuizjvC1s2fkp382y9LC",  # mSOL/USDC - $1M liquidity
            "GNfeVT5vSWgLYtzveexZJ2Ki9NBtTTzoHAd9oGvoJKW8",  # mSOL/USDC - $600k liquidity
            "BNFMGftsKAn36v5uaNonJyWSbpXxWVsia3G53tczf8Jm",  # USDT/USDT - $600k liquidity
            "ENrEBzFdNp8mZ11j1wXYZ5mbyX5yA3Z4t9ALbBKtZ2RD",  # MEW/SOL - $600k liquidity
            "GWPLjamb5ZxrGbTsYNWW7V3p1pAMryZSfaPFTdaEsWgC",  # MASK/SOL - $600k liquidity
            "8KJRGQJG5CSfwiZbqwcYBRQebi36Pxp2ZXSN1SZtounE",  # MEW/SOL - $400k liquidity
            "FCEnSxyJfRSKsz6tASUENCsfGwKgkH6YuRn1AMmyHhZn",  # Pepe/SOL - $400k liquidity
            "61R1ndXxvsWXXkWSyNkCxnzwd3zUNB8Q2ibmkiLPC8ht",  # RAY/USDC - $370k liquidity
            "HQcY5n2zP6rW74fyFEhWeBd3LnJpBcZechkvJpmdb8cx",  # mSOL/SOL - $365k liquidity
            "8EzbUfvcRT1Q6RL462ekGkgqbxsPmwC5FMLQZhSPMjJ3",  # mSOL/SOL - $352k liquidity
            "AHTTzwf3GmVMJdxWM8v2MSxyjZj8rQR6hyAC3g9477Yj",  # POPCAT/SOL - $307k liquidity
            "6oFWm7KPLfxnwMb3z5xwBoXNSPP3JJyirAPqPSiVcnsp",  # Bonk/SOL - $298k liquidity
            "9n3dSLrERZQp95dHXywft7xV8D8xnGFLaUHtEhQVaXaC",  # PYTH/SOL - $275k liquidity
            "3pvmL7M24uqzudAxUYmvixtkWTC5yaDhTUSyB8cewnJK",  # DOGE/SOL - $256k liquidity
            "GhDgKWmdrj6af23AqsBJhWu6NyLdLuYG7B4gkjZR4tVk",  # Bonk/USDC - $216k liquidity
            "EZVkeboWeXygtq8LMyENHyXdF5wpYrtExRNH9UwB1qYw",  # JUP/SOL - $216k liquidity
            "14bLC2KcZ2yFyCDSzHsNemoXUGf9fCmgqQ8jeHEfr3Ed",  # SHIB/SOL - $211k liquidity
        ],
    }


@pytest.fixture
def simple_test_pair_data(transaction_stats_data, volume_data, price_change_data):
    """Provide simplified test token pair data (for unit testing)"""
    return {
        "chainId": "ethereum",
        "dexId": "uniswap",
        "url": "https://test.com",
        "pairAddress": "0x1230000000000000000000000000000000000000",
        "baseToken": {"address": "0xabc0000000000000000000000000000000000000", "name": "Token A", "symbol": "TKA"},
        "quoteToken": {"address": "0xdef0000000000000000000000000000000000000", "name": "Token B", "symbol": "TKB"},
        "priceNative": "1.0",
        "priceUsd": "100.0",
        "txns": transaction_stats_data,
        "volume": volume_data,
        "priceChange": price_change_data,
        "liquidity": {"usd": 500000.0, "base": 5000.0, "quote": 5000.0},
    }


@pytest.fixture
def create_test_token_pair():
    """Provide factory function for creating test TokenPair instances"""

    def _create(chain_id, pair_address, base_symbol="TOKEN", quote_symbol="WETH", price_usd="100"):
        import datetime as dt

        from dexscreen.core.models import (
            BaseToken,
            Liquidity,
            PairTransactionCounts,
            PriceChangePeriods,
            TokenPair,
            TransactionCount,
            VolumeChangePeriods,
        )

        # Create proper model objects
        base_token = BaseToken(
            address="0x1000000000000000000000000000000000000000", name=base_symbol, symbol=base_symbol
        )

        quote_token = BaseToken(
            address="0x2000000000000000000000000000000000000000", name=quote_symbol, symbol=quote_symbol
        )

        transaction_count = TransactionCount(buys=1, sells=1)
        transactions = PairTransactionCounts(
            m5=transaction_count,
            h1=transaction_count,
            h6=transaction_count,
            h24=transaction_count,
        )

        volume = VolumeChangePeriods(m5=100.0)
        price_change = PriceChangePeriods(m5=1.0, h1=1.0, h6=1.0, h24=1.0)
        liquidity = Liquidity(usd=1000000.0, base=1000.0, quote=1000.0)

        # Convert timestamp to datetime
        pair_created_at = dt.datetime.fromtimestamp(1625097600000 / 1000, tz=dt.timezone.utc)

        return TokenPair(
            chainId=chain_id,
            dexId="uniswap",
            url=f"https://dexscreener.com/{chain_id}/{pair_address}",
            pairAddress=pair_address,
            baseToken=base_token,
            quoteToken=quote_token,
            priceNative=1.0,
            priceUsd=float(price_usd),
            txns=transactions,
            volume=volume,
            priceChange=price_change,
            liquidity=liquidity,
            fdv=1000000.0,
            pairCreatedAt=pair_created_at,
        )

    return _create


@pytest.fixture
def enable_integration_tests(monkeypatch):
    """Fixture for enabling integration tests"""
    monkeypatch.setenv("RUN_INTEGRATION_TESTS", "1")


@pytest.fixture
def integration_test_env(monkeypatch):
    """Configure integration test environment variables"""
    monkeypatch.setenv("RUN_INTEGRATION_TESTS", "1")
    # Can add other environment variables needed for integration tests
    # monkeypatch.setenv("API_TIMEOUT", "30")
    # monkeypatch.setenv("MAX_RETRIES", "3")


# ========== 4. Pre-configured Mocks (Pre-configured Mocks with Default Behavior) ==========


@pytest.fixture
def mock_http_session_success():
    """Provide HTTP Session configured with successful response"""
    from unittest.mock import Mock

    session = Mock()
    # Preset successful response behavior
    mock_response = Mock()
    mock_response.content = b'{"status": "ok"}'
    mock_response.raise_for_status = Mock()
    mock_response.headers = {"content-type": "application/json"}
    mock_response.status_code = 200
    session.request.return_value = mock_response
    session.get.return_value = mock_response
    session.post.return_value = mock_response

    return session


@pytest.fixture
def mock_async_http_session_success():
    """Provide async HTTP Session configured with successful response"""
    from unittest.mock import AsyncMock, Mock

    session = AsyncMock()
    # Preset successful response behavior
    mock_response = AsyncMock()
    mock_response.content = b'{"status": "ok"}'
    mock_response.raise_for_status = Mock()
    mock_response.headers = {"content-type": "application/json"}
    mock_response.status_code = 200
    session.request.return_value = mock_response
    session.get.return_value = mock_response
    session.post.return_value = mock_response

    return session


@pytest.fixture
def mock_http_session():
    """Basic HTTP Session mock - no preset behavior (backward compatible)"""
    from unittest.mock import Mock

    return Mock()


@pytest.fixture
def mock_async_http_session():
    """Basic async HTTP Session mock - no preset behavior (backward compatible)"""
    from unittest.mock import AsyncMock

    return AsyncMock()


@pytest.fixture
def mock_polling_stream(mock_http_client):
    """Provide mock PollingStream"""
    from unittest.mock import Mock

    from dexscreen.stream.polling import PollingStream

    stream = Mock(spec=PollingStream)
    stream.dexscreener_client = mock_http_client
    stream.interval = 0.5
    stream.running = False
    stream.tasks = []
    stream.subscriptions = {}

    return stream


@pytest.fixture
def batch_test_addresses():
    """Provide batch test addresses - returns Ethereum addresses by default"""
    return [f"0x{i:040x}" for i in range(100)]


@pytest.fixture
def batch_test_addresses_by_chain():
    """Provide batch test addresses by chain"""
    return {
        "ethereum": [f"0x{i:040x}" for i in range(100)],
        "solana": [f"{'A' * 32}{'BCDEFGHJKLMNPQRSTUVWXYZ'[i % 23]}{i % 9 + 1!s}" for i in range(100)],
        "bsc": [f"0xbsc{i:037x}" for i in range(100)],
    }


@pytest.fixture
def error_response_data():
    """Provide error response data"""
    return {
        "rate_limit": {"error": "Rate limit exceeded", "retry_after": 60},
        "not_found": {"error": "Resource not found", "status": 404},
        "server_error": {"error": "Internal server error", "status": 500},
        "invalid_request": {"error": "Invalid request parameters", "status": 400},
    }


@pytest.fixture
def real_address_factory(real_solana_token_addresses, real_solana_pairs_addresses, common_test_addresses):
    """
    Factory function: randomly select real test addresses

    Usage:
    - get_random_token(chain) - Get random token address for specified chain
    - get_random_pair() - Get random Solana pair address
    - get_random_tokens(chain, count) - Get multiple random token addresses
    - get_specific_token(chain, name) - Get specific token address
    """
    import random

    def get_random_token(chain="solana"):
        """Get random token address for specified chain"""
        if chain == "solana":
            return random.choice(real_solana_token_addresses["tokens"])
        elif chain in common_test_addresses:
            # Get token addresses from common_test_addresses
            tokens = [v for k, v in common_test_addresses[chain].items() if "token" in k]
            return random.choice(tokens) if tokens else None
        return None

    def get_random_pair():
        """Get random Solana pair address"""
        return random.choice(real_solana_pairs_addresses["pairs"])

    def get_random_tokens(chain="solana", count=2):
        """Get multiple unique random token addresses"""
        if chain == "solana":
            tokens = real_solana_token_addresses["tokens"]
            # Ensure count doesn't exceed available tokens
            count = min(count, len(tokens))
            return random.sample(tokens, count)
        elif chain in common_test_addresses:
            tokens = [v for k, v in common_test_addresses[chain].items() if "token" in k]
            count = min(count, len(tokens))
            return random.sample(tokens, count) if tokens else []
        return []

    def get_specific_token(chain="solana", name=None):
        """Get specific token address"""
        if chain == "solana" and name:
            # Specific well-known token mapping
            known_tokens = {
                "usdc": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "sol": "So11111111111111111111111111111111111111112",
                "jup": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
                "ray": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
                "bonk": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            }
            return known_tokens.get(name.lower())
        elif chain in common_test_addresses:
            # Search from common_test_addresses
            for key, value in common_test_addresses[chain].items():
                if name and name.lower() in key.lower():
                    return value
        return None

    def get_random_pairs(count=2):
        """Get multiple unique random pair addresses"""
        pairs = real_solana_pairs_addresses["pairs"]
        count = min(count, len(pairs))
        return random.sample(pairs, count)

    # Return factory method dictionary
    return {
        "get_random_token": get_random_token,
        "get_random_pair": get_random_pair,
        "get_random_tokens": get_random_tokens,
        "get_specific_token": get_specific_token,
        "get_random_pairs": get_random_pairs,
    }
