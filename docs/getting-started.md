# Getting Started with Dexscreen

This guide will help you get up and running with Dexscreen quickly, enabling you to monitor and analyze DeFi data with
ease.

## Installation

### Using uv

```bash
uv add dexscreen
```

### Using pip

```bash
pip install dexscreen
```

### From source

```bash
git clone https://github.com/yourusername/dexscreen.git
cd dexscreen
pip install -e .
```

## Basic Concepts

Dexscreen provides two main ways to interact with Dexscreener data:

1. **Query API** - One-time data fetching (synchronous or async) for:
   - Current price checks
   - Token discovery and search
   - Snapshot data analysis
   - Historical data retrieval

2. **Streaming API** - Real-time updates via HTTP polling for:
   - Real-time price monitoring
   - Trading bots
   - Alert systems
   - Portfolio tracking

## Your First Query

### Create a Client

```python
from dexscreen import DexscreenerClient

# Basic client (recommended for most use cases)
client = DexscreenerClient()

# With browser impersonation (use when encountering anti-bot protection)
client = DexscreenerClient(impersonate="chrome136")

# Debug mode (enable verbose logging during development)
client = DexscreenerClient(debug=True)
```

### Fetch Pair Data

```python
# 1. Search for pairs (by token name or symbol)
pairs = client.search_pairs("PEPE")
if pairs:
    print(f"Found {len(pairs)} PEPE pairs")
    for pair in pairs[:5]:  # Show top 5 results
        print(f"  {pair.base_token.symbol}/{pair.quote_token.symbol} on {pair.chain_id}")
        print(f"    Price: ${pair.price_usd:.8f}, DEX: {pair.dex_id}")
        print(f"    24h Volume: ${pair.volume.h24:,.0f}")
        print()

# 2. Get all pairs for a specific token
usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # Ethereum USDC
pairs = client.get_pairs_by_token_address("ethereum", usdc_address)
print(f"Found {len(pairs)} USDC pairs on Ethereum")

# Find the highest liquidity USDC pair
if pairs:
    best_usdc_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)
    print(f"Best USDC pair: {best_usdc_pair.base_token.symbol}/{best_usdc_pair.quote_token.symbol}")
    print(f"Liquidity: ${best_usdc_pair.liquidity.usd:,.0f}")

# 3. Get details for a specific pair
pair = client.get_pair_by_pair_address(
    "ethereum",
    "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # Uniswap V3 USDC/WETH
)
if pair:
    print(f"Pair Details:")
    print(f"  Price: ${pair.price_usd:.6f}")
    print(f"  24h Volume: ${pair.volume.h24:,.0f}")
    print(f"  24h Price Change: {pair.price_change.h24:+.2f}%")
    print(f"  DEX: {pair.dex_id}")
```

## Real-time Updates

### Basic Subscription

```python
import asyncio
from datetime import datetime

async def price_update_handler(pair):
    """Handle price updates - showing timestamp and key info"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {pair.base_token.symbol}: ${pair.price_usd:,.4f} "
          f"(24h: {pair.price_change.h24:+.2f}%)")

async def main():
    client = DexscreenerClient()

    print("Starting to monitor JUP token price...")

    # Subscribe to JUP pair on Solana
    await client.subscribe_pairs(
        chain_id="solana",
        pair_addresses=["JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"],
        callback=price_update_handler,
        interval=1.0  # Check for updates every second
    )

    # Monitor for 30 seconds
    print("Monitoring... (30 seconds)")
    await asyncio.sleep(30)

    # Clean up
    print("Closing connections...")
    await client.close_streams()
    print("Monitoring ended")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
```

### Monitor Multiple Pairs

```python
async def portfolio_monitor():
    client = DexscreenerClient()

    # Define your portfolio (chain_id, pair_address, description)
    portfolio = [
        ("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "USDC/WETH Uniswap V3"),
        ("solana", "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", "JUP/SOL Raydium"),
        ("bsc", "0x2170ed0880ac9a755fd29b2688956bd959f933f8", "ETH/BNB PancakeSwap"),
    ]

    # Portfolio update handler
    async def handle_portfolio_update(pair):
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Determine which token is the main token (non-stablecoin)
        main_token = pair.base_token if pair.base_token.symbol not in ["USDC", "USDT", "BUSD"] else pair.quote_token

        print(f"[{timestamp}] [{pair.chain_id.upper()}] {main_token.symbol}: "
              f"${pair.price_usd:,.4f} ({pair.price_change.h24:+.2f}%) "
              f"Vol: ${pair.volume.h24:,.0f}")

    print("Starting portfolio monitoring...")

    # Subscribe to all pairs
    for chain_id, pair_address, description in portfolio:
        print(f"Subscribing to {description} on {chain_id}")
        await client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=[pair_address],
            callback=handle_portfolio_update,
            interval=2.0  # Check every 2 seconds
        )

    print(f"\nMonitoring {len(portfolio)} pairs, press Ctrl+C to stop...")

    try:
        # Monitor for 1 minute (would be longer in production)
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\nInterrupt received, stopping...")
    finally:
        await client.close_streams()
        print("Portfolio monitoring stopped")

if __name__ == "__main__":
    asyncio.run(portfolio_monitor())
```

