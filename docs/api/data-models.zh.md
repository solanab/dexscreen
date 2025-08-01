# 数据模型参考

Dexscreen 中的所有数据模型都是 Pydantic 模型，提供自动验证和类型安全。

## 核心模型

### TokenPair

表示交易对的主要模型。大多数查询和流式方法都会返回此模型。

```python
class TokenPair(BaseModel):
    chain_id: str                      # 区块链标识符
    dex_id: str                        # DEX 标识符
    url: str                           # DEXScreener URL
    pair_address: str                  # 交易对合约地址
    base_token: BaseToken              # 基础代币信息
    quote_token: BaseToken             # 报价代币信息
    price_native: float                # 原生代币价格
    price_usd: Optional[float]         # USD 价格
    transactions: PairTransactionCounts # 交易统计
    volume: VolumeChangePeriods        # 交易量数据
    price_change: PriceChangePeriods   # 价格变化
    liquidity: Optional[Liquidity]     # 流动性信息
    fdv: Optional[float]               # 完全稀释估值
    pair_created_at: Optional[datetime] # 创建时间戳
```

**使用示例：**

```python
pair = client.get_pair_by_pair_address("ethereum", "0x88e6...")
if pair:
    print(f"交易对: {pair.base_token.symbol}/{pair.quote_token.symbol}")
    print(f"价格: ${pair.price_usd:,.4f}")
    print(f"24小时交易量: ${pair.volume.h24:,.0f}")
    print(f"24小时变化: {pair.price_change.h24:+.2f}%")
```

### BaseToken

交易对中的基本代币信息。

```python
class BaseToken(BaseModel):
    address: str    # 合约地址
    name: str       # 代币名称
    symbol: str     # 代币符号
```

**使用示例：**

```python
# 识别交易对中哪个是 USDC
if pair.base_token.symbol == "USDC":
    other_token = pair.quote_token
else:
    other_token = pair.base_token

print(f"交易 {other_token.symbol} 对 USDC")
```

## 交易统计

### TransactionCount

买入和卖出交易计数。

```python
class TransactionCount(BaseModel):
    buys: int      # 买入交易数量
    sells: int     # 卖出交易数量
```

### PairTransactionCounts

不同时间段的交易统计。

```python
class PairTransactionCounts(BaseModel):
    m5: TransactionCount    # 5 分钟
    h1: TransactionCount    # 1 小时
    h6: TransactionCount    # 6 小时
    h24: TransactionCount   # 24 小时
```

**使用示例：**

```python
# 分析买卖压力
buy_pressure = pair.transactions.h1.buys / (pair.transactions.h1.buys + pair.transactions.h1.sells)
print(f"买入压力 (1小时): {buy_pressure:.1%}")

# 检查最近活动
total_5m = pair.transactions.m5.buys + pair.transactions.m5.sells
print(f"最近 5 分钟交易数: {total_5m}")
```

## 市场数据

### VolumeChangePeriods

跨时间段的 USD 交易量。

```python
class VolumeChangePeriods(BaseModel):
    m5: Optional[float] = 0.0    # 5 分钟交易量
    h1: Optional[float] = 0.0    # 1 小时交易量
    h6: Optional[float] = 0.0    # 6 小时交易量
    h24: Optional[float] = 0.0   # 24 小时交易量
```

### PriceChangePeriods

跨时间段的价格变化百分比。

```python
class PriceChangePeriods(BaseModel):
    m5: Optional[float] = 0.0    # 5 分钟变化 %
    h1: Optional[float] = 0.0    # 1 小时变化 %
    h6: Optional[float] = 0.0    # 6 小时变化 %
    h24: Optional[float] = 0.0   # 24 小时变化 %
```

**使用示例：**

```python
# 找出趋势交易对
if pair.price_change.h1 > 5 and pair.volume.h1 > 100_000:
    print(f"上升趋势: {pair.base_token.symbol}")

# 交易量分析
volume_acceleration = pair.volume.h1 / (pair.volume.h6 / 6)
if volume_acceleration > 2:
    print("检测到交易量激增！")
```

### Liquidity

交易对的流动性信息。

```python
class Liquidity(BaseModel):
    usd: Optional[float]    # USD 总流动性
    base: float             # 基础代币流动性
    quote: float            # 报价代币流动性
```

