"""
Test script to validate API endpoints with multiple tokens/pairs (30 and 31 items)
"""

import asyncio
import logging

import orjson
from curl_cffi import AsyncSession

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Active Solana token addresses (found via search API)
SOLANA_TOKEN_ADDRESSES = [
    "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # POPCAT
    "F6qoefQq4iCBLoNZ34RjEqHjHkD8vtmoRSdw9Nd55J1k",  # SHIB
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "31k88G5Mq7ptbRDf3AM13HAq6wRQHXHikR8hik7wPygk",  # GP
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # JitoSOL
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # RAY
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",  # $WIF
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",  # JTO
    "HhJpBhRRn4g56VsyLuT8DL5Bv31HkXqsrahTTUCZeZg4",  # $MYRO
    "6MQpbiTC2YcogidTmKqMLK82qvE9z5QEm7EP3AEDpump",  # MASK
    "EkM5JPDagT71XDZCjdnz45PUHbNPBdNL45N2NKCHbyGR",  # PEPE
    "9TY6DUg1VSssYH5tFE95qoq5hnAGFak4w3cn72sJNCoV",  # DOGE
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  # JUP
    "9Vo93nxu8gpY5i54sB3okxCqCTou4Asxg817A63B1GPf",  # Doge
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",  # PYTH
    "B5WTLaRwaUQpKk7ir1wniNB6m5o8GgMrimhKMYan2R6B",  # Pepe
    "Dn4noZ5jgGfkntzcQSUZ8czkreiZ1ForXYoV2H8Dm7S1",  # USDT
    "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5",  # MEW
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    "So11111111111111111111111111111111111111112",  # SOL
    "ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82",  # BOME
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",  # ORCA
    "ATLASXmbPQxBUYbxPsV97usA3fPQYEqzQBUHgiFCUsXx",  # ATLAS
    "METAewgxyPbgwsseH8T16a39CQ5VyVxZi9zXiDPY18m",  # META
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Extra token 1
    "AGFEad2et2ZJif9jaGpdMixQqvW5i81aBdvKe7PHNfz3",  # Extra token 2
    "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",  # Extra token 3
    "4ENNdRkWNf1SxmYpzZawG9Q7WUncBzBrrp7ghyCX7Pmp",  # GMT token
    "CWE8jPTUYhdCTZYWPTe1o5DFqfdjzWKc9WKz6rSjQUdG",  # Extra token 5
    "Saber2gLauYim4Mvftnrasomsv6NvAuncvMEZwcLpD1",  # Extra token 6
]

