# 完整示例

本页包含 Dexscreen 常见用例的完整工作示例。

## 基本用法

### 简单价格检查

```python
from dexscreen import DexscreenerClient

def check_token_price():
    client = DexscreenerClient()

    # 获取代币的交易对
    pairs = client.get_pairs_by_token_address(
        "ethereum",
        "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
    )

    if pairs:
        # 找到流动性最高的交易对
        best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)
        print(f"流动性最高的 USDC 交易对: {best_pair.base_token.symbol}/{best_pair.quote_token.symbol}")
        print(f"DEX: {best_pair.dex_id}")
        print(f"价格: ${best_pair.price_usd:,.4f}")
        print(f"流动性: ${best_pair.liquidity.usd:,.0f}")

if __name__ == "__main__":
    check_token_price()
```

### 搜索和分析

```python
import asyncio
from dexscreen import DexscreenerClient

async def analyze_search_results():
    client = DexscreenerClient()

    # 搜索 PEPE 代币
    results = await client.search_pairs_async("PEPE")

    # 按流动性过滤和排序
    liquid_pairs = [p for p in results if p.liquidity and p.liquidity.usd > 50_000]
    liquid_pairs.sort(key=lambda p: p.liquidity.usd, reverse=True)

    print(f"找到 {len(liquid_pairs)} 个流动性充足的 PEPE 交易对\n")

    for pair in liquid_pairs[:5]:
        print(f"{pair.chain_id} - {pair.dex_id}")
        print(f"  交易对: {pair.base_token.symbol}/{pair.quote_token.symbol}")
        print(f"  价格: ${pair.price_usd:,.8f}")
        print(f"  24小时交易量: ${pair.volume.h24:,.0f}")
        print(f"  流动性: ${pair.liquidity.usd:,.0f}")
        print(f"  24小时变化: {pair.price_change.h24:+.2f}%")
        print()

if __name__ == "__main__":
    asyncio.run(analyze_search_results())
```

## 价格监控

### 实时价格跟踪器

```python
import asyncio
from datetime import datetime
from dexscreen import DexscreenerClient, FilterPresets

class PriceTracker:
    def __init__(self):
        self.client = DexscreenerClient()
        self.price_history = []
        self.alert_threshold = 0.05  # 5% 变化

    def handle_price_update(self, pair):
        """处理价格更新"""
        timestamp = datetime.now()
        self.price_history.append({
            'time': timestamp,
            'price': pair.price_usd,
            'volume': pair.volume.h24
        })

        # 保留最后 100 条记录
        if len(self.price_history) > 100:
            self.price_history.pop(0)

        # 检查显著变动
        if len(self.price_history) >= 2:
            prev_price = self.price_history[-2]['price']
            current_price = pair.price_usd
            change = (current_price - prev_price) / prev_price

            if abs(change) >= self.alert_threshold:
                self.send_alert(pair, change)

        # 显示当前状态
        print(f"[{timestamp.strftime('%H:%M:%S')}] "
              f"{pair.base_token.symbol}: ${pair.price_usd:,.4f} "
              f"(24小时: {pair.price_change.h24:+.2f}%)")

    def send_alert(self, pair, change):
        """发送价格警报"""
        direction = "📈" if change > 0 else "📉"
        print(f"\n{direction} 警报: {pair.base_token.symbol} 变动 {change:.2%}!\n")

    async def start_monitoring(self, chain_id, pair_address):
        """开始监控交易对"""
        print(f"开始监控 {chain_id} 上的 {pair_address}")

        await self.client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=[pair_address],
            callback=self.handle_price_update,
            filter=FilterPresets.significant_price_changes(0.001),  # 0.1% 变化
            interval=0.5  # 每 0.5 秒检查
        )

        # 运行 5 分钟
        await asyncio.sleep(300)
        await self.client.close_streams()

        # 显示摘要
        if self.price_history:
            prices = [h['price'] for h in self.price_history]
            print(f"\n会话摘要:")
            print(f"  起始价格: ${prices[0]:,.4f}")
            print(f"  结束价格: ${prices[-1]:,.4f}")
            print(f"  最低价格: ${min(prices):,.4f}")
            print(f"  最高价格: ${max(prices):,.4f}")
            print(f"  价格更新次数: {len(prices)}")

async def main():
    tracker = PriceTracker()
    await tracker.start_monitoring(
        "ethereum",
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # USDC/WETH
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## 套利检测

### 跨链套利扫描器

```python
import asyncio
from collections import defaultdict
from dexscreen import DexscreenerClient

