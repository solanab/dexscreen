# Dexscreen 入门指南

本指南将帮助您快速上手并开始使用 Dexscreen，让您轻松进行 DeFi 数据监控和分析。

## 安装

### 使用 uv

```bash
uv add dexscreen
```

### 使用 pip

```bash
pip install dexscreen
```

### 从源码安装

```bash
git clone https://github.com/yourusername/dexscreen.git
cd dexscreen
pip install -e .
```

## 基本概念

Dexscreen 提供两种主要方式与 Dexscreener 数据交互：

1. **查询 API** - 一次性数据获取（同步或异步），适用于：
   - 当前价格检查
   - 代币搜索和发现
   - 快照式数据分析
   - 历史数据获取

2. **流式 API** - 通过 HTTP 轮询实现实时更新，适用于：
   - 实时价格监控
   - 交易机器人
   - 警报系统
   - 投资组合跟踪

## 您的第一个查询

### 创建客户端

```python
from dexscreen import DexscreenerClient

# 基本客户端（推荐用于大多数用例）
client = DexscreenerClient()

# 带浏览器模拟（在遇到反机器人保护时使用）
client = DexscreenerClient(impersonate="chrome136")

# 调试模式（开发时启用详细日志）
client = DexscreenerClient(debug=True)
```

### 获取交易对数据

```python
# 1. 搜索交易对（按代币名称或符号）
pairs = client.search_pairs("PEPE")
if pairs:
    print(f"找到 {len(pairs)} 个 PEPE 交易对")
    for pair in pairs[:5]:  # 显示前 5 个结果
        print(f"  {pair.base_token.symbol}/{pair.quote_token.symbol} 在 {pair.chain_id}")
        print(f"    价格: ${pair.price_usd:.8f}, DEX: {pair.dex_id}")
        print(f"    24h交易量: ${pair.volume.h24:,.0f}")
        print()

# 2. 获取特定代币的所有交易对
usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # 以太坊 USDC
pairs = client.get_pairs_by_token_address("ethereum", usdc_address)
print(f"在以太坊找到 {len(pairs)} 个 USDC 交易对")

# 找到流动性最高的 USDC 交易对
if pairs:
    best_usdc_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)
    print(f"最佳 USDC 交易对: {best_usdc_pair.base_token.symbol}/{best_usdc_pair.quote_token.symbol}")
    print(f"流动性: ${best_usdc_pair.liquidity.usd:,.0f}")

# 3. 获取特定交易对的详细信息
pair = client.get_pair_by_pair_address(
    "ethereum",
    "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # Uniswap V3 USDC/WETH
)
if pair:
    print(f"交易对详情:")
    print(f"  价格: ${pair.price_usd:.6f}")
    print(f"  24小时交易量: ${pair.volume.h24:,.0f}")
    print(f"  24小时价格变化: {pair.price_change.h24:+.2f}%")
    print(f"  DEX: {pair.dex_id}")
```

## 实时更新

### 基本订阅

```python
import asyncio
from datetime import datetime

async def price_update_handler(pair):
    """处理价格更新 - 显示时间戳和关键信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {pair.base_token.symbol}: ${pair.price_usd:,.4f} "
          f"(24h: {pair.price_change.h24:+.2f}%)")

async def main():
    client = DexscreenerClient()

    print("开始监控 JUP 代币价格...")

    # 订阅 Solana 上的 JUP 交易对
    await client.subscribe_pairs(
        chain_id="solana",
        pair_addresses=["JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"],
        callback=price_update_handler,
        interval=1.0  # 每秒检查一次更新
    )

    # 监控 30 秒
    print("监控中... (30秒)")
    await asyncio.sleep(30)

    # 清理资源
    print("正在关闭连接...")
    await client.close_streams()
    print("监控结束")

# 运行异步函数
if __name__ == "__main__":
    asyncio.run(main())
```

### 监控多个交易对

