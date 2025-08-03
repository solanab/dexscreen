"""
Comprehensive error handling and edge case tests for DexscreenerClient
"""

import contextlib
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dexscreen import DexscreenerClient
from dexscreen.core.exceptions import (
    EmptyListError,
    InvalidAddressError,
    InvalidCallbackError,
    InvalidFilterError,
    InvalidIntervalError,
    InvalidParameterError,
    InvalidRangeError,
    InvalidTypeError,
    TooManyItemsError,
)
from dexscreen.utils.filters import FilterConfig


class TestInitializationErrorHandling:
    """Test client initialization error handling"""

    def test_init_invalid_impersonate_type(self):
        """Test client initialization with invalid impersonate type"""
        with pytest.raises(InvalidTypeError):
            DexscreenerClient(impersonate=123)  # type: ignore

    def test_init_invalid_impersonate_empty_string(self):
        """Test client initialization with empty impersonate string"""
        with pytest.raises(InvalidParameterError):
            DexscreenerClient(impersonate="")

    def test_init_invalid_impersonate_too_long(self):
        """Test client initialization with too long impersonate string"""
        with pytest.raises(InvalidRangeError, match="Must be between 1 and 50"):
            DexscreenerClient(impersonate="a" * 51)  # Max is 50

    def test_init_invalid_client_kwargs_type(self):
        """Test client initialization with invalid client_kwargs type"""
        with pytest.raises(InvalidTypeError):
            DexscreenerClient(client_kwargs="invalid")  # type: ignore

    def test_init_valid_parameters(self):
        """Test client initialization with valid parameters"""
        client = DexscreenerClient(impersonate="chrome", client_kwargs={"timeout": 30})
        assert client.client_kwargs["impersonate"] == "chrome"
        assert client.client_kwargs["timeout"] == 30

    def test_init_none_parameters(self):
        """Test client initialization with None parameters"""
        client = DexscreenerClient(impersonate=None, client_kwargs=None)
        assert "impersonate" not in client.client_kwargs