class ArbitrageScanner:
    def __init__(self, spread_threshold=0.01):  # 1% 最小价差
        self.client = DexscreenerClient()
        self.spread_threshold = spread_threshold
        self.prices_by_chain = defaultdict(dict)
        self.opportunities = []

    async def scan_token(self, token_symbol, token_addresses):
        """扫描代币的套利机会"""
        print(f"扫描 {token_symbol} 的套利机会...\n")

        # 并发获取所有链的交易对
        tasks = []
        for chain_id, token_address in token_addresses.items():
            task = self.client.get_pairs_by_token_address_async(chain_id, token_address)
            tasks.append((chain_id, task))

        # 处理结果
        for chain_id, task in tasks:
            try:
                pairs = await task
                if pairs:
                    # 获取流动性最高的交易对
                    best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)

                    if best_pair.price_usd:
                        self.prices_by_chain[token_symbol][chain_id] = {
                            'price': best_pair.price_usd,
                            'pair': best_pair,
                            'liquidity': best_pair.liquidity.usd if best_pair.liquidity else 0
                        }
            except Exception as e:
                print(f"获取 {chain_id} 时出错: {e}")

        # 寻找套利机会
        self.find_opportunities(token_symbol)

    def find_opportunities(self, token_symbol):
        """寻找代币的套利机会"""
        prices = self.prices_by_chain[token_symbol]

        if len(prices) < 2:
            print(f"{token_symbol} 需要至少 2 条链的价格")
            return

        # 找到最低和最高价格
        chains = list(prices.keys())
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                chain1, chain2 = chains[i], chains[j]
                price1 = prices[chain1]['price']
                price2 = prices[chain2]['price']

                # 计算价差
                if price1 > price2:
                    buy_chain, sell_chain = chain2, chain1
                    buy_price, sell_price = price2, price1
                else:
                    buy_chain, sell_chain = chain1, chain2
                    buy_price, sell_price = price1, price2

                spread = (sell_price - buy_price) / buy_price

                if spread >= self.spread_threshold:
                    opportunity = {
                        'token': token_symbol,
                        'buy_chain': buy_chain,
                        'sell_chain': sell_chain,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'spread': spread,
                        'buy_liquidity': prices[buy_chain]['liquidity'],
                        'sell_liquidity': prices[sell_chain]['liquidity']
                    }
                    self.opportunities.append(opportunity)
                    self.print_opportunity(opportunity)

    def print_opportunity(self, opp):
        """打印套利机会"""
        print(f"🎯 套利机会: {opp['token']}")
        print(f"  在 {opp['buy_chain']} 买入: ${opp['buy_price']:,.6f}")
        print(f"  在 {opp['sell_chain']} 卖出: ${opp['sell_price']:,.6f}")
        print(f"  价差: {opp['spread']:.2%}")
        print(f"  买入流动性: ${opp['buy_liquidity']:,.0f}")
        print(f"  卖出流动性: ${opp['sell_liquidity']:,.0f}")
        print()

async def main():
    scanner = ArbitrageScanner(spread_threshold=0.005)  # 0.5% 最小值

    # 定义要扫描的代币（符号 -> 链 -> 地址）
    tokens_to_scan = {
        "USDC": {
            "ethereum": "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "polygon": "2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "arbitrum": "FF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            "optimism": "7F5c764cBc14f9669B88837ca1490cCa17c31607"
        },
        "WETH": {
            "ethereum": "C02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "polygon": "7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
            "arbitrum": "82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "optimism": "4200000000000000000000000000000000000006"
        }
    }

    # 扫描每个代币
    for token_symbol, addresses in tokens_to_scan.items():
        await scanner.scan_token(token_symbol, addresses)
        await asyncio.sleep(1)  # 速率限制

    # 摘要
    print(f"\n找到 {len(scanner.opportunities)} 个套利机会")
    if scanner.opportunities:
        best = max(scanner.opportunities, key=lambda x: x['spread'])
        print(f"最佳机会: {best['token']} 有 {best['spread']:.2%} 价差")

