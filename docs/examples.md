# Complete Examples

This page contains complete, working examples for common use cases with Dexscreen.

## Basic Usage

### Simple Price Check

```python
from dexscreen import DexscreenerClient

def check_token_price():
    client = DexscreenerClient()

    # Get pairs for a token
    pairs = client.get_pairs_by_token_address(
        "ethereum",
        "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
    )

    if pairs:
        # Find the most liquid pair
        best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)
        print(f"Most liquid USDC pair: {best_pair.base_token.symbol}/{best_pair.quote_token.symbol}")
        print(f"DEX: {best_pair.dex_id}")
        print(f"Price: ${best_pair.price_usd:,.4f}")
        print(f"Liquidity: ${best_pair.liquidity.usd:,.0f}")

if __name__ == "__main__":
    check_token_price()
```

### Search and Analyze

```python
import asyncio
from dexscreen import DexscreenerClient

async def analyze_search_results():
    client = DexscreenerClient()

    # Search for PEPE tokens
    results = await client.search_pairs_async("PEPE")

    # Filter and sort by liquidity
    liquid_pairs = [p for p in results if p.liquidity and p.liquidity.usd > 50_000]
    liquid_pairs.sort(key=lambda p: p.liquidity.usd, reverse=True)

    print(f"Found {len(liquid_pairs)} liquid PEPE pairs\n")

    for pair in liquid_pairs[:5]:
        print(f"{pair.chain_id} - {pair.dex_id}")
        print(f"  Pair: {pair.base_token.symbol}/{pair.quote_token.symbol}")
        print(f"  Price: ${pair.price_usd:,.8f}")
        print(f"  24h Volume: ${pair.volume.h24:,.0f}")
        print(f"  Liquidity: ${pair.liquidity.usd:,.0f}")
        print(f"  24h Change: {pair.price_change.h24:+.2f}%")
        print()

if __name__ == "__main__":
    asyncio.run(analyze_search_results())
```

## Price Monitoring

### Real-time Price Tracker

```python
import asyncio
from datetime import datetime
from dexscreen import DexscreenerClient, FilterPresets

class PriceTracker:
    def __init__(self):
        self.client = DexscreenerClient()
        self.price_history = []
        self.alert_threshold = 0.05  # 5% change

    def handle_price_update(self, pair):
        """Process price updates"""
        timestamp = datetime.now()
        self.price_history.append({
            'time': timestamp,
            'price': pair.price_usd,
            'volume': pair.volume.h24
        })

        # Keep last 100 entries
        if len(self.price_history) > 100:
            self.price_history.pop(0)

        # Check for significant moves
        if len(self.price_history) >= 2:
            prev_price = self.price_history[-2]['price']
            current_price = pair.price_usd
            change = (current_price - prev_price) / prev_price

            if abs(change) >= self.alert_threshold:
                self.send_alert(pair, change)

        # Display current status
        print(f"[{timestamp.strftime('%H:%M:%S')}] "
              f"{pair.base_token.symbol}: ${pair.price_usd:,.4f} "
              f"(24h: {pair.price_change.h24:+.2f}%)")

    def send_alert(self, pair, change):
        """Send price alert"""
        direction = "📈" if change > 0 else "📉"
        print(f"\n{direction} ALERT: {pair.base_token.symbol} moved {change:.2%}!\n")

    async def start_monitoring(self, chain_id, pair_address):
        """Start monitoring a pair"""
        print(f"Starting price monitor for {pair_address} on {chain_id}")

        await self.client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=[pair_address],
            callback=self.handle_price_update,
            filter=FilterPresets.significant_price_changes(0.001),  # 0.1% changes
            interval=0.5  # Check every 0.5 seconds
        )

        # Run for 5 minutes
        await asyncio.sleep(300)
        await self.client.close_streams()

        # Show summary
        if self.price_history:
            prices = [h['price'] for h in self.price_history]
            print(f"\nSession Summary:")
            print(f"  Starting Price: ${prices[0]:,.4f}")
            print(f"  Ending Price: ${prices[-1]:,.4f}")
            print(f"  Min Price: ${min(prices):,.4f}")
            print(f"  Max Price: ${max(prices):,.4f}")
            print(f"  Price Updates: {len(prices)}")

async def main():
    tracker = PriceTracker()
    await tracker.start_monitoring(
        "ethereum",
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # USDC/WETH
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## Arbitrage Detection

### Cross-Chain Arbitrage Scanner

```python
import asyncio
from collections import defaultdict
from dexscreen import DexscreenerClient