```python
async def portfolio_monitor():
    client = DexscreenerClient()

    # 定义您的投资组合（链ID, 交易对地址, 描述）
    portfolio = [
        ("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640", "USDC/WETH Uniswap V3"),
        ("solana", "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", "JUP/SOL Raydium"),
        ("bsc", "0x2170ed0880ac9a755fd29b2688956bd959f933f8", "ETH/BNB PancakeSwap"),
    ]

    # 投资组合更新处理器
    async def handle_portfolio_update(pair):
        timestamp = datetime.now().strftime("%H:%M:%S")
        # 确定哪个代币是主要代币（非稳定币）
        main_token = pair.base_token if pair.base_token.symbol not in ["USDC", "USDT", "BUSD"] else pair.quote_token

        print(f"[{timestamp}] [{pair.chain_id.upper()}] {main_token.symbol}: "
              f"${pair.price_usd:,.4f} ({pair.price_change.h24:+.2f}%) "
              f"Vol: ${pair.volume.h24:,.0f}")

    print("开始监控投资组合...")

    # 订阅所有交易对
    for chain_id, pair_address, description in portfolio:
        print(f"订阅 {description} 在 {chain_id}")
        await client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=[pair_address],
            callback=handle_portfolio_update,
            interval=2.0  # 每 2 秒检查更新
        )

    print(f"\n正在监控 {len(portfolio)} 个交易对，按 Ctrl+C 停止...")

    try:
        # 监控 1 分钟（生产环境中可能会更长）
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...")
    finally:
        await client.close_streams()
        print("投资组合监控已停止")

if __name__ == "__main__":
    asyncio.run(portfolio_monitor())
```

## 过滤更新

使用过滤器控制何时触发回调，减少不必要的通知：

```python
from dexscreen import FilterPresets

# 1. 仅在价格显著变化时触发（1% 阈值）
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=handle_update,
    filter=FilterPresets.significant_price_changes(0.01),  # 1% 价格变化
    interval=0.5  # 每 0.5 秒检查
)

# 2. 限制更新频率以避免过载
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=handle_update,
    filter=FilterPresets.rate_limited(1.0),  # 每秒最多 1 次更新
    interval=0.2  # 快速轮询但限制回调频率
)

# 3. UI 友好的过滤（平衡更新频率和有用性）
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=handle_update,
    filter=FilterPresets.ui_friendly(),  # 预配置的 UI 优化设置
    interval=1.0
)
```

## 错误处理

在生产环境中，始终在回调中处理错误以避免订阅中断：

```python
import logging

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_callback(pair):
    try:
        # 您的业务逻辑
        if pair.price_usd and pair.price_usd > 100:
            print(f"高价值代币: {pair.base_token.symbol} = ${pair.price_usd:,.2f}")

        # 检查价格异常变化
        if abs(pair.price_change.h24) > 50:  # 24小时变化超过50%
            logger.warning(f"价格异常变化: {pair.base_token.symbol} {pair.price_change.h24:+.2f}%")

    except AttributeError as e:
        logger.error(f"数据字段缺失: {e}")
    except TypeError as e:
        logger.error(f"数据类型错误: {e}")
    except Exception as e:
        logger.error(f"处理更新时出现未知错误: {e}")
        # 重要：不要重新抛出异常，避免订阅中断

# 使用安全回调
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
        logger.error(f"订阅设置失败: {e}")
    finally:
        await client.close_streams()
        logger.info("监控会话结束")
```

## 同步 vs 异步

Dexscreen 支持两种模式：

### 同步模式

```python
# 简单直接，适用于脚本和一次性查询
client = DexscreenerClient()

# 同步搜索
pairs = client.search_pairs("PEPE")
print(f"找到 {len(pairs)} 个 PEPE 交易对")

# 同步获取特定交易对
pair = client.get_pair_by_pair_address("ethereum", "0x88e6...")
if pair:
    print(f"当前价格: ${pair.price_usd}")
```

### 异步模式

```python
# 更适合并发操作、实时监控和高性能应用
async def fetch_multiple_tokens():
    client = DexscreenerClient()

    # 定义要搜索的代币
    tokens = ["PEPE", "SHIB", "DOGE", "FLOKI"]

    print("并发搜索多个代币...")

    # 并发运行多个查询（更快）
    tasks = [client.search_pairs_async(token) for token in tokens]
    results = await asyncio.gather(*tasks)

    # 处理结果
    for token, token_pairs in zip(tokens, results):
        if token_pairs:
            best_pair = max(token_pairs, key=lambda p: p.volume.h24 or 0)
            print(f"{token}: 找到 {len(token_pairs)} 个交易对，"
                  f"最高交易量: ${best_pair.volume.h24:,.0f}")
        else:
            print(f"{token}: 未找到交易对")

# 运行异步函数
if __name__ == "__main__":
    asyncio.run(fetch_multiple_tokens())
```

## 下一步

### 📚 深入学习

1. **[查询 API](api/query-api.zh.md)** - 了解所有可用的数据获取方法
2. **[流式 API](api/streaming-api.zh.md)** - 掌握实时数据监控技术
3. **[数据模型](api/data-models.zh.md)** - 理解 API 返回的数据结构
4. **[过滤器](api/filtering.zh.md)** - 学习高级过滤技术优化性能
5. **[示例](examples.zh.md)** - 查看完整的生产就绪代码示例

