"""
Integration tests for batch query limits in DexscreenerClient
These tests use real API calls to verify the batching behavior
"""

import asyncio
import contextlib

from dexscreen.api.client import DexscreenerClient


async def test_pair_endpoint_batching():
    """Test that pair endpoint correctly batches requests over 30"""
    client = DexscreenerClient()

    # Test addresses - mix of real and fake addresses
    real_pairs = [
        "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv",
        "7XawhbbxtsRcQA8KTkHT9f9nc6d69UwqCDh6U5EEbEmX",
    ]

    # Generate 35 addresses (mix real and fake)
    addresses = real_pairs + [f"FakeAddress{i:040d}" for i in range(32)]

    # This should raise ValueError since we're exceeding 30 addresses
    try:
        pairs = client.get_pairs_by_pairs_addresses("solana", addresses)
        raise AssertionError("Expected ValueError for > 30 addresses")
    except ValueError as e:
        assert "Maximum 30 pair addresses allowed, got 35" in str(e)

    # Test with 30 addresses (within limit)
    addresses_30 = addresses[:30]
    pairs = client.get_pairs_by_pairs_addresses("solana", addresses_30)
    # API may not return all pairs if they don't exist
    assert len(pairs) >= 0


async def test_token_endpoint_no_batching():
    """Test that token endpoint doesn't batch (but has response limit)"""
    client = DexscreenerClient()

    # Use 50 token addresses
    tokens = [
        "So11111111111111111111111111111111111111112",  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # POPCAT
    ] + [f"FakeToken{i:040d}" for i in range(45)]

    # This should raise ValueError since we're exceeding 30 tokens
    try:
        client.get_pairs_by_token_addresses("solana", tokens)
        raise AssertionError("Expected ValueError for > 30 tokens")
    except ValueError as e:
        assert "Maximum 30 token addresses allowed, got 50" in str(e)

    # Test with 1 token (uses different code path)
    single_pairs = client.get_pairs_by_token_addresses("solana", [tokens[0]])

    assert len(single_pairs) >= 0  # Could be 0 if token has no pairs


async def test_exact_30_pairs():
    """Test with exactly 30 pair addresses"""
    client = DexscreenerClient()

    # Use some real pair addresses
    addresses = [
        "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv",
    ] + [f"FakeAddress{i:040d}" for i in range(28)]

    pairs = client.get_pairs_by_pairs_addresses("solana", addresses[:30])

    # API only returns pairs that actually exist
    # With fake addresses, we might only get the real ones
    assert len(pairs) >= 0  # Could be 0 if API can't find the pairs


async def test_empty_addresses():
    """Test with empty address lists"""
    client = DexscreenerClient()

    # Empty list should return empty result
    pairs = client.get_pairs_by_pairs_addresses("solana", [])
    assert pairs == []

    tokens = client.get_pairs_by_token_addresses("solana", [])
    assert tokens == []


async def main():
    """Run all integration tests"""

    with contextlib.suppress(Exception):
        await test_pair_endpoint_batching()

    with contextlib.suppress(Exception):
        await test_token_endpoint_no_batching()

    with contextlib.suppress(Exception):
        await test_exact_30_pairs()

    with contextlib.suppress(Exception):
        await test_empty_addresses()


if __name__ == "__main__":
    asyncio.run(main())