if __name__ == "__main__":
    asyncio.run(main())
```

## 投资组合跟踪

### 多资产投资组合监控器

```python
import asyncio
from datetime import datetime
from typing import Dict, List
from dexscreen import DexscreenerClient, FilterPresets

class PortfolioMonitor:
    def __init__(self):
        self.client = DexscreenerClient()
        self.portfolio = {}  # 地址 -> 持仓信息
        self.portfolio_value = 0
        self.initial_value = 0

    def add_position(self, chain_id: str, pair_address: str, amount: float, entry_price: float):
        """添加持仓到投资组合"""
        self.portfolio[f"{chain_id}:{pair_address}"] = {
            'chain_id': chain_id,
            'pair_address': pair_address,
            'amount': amount,
            'entry_price': entry_price,
            'current_price': entry_price,
            'pnl': 0,
            'pnl_percent': 0
        }
        self.initial_value += amount * entry_price

    def handle_update(self, pair):
        """处理投资组合持仓的价格更新"""
        key = f"{pair.chain_id}:{pair.pair_address}"
        if key in self.portfolio:
            position = self.portfolio[key]
            old_price = position['current_price']
            new_price = pair.price_usd

            # 更新持仓
            position['current_price'] = new_price
            position['pnl'] = (new_price - position['entry_price']) * position['amount']
            position['pnl_percent'] = ((new_price - position['entry_price']) / position['entry_price']) * 100

            # 仅显示显著变化
            if abs(new_price - old_price) / old_price > 0.001:  # 0.1% 变化
                self.display_position_update(pair, position)

    def display_position_update(self, pair, position):
        """显示持仓更新"""
        symbol = pair.base_token.symbol
        pnl_emoji = "🟢" if position['pnl'] >= 0 else "🔴"

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol}: "
              f"${position['current_price']:,.4f} "
              f"{pnl_emoji} 盈亏: ${position['pnl']:+,.2f} ({position['pnl_percent']:+.2f}%)")

    def calculate_portfolio_value(self):
        """计算投资组合总价值"""
        total = sum(p['amount'] * p['current_price'] for p in self.portfolio.values())
        return total

    def display_portfolio_summary(self):
        """显示投资组合摘要"""
        print("\n" + "="*60)
        print("投资组合摘要")
        print("="*60)

        current_value = self.calculate_portfolio_value()
        total_pnl = current_value - self.initial_value
        total_pnl_percent = (total_pnl / self.initial_value) * 100 if self.initial_value > 0 else 0

        print(f"初始价值: ${self.initial_value:,.2f}")
        print(f"当前价值: ${current_value:,.2f}")
        print(f"总盈亏: ${total_pnl:+,.2f} ({total_pnl_percent:+.2f}%)")
        print("\n持仓:")

        for key, position in self.portfolio.items():
            value = position['amount'] * position['current_price']
            weight = (value / current_value) * 100 if current_value > 0 else 0
            print(f"  {key}: ${value:,.2f} ({weight:.1f}%) "
                  f"盈亏: ${position['pnl']:+,.2f} ({position['pnl_percent']:+.2f}%)")

        print("="*60)

    async def start_monitoring(self):
        """开始监控所有投资组合持仓"""
        print("开始投资组合监控...")

        # 订阅所有持仓
        for key, position in self.portfolio.items():
            await self.client.subscribe_pairs(
                chain_id=position['chain_id'],
                pair_addresses=[position['pair_address']],
                callback=self.handle_update,
                filter=FilterPresets.ui_friendly(),  # 为 UI 平衡更新
                interval=1.0
            )

        # 运行 5 分钟并定期显示摘要
        for i in range(5):
            await asyncio.sleep(60)
            self.display_portfolio_summary()

        await self.client.close_streams()

async def main():
    monitor = PortfolioMonitor()

    # 示例投资组合
    monitor.add_position(
        "ethereum",
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # USDC/WETH
        1000,  # 1000 USDC
        0.0004  # 入场价格
    )

    monitor.add_position(
        "ethereum",
        "0x11b815efb8f581194ae79006d24e0d814b7697f6",  # WETH/USDT
        0.5,  # 0.5 WETH
        2500  # 入场价格
    )

    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

## 新代币发现

### 代币发布监控器

