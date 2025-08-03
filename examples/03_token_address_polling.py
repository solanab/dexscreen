"""
Example: Token Address Polling Best Practices

This example demonstrates how to poll all trading pairs for a specific token
using the token's contract address, rather than individual pair addresses.

Benefits of token address polling:
1. Monitor all DEX pairs for a token with a single subscription
2. Automatically discover new pairs as they're created
3. Efficient batch API calls for multiple pairs
4. Simplified portfolio tracking across multiple DEXes
"""

import asyncio
import logging
from datetime import datetime

from dexscreen import DexscreenerClient, FilterPresets, TokenPair

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TokenMonitor:
    """Monitor all pairs for specific tokens"""

    def __init__(self):
        # Use stable timeout for continuous monitoring (20 seconds)
        # For faster updates, use: DexscreenerClient(client_kwargs={"timeout": 10})
        # For poor networks, use: DexscreenerClient(client_kwargs={"timeout": 45})
        self.client = DexscreenerClient(client_kwargs={"timeout": 20})
        self.pair_stats = {}  # Track stats per pair

    def format_price(self, price: float) -> str:
        """Format price with appropriate decimal places"""
        if price > 1:
            return f"${price:.2f}"
        elif price > 0.01:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"

    def format_volume(self, volume: float) -> str:
        """Format volume in human readable format"""
        if volume >= 1_000_000:
            return f"${volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"${volume / 1_000:.2f}K"
        else:
            return f"${volume:.2f}"

    def handle_token_update(self, pairs: list[TokenPair]):
        """Handle updates for all pairs of a token"""
        logger.info(f"Token update received: timestamp={datetime.now().strftime('%H:%M:%S')}, pairs_count={len(pairs)}")

        # Sort pairs by 24h volume
        sorted_pairs = sorted(pairs, key=lambda p: p.volume.h24 or 0, reverse=True)

        # Display top pairs
        for i, pair in enumerate(sorted_pairs[:5], 1):
            pair_key = f"{pair.chain_id}:{pair.pair_address}"

            # Track if this is a new pair
            is_new = pair_key not in self.pair_stats
            if is_new:
                self.pair_stats[pair_key] = {"first_seen": datetime.now()}

            # Display pair info
            logger.info(
                f"Pair {i}: pair={pair.base_token.symbol}/{pair.quote_token.symbol}, "
                f"dex={pair.dex_id}, chain={pair.chain_id}, "
                f"address={pair.pair_address}, "
                f"price={self.format_price(pair.price_usd or 0)}, "
                f"volume_24h={self.format_volume(pair.volume.h24 or 0)}, "
                f"change_24h={pair.price_change.h24:+.2f}%, "
                f"liquidity={self.format_volume(pair.liquidity.usd or 0) if pair.liquidity else 'N/A'}, "
                f"is_new={is_new}"
            )

        if len(sorted_pairs) > 5:
            logger.debug(f"... and {len(sorted_pairs) - 5} more pairs")


async def example_basic_token_polling():
    """Basic example: Poll all pairs for a single token"""
    monitor = TokenMonitor()

    # USDC token on Solana
    chain = "solana"
    token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    logger.info(
        f"Starting token polling: token=USDC, chain={chain}, "
        f"address={token_address}, "
        "description=This will show all trading pairs across different DEXes"
    )

    # Subscribe to token with default filtering (only changes)
    await monitor.client.subscribe_tokens(
        chain,
        [token_address],
        callback=monitor.handle_token_update,
        interval=1.0,  # Poll every second
    )

    # Run for 30 seconds
    await asyncio.sleep(30)

    await monitor.client.close_streams()
    logger.info("Basic token polling example completed")


