"""
Dynamic config update example: Shows how to change client_kwargs at runtime
Demonstrates changing DNS servers and browser fingerprints (impersonate)
"""

import asyncio
import logging
from datetime import datetime

from dexscreen import DexscreenerClient

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    """Demonstrates how to dynamically update configuration at runtime"""

    # Initialize client with default configuration
    client = DexscreenerClient()

    logger.info("Starting Dynamic Configuration Update Example")

    # Monitored pair - using an active trading pair
    chain = "bsc"
    address = "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae"  # WBNB/USDT - Active pair on BSC

    update_count = 0
    last_price = None

    def on_update(pair):
        nonlocal update_count, last_price
        update_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        price_change = ""
        if last_price and last_price != pair.price_usd:
            change = pair.price_usd - last_price
            price_change = f" (Change: ${change:+.6f})"
        last_price = pair.price_usd
        logger.debug(
            f"Price update: timestamp={timestamp}, "
            f"update_num={update_count}, "
            f"price=${pair.price_usd:.6f}"
            f"{price_change if price_change else ''}"
        )

    # 1. Subscribe with default configuration
    logger.info("Step 1: Subscribe with default configuration")
    logger.debug(f"Current config: {client._client_300rpm.get_current_config()}")

    await client.subscribe_pairs(
        chain_id=chain,
        pair_addresses=[address],
        callback=on_update,
        filter=False,  # Disable filtering, show all polling results
        # interval=0.5,  # Poll every 0.5 seconds
    )

    logger.info("Running for 3 seconds...")
    await asyncio.sleep(3)

    # 2. Update browser fingerprint
    logger.info("Step 2: Update browser fingerprint to Safari")
    # Use async update_config method for hot switching
    await client._client_300rpm.update_config({"impersonate": "safari184"})
    logger.debug(f"Config updated: impersonate={client._client_300rpm.get_current_config().get('impersonate')}")
    logger.info("Continue running for 3 seconds...")
    await asyncio.sleep(3)

    # 3. Update multiple configuration parameters
    logger.info("Step 3: Update multiple configuration parameters")
    # Update browser fingerprint and timeout settings simultaneously
    new_config = {
        "impersonate": "chrome136",
        "timeout": 15,  # Increase timeout
        "headers": {"Accept": "application/json", "Accept-Encoding": "gzip, deflate, br"},
    }
    await client._client_300rpm.update_config(new_config)
    logger.debug("Multiple configs updated: impersonate=chrome136, timeout=15, headers=custom")
    logger.info("Continue running for 3 seconds...")
    await asyncio.sleep(3)

    # 4. Update single configuration item
    logger.info("Step 4: Update single configuration items")

    # Update timeout
    await client._client_300rpm.update_config({"timeout": 10})
    logger.debug("Updated timeout: timeout=10")

    # Update request headers
    custom_headers = {"X-Custom-Header": "MyValue", "User-Agent": "Custom-Agent/1.0"}
    await client._client_300rpm.update_config({"headers": custom_headers})
    logger.debug(f"Updated headers: headers={custom_headers}")

    # Disable proxy (set to None)
    await client._client_300rpm.update_config({"proxy": None})
    logger.debug("Proxy disabled")

    logger.info("Continue running for 3 seconds...")
    await asyncio.sleep(3)

    # 5. Batch update configuration
    logger.info("Step 5: Batch update multiple configurations")
    new_config = {
        "impersonate": "firefox135",
        "timeout": 5,
        "headers": {"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
        "verify": True,  # Enable SSL verification
    }

    await client._client_300rpm.update_config(new_config)
    logger.debug(f"Batch update completed: config={new_config}")
    logger.info("Continue running for 3 seconds...")
    await asyncio.sleep(3)

    # 6. Complete config replacement
    logger.info("Step 6: Complete config replacement (using replace=True)")
    # Use replace=True to completely replace config, keeping only specified items
    replacement_config = {
        "timeout": 8,
        "impersonate": "safari184",
    }
    await client._client_300rpm.update_config(replacement_config, replace=True)
    logger.debug(
        f"Config replaced: new_config={replacement_config}, current_config={client._client_300rpm.get_current_config()}"
    )
    logger.info("Continue running for 3 seconds...")
    await asyncio.sleep(3)

    # 7. View statistics
    logger.info("Step 7: View statistics")
    stats = client._client_300rpm.get_stats()
    logger.info(
        f"Client statistics: config_switches={stats['switches']}, "
        f"successful_requests={stats['successful_requests']}, "
        f"failed_requests={stats['failed_requests']}, "
        f"last_switch={stats.get('last_switch')}"
    )

    # Unsubscribe
    await client.unsubscribe_pairs(chain_id=chain, pair_addresses=[address])
    logger.info(f"Unsubscribed: total_updates={update_count}")

    # Close client
    await client.close_streams()
    logger.info("Demo complete")


if __name__ == "__main__":
    asyncio.run(main())
