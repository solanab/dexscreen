"""
Test script to validate API endpoints and get real response data
"""

import asyncio
from typing import cast

import orjson
from curl_cffi import AsyncSession
from curl_cffi.requests.session import HttpMethod


async def test_api_endpoints():
    """Test all API endpoints to get real response data"""

    async with AsyncSession(impersonate="chrome136") as session:
        endpoints = [
            # Token profiles endpoints
            (
                "GET",
                "https://api.dexscreener.com/token-profiles/latest/v1",
                "Latest Token Profiles",
            ),
            # Lasted boosts endpoints
            ("GET", "https://api.dexscreener.com/token-boosts/latest/v1", "Latest Boosted Tokens"),
            # Top boosts endpoints
            ("GET", "https://api.dexscreener.com/token-boosts/top/v1", "Top Boosted Tokens"),
            # Orders endpoint
            (
                "GET",
                "https://api.dexscreener.com/orders/v1/solana/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "Orders for Token",
            ),
            # Pair endpoints
            ## single
            (
                "GET",
                "https://api.dexscreener.com/latest/dex/pairs/solana/JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
                "Get Single Pair",
            ),
            ## multiple
            (
                "GET",
                "https://api.dexscreener.com/latest/dex/pairs/solana/JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN,So11111111111111111111111111111111111111112",
                "Get Multiple Pairs",
            ),
            # Search endpoint
            ("GET", "https://api.dexscreener.com/latest/dex/search?q=SOL/USDC", "Search Pairs"),
            # Pool endpoints
            (
                "GET",
                "https://api.dexscreener.com/token-pairs/v1/solana/JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
                "Get Single Pool",
            ),
            # Token endpoints
            ## single
            (
                "GET",
                "https://api.dexscreener.com/tokens/v1/solana/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "Get Single Token ",
            ),
            ## multiple
            (
                "GET",
                "https://api.dexscreener.com/tokens/v1/solana/So11111111111111111111111111111111111111112,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "Get Multiple Tokens ",
            ),
        ]

        results = {}

        for method, url, name in endpoints:
            try:
                response = await session.request(cast(HttpMethod, method.upper()), url, timeout=30)
                data = orjson.loads(response.content)

                # Pretty print response

                results[name] = {"url": url, "status": response.status_code, "data": data}

            except Exception as e:
                results[name] = {"url": url, "error": str(e)}

            # Rate limit respect
            await asyncio.sleep(0.5)

        # Save full results
        with open("api_test_results.json", "wb") as f:
            f.write(orjson.dumps(results, option=orjson.OPT_INDENT_2))


if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
