# Streaming API Reference

The Streaming API provides real-time data updates through HTTP polling, supporting dynamic subscription management,
flexible filtering, and multi-chain monitoring.

> **💡 Key Feature**: Unlike WebSocket-based APIs, Dexscreen uses intelligent HTTP polling for better reliability and
> easier debugging.

## Overview

Streaming methods provide continuous updates for price changes, volume, liquidity, and other metrics through intelligent
polling.

### Perfect For:

- **💰 Trading Bots** - Real-time price monitoring and execution
- **🔄 Arbitrage Detection** - Cross-chain price difference monitoring
- **📊 Portfolio Tracking** - Multi-asset performance monitoring
- **🔍 Token Discovery** - New pair and listing detection
- **🚨 Alert Systems** - Custom threshold-based notifications

> **⚡ Performance**: Polling intervals as low as 0.2 seconds with intelligent batching and filtering.

## Core Features

### 🔄 Dynamic Subscription Management

Subscriptions are **cumulative** - adding more pairs extends your monitoring rather than replacing it:

```python
# 1. Start monitoring USDC/WETH
await client.subscribe_pairs("ethereum", ["0xaaa..."], callback)

# 2. Add more pairs (now monitoring 3 pairs total)
await client.subscribe_pairs("ethereum", ["0xbbb...", "0xccc..."], callback)

# 3. Remove specific pairs (now monitoring 2 pairs)
await client.unsubscribe_pairs("ethereum", ["0xaaa..."])

# 4. Check what's currently active
active = client.get_active_subscriptions()
print(f"Monitoring {len(active)} subscriptions")
```

> **📘 Important**: Each `subscribe_pairs()` call **adds** to existing subscriptions - it doesn't replace them.

### 🌐 Multi-chain Support

Monitor multiple blockchains simultaneously with independent configurations:

```python
# Each chain can have different settings
await client.subscribe_pairs(
    "ethereum", eth_pairs, eth_callback,
    interval=1.0,  # Slower for expensive chains
    filter=FilterPresets.significant_price_changes(0.01)
)

await client.subscribe_pairs(
    "solana", sol_pairs, sol_callback,
    interval=0.2,  # Faster for cheaper chains
    filter=FilterPresets.ui_friendly()
)

await client.subscribe_pairs(
    "bsc", bsc_pairs, bsc_callback,
    interval=0.5,  # Balanced for moderate costs
    filter=FilterPresets.monitoring()
)
```

> **🚀 Pro Tip**: Adjust intervals based on chain speed and costs - faster chains can use shorter intervals.

## Main Methods

### subscribe_pairs

```python
async def subscribe_pairs(
    chain_id: str,
    pair_addresses: List[str],
    callback: Callable[[TokenPair], None],
    *,
    filter: Union[bool, FilterConfig] = True,
    interval: float = 0.2
) -> None
```

Subscribe to real-time pair updates. Supports dynamic addition - multiple calls accumulate subscriptions rather than
replacing them.

**Parameters:**

- `chain_id`: Blockchain identifier (e.g., "ethereum", "solana")
- `pair_addresses`: List of pair contract addresses
- `callback`: Function called on each update, receives TokenPair object
- `filter`: Filtering configuration:
  - `True` (default): Only emit on data changes
  - `False`: Emit all polling results
  - `FilterConfig` object: Custom filtering rules
- `interval`: Polling interval in seconds (default 0.2s)

**Real-World Examples:**

