"""
Comprehensive tests for DexscreenerClient - Part 2
Tests remaining methods and edge cases
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.models import OrderInfo, TokenInfo, TokenPair


class TestSearchAndTokenMethods:
    """Test search and token-related methods"""

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_search_pairs_success(self, mock_http_class, mock_api_response_factory):
        """Test successful search_pairs"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_http.request.return_value = mock_api_response_factory(
            chain_id="ethereum",
            base_address="0xabc0000000000000000000000000000000000000",
            quote_address="0xdef0000000000000000000000000000000000000",
        )

        client = DexscreenerClient()
        result = client.search_pairs("USDC")

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == f"0x{1 * 333:040x}"
        mock_http.request.assert_called_once_with("GET", "latest/dex/search?q=USDC")

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_search_pairs_none_response(self, mock_http_class):
        """Test search_pairs with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.search_pairs("USDC")

        assert result == []

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_search_pairs_no_pairs(self, mock_http_class):
        """Test search_pairs with no pairs in response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"other": "data"}

        client = DexscreenerClient()
        result = client.search_pairs("NOTFOUND")

        assert result == []

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_search_pairs_async_success(self, mock_http_class, mock_api_response_factory):
        """Test successful async search_pairs"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_http.request_async = AsyncMock(
            return_value=mock_api_response_factory(
                chain_id="ethereum",
                base_address="0xabc0000000000000000000000000000000000000",
                quote_address="0xdef0000000000000000000000000000000000000",
            )
        )

        client = DexscreenerClient()
        result = await client.search_pairs_async("USDC")

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == f"0x{1 * 333:040x}"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_search_pairs_async_none_response(self, mock_http_class):
        """Test async search_pairs with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.search_pairs_async("USDC")

        assert result == []


