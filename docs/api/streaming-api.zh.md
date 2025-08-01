# 流式 API 参考

流式 API 通过 HTTP 轮询提供实时数据更新，支持动态订阅管理、灵活过滤和多链监控。

## 概述

流式方法提供价格变化、交易量、流动性和其他指标的持续更新。它们适用于：

- 实时价格监控
- 套利检测
- 投资组合跟踪
- 新交易对发现
- 警报系统

## 核心功能

### 动态订阅管理

```python
# 1. 初始订阅
await client.subscribe_pairs("ethereum", ["0xaaa..."], callback)

# 2. 添加更多订阅（累积，不是替换）
await client.subscribe_pairs("ethereum", ["0xbbb...", "0xccc..."], callback)

# 3. 移除特定订阅
await client.unsubscribe_pairs("ethereum", ["0xaaa..."])

# 4. 查看活动订阅
active = client.get_active_subscriptions()
```

### 多链支持

```python
# 使用独立配置同时监控多条链
await client.subscribe_pairs("ethereum", eth_pairs, eth_callback, interval=1.0)
await client.subscribe_pairs("solana", sol_pairs, sol_callback, interval=0.2)
await client.subscribe_pairs("bsc", bsc_pairs, bsc_callback, interval=0.5)
```

## 主要方法

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

订阅实时交易对更新。支持动态添加 - 多次调用会累积订阅而不是替换。

**参数：**

- `chain_id`：区块链标识符（如 "ethereum"、"solana"）
- `pair_addresses`：交易对合约地址列表
- `callback`：每次更新时调用的函数，接收 TokenPair 对象
- `filter`：过滤配置：
  - `True`（默认）：仅在数据变化时触发
  - `False`：触发所有轮询结果
  - `FilterConfig` 对象：自定义过滤规则
- `interval`：轮询间隔（秒）（默认 0.2 秒）

**使用示例：**

```python
# 示例 1：实时价格监控
await client.subscribe_pairs(
    "ethereum",
    ["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],  # USDC/ETH
    price_monitor_callback,
    filter=FilterPresets.significant_price_changes(0.001),  # 0.1% 变化
    interval=0.5
)

# 示例 2：套利监控（多个 DEX）
dex_pairs = ["0xaaa...", "0xbbb...", "0xccc..."]  # 不同 DEX 上的同一代币
await client.subscribe_pairs(
    "ethereum",
    dex_pairs,
    arbitrage_callback,
    filter=False,  # 需要所有更新
    interval=0.2   # 最快速度
)

# 示例 3：投资组合跟踪
portfolio_config = FilterConfig(
    change_fields=["price_usd", "volume.h24"],
    price_change_threshold=0.02,  # 2% 变化阈值
    max_updates_per_second=0.5    # 每 2 秒最多 1 次更新
)
await client.subscribe_pairs(
    "ethereum",
    portfolio_pairs,
    portfolio_callback,
    filter=portfolio_config,
    interval=5.0  # 每 5 秒检查
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

订阅特定代币的所有交易对。自动发现新交易对 - 适合全面的代币监控。

**参数：**

- `chain_id`：区块链标识符
- `token_addresses`：代币合约地址列表
- `callback`：接收代币所有交易对列表的函数
- `filter`：过滤配置（与 subscribe_pairs 相同）
- `interval`：轮询间隔（秒）

**使用示例：**

```python
# 示例 1：监控新代币发布
await client.subscribe_tokens(
    "solana",
    ["NewTokenAddress..."],
    new_token_callback,
    filter=False,  # 获取所有更新以发现新交易对
    interval=0.5
)

