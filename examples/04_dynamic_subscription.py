"""
Example: Dynamic Subscription Management

This example demonstrates how to dynamically manage streaming subscriptions:
1. Solana Pairs: Start with 5 pair addresses, add 2 more, then remove 3
2. BSC Tokens: Monitor 5 popular tokens, add 1 more, then remove 2

This pattern is useful for:
- Portfolio management where tokens are added/removed dynamically
- Monitoring systems that adjust based on market conditions
- Resource optimization by unsubscribing from inactive tokens
- Cross-chain monitoring with different subscription types
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Union

import orjson

from dexscreen import DexscreenerClient, TokenPair

# Set different log levels to reduce noise
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# Only show DEBUG for our example
logging.getLogger(__name__).setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class BSCTokenManager:
    """Manages BSC token subscriptions"""

    def __init__(self):
        self.client = DexscreenerClient()
        self.token_pairs: dict[str, list[TokenPair]] = {}  # Store pairs for each token
        self.update_counts: dict[str, int] = {}  # Track updates per token

    def format_price(self, price: Union[float, None]) -> str:
        """Format price with appropriate decimal places"""
        if price is None:
            return "N/A"
        if price > 1:
            return f"${price:.2f}"
        elif price > 0.01:
            return f"${price:.4f}"
        elif price > 0.000001:
            return f"${price:.8f}"
        else:
            return f"${price:.2e}"

    def create_token_handler(self, token_address: str, symbol: str):
        """Create a callback handler for token updates"""

        def handle_token_update(pairs: list[TokenPair]):
            """Handle updates for all pairs of a token"""
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Initialize counter if needed
            if token_address not in self.update_counts:
                self.update_counts[token_address] = 0
            self.update_counts[token_address] += 1

            # Store latest pairs data
            self.token_pairs[token_address] = pairs

            # Find the pair with highest liquidity
            if pairs:
                best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity and p.liquidity.usd else 0)

                logger.debug(
                    f"BSC Token update: timestamp={timestamp}, "
                    f"update_num={self.update_counts[token_address]}, "
                    f"token={symbol}, "
                    f"pairs_count={len(pairs)}, "
                    f"best_price={self.format_price(best_pair.price_usd)}, "
                    f"total_liquidity=${sum(p.liquidity.usd for p in pairs if p.liquidity and p.liquidity.usd):,.0f}"
                )

        return handle_token_update

    def display_portfolio_status(self):
        """Display current BSC token portfolio status"""
        logger.info("\n" + "=" * 60)
        logger.info("BSC TOKEN PORTFOLIO STATUS")
        logger.info("=" * 60)

        if not self.token_pairs:
            logger.info("No active BSC token subscriptions")
            return

        total_updates = sum(self.update_counts.values())
        total_pairs = sum(len(pairs) for pairs in self.token_pairs.values())
        logger.info(
            f"Active tokens: {len(self.token_pairs)}, Total pairs: {total_pairs}, Total updates: {total_updates}"
        )

        for token_address, pairs in self.token_pairs.items():
            if pairs:
                best_pair = max(pairs, key=lambda p: p.liquidity.usd if p.liquidity and p.liquidity.usd else 0)
                symbol = (
                    best_pair.base_token.symbol
                    if best_pair.base_token.address.lower() == token_address.lower()
                    else best_pair.quote_token.symbol
                )
                logger.info(
                    f"{symbol}: "
                    f"pairs={len(pairs)}, "
                    f"best_price={self.format_price(best_pair.price_usd)}, "
                    f"updates={self.update_counts.get(token_address, 0)}"
                )
        logger.info("=" * 60 + "\n")


class DynamicTokenManager:
    """Manages dynamic token subscriptions"""

    def __init__(self):
        self.client = DexscreenerClient()
        self.token_data: dict[str, dict] = {}  # Store latest data for each token
        self.update_counts: dict[str, int] = {}  # Track updates per token

    def format_price(self, price: Union[float, None]) -> str:
        """Format price with appropriate decimal places"""
        if price is None:
            return "N/A"
        if price > 1:
            return f"${price:.2f}"
        elif price > 0.01:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"

    def format_volume(self, volume: Union[float, None]) -> str:
        """Format volume in human readable format"""
        if volume is None:
            return "N/A"
        if volume >= 1_000_000:
            return f"${volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"${volume / 1_000:.2f}K"
        else:
            return f"${volume:.2f}"

    def create_token_handler(self, address: str, symbol: str):
        """Create a callback handler for a specific token"""

        def handle_update(pair: TokenPair):
            """Handle updates for this token pair"""
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds

            # Initialize counter if needed
            if address not in self.update_counts:
                self.update_counts[address] = 0
            self.update_counts[address] += 1

            # Store latest data
            self.token_data[address] = {
                "symbol": symbol,
                "price": pair.price_usd,
                "volume_24h": pair.volume.h24,
                "price_change_24h": pair.price_change.h24,
                "liquidity": pair.liquidity.usd if pair.liquidity else None,
                "last_update": datetime.now(),
                "update_count": self.update_counts[address],
            }

            # Always log updates with timestamp
            logger.debug(
                f"Price update: timestamp={timestamp}, "
                f"update_num={self.update_counts[address]}, "
                f"token={symbol}, "
                f"price={self.format_price(pair.price_usd)}, "
                f"volume_24h={self.format_volume(pair.volume.h24)}, "
                f"change_24h={pair.price_change.h24:+.2f}%"
            )

        return handle_update

    def display_portfolio_status(self):
        """Display current portfolio status"""
        logger.info("\n" + "=" * 60)
        logger.info("PORTFOLIO STATUS")
        logger.info("=" * 60)

        if not self.token_data:
            logger.info("No active subscriptions")
            return

        total_updates = sum(self.update_counts.values())
        logger.info(f"Active pairs: {len(self.token_data)}, Total updates: {total_updates}")

        for _address, data in self.token_data.items():
            logger.info(
                f"{data['symbol']}: "
                f"price={self.format_price(data['price'])}, "
                f"volume={self.format_volume(data['volume_24h'])}, "
                f"updates={data['update_count']}"
            )
        logger.info("=" * 60 + "\n")


async def run_bsc_token_demo():
    """Run BSC token subscription demo"""
    bsc_manager = BSCTokenManager()

    # Load BSC popular tokens
    bsc_tokens_file = Path("bsc_popular_tokens.json")
    if not bsc_tokens_file.exists():
        logger.error("BSC tokens file not found. Please run get_bsc_tokens.py first.")
        return

    with open(bsc_tokens_file, "rb") as f:
        bsc_tokens = orjson.loads(f.read())

    # Use first 5 tokens for initial subscription
    initial_tokens = bsc_tokens[:5]
    additional_token = bsc_tokens[5] if len(bsc_tokens) > 5 else None

    logger.info("\n" + "=" * 60)
    logger.info("BSC TOKEN SUBSCRIPTION DEMO")
    logger.info("=" * 60)
    logger.info("This demo will:")
    logger.info("1. Subscribe to 5 popular BSC tokens")
    logger.info("2. Add 1 more token after 5 seconds")
    logger.info("3. Remove 2 tokens after 3 more seconds")
    logger.info("=" * 60 + "\n")

    # Step 1: Subscribe to initial 5 tokens
    logger.info("Step 1: Subscribing to 5 BSC tokens...")
    subscribed_tokens = []

    for token in initial_tokens:
        handler = bsc_manager.create_token_handler(token["address"], token["symbol"])
        await bsc_manager.client.subscribe_tokens(
            chain_id="bsc",
            token_addresses=[token["address"]],
            callback=handler,
            filter=False,  # Get all updates
            interval=0.5,  # Poll every 0.5 seconds
        )
        subscribed_tokens.append(token)
        logger.info(f"Subscribed to {token['symbol']} ({token['address'][:16]}...)")
        await asyncio.sleep(0.1)

    logger.info(f"Initial BSC subscriptions complete: {len(subscribed_tokens)} tokens\n")

    # Display initial status
    await asyncio.sleep(2)
    bsc_manager.display_portfolio_status()

    # Run for 5 seconds
    logger.info("Running for 5 seconds with initial tokens...")
    await asyncio.sleep(5)

    # Step 2: Add 1 more token
    if additional_token:
        logger.info("\nStep 2: Adding 1 more BSC token...")
        handler = bsc_manager.create_token_handler(additional_token["address"], additional_token["symbol"])
        await bsc_manager.client.subscribe_tokens(
            chain_id="bsc",
            token_addresses=[additional_token["address"]],
            callback=handler,
            filter=False,
            interval=0.5,
        )
        subscribed_tokens.append(additional_token)
        logger.info(f"Added {additional_token['symbol']} ({additional_token['address'][:16]}...)")
        logger.info(f"Now monitoring {len(subscribed_tokens)} BSC tokens\n")

    # Display status after adding token
    await asyncio.sleep(2)
    bsc_manager.display_portfolio_status()

    # Run for 3 more seconds
    logger.info("Running for 3 more seconds with all 6 tokens...")
    await asyncio.sleep(3)

    # Step 3: Remove 2 tokens
    logger.info("\nStep 3: Removing 2 BSC tokens...")
    tokens_to_remove = subscribed_tokens[:2]

    for token in tokens_to_remove:
        await bsc_manager.client.unsubscribe_tokens(chain_id="bsc", token_addresses=[token["address"]])
        # Remove from tracking
        if token["address"] in bsc_manager.token_pairs:
            del bsc_manager.token_pairs[token["address"]]
        subscribed_tokens.remove(token)
        logger.info(f"Unsubscribed from {token['symbol']} ({token['address'][:16]}...)")
        await asyncio.sleep(0.1)

    logger.info(f"Now monitoring {len(subscribed_tokens)} BSC tokens\n")

    # Run for 3 more seconds
    logger.info("Running for 3 more seconds with remaining tokens...")
    await asyncio.sleep(3)

    # Final status
    bsc_manager.display_portfolio_status()

    # Clean up
    logger.info("\nCleaning up BSC subscriptions...")
    await bsc_manager.client.close_streams()

    return bsc_manager


async def main():
    """Run the dynamic subscription example with both Solana pairs and BSC tokens"""

    # Run the original Solana demo first
    logger.info("=" * 80)
    logger.info("PART 1: SOLANA PAIR SUBSCRIPTIONS")
    logger.info("=" * 80)

    manager = DynamicTokenManager()

    # Active Solana trading pair addresses (not token addresses!)
    # These are actual pair addresses from DEXScreener
    initial_pairs = {
        "739FaSK16AUx5gBXjxoweJF71ioQHQmWm1x3pickfLjT": "Doge/USDC",  # High liquidity pair
        "879F697iuDJGMevRkRcnW21fcXiAeLJK1ffsw2ATebce": "MEW/SOL",  # Medium liquidity pair
        "DSUvc5qf5LJHHV5e2tD184ixotSnCnwj7i4jJa4Xsrmt": "BOME/SOL",  # Popular meme coin
        "9wFFyRfZBsuAha4YcuxcXLKwMxJR43S7fPfQLusDBzvT": "SOL/USDC",  # Major pair
        "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": "PYTH/USDC",  # Oracle token pair
    }

    additional_pairs = {
        "CKfatsPMUf8SkiURsDXs7eK6GWb4Jsd6UDbs7twMCWxo": "BOME/USDT",  # Another BOME pair
        "6oGsL2puUgySccKzn9XA9afqF217LfxP5ocq4B3LWsjy": "WIF/USDC",  # Popular meme coin
    }

    chain = "solana"

    logger.info("This part will:")
    logger.info("1. Subscribe to 5 Solana trading pairs")
    logger.info("2. Add 2 more pairs after 10 seconds")
    logger.info("3. Unsubscribe from the first 3 pairs after 5 more seconds")
    logger.info("=" * 60 + "\n")

    # Step 1: Subscribe to initial 5 pairs
    logger.info("Step 1: Subscribing to initial 5 trading pairs...")
    subscribed_addresses = []

    for address, symbol in initial_pairs.items():
        handler = manager.create_token_handler(address, symbol)
        await manager.client.subscribe_pairs(
            chain_id=chain,
            pair_addresses=[address],
            callback=handler,
            filter=False,  # Use default change detection
            interval=0.5,  # Poll every 0.5 seconds for more frequent updates
        )
        subscribed_addresses.append(address)
        logger.info(f"Subscribed to {symbol} ({address})")
        await asyncio.sleep(0.1)  # Small delay between subscriptions

    logger.info(f"Initial subscriptions complete: {len(subscribed_addresses)} pairs\n")

    # Display initial status
    await asyncio.sleep(2)
    manager.display_portfolio_status()

    # Run for 10 seconds with initial pairs
    logger.info("Running for 10 seconds with initial pairs...")
    await asyncio.sleep(10)

    # Step 2: Add 2 more pairs
    logger.info("\nStep 2: Adding 2 more pairs to the subscription list...")
    for address, symbol in additional_pairs.items():
        handler = manager.create_token_handler(address, symbol)
        await manager.client.subscribe_pairs(
            chain_id=chain,
            pair_addresses=[address],
            callback=handler,
            filter=False,
            interval=0.5,
        )
        subscribed_addresses.append(address)
        logger.info(f"Added subscription for {symbol} ({address})")
        await asyncio.sleep(0.1)

    logger.info(f"Now monitoring {len(subscribed_addresses)} pairs\n")

    # Display status after adding tokens
    await asyncio.sleep(2)
    manager.display_portfolio_status()

    # Run for 5 more seconds
    logger.info("Running for 5 more seconds with all 7 pairs...")
    await asyncio.sleep(5)

    # Step 3: Unsubscribe from first 3 pairs
    logger.info("\nStep 3: Unsubscribing from the first 3 pairs...")
    pairs_to_remove = list(initial_pairs.items())[:3]

    for address, symbol in pairs_to_remove:
        await manager.client.unsubscribe_pairs(chain_id=chain, pair_addresses=[address])
        # Remove from our tracking
        if address in manager.token_data:
            del manager.token_data[address]
        subscribed_addresses.remove(address)
        logger.info(f"Unsubscribed from {symbol} ({address})")
        await asyncio.sleep(0.1)

    logger.info(f"Now monitoring {len(subscribed_addresses)} pairs\n")

    # Run for 5 more seconds with remaining pairs
    logger.info("Running for 5 more seconds with remaining 4 pairs...")
    await asyncio.sleep(5)

    # Final status
    manager.display_portfolio_status()

    # Show active subscriptions
    active_subs = manager.client.get_active_subscriptions()
    logger.info("\nActive subscriptions from client:")
    for sub in active_subs:
        if sub["type"] == "pair":
            symbol = next(
                (v for k, v in {**initial_pairs, **additional_pairs}.items() if k == sub["pair_address"]), "Unknown"
            )
            logger.info(f"- {symbol}: {sub['chain']}:{sub['pair_address']}")

    # Clean up Solana subscriptions
    logger.info("\nCleaning up Solana subscriptions...")
    await manager.client.close_streams()

    # Summary for Solana part
    logger.info("\n" + "=" * 60)
    logger.info("SOLANA DEMO COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total Solana updates processed: {sum(manager.update_counts.values())}")
    for address, count in manager.update_counts.items():
        symbol = next((v for k, v in {**initial_pairs, **additional_pairs}.items() if k == address), "Unknown")
        logger.info(f"- {symbol}: {count} updates")
    logger.info("=" * 60)

    # Now run the BSC token demo
    logger.info("\n\n" + "=" * 80)
    logger.info("PART 2: BSC TOKEN SUBSCRIPTIONS")
    logger.info("=" * 80)

    bsc_manager = await run_bsc_token_demo()

    # Final summary
    logger.info("\n\n" + "=" * 80)
    logger.info("COMPLETE EXAMPLE SUMMARY")
    logger.info("=" * 80)
    logger.info("Solana Pairs Demo:")
    logger.info(f"  - Total updates: {sum(manager.update_counts.values())}")
    logger.info(f"  - Pairs monitored: {len(manager.update_counts)}")

    if bsc_manager:
        logger.info("\nBSC Tokens Demo:")
        logger.info(f"  - Total updates: {sum(bsc_manager.update_counts.values())}")
        logger.info(f"  - Tokens monitored: {len(bsc_manager.update_counts)}")
        logger.info(f"  - Total pairs tracked: {sum(len(pairs) for pairs in bsc_manager.token_pairs.values())}")

    logger.info("\nKey Takeaways:")
    logger.info("- Dynamic subscriptions work seamlessly across chains")
    logger.info("- subscribe_pairs monitors specific trading pairs")
    logger.info("- subscribe_tokens monitors all pairs of a token")
    logger.info("- Both subscription types can be added/removed dynamically")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