class ArbitrageScanner:
    def __init__(self, spread_threshold=0.01):  # 1% minimum spread
        self.client = DexscreenerClient()
        self.spread_threshold = spread_threshold
        self.prices_by_chain = defaultdict(dict)
        self.opportunities = []

    async def scan_token(self, token_symbol, token_addresses):
        """Scan a token across multiple chains"""
        print(f"Scanning {token_symbol} for arbitrage opportunities...\n")

        # Fetch pairs from all chains concurrently
        tasks = []
        for chain_id, token_address in token_addresses.items():
            task = self.client.get_pairs_by_token_address_async(chain_id, token_address)
            tasks.append((chain_id, task))

        # Process results
        for chain_id, task in tasks:
            try:
                pairs = await task
                if pairs:
                    # Get the most liquid pair
                    best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)

                    if best_pair.price_usd:
                        self.prices_by_chain[token_symbol][chain_id] = {
                            'price': best_pair.price_usd,
                            'pair': best_pair,
                            'liquidity': best_pair.liquidity.usd if best_pair.liquidity else 0
                        }
            except Exception as e:
                print(f"Error fetching {chain_id}: {e}")

        # Find arbitrage opportunities
        self.find_opportunities(token_symbol)

    def find_opportunities(self, token_symbol):
        """Find arbitrage opportunities for a token"""
        prices = self.prices_by_chain[token_symbol]

        if len(prices) < 2:
            print(f"Need at least 2 chains with prices for {token_symbol}")
            return

        # Find min and max prices
        chains = list(prices.keys())
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                chain1, chain2 = chains[i], chains[j]
                price1 = prices[chain1]['price']
                price2 = prices[chain2]['price']

                # Calculate spread
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
        """Print arbitrage opportunity"""
        print(f"🎯 ARBITRAGE OPPORTUNITY: {opp['token']}")
        print(f"  Buy on {opp['buy_chain']}: ${opp['buy_price']:,.6f}")
        print(f"  Sell on {opp['sell_chain']}: ${opp['sell_price']:,.6f}")
        print(f"  Spread: {opp['spread']:.2%}")
        print(f"  Buy Liquidity: ${opp['buy_liquidity']:,.0f}")
        print(f"  Sell Liquidity: ${opp['sell_liquidity']:,.0f}")
        print()

async def main():
    scanner = ArbitrageScanner(spread_threshold=0.005)  # 0.5% minimum

    # Define tokens to scan (symbol -> chain -> address)
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

    # Scan each token
    for token_symbol, addresses in tokens_to_scan.items():
        await scanner.scan_token(token_symbol, addresses)
        await asyncio.sleep(1)  # Rate limiting

    # Summary
    print(f"\nFound {len(scanner.opportunities)} arbitrage opportunities")
    if scanner.opportunities:
        best = max(scanner.opportunities, key=lambda x: x['spread'])
        print(f"Best opportunity: {best['token']} with {best['spread']:.2%} spread")

if __name__ == "__main__":
    asyncio.run(main())
```

## Portfolio Tracking

### Multi-Asset Portfolio Monitor

```python
import asyncio
from datetime import datetime
from typing import Dict, List
from dexscreen import DexscreenerClient, FilterPresets

