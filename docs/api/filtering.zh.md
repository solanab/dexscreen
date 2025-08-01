# 过滤配置

过滤允许您控制何时触发流式回调，减少噪音并专注于有意义的变化。

## 概述

过滤系统提供：

- **变化检测** - 仅在实际数据变化时触发
- **阈值过滤** - 仅在显著变化时触发
- **速率限制** - 控制最大更新频率
- **字段选择** - 仅监控特定字段

## FilterConfig 类

用于精确控制的自定义过滤配置。

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FilterConfig:
    # 要监控变化的字段
    change_fields: List[str] = field(default_factory=lambda: [
        "price_usd", "price_native", "volume.h24", "liquidity.usd"
    ])

    # 变化阈值（None = 任何变化都触发）
    price_change_threshold: Optional[float] = None      # 价格变化 %（如 0.01 = 1%）
    volume_change_threshold: Optional[float] = None     # 交易量变化 %（如 0.10 = 10%）
    liquidity_change_threshold: Optional[float] = None  # 流动性变化 %（如 0.05 = 5%）

    # 速率限制
    max_updates_per_second: Optional[float] = None      # 最大更新/秒（如 1.0 = 1/秒）
```

### 参数

- **`change_fields`**：要监控的字段列表。只有这些字段的变化才能触发更新。支持嵌套字段（如 "volume.h24"）
- **`price_change_threshold`**：价格变化百分比阈值。设置为 0.01 表示 1% 的变化
- **`volume_change_threshold`**：交易量变化百分比阈值。设置为 0.10 表示 10% 的变化
- **`liquidity_change_threshold`**：流动性变化百分比阈值。设置为 0.05 表示 5% 的变化
- **`max_updates_per_second`**：限制更新频率以避免回调过载

### 自定义配置示例

```python
from dexscreen.utils import FilterConfig

# 高频交易配置
hft_config = FilterConfig(
    change_fields=["price_usd"],           # 仅监控价格
    price_change_threshold=0.0001,         # 0.01% 变化
    max_updates_per_second=10.0            # 允许频繁更新
)

# 长期监控配置
hodl_config = FilterConfig(
    change_fields=["price_usd", "liquidity.usd"],
    price_change_threshold=0.05,           # 5% 变化
    liquidity_change_threshold=0.20,       # 20% 流动性变化
    max_updates_per_second=0.1             # 每 10 秒最多一次
)

# 交易量激增检测
volume_config = FilterConfig(
    change_fields=["volume.h24", "volume.h1", "transactions.m5.buys", "transactions.m5.sells"],
    volume_change_threshold=0.15,          # 15% 交易量变化
    max_updates_per_second=0.5             # 每 2 秒最多一次
)
```

## FilterPresets

常见用例的预配置过滤器。

### simple_change_detection()

```python
config = FilterPresets.simple_change_detection()
```

基本变化检测（默认行为）- 任何监控字段的变化都会触发更新。

**用于**：需要所有变化的一般监控

### significant_price_changes(threshold)

```python
config = FilterPresets.significant_price_changes(0.01)  # 1% 阈值
```

仅在价格变化超过阈值时触发。

**用于**：价格警报、交易信号

### significant_all_changes(price_threshold, volume_threshold, liquidity_threshold)

```python
config = FilterPresets.significant_all_changes(
    price_threshold=0.005,      # 0.5% 价格变化
    volume_threshold=0.10,      # 10% 交易量变化
    liquidity_threshold=0.05    # 5% 流动性变化
)
```

所有指标必须满足其阈值才能触发。

**用于**：需要多重确认的高置信度信号

### rate_limited(max_per_second)

```python
config = FilterPresets.rate_limited(1.0)  # 每秒最多 1 次更新
```

限制更新频率，无论变化如何。

**用于**：UI 更新、减少回调负载

### ui_friendly()

```python
config = FilterPresets.ui_friendly()
```

针对用户界面优化：

- 价格变化阈值：0.1%
- 交易量变化阈值：5%
- 每秒最多 2 次更新

**用于**：仪表板显示、实时图表

### monitoring()

```python
config = FilterPresets.monitoring()
```

针对监控系统优化：

- 价格变化阈值：1%
- 交易量变化阈值：10%
- 流动性变化阈值：5%
- 每秒最多 0.2 次更新（每 5 秒一次）

**用于**：警报系统、后台监控

## 使用示例

### 基本过滤

```python
# 默认过滤（仅变化）
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6..."],
    callback=handle_update,
    filter=True  # 默认
)

# 无过滤（所有更新）
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6..."],
    callback=handle_update,
    filter=False
)