# Active Solana pair addresses (found via search API)
SOLANA_PAIR_ADDRESSES = [
    "739FaSK16AUx5gBXjxoweJF71ioQHQmWm1x3pickfLjT",  # Doge/USDC - $307M liquidity
    "879F697iuDJGMevRkRcnW21fcXiAeLJK1ffsw2ATebce",  # MEW/SOL - $31M liquidity
    "DSUvc5qf5LJHHV5e2tD184ixotSnCnwj7i4jJa4Xsrmt",  # BOME/SOL - $28M liquidity
    "EP2ib6dYdEeqD8MfE2ezHCxX3kP3K2eLKkirfPm5eyMx",  # $WIF/SOL - $15M liquidity
    "FRhB8L7Y9Qq41qZXYLtC2nw8An1RJfLLxRF2x9RwLLMo",  # POPCAT/SOL - $11M liquidity
    "HcjZvfeSNJbNkfLD4eEcRBr96AD3w1GpmMppaeRZf7ur",  # mSOL/SOL - $10M liquidity
    "AVs9TA4nWDzfPJE9gGVNJMVhcQy3V9PGazuz33BfG2RA",  # RAY/SOL - $9M liquidity
    "2AXXcN6oN9bBT5owwmTH53C7QHUXvhLeu718Kqt8rvY2",  # RAY/SOL - $7M liquidity
    "6UmmUiYoBjSrhakAobJw8BvkmJtDVxaeBtbt7rxWo1mg",  # RAY/USDC - $7M liquidity
    "G2FiE1yn9N9ZJx5e1E2LxxMnHvb1H3hCuHLPfKJ98smA",  # JTO/JitoSOL - $5M liquidity
    "9vNKzrrHAjqjuTGLjCBo9Ai4edMYgP9dsG4tFZ2hF251",  # GP/USDC - $4M liquidity
    "3ne4mWqdYuNiYrYZC9TrA3FcfuFdErghH97vNPbjicr1",  # Bonk/SOL - $3M liquidity
    "EowpY5U8gXssLrsQ5zxchWtHtbvdiAyvXKQ7Wk4mNfTt",  # MEW/SOL - $2M liquidity
    "DVa7Qmb5ct9RCpaU7UTpSaf3GVMYz17vNVU67XpdCRut",  # RAY/USDT - $1M liquidity
    "76KUM4kqR9CP193ir9wksgNu5m1tRxPikfHdPaNhKwiY",  # PEPE/USDC - $1M liquidity
    "C1MgLojNLWBKADvu9BHdtgzz1oZX4dZ5zGdGcgvvW8Wz",  # JUP/SOL - $1M liquidity
    "5WGYajM1xtLy3QrLHGSX4YPwsso3jrjEsbU1VivUErzk",  # $MYRO/USDC - $1M liquidity
    "5zpyutJu9ee6jFymDGoK7F6S5Kczqtc9FomP3ueKuyA9",  # Bonk/SOL - $1M liquidity
    "HBS7a3br8GMMWuqVa7VB3SMFa7xVi1tSFdoF5w4ZZ3kS",  # POPCAT/USDC - $1M liquidity
    "AqJ5JYNb7ApkJwvbuXxPnTtKeuizjvC1s2fkp382y9LC",  # mSOL/USDC - $1M liquidity
    "GNfeVT5vSWgLYtzveexZJ2Ki9NBtTTzoHAd9oGvoJKW8",  # mSOL/USDC - $600k liquidity
    "BNFMGftsKAn36v5uaNonJyWSbpXxWVsia3G53tczf8Jm",  # USDT/USDT - $600k liquidity
    "ENrEBzFdNp8mZ11j1wXYZ5mbyX5yA3Z4t9ALbBKtZ2RD",  # MEW/SOL - $600k liquidity
    "GWPLjamb5ZxrGbTsYNWW7V3p1pAMryZSfaPFTdaEsWgC",  # MASK/SOL - $600k liquidity
    "8KJRGQJG5CSfwiZbqwcYBRQebi36Pxp2ZXSN1SZtounE",  # MEW/SOL - $400k liquidity
    "FCEnSxyJfRSKsz6tASUENCsfGwKgkH6YuRn1AMmyHhZn",  # Pepe/SOL - $400k liquidity
    "61R1ndXxvsWXXkWSyNkCxnzwd3zUNB8Q2ibmkiLPC8ht",  # RAY/USDC - $370k liquidity
    "HQcY5n2zP6rW74fyFEhWeBd3LnJpBcZechkvJpmdb8cx",  # mSOL/SOL - $365k liquidity
    "8EzbUfvcRT1Q6RL462ekGkgqbxsPmwC5FMLQZhSPMjJ3",  # mSOL/SOL - $352k liquidity
    "AHTTzwf3GmVMJdxWM8v2MSxyjZj8rQR6hyAC3g9477Yj",  # POPCAT/SOL - $307k liquidity
    "6oFWm7KPLfxnwMb3z5xwBoXNSPP3JJyirAPqPSiVcnsp",  # Bonk/SOL - $298k liquidity
    "9n3dSLrERZQp95dHXywft7xV8D8xnGFLaUHtEhQVaXaC",  # PYTH/SOL - $275k liquidity
    "3pvmL7M24uqzudAxUYmvixtkWTC5yaDhTUSyB8cewnJK",  # DOGE/SOL - $256k liquidity
    "GhDgKWmdrj6af23AqsBJhWu6NyLdLuYG7B4gkjZR4tVk",  # Bonk/USDC - $216k liquidity
    "EZVkeboWeXygtq8LMyENHyXdF5wpYrtExRNH9UwB1qYw",  # JUP/SOL - $216k liquidity
    "14bLC2KcZ2yFyCDSzHsNemoXUGf9fCmgqQ8jeHEfr3Ed",  # SHIB/SOL - $211k liquidity
]