class PortfolioMonitor:
    def __init__(self):
        self.client = DexscreenerClient()
        self.portfolio = {}  # address -> position info
        self.portfolio_value = 0
        self.initial_value = 0

    def add_position(self, chain_id: str, pair_address: str, amount: float, entry_price: float):
        """Add a position to the portfolio"""
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
        """Handle price updates for portfolio positions"""
        key = f"{pair.chain_id}:{pair.pair_address}"
        if key in self.portfolio:
            position = self.portfolio[key]
            old_price = position['current_price']
            new_price = pair.price_usd

            # Update position
            position['current_price'] = new_price
            position['pnl'] = (new_price - position['entry_price']) * position['amount']
            position['pnl_percent'] = ((new_price - position['entry_price']) / position['entry_price']) * 100

            # Only show significant changes
            if abs(new_price - old_price) / old_price > 0.001:  # 0.1% change
                self.display_position_update(pair, position)

    def display_position_update(self, pair, position):
        """Display position update"""
        symbol = pair.base_token.symbol
        pnl_emoji = "🟢" if position['pnl'] >= 0 else "🔴"

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol}: "
              f"${position['current_price']:,.4f} "
              f"{pnl_emoji} P&L: ${position['pnl']:+,.2f} ({position['pnl_percent']:+.2f}%)")

    def calculate_portfolio_value(self):
        """Calculate total portfolio value"""
        total = sum(p['amount'] * p['current_price'] for p in self.portfolio.values())
        return total

    def display_portfolio_summary(self):
        """Display portfolio summary"""
        print("\n" + "="*60)
        print("PORTFOLIO SUMMARY")
        print("="*60)

        current_value = self.calculate_portfolio_value()
        total_pnl = current_value - self.initial_value
        total_pnl_percent = (total_pnl / self.initial_value) * 100 if self.initial_value > 0 else 0

        print(f"Initial Value: ${self.initial_value:,.2f}")
        print(f"Current Value: ${current_value:,.2f}")
        print(f"Total P&L: ${total_pnl:+,.2f} ({total_pnl_percent:+.2f}%)")
        print("\nPositions:")

        for key, position in self.portfolio.items():
            value = position['amount'] * position['current_price']
            weight = (value / current_value) * 100 if current_value > 0 else 0
            print(f"  {key}: ${value:,.2f} ({weight:.1f}%) "
                  f"P&L: ${position['pnl']:+,.2f} ({position['pnl_percent']:+.2f}%)")

        print("="*60)

    async def start_monitoring(self):
        """Start monitoring all portfolio positions"""
        print("Starting portfolio monitor...")

        # Subscribe to all positions
        for key, position in self.portfolio.items():
            await self.client.subscribe_pairs(
                chain_id=position['chain_id'],
                pair_addresses=[position['pair_address']],
                callback=self.handle_update,
                filter=FilterPresets.ui_friendly(),  # Balanced updates for UI
                interval=1.0
            )

        # Run for 5 minutes with periodic summaries
        for i in range(5):
            await asyncio.sleep(60)
            self.display_portfolio_summary()

        await self.client.close_streams()

async def main():
    monitor = PortfolioMonitor()

    # Example portfolio
    monitor.add_position(
        "ethereum",
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # USDC/WETH
        1000,  # 1000 USDC
        0.0004  # Entry price
    )

    monitor.add_position(
        "ethereum",
        "0x11b815efb8f581194ae79006d24e0d814b7697f6",  # WETH/USDT
        0.5,  # 0.5 WETH
        2500  # Entry price
    )

    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

## New Token Discovery