```python
# Example 1: High-frequency trading monitor
await client.subscribe_pairs(
    "ethereum",
    ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],  # USDC/ETH
    hft_callback,
    filter=FilterPresets.significant_price_changes(0.001),  # 0.1% sensitivity
    interval=0.2  # Very fast updates
)

# Example 2: Cross-DEX arbitrage scanner
# Monitor WETH/USDC on different DEXs
weth_usdc_pairs = [
    "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # Uniswap V3
    "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",  # Uniswap V3 (different fee)
    "0x397ff1542f962076d0bfe58ea045ffa2d347aca0"   # Sushiswap
]

await client.subscribe_pairs(
    "ethereum",
    weth_usdc_pairs,
    arbitrage_scanner,
    filter=False,  # Need all price updates for comparison
    interval=0.5   # Fast enough for arb opportunities
)

# Example 3: Portfolio tracking with smart filtering
portfolio_config = FilterConfig(
    change_fields=["price_usd", "volume.h24", "liquidity.usd"],
    price_change_threshold=0.02,     # 2% price change threshold
    volume_change_threshold=0.15,    # 15% volume change threshold
    max_updates_per_second=0.5       # Max 1 update per 2 seconds
)

await client.subscribe_pairs(
    "ethereum",
    portfolio_pairs,
    portfolio_tracker,
    filter=portfolio_config,
    interval=10.0  # Relaxed checking for long-term holdings
)
```

### subscribe_tokens

```python
async def subscribe_tokens(
    chain_id: str,
    token_addresses: List[str],
    callback: Callable[[List[TokenPair]], None],
    *,
    filter: Union[bool, FilterConfig] = True,
    interval: float = 0.2
) -> None
```

Subscribe to all pairs of specific tokens. Automatically discovers new pairs - ideal for comprehensive token monitoring.

**Parameters:**

- `chain_id`: Blockchain identifier
- `token_addresses`: List of token contract addresses
- `callback`: Function receiving list of all pairs for the token
- `filter`: Filtering configuration (same as subscribe_pairs)
- `interval`: Polling interval in seconds

**Real-World Examples:**

```python
# Example 1: New token launch monitor
# Great for discovering new DEX listings
await client.subscribe_tokens(
    "solana",
    ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"],  # USDC on Solana
    new_listing_detector,
    filter=False,  # Get all updates to catch new pairs immediately
    interval=1.0   # Check every second for new listings
)

# Example 2: Stablecoin liquidity monitoring across all pairs
# Monitor USDC liquidity changes across all DEXs
await client.subscribe_tokens(
    "ethereum",
    ["A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],  # USDC
    liquidity_monitor,
    filter=FilterConfig(
        change_fields=["liquidity.usd", "volume.h1"],
        liquidity_change_threshold=0.05,  # 5% liquidity threshold
        volume_change_threshold=0.25      # 25% volume spike threshold
    ),
    interval=5.0  # Check every 5 seconds for liquidity changes
)

# Example 3: Multi-DEX price comparison for arbitrage
def price_comparison_callback(pairs: List[TokenPair]):
    """Analyze price differences across DEXs"""
    if len(pairs) < 2:
        return

    # Group pairs by DEX
    dex_prices = {}
    for pair in pairs:
        if pair.price_usd:
            dex_prices[pair.dex_id] = pair.price_usd

    # Find arbitrage opportunities
    if len(dex_prices) >= 2:
        prices = list(dex_prices.values())
        spread = (max(prices) - min(prices)) / min(prices)

        if spread > 0.005:  # 0.5% spread threshold
            print(f"Arbitrage opportunity: {spread:.2%} spread")
            for dex, price in dex_prices.items():
                print(f"  {dex}: ${price:.6f}")

# Monitor WETH across all BSC DEXs
await client.subscribe_tokens(
    "bsc",
    ["0x2170Ed0880ac9A755fd29B2688956BD959F933F8"],  # WETH on BSC
    price_comparison_callback,
    interval=2.0
)
```

### unsubscribe_pairs

```python
async def unsubscribe_pairs(chain_id: str, pair_addresses: List[str]) -> None
```

Remove specific pair subscriptions. Chain ID must match exactly.

```python
# Remove single subscription
await client.unsubscribe_pairs("ethereum", ["0xaaa..."])

# Batch removal (more efficient)
await client.unsubscribe_pairs("ethereum", [
    "0xaaa...",
    "0xbbb...",
    "0xccc..."
])

# ⚠️ Chain ID must match exactly
# This WON'T remove the subscription (wrong chain)
await client.unsubscribe_pairs("bsc", ["0xaaa..."])  # Address on ethereum
```

> **📝 Note**: Unsubscribing from non-existent pairs is safe and will be ignored.

### unsubscribe_tokens

```python
async def unsubscribe_tokens(chain_id: str, token_addresses: List[str]) -> None
```