# 示例 2：稳定币流动性监控
await client.subscribe_tokens(
    "ethereum",
    ["A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],  # USDC
    liquidity_callback,
    filter=FilterConfig(
        change_fields=["liquidity.usd"],
        liquidity_change_threshold=0.05  # 5% 流动性变化
    ),
    interval=2.0
)

# 示例 3：跨 DEX 价格比较
def compare_prices_callback(pairs: List[TokenPair]):
    # 按 DEX 分组并查找价格差异
    by_dex = {}
    for pair in pairs:
        if pair.dex_id not in by_dex:
            by_dex[pair.dex_id] = []
        by_dex[pair.dex_id].append(pair)
    # 分析价格差异...

await client.subscribe_tokens("bsc", ["TokenAddress..."], compare_prices_callback)
```

### unsubscribe_pairs

```python
async def unsubscribe_pairs(chain_id: str, pair_addresses: List[str]) -> None
```

移除特定交易对订阅。必须指定正确的 chain_id。

```python
# 移除单个订阅
await client.unsubscribe_pairs("ethereum", ["0xaaa..."])

# 批量移除
await client.unsubscribe_pairs("ethereum", ["0xaaa...", "0xbbb...", "0xccc..."])

# 注意：chain_id 必须匹配
# 这不会影响任何订阅（不同的 chain_id）
await client.unsubscribe_pairs("bsc", ["0xaaa..."])
```

### unsubscribe_tokens

```python
async def unsubscribe_tokens(chain_id: str, token_addresses: List[str]) -> None
```

移除特定代币的所有交易对订阅。

```python
# 停止监控 USDC
await client.unsubscribe_tokens(
    "ethereum",
    ["A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]
)
```

### close_streams

```python
async def close_streams() -> None
```

关闭所有订阅和流连接。通常在程序退出时调用。

```python
try:
    # 运行订阅...
    await client.subscribe_pairs(...)
finally:
    # 确保清理
    await client.close_streams()
```

## 管理方法

### get_active_subscriptions

```python
def get_active_subscriptions() -> List[Dict[str, Any]]
```

获取所有活动订阅的详细信息。

```python
# 查看所有订阅
active = client.get_active_subscriptions()
for sub in active:
    if sub["type"] == "pair":
        print(f"交易对: {sub['chain_id']}:{sub['pair_address']}")
    else:
        print(f"代币: {sub['chain_id']}:{sub['token_address']}")

# 返回格式示例
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

## 高级用法

### 完整订阅生命周期管理

```python
class PortfolioManager:
    def __init__(self):
        self.client = DexscreenerClient()
        self.active_pairs = set()

    async def add_pair(self, chain_id: str, pair_address: str):
        """动态添加交易对到投资组合"""
        if (chain_id, pair_address) not in self.active_pairs:
            await self.client.subscribe_pairs(
                chain_id,
                [pair_address],
                self.handle_update,
                filter=FilterPresets.monitoring()
            )
            self.active_pairs.add((chain_id, pair_address))

    async def remove_pair(self, chain_id: str, pair_address: str):
        """从投资组合移除交易对"""
        if (chain_id, pair_address) in self.active_pairs:
            await self.client.unsubscribe_pairs(chain_id, [pair_address])
            self.active_pairs.remove((chain_id, pair_address))

    def handle_update(self, pair: TokenPair):
        """处理价格更新"""
        # 实现您的逻辑
        pass

# 使用示例
manager = PortfolioManager()

# 动态管理
await manager.add_pair("ethereum", "0xaaa...")
await manager.add_pair("ethereum", "0xbbb...")
await manager.remove_pair("ethereum", "0xaaa...")
```

### 多策略并行监控

```python
# 为不同目的创建不同的监控策略
client = DexscreenerClient()

# 策略 1：高频交易监控
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

# 策略 2：流动性提供者监控
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

# 策略 3：价格警报
alert_config = FilterConfig(
    price_change_threshold=0.05  # 5% 变化触发警报
)
await client.subscribe_pairs(
    "bsc",
    alert_pairs,
    send_price_alert,
    filter=alert_config,
    interval=10.0
)
```

## 回调最佳实践

### 错误处理

始终在 try-except 中包装回调逻辑：

```python
async def safe_callback(pair: TokenPair):
    try:
        # 您的逻辑
        if pair.price_usd > threshold:
            await send_alert(pair)
    except Exception as e:
        logger.error(f"回调错误: {e}")
        # 不要让错误导致订阅崩溃
```

### 异步回调

回调可以是同步或异步的：

```python
# 同步回调
def sync_handler(pair: TokenPair):
    print(f"价格: ${pair.price_usd}")

# 异步回调
async def async_handler(pair: TokenPair):
    await database.save_price(pair)
    await check_trading_conditions(pair)

# 两者都可以与 subscribe_pairs 一起使用
await client.subscribe_pairs("ethereum", addresses, sync_handler)
await client.subscribe_pairs("ethereum", addresses, async_handler)
```

### 状态管理

使用闭包或类来处理有状态的回调：

```python
# 使用闭包
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

# 使用类
class TradingStrategy:
    def __init__(self):
        self.positions = {}
        self.alerts = []

    async def process_update(self, pair: TokenPair):
        # 复杂的有状态逻辑
        if self.should_buy(pair):
            await self.execute_buy(pair)
```

## 性能优化

### 1. 订阅限制

- 每条链最多 30 个交易对订阅
- 超过限制将记录警告并忽略额外订阅
- 使用 `subscribe_tokens` 监控代币的所有交易对（无限制）

### 2. 轮询优化

- 同一链上的多个订阅会自动批处理
- 轮询间隔是该链上所有订阅的最小值
- 过滤器独立应用于每个订阅

### 3. 最佳实践

- 订阅前检查 `get_active_subscriptions()` 避免重复
- 使用适当的过滤减少不必要的回调
- 程序退出时始终调用 `close_streams()`
- 平衡轮询间隔与实时需求

## 常见模式

### 价格警报系统

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

### 交易量激增检测

```python
async def detect_volume_surges():
    client = DexscreenerClient()

    # 跟踪交易量历史
    volume_history = defaultdict(list)

    def volume_callback(pair: TokenPair):
        history = volume_history[pair.pair_address]
        history.append(pair.volume.m5 or 0)

        # 保留最后 12 个周期（5 分钟数据的 1 小时）
        if len(history) > 12:
            history.pop(0)

        if len(history) >= 6:
            recent_avg = sum(history[-3:]) / 3
            older_avg = sum(history[-6:-3]) / 3

            if older_avg > 0:
                surge = recent_avg / older_avg
                if surge > 3:  # 3 倍交易量激增
                    print(f"检测到交易量激增: {pair.base_token.symbol} - {surge:.1f}x")

    # 监控高流动性交易对
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
