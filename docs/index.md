# Dexscreen Documentation

Welcome to the Dexscreen documentation! This Python SDK provides a stable, reliable, and feature-rich interface for the
[Dexscreener.com](https://dexscreener.com/) API, enabling real-time DeFi data monitoring and analysis.

> **🎯 Quick Start**: New to Dexscreen? Start with our [Getting Started Guide](getting-started.md) for installation and
> your first queries.

## 🚀 Quick Navigation

| Section                                   | Description                                     | Best For                                 |
| ----------------------------------------- | ----------------------------------------------- | ---------------------------------------- |
| **[Getting Started](getting-started.md)** | Installation, setup, and your first queries     | New users, quick setup                   |
| **[Query API](api/query-api.md)**         | Single query methods for fetching data          | One-time data fetching, API reference    |
| **[Streaming API](api/streaming-api.md)** | Real-time subscription methods for live updates | Real-time monitoring, trading bots       |
| **[Data Models](api/data-models.md)**     | Complete reference for all data structures      | Understanding API responses              |
| **[Filtering](api/filtering.md)**         | Advanced filtering and configuration options    | Optimizing subscriptions, reducing noise |
| **[Examples](examples.md)**               | Complete working examples for common use cases  | Learning by example, production patterns |

## 📚 Documentation Structure

### 🎯 Getting Started

- **[Getting Started Guide](getting-started.md)** - Installation, basic setup, and your first queries
- **[Examples](examples.md)** - Complete, runnable examples for common use cases

> **💡 New User Path**: [Getting Started](getting-started.md) → [Examples](examples.md) → [Query API](api/query-api.md)
> → [Streaming API](api/streaming-api.md)

### 📖 API Reference

- **[Query API](api/query-api.md)** - Comprehensive guide to all query methods for one-time data fetching
- **[Streaming API](api/streaming-api.md)** - Real-time subscription methods for continuous updates
- **[Data Models](api/data-models.md)** - Complete reference for all data structures and types
- **[Filtering](api/filtering.md)** - Advanced filtering, rate limiting, and performance optimization

> **⚠️ Important**: Always check the [Data Models](api/data-models.md) reference when working with API responses.

## ⚡ Quick Start

### Installation

**Using uv (recommended):**

```bash
uv add dexscreen
```

**Using pip:**

```bash
pip install dexscreen
```

### Basic Usage Examples

**📊 Get Token Price:**

```python
from dexscreen import DexscreenerClient

client = DexscreenerClient()

# Get all USDC pairs on Ethereum
pairs = client.get_pairs_by_token_address(
    "ethereum",
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
)

if pairs:
    # Find the most liquid pair
    best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)
    print(f"USDC Price: ${best_pair.price_usd:.4f}")
    print(f"24h Volume: ${best_pair.volume.h24:,.0f}")
```

**🔄 Real-time Monitoring:**

```python
import asyncio
from dexscreen import DexscreenerClient, FilterPresets

async def price_alert(pair):
    print(f"{pair.base_token.symbol}: ${pair.price_usd:.4f}")

async def main():
    client = DexscreenerClient()

    # Monitor USDC/WETH pair for price changes > 0.1%
    await client.subscribe_pairs(
        chain_id="ethereum",
        pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
        callback=price_alert,
        filter=FilterPresets.significant_price_changes(0.001)  # 0.1%
    )

    await asyncio.sleep(60)  # Monitor for 1 minute
    await client.close_streams()

asyncio.run(main())
```

> **📖 Learn More**: See [Examples](examples.md) for complete, production-ready code examples.
>
> **🔍 Need Help?** Check our [troubleshooting section](#need-help) below or browse the [Examples](examples.md) for
> common patterns.

## 📊 API Quick Reference

### 🔍 Query Methods ([Full Reference](api/query-api.md))

| Method                                                | Description                         | Rate Limit | Use Case           |
| ----------------------------------------------------- | ----------------------------------- | ---------- | ------------------ |
| `get_pair(address)`                                   | Get pair by address (any chain)     | 300/min    | Quick price check  |
| `get_pair_by_pair_address(chain_id, pair_address)`    | Get specific pair on specific chain | 300/min    | Detailed pair info |
| `get_pairs_by_token_address(chain_id, token_address)` | Get all pairs for a token           | 300/min    | Token analysis     |
| `search_pairs(query)`                                 | Search pairs by name/symbol/address | 300/min    | Token discovery    |
| `get_latest_token_profiles()`                         | Latest token profiles               | 60/min     | New token tracking |
| `get_latest_boosted_tokens()`                         | Latest boosted tokens               | 60/min     | Promoted tokens    |

### 📡 Streaming Methods ([Full Reference](api/streaming-api.md))

| Method                                                  | Description                 | Best For              |
| ------------------------------------------------------- | --------------------------- | --------------------- |
| `subscribe_pairs(chain_id, pair_addresses, callback)`   | Monitor specific pairs      | Price alerts, trading |
| `subscribe_tokens(chain_id, token_addresses, callback)` | Monitor all pairs of tokens | Token monitoring      |
| `unsubscribe_pairs(chain_id, pair_addresses)`           | Stop monitoring pairs       | Dynamic management    |
| `unsubscribe_tokens(chain_id, token_addresses)`         | Stop monitoring tokens      | Dynamic management    |
| `get_active_subscriptions()`                            | List active subscriptions   | Debugging, monitoring |
| `close_streams()`                                       | Clean up all connections    | Cleanup, shutdown     |

> **⚠️ Rate Limits**: The SDK automatically handles rate limiting with intelligent retry logic.

## 🔑 Key Features

### ✨ Core Functionality

- **🌐 Complete API Coverage** - All Dexscreener endpoints with full feature parity
- **⚡ Real-time Updates** - HTTP-based streaming with configurable polling intervals
- **🎯 Smart Filtering** - Client-side filtering with customizable thresholds to reduce noise
- **🔗 Multi-chain Support** - Monitor multiple blockchains simultaneously with independent configurations

### 🛡️ Reliability & Performance

- **🚦 Automatic Rate Limiting** - Intelligent retry logic with exponential backoff
- **🕵️ Browser Impersonation** - Advanced anti-bot bypass using curl_cffi
- **🔒 Type Safety** - Full Pydantic model validation with comprehensive error handling
- **📊 Batch Operations** - Efficient batch processing for multiple queries

### 🎨 Developer Experience

- **🐍 Async/Sync Support** - Both synchronous and asynchronous APIs
- **📝 Rich Documentation** - Comprehensive guides with practical examples
- **🔧 Flexible Configuration** - Customizable filters, intervals, and callbacks
- **🐛 Debug-Friendly** - Detailed logging and error messages

## 🛠️ Common Use Cases

### 💰 Trading & DeFi

**📈 Price Monitoring** - [Complete Example](examples.md#price-monitoring)

```python
# Track significant price movements (1% threshold)
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=price_alert,
    filter=FilterPresets.significant_price_changes(0.01)
)
```

**🔄 Arbitrage Detection** - [Complete Example](examples.md#arbitrage-detection)

```python
# Monitor USDC across multiple chains for price differences
chains = ["ethereum", "polygon", "arbitrum"]
for chain in chains:
    await client.subscribe_pairs(chain, usdc_pairs[chain], arbitrage_callback)
```

### 📊 Analytics & Research

**🔍 New Token Discovery** - [Complete Example](examples.md#new-token-discovery)

```python
# Monitor all pairs of a token for new DEX listings
await client.subscribe_tokens(
    chain_id="solana",
    token_addresses=["JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"],
    callback=new_pair_callback
)
```

**📈 Portfolio Tracking** - [Complete Example](examples.md#portfolio-tracking)

```python
# Track multiple assets with custom filters per chain
for chain_id, config in portfolio_config.items():
    await client.subscribe_pairs(
        chain_id=chain_id,
        pair_addresses=config['pairs'],
        callback=portfolio_callback,
        filter=config['filter']
    )
```

### 🚨 Monitoring & Alerts

**⚠️ Volume Surge Detection** - [Complete Example](examples.md#volume-analysis)

```python
# Detect unusual trading activity
volume_config = FilterConfig(
    change_fields=["volume.m5", "volume.h1"],
    volume_change_threshold=0.50  # 50% volume increase
)
```

**💧 Liquidity Monitoring** - [Complete Example](examples.md#liquidity-monitoring)

```python
# Track liquidity additions/removals
liquidity_config = FilterConfig(
    change_fields=["liquidity.usd"],
    liquidity_change_threshold=0.10  # 10% liquidity change
)
```

> **🔗 More Examples**: Visit the [Examples page](examples.md) for complete, production-ready implementations.
>
> **📊 Performance Tips**: See our [performance optimization](#best-practices) section and
> [filtering guide](api/filtering.md) for best practices.

## Best Practices

### ⚡ Performance Optimization

1. **🎯 Use Appropriate Intervals**

   ```python
   # High-frequency trading: 0.2s
   interval=0.2

   # Portfolio monitoring: 5-10s
   interval=5.0

   # Long-term alerts: 30-60s
   interval=30.0
   ```

2. **🔍 Apply Smart Filtering** - [Learn more](api/filtering.md)

   ```python
   # Only significant changes
   filter=FilterPresets.significant_price_changes(0.01)

   # Rate-limited updates
   filter=FilterPresets.rate_limited(1.0)  # Max 1/second
   ```

### 🛡️ Error Handling & Resource Management

1. **🚨 Handle Errors Gracefully**

   ```python
   async def safe_callback(pair):
       try:
           await process_update(pair)
       except Exception as e:
           logger.error(f"Callback error: {e}")
           # Don't let errors crash subscriptions
   ```

2. **🧹 Clean Up Resources**

   ```python
   try:
       await client.subscribe_pairs(...)
       await asyncio.sleep(300)  # Run for 5 minutes
   finally:
       await client.close_streams()  # Always cleanup
   ```

# Check active subscriptions

```python
active = client.get_active_subscriptions()
print(f"Active subscriptions: {len(active)}")
```

### 🎯 Development Guidelines

- **Rate Limits**: SDK handles automatically, but monitor your usage
- **Type Safety**: Use type hints for better IDE support
- **Testing**: Use small intervals and short durations during development
- **Logging**: Enable debug logging for troubleshooting

> **📖 Deep Dive**: Read the [Getting Started Guide](getting-started.md) for detailed setup instructions.

## 🔗 External Resources

### 📚 Documentation & Code

- **[📖 Complete API Documentation](api/query-api.md)** - Detailed method reference
- **[🎯 Getting Started Tutorial](getting-started.md)** - Step-by-step setup guide
- **[💡 Practical Examples](examples.md)** - Production-ready code samples
- **[GitHub Repository](https://github.com/yourusername/dexscreen)** - Source code and issues

### 🌐 Related Services

- **[Dexscreener.com](https://dexscreener.com/)** - Official Dexscreener platform
- **[Dexscreener API Docs](https://docs.dexscreener.com/)** - Upstream API documentation
- **[PyPI Package](https://pypi.org/project/dexscreen/)** - Official package repository

---

## Need Help?

| Issue Type           | Resource                                                                    |
| -------------------- | --------------------------------------------------------------------------- |
| **Getting Started**  | [Getting Started Guide](getting-started.md)                                 |
| **API Questions**    | [Query API](api/query-api.md) or [Streaming API](api/streaming-api.md)      |
| **Code Examples**    | [Examples Page](examples.md)                                                |
| **Bug Reports**      | [GitHub Issues](https://github.com/yourusername/dexscreen/issues)           |
| **Feature Requests** | [GitHub Discussions](https://github.com/yourusername/dexscreen/discussions) |

---

## 📄 License

**MIT License** - See [LICENSE](https://github.com/yourusername/dexscreen/blob/main/LICENSE) file for complete terms and conditions.

> **🙏 Contributing**: We welcome contributions! Please read our contributing guidelines in the GitHub repository.
