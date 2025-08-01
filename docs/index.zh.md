# Dexscreen 文档

欢迎使用 Dexscreen 文档！这个 Python SDK 为 [Dexscreener.com](https://dexscreener.com/)
API 提供了稳定、可靠且功能丰富的接口，支持实时 DeFi 数据监控和分析。

> **🎯 快速开始**：Dexscreen 新手？从我们的[入门指南](getting-started.zh.md)开始，了解安装和首次查询。

## 🚀 快速导航

| 章节                                    | 描述                     | 适用场景                 |
| --------------------------------------- | ------------------------ | ------------------------ |
| **[入门指南](getting-started.zh.md)**   | 安装、设置和首次查询     | 新用户、快速设置         |
| **[查询 API](api/query-api.zh.md)**     | 单次查询方法获取数据     | 一次性数据获取、API 参考 |
| **[流式 API](api/streaming-api.zh.md)** | 实时订阅方法获取实时更新 | 实时监控、交易机器人     |
| **[数据模型](api/data-models.zh.md)**   | 所有数据结构的完整参考   | 理解 API 响应            |
| **[过滤器](api/filtering.zh.md)**       | 高级过滤和配置选项       | 优化订阅、减少噪音       |
| **[示例](examples.zh.md)**              | 常见用例的完整工作示例   | 实例学习、生产模式       |

## 📚 文档结构

### 🎯 快速开始

- **[入门指南](getting-started.zh.md)** - 安装、基本设置和首次查询
- **[示例](examples.zh.md)** - 常见用例的完整可运行示例

> **💡 新用户路径**：[入门指南](getting-started.zh.md) → [示例](examples.zh.md) → [查询 API](api/query-api.zh.md) →
> [流式 API](api/streaming-api.zh.md)

### 📖 API 参考

- **[查询 API](api/query-api.zh.md)** - 一次性数据获取的所有查询方法综合指南
- **[流式 API](api/streaming-api.zh.md)** - 持续更新的实时订阅方法
- **[数据模型](api/data-models.zh.md)** - 所有数据结构和类型的完整参考
- **[过滤器](api/filtering.zh.md)** - 高级过滤、速率限制和性能优化

> **⚠️ 重要**：处理 API 响应时请务必查看[数据模型](api/data-models.zh.md)参考。

## ⚡ 快速开始

### 安装

**使用 uv（推荐）：**

```bash
uv add dexscreen
```

**使用 pip：**

```bash
pip install dexscreen
```

### 基本使用示例

**📊 获取代币价格：**

```python
from dexscreen import DexscreenerClient

client = DexscreenerClient()

# 获取以太坊上的所有 USDC 交易对
pairs = client.get_pairs_by_token_address(
    "ethereum",
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
)

if pairs:
    # 找到流动性最高的交易对
    best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)
    print(f"USDC 价格: ${best_pair.price_usd:.4f}")
    print(f"24小时交易量: ${best_pair.volume.h24:,.0f}")
```

**🔄 实时监控：**

```python
import asyncio
from dexscreen import DexscreenerClient, FilterPresets

async def price_alert(pair):
    print(f"{pair.base_token.symbol}: ${pair.price_usd:.4f}")

async def main():
    client = DexscreenerClient()

    # 监控 USDC/WETH 交易对，价格变化 > 0.1%
    await client.subscribe_pairs(
        chain_id="ethereum",
        pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
        callback=price_alert,
        filter=FilterPresets.significant_price_changes(0.001)  # 0.1%
    )

    await asyncio.sleep(60)  # 监控 1 分钟
    await client.close_streams()

asyncio.run(main())
```

> **📖 了解更多**：查看[示例](examples.zh.md)获取完整的生产就绪代码示例。
>
> **🔍 需要帮助？**：查看下方的[疑难解答](#需要帮助)部分或浏览[示例](examples.zh.md)了解常见模式。

## 📊 API 快速参考

### 🔍 查询方法（[完整参考](api/query-api.zh.md)）

| 方法                                                  | 描述                       | 速率限制 | 使用场景       |
| ----------------------------------------------------- | -------------------------- | -------- | -------------- |
| `get_pair(address)`                                   | 按地址获取交易对（任意链） | 300/分钟 | 快速价格检查   |
| `get_pair_by_pair_address(chain_id, pair_address)`    | 获取特定链上的特定交易对   | 300/分钟 | 详细交易对信息 |
| `get_pairs_by_token_address(chain_id, token_address)` | 获取代币的所有交易对       | 300/分钟 | 代币分析       |
| `search_pairs(query)`                                 | 按名称/符号/地址搜索交易对 | 300/分钟 | 代币发现       |
| `get_latest_token_profiles()`                         | 最新代币档案               | 60/分钟  | 新代币跟踪     |
| `get_latest_boosted_tokens()`                         | 最新推广代币               | 60/分钟  | 推广代币       |

### 📡 流式方法（[完整参考](api/streaming-api.zh.md)）

| 方法                                                    | 描述                 | 最适用于       |
| ------------------------------------------------------- | -------------------- | -------------- |
| `subscribe_pairs(chain_id, pair_addresses, callback)`   | 监控特定交易对       | 价格警报、交易 |
| `subscribe_tokens(chain_id, token_addresses, callback)` | 监控代币的所有交易对 | 代币监控       |
| `unsubscribe_pairs(chain_id, pair_addresses)`           | 停止监控交易对       | 动态管理       |
| `unsubscribe_tokens(chain_id, token_addresses)`         | 停止监控代币         | 动态管理       |
| `get_active_subscriptions()`                            | 列出活动订阅         | 调试、监控     |
| `close_streams()`                                       | 清理所有连接         | 清理、关闭     |

> **⚠️ 速率限制**：SDK 自动处理速率限制，并配备智能重试逻辑。

## 🔑 核心功能

### ✨ 核心功能

- **🌐 完整 API 覆盖** - 所有 Dexscreener 端点，功能完全对等
- **⚡ 实时更新** - 基于 HTTP 的流式传输，可配置轮询间隔
- **🎯 智能过滤** - 带自定义阈值的客户端过滤，减少噪音
- **🔗 多链支持** - 使用独立配置同时监控多个区块链

### 🛡️ 可靠性与性能

- **🚦 自动速率限制** - 智能重试逻辑与指数退避
- **🕵️ 浏览器模拟** - 使用 curl_cffi 的高级反机器人绕过
- **🔒 类型安全** - 完整的 Pydantic 模型验证与综合错误处理
- **📊 批量操作** - 多查询的高效批量处理

### 🎨 开发者体验

- **🐍 异步/同步支持** - 同时提供同步和异步 API
- **📝 丰富文档** - 带实际示例的综合指南
- **🔧 灵活配置** - 可自定义过滤器、间隔和回调
- **🐛 调试友好** - 详细日志和错误消息

## 🛠️ 常见用例

### 💰 交易与 DeFi

**📈 价格监控** - [完整示例](examples.zh.md#价格监控)

```python
# 跟踪显著价格变动（1% 阈值）
await client.subscribe_pairs(
    chain_id="ethereum",
    pair_addresses=["0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"],
    callback=price_alert,
    filter=FilterPresets.significant_price_changes(0.01)
)
```

**🔄 套利检测** - [完整示例](examples.zh.md#套利检测)

```python
# 监控多条链上的 USDC 价格差异
chains = ["ethereum", "polygon", "arbitrum"]
for chain in chains:
    await client.subscribe_pairs(chain, usdc_pairs[chain], arbitrage_callback)
```

### 📊 分析与研究

**🔍 新代币发现** - [完整示例](examples.zh.md#新代币发现)

```python
# 监控代币的所有交易对以发现新的 DEX 上市
await client.subscribe_tokens(
    chain_id="solana",
    token_addresses=["JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"],
    callback=new_pair_callback
)
```

**📈 投资组合跟踪** - [完整示例](examples.zh.md#投资组合跟踪)

```python
# 使用每条链的自定义过滤器跟踪多个资产
for chain_id, config in portfolio_config.items():
    await client.subscribe_pairs(
        chain_id=chain_id,
        pair_addresses=config['pairs'],
        callback=portfolio_callback,
        filter=config['filter']
    )
```

### 🚨 监控与警报

**⚠️ 交易量激增检测** - [完整示例](examples.zh.md#交易量分析)

```python
# 检测异常交易活动
volume_config = FilterConfig(
    change_fields=["volume.m5", "volume.h1"],
    volume_change_threshold=0.50  # 50% 交易量增长
)
```

**💧 流动性监控** - [完整示例](examples.zh.md#流动性监控)

```python
# 跟踪流动性添加/移除
liquidity_config = FilterConfig(
    change_fields=["liquidity.usd"],
    liquidity_change_threshold=0.10  # 10% 流动性变化
)
```

> **🔗 更多示例**：访问[示例页面](examples.zh.md)获取完整的生产就绪实现。

> **📊 性能提示**：查看我们的[性能优化](#最佳实践)部分和[过滤指南](api/filtering.zh.md)了解最佳实践。

## 最佳实践

### ⚡ 性能优化

1. **🎯 使用适当的间隔**

   ```python
   # 高频交易：0.2秒
   interval=0.2

   # 投资组合监控：5-10秒
   interval=5.0

   # 长期警报：30-60秒
   interval=30.0
   ```

2. **🔍 应用智能过滤** - [了解更多](api/filtering.zh.md)

   ```python
   # 仅显著变化
   filter=FilterPresets.significant_price_changes(0.01)

   # 速率限制更新
   filter=FilterPresets.rate_limited(1.0)  # 每秒最多 1 次
   ```

### 🛡️ 错误处理与资源管理

1. **🚨 优雅处理错误**

   ```python
   async def safe_callback(pair):
       try:
           await process_update(pair)
       except Exception as e:
           logger.error(f"回调错误: {e}")
           # 不要让错误导致订阅崩溃
   ```

2. **🧹 清理资源**

   ```python
   try:
       await client.subscribe_pairs(...)
       await asyncio.sleep(300)  # 运行 5 分钟
   finally:
       await client.close_streams()  # 始终清理
   ```

# 检查活动订阅

```python
active = client.get_active_subscriptions()
print(f"活动订阅数: {len(active)}")
```

### 🎯 开发指南

- **速率限制**：SDK 自动处理，但要监控您的使用情况
- **类型安全**：使用类型提示获得更好的 IDE 支持
- **测试**：开发期间使用小间隔和短持续时间
- **日志记录**：启用调试日志以进行故障排除

> **📖 深入了解**：阅读[入门指南](getting-started.zh.md)获取详细的设置说明。

## 🔗 外部资源

### 📚 文档与代码

- **[📖 完整 API 文档](api/query-api.zh.md)** - 详细的方法参考
- **[🎯 入门教程](getting-started.zh.md)** - 分步设置指南
- **[💡 实用示例](examples.zh.md)** - 生产就绪代码示例
- **[GitHub 仓库](https://github.com/yourusername/dexscreen)** - 源代码和问题反馈

### 🌐 相关服务

- **[Dexscreener.com](https://dexscreener.com/)** - 官方 Dexscreener 平台
- **[Dexscreener API 文档](https://docs.dexscreener.com/)** - 上游 API 文档
- **[PyPI 包](https://pypi.org/project/dexscreen/)** - 官方包仓库

---

## 需要帮助？

| 问题类型     | 资源                                                                        |
| ------------ | --------------------------------------------------------------------------- |
| **快速开始** | [入门指南](getting-started.zh.md)                                           |
| **API 问题** | [查询 API](api/query-api.zh.md) 或 [流式 API](api/streaming-api.zh.md)              |
| **代码示例** | [示例页面](examples.zh.md)                                                  |
| **错误报告** | [GitHub Issues](https://github.com/yourusername/dexscreen/issues)           |
| **功能请求** | [GitHub Discussions](https://github.com/yourusername/dexscreen/discussions) |

---

## 📄 许可证

**MIT 许可证** - 查看 [LICENSE](https://github.com/yourusername/dexscreen/blob/main/LICENSE) 文件了解完整条款和条件。

> **🙏 贡献**：我们欢迎贡献！请阅读 GitHub 仓库中的贡献指南。