# 预设过滤
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6..."],
    callback=handle_update,
    filter=FilterPresets.significant_price_changes(0.02)  # 2%
)
```

### 高级过滤

```python
# 多指标监控
comprehensive_config = FilterConfig(
    change_fields=["price_usd", "volume.h24", "liquidity.usd", "price_change.h24"],
    price_change_threshold=0.02,           # 2% 价格变化
    volume_change_threshold=0.25,          # 25% 交易量变化
    liquidity_change_threshold=0.10,       # 10% 流动性变化
    max_updates_per_second=1.0             # 每秒最多一次
)

await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=addresses,
    callback=comprehensive_handler,
    filter=comprehensive_config
)
```

### 条件过滤

将过滤与回调逻辑结合：

```python
# 显著变化的过滤配置
config = FilterConfig(
    change_fields=["price_usd", "volume.h1"],
    price_change_threshold=0.001  # 0.1%
)

# 回调中的附加逻辑
def smart_callback(pair: TokenPair):
    # 过滤器已确保显著变化
    # 添加更多条件
    if pair.volume.h1 > 10_000:  # 最小交易量
        if pair.liquidity and pair.liquidity.usd > 50_000:  # 最小流动性
            process_significant_update(pair)
```

## 可监控字段

您可以在 `change_fields` 中监控的字段：

### 价格字段

- `price_usd` - USD 价格
- `price_native` - 原生代币价格

### 交易量字段

- `volume.h24` - 24小时交易量
- `volume.h6` - 6小时交易量
- `volume.h1` - 1小时交易量
- `volume.m5` - 5分钟交易量

### 流动性字段

- `liquidity.usd` - USD 流动性
- `liquidity.base` - 基础代币流动性
- `liquidity.quote` - 报价代币流动性

### 交易字段

- `transactions.m5.buys` - 5分钟买入数
- `transactions.m5.sells` - 5分钟卖出数
- `transactions.h1.buys` - 1小时买入数
- `transactions.h1.sells` - 1小时卖出数
- `transactions.h6.buys` - 6小时买入数
- `transactions.h6.sells` - 6小时卖出数
- `transactions.h24.buys` - 24小时买入数
- `transactions.h24.sells` - 24小时卖出数

### 价格变化字段

- `price_change.m5` - 5分钟价格变化 %
- `price_change.h1` - 1小时价格变化 %
- `price_change.h6` - 6小时价格变化 %
- `price_change.h24` - 24小时价格变化 %

### 其他字段

- `fdv` - 完全稀释估值

**注意**：对嵌套字段使用点表示法（如 `volume.h24`、`transactions.m5.buys`）

## 性能考虑

### 过滤器效率

过滤器在获取数据后在客户端应用：

1. **数据获取**：在指定间隔发生
2. **变化检测**：与之前的数据比较
3. **阈值检查**：应用配置的阈值
4. **速率限制**：强制执行最大更新频率
5. **回调执行**：仅在所有条件通过时

### 优化技巧

1. **最小化监控字段**：仅包含您实际需要的字段

   ```python
   # 好 - 特定字段
   change_fields=["price_usd", "volume.h24"]

   # 坏 - 监控所有内容
   change_fields=["price_usd", "price_native", "volume.h24", "volume.h6", ...]
   ```

2. **设置适当的阈值**：在灵敏度和噪音之间取得平衡

   ```python
   # 高价值资产 - 较大阈值
   eth_config = FilterConfig(price_change_threshold=0.01)  # 1%

   # 低价值/波动资产 - 较小阈值
   meme_config = FilterConfig(price_change_threshold=0.001)  # 0.1%
   ```

3. **使用速率限制**：防止回调过载

   ```python
   # 用于 UI 更新
   ui_config = FilterConfig(max_updates_per_second=2.0)

   # 用于日志/数据库
   db_config = FilterConfig(max_updates_per_second=0.1)  # 每 10 秒一次
   ```

## 常见模式

### 价格警报系统

```python
# 不同的警报级别
minor_alert = FilterConfig(
    change_fields=["price_usd"],
    price_change_threshold=0.02,  # 2%
    max_updates_per_second=1.0
)

major_alert = FilterConfig(
    change_fields=["price_usd"],
    price_change_threshold=0.05,  # 5%
    max_updates_per_second=None   # 主要警报无速率限制
)

# 使用不同的回调订阅
await client.subscribe_pairs(chain_id, pairs, minor_callback, filter=minor_alert)
await client.subscribe_pairs(chain_id, pairs, major_callback, filter=major_alert)
```

### 多策略过滤

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
        max_updates_per_second=0.2      # 每 5 秒一次
    ),
    "liquidity": FilterConfig(
        change_fields=["liquidity.usd"],
        liquidity_change_threshold=0.10,  # 10%
        max_updates_per_second=0.1        # 每 10 秒一次
    )
}

# 对不同交易对应用不同策略
for strategy_name, config in strategies.items():
    pairs = get_pairs_for_strategy(strategy_name)
    callback = create_strategy_callback(strategy_name)
    await client.subscribe_pairs("ethereum", pairs, callback, filter=config)
```

---
