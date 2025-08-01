# 查询 API 参考

查询 API 提供同步和异步方法从 Dexscreener 获取数据。所有方法都有同步和异步版本。

## 概述

查询方法是一次性数据获取，立即返回当前数据。它们适用于：

- 获取当前价格
- 搜索代币
- 获取交易对信息
- 检索代币档案

## 速率限制

- **交易对查询**：300 请求/分钟
- **代币档案/订单**：60 请求/分钟

SDK 自动处理速率限制和重试逻辑。

## 交易对查询 (Pair Queries)

### get_pair / get_pair_async

```python
def get_pair(address: str) -> Optional[TokenPair]
async def get_pair_async(address: str) -> Optional[TokenPair]
```

获取单个交易对信息（通过搜索实现，无需指定链）。

**示例：**

```python
# 同步
pair = client.get_pair("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
if pair:
    print(f"{pair.base_token.symbol}: ${pair.price_usd}")

# 异步
pair = await client.get_pair_async("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
```

### get_pair_by_pair_address / get_pair_by_pair_address_async

```python
def get_pair_by_pair_address(chain_id: str, pair_address: str) -> Optional[TokenPair]
async def get_pair_by_pair_address_async(chain_id: str, pair_address: str) -> Optional[TokenPair]
```

获取指定链上的交易对信息。

**参数：**

- `chain_id`：区块链标识符（如 "ethereum"、"solana"、"bsc"）
- `pair_address`：交易对合约地址

**示例：**

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

批量获取交易对信息（同一链）。最多支持 30 个地址，超过将抛出 ValueError。

**示例：**

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

搜索交易对（按名称、符号或地址）。

**示例：**

```python
# 按符号搜索
results = client.search_pairs("PEPE")

# 按名称搜索
results = client.search_pairs("Shiba Inu")

# 按地址搜索
results = client.search_pairs("0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640")
```

### get_pairs_by_token_address / get_pairs_by_token_address_async

```python
def get_pairs_by_token_address(chain_id: str, token_address: str) -> List[TokenPair]
async def get_pairs_by_token_address_async(chain_id: str, token_address: str) -> List[TokenPair]
```

获取指定链上单个代币的所有交易对。返回该代币在该链所有 DEX 上的所有交易对。

**示例：**

```python
# 获取以太坊上的所有 USDC 交易对
usdc_pairs = client.get_pairs_by_token_address(
    "ethereum",
    "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
)

for pair in usdc_pairs:
    other_token = pair.quote_token if pair.base_token.address.lower() == usdc_address.lower() else pair.base_token
    print(f"USDC/{other_token.symbol} 在 {pair.dex_id}: ${pair.price_usd}")
```

### get_pairs_by_token_addresses / get_pairs_by_token_addresses_async

```python
def get_pairs_by_token_addresses(chain_id: str, token_addresses: List[str]) -> List[TokenPair]
async def get_pairs_by_token_addresses_async(chain_id: str, token_addresses: List[str]) -> List[TokenPair]
```

批量获取指定链上多个代币的所有交易对。返回所有包含任意指定代币的交易对（去重）。

**注意**：

- 需要指定链 ID（如 "solana"、"ethereum" 等）
- 最多支持 30 个代币地址，超过将抛出 ValueError
- API 最多返回 30 个交易对（最相关/活跃的）
- 返回的是所有包含这些代币的交易对集合，如果一个交易对包含多个指定的代币（如 USDC/SOL 对同时包含 USDC 和 SOL），它只会出现一次

**示例：**

```python
# 获取多个代币的交易对
token_addresses = [
    "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "dac17f958d2ee523a2206206994597c13d831ec7",  # USDT
    "6B175474E89094C44Da98b954EedeAC495271d0F"   # DAI
]

stablecoin_pairs = client.get_pairs_by_token_addresses("ethereum", token_addresses)
```

## 代币信息查询 (Token Information)

### get_latest_token_profiles / get_latest_token_profiles_async

```python
def get_latest_token_profiles() -> List[TokenInfo]
async def get_latest_token_profiles_async() -> List[TokenInfo]
```

获取最新代币档案。速率限制：60请求/分钟。

**示例：**

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

获取最新推广代币。速率限制：60请求/分钟。

**示例：**