## Filtering Updates

Control when your callback is triggered using filters to reduce unnecessary notifications:

```python
from dexscreen import FilterPresets

# 1. Only trigger on significant price changes (1% threshold)
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=handle_update,
    filter=FilterPresets.significant_price_changes(0.01),  # 1% price change
    interval=0.5  # Check every 0.5 seconds
)

# 2. Limit update frequency to avoid overload
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=handle_update,
    filter=FilterPresets.rate_limited(1.0),  # Max 1 update per second
    interval=0.2  # Poll quickly but limit callback frequency
)

# 3. UI-friendly filtering (balanced update frequency and usefulness)
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=handle_update,
    filter=FilterPresets.ui_friendly(),  # Pre-configured for UI optimization
    interval=1.0
)
```

## Error Handling

Always handle errors in your callbacks to prevent subscription interruptions in production:

```python
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_callback(pair):
    try:
        # Your business logic
        if pair.price_usd and pair.price_usd > 100:
            print(f"High value token: {pair.base_token.symbol} = ${pair.price_usd:,.2f}")

        # Check for anomalous price changes
        if abs(pair.price_change.h24) > 50:  # 50% change in 24h
            logger.warning(f"Anomalous price change: {pair.base_token.symbol} {pair.price_change.h24:+.2f}%")

    except AttributeError as e:
        logger.error(f"Missing data field: {e}")
    except TypeError as e:
        logger.error(f"Data type error: {e}")
    except Exception as e:
        logger.error(f"Unknown error processing update: {e}")
        # Important: Don't re-raise to avoid breaking the subscription

# Use the safe callback
async def robust_monitoring():
    client = DexscreenerClient()

    try:
        await client.subscribe_pairs(
            chain_id="ethereum",
            pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
            callback=safe_callback,
            interval=1.0
        )

        await asyncio.sleep(30)

    except Exception as e:
        logger.error(f"Failed to set up subscription: {e}")
    finally:
        await client.close_streams()
        logger.info("Monitoring session ended")
```

## Async vs Sync

Dexscreen supports both patterns:

### Synchronous Mode

```python
# Simple and straightforward, ideal for scripts and one-time queries
client = DexscreenerClient()

# Synchronous search
pairs = client.search_pairs("PEPE")
print(f"Found {len(pairs)} PEPE pairs")

# Synchronous get specific pair
pair = client.get_pair_by_pair_address("ethereum", "0x88e6...")
if pair:
    print(f"Current price: ${pair.price_usd}")
```

### Asynchronous Mode

```python
# Better for concurrent operations, real-time monitoring, and high-performance applications
async def fetch_multiple_tokens():
    client = DexscreenerClient()

    # Define tokens to search
    tokens = ["PEPE", "SHIB", "DOGE", "FLOKI"]

    print("Searching multiple tokens concurrently...")

    # Run multiple queries concurrently (faster)
    tasks = [client.search_pairs_async(token) for token in tokens]
    results = await asyncio.gather(*tasks)

    # Process results
    for token, token_pairs in zip(tokens, results):
        if token_pairs:
            best_pair = max(token_pairs, key=lambda p: p.volume.h24 or 0)
            print(f"{token}: Found {len(token_pairs)} pairs, "
                  f"highest volume: ${best_pair.volume.h24:,.0f}")
        else:
            print(f"{token}: No pairs found")

# Run the async function
if __name__ == "__main__":
    asyncio.run(fetch_multiple_tokens())
```

## Next Steps

### 📚 Deep Dive

1. **[Query API](api/query-api.md)** - Learn all available data fetching methods
2. **[Streaming API](api/streaming-api.md)** - Master real-time data monitoring techniques
3. **[Data Models](api/data-models.md)** - Understand the data structures returned by the API
4. **[Filtering](api/filtering.md)** - Learn advanced filtering techniques for performance optimization
5. **[Examples](examples.md)** - View complete production-ready code examples

