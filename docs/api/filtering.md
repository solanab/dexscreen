# Filtering Configuration

Filtering allows you to control when streaming callbacks are triggered, reducing noise and focusing on meaningful
changes.

## Overview

The filtering system provides:

- **Change Detection** - Only trigger on actual data changes
- **Threshold Filtering** - Trigger only on significant changes
- **Rate Limiting** - Control maximum update frequency
- **Field Selection** - Monitor specific fields only

## FilterConfig Class

Custom filtering configuration for precise control.

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FilterConfig:
    # Fields to monitor for changes
    change_fields: List[str] = field(default_factory=lambda: [
        "price_usd", "price_native", "volume.h24", "liquidity.usd"
    ])

    # Change thresholds (None = any change triggers)
    price_change_threshold: Optional[float] = None      # Price change % (e.g., 0.01 = 1%)
    volume_change_threshold: Optional[float] = None     # Volume change % (e.g., 0.10 = 10%)
    liquidity_change_threshold: Optional[float] = None  # Liquidity change % (e.g., 0.05 = 5%)

    # Rate limiting
    max_updates_per_second: Optional[float] = None      # Max updates/sec (e.g., 1.0 = 1/sec)
```

### Parameters

- **`change_fields`**: List of fields to monitor. Only changes in these fields can trigger updates. Supports nested
  fields (e.g., "volume.h24")
- **`price_change_threshold`**: Price change percentage threshold. Set to 0.01 for 1% changes
- **`volume_change_threshold`**: Volume change percentage threshold. Set to 0.10 for 10% changes
- **`liquidity_change_threshold`**: Liquidity change percentage threshold. Set to 0.05 for 5% changes
- **`max_updates_per_second`**: Limits update frequency to avoid overwhelming callbacks

### Custom Configuration Examples

```python
from dexscreen.utils import FilterConfig

# High-frequency trading config
hft_config = FilterConfig(
    change_fields=["price_usd"],           # Only monitor price
    price_change_threshold=0.0001,         # 0.01% changes
    max_updates_per_second=10.0            # Allow frequent updates
)

# Long-term monitoring config
hodl_config = FilterConfig(
    change_fields=["price_usd", "liquidity.usd"],
    price_change_threshold=0.05,           # 5% changes
    liquidity_change_threshold=0.20,       # 20% liquidity changes
    max_updates_per_second=0.1             # Once per 10 seconds max
)

# Volume surge detection
volume_config = FilterConfig(
    change_fields=["volume.h24", "volume.h1", "transactions.m5.buys", "transactions.m5.sells"],
    volume_change_threshold=0.15,          # 15% volume changes
    max_updates_per_second=0.5             # Once per 2 seconds max
)
```

## FilterPresets

Pre-configured filters for common use cases.

### simple_change_detection()

```python
config = FilterPresets.simple_change_detection()
```

Basic change detection (default behavior) - any monitored field change triggers an update.

**Use for**: General monitoring where you want all changes

### significant_price_changes(threshold)

```python
config = FilterPresets.significant_price_changes(0.01)  # 1% threshold
```

Only triggers when price changes exceed the threshold.

**Use for**: Price alerts, trading signals

### significant_all_changes(price_threshold, volume_threshold, liquidity_threshold)

```python
config = FilterPresets.significant_all_changes(
    price_threshold=0.005,      # 0.5% price change
    volume_threshold=0.10,      # 10% volume change
    liquidity_threshold=0.05    # 5% liquidity change
)
```

All metrics must meet their thresholds to trigger.

**Use for**: High-confidence signals requiring multiple confirmations

### rate_limited(max_per_second)

```python
config = FilterPresets.rate_limited(1.0)  # Max 1 update per second
```

Limits update frequency regardless of changes.

**Use for**: UI updates, reducing callback load

### ui_friendly()

```python
config = FilterPresets.ui_friendly()
```

Optimized for user interfaces:

- Price change threshold: 0.1%
- Volume change threshold: 5%
- Max 2 updates per second

**Use for**: Dashboard displays, real-time charts

### monitoring()

```python
config = FilterPresets.monitoring()
```

Optimized for monitoring systems:

- Price change threshold: 1%
- Volume change threshold: 10%
- Liquidity change threshold: 5%
- Max 0.2 updates per second (once per 5 seconds)

**Use for**: Alert systems, background monitoring

## Usage Examples

### Basic Filtering

```python
# Default filtering (changes only)
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6..."],
    callback=handle_update,
    filter=True  # Default
)

