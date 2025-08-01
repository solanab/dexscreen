# Query API Reference

The Query API provides synchronous and asynchronous methods for fetching data from Dexscreener. All methods have both
sync and async versions.

## Overview

Query methods are one-time data fetches that return immediately with the current data. They are ideal for:

- Getting current prices
- Searching for tokens
- Fetching pair information
- Retrieving token profiles

## Rate Limits

- **Pair queries**: 300 requests/minute
- **Token profiles/orders**: 60 requests/minute

The SDK automatically handles rate limiting with retry logic.

## Pair Queries

### get_pair / get_pair_async

```python
def get_pair(address: str) -> Optional[TokenPair]
async def get_pair_async(address: str) -> Optional[TokenPair]
```

Get information for a single trading pair (implemented via search, no need to specify chain).

**Example:**

```python
# Sync
pair = client.get_pair("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
if pair:
    print(f"{pair.base_token.symbol}: ${pair.price_usd}")

# Async
pair = await client.get_pair_async("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
```

### get_pair_by_pair_address / get_pair_by_pair_address_async

```python
def get_pair_by_pair_address(chain_id: str, pair_address: str) -> Optional[TokenPair]
async def get_pair_by_pair_address_async(chain_id: str, pair_address: str) -> Optional[TokenPair]
```

Get trading pair information on a specified blockchain.

**Parameters:**

- `chain_id`: Blockchain identifier (e.g., "ethereum", "solana", "bsc")
- `pair_address`: The pair contract address

**Example:**

```python
pair = client.get_pair_by_pair_address(
    "ethereum",
    "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # USDC/WETH
)
```

### get_pairs_by_pairs_addresses / get_pairs_by_pairs_addresses_async

```python
def get_pairs_by_pairs_addresses(chain_id: str, pair_addresses: List[str]) -> List[TokenPair]
async def get_pairs_by_pairs_addresses_async(chain_id: str, pair_addresses: List[str]) -> List[TokenPair]
```

Batch fetch trading pair information (same chain). Supports up to 30 addresses, exceeding this will raise ValueError.

**Example:**

```python
pairs = client.get_pairs_by_pairs_addresses(
    "ethereum",
    [
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        "0x11b815efb8f581194ae79006d24e0d814b7697f6",
        "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36"
    ]
)
```

### search_pairs / search_pairs_async

```python
def search_pairs(query: str) -> List[TokenPair]
async def search_pairs_async(query: str) -> List[TokenPair]
```

Search for trading pairs (by name, symbol, or address).

**Example:**

```python
# Search by symbol
results = client.search_pairs("PEPE")

# Search by name
results = client.search_pairs("Shiba Inu")

# Search by address
results = client.search_pairs("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
```

### get_pairs_by_token_address / get_pairs_by_token_address_async

```python
def get_pairs_by_token_address(chain_id: str, token_address: str) -> List[TokenPair]
async def get_pairs_by_token_address_async(chain_id: str, token_address: str) -> List[TokenPair]
```

Get all trading pairs for a single token on a specified chain. Returns all trading pairs for that token across all DEXs
on that chain.

**Example:**

```python
# Get all USDC pairs on Ethereum
usdc_pairs = client.get_pairs_by_token_address(
    "ethereum",
    "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
)

for pair in usdc_pairs:
    other_token = pair.quote_token if pair.base_token.address.lower() == usdc_address.lower() else pair.base_token
    print(f"USDC/{other_token.symbol} on {pair.dex_id}: ${pair.price_usd}")
```

### get_pairs_by_token_addresses / get_pairs_by_token_addresses_async

```python
def get_pairs_by_token_addresses(chain_id: str, token_addresses: List[str]) -> List[TokenPair]
async def get_pairs_by_token_addresses_async(chain_id: str, token_addresses: List[str]) -> List[TokenPair]
```

Batch fetch all trading pairs for multiple tokens on a specified chain. Returns all trading pairs containing any of the
specified tokens (deduplicated).

**Important Notes**:

- Chain ID must be specified (e.g., "solana", "ethereum", etc.)
- Supports up to 30 token addresses max, exceeding this will raise ValueError
- API returns maximum 30 trading pairs (most relevant/active)
- Returns a collection of all trading pairs containing any of these tokens. If a trading pair contains multiple
  specified tokens (e.g., USDC/SOL pair contains both USDC and SOL), it will only appear once

**Example:**

```python
# Get pairs for multiple tokens
token_addresses = [
    "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "dac17f958d2ee523a2206206994597c13d831ec7",  # USDT
    "6B175474E89094C44Da98b954EedeAC495271d0F"   # DAI
]

stablecoin_pairs = client.get_pairs_by_token_addresses("ethereum", token_addresses)
```

## Token Information Queries

### get_latest_token_profiles / get_latest_token_profiles_async

```python
def get_latest_token_profiles() -> List[TokenInfo]
async def get_latest_token_profiles_async() -> List[TokenInfo]
```

Get latest token profiles. Rate limit: 60 requests/minute.

**Example:**

```python
profiles = client.get_latest_token_profiles()
for token in profiles[:10]:
    print(f"{token.token_address}: {token.description}")
```