class TestTokenInfoMethods:
    """Test token info methods"""

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_latest_token_profiles_success(self, mock_http_class):
        """Test successful get_latest_token_profiles"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        token_data = [
            {
                "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "chainId": "ethereum",
                "tokenAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "amount": 1000.0,
                "totalAmount": 10000.0,
                "icon": "https://example.com/token.png",
                "header": "Test Token",
                "description": "A test token",
                "links": [],
            }
        ]
        mock_http.request.return_value = token_data

        client = DexscreenerClient()
        result = client.get_latest_token_profiles()

        assert len(result) == 1
        assert isinstance(result[0], TokenInfo)
        assert result[0].token_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        mock_http.request.assert_called_once_with("GET", "token-profiles/latest/v1")

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_latest_token_profiles_none_response(self, mock_http_class):
        """Test get_latest_token_profiles with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_latest_token_profiles()

        assert result == []

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_latest_token_profiles_async_success(self, mock_http_class):
        """Test successful async get_latest_token_profiles"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        token_data = [
            {
                "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "chainId": "ethereum",
                "tokenAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "amount": 1000.0,
                "totalAmount": 10000.0,
                "icon": "https://example.com/token.png",
                "header": "Test Token",
                "description": "A test token",
                "links": [],
            }
        ]
        mock_http.request_async = AsyncMock(return_value=token_data)

        client = DexscreenerClient()
        result = await client.get_latest_token_profiles_async()

        assert len(result) == 1
        assert isinstance(result[0], TokenInfo)
        assert result[0].token_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_latest_token_profiles_async_none_response(self, mock_http_class):
        """Test async get_latest_token_profiles with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.get_latest_token_profiles_async()

        assert result == []

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_latest_boosted_tokens_success(self, mock_http_class):
        """Test successful get_latest_boosted_tokens"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        token_data = [
            {
                "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "chainId": "ethereum",
                "tokenAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "amount": 2000.0,
                "totalAmount": 20000.0,
                "icon": "https://example.com/boost.png",
                "header": "Boosted Token",
                "description": "A boosted token",
                "links": [],
            }
        ]
        mock_http.request.return_value = token_data

        client = DexscreenerClient()
        result = client.get_latest_boosted_tokens()

        assert len(result) == 1
        assert isinstance(result[0], TokenInfo)
        assert result[0].token_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        mock_http.request.assert_called_once_with("GET", "token-boosts/latest/v1")

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_latest_boosted_tokens_none_response(self, mock_http_class):
        """Test get_latest_boosted_tokens with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_latest_boosted_tokens()

        assert result == []

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_latest_boosted_tokens_async_success(self, mock_http_class):
        """Test successful async get_latest_boosted_tokens"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        token_data = [
            {
                "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "chainId": "ethereum",
                "tokenAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "amount": 2000.0,
                "totalAmount": 20000.0,
                "icon": "https://example.com/boost.png",
                "header": "Boosted Token",
                "description": "A boosted token",
                "links": [],
            }
        ]
        mock_http.request_async = AsyncMock(return_value=token_data)

        client = DexscreenerClient()
        result = await client.get_latest_boosted_tokens_async()

        assert len(result) == 1
        assert isinstance(result[0], TokenInfo)
        assert result[0].token_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_latest_boosted_tokens_async_none_response(self, mock_http_class):
        """Test async get_latest_boosted_tokens with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.get_latest_boosted_tokens_async()

        assert result == []

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_tokens_most_active_success(self, mock_http_class):
        """Test successful get_tokens_most_active"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        token_data = [
            {
                "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "chainId": "ethereum",
                "tokenAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "amount": 5000.0,
                "totalAmount": 50000.0,
                "icon": "https://example.com/active.png",
                "header": "Active Token",
                "description": "An active token",
                "links": [],
            }
        ]
        mock_http.request.return_value = token_data

        client = DexscreenerClient()
        result = client.get_tokens_most_active()

        assert len(result) == 1
        assert isinstance(result[0], TokenInfo)
        assert result[0].token_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        mock_http.request.assert_called_once_with("GET", "token-boosts/top/v1")

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_tokens_most_active_none_response(self, mock_http_class):
        """Test get_tokens_most_active with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_tokens_most_active()

        assert result == []

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_tokens_most_active_async_success(self, mock_http_class):
        """Test successful async get_tokens_most_active"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        token_data = [
            {
                "url": "https://dexscreener.com/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "chainId": "ethereum",
                "tokenAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "amount": 5000.0,
                "totalAmount": 50000.0,
                "icon": "https://example.com/active.png",
                "header": "Active Token",
                "description": "An active token",
                "links": [],
            }
        ]
        mock_http.request_async = AsyncMock(return_value=token_data)

        client = DexscreenerClient()
        result = await client.get_tokens_most_active_async()

        assert len(result) == 1
        assert isinstance(result[0], TokenInfo)
        assert result[0].token_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_tokens_most_active_async_none_response(self, mock_http_class):
        """Test async get_tokens_most_active with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.get_tokens_most_active_async()

        assert result == []


