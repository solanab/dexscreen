"""
Token pair filtering utilities for reducing noise and controlling update frequency
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..core.models import TokenPair


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

    def should_emit(self, key: str, pair: TokenPair) -> bool:
        """
        Check if update should be emitted based on filter rules.

        Args:
            key: Unique identifier for the subscription (e.g., "ethereum:0x...")
            pair: The token pair data

        Returns:
            True if update should be emitted, False otherwise
        """
        # Check rate limiting first
        if not self._check_rate_limit(key):
            return False

        # Check for changes
        if not self._has_relevant_changes(key, pair):
            return False

        # Check if changes are significant enough
        if not self._are_changes_significant(key, pair):
            return False

        # Update cache and emit
        self._update_cache(key, pair)
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
        if key:
            self._cache.pop(key, None)
            self._last_update_times.pop(key, None)
        else:
            self._cache.clear()
            self._last_update_times.clear()


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
