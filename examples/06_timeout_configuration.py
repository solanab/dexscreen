"""
Timeout Configuration Example: Demonstrates various timeout settings and best practices

This example shows:
1. Default timeout behavior
2. Custom timeout configuration
3. Runtime timeout updates
4. Timeout best practices for different scenarios
5. Error handling for timeout situations
"""

import asyncio
import logging
from datetime import datetime

from dexscreen import DexscreenerClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def demonstrate_default_timeout():
    """Demonstrate default timeout behavior (10 seconds)"""
    logger.info("=== Default Timeout Demo ===")

    # Default client with 10-second timeout
    client = DexscreenerClient()

    try:
        # Single API call with default timeout
        pairs = await client.get_pairs_by_token_address_async("solana", "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
        logger.info(f"✅ Default timeout successful: Got {len(pairs)} pairs")

    except Exception as e:
        logger.error(f"❌ Default timeout failed: {e}")

    await client.close_streams()


async def demonstrate_custom_timeout():
    """Demonstrate custom timeout configuration for different scenarios"""
    logger.info("=== Custom Timeout Demo ===")

    # Fast client for quick trading (5 seconds)
    fast_client = DexscreenerClient(client_kwargs={"timeout": 5})
    logger.info("⚡ Fast client created (5s timeout)")

    # Stable client for monitoring (30 seconds)
    stable_client = DexscreenerClient(client_kwargs={"timeout": 30})
    logger.info("🔒 Stable client created (30s timeout)")

    # Conservative client for poor networks (60 seconds)
    conservative_client = DexscreenerClient(client_kwargs={"timeout": 60})
    logger.info("🐌 Conservative client created (60s timeout)")

    try:
        # Test fast client
        start_time = datetime.now()
        pairs = await fast_client.get_pairs_by_token_address_async(
            "ethereum", "0xA0b86a33E6417c7Df4e9c1b4F0F6FAF0Ed6e4cAE"
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"⚡ Fast client: {elapsed:.2f}s, {len(pairs)} pairs")

    except Exception as e:
        logger.warning(f"⚡ Fast client timeout (expected for slow networks): {e}")

    try:
        # Test stable client
        start_time = datetime.now()
        results = await stable_client.search_pairs_async("USDT")
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"🔒 Stable client: {elapsed:.2f}s, {len(results)} results")

    except Exception as e:
        logger.error(f"🔒 Stable client failed: {e}")

    # Close clients
    await fast_client.close_streams()
    await stable_client.close_streams()
    await conservative_client.close_streams()


async def demonstrate_runtime_timeout_updates():
    """Demonstrate updating timeout at runtime"""
    logger.info("=== Runtime Timeout Updates Demo ===")

    client = DexscreenerClient()

    # Initial configuration
    logger.info("📊 Initial timeout: 10s (default)")

    # Start monitoring a pair
    chain = "bsc"
    address = "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae"  # WBNB/USDT

    update_count = 0

    def on_price_update(pair):
        nonlocal update_count
        update_count += 1
        logger.info(f"📈 Price update #{update_count}: ${pair.price_usd:.6f}")

    # Subscribe with default timeout
    await client.subscribe_pairs(chain_id=chain, pair_addresses=[address], callback=on_price_update, interval=1.0)

    # Run for 3 seconds
    logger.info("🏃 Running with default timeout (10s)...")
    await asyncio.sleep(3)

    # Update to faster timeout for quick responses
    logger.info("⚡ Updating to fast timeout (5s)...")
    await client._client_300rpm.update_config({"timeout": 5})
    await asyncio.sleep(3)

    # Update to stable timeout for reliability
    logger.info("🔒 Updating to stable timeout (25s)...")
    await client._client_300rpm.update_config({"timeout": 25})
    await asyncio.sleep(3)

    # Multiple config update including timeout
    logger.info("🔧 Batch config update (timeout + browser)...")
    await client._client_300rpm.update_config({"timeout": 15, "impersonate": "safari184"})
    await asyncio.sleep(3)

    # Stop monitoring
    await client.unsubscribe_pairs(chain_id=chain, pair_addresses=[address])
    logger.info(f"📊 Total updates received: {update_count}")

    await client.close_streams()