async def example_multi_token_portfolio():
    """Advanced example: Monitor multiple tokens as a portfolio"""
    monitor = TokenMonitor()

    # Using Solana chain for this example
    chain = "solana"

    # Portfolio of popular tokens on Solana
    portfolio = {
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",  # USDC on Solana
        "So11111111111111111111111111111111111112": "SOL",  # Wrapped SOL
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",  # USDT on Solana
    }

    total_volume = {}

    async def handle_portfolio_update(token_address: str, token_symbol: str):
        """Create a handler for each token"""

        def handler(pairs: list[TokenPair]):
            # Calculate total volume across all pairs
            total_24h_volume = sum(p.volume.h24 or 0 for p in pairs)
            total_volume[token_symbol] = total_24h_volume

            logger.debug(
                f"{token_symbol} update: timestamp={datetime.now().strftime('%H:%M:%S')}, "
                f"total_pairs={len(pairs)}, "
                f"total_volume_24h={monitor.format_volume(total_24h_volume)}"
            )

            # Show top pair
            if pairs:
                top_pair = max(pairs, key=lambda p: p.volume.h24 or 0)
                logger.debug(
                    f"{token_symbol} top pair: "
                    f"pair={top_pair.base_token.symbol}/{top_pair.quote_token.symbol}, "
                    f"volume_24h={monitor.format_volume(top_pair.volume.h24 or 0)}"
                )

        return handler

    logger.info(f"Starting portfolio monitoring: tokens_count={len(portfolio)}, tokens={list(portfolio.values())}")

    # Subscribe to all tokens with rate limiting
    for token_address, token_symbol in portfolio.items():
        handler = await handle_portfolio_update(token_address, token_symbol)
        await monitor.client.subscribe_tokens(
            chain,
            [token_address],
            callback=handler,
            filter=FilterPresets.rate_limited(0.5),  # Max 1 update per 2 seconds
            interval=2.0,  # Poll every 2 seconds
        )
        await asyncio.sleep(0.1)  # Stagger subscriptions

    # Run for 30 seconds
    await asyncio.sleep(30)

    # Show portfolio summary
    logger.info("Portfolio Summary")
    for symbol, volume in sorted(total_volume.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"Token summary: symbol={symbol}, volume_24h={monitor.format_volume(volume)}")

    await monitor.client.close_streams()
    logger.info("Portfolio monitoring example completed")


async def example_new_pair_detection():
    """Example: Detect new trading pairs for a token"""
    monitor = TokenMonitor()

    # Using Solana chain for this example
    chain = "solana"
    known_pairs = set()

    def detect_new_pairs(pairs: list[TokenPair]):
        """Detect and alert on new pairs"""
        current_pairs = {f"{p.chain_id}:{p.pair_address}" for p in pairs}
        new_pairs = current_pairs - known_pairs

        if new_pairs:
            logger.warning(f"NEW PAIRS DETECTED: count={len(new_pairs)}, alert_type=new_pair_creation")
            for pair in pairs:
                pair_key = f"{pair.chain_id}:{pair.pair_address}"
                if pair_key in new_pairs:
                    logger.warning(
                        f"New pair details: pair={pair.base_token.symbol}/{pair.quote_token.symbol}, "
                        f"dex={pair.dex_id}, chain={pair.chain_id}, "
                        f"address={pair.pair_address}, "
                        f"initial_price={monitor.format_price(pair.price_usd or 0)}, "
                        f"initial_liquidity={monitor.format_volume(pair.liquidity.usd if pair.liquidity and pair.liquidity.usd else 0)}, "
                        f"created_at={pair.pair_created_at}"
                    )

        known_pairs.update(current_pairs)

        # Also show summary
        logger.debug(f"Pair check summary: timestamp={datetime.now().strftime('%H:%M:%S')}, total_pairs={len(pairs)}")

    # Monitor a token that might get new pairs
    token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC on Solana

    logger.info(
        f"Starting new pair detection: token_address={token_address}, "
        "description=This example will detect when new trading pairs are created"
    )

    # First, get initial pairs
    initial_pairs = await monitor.client.get_pairs_by_token_address_async(chain, token_address)
    known_pairs = {f"{p.chain_id}:{p.pair_address}" for p in initial_pairs}
    logger.info(f"Initial state: known_pairs_count={len(known_pairs)}")

    # Subscribe with no filtering to catch all updates
    await monitor.client.subscribe_tokens(
        chain,
        [token_address],
        callback=detect_new_pairs,
        filter=False,  # No filtering - we want all updates
        interval=5.0,  # Check every 5 seconds
    )

    # Run for 60 seconds
    await asyncio.sleep(60)

    await monitor.client.close_streams()
    logger.info("New pair detection example completed")