### get_latest_boosted_tokens / get_latest_boosted_tokens_async

```python
def get_latest_boosted_tokens() -> List[TokenInfo]
async def get_latest_boosted_tokens_async() -> List[TokenInfo]
```

Get latest boosted tokens. Rate limit: 60 requests/minute.

**Example:**

```python
boosted = client.get_latest_boosted_tokens()
for token in boosted:
    print(f"{token.chain_id}: {token.token_address} - Boost: {token.amount}")
```

### get_tokens_most_active / get_tokens_most_active_async

```python
def get_tokens_most_active() -> List[TokenInfo]
async def get_tokens_most_active_async() -> List[TokenInfo]
```

Get most active boosted tokens. Rate limit: 60 requests/minute.

## Pool Information Queries

### get_pools_by_token_address / get_pools_by_token_address_async

```python
def get_pools_by_token_address(chain_id: str, token_address: str) -> List[TokenPair]
async def get_pools_by_token_address_async(chain_id: str, token_address: str) -> List[TokenPair]
```

Get pool information using the token-pairs/v1 endpoint. Similar to get_pairs_by_pairs_addresses but uses a different API
endpoint. Rate limit: 300 requests/minute.

## Order Queries

### get_orders_paid_of_token / get_orders_paid_of_token_async

```python
def get_orders_paid_of_token(chain_id: str, token_address: str) -> List[OrderInfo]
async def get_orders_paid_of_token_async(chain_id: str, token_address: str) -> List[OrderInfo]
```

Get paid orders for a token. Rate limit: 60 requests/minute.

**Example:**

```python
orders = client.get_orders_paid_of_token("ethereum", token_address)
for order in orders:
    print(f"Order {order.type}: {order.status} at {order.payment_timestamp}")
```

## Best Practices

### 1. Use Async for Multiple Queries

When fetching data for multiple tokens/pairs, use async methods:

```python
import asyncio

async def fetch_multiple_tokens():
    client = DexscreenerClient()

    tokens = ["address1", "address2", "address3"]

    # Concurrent fetching
    tasks = [
        client.get_pairs_by_token_address_async("ethereum", addr)
        for addr in tokens
    ]

    results = await asyncio.gather(*tasks)
    return results
```

### 2. Handle Rate Limits

The SDK handles rate limits automatically, but you can also be proactive:

```python
# Space out requests for token profiles (60/min limit)
import time

for token_address in large_token_list:
    orders = client.get_orders_paid_of_token("ethereum", token_address)
    process_orders(orders)
    time.sleep(1.1)  # ~54 requests per minute to be safe
```

### 3. Error Handling

Always handle potential None returns:

```python
pair = client.get_pair_by_pair_address("ethereum", pair_address)
if pair:
    # Process pair data
    print(f"Price: ${pair.price_usd}")
else:
    print(f"Pair {pair_address} not found")
```

### 4. Batch Operations

For multiple addresses on the same chain, use batch methods:

```python
# Instead of this:
pairs = []
for address in addresses:
    pair = client.get_pair_by_pair_address("ethereum", address)
    if pair:
        pairs.append(pair)

# Do this:
pairs = client.get_pairs_by_pairs_addresses("ethereum", addresses)
```

## Common Patterns

### Finding Arbitrage Opportunities

```python
async def find_arbitrage(token_address: str):
    client = DexscreenerClient()

    # Get pairs across multiple chains
    chains = ["ethereum", "bsc", "polygon", "arbitrum"]

    tasks = [
        client.get_pairs_by_token_address_async(chain, token_address)
        for chain in chains
    ]

    all_pairs = await asyncio.gather(*tasks)

    # Flatten and analyze
    prices_by_chain = {}
    for chain, pairs in zip(chains, all_pairs):
        if pairs:
            # Get the most liquid pair
            best_pair = max(pairs, key=lambda p: p.liquidity.usd or 0)
            prices_by_chain[chain] = best_pair.price_usd

    # Find arbitrage
    if len(prices_by_chain) > 1:
        min_price = min(prices_by_chain.values())
        max_price = max(prices_by_chain.values())
        spread = ((max_price - min_price) / min_price) * 100

        if spread > 1:  # 1% threshold
            print(f"Arbitrage opportunity: {spread:.2f}% spread")
            return prices_by_chain
```

### Token Discovery

```python
def discover_new_tokens():
    client = DexscreenerClient()

    # Get latest profiles
    profiles = client.get_latest_token_profiles()

    # Filter interesting tokens
    interesting = []
    for token in profiles:
        # Get trading data
        pairs = client.get_pairs_by_token_address(token.chain_id, token.token_address)

        if pairs:
            total_volume = sum(p.volume.h24 for p in pairs if p.volume.h24)
            total_liquidity = sum(p.liquidity.usd for p in pairs if p.liquidity and p.liquidity.usd)

            if total_volume > 100_000 and total_liquidity > 50_000:
                interesting.append({
                    'token': token,
                    'pairs': pairs,
                    'volume': total_volume,
                    'liquidity': total_liquidity
                })

    return interesting
```