# No filtering (all updates)
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6..."],
    callback=handle_update,
    filter=False
)

# Preset filtering
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6..."],
    callback=handle_update,
    filter=FilterPresets.significant_price_changes(0.02)  # 2%
)
```

### Advanced Filtering

```python
# Multi-metric monitoring
comprehensive_config = FilterConfig(
    change_fields=["price_usd", "volume.h24", "liquidity.usd", "price_change.h24"],
    price_change_threshold=0.02,           # 2% price change
    volume_change_threshold=0.25,          # 25% volume change
    liquidity_change_threshold=0.10,       # 10% liquidity change
    max_updates_per_second=1.0             # Max once per second
)

await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=addresses,
    callback=comprehensive_handler,
    filter=comprehensive_config
)
```

### Conditional Filtering

Combine filtering with callback logic:

```python
# Filter config for significant changes
config = FilterConfig(
    change_fields=["price_usd", "volume.h1"],
    price_change_threshold=0.001  # 0.1%
)

# Additional logic in callback
def smart_callback(pair: TokenPair):
    # Filter already ensured significant change
    # Add more conditions
    if pair.volume.h1 > 10_000:  # Minimum volume
        if pair.liquidity and pair.liquidity.usd > 50_000:  # Minimum liquidity
            process_significant_update(pair)
```

## Monitorable Fields

Fields you can monitor in `change_fields`:

### Price Fields

- `price_usd` - USD price
- `price_native` - Native token price

### Volume Fields

- `volume.h24` - 24-hour volume
- `volume.h6` - 6-hour volume
- `volume.h1` - 1-hour volume
- `volume.m5` - 5-minute volume

### Liquidity Fields

- `liquidity.usd` - USD liquidity
- `liquidity.base` - Base token liquidity
- `liquidity.quote` - Quote token liquidity

### Transaction Fields

- `transactions.m5.buys` - 5-minute buy count
- `transactions.m5.sells` - 5-minute sell count
- `transactions.h1.buys` - 1-hour buy count
- `transactions.h1.sells` - 1-hour sell count
- `transactions.h6.buys` - 6-hour buy count
- `transactions.h6.sells` - 6-hour sell count
- `transactions.h24.buys` - 24-hour buy count
- `transactions.h24.sells` - 24-hour sell count

### Price Change Fields

- `price_change.m5` - 5-minute price change %
- `price_change.h1` - 1-hour price change %
- `price_change.h6` - 6-hour price change %
- `price_change.h24` - 24-hour price change %

### Other Fields

- `fdv` - Fully diluted valuation

**Note**: Use dot notation for nested fields (e.g., `volume.h24`, `transactions.m5.buys`)

## Performance Considerations

### Filter Efficiency

Filters are applied client-side after data is fetched:

1. **Data Fetching**: Happens at the specified interval
2. **Change Detection**: Compares with previous data
3. **Threshold Check**: Applies configured thresholds
4. **Rate Limiting**: Enforces max update frequency
5. **Callback Execution**: Only if all conditions pass

### Optimization Tips

1. **Minimize Monitored Fields**: Only include fields you actually need

   ```python
   # Good - specific fields
   change_fields=["price_usd", "volume.h24"]

   # Bad - monitoring everything
   change_fields=["price_usd", "price_native", "volume.h24", "volume.h6", ...]
   ```

2. **Set Appropriate Thresholds**: Balance between sensitivity and noise

   ```python
   # High-value assets - larger threshold
   eth_config = FilterConfig(price_change_threshold=0.01)  # 1%

   # Low-value/volatile assets - smaller threshold
   meme_config = FilterConfig(price_change_threshold=0.001)  # 0.1%
   ```

3. **Use Rate Limiting**: Prevent callback overload

   ```python
   # For UI updates
   ui_config = FilterConfig(max_updates_per_second=2.0)

   # For logging/database
   db_config = FilterConfig(max_updates_per_second=0.1)  # Once per 10 sec
   ```

## Common Patterns

### Price Alert System

```python
# Different alert levels
minor_alert = FilterConfig(
    change_fields=["price_usd"],
    price_change_threshold=0.02,  # 2%
    max_updates_per_second=1.0
)

