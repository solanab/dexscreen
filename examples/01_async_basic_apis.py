"""
Async example: Demonstrates all basic APIs
Shows how to use async methods to call all API methods
"""

import asyncio
import logging
from datetime import datetime

from dexscreen import DexscreenerClient

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    """Demonstrates all basic API async calls"""
    # Initialize client with default 10-second timeout
    # For faster responses, use: DexscreenerClient(client_kwargs={"timeout": 5})
    # For stable connections, use: DexscreenerClient(client_kwargs={"timeout": 30})
    client = DexscreenerClient()

    logger.info("Starting DexScreener Python SDK - Async API Example")
    logger.info("Using default timeout: 10 seconds")

    # 1. Single pair query
    logger.info("Example 1: Query single pair (method: get_pair_async)")
    pair = await client.get_pair_async("EEEnep1wgtWV4Gp1rJFppNHN3V4EutEUWzxx1LiXZhx9")
    if pair:
        logger.info(
            f"Pair data: {pair.base_token.symbol}/{pair.quote_token.symbol}, "
            f"price_usd=${pair.price_usd:.6f}, "
            f"volume_24h=${pair.volume.h24:,.2f}, "
            f"liquidity_usd=${pair.liquidity.usd:,.2f}"
            if pair.liquidity
            else "liquidity_usd=N/A"
        )

    # 2. Query pair on specific chain
    logger.info("Example 2: Query pair on specific chain (method: get_pair_by_pair_address_async)")
    eth_pair = await client.get_pair_by_pair_address_async(
        "ethereum",
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # USDC-WETH
    )
    if eth_pair:
        logger.info(
            f"Chain pair data: chain={eth_pair.chain_id}, "
            f"pair={eth_pair.base_token.symbol}/{eth_pair.quote_token.symbol}, "
            f"dex={eth_pair.dex_id}, "
            f"price_usd=${eth_pair.price_usd:.4f}"
        )

    # 3. Batch query pairs
    logger.info("Example 3: Batch query pairs (method: get_pairs_by_pairs_addresses_async)")
    bsc_pairs = await client.get_pairs_by_pairs_addresses_async(
        "bsc",
        [
            "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae",  # USDT-WBNB
            "0x7213a321F1855CF1779f42c0CD85d3D95291D34C",  # BTCB-BUSD
        ],
    )
    for pair in bsc_pairs:
        logger.debug(f"BSC pair: {pair.base_token.symbol}/{pair.quote_token.symbol}, price_usd=${pair.price_usd:.4f}")

    # 4. Search pairs
    logger.info("Example 4: Search pairs (method: search_pairs_async, query: PEPE)")
    search_results = await client.search_pairs_async("PEPE")
    logger.info(f"Search results: total_found={len(search_results)}")
    for i, pair in enumerate(search_results[:3]):  # Show first 3
        logger.debug(f"Result {i + 1}: chain={pair.chain_id}, pair={pair.base_token.symbol}/{pair.quote_token.symbol}")

    # 5. Latest token profiles
    logger.info("Example 5: Latest token profiles (method: get_latest_token_profiles_async)")
    profiles = await client.get_latest_token_profiles_async()
    logger.info(f"Token profiles retrieved: count={len(profiles)}")
    if profiles:
        token = profiles[0]
        logger.debug(
            f"Latest token: address={token.token_address[:16]}..., "
            f"chain={token.chain_id}, "
            f"description={token.description[:60] + '...' if token.description else None}"
        )

    # 6. Latest boosted tokens
    logger.info("Example 6: Latest boosted tokens (method: get_latest_boosted_tokens_async)")
    boosted = await client.get_latest_boosted_tokens_async()
    logger.info(f"Boosted tokens retrieved: count={len(boosted)}")
    if boosted:
        token = boosted[0]
        logger.debug(f"Latest boost: boost_amount=${token.amount:,.2f}, total_boost=${token.total_amount:,.2f}")

    # 7. Most active tokens
    logger.info("Example 7: Most active tokens (method: get_tokens_most_active_async)")
    active_tokens = await client.get_tokens_most_active_async()
    logger.info(f"Active tokens retrieved: count={len(active_tokens)}")
    for i, token in enumerate(active_tokens[:3]):
        logger.debug(f"Active token {i + 1}: chain={token.chain_id}, total_boost=${token.total_amount:,.2f}")

    # 8. Token order query
    logger.info("Example 8: Token order query (method: get_orders_paid_of_token_async)")
    orders = await client.get_orders_paid_of_token_async("solana", "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
    logger.info(f"Orders retrieved: count={len(orders)}")
    for order in orders[:3]:
        timestamp = datetime.fromtimestamp(order.payment_timestamp / 1000)
        logger.debug(f"Order: type={order.type}, status={order.status}, timestamp={timestamp.isoformat()}")

    logger.info("Demo complete")


if __name__ == "__main__":
    asyncio.run(main())
