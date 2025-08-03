#!/usr/bin/env python3
"""
Enhanced Logging Demo

This example demonstrates the comprehensive logging enhancements across the dexscreen library,
including structured logging, correlation IDs, request tracking, and error context preservation.
"""

import asyncio
import contextlib
import json
import logging
from pathlib import Path

from dexscreen import DexscreenerClient
from dexscreen.stream.polling import PollingStream
from dexscreen.utils import (
    FilterPresets,
    get_request_tracker,
    setup_structured_logging,
    track_request,
)


def setup_demo_logging():
    """Set up structured logging for the demo"""
    # Configure structured logging with JSON output
    setup_structured_logging(
        level=logging.DEBUG,
        use_structured_format=True,
        include_correlation_id=True,
        include_context=True,
    )

    # Also add console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)


@track_request("demo_api_call", include_args=True, include_result=True)
def demonstrate_sync_api_calls():
    """Demonstrate enhanced logging in synchronous API calls"""

    client = DexscreenerClient()

    # Test successful requests
    try:
        trending = client.get_latest_token_profiles()

        if trending:
            pair = trending[0]
            detailed = client.get_pair(pair.token_address)
            if detailed:
                pass
            else:
                pass

    except Exception:
        pass
        # Error context will be automatically logged with correlation ID

    return "sync_demo_completed"


@track_request("demo_async_api_call", include_args=True, include_result=True)
async def demonstrate_async_api_calls():
    """Demonstrate enhanced logging in asynchronous API calls"""

    client = DexscreenerClient()

    try:
        trending = await client.get_latest_token_profiles_async()

        if trending:
            pair = trending[0]
            detailed = await client.get_pair_async(pair.token_address)
            if detailed:
                pass
            else:
                pass

    except Exception:
        pass
        # Error context will be automatically logged with correlation ID

    return "async_demo_completed"


@track_request("demo_streaming", include_args=True)
async def demonstrate_streaming_with_logging():
    """Demonstrate enhanced logging in streaming operations"""

    client = DexscreenerClient()
    stream = PollingStream(client, interval=2.0, filter_changes=True)

    # Set up callback with logging
    update_count = 0

    def on_pair_update(pair):
        nonlocal update_count
        update_count += 1

    try:
        await stream.connect()

        # Subscribe to a popular Solana pair
        solana_pair = "DSUvc5qf5LJHHV5e2tD184ixotSnCnwj7i4jJa4Xsrmt"  # BOME/SOL
        await stream.subscribe("solana", solana_pair, on_pair_update)

        # Let it run for a bit to collect some data
        await asyncio.sleep(10)

        # Check streaming stats
        stream.get_streaming_stats()

    except Exception:
        pass

    finally:
        await stream.disconnect()

    return f"streaming_demo_completed_with_{update_count}_updates"


def demonstrate_rate_limiting_and_filtering():
    """Demonstrate rate limiting and filtering with enhanced logging"""

    # Create a filter with logging
    filter_config = FilterPresets.ui_friendly()
    from dexscreen.utils.filters import TokenPairFilter

    pair_filter = TokenPairFilter(filter_config)

    # Simulate some filter operations

    # This would normally be done with real TokenPair objects
    # For demo purposes, we'll just log the filter stats
    pair_filter.log_stats("demo_filter_check")


def demonstrate_error_handling():
    """Demonstrate enhanced error logging and context preservation"""

    client = DexscreenerClient()

    # Test with invalid data to trigger error logging
    with contextlib.suppress(Exception):
        # This should trigger error handling with enhanced context
        client.get_pair("invalid_address_format")

    # Test rate limiting
    # client._client_300rpm.log_stats("demo_rate_limit_check")  # Method not available


@track_request("full_demo", include_result=True)
async def run_full_demo():
    """Run the complete enhanced logging demonstration"""

    # Track the demo with correlation IDs
    tracker = get_request_tracker()

    try:
        # Sync API calls
        demonstrate_sync_api_calls()

        # Async API calls
        await demonstrate_async_api_calls()

        # Streaming
        await demonstrate_streaming_with_logging()

        # Rate limiting and filtering
        demonstrate_rate_limiting_and_filtering()

        # Error handling
        demonstrate_error_handling()

        # Show active requests
        tracker.log_active_requests()

        return "full_demo_success"

    except Exception:
        return "full_demo_failed"


def show_log_samples():
    """Show sample log entries from the demo"""
    log_file = Path("demo_logs.jsonl")

    if not log_file.exists():
        return

    with open(log_file) as f:
        lines = f.readlines()

        # Show first few and last few entries
        sample_lines = lines[:3] + lines[-3:] if len(lines) > 6 else lines

        for _i, line in enumerate(sample_lines):
            try:
                log_entry = json.loads(line.strip())
                if "context" in log_entry:
                    pass
            except json.JSONDecodeError:
                pass


if __name__ == "__main__":
    # Set up logging first
    setup_demo_logging()

    # Run the demo
    asyncio.run(run_full_demo())

    # Show some sample logs
    show_log_samples()