async def example_token_arbitrage_monitor():
    """Example: Monitor price differences across DEXes for arbitrage"""
    monitor = TokenMonitor()

    # Using Ethereum chain for this example
    chain = "ethereum"

    def check_arbitrage_opportunities(pairs: list[TokenPair]):
        """Check for price differences between pairs"""
        # Group pairs by quote token
        pairs_by_quote = {}
        for pair in pairs:
            quote = pair.quote_token.symbol
            if quote not in pairs_by_quote:
                pairs_by_quote[quote] = []
            pairs_by_quote[quote].append(pair)

        logger.info(f"Arbitrage check: timestamp={datetime.now().strftime('%H:%M:%S')}")

        # Check each quote token group
        for quote_symbol, quote_pairs in pairs_by_quote.items():
            if len(quote_pairs) < 2:
                continue

            # Sort by price
            sorted_pairs = sorted(quote_pairs, key=lambda p: p.price_usd or 0)

            if len(sorted_pairs) >= 2:
                lowest = sorted_pairs[0]
                highest = sorted_pairs[-1]

                if lowest.price_usd and highest.price_usd and lowest.price_usd > 0:
                    spread_pct = ((highest.price_usd - lowest.price_usd) / lowest.price_usd) * 100

                    if spread_pct > 0.5:  # Show if spread > 0.5%
                        buy_liq = lowest.liquidity.usd if lowest.liquidity else 0
                        sell_liq = highest.liquidity.usd if highest.liquidity else 0
                        logger.warning(
                            f"ARBITRAGE OPPORTUNITY: quote_token={quote_symbol}, "
                            f"spread_pct={spread_pct:.2f}%, "
                            f"buy_dex={lowest.dex_id}, "
                            f"buy_price={monitor.format_price(lowest.price_usd)}, "
                            f"buy_liquidity={monitor.format_volume(buy_liq)}, "
                            f"sell_dex={highest.dex_id}, "
                            f"sell_price={monitor.format_price(highest.price_usd)}, "
                            f"sell_liquidity={monitor.format_volume(sell_liq)}"
                        )

    # Monitor WETH for arbitrage opportunities
    token_address = "C02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH on Ethereum

    logger.info(
        "Starting arbitrage monitoring: token=WETH, "
        f"token_address={token_address}, "
        "description=Looking for price differences across DEXes"
    )

    await monitor.client.subscribe_tokens(
        chain,
        [token_address],
        callback=check_arbitrage_opportunities,
        filter=FilterPresets.significant_price_changes(0.001),  # 0.1% changes
        interval=1.0,
    )

    # Run for 45 seconds
    await asyncio.sleep(45)

    await monitor.client.close_streams()
    logger.info("Arbitrage monitoring example completed")


async def main():
    """Run all examples"""
    examples = [
        ("Basic Token Polling", example_basic_token_polling),
        ("Multi-Token Portfolio", example_multi_token_portfolio),
        ("New Pair Detection", example_new_pair_detection),
        ("Arbitrage Monitoring", example_token_arbitrage_monitor),
    ]

    for i, (name, example_func) in enumerate(examples, 1):
        logger.info(f"\n{'=' * 60}\nExample {i}: {name}\n{'=' * 60}")

        await example_func()

        if i < len(examples):
            logger.info("Press Enter to continue to the next example...")
            input()


if __name__ == "__main__":
    asyncio.run(main())