### Token Launch Monitor

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
        """Scan for newly launched tokens"""
        print("Scanning for new token launches...\n")

        # Get latest token profiles
        profiles = await self.client.get_latest_token_profiles_async()

        for token in profiles:
            if token.token_address not in self.monitored_tokens:
                # Get pair data
                pairs = await self.client.get_pairs_by_token_address_async(
                    token.chain_id,
                    token.token_address
                )

                if pairs:
                    # Analyze the token
                    analysis = await self.analyze_new_token(token, pairs)
                    if analysis['is_interesting']:
                        self.new_tokens.append(analysis)
                        self.print_token_alert(analysis)

                self.monitored_tokens.add(token.token_address)
                await asyncio.sleep(0.5)  # Rate limiting

    async def analyze_new_token(self, token_info, pairs):
        """Analyze a new token for potential"""
        # Get the most liquid pair
        best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity else 0)

        # Calculate metrics
        total_liquidity = sum(p.liquidity.usd for p in pairs if p.liquidity and p.liquidity.usd)
        total_volume = sum(p.volume.h24 for p in pairs if p.volume.h24)
        pair_count = len(pairs)

        # Check if created recently (within 24 hours)
        is_new = False
        if best_pair.pair_created_at:
            age = datetime.now() - best_pair.pair_created_at
            is_new = age < timedelta(days=1)

        # Determine if interesting
        is_interesting = (
            total_liquidity > 50_000 and  # Minimum $50k liquidity
            total_volume > 100_000 and     # Minimum $100k volume
            pair_count >= 2                # At least 2 pairs
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
        """Print alert for interesting token"""
        token = analysis['token_info']

        print(f"🚀 NEW TOKEN ALERT: {token.token_address}")
        print(f"  Chain: {token.chain_id}")
        print(f"  Price: ${analysis['price']:,.8f}")
        print(f"  24h Change: {analysis['price_change_24h']:+.2f}%")
        print(f"  Total Liquidity: ${analysis['total_liquidity']:,.0f}")
        print(f"  24h Volume: ${analysis['total_volume']:,.0f}")
        print(f"  Number of Pairs: {analysis['pair_count']}")

        if token.description:
            print(f"  Description: {token.description[:100]}...")

        print(f"  URL: {token.url}")
        print()

    async def monitor_launches(self, duration_minutes=30):
        """Monitor for new launches for specified duration"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)

        print(f"Monitoring new token launches for {duration_minutes} minutes...")
        print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        while datetime.now() < end_time:
            await self.scan_new_tokens()

            # Wait before next scan
            await asyncio.sleep(60)  # Scan every minute

        # Final summary
        print(f"\nMonitoring complete. Found {len(self.new_tokens)} interesting tokens:")
        for token in self.new_tokens:
            print(f"- {token['token_info'].token_address} on {token['token_info'].chain_id}")

async def main():
    monitor = TokenLaunchMonitor()
    await monitor.monitor_launches(duration_minutes=5)

if __name__ == "__main__":
    asyncio.run(main())
```

## Volume Analysis

### Volume Surge Detector

```python
import asyncio
from collections import defaultdict, deque
from dexscreen import DexscreenerClient, FilterConfig

class VolumeSurgeDetector:
    def __init__(self, surge_multiplier=3.0):
        self.client = DexscreenerClient()
        self.surge_multiplier = surge_multiplier
        self.volume_history = defaultdict(lambda: deque(maxlen=12))  # 12 x 5min = 1 hour
        self.surge_alerts = []

    def calculate_volume_surge(self, pair):
        """Calculate if there's a volume surge"""
        history = self.volume_history[pair.pair_address]
        current_volume = pair.volume.m5 or 0

        # Add to history
        history.append(current_volume)

        if len(history) < 6:  # Need at least 30 minutes of data
            return None

        # Compare recent vs older volume
        recent_avg = sum(list(history)[-3:]) / 3  # Last 15 minutes
        older_avg = sum(list(history)[-6:-3]) / 3  # Previous 15 minutes

        if older_avg > 0:
            surge_ratio = recent_avg / older_avg
            if surge_ratio >= self.surge_multiplier:
                return surge_ratio

        return None

    def handle_volume_update(self, pair):
        """Process volume updates"""
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
        """Print volume surge alert"""
        pair = alert['pair']
        print(f"\n🔊 VOLUME SURGE DETECTED at {alert['timestamp'].strftime('%H:%M:%S')}")
        print(f"  Pair: {pair.base_token.symbol}/{pair.quote_token.symbol} on {pair.chain_id}")
        print(f"  Surge: {alert['surge_ratio']:.1f}x normal volume")
        print(f"  5min Volume: ${alert['5m_volume']:,.0f}")
        print(f"  24h Volume: ${alert['24h_volume']:,.0f}")
        print(f"  Current Price: ${pair.price_usd:,.6f}")
        print(f"  Price Change 1h: {pair.price_change.h1:+.2f}%")
        print()

    async def monitor_tokens(self, chain_id, token_addresses):
        """Monitor tokens for volume surges"""
        print(f"Monitoring {len(token_addresses)} tokens on {chain_id} for volume surges...\n")

        # Get initial pairs for each token
        all_pairs = []
        for token_address in token_addresses:
            pairs = await self.client.get_pairs_by_token_address_async(chain_id, token_address)
            # Get top 3 most liquid pairs for each token
            liquid_pairs = sorted(
                [p for p in pairs if p.liquidity and p.liquidity.usd > 10_000],
                key=lambda p: p.liquidity.usd,
                reverse=True
            )[:3]
            all_pairs.extend(liquid_pairs)

        print(f"Monitoring {len(all_pairs)} pairs total\n")

        # Subscribe to volume updates
        pair_addresses = [p.pair_address for p in all_pairs]

        filter_config = FilterConfig(
            change_fields=["volume.m5", "volume.h1"],
            volume_change_threshold=0.10  # 10% volume change
        )

        await self.client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=pair_addresses,
            callback=self.handle_volume_update,
            filter=filter_config,
            interval=1.0
        )

        # Monitor for 10 minutes
        await asyncio.sleep(600)
        await self.client.close_streams()

        # Summary
        print(f"\nDetected {len(self.surge_alerts)} volume surges")
        if self.surge_alerts:
            biggest_surge = max(self.surge_alerts, key=lambda x: x['surge_ratio'])
            print(f"Biggest surge: {biggest_surge['surge_ratio']:.1f}x on "
                  f"{biggest_surge['pair'].base_token.symbol}")

