"""
Test filter functionality
"""

import time

from dexscreen.core.models import TokenPair
from dexscreen.utils.filters import FilterConfig, FilterPresets, TokenPairFilter


class TestTokenPairFilter:
    """Test TokenPairFilter class"""

    def test_filter_initialization(self):
        """Test filter initialization"""
        # Default configuration
        filter1 = TokenPairFilter()
        assert filter1.config is not None
        assert isinstance(filter1.config.change_fields, list)

        # Custom configuration
        config = FilterConfig(change_fields=["price_usd"], price_change_threshold=0.01)
        filter2 = TokenPairFilter(config)
        assert filter2.config == config

    def test_first_update_always_emitted(self, simple_test_pair_data):
        """Test that the first update is always emitted"""
        filter_instance = TokenPairFilter()
        pair = TokenPair(**simple_test_pair_data)

        # First update should always pass
        assert filter_instance.should_emit("test_key", pair) is True

    def test_simple_change_detection(self, simple_test_pair_data):
        """Test simple change detection"""
        filter_instance = TokenPairFilter()
        pair1 = TokenPair(**simple_test_pair_data)

        # First update
        assert filter_instance.should_emit("test_key", pair1) is True

        # Same data, should not trigger
        pair2 = TokenPair(**simple_test_pair_data)
        assert filter_instance.should_emit("test_key", pair2) is False

        # Price change, should trigger
        simple_test_pair_data["priceUsd"] = "101.0"
        pair3 = TokenPair(**simple_test_pair_data)
        assert filter_instance.should_emit("test_key", pair3) is True

    def test_price_change_threshold(self, simple_test_pair_data):
        """Test price change threshold"""
        config = FilterConfig(price_change_threshold=0.05)  # 5% threshold
        filter_instance = TokenPairFilter(config)

        pair1 = TokenPair(**simple_test_pair_data)
        assert filter_instance.should_emit("test_key", pair1) is True

        # Small change (1%), should not trigger
        simple_test_pair_data["priceUsd"] = "101.0"
        pair2 = TokenPair(**simple_test_pair_data)
        assert filter_instance.should_emit("test_key", pair2) is False

        # Large change (10%), should trigger
        simple_test_pair_data["priceUsd"] = "110.0"
        pair3 = TokenPair(**simple_test_pair_data)
        assert filter_instance.should_emit("test_key", pair3) is True

    def test_rate_limiting(self, simple_test_pair_data):
        """Test rate limiting"""
        config = FilterConfig(max_updates_per_second=2.0)  # Max 2 updates per second
        filter_instance = TokenPairFilter(config)

        pair = TokenPair(**simple_test_pair_data)

        # First update should pass
        assert filter_instance.should_emit("test_key", pair) is True

        # Immediate second update should be blocked (even if data changes)
        simple_test_pair_data["priceUsd"] = "200.0"
        pair2 = TokenPair(**simple_test_pair_data)
        assert filter_instance.should_emit("test_key", pair2) is False

        # Should pass after waiting enough time
        time.sleep(0.6)
        simple_test_pair_data["priceUsd"] = "300.0"
        pair3 = TokenPair(**simple_test_pair_data)
        assert filter_instance.should_emit("test_key", pair3) is True

    def test_multiple_keys(self, simple_test_pair_data):
        """Test independent filtering for multiple subscription keys"""
        filter_instance = TokenPairFilter()

        pair1 = TokenPair(**simple_test_pair_data)
        pair2 = TokenPair(**simple_test_pair_data)

        # Different keys should be filtered independently
        assert filter_instance.should_emit("key1", pair1) is True
        assert filter_instance.should_emit("key2", pair2) is True

        # Second update with the same data should be filtered
        assert filter_instance.should_emit("key1", pair1) is False
        assert filter_instance.should_emit("key2", pair2) is False

    def test_reset_functionality(self, simple_test_pair_data):
        """Test reset functionality"""
        filter_instance = TokenPairFilter()
        pair = TokenPair(**simple_test_pair_data)

        # Initial update
        assert filter_instance.should_emit("test_key", pair) is True
        assert filter_instance.should_emit("test_key", pair) is False

        # Reset specific key
        filter_instance.reset("test_key")
        assert filter_instance.should_emit("test_key", pair) is True

        # Reset all
        filter_instance.reset()
        assert len(filter_instance._cache) == 0
        assert len(filter_instance._last_update_times) == 0