### 🚀 Project Ideas

- **Price Alert Bot**: Monitor token price changes and send notifications
- **Arbitrage Scanner**: Find arbitrage opportunities across different DEXs and chains
- **Portfolio Dashboard**: Track your DeFi portfolio in real-time
- **New Token Discovery Tool**: Automatically discover and analyze newly listed tokens
- **Liquidity Monitoring System**: Track large liquidity changes

## FAQ & Troubleshooting

### 🚦 Rate Limiting

**Problem**: Encountering rate limit errors **Solution**:

- The SDK handles rate limits automatically with backoff retry
- If frequently hitting limits, consider increasing polling intervals
- Use batch methods (e.g., `get_pairs_by_pairs_addresses`) instead of multiple individual calls

### 📊 No Data Returned

**Common causes**:

- ❌ Wrong chain_id: Use `"ethereum"` not `"eth"`
- ❌ Invalid contract addresses: Ensure addresses are correctly formatted and checksummed
- ❌ Token doesn't exist: Some tokens may not have pairs on certain chains
- ❌ New tokens: Recently launched tokens may not be indexed yet

**Solutions**:

```python
# Verify address format
from web3 import Web3
address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
if Web3.isAddress(address):
    pairs = client.get_pairs_by_token_address("ethereum", address)
else:
    print("Invalid Ethereum address")
```

### 🔄 Subscription Not Updating

**Diagnostic steps**:

1. **Check filter configuration**: Ensure filters aren't filtering out all updates

   ```python
   # Temporarily disable filter for testing
   await client.subscribe_pairs(..., filter=False)
   ```

2. **Verify pair activity**: Ensure the pair has actual trading activity

   ```python
   pair = client.get_pair_by_pair_address(chain_id, pair_address)
   if pair and pair.volume.h24 > 0:
       print("Pair is active")
   else:
       print("Pair may be inactive")
   ```

3. **Check callback errors**: Ensure callback function isn't throwing exceptions
   ```python
   async def debug_callback(pair):
       try:
           print(f"Update received: {pair.base_token.symbol}")
           # Your logic...
       except Exception as e:
           print(f"Callback error: {e}")
   ```

### 🔧 Connection Issues

**Problem**: Can't connect to Dexscreener API

**Solutions**:

```python
# Enable browser impersonation to bypass anti-bot protection
client = DexscreenerClient(impersonate="chrome136")

# Or enable debug mode to see detailed errors
client = DexscreenerClient(debug=True)
```

### 💾 Memory Usage

**Problem**: High memory usage after long-running sessions

**Solutions**:

- Periodically clean up unneeded subscriptions
- Use appropriate filters to reduce data processing
- Implement data rotation strategies

```python
# Example periodic cleanup
import asyncio
from datetime import datetime, timedelta

class ManagedClient:
    def __init__(self):
        self.client = DexscreenerClient()
        self.last_cleanup = datetime.now()

    async def periodic_cleanup(self):
        while True:
            await asyncio.sleep(3600)  # Check every hour
            if datetime.now() - self.last_cleanup > timedelta(hours=6):
                print("Performing periodic cleanup...")
                await self.client.close_streams()
                self.client = DexscreenerClient()  # Create fresh instance
                self.last_cleanup = datetime.now()
```

## 🆘 Getting Help

| Resource Type               | Link                                                                        | Use Case                         |
| --------------------------- | --------------------------------------------------------------------------- | -------------------------------- |
| **📖 Complete Examples**    | [Examples Page](examples.md)                                                | Need working code references     |
| **📋 API Reference**        | [Query API](api/query-api.md)                                               | Learn specific method usage      |
| **🐛 Bug Reports**          | [GitHub Issues](https://github.com/yourusername/dexscreen/issues)           | Found a bug or issue             |
| **💡 Feature Requests**     | [GitHub Discussions](https://github.com/yourusername/dexscreen/discussions) | Suggest new features             |
| **💬 Community Discussion** | [GitHub Discussions](https://github.com/yourusername/dexscreen/discussions) | General questions and discussion |

### 🔍 Best Practices When Seeking Help

1. **Provide complete error messages** and relevant code snippets
2. **Explain your use case** and expected behavior
3. **Include system information** (Python version, OS, etc.)
4. **Check existing issues** first to see if there's already a solution

> **💡 Tip**: Most issues can be resolved by checking the complete code in [Examples](examples.md)!

---

**🎉 Congratulations!** You now have the fundamentals of Dexscreen. Continue exploring [Examples](examples.md) to learn
more advanced usage, or start building your first DeFi monitoring application!