```python
boosted = client.get_latest_boosted_tokens()
for token in boosted:
    print(f"{token.chain_id}: {token.token_address} - 推广: {token.amount}")
```

### get_tokens_most_active / get_tokens_most_active_async

```python
def get_tokens_most_active() -> List[TokenInfo]
async def get_tokens_most_active_async() -> List[TokenInfo]
```

获取最活跃推广代币。速率限制：60请求/分钟。

## 池信息查询 (Pool Information)

### get_pools_by_token_address / get_pools_by_token_address_async

```python
def get_pools_by_token_address(chain_id: str, token_address: str) -> List[TokenPair]
async def get_pools_by_token_address_async(chain_id: str, token_address: str) -> List[TokenPair]
```

使用 token-pairs/v1 端点获取池信息。与 get_pairs_by_pairs_addresses 类似，但使用不同的 API 端点。速率限制：300请求/分钟。

## 订单查询 (Order Queries)

### get_orders_paid_of_token / get_orders_paid_of_token_async

```python
def get_orders_paid_of_token(chain_id: str, token_address: str) -> List[OrderInfo]
async def get_orders_paid_of_token_async(chain_id: str, token_address: str) -> List[OrderInfo]
```

获取代币付费订单。速率限制：60请求/分钟。

**示例：**

```python
orders = client.get_orders_paid_of_token("ethereum", token_address)
for order in orders:
    print(f"订单 {order.type}: {order.status} 于 {order.payment_timestamp}")
```

## 最佳实践

### 1. 多查询使用异步

获取多个代币/交易对数据时，使用异步方法：

```python
import asyncio

async def fetch_multiple_tokens():
    client = DexscreenerClient()

    tokens = ["address1", "address2", "address3"]

    # 并发获取
    tasks = [
        client.get_pairs_by_token_address_async("ethereum", addr)
        for addr in tokens
    ]

    results = await asyncio.gather(*tasks)
    return results
```

### 2. 处理速率限制

SDK 自动处理速率限制，但您也可以主动处理：

```python
# 为代币档案请求留出间隔（60/分钟限制）
import time

for token_address in large_token_list:
    orders = client.get_orders_paid_of_token("ethereum", token_address)
    process_orders(orders)
    time.sleep(1.1)  # 安全起见约 54 请求每分钟
```

### 3. 错误处理

始终处理潜在的 None 返回：

```python
pair = client.get_pair_by_pair_address("ethereum", pair_address)
if pair:
    # 处理交易对数据
    print(f"价格: ${pair.price_usd}")
else:
    print(f"未找到交易对 {pair_address}")
```

### 4. 批量操作

对于同一链上的多个地址，使用批量方法：

```python
# 不要这样做：
pairs = []
for address in addresses:
    pair = client.get_pair_by_pair_address("ethereum", address)
    if pair:
        pairs.append(pair)

# 应该这样做：
pairs = client.get_pairs_by_pairs_addresses("ethereum", addresses)
```

## 常见模式

### 寻找套利机会

```python
async def find_arbitrage(token_address: str):
    client = DexscreenerClient()

    # 获取多条链上的交易对
    chains = ["ethereum", "bsc", "polygon", "arbitrum"]

    tasks = [
        client.get_pairs_by_token_address_async(chain, token_address)
        for chain in chains
    ]

    all_pairs = await asyncio.gather(*tasks)

    # 扁平化并分析
    prices_by_chain = {}
    for chain, pairs in zip(chains, all_pairs):
        if pairs:
            # 获取流动性最高的交易对
            best_pair = max(pairs, key=lambda p: p.liquidity.usd or 0)
            prices_by_chain[chain] = best_pair.price_usd

    # 寻找套利机会
    if len(prices_by_chain) > 1:
        min_price = min(prices_by_chain.values())
        max_price = max(prices_by_chain.values())
        spread = ((max_price - min_price) / min_price) * 100

        if spread > 1:  # 1% 阈值
            print(f"套利机会: {spread:.2f}% 价差")
            return prices_by_chain
```

### 代币发现

```python
def discover_new_tokens():
    client = DexscreenerClient()

    # 获取最新档案
    profiles = client.get_latest_token_profiles()

    # 过滤有趣的代币
    interesting = []
    for token in profiles:
        # 获取交易数据
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

---