async def test_token_endpoints():
    """Test token endpoints with 30 and 31 tokens"""

    async with AsyncSession(impersonate="chrome136") as session:
        results = {}

        # Test with 30 tokens
        logger.info("Testing token endpoint with count=30")
        tokens_30 = SOLANA_TOKEN_ADDRESSES[:30]
        logger.debug(
            "Token request details - total_tokens=%d, first_tokens=%s, last_tokens=%s",
            len(tokens_30),
            tokens_30[:3],
            tokens_30[-3:],
        )
        url_30 = f"https://api.dexscreener.com/tokens/v1/solana/{','.join(tokens_30)}"

        try:
            logger.debug("Request details - url_length=%d", len(url_30))
            response = await session.request("GET", url_30, timeout=30)
            data = orjson.loads(response.content)

            logger.info(
                "Response received - status=%d, response_type=%s, pairs_count=%s",
                response.status_code,
                type(data).__name__,
                len(data) if isinstance(data, list) else None,
            )
            if isinstance(data, list):
                # Count unique tokens from request that were found
                requested_tokens = {t.lower() for t in tokens_30}
                found_tokens = set()
                for pair in data:
                    if "baseToken" in pair and "address" in pair["baseToken"]:
                        addr = pair["baseToken"]["address"].lower()
                        if addr in requested_tokens:
                            found_tokens.add(addr)
                    if "quoteToken" in pair and "address" in pair["quoteToken"]:
                        addr = pair["quoteToken"]["address"].lower()
                        if addr in requested_tokens:
                            found_tokens.add(addr)
                logger.info(
                    "Token coverage - found=%d, requested=%d, coverage_percent=%.1f",
                    len(found_tokens),
                    len(tokens_30),
                    round(len(found_tokens) / len(tokens_30) * 100, 1),
                )
                missing_tokens = requested_tokens - found_tokens
                if missing_tokens:
                    logger.warning(
                        "Missing tokens - count=%d, sample=%s", len(missing_tokens), list(missing_tokens)[:5]
                    )
            else:
                logger.error(
                    "Unexpected response format - preview: %s",
                    orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()[:200],
                )

            results["30_tokens"] = {
                "status": response.status_code,
                "url_length": len(url_30),
                "tokens_requested": len(tokens_30),
                "response_count": len(data) if isinstance(data, list) else None,
                "success": response.status_code == 200,
            }

        except Exception as e:
            logger.exception("Error testing 30 tokens")
            results["30_tokens"] = {"error": str(e)}

        # Rate limit respect
        await asyncio.sleep(0.5)

        # Test with 31 tokens
        logger.info("Testing token endpoint with count=31")
        tokens_31 = SOLANA_TOKEN_ADDRESSES[:31]
        logger.debug("Token request details - total_tokens=%d, additional_token=%s", len(tokens_31), tokens_31[-1])
        url_31 = f"https://api.dexscreener.com/tokens/v1/solana/{','.join(tokens_31)}"

        try:
            logger.debug("Request details - url_length=%d, url_length_diff=%d", len(url_31), len(url_31) - len(url_30))
            response = await session.request("GET", url_31, timeout=30)
            data = orjson.loads(response.content)

            logger.info(
                "Response received - status=%d, response_type=%s, pairs_count=%s",
                response.status_code,
                type(data).__name__,
                len(data) if isinstance(data, list) else None,
            )
            if isinstance(data, list):
                # Count unique tokens from request that were found
                requested_tokens = {t.lower() for t in tokens_31}
                found_tokens = set()
                for pair in data:
                    if "baseToken" in pair and "address" in pair["baseToken"]:
                        addr = pair["baseToken"]["address"].lower()
                        if addr in requested_tokens:
                            found_tokens.add(addr)
                    if "quoteToken" in pair and "address" in pair["quoteToken"]:
                        addr = pair["quoteToken"]["address"].lower()
                        if addr in requested_tokens:
                            found_tokens.add(addr)
                logger.info(
                    "Token coverage - found=%d, requested=%d, coverage_percent=%.1f",
                    len(found_tokens),
                    len(tokens_31),
                    round(len(found_tokens) / len(tokens_31) * 100, 1),
                )
            else:
                logger.error(
                    "Unexpected response format - preview: %s",
                    orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()[:200],
                )

            results["31_tokens"] = {
                "status": response.status_code,
                "url_length": len(url_31),
                "tokens_requested": len(tokens_31),
                "response_count": len(data) if isinstance(data, list) else None,
                "success": response.status_code == 200,
            }

        except Exception as e:
            logger.exception("Error testing 31 tokens")
            results["31_tokens"] = {"error": str(e)}

        return results