```python
import asyncio
from datetime import datetime, timedelta
from dexscreen import DexscreenerClient

class TokenLaunchMonitor:
    def __init__(self):
        self.client = DexscreenerClient()
        self.new_tokens = []
        self.monitored_tokens = set()

    async def scan_new_tokens(self):
        """扫描新发布的代币"""
        print("扫描新代币发布...\n")

        # 获取最新代币档案
        profiles = await self.client.get_latest_token_profiles_async()

        for token in profiles:
            if token.token_address not in self.monitored_tokens:
                # 获取交易对数据
                pairs = await self.client.get_pairs_by_token_address_async(
                    token.chain_id,
                    token.token_address
                )

                if pairs:
                    # 分析代币
                    analysis = await self.analyze_new_token(token, pairs)
                    if analysis['is_interesting']:
                        self.new_tokens.append(analysis)
                        self.print_token_alert(analysis)

                self.monitored_tokens.add(token.token_address)
                await asyncio.sleep(0.5)  # 速率限制

    async def analyze_new_token(self, token_info, pairs):
        """分析新代币的潜力"""
        # 获取流动性最高的交易对
        best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)

        # 计算指标
        total_liquidity = sum(p.liquidity.usd for p in pairs if p.liquidity and p.liquidity.usd)
        total_volume = sum(p.volume.h24 for p in pairs if p.volume.h24)
        pair_count = len(pairs)

        # 检查是否最近创建（24小时内）
        is_new = False
        if best_pair.pair_created_at:
            age = datetime.now() - best_pair.pair_created_at
            is_new = age < timedelta(days=1)

        # 判断是否有趣
        is_interesting = (
            total_liquidity > 50_000 and  # 最低 $50k 流动性
            total_volume > 100_000 and     # 最低 $100k 交易量
            pair_count >= 2                # 至少 2 个交易对
        )

        return {
            'token_info': token_info,
            'best_pair': best_pair,
            'total_liquidity': total_liquidity,
            'total_volume': total_volume,
            'pair_count': pair_count,
            'is_new': is_new,
            'is_interesting': is_interesting,
            'price': best_pair.price_usd,
            'price_change_24h': best_pair.price_change.h24
        }

    def print_token_alert(self, analysis):
        """打印有趣代币的警报"""
        token = analysis['token_info']

        print(f"🚀 新代币警报: {token.token_address}")
        print(f"  链: {token.chain_id}")
        print(f"  价格: ${analysis['price']:,.8f}")
        print(f"  24小时变化: {analysis['price_change_24h']:+.2f}%")
        print(f"  总流动性: ${analysis['total_liquidity']:,.0f}")
        print(f"  24小时交易量: ${analysis['total_volume']:,.0f}")
        print(f"  交易对数量: {analysis['pair_count']}")

        if token.description:
            print(f"  描述: {token.description[:100]}...")

        print(f"  URL: {token.url}")
        print()

    async def monitor_launches(self, duration_minutes=30):
        """监控新发布指定时长"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)

        print(f"监控新代币发布 {duration_minutes} 分钟...")
        print(f"开始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"结束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        while datetime.now() < end_time:
            await self.scan_new_tokens()

            # 等待下次扫描
            await asyncio.sleep(60)  # 每分钟扫描

        # 最终摘要
        print(f"\n监控完成。找到 {len(self.new_tokens)} 个有趣的代币:")
        for token in self.new_tokens:
            print(f"- {token['token_info'].token_address} 在 {token['token_info'].chain_id}")

async def main():
    monitor = TokenLaunchMonitor()
    await monitor.monitor_launches(duration_minutes=5)

if __name__ == "__main__":
    asyncio.run(main())
```

## 交易量分析

### 交易量激增检测器

