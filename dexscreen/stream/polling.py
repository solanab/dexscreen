"""
Unified streaming interface
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional

from ..core.exceptions import HttpError
from ..core.models import TokenPair
from ..utils.logging_config import get_contextual_logger
from ..utils.retry import RetryConfig, RetryManager, RetryPresets

logger = logging.getLogger(__name__)


class StreamingClient(ABC):
    """Base class for streaming data"""

    def __init__(self):
        self.subscriptions: dict[str, set[Callable]] = {}
        self.running = False
        self.callback_errors: dict[str, int] = {}  # Track errors per subscription

        # Enhanced logging
        self.contextual_logger = get_contextual_logger(__name__)

        # Streaming statistics
        self.stats = {
            "total_subscriptions": 0,
            "active_subscriptions": 0,
            "total_emissions": 0,
            "total_callback_errors": 0,
            "last_emission_time": None,
        }

    @abstractmethod
    async def connect(self):
        """Establish connection"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection"""
        pass

    @abstractmethod
    async def subscribe(
        self,
        chain_id: str,
        address: str,
        callback: Callable[[TokenPair], None],
        interval: Optional[float] = None,
    ):
        """Subscribe to pair updates"""
        pass

    async def unsubscribe(self, chain_id: str, address: str, callback: Optional[Callable] = None):
        """Unsubscribe from pair updates"""
        key = f"{chain_id}:{address}"
        if key in self.subscriptions:
            if callback:
                self.subscriptions[key].discard(callback)
                if not self.subscriptions[key]:
                    del self.subscriptions[key]
                    await self._on_last_unsubscription(chain_id, address)
            else:
                del self.subscriptions[key]
                await self._on_last_unsubscription(chain_id, address)

    async def _emit(self, chain_id: str, address: str, pair: TokenPair):
        """Emit update to all subscribers"""
        key = f"{chain_id}:{address}"
        if key in self.subscriptions:
            for callback in self.subscriptions[key].copy():
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(pair)
                    else:
                        callback(pair)
                except Exception as e:
                    # Log the error but continue processing other callbacks
                    logger.exception("Callback error for subscription %s: %s", key, type(e).__name__)
                    # Track error count
                    if key not in self.callback_errors:
                        self.callback_errors[key] = 0
                    self.callback_errors[key] += 1

    @abstractmethod
    async def _on_new_subscription(self, chain_id: str, address: str):
        """Called when first subscriber for a pair"""
        pass

    @abstractmethod
    async def _on_last_unsubscription(self, chain_id: str, address: str):
        """Called when last subscriber removed"""
        pass

    def get_callback_error_count(self, chain_id: Optional[str] = None, address: Optional[str] = None) -> int:
        """Get the number of callback errors for a specific subscription or all subscriptions"""
        if chain_id and address:
            key = f"{chain_id}:{address}"
            return self.callback_errors.get(key, 0)
        return sum(self.callback_errors.values())

    def get_streaming_stats(self) -> dict:
        """Get comprehensive streaming statistics"""
        combined_stats = self.stats.copy()
        if hasattr(self, "polling_stats"):
            combined_stats.update(self.polling_stats)  # type: ignore[attr-defined]
        combined_stats.update(
            {
                "total_callback_errors": sum(self.callback_errors.values()),
                "subscriptions_with_errors": len([k for k, v in self.callback_errors.items() if v > 0]),
                "running": self.running,
            }
        )
        return combined_stats