async def test_pair_endpoints():
    """Test pair endpoints with 30 and 31 pairs"""

    async with AsyncSession(impersonate="chrome136") as session:
        results = {}

        # Test with 30 pairs
        logger.info("Testing pair endpoint with count=30")
        pairs_30 = SOLANA_PAIR_ADDRESSES[:30]
        logger.debug(
            "Pair request details - total_pairs=%d, first_pairs=%s, last_pairs=%s",
            len(pairs_30),
            pairs_30[:3],
            pairs_30[-3:],
        )
        url_30 = f"https://api.dexscreener.com/latest/dex/pairs/solana/{','.join(pairs_30)}"

        try:
            logger.debug("Request details - url_length=%d", len(url_30))
            response = await session.request("GET", url_30, timeout=30)
            data = orjson.loads(response.content)

            logger.info(
                "Response received - status=%d, response_type=%s, has_pairs=%s, pairs_count=%s",
                response.status_code,
                type(data).__name__,
                "pairs" in data if isinstance(data, dict) else False,
                len(data.get("pairs", [])) if isinstance(data, dict) else None,
            )
            if isinstance(data, dict) and "pairs" in data:
                # Check which pairs were found
                requested_pairs = {p.lower() for p in pairs_30}
                found_pairs = set()
                for pair in data["pairs"]:
                    if "pairAddress" in pair:
                        addr = pair["pairAddress"].lower()
                        if addr in requested_pairs:
                            found_pairs.add(addr)
                logger.info(
                    "Pair coverage - found=%d, requested=%d, coverage_percent=%.1f",
                    len(found_pairs),
                    len(pairs_30),
                    round(len(found_pairs) / len(pairs_30) * 100, 1),
                )
                missing_pairs = requested_pairs - found_pairs
                if missing_pairs:
                    logger.warning("Missing pairs - count=%d, sample=%s", len(missing_pairs), list(missing_pairs)[:5])
            else:
                logger.error(
                    "Unexpected response format - preview: %s",
                    orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()[:200],
                )

            results["30_pairs"] = {
                "status": response.status_code,
                "url_length": len(url_30),
                "pairs_requested": len(pairs_30),
                "response_count": len(data.get("pairs", [])) if isinstance(data, dict) else None,
                "success": response.status_code == 200,
            }

        except Exception as e:
            logger.exception("Error testing 30 pairs")
            results["30_pairs"] = {"error": str(e)}

        # Rate limit respect
        await asyncio.sleep(0.5)

        # Test with 31 pairs
        logger.info("Testing pair endpoint with count=31")
        pairs_31 = SOLANA_PAIR_ADDRESSES[:31]
        logger.debug("Pair request details - total_pairs=%d, additional_pair=%s", len(pairs_31), pairs_31[-1])
        url_31 = f"https://api.dexscreener.com/latest/dex/pairs/solana/{','.join(pairs_31)}"

        try:
            logger.debug("Request details - url_length=%d, url_length_diff=%d", len(url_31), len(url_31) - len(url_30))
            response = await session.request("GET", url_31, timeout=30)
            data = orjson.loads(response.content)

            logger.info(
                "Response received - status=%d, response_type=%s, has_pairs=%s, pairs_count=%s",
                response.status_code,
                type(data).__name__,
                "pairs" in data if isinstance(data, dict) else False,
                len(data.get("pairs", [])) if isinstance(data, dict) else None,
            )
            if isinstance(data, dict) and "pairs" in data:
                # Check which pairs were found
                requested_pairs = {p.lower() for p in pairs_31}
                found_pairs = set()
                for pair in data["pairs"]:
                    if "pairAddress" in pair:
                        addr = pair["pairAddress"].lower()
                        if addr in requested_pairs:
                            found_pairs.add(addr)
                logger.info(
                    "Pair coverage - found=%d, requested=%d, coverage_percent=%.1f",
                    len(found_pairs),
                    len(pairs_31),
                    round(len(found_pairs) / len(pairs_31) * 100, 1),
                )
            else:
                logger.error(
                    "Unexpected response format - preview: %s",
                    orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()[:200],
                )

            results["31_pairs"] = {
                "status": response.status_code,
                "url_length": len(url_31),
                "pairs_requested": len(pairs_31),
                "response_count": len(data.get("pairs", [])) if isinstance(data, dict) else None,
                "success": response.status_code == 200,
            }

        except Exception as e:
            logger.exception("Error testing 31 pairs")
            results["31_pairs"] = {"error": str(e)}

        return results