```python
import asyncio
from collections import defaultdict, deque
from dexscreen import DexscreenerClient, FilterConfig

class VolumeSurgeDetector:
    def __init__(self, surge_multiplier=3.0):
        self.client = DexscreenerClient()
        self.surge_multiplier = surge_multiplier
        self.volume_history = defaultdict(lambda: deque(maxlen=12))  # 12 x 5分钟 = 1小时
        self.surge_alerts = []

    def calculate_volume_surge(self, pair):
        """计算是否有交易量激增"""
        history = self.volume_history[pair.pair_address]
        current_volume = pair.volume.m5 or 0

        # 添加到历史
        history.append(current_volume)

        if len(history) < 6:  # 需要至少 30 分钟的数据
            return None

        # 比较最近和之前的交易量
        recent_avg = sum(list(history)[-3:]) / 3  # 最后 15 分钟
        older_avg = sum(list(history)[-6:-3]) / 3  # 之前 15 分钟

        if older_avg > 0:
            surge_ratio = recent_avg / older_avg
            if surge_ratio >= self.surge_multiplier:
                return surge_ratio

        return None

    def handle_volume_update(self, pair):
        """处理交易量更新"""
        surge = self.calculate_volume_surge(pair)

        if surge:
            alert = {
                'timestamp': datetime.now(),
                'pair': pair,
                'surge_ratio': surge,
                '5m_volume': pair.volume.m5,
                '24h_volume': pair.volume.h24
            }
            self.surge_alerts.append(alert)
            self.print_surge_alert(alert)

    def print_surge_alert(self, alert):
        """打印交易量激增警报"""
        pair = alert['pair']
        print(f"\n🔊 检测到交易量激增 于 {alert['timestamp'].strftime('%H:%M:%S')}")
        print(f"  交易对: {pair.base_token.symbol}/{pair.quote_token.symbol} 在 {pair.chain_id}")
        print(f"  激增: {alert['surge_ratio']:.1f}x 正常交易量")
        print(f"  5分钟交易量: ${alert['5m_volume']:,.0f}")
        print(f"  24小时交易量: ${alert['24h_volume']:,.0f}")
        print(f"  当前价格: ${pair.price_usd:,.6f}")
        print(f"  1小时价格变化: {pair.price_change.h1:+.2f}%")
        print()

    async def monitor_tokens(self, chain_id, token_addresses):
        """监控代币的交易量激增"""
        print(f"监控 {chain_id} 上 {len(token_addresses)} 个代币的交易量激增...\n")

        # 获取每个代币的初始交易对
        all_pairs = []
        for token_address in token_addresses:
            pairs = await self.client.get_pairs_by_token_address_async(chain_id, token_address)
            # 获取每个代币流动性最高的前 3 个交易对
            liquid_pairs = sorted(
                [p for p in pairs if p.liquidity and p.liquidity.usd > 10_000],
                key=lambda p: p.liquidity.usd,
                reverse=True
            )[:3]
            all_pairs.extend(liquid_pairs)

        print(f"总共监控 {len(all_pairs)} 个交易对\n")

        # 订阅交易量更新
        pair_addresses = [p.pair_address for p in all_pairs]

        filter_config = FilterConfig(
            change_fields=["volume.m5", "volume.h1"],
            volume_change_threshold=0.10  # 10% 交易量变化
        )

        await self.client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=pair_addresses,
            callback=self.handle_volume_update,
            filter=filter_config,
            interval=1.0
        )

        # 监控 10 分钟
        await asyncio.sleep(600)
        await self.client.close_streams()

        # 摘要
        print(f"\n检测到 {len(self.surge_alerts)} 次交易量激增")
        if self.surge_alerts:
            biggest_surge = max(self.surge_alerts, key=lambda x: x['surge_ratio'])
            print(f"最大激增: {biggest_surge['surge_ratio']:.1f}x 在 "
                  f"{biggest_surge['pair'].base_token.symbol}")

async def main():
    detector = VolumeSurgeDetector(surge_multiplier=2.5)  # 2.5x 激增阈值

    # 监控以太坊上的热门代币
    await detector.monitor_tokens(
        "ethereum",
        [
            "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
            "C02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
            "6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
            "dAC17F958D2ee523a2206206994597C13D831ec7"   # USDT
        ]
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## 流动性监控

### 流动性变化跟踪器

```python
import asyncio
from datetime import datetime
from dexscreen import DexscreenerClient, FilterConfig