major_alert = FilterConfig(
    change_fields=["price_usd"],
    price_change_threshold=0.05,  # 5%
    max_updates_per_second=None   # No rate limit for major alerts
)

# Subscribe with different callbacks
await client.subscribe_pairs(chain_id, pairs, minor_callback, filter=minor_alert)
await client.subscribe_pairs(chain_id, pairs, major_callback, filter=major_alert)
```

### Multi-Strategy Filtering

```python
strategies = {
    "scalping": FilterConfig(
        change_fields=["price_usd"],
        price_change_threshold=0.0005,  # 0.05%
        max_updates_per_second=10.0
    ),
    "swing": FilterConfig(
        change_fields=["price_usd", "volume.h24"],
        price_change_threshold=0.02,    # 2%
        volume_change_threshold=0.30,   # 30%
        max_updates_per_second=0.2      # Once per 5 sec
    ),
    "liquidity": FilterConfig(
        change_fields=["liquidity.usd"],
        liquidity_change_threshold=0.10,  # 10%
        max_updates_per_second=0.1        # Once per 10 sec
    )
}

# Apply different strategies to different pairs
for strategy_name, config in strategies.items():
    pairs = get_pairs_for_strategy(strategy_name)
    callback = create_strategy_callback(strategy_name)
    await client.subscribe_pairs("ethereum", pairs, callback, filter=config)
```

### Production Alert System

```python
from enum import Enum
from datetime import datetime

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class ProductionAlertSystem:
    def __init__(self):
        self.alert_count = {level: 0 for level in AlertLevel}

    async def deploy_monitoring(self, client, watch_pairs):
        """Deploy production-grade filtering system"""

        # Tier 1: Informational (1% moves)
        info_filter = FilterConfig(
            change_fields=["price_usd"],
            price_change_threshold=0.01,
            max_updates_per_second=0.5  # Don't spam
        )

        # Tier 2: Warning (5% moves + volume)
        warning_filter = FilterConfig(
            change_fields=["price_usd", "volume.h24"],
            price_change_threshold=0.05,
            volume_change_threshold=0.75,
            max_updates_per_second=2.0
        )

        # Tier 3: Critical (10% moves + liquidity issues)
        critical_filter = FilterConfig(
            change_fields=["price_usd", "liquidity.usd"],
            price_change_threshold=0.10,
            liquidity_change_threshold=0.25,
            max_updates_per_second=10.0  # No limits on critical
        )

        # Deploy all tiers
        await client.subscribe_pairs(
            "ethereum", watch_pairs,
            lambda p: self.handle_alert(p, AlertLevel.INFO),
            filter=info_filter
        )

        await client.subscribe_pairs(
            "ethereum", watch_pairs,
            lambda p: self.handle_alert(p, AlertLevel.WARNING),
            filter=warning_filter
        )

        await client.subscribe_pairs(
            "ethereum", watch_pairs,
            lambda p: self.handle_alert(p, AlertLevel.CRITICAL),
            filter=critical_filter
        )

        print(f"🚀 Production monitoring deployed for {len(watch_pairs)} pairs")

    async def handle_alert(self, pair, level: AlertLevel):
        self.alert_count[level] += 1

        if level == AlertLevel.CRITICAL:
            await self.send_sms(f"CRITICAL: {pair.base_token.symbol} moved {pair.price_change.h24:+.1f}%")
            await self.send_email_alert(pair, level)
        elif level == AlertLevel.WARNING:
            await self.send_slack_message(pair, level)
        else:
            print(f"📊 {pair.base_token.symbol}: {pair.price_change.h24:+.2f}%")

    async def send_sms(self, message): pass  # Implement SMS
    async def send_email_alert(self, pair, level): pass  # Implement email
    async def send_slack_message(self, pair, level): pass  # Implement Slack

# Usage
alert_system = ProductionAlertSystem()
watch_list = ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]  # Add your pairs
await alert_system.deploy_monitoring(client, watch_list)
```