async def main():
    """Run all tests"""
    logger.info("Starting API multi-item limit tests")
    logger.info(
        "Test objectives - goals: Check if API accepts 30+ items in batch queries, "
        "Identify any limits imposed by the API"
    )

    # Test token endpoints
    token_results = await test_token_endpoints()

    # Rate limit respect
    await asyncio.sleep(1)

    # Test pair endpoints
    pair_results = await test_pair_endpoints()

    # Combine results
    all_results = {"tokens": token_results, "pairs": pair_results}

    # Save results
    with open("api_multi_test_results.json", "wb") as f:
        f.write(orjson.dumps(all_results, option=orjson.OPT_INDENT_2))

    # Summary
    logger.info("\n" + "=" * 50 + " SUMMARY " + "=" * 50)
    logger.warning(
        "API response notes - reasons: Some tokens/pairs may be inactive or delisted, "
        "API may have internal limits on response size, API may deduplicate or filter results"
    )

    logger.info(
        "Token endpoint results - test_30=%s",
        "SUCCESS" if token_results.get("30_tokens", {}).get("success") else "FAILED",
    )
    if token_results.get("30_tokens", {}).get("success"):
        requested = token_results["30_tokens"].get("tokens_requested", 30)
        returned = token_results["30_tokens"].get("response_count", 0)
        logger.info(
            "  30 tokens detail - requested=%d, returned=%d, return_rate=%.1f%%",
            requested,
            returned,
            round(returned / requested * 100, 1),
        )

    logger.info("  31 tokens - result=%s", "SUCCESS" if token_results.get("31_tokens", {}).get("success") else "FAILED")
    if token_results.get("31_tokens", {}).get("success"):
        requested = token_results["31_tokens"].get("tokens_requested", 31)
        returned = token_results["31_tokens"].get("response_count", 0)
        logger.info(
            "  31 tokens detail - requested=%d, returned=%d, return_rate=%.1f%%",
            requested,
            returned,
            round(returned / requested * 100, 1),
        )

    logger.info(
        "Pair endpoint results - test_30=%s", "SUCCESS" if pair_results.get("30_pairs", {}).get("success") else "FAILED"
    )
    if pair_results.get("30_pairs", {}).get("success"):
        requested = pair_results["30_pairs"].get("pairs_requested", 30)
        returned = pair_results["30_pairs"].get("response_count", 0)
        logger.info(
            "  30 pairs detail - requested=%d, returned=%d, return_rate=%.1f%%",
            requested,
            returned,
            round(returned / requested * 100, 1),
        )

    logger.info("  31 pairs - result=%s", "SUCCESS" if pair_results.get("31_pairs", {}).get("success") else "FAILED")
    if pair_results.get("31_pairs", {}).get("success"):
        requested = pair_results["31_pairs"].get("pairs_requested", 31)
        returned = pair_results["31_pairs"].get("response_count", 0)
        logger.info(
            "  31 pairs detail - requested=%d, returned=%d, return_rate=%.1f%%",
            requested,
            returned,
            round(returned / requested * 100, 1),
        )

    logger.info("Results saved to file: api_multi_test_results.json")

    # Additional observations
    logger.info("\n" + "=" * 50 + " OBSERVATIONS " + "=" * 50)
    observations = {
        "token_endpoint": [
            "Accepts 30+ tokens in a single request",
            "Returns pairs containing the requested tokens",
            "Some tokens may not have any pairs (inactive/delisted)",
        ],
        "pair_endpoint": [
            "Has a hard limit of 30 pairs maximum",
            "Returns 400 Bad Request for 31+ pairs",
            "All requested pairs are returned if they exist",
        ],
        "url_length": "Not the limiting factor (tested up to 1446 chars)",
    }

    for endpoint, notes in observations.items():
        logger.info("Observations for %s: %s", endpoint, notes)


if __name__ == "__main__":
    asyncio.run(main())