class LiquidityTracker:
    def __init__(self):
        self.client = DexscreenerClient()
        self.liquidity_snapshots = {}
        self.significant_changes = []

    def handle_liquidity_update(self, pair):
        """处理流动性更新"""
        if not pair.liquidity or not pair.liquidity.usd:
            return

        key = f"{pair.chain_id}:{pair.pair_address}"
        current_liquidity = pair.liquidity.usd

        # 检查显著变化
        if key in self.liquidity_snapshots:
            prev_liquidity = self.liquidity_snapshots[key]['liquidity']
            change = (current_liquidity - prev_liquidity) / prev_liquidity

            if abs(change) > 0.1:  # 10% 变化
                event = {
                    'timestamp': datetime.now(),
                    'pair': pair,
                    'prev_liquidity': prev_liquidity,
                    'current_liquidity': current_liquidity,
                    'change_percent': change * 100,
                    'type': '增加' if change > 0 else '移除'
                }
                self.significant_changes.append(event)
                self.print_liquidity_event(event)

        # 更新快照
        self.liquidity_snapshots[key] = {
            'liquidity': current_liquidity,
            'timestamp': datetime.now(),
            'pair': pair
        }

    def print_liquidity_event(self, event):
        """打印流动性变化事件"""
        pair = event['pair']
        emoji = "💰" if event['type'] == '增加' else "💸"

        print(f"\n{emoji} 流动性{event['type']}")
        print(f"  时间: {event['timestamp'].strftime('%H:%M:%S')}")
        print(f"  交易对: {pair.base_token.symbol}/{pair.quote_token.symbol} 在 {pair.dex_id}")
        print(f"  之前: ${event['prev_liquidity']:,.0f}")
        print(f"  当前: ${event['current_liquidity']:,.0f}")
        print(f"  变化: {event['change_percent']:+.1f}%")
        print(f"  价格影响: 当前价格 ${pair.price_usd:,.6f}")
        print()

    async def monitor_liquidity_changes(self, pairs_to_monitor):
        """监控特定交易对的流动性变化"""
        print(f"监控 {len(pairs_to_monitor)} 个交易对的流动性...\n")

        # 按链分组
        by_chain = defaultdict(list)
        for chain_id, pair_address in pairs_to_monitor:
            by_chain[chain_id].append(pair_address)

        # 订阅每条链
        for chain_id, addresses in by_chain.items():
            filter_config = FilterConfig(
                change_fields=["liquidity.usd", "liquidity.base", "liquidity.quote"],
                liquidity_change_threshold=0.05,  # 5% 变化阈值
                max_updates_per_second=1.0
            )

            await self.client.subscribe_pairs(
                chain_id=chain_id,
                pair_addresses=addresses,
                callback=self.handle_liquidity_update,
                filter=filter_config,
                interval=2.0
            )

        # 监控 10 分钟
        await asyncio.sleep(600)
        await self.client.close_streams()

        # 摘要
        self.print_summary()

    def print_summary(self):
        """打印监控摘要"""
        print("\n" + "="*60)
        print("流动性监控摘要")
        print("="*60)

        if not self.significant_changes:
            print("未检测到显著的流动性变化")
            return

        # 计算统计数据
        additions = [e for e in self.significant_changes if e['type'] == '增加']
        removals = [e for e in self.significant_changes if e['type'] == '移除']

        print(f"总事件数: {len(self.significant_changes)}")
        print(f"流动性增加: {len(additions)}")
        print(f"流动性移除: {len(removals)}")

        if additions:
            biggest_add = max(additions, key=lambda x: x['change_percent'])
            print(f"\n最大增加: {biggest_add['change_percent']:+.1f}% 在 "
                  f"{biggest_add['pair'].base_token.symbol}")

        if removals:
            biggest_remove = min(removals, key=lambda x: x['change_percent'])
            print(f"最大移除: {biggest_remove['change_percent']:+.1f}% 在 "
                  f"{biggest_remove['pair'].base_token.symbol}")

        print("="*60)

async def main():
    tracker = LiquidityTracker()

    # 监控主要交易对
    pairs_to_monitor = [
        ("ethereum", "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"),  # USDC/WETH Uniswap V3
        ("ethereum", "0x11b815efb8f581194ae79006d24e0d814b7697f6"),  # WETH/USDT Uniswap V3
        ("ethereum", "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36"),  # WETH/USDT Uniswap V3
        ("bsc", "0x7213a321f1855cf1779f42c0cd85d3d95291d34c"),        # USDT/USDC PancakeSwap
        ("polygon", "0x45dda9cb7c25131df268515131f647d726f50608"),     # USDC/WETH QuickSwap
    ]

    await tracker.monitor_liquidity_changes(pairs_to_monitor)