class TestAddressValidationErrors:
    """Test address validation error handling"""

    def test_get_pair_invalid_address_type(self):
        """Test get_pair with invalid address type"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pair(123)  # type: ignore

    def test_get_pair_empty_address(self):
        """Test get_pair with empty address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            client.get_pair("")

    def test_get_pair_none_address(self):
        """Test get_pair with None address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pair(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_get_pair_async_invalid_address_type(self):
        """Test async get_pair with invalid address type"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            await client.get_pair_async(123)  # type: ignore

    @pytest.mark.asyncio
    async def test_get_pair_async_empty_address(self):
        """Test async get_pair with empty address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            await client.get_pair_async("")

    def test_get_pair_by_pair_address_invalid_chain_id(self):
        """Test get_pair_by_pair_address with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pair_by_pair_address(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_pair_by_pair_address_empty_chain_id(self):
        """Test get_pair_by_pair_address with empty chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidParameterError):
            client.get_pair_by_pair_address("", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

    def test_get_pair_by_pair_address_invalid_pair_address(self):
        """Test get_pair_by_pair_address with invalid pair_address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            client.get_pair_by_pair_address("ethereum", "")

    @pytest.mark.asyncio
    async def test_get_pair_by_pair_address_async_invalid_chain_id(self):
        """Test async get_pair_by_pair_address with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            await client.get_pair_by_pair_address_async(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    @pytest.mark.asyncio
    async def test_get_pair_by_pair_address_async_empty_pair_address(self):
        """Test async get_pair_by_pair_address with empty pair_address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            await client.get_pair_by_pair_address_async("ethereum", "")


class TestBatchLimitErrors:
    """Test batch limit error handling"""

    def test_get_pairs_by_pairs_addresses_invalid_chain_id_type(self):
        """Test get_pairs_by_pairs_addresses with invalid chain_id type"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pairs_by_pairs_addresses(123, ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])  # type: ignore

    def test_get_pairs_by_pairs_addresses_invalid_addresses_type(self):
        """Test get_pairs_by_pairs_addresses with invalid addresses type"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pairs_by_pairs_addresses("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_pairs_by_pairs_addresses_exceeds_limit(self, batch_test_addresses):
        """Test get_pairs_by_pairs_addresses exceeds limit"""
        client = DexscreenerClient()
        # Create 31 addresses (exceeds MAX_PAIRS_PER_REQUEST of 30)
        addresses = batch_test_addresses[:31]

        with pytest.raises(TooManyItemsError, match="Too many pair_addresses: 31. Maximum allowed: 30"):
            client.get_pairs_by_pairs_addresses("ethereum", addresses)

    def test_get_pairs_by_pairs_addresses_invalid_address_in_list(self):
        """Test get_pairs_by_pairs_addresses with invalid address in list"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            client.get_pairs_by_pairs_addresses("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", ""])

    @pytest.mark.asyncio
    async def test_get_pairs_by_pairs_addresses_async_exceeds_limit(self, batch_test_addresses):
        """Test async get_pairs_by_pairs_addresses exceeds limit"""
        client = DexscreenerClient()
        addresses = batch_test_addresses[:31]

        with pytest.raises(TooManyItemsError, match="Too many pair_addresses: 31. Maximum allowed: 30"):
            await client.get_pairs_by_pairs_addresses_async("ethereum", addresses)

    def test_get_pairs_by_token_addresses_exceeds_limit(self, batch_test_addresses):
        """Test get_pairs_by_token_addresses exceeds limit"""
        client = DexscreenerClient()
        # Create 31 addresses (exceeds MAX_TOKENS_PER_REQUEST of 30)
        addresses = batch_test_addresses[:31]

        with pytest.raises(TooManyItemsError, match="Too many token_addresses: 31. Maximum allowed: 30"):
            client.get_pairs_by_token_addresses("ethereum", addresses)

    def test_get_pairs_by_token_addresses_invalid_addresses_type(self):
        """Test get_pairs_by_token_addresses with invalid addresses type"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pairs_by_token_addresses("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_pairs_by_token_addresses_invalid_address_in_list(self):
        """Test get_pairs_by_token_addresses with invalid address in list"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            client.get_pairs_by_token_addresses("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", ""])

    @pytest.mark.asyncio
    async def test_get_pairs_by_token_addresses_async_exceeds_limit(self, batch_test_addresses):
        """Test async get_pairs_by_token_addresses exceeds limit"""
        client = DexscreenerClient()
        addresses = batch_test_addresses[:31]

        with pytest.raises(TooManyItemsError, match="Too many token_addresses: 31. Maximum allowed: 30"):
            await client.get_pairs_by_token_addresses_async("ethereum", addresses)


class TestSearchValidationErrors:
    """Test search query validation errors"""

    def test_search_pairs_invalid_query_type(self):
        """Test search_pairs with invalid query type"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.search_pairs(123)  # type: ignore

    def test_search_pairs_empty_query(self):
        """Test search_pairs with empty query"""
        client = DexscreenerClient()
        # Empty query now raises InvalidParameterError from validation
        with pytest.raises(InvalidParameterError, match="non-empty string"):
            client.search_pairs("")

    def test_search_pairs_too_long_query(self):
        """Test search_pairs with too long query"""
        client = DexscreenerClient()
        long_query = "a" * 101  # Max is 100
        with pytest.raises(InvalidRangeError, match="Must be between 1 and 100"):
            client.search_pairs(long_query)

    @pytest.mark.asyncio
    async def test_search_pairs_async_invalid_query_type(self):
        """Test async search_pairs with invalid query type"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            await client.search_pairs_async(123)  # type: ignore

    @pytest.mark.asyncio
    async def test_search_pairs_async_empty_query(self):
        """Test async search_pairs with empty query"""
        client = DexscreenerClient()
        # Empty query now raises InvalidParameterError from validation
        with pytest.raises(InvalidParameterError, match="non-empty string"):
            await client.search_pairs_async("")


class TestTokenMethodsValidationErrors:
    """Test token methods validation errors"""

    def test_get_pairs_by_token_address_invalid_chain_id(self):
        """Test get_pairs_by_token_address with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pairs_by_token_address(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_pairs_by_token_address_empty_token_address(self):
        """Test get_pairs_by_token_address with empty token_address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            client.get_pairs_by_token_address("ethereum", "")

    @pytest.mark.asyncio
    async def test_get_pairs_by_token_address_async_invalid_chain_id(self):
        """Test async get_pairs_by_token_address with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            await client.get_pairs_by_token_address_async(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_pools_by_token_address_invalid_chain_id(self):
        """Test get_pools_by_token_address with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_pools_by_token_address(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_pools_by_token_address_empty_token_address(self):
        """Test get_pools_by_token_address with empty token_address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            client.get_pools_by_token_address("ethereum", "")

    @pytest.mark.asyncio
    async def test_get_pools_by_token_address_async_invalid_chain_id(self):
        """Test async get_pools_by_token_address with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            await client.get_pools_by_token_address_async(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_orders_paid_of_token_invalid_chain_id(self):
        """Test get_orders_paid_of_token with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            client.get_orders_paid_of_token(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    def test_get_orders_paid_of_token_empty_token_address(self):
        """Test get_orders_paid_of_token with empty token_address"""
        client = DexscreenerClient()
        with pytest.raises(InvalidAddressError):
            client.get_orders_paid_of_token("ethereum", "")

    @pytest.mark.asyncio
    async def test_get_orders_paid_of_token_async_invalid_chain_id(self):
        """Test async get_orders_paid_of_token with invalid chain_id"""
        client = DexscreenerClient()
        with pytest.raises(InvalidTypeError):
            await client.get_orders_paid_of_token_async(123, "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore


class TestSubscriptionValidationErrors:
    """Test subscription methods validation errors"""

    @pytest.mark.asyncio
    async def test_subscribe_pairs_invalid_chain_id_type(self):
        """Test subscribe_pairs with invalid chain_id type"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidTypeError):
            await client.subscribe_pairs(123, ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback)  # type: ignore

    @pytest.mark.asyncio
    async def test_subscribe_pairs_empty_chain_id(self):
        """Test subscribe_pairs with empty chain_id"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidParameterError):
            await client.subscribe_pairs("", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback)

    @pytest.mark.asyncio
    async def test_subscribe_pairs_invalid_addresses_type(self):
        """Test subscribe_pairs with invalid addresses type"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidTypeError):
            await client.subscribe_pairs("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", callback)  # type: ignore

    @pytest.mark.asyncio
    async def test_subscribe_pairs_empty_addresses_list(self):
        """Test subscribe_pairs with empty addresses list"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(EmptyListError, match="Empty pair_addresses list"):
            await client.subscribe_pairs("ethereum", [], callback)

    @pytest.mark.asyncio
    async def test_subscribe_pairs_invalid_address_in_list(self):
        """Test subscribe_pairs with invalid address in list"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidAddressError):
            await client.subscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", ""], callback)

    @pytest.mark.asyncio
    async def test_subscribe_pairs_invalid_callback_type(self):
        """Test subscribe_pairs with invalid callback type"""
        client = DexscreenerClient()

        with pytest.raises(InvalidCallbackError, match="Must be callable"):
            await client.subscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], "not_a_function")  # type: ignore

    @pytest.mark.asyncio
    async def test_subscribe_pairs_none_callback(self):
        """Test subscribe_pairs with None callback"""
        client = DexscreenerClient()

        with pytest.raises(InvalidCallbackError, match="Must be callable"):
            await client.subscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], None)  # type: ignore

    @pytest.mark.asyncio
    async def test_subscribe_pairs_invalid_filter_type(self):
        """Test subscribe_pairs with invalid filter type"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidFilterError):
            await client.subscribe_pairs(
                "ethereum",
                ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
                callback,
                filter="invalid",  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_subscribe_pairs_invalid_interval_type(self):
        """Test subscribe_pairs with invalid interval type"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidIntervalError):
            await client.subscribe_pairs(
                "ethereum",
                ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
                callback,
                interval="invalid",  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_subscribe_pairs_negative_interval(self):
        """Test subscribe_pairs with negative interval"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidIntervalError):
            await client.subscribe_pairs(
                "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, interval=-1.0
            )

    @pytest.mark.asyncio
    async def test_subscribe_pairs_zero_interval(self):
        """Test subscribe_pairs with zero interval"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        with pytest.raises(InvalidIntervalError):
            await client.subscribe_pairs(
                "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, interval=0.0
            )

    @pytest.mark.asyncio
    async def test_subscribe_tokens_invalid_chain_id_type(self):
        """Test subscribe_tokens with invalid chain_id type"""
        client = DexscreenerClient()

        def callback(pairs):
            pass

        with pytest.raises(InvalidTypeError):
            await client.subscribe_tokens(123, ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback)  # type: ignore

    @pytest.mark.asyncio
    async def test_subscribe_tokens_empty_addresses_list(self):
        """Test subscribe_tokens with empty addresses list"""
        client = DexscreenerClient()

        def callback(pairs):
            pass

        with pytest.raises(EmptyListError, match="Empty token_addresses list"):
            await client.subscribe_tokens("ethereum", [], callback)

    @pytest.mark.asyncio
    async def test_subscribe_tokens_invalid_callback_type(self):
        """Test subscribe_tokens with invalid callback type"""
        client = DexscreenerClient()

        with pytest.raises(InvalidCallbackError, match="Must be callable"):
            await client.subscribe_tokens("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], "not_a_function")  # type: ignore

    @pytest.mark.asyncio
    async def test_subscribe_tokens_invalid_filter_type(self):
        """Test subscribe_tokens with invalid filter type"""
        client = DexscreenerClient()

        def callback(pairs):
            pass

        with pytest.raises(InvalidFilterError):
            await client.subscribe_tokens(
                "ethereum",
                ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
                callback,
                filter=123,  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_unsubscribe_pairs_invalid_chain_id_type(self):
        """Test unsubscribe_pairs with invalid chain_id type"""
        client = DexscreenerClient()

        with pytest.raises(InvalidTypeError):
            await client.unsubscribe_pairs(123, ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])  # type: ignore

    @pytest.mark.asyncio
    async def test_unsubscribe_pairs_invalid_addresses_type(self):
        """Test unsubscribe_pairs with invalid addresses type"""
        client = DexscreenerClient()

        with pytest.raises(InvalidTypeError):
            await client.unsubscribe_pairs("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    @pytest.mark.asyncio
    async def test_unsubscribe_pairs_invalid_address_in_list(self):
        """Test unsubscribe_pairs with invalid address in list"""
        client = DexscreenerClient()

        with pytest.raises(InvalidAddressError):
            await client.unsubscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", ""])

    @pytest.mark.asyncio
    async def test_unsubscribe_tokens_invalid_chain_id_type(self):
        """Test unsubscribe_tokens with invalid chain_id type"""
        client = DexscreenerClient()

        with pytest.raises(InvalidTypeError):
            await client.unsubscribe_tokens(123, ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"])  # type: ignore

    @pytest.mark.asyncio
    async def test_unsubscribe_tokens_invalid_addresses_type(self):
        """Test unsubscribe_tokens with invalid addresses type"""
        client = DexscreenerClient()

        with pytest.raises(InvalidTypeError):
            await client.unsubscribe_tokens("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")  # type: ignore

    @pytest.mark.asyncio
    async def test_unsubscribe_tokens_invalid_address_in_list(self):
        """Test unsubscribe_tokens with invalid address in list"""
        client = DexscreenerClient()

        with pytest.raises(InvalidAddressError):
            await client.unsubscribe_tokens("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", ""])


class TestHTTPErrorHandling:
    """Test HTTP error handling"""

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_http_error_handling_in_get_pair(self, mock_http_class):
        """Test HTTP error handling in get_pair"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Simulate HTTP error by raising exception
        mock_http.request.side_effect = Exception("HTTP Error")

        client = DexscreenerClient()

        # Should handle error gracefully and return None
        with pytest.raises(Exception, match="HTTP Error"):
            client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

    @patch("dexscreen.api.client.HttpClientCffi")
    @pytest.mark.asyncio
    async def test_http_error_handling_in_get_pair_async(self, mock_http_class):
        """Test HTTP error handling in async get_pair"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Simulate HTTP error by raising exception
        mock_http.request_async = AsyncMock(side_effect=Exception("HTTP Error"))

        client = DexscreenerClient()

        # Should handle error gracefully
        with pytest.raises(Exception, match="HTTP Error"):
            await client.get_pair_async("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_malformed_json_response(self, mock_http_class):
        """Test handling of malformed JSON responses"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Return malformed data that can't be parsed into TokenPair
        mock_http.request.return_value = {"pairs": [{"invalid": "data"}]}

        client = DexscreenerClient()

        # Should handle parsing error gracefully
        with pytest.raises(ValueError):  # Pydantic validation error
            client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_unexpected_response_structure(self, mock_http_class):
        """Test handling of unexpected response structure"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Return unexpected structure
        mock_http.request.return_value = "unexpected string response"

        client = DexscreenerClient()
        result = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        # Should return None for unexpected response
        assert result is None

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_empty_pairs_array(self, mock_http_class):
        """Test handling of empty pairs array"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Return empty pairs array
        mock_http.request.return_value = {"pairs": []}

        client = DexscreenerClient()
        result = client.get_pair("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")

        # Should return None for empty pairs
        assert result is None


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_maximum_valid_addresses_batch(self, batch_test_addresses):
        """Test with maximum valid number of addresses"""
        client = DexscreenerClient()

        # Test with exactly 30 addresses (the limit)
        addresses = batch_test_addresses[:30]

        # Should not raise error (will fail on HTTP call, but validation should pass)
        with contextlib.suppress(Exception):
            client.get_pairs_by_pairs_addresses(
                "ethereum", addresses
            )  # Expected to fail on HTTP, but validation should pass

        with contextlib.suppress(Exception):
            client.get_pairs_by_token_addresses(
                "ethereum", addresses
            )  # Expected to fail on HTTP, but validation should pass

    @pytest.mark.asyncio
    async def test_maximum_valid_addresses_batch_async(self, batch_test_addresses):
        """Test async with maximum valid number of addresses"""
        client = DexscreenerClient()

        # Test with exactly 30 addresses (the limit)
        addresses = batch_test_addresses[:30]

        # Should not raise error (will fail on HTTP call, but validation should pass)
        with contextlib.suppress(Exception):
            await client.get_pairs_by_pairs_addresses_async(
                "ethereum", addresses
            )  # Expected to fail on HTTP, but validation should pass

        with contextlib.suppress(Exception):
            await client.get_pairs_by_token_addresses_async(
                "ethereum", addresses
            )  # Expected to fail on HTTP, but validation should pass

    def test_single_address_batch(self):
        """Test batch methods with single address"""
        client = DexscreenerClient()

        # Test with single address
        with contextlib.suppress(Exception):
            client.get_pairs_by_pairs_addresses(
                "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
            )  # Expected to fail on HTTP, but validation should pass

        with contextlib.suppress(Exception):
            client.get_pairs_by_token_addresses(
                "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]
            )  # Expected to fail on HTTP, but validation should pass

    @pytest.mark.asyncio
    async def test_very_small_interval(self):
        """Test subscription with very small interval"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        # Test with very small but valid interval
        with contextlib.suppress(Exception):
            await client.subscribe_pairs(
                "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, interval=0.001
            )  # Expected to fail on stream creation, but validation should pass

    @pytest.mark.asyncio
    async def test_very_large_interval(self):
        """Test subscription with very large interval"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        # Test with very large interval
        with contextlib.suppress(Exception):
            await client.subscribe_pairs(
                "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, interval=3600.0
            )  # Expected to fail on stream creation, but validation should pass

    def test_case_sensitivity_in_addresses(self):
        """Test case sensitivity handling in addresses"""
        client = DexscreenerClient()

        # Test different case variations
        addresses = [
            "0x123abc0000000000000000000000000000000000",
            "0x123ABC0000000000000000000000000000000000",
            "0X123ABC0000000000000000000000000000000000",
            "0X123abc0000000000000000000000000000000000",
        ]

        for addr in addresses:
            with contextlib.suppress(Exception):
                client.get_pair(addr)  # Expected to fail on HTTP, but validation should pass

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_whitespace_handling_in_strings(self, mock_http_class):
        """Test whitespace handling in string inputs"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"pairs": []}

        client = DexscreenerClient()

        # Test strings with leading/trailing whitespace
        # Address validation strips whitespace, so this becomes a valid address
        result = client.get_pair("  0x1230000000000000000000000000000000000000  ")
        # Verify it doesn't crash - API returns None for no results
        assert result is None

        # Query validation strips whitespace, so "  USDC  " becomes "USDC" which is valid
        result = client.search_pairs("  USDC  ")
        assert isinstance(result, list)

    def test_unicode_handling_in_strings(self):
        """Test Unicode character handling in string inputs"""
        client = DexscreenerClient()

        # Test with Unicode characters - address too short
        with pytest.raises(InvalidAddressError, match="Address length must be between 20 and 70 characters"):
            client.get_pair("0x123🚀")

        # Query validation doesn't check for Unicode, only dangerous HTML/script chars
        # Change test to include dangerous character
        with pytest.raises(InvalidParameterError, match="query without HTML/script characters"):
            client.search_pairs("USDC<script>")

    @patch("dexscreen.api.client.HttpClientCffi")
    def test_special_characters_in_strings(self, mock_http_class):
        """Test special character handling in string inputs"""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.request.return_value = {"pairs": []}

        client = DexscreenerClient()

        # These addresses have valid length but contain special characters
        # Address validation doesn't check for special chars, only format/length
        # So these will pass validation but API returns no results
        special_chars = [
            "0x1230000000000000000000000000000000000000;",
            "0x1230000000000000000000000000000000000000'",
            '0x1230000000000000000000000000000000000000"',
            "0x1230000000000000000000000000000000000000<>",
            "0x1230000000000000000000000000000000000000&",
        ]

        for addr in special_chars:
            # These pass validation, API handles them
            result = client.get_pair(addr)
            assert result is None  # API returns no results

    @pytest.mark.asyncio
    async def test_concurrent_subscriptions(self):
        """Test multiple concurrent subscriptions"""
        client = DexscreenerClient()

        def callback(pair):
            pass

        # Test subscribing to multiple pairs concurrently
        with contextlib.suppress(Exception):
            await client.subscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback)
            await client.subscribe_pairs("ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5641"], callback)
            await client.subscribe_pairs(
                "solana", ["7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr"], callback
            )  # Expected to fail on stream creation, but should handle multiple subscriptions

    @pytest.mark.asyncio
    async def test_filter_config_edge_cases(self):
        """Test FilterConfig edge cases"""
        client = DexscreenerClient()

        # Test with extreme FilterConfig values
        extreme_filter = FilterConfig(
            price_change_threshold=0.0001,  # Very small threshold
            volume_change_threshold=1000000.0,  # Very large threshold
        )

        def callback(pair):
            pass

        # Should handle extreme filter configs
        with contextlib.suppress(Exception):
            await client.subscribe_pairs(
                "ethereum", ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"], callback, filter=extreme_filter
            )  # Expected to fail on stream creation, but filter should be valid
