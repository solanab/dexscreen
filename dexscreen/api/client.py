"""
Simplified Dexscreener client with clean API
"""

import asyncio
from typing import Any, Callable, Optional, Union

from ..core.http import HttpClientCffi
from ..core.models import OrderInfo, TokenInfo, TokenPair
from ..stream.polling import PollingStream
from ..utils.filters import FilterConfig, TokenPairFilter


class DexscreenerClient:
    """
    Simplified Dexscreener client with clean unified API
    """

    # API limits
    MAX_PAIRS_PER_REQUEST = 30
    MAX_TOKENS_PER_REQUEST = 30

    def __init__(self, impersonate: Optional[str] = None, client_kwargs: Optional[dict[str, Any]] = None):
        """
        Initialize Dexscreener client.

        Args:
            impersonate: Browser to impersonate (default: None, uses random market-share based selection)
            client_kwargs: Optional kwargs to pass to curl_cffi clients.
        """
        # Setup client kwargs
        self.client_kwargs = client_kwargs or {}
        # Use provided impersonate or our custom realworld browser selection
        if impersonate:
            self.client_kwargs["impersonate"] = impersonate
        else:
            # Don't set it here, let HttpClientCffi handle it
            pass

        # HTTP clients for different rate limits
        self._client_60rpm = HttpClientCffi(
            60, 60, base_url="https://api.dexscreener.com", client_kwargs=self.client_kwargs
        )
        self._client_300rpm = HttpClientCffi(
            300, 60, base_url="https://api.dexscreener.com", client_kwargs=self.client_kwargs
        )

        # Single streaming client for all subscriptions
        self._http_stream: Optional[PollingStream] = None

        # Active subscriptions
        self._active_subscriptions: dict[str, dict] = {}

        # Filters for each subscription
        self._filters: dict[str, TokenPairFilter] = {}

    # ========== Single Query Methods ==========

    def get_pair(self, address: str) -> Optional[TokenPair]:
        """Get a single token pair by address using search"""
        # Since the API requires chain ID, we use search as a workaround
        resp = self._client_300rpm.request("GET", f"latest/dex/search?q={address}")
        if resp is not None and isinstance(resp, dict) and "pairs" in resp and len(resp["pairs"]) > 0:
            # Return the first matching pair
            for pair in resp["pairs"]:
                if pair.get("pairAddress", "").lower() == address.lower():
                    return TokenPair(**pair)
            # If no exact match, return the first result
            return TokenPair(**resp["pairs"][0])
        return None

    async def get_pair_async(self, address: str) -> Optional[TokenPair]:
        """Async version of get_pair"""
        # Since the API requires chain ID, we use search as a workaround
        resp = await self._client_300rpm.request_async("GET", f"latest/dex/search?q={address}")
        if resp is not None and isinstance(resp, dict) and "pairs" in resp and len(resp["pairs"]) > 0:
            # Return the first matching pair
            for pair in resp["pairs"]:
                if pair.get("pairAddress", "").lower() == address.lower():
                    return TokenPair(**pair)
            # If no exact match, return the first result
            return TokenPair(**resp["pairs"][0])
        return None

    def get_pairs_by_pairs_addresses(self, chain_id: str, pair_addresses: list[str]) -> list[TokenPair]:
        """
        Get multiple pairs from a specific chain.

        NOTE: API limit is 30 pairs per request. Requests with more than 30 pair addresses will raise an error.

        Args:
            chain_id: The blockchain identifier (e.g., "solana", "ethereum")
            pair_addresses: List of pair addresses (max 30)

        Returns:
            List of TokenPair objects

        Raises:
            ValueError: If more than 30 pair addresses are provided
        """
        if not pair_addresses:
            return []

        if len(pair_addresses) > self.MAX_PAIRS_PER_REQUEST:
            raise ValueError(f"Maximum {self.MAX_PAIRS_PER_REQUEST} pair addresses allowed, got {len(pair_addresses)}")

        addresses_str = ",".join(pair_addresses)
        resp = self._client_300rpm.request("GET", f"latest/dex/pairs/{chain_id}/{addresses_str}")
        if resp is None:
            return []
        if isinstance(resp, dict) and "pairs" in resp and resp["pairs"] is not None:
            return [TokenPair(**pair) for pair in resp["pairs"]]
        return []

    async def get_pairs_by_pairs_addresses_async(self, chain_id: str, pair_addresses: list[str]) -> list[TokenPair]:
        """
        Async version of get_pairs_by_pairs_addresses.

        NOTE: API limit is 30 pairs per request. Requests with more than 30 pair addresses will raise an error.

        Args:
            chain_id: The blockchain identifier (e.g., "solana", "ethereum")
            pair_addresses: List of pair addresses (max 30)

        Returns:
            List of TokenPair objects

        Raises:
            ValueError: If more than 30 pair addresses are provided
        """
        if not pair_addresses:
            return []

        if len(pair_addresses) > self.MAX_PAIRS_PER_REQUEST:
            raise ValueError(f"Maximum {self.MAX_PAIRS_PER_REQUEST} pair addresses allowed, got {len(pair_addresses)}")

        addresses_str = ",".join(pair_addresses)
        resp = await self._client_300rpm.request_async("GET", f"latest/dex/pairs/{chain_id}/{addresses_str}")
        if resp is None:
            return []
        if isinstance(resp, dict) and "pairs" in resp and resp["pairs"] is not None:
            return [TokenPair(**pair) for pair in resp["pairs"]]
        return []

    def get_pair_by_pair_address(self, chain_id: str, pair_address: str) -> Optional[TokenPair]:
        """Get a single token pair by chain and pair address"""
        pairs = self.get_pairs_by_pairs_addresses(chain_id, [pair_address])
        return pairs[0] if pairs else None

    async def get_pair_by_pair_address_async(self, chain_id: str, pair_address: str) -> Optional[TokenPair]:
        """Async version of get_pair_by_pair_address"""
        pairs = await self.get_pairs_by_pairs_addresses_async(chain_id, [pair_address])
        return pairs[0] if pairs else None

    def search_pairs(self, query: str) -> list[TokenPair]:
        """Search for pairs by query"""
        resp = self._client_300rpm.request("GET", f"latest/dex/search?q={query}")
        if resp is not None and isinstance(resp, dict):
            return [TokenPair(**pair) for pair in resp.get("pairs", [])]
        return []

    async def search_pairs_async(self, query: str) -> list[TokenPair]:
        """Async version of search_pairs"""
        resp = await self._client_300rpm.request_async("GET", f"latest/dex/search?q={query}")
        if resp is not None and isinstance(resp, dict):
            return [TokenPair(**pair) for pair in resp.get("pairs", [])]
        return []

    def get_latest_token_profiles(self) -> list[TokenInfo]:
        """Get latest token profiles"""
        resp = self._client_60rpm.request("GET", "token-profiles/latest/v1")
        if resp is not None:
            return [TokenInfo(**token) for token in resp]
        return []

    async def get_latest_token_profiles_async(self) -> list[TokenInfo]:
        """Async version of get_latest_token_profiles"""
        resp = await self._client_60rpm.request_async("GET", "token-profiles/latest/v1")
        if resp is not None:
            return [TokenInfo(**token) for token in resp]
        return []

    def get_latest_boosted_tokens(self) -> list[TokenInfo]:
        """Get latest boosted tokens"""
        resp = self._client_60rpm.request("GET", "token-boosts/latest/v1")
        if resp is not None:
            return [TokenInfo(**token) for token in resp]
        return []

    async def get_latest_boosted_tokens_async(self) -> list[TokenInfo]:
        """Async version of get_latest_boosted_tokens"""
        resp = await self._client_60rpm.request_async("GET", "token-boosts/latest/v1")
        if resp is not None:
            return [TokenInfo(**token) for token in resp]
        return []

    def get_tokens_most_active(self) -> list[TokenInfo]:
        """Get tokens with most active boosts"""
        resp = self._client_60rpm.request("GET", "token-boosts/top/v1")
        if resp is not None:
            return [TokenInfo(**token) for token in resp]
        return []

    async def get_tokens_most_active_async(self) -> list[TokenInfo]:
        """Async version of get_tokens_most_active"""
        resp = await self._client_60rpm.request_async("GET", "token-boosts/top/v1")
        if resp is not None:
            return [TokenInfo(**token) for token in resp]
        return []

    def get_orders_paid_of_token(self, chain_id: str, token_address: str) -> list[OrderInfo]:
        """Get orders for a token"""
        resp = self._client_60rpm.request("GET", f"orders/v1/{chain_id}/{token_address}")
        if resp is not None:
            return [OrderInfo(**order) for order in resp]
        return []

    async def get_orders_paid_of_token_async(self, chain_id: str, token_address: str) -> list[OrderInfo]:
        """Async version of get_orders_paid_of_token"""
        resp = await self._client_60rpm.request_async("GET", f"orders/v1/{chain_id}/{token_address}")
        if resp is not None:
            return [OrderInfo(**order) for order in resp]
        return []

    def get_pairs_by_token_address(self, chain_id: str, token_address: str) -> list[TokenPair]:
        """Get all pairs for a single token address on a specific chain"""
        # Use the correct endpoint format: /tokens/v1/{chain}/{address}
        resp = self._client_300rpm.request("GET", f"tokens/v1/{chain_id}/{token_address}")
        if resp is None:
            return []

        # The response is a direct array of pairs
        if isinstance(resp, list):
            return [TokenPair(**pair) for pair in resp]
        return []

    async def get_pairs_by_token_address_async(self, chain_id: str, token_address: str) -> list[TokenPair]:
        """Async version of get_pairs_by_token_address"""
        # Use the correct endpoint format: /tokens/v1/{chain}/{address}
        resp = await self._client_300rpm.request_async("GET", f"tokens/v1/{chain_id}/{token_address}")
        if resp is None:
            return []

        # The response is a direct array of pairs
        if isinstance(resp, list):
            return [TokenPair(**pair) for pair in resp]
        return []

    def get_pairs_by_token_addresses(self, chain_id: str, token_addresses: list[str]) -> list[TokenPair]:
        """
        Get all pairs for given token addresses on a specific chain.

        NOTE: To simplify the API, we now limit this to 30 token addresses per request.
        The API will return a MAXIMUM of 30 pairs regardless.

        Args:
            chain_id: The blockchain identifier (e.g., "solana", "ethereum")
            token_addresses: List of token addresses (max 30)

        Returns:
            List of TokenPair objects (maximum 30 pairs)

        Raises:
            ValueError: If more than 30 token addresses are provided
        """
        if not token_addresses:
            return []

        if len(token_addresses) > self.MAX_TOKENS_PER_REQUEST:
            raise ValueError(
                f"Maximum {self.MAX_TOKENS_PER_REQUEST} token addresses allowed, got {len(token_addresses)}"
            )

        if len(token_addresses) == 1:
            # For single token, use the single token method
            return self.get_pairs_by_token_address(chain_id, token_addresses[0])

        # The API supports comma-separated addresses
        addresses_str = ",".join(token_addresses)
        resp = self._client_300rpm.request("GET", f"tokens/v1/{chain_id}/{addresses_str}")
        if resp is None:
            return []

        # Response is a direct array of pairs
        if isinstance(resp, list):
            # Return unique pairs (avoid duplicates if a pair contains multiple requested tokens)
            seen_pairs = set()
            unique_pairs = []
            for pair_data in resp:
                pair = TokenPair(**pair_data)
                pair_key = f"{pair.chain_id}:{pair.pair_address}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    unique_pairs.append(pair)
            return unique_pairs
        return []

    def get_pools_by_token_address(self, chain_id: str, token_address: str) -> list[TokenPair]:
        """Get pools info using token-pairs/v1 endpoint (Pool endpoint)"""
        # Use the token-pairs/v1 endpoint
        resp = self._client_300rpm.request("GET", f"token-pairs/v1/{chain_id}/{token_address}")
        if resp is None:
            return []

        # The response is a direct array of pairs
        if isinstance(resp, list):
            return [TokenPair(**pair) for pair in resp]
        return []

    async def get_pools_by_token_address_async(self, chain_id: str, token_address: str) -> list[TokenPair]:
        """Async version of get_pools_by_token_address"""
        # Use the token-pairs/v1 endpoint
        resp = await self._client_300rpm.request_async("GET", f"token-pairs/v1/{chain_id}/{token_address}")
        if resp is None:
            return []

        # The response is a direct array of pairs
        if isinstance(resp, list):
            return [TokenPair(**pair) for pair in resp]
        return []

    async def get_pairs_by_token_addresses_async(self, chain_id: str, token_addresses: list[str]) -> list[TokenPair]:
        """
        Async version of get_pairs_by_token_addresses.

        NOTE: To simplify the API, we now limit this to 30 token addresses per request.
        The API will return a MAXIMUM of 30 pairs regardless.

        Args:
            chain_id: The blockchain identifier (e.g., "solana", "ethereum")
            token_addresses: List of token addresses (max 30)

        Returns:
            List of TokenPair objects (maximum 30 pairs)

        Raises:
            ValueError: If more than 30 token addresses are provided
        """
        if not token_addresses:
            return []

        if len(token_addresses) > self.MAX_TOKENS_PER_REQUEST:
            raise ValueError(
                f"Maximum {self.MAX_TOKENS_PER_REQUEST} token addresses allowed, got {len(token_addresses)}"
            )

        if len(token_addresses) == 1:
            # For single token, use the single token method
            return await self.get_pairs_by_token_address_async(chain_id, token_addresses[0])

        # The API supports comma-separated addresses
        addresses_str = ",".join(token_addresses)
        resp = await self._client_300rpm.request_async("GET", f"tokens/v1/{chain_id}/{addresses_str}")
        if resp is None:
            return []

        # Response is a direct array of pairs
        if isinstance(resp, list):
            # Return unique pairs (avoid duplicates if a pair contains multiple requested tokens)
            seen_pairs = set()
            unique_pairs = []
            for pair_data in resp:
                pair = TokenPair(**pair_data)
                pair_key = f"{pair.chain_id}:{pair.pair_address}"
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    unique_pairs.append(pair)
            return unique_pairs
        return []

    # ========== Streaming Methods ==========

    async def subscribe_pairs(
        self,
        chain_id: str,
        pair_addresses: list[str],
        callback: Callable[[TokenPair], None],
        *,  # Force keyword arguments
        filter: Union[bool, FilterConfig] = True,
        interval: float = 0.2,
    ) -> None:
        """
        Subscribe to pair updates.

        Args:
            chain_id: Blockchain identifier (e.g., "ethereum", "solana")
            pair_addresses: List of pair contract addresses
            callback: Function to call on updates
            filter: Filtering configuration:
                - False: No filtering, receive all updates
                - True: Default filtering (changes only)
                - FilterConfig: Custom filter configuration
            interval: Polling interval for HTTP mode (seconds, default 0.2s = 300/min)

        Examples:
            # Simple change detection (default)
            await client.subscribe_pairs("ethereum", ["0x..."], callback)

            # No filtering
            await client.subscribe_pairs("ethereum", ["0x..."], callback, filter=False)

            # Only significant price changes (1%)
            from dexscreen.utils import FilterPresets
            await client.subscribe_pairs(
                "ethereum", ["0x..."], callback,
                filter=FilterPresets.significant_price_changes(0.01)
            )

            # Custom filter config
            from dexscreen.utils import FilterConfig
            config = FilterConfig(price_change_threshold=0.02)
            await client.subscribe_pairs("ethereum", ["0x..."], callback, filter=config)
        """
        # Handle single pair address for backward compatibility
        for pair_address in pair_addresses:
            subscription_key = f"{chain_id}:{pair_address}"

            # Setup filter based on parameter type
            if filter is False:
                # No filtering
                actual_callback = callback
                filter_config_used = None
            elif filter is True:
                # Use default filter configuration
                filter_config_used = FilterConfig()
                filter_instance = TokenPairFilter(filter_config_used)
                self._filters[subscription_key] = filter_instance

                # Create filtered callback
                async def filtered_callback(
                    pair: TokenPair, filter_instance=filter_instance, subscription_key=subscription_key
                ):
                    if filter_instance.should_emit(subscription_key, pair):
                        if asyncio.iscoroutinefunction(callback):
                            await callback(pair)
                        else:
                            callback(pair)

                actual_callback = filtered_callback
            elif isinstance(filter, FilterConfig):
                # Use custom filter configuration
                filter_config_used = filter
                filter_instance = TokenPairFilter(filter_config_used)
                self._filters[subscription_key] = filter_instance

                # Create filtered callback
                async def filtered_callback(
                    pair: TokenPair, filter_instance=filter_instance, subscription_key=subscription_key
                ):
                    if filter_instance.should_emit(subscription_key, pair):
                        if asyncio.iscoroutinefunction(callback):
                            await callback(pair)
                        else:
                            callback(pair)

                actual_callback = filtered_callback
            else:
                raise ValueError(f"Invalid filter type: {type(filter)}. Must be bool or FilterConfig")

            # Store subscription info
            self._active_subscriptions[subscription_key] = {
                "chain": chain_id,
                "pair_address": pair_address,
                "callback": callback,
                "filter": filter,
                "filter_config": filter_config_used,
                "interval": interval,
            }

            # Subscribe to updates
            # Always pass filter_changes=False to PollingStream since filtering is handled here
            await self._subscribe_http(chain_id, pair_address, actual_callback, interval)

    async def subscribe_tokens(
        self,
        chain_id: str,
        token_addresses: list[str],
        callback: Callable[[list[TokenPair]], None],
        *,  # Force keyword arguments
        filter: Union[bool, FilterConfig] = True,
        interval: float = 0.2,
    ) -> None:
        """
        Subscribe to all pairs of tokens.

        Args:
            chain_id: Blockchain identifier (e.g., "ethereum", "solana")
            token_addresses: List of token contract addresses
            callback: Function to call on updates (receives list of TokenPair)
            filter: Filtering configuration (same as subscribe_pairs)
            interval: Polling interval (seconds, default 0.2s = 300/min)

        Example:
            # Subscribe to all pairs of USDC token on Solana
            await client.subscribe_tokens(
                "solana",
                ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"],
                callback=handle_usdc_pairs
            )
        """
        # Handle multiple token addresses
        for token_address in token_addresses:
            subscription_key = f"token:{chain_id}:{token_address}"

            # Setup filter based on parameter type
            if filter is False:
                # No filtering
                actual_callback = callback
                filter_config_used = None
            elif filter is True:
                # Use default filter configuration
                filter_config_used = FilterConfig()
                filter_instance = TokenPairFilter(filter_config_used)
                self._filters[subscription_key] = filter_instance

                # For token subscriptions, we need to track pairs individually
                async def filtered_callback(pairs: list[TokenPair], filter_instance=filter_instance):
                    filtered_pairs = []
                    for pair in pairs:
                        pair_key = f"{pair.chain_id}:{pair.pair_address}"
                        if filter_instance.should_emit(pair_key, pair):
                            filtered_pairs.append(pair)

                    if filtered_pairs:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(filtered_pairs)
                        else:
                            callback(filtered_pairs)

                actual_callback = filtered_callback
            elif isinstance(filter, FilterConfig):
                # Use custom filter configuration
                filter_config_used = filter
                filter_instance = TokenPairFilter(filter_config_used)
                self._filters[subscription_key] = filter_instance

                # For token subscriptions, we need to track pairs individually
                async def filtered_callback(pairs: list[TokenPair], filter_instance=filter_instance):
                    filtered_pairs = []
                    for pair in pairs:
                        pair_key = f"{pair.chain_id}:{pair.pair_address}"
                        if filter_instance.should_emit(pair_key, pair):
                            filtered_pairs.append(pair)

                    if filtered_pairs:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(filtered_pairs)
                        else:
                            callback(filtered_pairs)

                actual_callback = filtered_callback
            else:
                raise ValueError(f"Invalid filter type: {type(filter)}. Must be bool or FilterConfig")

            # Store subscription info
            self._active_subscriptions[subscription_key] = {
                "type": "token",
                "chain": chain_id,
                "token_address": token_address,
                "callback": callback,
                "filter": filter,
                "filter_config": filter_config_used,
                "interval": interval,
            }

            # Subscribe to updates
            await self._subscribe_token_http(chain_id, token_address, actual_callback, interval)

    async def _subscribe_http(self, chain_id: str, pair_address: str, callback: Callable, interval: float):
        """Subscribe to updates"""
        # Create single HTTP stream client if needed
        if self._http_stream is None:
            # Always pass filter_changes=False since filtering is handled in subscribe method
            self._http_stream = PollingStream(
                self,
                interval=1.0,  # Default interval, will be overridden per subscription
                filter_changes=False,
            )
            await self._http_stream.connect()

        # Subscribe with specific interval
        await self._http_stream.subscribe(chain_id, pair_address, callback, interval)

    async def _subscribe_token_http(self, chain_id: str, token_address: str, callback: Callable, interval: float):
        """Subscribe to token pair updates"""
        # Create single HTTP stream client if needed
        if self._http_stream is None:
            # Always pass filter_changes=False since filtering is handled in subscribe method
            self._http_stream = PollingStream(
                self,
                interval=1.0,  # Default interval, will be overridden per subscription
                filter_changes=False,
            )
            await self._http_stream.connect()

        # Subscribe with specific interval
        await self._http_stream.subscribe_token(chain_id, token_address, callback, interval)

    async def unsubscribe_pairs(self, chain_id: str, pair_addresses: list[str]) -> None:
        """Unsubscribe from pair updates"""
        for pair_address in pair_addresses:
            subscription_key = f"{chain_id}:{pair_address}"

            if subscription_key not in self._active_subscriptions:
                continue

            # Unsubscribe from the single HTTP client
            if self._http_stream and self._http_stream.has_subscription(chain_id, pair_address):
                await self._http_stream.unsubscribe(chain_id, pair_address)

            # Clean up
            del self._active_subscriptions[subscription_key]
            if subscription_key in self._filters:
                self._filters[subscription_key].reset(subscription_key)
                del self._filters[subscription_key]

    async def unsubscribe_tokens(self, chain_id: str, token_addresses: list[str]) -> None:
        """Unsubscribe from token pair updates"""
        for token_address in token_addresses:
            subscription_key = f"token:{chain_id}:{token_address}"

            if subscription_key not in self._active_subscriptions:
                continue

            # Unsubscribe from the single HTTP client
            if self._http_stream and self._http_stream.has_token_subscription(chain_id, token_address):
                await self._http_stream.unsubscribe_token(chain_id, token_address)

            # Clean up
            del self._active_subscriptions[subscription_key]
            if subscription_key in self._filters:
                self._filters[subscription_key].reset()
                del self._filters[subscription_key]

    async def close_streams(self) -> None:
        """Close all streaming connections"""
        # Close HTTP stream
        if self._http_stream:
            await self._http_stream.close()
            self._http_stream = None

        # Clear subscriptions and filters
        self._active_subscriptions.clear()
        for filter_instance in self._filters.values():
            filter_instance.reset()
        self._filters.clear()

    def get_active_subscriptions(self) -> list[dict]:
        """Get list of active subscriptions"""
        subscriptions = []
        for _key, info in self._active_subscriptions.items():
            if info.get("type") == "token":
                subscriptions.append(
                    {
                        "type": "token",
                        "chain": info["chain"],
                        "token_address": info["token_address"],
                        "filter": info["filter"],
                        "interval": info.get("interval", 0.2),
                    }
                )
            else:
                subscriptions.append(
                    {
                        "type": "pair",
                        "chain": info["chain"],
                        "pair_address": info["pair_address"],
                        "filter": info["filter"],
                        "interval": info.get("interval", 0.2),
                    }
                )
        return subscriptions