class TestFilterPresets:
    """Test preset filter configurations"""

    def test_simple_change_detection_preset(self):
        """Test simple change detection preset"""
        config = FilterPresets.simple_change_detection()
        assert isinstance(config, FilterConfig)
        assert config.price_change_threshold is None
        assert config.volume_change_threshold is None
        assert config.max_updates_per_second is None

    def test_significant_price_changes_preset(self):
        """Test significant price change preset"""
        config = FilterPresets.significant_price_changes(0.02)
        assert config.price_change_threshold == 0.02
        assert config.change_fields == ["price_usd"]

    def test_significant_all_changes_preset(self):
        """Test significant all changes preset"""
        config = FilterPresets.significant_all_changes()
        assert config.price_change_threshold == 0.005
        assert config.volume_change_threshold == 0.10
        assert config.liquidity_change_threshold == 0.05

    def test_rate_limited_preset(self):
        """Test rate limited preset"""
        config = FilterPresets.rate_limited(0.5)
        assert config.max_updates_per_second == 0.5

    def test_ui_friendly_preset(self):
        """Test UI friendly preset"""
        config = FilterPresets.ui_friendly()
        assert config.price_change_threshold == 0.001
        assert config.volume_change_threshold == 0.05
        assert config.max_updates_per_second == 2.0

    def test_monitoring_preset(self):
        """Test monitoring preset"""
        config = FilterPresets.monitoring()
        assert config.price_change_threshold == 0.01
        assert config.volume_change_threshold == 0.10
        assert config.liquidity_change_threshold == 0.05
        assert config.max_updates_per_second == 0.2


class TestFilterEdgeCases:
    """Test filter edge cases"""

    def test_none_values_handling(self):
        """Test handling of None values"""
        filter_instance = TokenPairFilter()

        # Create data with None values
        pair_data = {
            "chainId": "ethereum",
            "dexId": "uniswap",
            "url": "https://test.com",
            "pairAddress": "0x123",
            "baseToken": {"address": "0xabc", "name": "Token A", "symbol": "TKA"},
            "quoteToken": {"address": "0xdef", "name": "Token B", "symbol": "TKB"},
            "priceNative": "1.0",
            "priceUsd": None,  # None value
            "txns": {
                "m5": {"buys": 10, "sells": 5},
                "h1": {"buys": 100, "sells": 50},
                "h6": {"buys": 600, "sells": 300},
                "h24": {"buys": 2400, "sells": 1200},
            },
            "volume": {"m5": 1000.0, "h1": 5000.0, "h6": 30000.0, "h24": 120000.0},
            "priceChange": {"m5": 0.5, "h1": -0.2, "h6": 1.5, "h24": -2.3},
        }

        pair = TokenPair(**pair_data)
        # Should be able to handle None values
        assert filter_instance.should_emit("test_key", pair) is True

    def test_zero_to_nonzero_change(self):
        """Test change from zero to non-zero"""
        config = FilterConfig(price_change_threshold=0.01)
        filter_instance = TokenPairFilter(config)

        # Initial price is 0
        pair_data = {
            "chainId": "ethereum",
            "dexId": "uniswap",
            "url": "https://test.com",
            "pairAddress": "0x123",
            "baseToken": {"address": "0xabc", "name": "Token A", "symbol": "TKA"},
            "quoteToken": {"address": "0xdef", "name": "Token B", "symbol": "TKB"},
            "priceNative": "0",
            "priceUsd": 0.0,
            "txns": {
                "m5": {"buys": 0, "sells": 0},
                "h1": {"buys": 0, "sells": 0},
                "h6": {"buys": 0, "sells": 0},
                "h24": {"buys": 0, "sells": 0},
            },
            "volume": {"m5": 0, "h1": 0, "h6": 0, "h24": 0},
            "priceChange": {"m5": 0, "h1": 0, "h6": 0, "h24": 0},
        }

        pair1 = TokenPair(**pair_data)
        assert filter_instance.should_emit("test_key", pair1) is True

        # Any non-zero value from 0 should trigger
        pair_data["priceUsd"] = 0.001
        pair2 = TokenPair(**pair_data)
        assert filter_instance.should_emit("test_key", pair2) is True