class TestOrderMethods:
    """Test order-related methods"""

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_orders_paid_of_token_success(self, mock_http_class):
        """Test successful get_orders_paid_of_token"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        order_data = [
            {
                "type": "tokenProfile",
                "status": "paid",
                "paymentTimestamp": 1640995200,
            }
        ]
        mock_http.request.return_value = order_data

        client = DexscreenerClient()
        result = client.get_orders_paid_of_token("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert len(result) == 1
        assert isinstance(result[0], OrderInfo)
        assert result[0].type == "tokenProfile"
        assert result[0].status == "paid"
        assert result[0].payment_timestamp == 1640995200
        mock_http.request.assert_called_once_with(
            "GET", "orders/v1/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_orders_paid_of_token_none_response(self, mock_http_class):
        """Test get_orders_paid_of_token with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_orders_paid_of_token("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_orders_paid_of_token_async_success(self, mock_http_class):
        """Test successful async get_orders_paid_of_token"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        order_data = [
            {
                "type": "tokenProfile",
                "status": "paid",
                "paymentTimestamp": 1640995200,
            }
        ]
        mock_http.request_async = AsyncMock(return_value=order_data)

        client = DexscreenerClient()
        result = await client.get_orders_paid_of_token_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert len(result) == 1
        assert isinstance(result[0], OrderInfo)
        assert result[0].type == "tokenProfile"
        assert result[0].status == "paid"
        assert result[0].payment_timestamp == 1640995200

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_orders_paid_of_token_async_none_response(self, mock_http_class):
        """Test async get_orders_paid_of_token with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.get_orders_paid_of_token_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []


class TestTokenPairMethods:
    """Test token pair-related methods"""

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_token_address_success(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test successful get_pairs_by_token_address"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
        ]
        mock_http.request.return_value = pairs_data

        client = DexscreenerClient()
        result = client.get_pairs_by_token_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        mock_http.request.assert_called_once_with(
            "GET", "tokens/v1/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_token_address_none_response(self, mock_http_class):
        """Test get_pairs_by_token_address with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_pairs_by_token_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_token_address_invalid_response(self, mock_http_class):
        """Test get_pairs_by_token_address with invalid response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"invalid": "response"}

        client = DexscreenerClient()
        result = client.get_pairs_by_token_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pairs_by_token_address_async_success(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test successful async get_pairs_by_token_address"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
        ]
        mock_http.request_async = AsyncMock(return_value=pairs_data)

        client = DexscreenerClient()
        result = await client.get_pairs_by_token_address_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pairs_by_token_address_async_none_response(self, mock_http_class):
        """Test async get_pairs_by_token_address with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.get_pairs_by_token_address_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []

    def test_get_pairs_by_token_addresses_empty_list(self):
        """Test get_pairs_by_token_addresses with empty list"""
        client = DexscreenerClient()
        result = client.get_pairs_by_token_addresses("ethereum", [])
        assert result == []

    def test_get_pairs_by_token_addresses_exceeds_limit(self, batch_test_addresses):
        """Test get_pairs_by_token_addresses exceeds limit"""
        from dexscreen.core.exceptions import TooManyItemsError

        client = DexscreenerClient()
        # Create 31 addresses (exceeds MAX_TOKENS_PER_REQUEST of 30)
        addresses = batch_test_addresses[:31]

        with pytest.raises(TooManyItemsError, match="Too many token_addresses: 31. Maximum allowed: 30"):
            client.get_pairs_by_token_addresses("ethereum", addresses)

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_token_addresses_single_token(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test get_pairs_by_token_addresses with single token (uses different endpoint)"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
        ]
        mock_http.request.return_value = pairs_data

        client = DexscreenerClient()
        result = client.get_pairs_by_token_addresses("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        # Should call single token endpoint
        mock_http.request.assert_called_once_with(
            "GET", "tokens/v1/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_token_addresses_multiple_tokens(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test get_pairs_by_token_addresses with multiple tokens"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            },
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # Duplicate pair address
                "baseToken": {
                    "address": "0xghi0000000000000000000000000000000000000",
                    "name": "Token C",
                    "symbol": "TKC",
                },
                "quoteToken": {"address": "0xdef", "name": "Token B", "symbol": "TKB"},
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            },
        ]
        mock_http.request.return_value = pairs_data

        client = DexscreenerClient()
        result = client.get_pairs_by_token_addresses(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0x4567890123456789012345678901234567890123"]
        )

        # Should deduplicate pairs with same chain_id:pair_address
        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        mock_http.request.assert_called_once_with(
            "GET",
            "tokens/v1/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640,0x4567890123456789012345678901234567890123",
        )

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_token_addresses_none_response(self, mock_http_class):
        """Test get_pairs_by_token_addresses with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_pairs_by_token_addresses(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0x4567890123456789012345678901234567890123"]
        )

        assert result == []

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pairs_by_token_addresses_invalid_response(self, mock_http_class):
        """Test get_pairs_by_token_addresses with invalid response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"invalid": "response"}

        client = DexscreenerClient()
        result = client.get_pairs_by_token_addresses(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0x4567890123456789012345678901234567890123"]
        )

        assert result == []


class TestPoolMethods:
    """Test pool-related methods"""

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pools_by_token_address_success(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test successful get_pools_by_token_address"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
        ]
        mock_http.request.return_value = pairs_data

        client = DexscreenerClient()
        result = client.get_pools_by_token_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        mock_http.request.assert_called_once_with(
            "GET", "token-pairs/v1/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        )

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pools_by_token_address_none_response(self, mock_http_class):
        """Test get_pools_by_token_address with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = None

        client = DexscreenerClient()
        result = client.get_pools_by_token_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_get_pools_by_token_address_invalid_response(self, mock_http_class):
        """Test get_pools_by_token_address with invalid response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"invalid": "response"}

        client = DexscreenerClient()
        result = client.get_pools_by_token_address("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pools_by_token_address_async_success(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test successful async get_pools_by_token_address"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
        ]
        mock_http.request_async = AsyncMock(return_value=pairs_data)

        client = DexscreenerClient()
        result = await client.get_pools_by_token_address_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)
        assert result[0].pair_address == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pools_by_token_address_async_none_response(self, mock_http_class):
        """Test async get_pools_by_token_address with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.get_pools_by_token_address_async("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_pairs_by_token_addresses_async_empty_list(self):
        """Test async get_pairs_by_token_addresses with empty list"""
        client = DexscreenerClient()
        result = await client.get_pairs_by_token_addresses_async("ethereum", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_pairs_by_token_addresses_async_exceeds_limit(self, batch_test_addresses):
        """Test async get_pairs_by_token_addresses exceeds limit"""
        from dexscreen.core.exceptions import TooManyItemsError

        client = DexscreenerClient()
        addresses = batch_test_addresses[:31]

        with pytest.raises(TooManyItemsError, match="Too many token_addresses: 31. Maximum allowed: 30"):
            await client.get_pairs_by_token_addresses_async("ethereum", addresses)

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pairs_by_token_addresses_async_single_token(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test async get_pairs_by_token_addresses with single token"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
        ]
        mock_http.request_async = AsyncMock(return_value=pairs_data)

        client = DexscreenerClient()
        result = await client.get_pairs_by_token_addresses_async(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
        )

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pairs_by_token_addresses_async_multiple_tokens(
        self, mock_http_class, transaction_stats_data, volume_data, price_change_data
    ):
        """Test async get_pairs_by_token_addresses with multiple tokens"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        pairs_data = [
            {
                "chainId": "ethereum",
                "dexId": "uniswap",
                "url": "https://test.com",
                "pairAddress": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                "baseToken": {
                    "address": "0xabc0000000000000000000000000000000000000",
                    "name": "Token A",
                    "symbol": "TKA",
                },
                "quoteToken": {
                    "address": "0xdef0000000000000000000000000000000000000",
                    "name": "Token B",
                    "symbol": "TKB",
                },
                "priceNative": "1.0",
                "priceUsd": "100.0",
                "txns": transaction_stats_data,
                "volume": volume_data,
                "priceChange": price_change_data,
            }
        ]
        mock_http.request_async = AsyncMock(return_value=pairs_data)

        client = DexscreenerClient()
        result = await client.get_pairs_by_token_addresses_async(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0x4567890123456789012345678901234567890123"]
        )

        assert len(result) == 1
        assert isinstance(result[0], TokenPair)

    @pytest.mark.asyncio
    @patch("dexscreen.api.client.HttpClientCffi")
    async def test_get_pairs_by_token_addresses_async_none_response(self, mock_http_class):
        """Test async get_pairs_by_token_addresses with None response"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request_async = AsyncMock(return_value=None)

        client = DexscreenerClient()
        result = await client.get_pairs_by_token_addresses_async(
            "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "0x4567890123456789012345678901234567890123"]
        )

        assert result == []