async def main():
    detector = VolumeSurgeDetector(surge_multiplier=2.5)  # 2.5x surge threshold

    # Monitor popular tokens on Ethereum
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

## Liquidity Monitoring

### Liquidity Change Tracker

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
        """Handle liquidity updates"""
        if not pair.liquidity or not pair.liquidity.usd:
            return

        key = f"{pair.chain_id}:{pair.pair_address}"
        current_liquidity = pair.liquidity.usd

        # Check for significant change
        if key in self.liquidity_snapshots:
            prev_liquidity = self.liquidity_snapshots[key]['liquidity']
            change = (current_liquidity - prev_liquidity) / prev_liquidity

            if abs(change) > 0.1:  # 10% change
                event = {
                    'timestamp': datetime.now(),
                    'pair': pair,
                    'prev_liquidity': prev_liquidity,
                    'current_liquidity': current_liquidity,
                    'change_percent': change * 100,
                    'type': 'addition' if change > 0 else 'removal'
                }
                self.significant_changes.append(event)
                self.print_liquidity_event(event)

        # Update snapshot
        self.liquidity_snapshots[key] = {
            'liquidity': current_liquidity,
            'timestamp': datetime.now(),
            'pair': pair
        }

    def print_liquidity_event(self, event):
        """Print liquidity change event"""
        pair = event['pair']
        emoji = "💰" if event['type'] == 'addition' else "💸"

        print(f"\n{emoji} LIQUIDITY {event['type'].upper()}")
        print(f"  Time: {event['timestamp'].strftime('%H:%M:%S')}")
        print(f"  Pair: {pair.base_token.symbol}/{pair.quote_token.symbol} on {pair.dex_id}")
        print(f"  Previous: ${event['prev_liquidity']:,.0f}")
        print(f"  Current: ${event['current_liquidity']:,.0f}")
        print(f"  Change: {event['change_percent']:+.1f}%")
        print(f"  Price Impact: Current price ${pair.price_usd:,.6f}")
        print()

    async def monitor_liquidity_changes(self, pairs_to_monitor):
        """Monitor liquidity changes for specific pairs"""
        print(f"Monitoring liquidity for {len(pairs_to_monitor)} pairs...\n")

        # Group by chain
        by_chain = defaultdict(list)
        for chain_id, pair_address in pairs_to_monitor:
            by_chain[chain_id].append(pair_address)

        # Subscribe to each chain
        for chain_id, addresses in by_chain.items():
            filter_config = FilterConfig(
                change_fields=["liquidity.usd", "liquidity.base", "liquidity.quote"],
                liquidity_change_threshold=0.05,  # 5% change threshold
                max_updates_per_second=1.0
            )

            await self.client.subscribe_pairs(
                chain_id=chain_id,
                pair_addresses=addresses,
                callback=self.handle_liquidity_update,
                filter=filter_config,
                interval=2.0
            )

        # Monitor for 10 minutes
        await asyncio.sleep(600)
        await self.client.close_streams()

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print monitoring summary"""
        print("\n" + "="*60)
        print("LIQUIDITY MONITORING SUMMARY")
        print("="*60)

        if not self.significant_changes:
            print("No significant liquidity changes detected")
            return

        # Calculate statistics
        additions = [e for e in self.significant_changes if e['type'] == 'addition']
        removals = [e for e in self.significant_changes if e['type'] == 'removal']

        print(f"Total Events: {len(self.significant_changes)}")
        print(f"Liquidity Additions: {len(additions)}")
        print(f"Liquidity Removals: {len(removals)}")

        if additions:
            biggest_add = max(additions, key=lambda x: x['change_percent'])
            print(f"\nBiggest Addition: {biggest_add['change_percent']:+.1f}% on "
                  f"{biggest_add['pair'].base_token.symbol}")

        if removals:
            biggest_remove = min(removals, key=lambda x: x['change_percent'])
            print(f"Biggest Removal: {biggest_remove['change_percent']:+.1f}% on "
                  f"{biggest_remove['pair'].base_token.symbol}")

        print("="*60)

async def main():
    tracker = LiquidityTracker()

    # Monitor major pairs
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

## Alert System

### Comprehensive Alert System

```python
import asyncio
from datetime import datetime
from enum import Enum
from typing import List, Dict, Callable
from dexscreen import DexscreenerClient, FilterConfig

class AlertType(Enum):
    PRICE_INCREASE = "price_increase"
    PRICE_DECREASE = "price_decrease"
    VOLUME_SURGE = "volume_surge"
    LIQUIDITY_CHANGE = "liquidity_change"
    NEW_ATH = "new_ath"
    LARGE_TRANSACTION = "large_transaction"

class AlertSystem:
    def __init__(self):
        self.client = DexscreenerClient()
        self.alerts: List[Dict] = []
        self.alert_handlers: Dict[AlertType, List[Callable]] = defaultdict(list)
        self.price_history = defaultdict(list)
        self.ath_tracker = {}

    def register_handler(self, alert_type: AlertType, handler: Callable):
        """Register a handler for specific alert types"""
        self.alert_handlers[alert_type].append(handler)

    def create_alert(self, alert_type: AlertType, pair, data: Dict):
        """Create and dispatch an alert"""
        alert = {
            'type': alert_type,
            'timestamp': datetime.now(),
            'pair': pair,
            'chain_id': pair.chain_id,
            'symbol': pair.base_token.symbol,
            'data': data
        }

        self.alerts.append(alert)

        # Dispatch to handlers
        for handler in self.alert_handlers[alert_type]:
            try:
                handler(alert)
            except Exception as e:
                print(f"Error in alert handler: {e}")

    def check_price_alerts(self, pair):
        """Check for price-based alerts"""
        key = f"{pair.chain_id}:{pair.pair_address}"

        # Track price history
        self.price_history[key].append(pair.price_usd)
        if len(self.price_history[key]) > 100:
            self.price_history[key].pop(0)

        # Check for new ATH
        if key not in self.ath_tracker or pair.price_usd > self.ath_tracker[key]:
            if key in self.ath_tracker:  # Not first time
                self.create_alert(AlertType.NEW_ATH, pair, {
                    'new_ath': pair.price_usd,
                    'previous_ath': self.ath_tracker[key],
                    'increase': ((pair.price_usd - self.ath_tracker[key]) / self.ath_tracker[key]) * 100
                })
            self.ath_tracker[key] = pair.price_usd

        # Check recent price changes
        if len(self.price_history[key]) >= 2:
            recent_change = (pair.price_usd - self.price_history[key][-2]) / self.price_history[key][-2]

            if recent_change > 0.05:  # 5% increase
                self.create_alert(AlertType.PRICE_INCREASE, pair, {
                    'change_percent': recent_change * 100,
                    'current_price': pair.price_usd
                })
            elif recent_change < -0.05:  # 5% decrease
                self.create_alert(AlertType.PRICE_DECREASE, pair, {
                    'change_percent': recent_change * 100,
                    'current_price': pair.price_usd
                })

    def check_volume_alerts(self, pair):
        """Check for volume-based alerts"""
        # Volume surge detection
        if pair.volume.m5 and pair.volume.h1:
            hourly_avg_5min = pair.volume.h1 / 12  # Average 5-min volume in last hour
            if pair.volume.m5 > hourly_avg_5min * 3:  # 3x average
                self.create_alert(AlertType.VOLUME_SURGE, pair, {
                    'current_5m_volume': pair.volume.m5,
                    'average_5m_volume': hourly_avg_5min,
                    'surge_multiplier': pair.volume.m5 / hourly_avg_5min
                })

    def check_liquidity_alerts(self, pair):
        """Check for liquidity changes"""
        if pair.liquidity and pair.liquidity.usd:
            # This would need historical data to compare
            # For demo, we'll check if liquidity is very low
            if pair.liquidity.usd < 50_000:
                self.create_alert(AlertType.LIQUIDITY_CHANGE, pair, {
                    'current_liquidity': pair.liquidity.usd,
                    'warning': 'Low liquidity detected'
                })

    def comprehensive_check(self, pair):
        """Run all alert checks"""
        self.check_price_alerts(pair)
        self.check_volume_alerts(pair)
        self.check_liquidity_alerts(pair)

    async def monitor_with_alerts(self, chain_id: str, pair_addresses: List[str]):
        """Monitor pairs with comprehensive alerts"""
        print(f"Starting alert system for {len(pair_addresses)} pairs on {chain_id}\n")

        # Configure filtering for relevant changes
        filter_config = FilterConfig(
            change_fields=["price_usd", "volume.m5", "volume.h1", "liquidity.usd"],
            price_change_threshold=0.001,  # 0.1% for high sensitivity
            volume_change_threshold=0.10,   # 10% volume changes
            max_updates_per_second=2.0
        )

        await self.client.subscribe_pairs(
            chain_id=chain_id,
            pair_addresses=pair_addresses,
            callback=self.comprehensive_check,
            filter=filter_config,
            interval=0.5
        )

        # Run for specified duration
        await asyncio.sleep(300)  # 5 minutes
        await self.client.close_streams()

        # Print summary
        self.print_alert_summary()

    def print_alert_summary(self):
        """Print summary of all alerts"""
        print("\n" + "="*60)
        print("ALERT SUMMARY")
        print("="*60)

        if not self.alerts:
            print("No alerts triggered")
            return

        # Group by type
        by_type = defaultdict(list)
        for alert in self.alerts:
            by_type[alert['type']].append(alert)

        for alert_type, alerts in by_type.items():
            print(f"\n{alert_type.value.upper()}: {len(alerts)} alerts")

            # Show last 3 alerts of this type
            for alert in alerts[-3:]:
                print(f"  [{alert['timestamp'].strftime('%H:%M:%S')}] "
                      f"{alert['symbol']} on {alert['chain_id']}")

                # Type-specific details
                if alert_type == AlertType.PRICE_INCREASE:
                    print(f"    +{alert['data']['change_percent']:.2f}% "
                          f"to ${alert['data']['current_price']:,.6f}")
                elif alert_type == AlertType.VOLUME_SURGE:
                    print(f"    {alert['data']['surge_multiplier']:.1f}x normal volume")
                elif alert_type == AlertType.NEW_ATH:
                    print(f"    New ATH: ${alert['data']['new_ath']:,.6f} "
                          f"(+{alert['data']['increase']:.2f}%)")

# Example handlers
def console_handler(alert: Dict):
    """Print alerts to console"""
    emoji_map = {
        AlertType.PRICE_INCREASE: "📈",
        AlertType.PRICE_DECREASE: "📉",
        AlertType.VOLUME_SURGE: "🔊",
        AlertType.LIQUIDITY_CHANGE: "💧",
        AlertType.NEW_ATH: "🚀",
        AlertType.LARGE_TRANSACTION: "🐋"
    }

    emoji = emoji_map.get(alert['type'], "📢")
    print(f"\n{emoji} ALERT: {alert['type'].value} - {alert['symbol']} "
          f"at {alert['timestamp'].strftime('%H:%M:%S')}")

async def main():
    alert_system = AlertSystem()

    # Register handlers
    alert_system.register_handler(AlertType.PRICE_INCREASE, console_handler)
    alert_system.register_handler(AlertType.PRICE_DECREASE, console_handler)
    alert_system.register_handler(AlertType.VOLUME_SURGE, console_handler)
    alert_system.register_handler(AlertType.NEW_ATH, console_handler)

    # Monitor some active pairs
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

## Next Steps

These examples demonstrate various use cases for Dexscreen. You can:

1. **Combine examples** - Mix monitoring with alerts, add database storage, etc.
2. **Extend functionality** - Add notifications, web interfaces, trading bot integration
3. **Optimize performance** - Use async operations, batch requests, smart filtering
4. **Scale up** - Monitor more pairs, implement distributed systems

For more details, see:

- [Getting Started](getting-started.md) - Installation and basics
- [Query API](api/query-api.md) - All query methods
- [Streaming API](api/streaming-api.md) - Real-time subscriptions
- [Filtering](api/filtering.md) - Advanced filtering options