class PollingStream(StreamingClient):
    """Polling implementation with streaming interface"""

    def __init__(
        self,
        dexscreener_client,
        interval: float = 1.0,
        filter_changes: bool = True,
        retry_config: Optional[RetryConfig] = None,
    ):
        super().__init__()
        self.dexscreener_client = dexscreener_client  # The main DexscreenerClient instance
        self.interval = interval  # Default interval
        self.filter_changes = filter_changes  # Whether to filter for changes
        self.retry_config = retry_config or RetryPresets.network_operations()  # Conservative retry for polling
        self.tasks: dict[str, asyncio.Task] = {}
        self._cache: dict[str, Optional[TokenPair]] = {}

        # Enhanced polling statistics
        self.polling_stats = {
            "total_polls": 0,
            "successful_polls": 0,
            "failed_polls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_poll_duration": 0.0,
            "last_poll_time": None,
        }

        init_context = {
            "interval": interval,
            "filter_changes": filter_changes,
            "polling_mode": "http",
        }

        self.contextual_logger.debug("PollingStream initialized", context=init_context)

        # Data structures for chain-based polling (max 30 per chain)
        self._chain_subscriptions: dict[str, set[str]] = {}  # chain -> set of addresses
        self._chain_tasks: dict[str, asyncio.Task] = {}  # chain -> polling task
        self._subscription_intervals: dict[str, float] = {}  # subscription_key -> interval
        self._chain_intervals: dict[str, float] = {}  # chain -> minimum interval

        # Token subscription data structures
        self._token_subscriptions: dict[str, set[Callable]] = {}  # chain:token_address -> set of callbacks
        self._token_tasks: dict[str, asyncio.Task] = {}  # chain:token_address -> polling task
        self._token_intervals: dict[str, float] = {}  # chain:token_address -> interval

    async def connect(self):
        """Start streaming service"""
        connect_context = {
            "operation": "connect",
            "previous_state": "running" if self.running else "stopped",
        }

        self.contextual_logger.info("Starting polling stream service", context=connect_context)

        self.running = True

        connect_context.update({"current_state": "running"})
        self.contextual_logger.info("Polling stream service started", context=connect_context)

    async def disconnect(self):
        """Stop all polling tasks"""
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()

        # Stop chain polling tasks
        for task in self._chain_tasks.values():
            task.cancel()
        self._chain_tasks.clear()
        self._chain_subscriptions.clear()

        # Stop token polling tasks
        for task in self._token_tasks.values():
            task.cancel()
        self._token_tasks.clear()
        self._token_subscriptions.clear()
        self._token_intervals.clear()

    async def subscribe(
        self,
        chain_id: str,
        address: str,
        callback: Callable[[TokenPair], None],
        interval: Optional[float] = None,
    ):
        """Subscribe to pair updates"""
        key = f"{chain_id}:{address}"
        if interval is None:
            interval = self.interval  # Use default if not specified

        # Store the interval for this subscription
        self._subscription_intervals[key] = interval

        if key not in self.subscriptions:
            self.subscriptions[key] = set()
            await self._on_new_subscription(chain_id, address)
        self.subscriptions[key].add(callback)

    async def _on_new_subscription(self, chain_id: str, address: str):
        """Start polling for a new pair"""
        # Add to chain subscriptions
        if chain_id not in self._chain_subscriptions:
            self._chain_subscriptions[chain_id] = set()
        self._chain_subscriptions[chain_id].add(address)

        # Update chain interval to be the minimum of all subscriptions
        self._update_chain_interval(chain_id)

        # Restart chain polling task if needed
        await self._restart_chain_polling(chain_id)

    async def _on_last_unsubscription(self, chain_id: str, address: str):
        """Stop polling for a pair"""
        key = f"{chain_id}:{address}"
        if key in self._cache:
            del self._cache[key]

        # Remove interval data
        if key in self._subscription_intervals:
            del self._subscription_intervals[key]

        # Remove from chain subscriptions
        if chain_id in self._chain_subscriptions:
            self._chain_subscriptions[chain_id].discard(address)

            # If no more addresses for this chain, stop the chain task
            if not self._chain_subscriptions[chain_id]:
                del self._chain_subscriptions[chain_id]
                if chain_id in self._chain_tasks:
                    self._chain_tasks[chain_id].cancel()
                    del self._chain_tasks[chain_id]
                if chain_id in self._chain_intervals:
                    del self._chain_intervals[chain_id]
            else:
                # Update chain interval and restart polling
                self._update_chain_interval(chain_id)
                await self._restart_chain_polling(chain_id)

    def _update_chain_interval(self, chain_id: str):
        """Update the chain interval to be the minimum of all subscriptions"""
        if chain_id not in self._chain_subscriptions:
            return

        # Find the minimum interval for all subscriptions in this chain
        min_interval = float("inf")
        for address in self._chain_subscriptions[chain_id]:
            key = f"{chain_id}:{address}"
            if key in self._subscription_intervals:
                min_interval = min(min_interval, self._subscription_intervals[key])

        # Use default interval if no subscriptions found
        if min_interval == float("inf"):
            min_interval = self.interval

        self._chain_intervals[chain_id] = min_interval

    async def _restart_chain_polling(self, chain_id: str):
        """Restart polling for a chain with updated addresses"""
        # Cancel existing task if any
        if chain_id in self._chain_tasks:
            self._chain_tasks[chain_id].cancel()

        # Start new polling task for this chain
        if self._chain_subscriptions.get(chain_id):
            task = asyncio.create_task(self._poll_chain(chain_id))
            self._chain_tasks[chain_id] = task

    async def _poll_chain(self, chain_id: str):
        """Poll all pairs for a specific chain (max 30 per chain)"""

        next_poll_time = time.time()

        while self.running and chain_id in self._chain_subscriptions:
            # Get the current interval for this chain
            interval = self._chain_intervals.get(chain_id, self.interval)

            # Calculate next poll time at the beginning
            next_poll_time += interval

            # Create a task for fetching pairs (non-blocking)
            asyncio.create_task(self._batch_fetch_and_emit(chain_id))

            # Calculate how long to sleep to maintain fixed interval
            current_time = time.time()
            sleep_time = max(0, next_poll_time - current_time)

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                # If we're behind schedule, adjust but don't accumulate delay
                next_poll_time = current_time + interval

    async def _batch_fetch_and_emit(self, chain_id: str):
        """Fetch multiple pairs for a chain and emit updates"""

        if chain_id not in self._chain_subscriptions:
            return

        addresses = list(self._chain_subscriptions[chain_id])
        if not addresses:
            return

        # Check if we have too many subscriptions for a single chain
        max_subscriptions = 30
        if len(addresses) > max_subscriptions:
            logger.warning(
                "Subscription limit exceeded for chain %s: %d addresses requested, limiting to %d",
                chain_id,
                len(addresses),
                max_subscriptions,
            )
            addresses = addresses[:max_subscriptions]

        retry_manager = RetryManager(self.retry_config)

        while True:
            try:
                # Log API request time
                request_start = time.time()

                # Fetch all pairs in one request (max 30 due to limit above)
                pairs = await self.dexscreener_client.get_pairs_by_pairs_addresses_async(chain_id, addresses)

                request_end = time.time()
                request_duration = request_end - request_start

                # Update polling statistics
                self.polling_stats["total_polls"] += 1
                self.polling_stats["successful_polls"] += 1
                self.polling_stats["last_poll_time"] = request_end

                # Update average poll duration
                total_polls = self.polling_stats["total_polls"]
                current_avg = self.polling_stats["average_poll_duration"]
                self.polling_stats["average_poll_duration"] = (
                    current_avg * (total_polls - 1) + request_duration
                ) / total_polls

                logger.debug(
                    "Batch fetch completed for chain %s: %d addresses, %d pairs returned in %.2fms",
                    chain_id,
                    len(addresses),
                    len(pairs),
                    request_duration * 1000,
                )

                # Create a mapping for quick lookup
                pairs_map = {pair.pair_address.lower(): pair for pair in pairs}

                # Process each address
                for address in addresses:
                    key = f"{chain_id}:{address}"
                    pair = pairs_map.get(address.lower())

                    if pair:
                        # Add request timing info to the pair object for debugging
                        pair._request_duration = request_duration
                        pair._request_time = request_end

                        # Check if we should filter for changes
                        if self.filter_changes:
                            # Only emit if data changed
                            if self._has_changed(key, pair):
                                self._cache[key] = pair
                                await self._emit(chain_id, address, pair)
                                self.polling_stats["cache_misses"] += 1
                            else:
                                self.polling_stats["cache_hits"] += 1
                        else:
                            # Raw mode: emit every update
                            await self._emit(chain_id, address, pair)

                # Success - break out of retry loop
                break

            except Exception as e:
                retry_manager.record_failure(e)

                # Update error statistics
                self.polling_stats["total_polls"] += 1
                self.polling_stats["failed_polls"] += 1

                if retry_manager.should_retry(e):
                    retry_context = {
                        "operation": "batch_fetch_retry",
                        "chain_id": chain_id,
                        "addresses_count": len(addresses),
                        "attempt": retry_manager.attempt,
                        "max_retries": self.retry_config.max_retries + 1,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "retry_delay": retry_manager.calculate_delay(),
                    }

                    self.contextual_logger.warning(
                        "Polling error for chain %s, retrying (attempt %d/%d): %s",
                        chain_id,
                        retry_manager.attempt,
                        self.retry_config.max_retries + 1,
                        str(e),
                        context=retry_context,
                    )

                    logger.warning(
                        "Polling error for chain %s with %d addresses (attempt %d/%d): %s. Retrying in %.2fs",
                        chain_id,
                        len(addresses),
                        retry_manager.attempt,
                        self.retry_config.max_retries + 1,
                        str(e),
                        retry_manager.calculate_delay(),
                    )
                    await retry_manager.wait_async()
                    continue
                else:
                    # Max retries exceeded - log and continue to next poll cycle
                    final_error_context = {
                        "operation": "batch_fetch_final_failure",
                        "chain_id": chain_id,
                        "addresses_count": len(addresses),
                        "total_attempts": retry_manager.attempt,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "will_retry_next_poll": True,
                    }

                    if isinstance(e, HttpError):
                        self.contextual_logger.warning(
                            "HTTP error during batch fetch after %d attempts, will retry on next poll: %s",
                            retry_manager.attempt,
                            str(e),
                            context=final_error_context,
                        )

                        logger.warning(
                            "HTTP error during batch fetch for chain %s with %d addresses after %d attempts: %s. Will retry on next poll.",
                            chain_id,
                            len(addresses),
                            retry_manager.attempt,
                            e,
                        )
                    else:
                        self.contextual_logger.error(
                            "Polling failed after %d attempts, will retry on next poll: %s",
                            retry_manager.attempt,
                            str(e),
                            context=final_error_context,
                            exc_info=True,
                        )

                        logger.exception(
                            "Polling failed for chain %s with %d addresses after %d attempts: %s. Will retry on next poll.",
                            chain_id,
                            len(addresses),
                            retry_manager.attempt,
                            type(e).__name__,
                        )
                    break

    def _has_changed(self, key: str, new_pair: TokenPair) -> bool:
        """Check if pair data has changed"""
        old_pair = self._cache.get(key)
        if not old_pair:
            return True

        return (
            old_pair.price_usd != new_pair.price_usd
            or old_pair.price_native != new_pair.price_native
            or old_pair.volume.h24 != new_pair.volume.h24
            or old_pair.liquidity != new_pair.liquidity
        )

    def has_subscription(self, chain_id: str, address: str) -> bool:
        """Check if there's an active subscription for a pair"""
        key = f"{chain_id}:{address}"
        return key in self.subscriptions

    async def close(self):
        """Alias for disconnect with stats logging"""
        close_context = {
            "operation": "close_stream",
            "final_stats": self.get_streaming_stats(),
        }

        self.contextual_logger.info("Closing polling stream", context=close_context)
        await self.disconnect()

        self.contextual_logger.info("Polling stream closed", context=close_context)

    # Token subscription methods
    async def subscribe_token(
        self,
        chain_id: str,
        token_address: str,
        callback: Callable[[list[TokenPair]], None],
        interval: float = 0.2,
    ):
        """Subscribe to all pairs of a token"""
        key = f"{chain_id}:{token_address}"
        if key not in self._token_subscriptions:
            self._token_subscriptions[key] = set()
            self._token_intervals[key] = interval
            # Start polling for this token
            await self._start_token_polling(chain_id, token_address)

        self._token_subscriptions[key].add(callback)

    async def unsubscribe_token(self, chain_id: str, token_address: str):
        """Unsubscribe from token updates"""
        key = f"{chain_id}:{token_address}"
        if key in self._token_subscriptions:
            del self._token_subscriptions[key]

            # Stop the polling task
            if key in self._token_tasks:
                self._token_tasks[key].cancel()
                del self._token_tasks[key]

            # Clear interval
            if key in self._token_intervals:
                del self._token_intervals[key]

    def has_token_subscription(self, chain_id: str, token_address: str) -> bool:
        """Check if there's an active token subscription"""
        key = f"{chain_id}:{token_address}"
        return key in self._token_subscriptions

    async def _start_token_polling(self, chain_id: str, token_address: str):
        """Start polling for a token"""
        key = f"{chain_id}:{token_address}"
        # Cancel existing task if any
        if key in self._token_tasks:
            self._token_tasks[key].cancel()

        # Start new polling task
        task = asyncio.create_task(self._poll_token(chain_id, token_address))
        self._token_tasks[key] = task

    async def _poll_token(self, chain_id: str, token_address: str):
        """Poll all pairs for a specific token"""

        key = f"{chain_id}:{token_address}"
        next_poll_time = time.time()

        while self.running and key in self._token_subscriptions:
            # Get the interval for this token
            interval = self._token_intervals.get(key, self.interval)

            # Calculate next poll time at the beginning
            next_poll_time += interval

            # Create a task for fetching (non-blocking)
            asyncio.create_task(self._fetch_and_emit_token(chain_id, token_address))

            # Calculate how long to sleep to maintain fixed interval
            current_time = time.time()
            sleep_time = max(0, next_poll_time - current_time)

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                # If we're behind schedule, adjust but don't accumulate delay
                next_poll_time = current_time + interval

    async def _fetch_and_emit_token(self, chain_id: str, token_address: str):
        """Fetch all pairs for a token and emit updates"""

        key = f"{chain_id}:{token_address}"
        if key not in self._token_subscriptions:
            return

        retry_manager = RetryManager(self.retry_config)

        while True:
            try:
                # Log API request time
                request_start = time.time()

                # Fetch all pairs for this token
                pairs = await self.dexscreener_client.get_pairs_by_token_address_async(chain_id, token_address)

                request_end = time.time()
                request_duration = request_end - request_start

                logger.debug(
                    "Token fetch completed for %s:%s - %d pairs returned in %.2fms",
                    chain_id,
                    token_address,
                    len(pairs),
                    request_duration * 1000,
                )

                # Add timing info for debugging
                for pair in pairs:
                    pair._request_duration = request_duration
                    pair._request_time = request_end

                # Emit to all callbacks
                for callback in self._token_subscriptions[key].copy():
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(pairs)
                        else:
                            callback(pairs)
                    except Exception as e:
                        logger.exception(
                            "Token callback error for %s:%s - %s", chain_id, token_address, type(e).__name__
                        )

                # Success - break out of retry loop
                break

            except Exception as e:
                retry_manager.record_failure(e)

                if retry_manager.should_retry(e):
                    logger.warning(
                        "Token polling error for %s:%s (attempt %d/%d): %s. Retrying in %.2fs",
                        chain_id,
                        token_address,
                        retry_manager.attempt,
                        self.retry_config.max_retries + 1,
                        str(e),
                        retry_manager.calculate_delay(),
                    )
                    await retry_manager.wait_async()
                    continue
                else:
                    # Max retries exceeded - log and continue to next poll cycle
                    if isinstance(e, HttpError):
                        logger.warning(
                            "HTTP error during token fetch for %s:%s after %d attempts: %s. Will retry on next poll.",
                            chain_id,
                            token_address,
                            retry_manager.attempt,
                            e,
                        )
                    else:
                        logger.exception(
                            "Token polling failed for %s:%s after %d attempts: %s. Will retry on next poll.",
                            chain_id,
                            token_address,
                            retry_manager.attempt,
                            type(e).__name__,
                        )
                    break