### 🚀 实际项目思路

- **价格警报机器人**: 监控代币价格变化并发送通知
- **套利扫描器**: 跨不同 DEX 和链寻找套利机会
- **投资组合仪表板**: 实时跟踪您的 DeFi 投资组合
- **新代币发现工具**: 自动发现和分析新上市的代币
- **流动性监控系统**: 跟踪大额流动性变化

## 常见问题询阵

### 🚦 速率限制

**问题**: 遇到速率限制错误 **解决方案**:

- SDK 自动处理速率限制，会自动退避重试
- 如果频繁遇到限制，考虑增加轮询间隔
- 使用批量方法（如 `get_pairs_by_pairs_addresses`）而不是多次单独调用

### 📊 没有返回数据

**常见原因**:

- ❌ 错误的 chain_id：使用 `"ethereum"` 而不是 `"eth"`
- ❌ 无效的合约地址：确保地址格式正确且经过校验和
- ❌ 代币不存在：某些代币可能在特定链上没有交易对
- ❌ 新代币：刚发布的代币可能还未被索引

**解决方法**:

```python
# 验证地址格式
from web3 import Web3
address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
if Web3.isAddress(address):
    pairs = client.get_pairs_by_token_address("ethereum", address)
else:
    print("无效的以太坊地址")
```

### 🔄 订阅未更新

**诊断步骤**:

1. **检查过滤器配置**：确保过滤器不会过滤掉所有更新

   ```python
   # 临时禁用过滤器进行测试
   await client.subscribe_pairs(..., filter=False)
   ```

2. **验证交易对活跃度**：确保交易对有实际的交易活动

   ```python
   pair = client.get_pair_by_pair_address(chain_id, pair_address)
   if pair and pair.volume.h24 > 0:
       print("交易对活跃")
   else:
       print("交易对可能不活跃")
   ```

3. **检查回调错误**：确保回调函数没有抛出异常

   ```python
   async def debug_callback(pair):
       try:
           print(f"收到更新: {pair.base_token.symbol}")
           # 您的逻辑...
       except Exception as e:
           print(f"回调错误: {e}")
   ```

### 🔧 连接问题

**问题**: 无法连接到 Dexscreener API

**解决方案**:

```python
# 启用浏览器模拟以绕过反机器人保护
client = DexscreenerClient(impersonate="chrome136")

# 或者设置调试模式查看详细错误
client = DexscreenerClient(debug=True)
```

### 💾 内存使用

**问题**: 长时间运行后内存使用过高

**解决方案**:

- 定期清理不需要的订阅
- 使用适当的过滤器减少数据处理
- 实现数据轮换策略

```python
# 定期清理示例
import asyncio
from datetime import datetime, timedelta

class ManagedClient:
    def __init__(self):
        self.client = DexscreenerClient()
        self.last_cleanup = datetime.now()

    async def periodic_cleanup(self):
        while True:
            await asyncio.sleep(3600)  # 每小时检查
            if datetime.now() - self.last_cleanup > timedelta(hours=6):
                print("执行定期清理...")
                await self.client.close_streams()
                self.client = DexscreenerClient()  # 创建新实例
                self.last_cleanup = datetime.now()
```

## 🆘 获取帮助

| 资源类型        | 链接                                                                        | 适用情况         |
| --------------- | --------------------------------------------------------------------------- | ---------------- |
| **📖 完整示例** | [示例页面](examples.zh.md)                                                  | 需要工作代码参考 |
| **📋 API 参考** | [查询 API](api/query-api.zh.md)                                                 | 了解具体方法用法 |
| **🐛 错误报告** | [GitHub Issues](https://github.com/yourusername/dexscreen/issues)           | 发现 bug 或问题  |
| **💡 功能建议** | [GitHub Discussions](https://github.com/yourusername/dexscreen/discussions) | 建议新功能       |
| **💬 社区讨论** | [GitHub Discussions](https://github.com/yourusername/dexscreen/discussions) | 一般问题和讨论   |

### 🔍 寻求帮助时的最佳实践

1. **提供完整的错误信息**和相关的代码片段
2. **说明您的使用场景**和期望的行为
3. **包含系统信息**（Python 版本、操作系统等）
4. **先检查现有的 Issues** 看是否已有解决方案

> **💡 提示**: 大多数问题都可以通过查看[示例](examples.zh.md)中的完整代码得到解答！

---

**🎉 恭喜！**
您现在已经掌握了 Dexscreen 的基础知识。继续探索[示例](examples.zh.md)以了解更多高级用法，或直接开始构建您的第一个 DeFi 监控应用！