**使用示例：**

```python
# 按最低流动性过滤
if pair.liquidity and pair.liquidity.usd > 50_000:
    print(f"流动性充足的交易对: ${pair.liquidity.usd:,.0f}")

# 计算代币数量
print(f"池中包含: {pair.liquidity.base:,.2f} {pair.base_token.symbol}")
print(f"池中包含: {pair.liquidity.quote:,.2f} {pair.quote_token.symbol}")
```

## 代币信息

### TokenInfo

详细的代币档案信息。

```python
class TokenInfo(BaseModel):
    url: str                        # DEXScreener URL
    chain_id: str                   # 区块链标识符
    token_address: str              # 代币合约地址
    amount: float = 0.0             # 推广金额
    total_amount: float = 0.0       # 总推广金额
    icon: Optional[str]             # 图标 URL
    header: Optional[str]           # 头部图片 URL
    description: Optional[str]      # 代币描述
    links: List[TokenLink] = []     # 相关链接
```

### TokenLink

与代币相关的链接。

```python
class TokenLink(BaseModel):
    type: Optional[str]     # 链接类型（website、twitter 等）
    label: Optional[str]    # 显示标签
    url: Optional[str]      # 链接 URL
```

**使用示例：**

```python
# 获取代币档案
profiles = client.get_latest_token_profiles()

for token in profiles:
    print(f"代币: {token.token_address}")
    print(f"链: {token.chain_id}")

    if token.description:
        print(f"描述: {token.description}")

    # 显示社交链接
    for link in token.links:
        if link.type == "twitter":
            print(f"Twitter: {link.url}")
```

### OrderInfo

代币的订单/支付信息。

```python
class OrderInfo(BaseModel):
    type: str               # 订单类型
    status: str             # 订单状态
    payment_timestamp: int  # 支付时间戳（毫秒）
```

**使用示例：**

```python
orders = client.get_orders_paid_of_token("ethereum", token_address)

for order in orders:
    timestamp = datetime.fromtimestamp(order.payment_timestamp / 1000)
    print(f"订单 {order.type}: {order.status} 于 {timestamp}")
```

## 处理可选字段

许多字段是可选的，可能为 None。使用前始终检查：

```python
# 安全访问模式
if pair.price_usd:
    print(f"价格: ${pair.price_usd}")
else:
    print("USD 价格不可用")

# 使用默认值
volume_24h = pair.volume.h24 or 0
liquidity_usd = pair.liquidity.usd if pair.liquidity else 0

# 链式可选检查
if pair.liquidity and pair.liquidity.usd and pair.liquidity.usd > 100_000:
    print("高流动性交易对")
```

## 类型提示和 IDE 支持

所有模型都有完整的类型提示，提供出色的 IDE 支持：

```python
from dexscreen import TokenPair, DexscreenerClient

def analyze_pair(pair: TokenPair) -> dict:
    """分析交易对"""
    return {
        "symbol": pair.base_token.symbol,
        "price": pair.price_usd,
        "volume_24h": pair.volume.h24,
        "liquidity": pair.liquidity.usd if pair.liquidity else 0,
        "buy_pressure": calculate_buy_pressure(pair.transactions)
    }

def calculate_buy_pressure(txns: PairTransactionCounts) -> float:
    """从交易中计算买入压力"""
    total = txns.h24.buys + txns.h24.sells
    return txns.h24.buys / total if total > 0 else 0.5
```

## 模型验证

Pydantic 自动验证数据：

```python
from pydantic import ValidationError

try:
    # 这将验证失败
    token = BaseToken(
        address="invalid",  # 应该是有效地址
        name="",           # 不应为空
        symbol=""          # 不应为空
    )
except ValidationError as e:
    print(f"验证错误: {e}")
```

## JSON 序列化

所有模型都可以轻松序列化：

```python
# 转换为字典
pair_dict = pair.model_dump()

# 转换为 JSON 字符串
pair_json = pair.model_dump_json()

# 排除 None 值
pair_dict = pair.model_dump(exclude_none=True)

# 保存到文件
import json
with open("pair_data.json", "w") as f:
    json.dump(pair.model_dump(), f, indent=2)
```

---
