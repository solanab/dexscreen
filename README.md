# Dexscreen

A stable and reliable Python SDK for [Dexscreener.com](https://dexscreener.com/) API with HTTP support:

- **Single Query** - Traditional one-time API calls
- **Real-time Updates** - Live price updates with configurable intervals

[![Downloads](https://pepy.tech/badge/dexscreen)](https://pepy.tech/project/dexscreen)
[![PyPI version](https://badge.fury.io/py/dexscreen.svg)](https://badge.fury.io/py/dexscreen)
[![Python Version](https://img.shields.io/pypi/pyversions/dexscreen)](https://pypi.org/project/dexscreen/)

## Features

- ✅ Complete official API coverage
- ✅ Stable HTTP-based streaming
- ✅ Automatic rate limiting
- ✅ Browser impersonation for anti-bot bypass (using curl_cffi)
- ✅ Type-safe with Pydantic models
- ✅ Async/sync support
- ✅ Simple, focused interface

## Installation

use uv (Recommended)

```bash
uv add dexscreen
```

or pip

```bash
pip install dexscreen
```

## Quick Start

### Mode 1: Single Query (Traditional API calls)

```python
from dexscreen import DexscreenerClient

# Default client with 10-second timeout
client = DexscreenerClient()

# Custom timeout client
client = DexscreenerClient(client_kwargs={"timeout": 30})

# Get a specific pair by token address
pairs = client.get_pairs_by_token_address("solana", "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
if pairs:
    pair = pairs[0]  # Get the first pair
    print(f"{pair.base_token.symbol}: ${pair.price_usd}")

# Search for tokens
results = client.search_pairs("PEPE")
for pair in results[:5]:
    print(f"{pair.base_token.symbol} on {pair.chain_id}: ${pair.price_usd}")

# Get token information
profiles = client.get_latest_token_profiles()
boosted = client.get_latest_boosted_tokens()
```

### Mode 2: Real-time Updates

```python
import asyncio
from dexscreen import DexscreenerClient

async def handle_price_update(pair):
    print(f"{pair.base_token.symbol}: ${pair.price_usd} ({pair.price_change.h24:+.2f}%)")

async def main():
    client = DexscreenerClient()

    # Subscribe to pair updates (default interval: 0.2 seconds)
    await client.subscribe_pairs(
        chain_id="solana",
        pair_addresses=["JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"],
        callback=handle_price_update,
        interval=0.2  # Poll 5 times per second (300/min)
    )

    # Let it run for 30 seconds
    await asyncio.sleep(30)
    await client.close_streams()

asyncio.run(main())
```

### Filtering Options

```python
from dexscreen import DexscreenerClient, FilterPresets

# Default filtering - only receive updates when data changes
await client.subscribe_pairs(
    chain_id="solana",
    pair_addresses=["JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"],
    callback=handle_price_update,
    filter=True,  # Default value
    interval=0.2
)

# No filtering - receive all polling results
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"],
    callback=handle_price_update,
    filter=False,  # Get all updates even if data hasn't changed
    interval=1.0
)

# Advanced filtering - only significant price changes (1%)
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"],
    callback=handle_price_update,
    filter=FilterPresets.significant_price_changes(0.01)
)

# Rate limited updates - max 1 update per second
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"],
    callback=handle_price_update,
    filter=FilterPresets.rate_limited(1.0)
)
```

## Advanced Usage

### Price Monitoring for Arbitrage

```python
from dexscreen import DexscreenerClient

async def monitor_arbitrage():
    client = DexscreenerClient()

    # Monitor same token on different chains
    pairs = [
        ("ethereum", "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"),  # USDC/WETH
        ("bsc", "0x7213a321F1855CF1779f42c0CD85d3D95291D34C"),      # USDC/BUSD
        ("polygon", "0x45dDa9cb7c25131DF268515131f647d726f50608"),  # USDC/WETH
    ]

    prices = {}

    async def track_price(pair):
        key = f"{pair.chain_id}:{pair.base_token.symbol}"
        prices[key] = float(pair.price_usd)

        # Check for arbitrage opportunity
        if len(prices) > 1:
            min_price = min(prices.values())
            max_price = max(prices.values())
            spread = ((max_price - min_price) / min_price) * 100

            if spread > 0.5:  # 0.5% spread
                print(f"ARBITRAGE: {spread:.2f}% spread detected!")

    # Subscribe to all pairs
    for chain, address in pairs:
        await client.subscribe_pairs(
            chain_id=chain,
            pair_addresses=[address],
            callback=track_price,
            interval=0.5
        )

    await asyncio.sleep(60)  # Monitor for 1 minute
```

### High-Volume Pairs Discovery

```python
async def find_trending_tokens():
    client = DexscreenerClient()

    # Search for tokens
    results = await client.search_pairs_async("SOL")

    # Filter high volume pairs (>$1M daily volume)
    high_volume = [
        p for p in results
        if p.volume.h24 and p.volume.h24 > 1_000_000
    ]

    # Sort by volume
    high_volume.sort(key=lambda x: x.volume.h24, reverse=True)

    # Monitor top 5
    for pair in high_volume[:5]:
        print(f"{pair.base_token.symbol}: Vol ${pair.volume.h24/1e6:.2f}M")

        await client.subscribe_pairs(
            chain_id=pair.chain_id,
            pair_addresses=[pair.pair_address],
            callback=handle_price_update,
            interval=2.0
        )
```

## Documentation

📖 **[Full Documentation](docs/index.md)** - Complete API reference, guides, and examples.

### Quick API Overview

#### Main Client

```python
client = DexscreenerClient(impersonate="chrome136")
```

#### Key Methods

- `get_pairs_by_token_address(chain_id, token_address)` - Get pairs for a token
- `search_pairs(query)` - Search pairs
- `subscribe_pairs(chain_id, pair_addresses, callback)` - Real-time pair updates
- `subscribe_tokens(chain_id, token_addresses, callback)` - Monitor all pairs of tokens

#### Data Models

- `TokenPair` - Main pair data model
- `TokenInfo` - Token profile information
- `OrderInfo` - Order information

## Rate Limits

The SDK automatically handles rate limiting:

- 60 requests/minute for token profile endpoints
- 300 requests/minute for pair data endpoints

## Timeout Configuration

The SDK provides flexible timeout configuration for different use cases:

### Default Timeout
```python
# Default timeout is 10 seconds
client = DexscreenerClient()
```

### Custom Timeout
```python
# Set custom timeout during initialization
client = DexscreenerClient(client_kwargs={"timeout": 30})

# Different timeouts for different scenarios
fast_client = DexscreenerClient(client_kwargs={"timeout": 5})    # Quick responses
stable_client = DexscreenerClient(client_kwargs={"timeout": 60}) # Stable connections
```

### Runtime Timeout Updates
```python
# Update timeout at runtime
await client._client_300rpm.update_config({"timeout": 15})

# Multiple config updates including timeout
await client._client_300rpm.update_config({
    "timeout": 25,
    "impersonate": "chrome136"
})
```

### Recommended Timeout Values

| Use Case | Timeout (seconds) | Description |
|----------|------------------|-------------|
| Quick Trading | 5-10 | Fast response for time-sensitive operations |
| General Use | 10-15 | Default balanced setting |
| Stable Monitoring | 20-30 | Reliable for long-running subscriptions |
| Poor Networks | 30-60 | Handle unstable connections |

## Browser Impersonation

The SDK uses curl_cffi for browser impersonation to bypass anti-bot protection:

```python
# Use different browser versions
client = DexscreenerClient(impersonate="chrome134")
client = DexscreenerClient(impersonate="safari180")

# Combine browser impersonation with custom timeout
client = DexscreenerClient(
    impersonate="chrome136", 
    client_kwargs={"timeout": 20}
)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details
