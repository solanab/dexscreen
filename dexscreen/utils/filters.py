"""
Token pair filtering utilities for reducing noise and controlling update frequency
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..core.models import TokenPair
from .logging_config import get_contextual_logger, with_correlation_id


@dataclass
class FilterConfig:
    """Configuration for token pair filtering"""

    # Change detection fields - which fields to monitor for changes
    change_fields: list[str] = field(default_factory=lambda: ["price_usd", "price_native", "volume.h24", "liquidity"])

    # Significant change thresholds (None means any change triggers)
    price_change_threshold: Optional[float] = None  # e.g., 0.01 for 1%
    volume_change_threshold: Optional[float] = None  # e.g., 0.10 for 10%
    liquidity_change_threshold: Optional[float] = None  # e.g., 0.05 for 5%

    # Rate limiting
    max_updates_per_second: Optional[float] = None  # e.g., 1.0 for max 1 update/sec


class TokenPairFilter:
    """Filter for token pair updates based on configuration"""

    def __init__(self, config: Optional[FilterConfig] = None):
        """
        Initialize filter with optional configuration.
        If no config provided, acts as a simple change detector.
        """
        self.config = config or FilterConfig()
        self._cache: dict[str, dict[str, Any]] = {}
        self._last_update_times: dict[str, float] = {}

        # Enhanced logging
        self.contextual_logger = get_contextual_logger(__name__)

        # Filter statistics
        self.stats = {
            "total_evaluations": 0,
            "total_emissions": 0,
            "rate_limited_blocks": 0,
            "no_change_blocks": 0,
            "insignificant_change_blocks": 0,
            "cache_size": 0,
            "emission_rate": 0.0,
        }

        init_context = {
            "change_fields": self.config.change_fields,
            "price_threshold": self.config.price_change_threshold,
            "volume_threshold": self.config.volume_change_threshold,
            "liquidity_threshold": self.config.liquidity_change_threshold,
            "max_updates_per_second": self.config.max_updates_per_second,
        }

        self.contextual_logger.debug("TokenPairFilter initialized", context=init_context)

    @with_correlation_id()
    def should_emit(self, key: str, pair: TokenPair) -> bool:
        """
        Check if update should be emitted based on filter rules.

        Args:
            key: Unique identifier for the subscription (e.g., "ethereum:0x...")
            pair: The token pair data

        Returns:
            True if update should be emitted, False otherwise
        """
        self.stats["total_evaluations"] += 1

        filter_context = {
            "operation": "filter_evaluation",
            "subscription_key": key[:32] + "..." if len(key) > 32 else key,
            "pair_address": pair.pair_address[:10] + "..." if len(pair.pair_address) > 10 else pair.pair_address,
            "chain_id": pair.chain_id,
            "current_price": pair.price_usd,
        }

        try:
            # Check rate limiting first
            if not self._check_rate_limit(key):
                self.stats["rate_limited_blocks"] += 1
                filter_context.update(
                    {
                        "blocked_reason": "rate_limited",
                        "max_updates_per_second": self.config.max_updates_per_second,
                    }
                )

                self.contextual_logger.debug(
                    "Filter blocked update due to rate limiting for %s", key, context=filter_context
                )
                return False

            # Check for changes
            if not self._has_relevant_changes(key, pair):
                self.stats["no_change_blocks"] += 1
                filter_context.update(
                    {
                        "blocked_reason": "no_changes",
                        "monitored_fields": self.config.change_fields,
                    }
                )

                self.contextual_logger.debug(
                    "Filter blocked update - no relevant changes for %s", key, context=filter_context
                )
                return False

            # Check if changes are significant enough
            if not self._are_changes_significant(key, pair):
                self.stats["insignificant_change_blocks"] += 1
                filter_context.update(
                    {
                        "blocked_reason": "insignificant_changes",
                        "price_threshold": self.config.price_change_threshold,
                        "volume_threshold": self.config.volume_change_threshold,
                        "liquidity_threshold": self.config.liquidity_change_threshold,
                    }
                )

                self.contextual_logger.debug(
                    "Filter blocked update - changes not significant for %s", key, context=filter_context
                )
                return False

            # Update cache and emit
            self._update_cache(key, pair)
            self.stats["total_emissions"] += 1
            self.stats["cache_size"] = len(self._cache)

            # Calculate emission rate
            if self.stats["total_evaluations"] > 0:
                self.stats["emission_rate"] = self.stats["total_emissions"] / self.stats["total_evaluations"]

            filter_context.update(
                {
                    "result": "emitted",
                    "total_emissions": self.stats["total_emissions"],
                    "emission_rate": self.stats["emission_rate"],
                }
            )

            self.contextual_logger.debug(
                "Filter allowing update emission for %s (emission #%d)",
                key,
                self.stats["total_emissions"],
                context=filter_context,
            )

            return True

        except Exception as e:
            error_context = {
                "operation": "filter_evaluation_error",
                "subscription_key": key,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "pair_data": {
                    "address": pair.pair_address,
                    "chain": pair.chain_id,
                    "price": pair.price_usd,
                },
            }

            self.contextual_logger.error(
                "Error during filter evaluation for %s: %s", key, str(e), context=error_context, exc_info=True
            )

            # On error, default to allowing the emission to avoid blocking data
            return True

    def _check_rate_limit(self, key: str) -> bool:
        """Check if rate limit allows this update"""
        if self.config.max_updates_per_second is None:
            return True

        current_time = time.time()
        last_update = self._last_update_times.get(key, 0)

        min_interval = 1.0 / self.config.max_updates_per_second
        if current_time - last_update < min_interval:
            return False

        self._last_update_times[key] = current_time
        return True

    def _has_relevant_changes(self, key: str, pair: TokenPair) -> bool:
        """Check if monitored fields have changed"""
        if key not in self._cache:
            return True  # First update

        cached_values = self._cache[key]
        current_values = self._extract_values(pair)

        # Check each monitored field
        for field_name in self.config.change_fields:
            if (
                field_name in current_values
                and field_name in cached_values
                and current_values[field_name] != cached_values[field_name]
            ):
                return True

        return False

    def _are_changes_significant(self, key: str, pair: TokenPair) -> bool:
        """Check if changes meet significance thresholds"""
        if key not in self._cache:
            return True  # First update is always significant

        cached_values = self._cache[key]

        # Check price change threshold
        if self.config.price_change_threshold is not None and not self._check_threshold(
            cached_values.get("price_usd"), pair.price_usd, self.config.price_change_threshold
        ):
            return False

        # Check volume change threshold
        if self.config.volume_change_threshold is not None:
            current_volume = pair.volume.h24 if pair.volume else None
            cached_volume = cached_values.get("volume.h24")
            if not self._check_threshold(cached_volume, current_volume, self.config.volume_change_threshold):
                return False

        # Check liquidity change threshold
        if self.config.liquidity_change_threshold is not None:
            current_liquidity = pair.liquidity.usd if pair.liquidity else None
            cached_liquidity = cached_values.get("liquidity.usd")
            if not self._check_threshold(cached_liquidity, current_liquidity, self.config.liquidity_change_threshold):
                return False

        return True

    def _check_threshold(self, old_value: Optional[float], new_value: Optional[float], threshold: float) -> bool:
        """Check if change exceeds threshold"""
        if old_value is None or new_value is None:
            return True  # Can't compare, allow update

        if old_value == 0:
            return new_value != 0  # Any change from 0 is significant

        change_ratio = abs(new_value - old_value) / abs(old_value)
        return change_ratio >= threshold

    def _extract_values(self, pair: TokenPair) -> dict[str, Any]:
        """Extract values for monitored fields"""
        values = {}

        for field_name in self.config.change_fields:
            if "." in field_name:
                # Handle nested fields like "volume.h24"
                parts = field_name.split(".")
                obj: Any = pair

                for part in parts:
                    obj = getattr(obj, part, None)
                    if obj is None:
                        break

                values[field_name] = obj
            else:
                # Direct field
                values[field_name] = getattr(pair, field_name, None)

        return values

    def _update_cache(self, key: str, pair: TokenPair):
        """Update cached values"""
        self._cache[key] = self._extract_values(pair)

    def reset(self, key: Optional[str] = None):
        """Reset filter state for a specific key or all keys"""
        reset_context = {
            "operation": "filter_reset",
            "reset_scope": "single_key" if key else "all_keys",
            "key": key if key else None,
            "cache_size_before": len(self._cache),
        }

        if key:
            self._cache.pop(key, None)
            self._last_update_times.pop(key, None)
            reset_context["cache_size_after"] = len(self._cache)

            self.contextual_logger.debug("Filter state reset for key: %s", key, context=reset_context)
        else:
            self._cache.clear()
            self._last_update_times.clear()
            reset_context["cache_size_after"] = 0

            self.contextual_logger.info("Filter state reset for all keys", context=reset_context)

    def get_filter_stats(self) -> dict[str, Any]:
        """Get comprehensive filter statistics"""
        total_blocks = (
            self.stats["rate_limited_blocks"]
            + self.stats["no_change_blocks"]
            + self.stats["insignificant_change_blocks"]
        )

        stats = self.stats.copy()
        stats.update(
            {
                "total_blocks": total_blocks,
                "block_rate": total_blocks / max(1, self.stats["total_evaluations"]),
                "cache_size": len(self._cache),
                "tracked_subscriptions": len(self._last_update_times),
                "config": {
                    "change_fields": self.config.change_fields,
                    "price_threshold": self.config.price_change_threshold,
                    "volume_threshold": self.config.volume_change_threshold,
                    "liquidity_threshold": self.config.liquidity_change_threshold,
                    "max_updates_per_second": self.config.max_updates_per_second,
                },
            }
        )

        return stats

    def log_stats(self, operation: str = "filter_stats"):
        """Log current filter statistics"""
        stats = self.get_filter_stats()

        stats_context = {"operation": operation, **stats}

        self.contextual_logger.info(
            "Filter stats: %d evaluations, %d emissions (%.1f%%), %d blocks (%.1f%%)",
            stats["total_evaluations"],
            stats["total_emissions"],
            stats["emission_rate"] * 100,
            stats["total_blocks"],
            stats["block_rate"] * 100,
            context=stats_context,
        )


# Preset configurations
class FilterPresets:
    """Common filter configurations"""

    @staticmethod
    def simple_change_detection() -> FilterConfig:
        """Basic change detection (default behavior)"""
        return FilterConfig()

    @staticmethod
    def significant_price_changes(threshold: float = 0.01) -> FilterConfig:
        """Only emit on significant price changes"""
        return FilterConfig(change_fields=["price_usd"], price_change_threshold=threshold)

    @staticmethod
    def significant_all_changes(
        price_threshold: float = 0.005,
        volume_threshold: float = 0.10,
        liquidity_threshold: float = 0.05,
    ) -> FilterConfig:
        """Only emit on significant changes in any metric"""
        return FilterConfig(
            price_change_threshold=price_threshold,
            volume_change_threshold=volume_threshold,
            liquidity_change_threshold=liquidity_threshold,
        )

    @staticmethod
    def rate_limited(max_per_second: float = 1.0) -> FilterConfig:
        """Rate limit updates"""
        return FilterConfig(max_updates_per_second=max_per_second)

    @staticmethod
    def ui_friendly() -> FilterConfig:
        """Suitable for UI updates - rate limited with significance thresholds"""
        return FilterConfig(
            price_change_threshold=0.001,  # 0.1% price change
            volume_change_threshold=0.05,  # 5% volume change
            max_updates_per_second=2.0,  # Max 2 updates per second
        )

    @staticmethod
    def monitoring() -> FilterConfig:
        """For monitoring dashboards - less frequent updates"""
        return FilterConfig(
            price_change_threshold=0.01,  # 1% price change
            volume_change_threshold=0.10,  # 10% volume change
            liquidity_change_threshold=0.05,  # 5% liquidity change
            max_updates_per_second=0.2,  # Max 1 update per 5 seconds
        )