async def demonstrate_timeout_error_handling():
    """Demonstrate proper timeout error handling"""
    logger.info("=== Timeout Error Handling Demo ===")

    # Create a client with very short timeout to trigger timeout errors
    client = DexscreenerClient(client_kwargs={"timeout": 0.1})  # 100ms - very short

    try:
        # This will likely timeout due to the very short timeout
        logger.info("🔥 Attempting API call with 100ms timeout (likely to fail)...")
        pairs = await client.get_pairs_by_token_address_async("ethereum", "0xA0b86a33E6417c7Df4e9c1b4F0F6FAF0Ed6e4cAE")
        logger.info(f"😲 Surprisingly succeeded: {len(pairs)} pairs")

    except Exception as e:
        logger.warning(f"⏰ Expected timeout error: {type(e).__name__}: {e}")

        # Show how to handle timeout gracefully
        logger.info("🛠️ Handling timeout - switching to longer timeout...")
        await client._client_300rpm.update_config({"timeout": 15})

        try:
            # Retry with longer timeout
            pairs = await client.get_pairs_by_token_address_async(
                "ethereum", "0xA0b86a33E6417c7Df4e9c1b4F0F6FAF0Ed6e4cAE"
            )
            logger.info(f"✅ Recovery successful: {len(pairs)} pairs")
        except Exception as retry_error:
            logger.error(f"❌ Recovery failed: {retry_error}")

    await client.close_streams()


async def demonstrate_scenario_based_timeouts():
    """Demonstrate timeout configuration for specific trading scenarios"""
    logger.info("=== Scenario-Based Timeout Demo ===")

    scenarios = [
        {
            "name": "High-Frequency Trading",
            "timeout": 5,
            "description": "Fast responses for time-sensitive operations",
            "emoji": "⚡",
        },
        {
            "name": "Portfolio Monitoring",
            "timeout": 15,
            "description": "Balanced setting for regular monitoring",
            "emoji": "📊",
        },
        {
            "name": "Long-term Analysis",
            "timeout": 30,
            "description": "Stable connections for batch processing",
            "emoji": "🔬",
        },
        {
            "name": "Mobile/Poor Network",
            "timeout": 45,
            "description": "Handle unstable connections gracefully",
            "emoji": "📱",
        },
    ]

    for scenario in scenarios:
        logger.info(f"{scenario['emoji']} Testing {scenario['name']} (timeout: {scenario['timeout']}s)")
        logger.info(f"   Use case: {scenario['description']}")

        client = DexscreenerClient(client_kwargs={"timeout": scenario["timeout"]})

        try:
            start_time = datetime.now()
            pairs = await client.get_pairs_by_token_address_async(
                "solana", "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
            )
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"   ✅ Success: {elapsed:.2f}s, {len(pairs)} pairs")

        except Exception as e:
            logger.warning(f"   ❌ Failed: {e}")

        await client.close_streams()
        await asyncio.sleep(1)  # Brief pause between scenarios


async def main():
    """Run all timeout configuration demonstrations"""
    logger.info("🚀 Starting Timeout Configuration Examples")
    logger.info("=" * 60)

    try:
        await demonstrate_default_timeout()
        await asyncio.sleep(2)

        await demonstrate_custom_timeout()
        await asyncio.sleep(2)

        await demonstrate_runtime_timeout_updates()
        await asyncio.sleep(2)

        await demonstrate_timeout_error_handling()
        await asyncio.sleep(2)

        await demonstrate_scenario_based_timeouts()

    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")

    logger.info("=" * 60)
    logger.info("🎯 Timeout Configuration Examples Complete")
    logger.info("")
    logger.info("📋 Key Takeaways:")
    logger.info("  • Default timeout: 10 seconds (good for most use cases)")
    logger.info("  • Quick trading: 5-10 seconds")
    logger.info("  • Stable monitoring: 20-30 seconds")
    logger.info("  • Poor networks: 30-60 seconds")
    logger.info("  • Runtime updates: await client._client_300rpm.update_config({'timeout': X})")
    logger.info("  • Always handle timeout errors gracefully")


if __name__ == "__main__":
    asyncio.run(main())