if __name__ == "__main__":
    asyncio.run(main())
```

## 警报系统

### 综合警报系统

```python
import asyncio
from datetime import datetime
from enum import Enum
from typing import List, Dict, Callable
from dexscreen import DexscreenerClient, FilterConfig

class AlertType(Enum):
    PRICE_INCREASE = "价格上涨"
    PRICE_DECREASE = "价格下跌"
    VOLUME_SURGE = "交易量激增"
    LIQUIDITY_CHANGE = "流动性变化"
    NEW_ATH = "新高"
    LARGE_TRANSACTION = "大额交易"

class AlertSystem:
    def __init__(self):
        self.client = DexscreenerClient()
        self.alerts: List[Dict] = []
        self.alert_handlers: Dict[AlertType, List[Callable]] = defaultdict(list)
        self.price_history = defaultdict(list)
        self.ath_tracker = {}

    def register_handler(self, alert_type: AlertType, handler: Callable):
        """为特定警报类型注册处理器"""
        self.alert_handlers[alert_type].append(handler)

    def create_alert(self, alert_type: AlertType, pair, data: Dict):
        """创建并分发警报"""
        alert = {
            'type': alert_type,
            'timestamp': datetime.now(),
            'pair': pair,
            'chain_id': pair.chain_id,
            'symbol': pair.base_token.symbol,
            'data': data
        }

        self.alerts.append(alert)

        # 分发给处理器
        for handler in self.alert_handlers[alert_type]:
            try:
                handler(alert)
            except Exception as e:
                print(f"警报处理器错误: {e}")

    def check_price_alerts(self, pair):
        """检查基于价格的警报"""
        key = f"{pair.chain_id}:{pair.pair_address}"

        # 跟踪价格历史
        self.price_history[key].append(pair.price_usd)
        if len(self.price_history[key]) > 100:
            self.price_history[key].pop(0)

        # 检查新高
        if key not in self.ath_tracker or pair.price_usd > self.ath_tracker[key]:
            if key in self.ath_tracker:  # 不是第一次
                self.create_alert(AlertType.NEW_ATH, pair, {
                    'new_ath': pair.price_usd,
                    'previous_ath': self.ath_tracker[key],
                    'increase': ((pair.price_usd - self.ath_tracker[key]) / self.ath_tracker[key]) * 100
                })
            self.ath_tracker[key] = pair.price_usd

        # 检查最近价格变化
        if len(self.price_history[key]) >= 2:
            recent_change = (pair.price_usd - self.price_history[key][-2]) / self.price_history[key][-2]

            if recent_change > 0.05:  # 5% 上涨
                self.create_alert(AlertType.PRICE_INCREASE, pair, {
                    'change_percent': recent_change * 100,
                    'current_price': pair.price_usd
                })
            elif recent_change < -0.05:  # 5% 下跌
                self.create_alert(AlertType.PRICE_DECREASE, pair, {
                    'change_percent': recent_change * 100,
                    'current_price': pair.price_usd
                })

    def check_volume_alerts(self, pair):
        """检查基于交易量的警报"""
        # 交易量激增检测
        if pair.volume.m5 and pair.volume.h1:
            hourly_avg_5min = pair.volume.h1 / 12  # 过去一小时的平均5分钟交易量
            if pair.volume.m5 > hourly_avg_5min * 3:  # 3倍平均值
                self.create_alert(AlertType.VOLUME_SURGE, pair, {
                    'current_5m_volume': pair.volume.m5,
                    'average_5m_volume': hourly_avg_5min,
                    'surge_multiplier': pair.volume.m5 / hourly_avg_5min
                })

    def check_liquidity_alerts(self, pair):
        """检查流动性变化"""
        if pair.liquidity and pair.liquidity.usd:
            # 这需要历史数据来比较
            # 为演示，我们检查流动性是否非常低
            if pair.liquidity.usd < 50_000:
                self.create_alert(AlertType.LIQUIDITY_CHANGE, pair, {
                    'current_liquidity': pair.liquidity.usd,
                    'warning': '检测到低流动性'
                })

    def comprehensive_check(self, pair):
        """运行所有警报检查"""
        self.check_price_alerts(pair)
        self.check_volume_alerts(pair)
        self.check_liquidity_alerts(pair)

    async def monitor_with_alerts(self, chain_id: str, pair_addresses: List[str]):
        """使用综合警报监控交易对"""
        print(f"为 {chain_id} 上的 {len(pair_addresses)} 个交易对启动警报系统\n")

        # 配置过滤以获取相关变化
        filter_config = FilterConfig(
            change_fields=["price_usd", "volume.m5", "volume.h1", "liquidity.usd"],
            price_change_threshold=0.001,  # 0.1% 高灵敏度
            volume_change_threshold=0.10,   # 10% 交易量变化
            max_updates_per_second=2.0
        )

        await self.client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=pair_addresses,
            callback=self.comprehensive_check,
            filter=filter_config,
            interval=0.5
        )

        # 运行指定时长
        await asyncio.sleep(300)  # 5 分钟
        await self.client.close_streams()

        # 打印摘要
        self.print_alert_summary()

    def print_alert_summary(self):
        """打印所有警报的摘要"""
        print("\n" + "="*60)
        print("警报摘要")
        print("="*60)

        if not self.alerts:
            print("没有触发警报")
            return

        # 按类型分组
        by_type = defaultdict(list)
        for alert in self.alerts:
            by_type[alert['type']].append(alert)

        for alert_type, alerts in by_type.items():
            print(f"\n{alert_type.value.upper()}: {len(alerts)} 个警报")

            # 显示该类型的最后 3 个警报
            for alert in alerts[-3:]:
                print(f"  [{alert['timestamp'].strftime('%H:%M:%S')}] "
                      f"{alert['symbol']} 在 {alert['chain_id']}")

                # 特定类型的详情
                if alert_type == AlertType.PRICE_INCREASE:
                    print(f"    +{alert['data']['change_percent']:.2f}% "
                          f"到 ${alert['data']['current_price']:,.6f}")
                elif alert_type == AlertType.VOLUME_SURGE:
                    print(f"    {alert['data']['surge_multiplier']:.1f}x 正常交易量")
                elif alert_type == AlertType.NEW_ATH:
                    print(f"    新高: ${alert['data']['new_ath']:,.6f} "
                          f"(+{alert['data']['increase']:.2f}%)")