Remove all pair subscriptions for specific tokens.

```python
# Stop monitoring USDC
await client.unsubscribe_tokens(
    "ethereum",
    ["A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]
)
```

### close_streams

```python
async def close_streams() -> None
```

Gracefully close all subscriptions and streaming connections. **Always call this on program exit.**

```python
# Pattern 1: Try/finally (recommended)
try:
    await client.subscribe_pairs(...)
    await asyncio.sleep(300)  # Run for 5 minutes
finally:
    await client.close_streams()  # Always cleanup

# Pattern 2: Context manager style
async def monitor_with_cleanup():
    client = DexscreenerClient()
    try:
        await client.subscribe_pairs(...)
        # Your monitoring logic
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await client.close_streams()
        print("Streams closed.")
```

> **⚠️ Important**: Failing to call `close_streams()` may leave background tasks running.

## Management Methods

### get_active_subscriptions

```python
def get_active_subscriptions() -> List[Dict[str, Any]]
```

Get detailed information about all active subscriptions.

```python
# View all subscriptions
active = client.get_active_subscriptions()
for sub in active:
    if sub["type"] == "pair":
        print(f"Pair: {sub['chain_id']}:{sub['pair_address']}")
    else:
        print(f"Token: {sub['chain_id']}:{sub['token_address']}")

# Return format example
[
    {
        "type": "pair",
        "chain_id": "ethereum",
        "pair_address": "0x88e6...",
        "filter": True,
        "interval": 1.0
    },
    {
        "type": "token",
        "chain_id": "solana",
        "token_address": "EPjFW...",
        "filter": FilterConfig(...),
        "interval": 0.2
    }
]
```

## Advanced Usage

### Complete Subscription Lifecycle Management

```python
class PortfolioManager:
    def __init__(self):
        self.client = DexscreenerClient()
        self.active_pairs = set()

    async def add_pair(self, chain_id: str, pair_address: str):
        """Dynamically add a pair to the portfolio"""
        if (chain_id, pair_address) not in self.active_pairs:
            await self.client.subscribe_pairs(
                chain_id,
                [pair_address],
                self.handle_update,
                filter=FilterPresets.monitoring()
            )
            self.active_pairs.add((chain_id, pair_address))

    async def remove_pair(self, chain_id: str, pair_address: str):
        """Remove a pair from the portfolio"""
        if (chain_id, pair_address) in self.active_pairs:
            await self.client.unsubscribe_pairs(chain_id, [pair_address])
            self.active_pairs.remove((chain_id, pair_address))

    def handle_update(self, pair: TokenPair):
        """Process price updates"""
        # Implement your logic
        pass

# Usage example
manager = PortfolioManager()

# Dynamic management
await manager.add_pair("ethereum", "0xaaa...")
await manager.add_pair("ethereum", "0xbbb...")
await manager.remove_pair("ethereum", "0xaaa...")
```

### Multi-Strategy Parallel Monitoring

```python
# Create different monitoring strategies for different purposes
client = DexscreenerClient()

# Strategy 1: High-frequency trading monitor
await client.subscribe_pairs(
    "solana",
    hft_pairs,
    hft_callback,
    filter=FilterConfig(
        price_change_threshold=0.0001,  # 0.01%
        max_updates_per_second=10.0
    ),
    interval=0.2
)

# Strategy 2: Liquidity provider monitor
await client.subscribe_pairs(
    "ethereum",
    lp_pairs,
    lp_callback,
    filter=FilterConfig(
        change_fields=["liquidity.usd", "volume.h24"],
        liquidity_change_threshold=0.01,  # 1%
        volume_change_threshold=0.20      # 20%
    ),
    interval=5.0
)

# Strategy 3: Price alerts
alert_config = FilterConfig(
    price_change_threshold=0.05  # 5% change triggers alert
)
await client.subscribe_pairs(
    "bsc",
    alert_pairs,
    send_price_alert,
    filter=alert_config,
    interval=10.0
)
```

## Callback Best Practices

### Error Handling

Always wrap callback logic in try-except:

```python
async def safe_callback(pair: TokenPair):
    try:
        # Your logic here
        if pair.price_usd > threshold:
            await send_alert(pair)
    except Exception as e:
        logger.error(f"Callback error: {e}")
        # Don't let errors crash the subscription
```

### Async Callbacks

Callbacks can be sync or async:

```python
# Sync callback
def sync_handler(pair: TokenPair):
    print(f"Price: ${pair.price_usd}")

# Async callback
async def async_handler(pair: TokenPair):
    await database.save_price(pair)
    await check_trading_conditions(pair)

# Both work with subscribe_pairs
await client.subscribe_pairs("ethereum", addresses, sync_handler)
await client.subscribe_pairs("ethereum", addresses, async_handler)
```

### State Management

Use closures or classes for stateful callbacks:

```python
# Using closure
def create_ma_calculator(period: int):
    prices = []

    def calculate_ma(pair: TokenPair):
        prices.append(pair.price_usd)
        if len(prices) > period:
            prices.pop(0)

        if len(prices) == period:
            ma = sum(prices) / period
            print(f"MA({period}): ${ma:.4f}")

    return calculate_ma

# Using class
class TradingStrategy:
    def __init__(self):
        self.positions = {}
        self.alerts = []

    async def process_update(self, pair: TokenPair):
        # Complex stateful logic
        if self.should_buy(pair):
            await self.execute_buy(pair)
```

## Performance Optimization

### 1. Subscription Limits

- Maximum 30 pair subscriptions per chain
- Exceeding limits will log warnings and ignore extra subscriptions
- Use `subscribe_tokens` to monitor all pairs of a token (no limit)

### 2. Polling Optimization

- Multiple subscriptions on the same chain are batched automatically
- Polling interval is the minimum of all subscriptions on that chain
- Filters are applied independently per subscription

### 3. Best Practices

- Check `get_active_subscriptions()` before subscribing to avoid duplicates
- Use appropriate filtering to reduce unnecessary callbacks
- Always call `close_streams()` on program exit
- Balance polling intervals with your real-time needs

## Common Patterns

### Price Alert System

```python
class PriceAlertSystem:
    def __init__(self, alert_thresholds: Dict[str, float]):
        self.client = DexscreenerClient()
        self.thresholds = alert_thresholds
        self.last_prices = {}

    async def start_monitoring(self):
        for pair_address, threshold in self.thresholds.items():
            await self.client.subscribe_pairs(
                "ethereum",
                [pair_address],
                self.check_price,
                filter=FilterConfig(
                    price_change_threshold=threshold
                )
            )

    def check_price(self, pair: TokenPair):
        if pair.pair_address in self.last_prices:
            old_price = self.last_prices[pair.pair_address]
            change = abs(pair.price_usd - old_price) / old_price

            if change >= self.thresholds[pair.pair_address]:
                self.send_alert(pair, old_price, pair.price_usd)

        self.last_prices[pair.pair_address] = pair.price_usd
```

### Volume Surge Detection

```python
async def detect_volume_surges():
    client = DexscreenerClient()

    # Track volume history
    volume_history = defaultdict(list)

    def volume_callback(pair: TokenPair):
        history = volume_history[pair.pair_address]
        history.append(pair.volume.m5 or 0)

        # Keep last 12 periods (1 hour of 5-min data)
        if len(history) > 12:
            history.pop(0)

        if len(history) >= 6:
            recent_avg = sum(history[-3:]) / 3
            older_avg = sum(history[-6:-3]) / 3

            if older_avg > 0:
                surge = recent_avg / older_avg
                if surge > 3:  # 3x volume surge
                    print(f"Volume surge detected: {pair.base_token.symbol} - {surge:.1f}x")

    # Monitor high-liquidity pairs
    pairs = await client.search_pairs_async("ETH")
    liquid_pairs = [p for p in pairs if p.liquidity and p.liquidity.usd > 100_000]

    addresses = [p.pair_address for p in liquid_pairs[:20]]
    await client.subscribe_pairs(
        "ethereum",
        addresses,
        volume_callback,
        filter=FilterConfig(change_fields=["volume.m5"]),
        interval=0.5
    )
```