# 示例处理器
def console_handler(alert: Dict):
    """将警报打印到控制台"""
    emoji_map = {
        AlertType.PRICE_INCREASE: "📈",
        AlertType.PRICE_DECREASE: "📉",
        AlertType.VOLUME_SURGE: "🔊",
        AlertType.LIQUIDITY_CHANGE: "💧",
        AlertType.NEW_ATH: "🚀",
        AlertType.LARGE_TRANSACTION: "🐋"
    }

    emoji = emoji_map.get(alert['type'], "📢")
    print(f"\n{emoji} 警报: {alert['type'].value} - {alert['symbol']} "
          f"于 {alert['timestamp'].strftime('%H:%M:%S')}")

async def main():
    alert_system = AlertSystem()

    # 注册处理器
    alert_system.register_handler(AlertType.PRICE_INCREASE, console_handler)
    alert_system.register_handler(AlertType.PRICE_DECREASE, console_handler)
    alert_system.register_handler(AlertType.VOLUME_SURGE, console_handler)
    alert_system.register_handler(AlertType.NEW_ATH, console_handler)

    # 监控一些活跃的交易对
    await alert_system.monitor_with_alerts(
        "ethereum",
        [
            "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # USDC/WETH
            "0x11b815efb8f581194ae79006d24e0d814b7697f6",  # WETH/USDT
            "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36"   # WETH/USDT
        ]
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## 下一步

这些示例展示了 Dexscreen 的各种用例。您可以：

1. **组合示例** - 混合监控与警报，添加数据库存储等
2. **扩展功能** - 添加通知、Web 界面、交易机器人集成
3. **优化性能** - 使用异步操作、批量请求、智能过滤
4. **扩展规模** - 监控更多交易对，实现分布式系统

更多详情，请参见：

- [入门指南](getting-started.zh.md) - 安装和基础知识
- [查询 API](api/query-api.zh.md) - 所有查询方法
- [流式 API](api/streaming-api.zh.md) - 实时订阅
- [过滤](api/filtering.zh.md) - 高级过滤选项
