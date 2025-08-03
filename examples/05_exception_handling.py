#!/usr/bin/env python3
"""
Example demonstrating comprehensive exception handling with the dexscreen SDK.

This example shows how to handle different types of errors that can occur
when using the dexscreen API, including proper retry logic and error categorization.
"""

import asyncio
import logging
from typing import Optional

from dexscreen import (
    # Exception categories
    APIError,
    DexscreenerClient,
    InvalidAddressError,
    InvalidChainError,
    NetworkError,
    # Specific exceptions
    RateLimitError,
    StreamError,
    SubscriptionError,
    TimeoutError,
    ValidationError,
    get_error_category,
    # Utility functions
    is_retryable_error,
    should_wait_before_retry,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RobustDexscreenClient:
    """
    A wrapper around DexscreenerClient that demonstrates robust error handling.
    """

    def __init__(self, max_retries: int = 3):
        self.client = DexscreenerClient()
        self.max_retries = max_retries

    async def get_pair_with_retry(self, address: str) -> Optional[dict]:
        """
        Get a token pair with automatic retry logic for retryable errors.
        """
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempting to fetch pair {address} (attempt {attempt + 1})")
                pair = await self.client.get_pair_async(address)

                if pair is None:
                    logger.warning(f"No pair found for address {address}")
                    return None

                logger.info(f"Successfully fetched pair: {pair.base_token.symbol}/{pair.quote_token.symbol}")
                return pair.model_dump()

            except RateLimitError as e:
                logger.warning(f"Rate limit exceeded: {e}")
                if attempt < self.max_retries and e.retry_after:
                    logger.info(f"Waiting {e.retry_after}s before retry...")
                    await asyncio.sleep(e.retry_after)
                    continue
                raise

            except TimeoutError as e:
                logger.warning(f"Request timed out: {e}")
                if attempt < self.max_retries:
                    wait_time = should_wait_before_retry(e) or 2.0
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except NetworkError as e:
                logger.error(f"Network error: {e}")
                if attempt < self.max_retries and is_retryable_error(e):
                    wait_time = should_wait_before_retry(e) or 5.0
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except ValidationError as e:
                # Validation errors are usually not retryable
                logger.error(f"Validation error (not retrying): {e}")
                if isinstance(e, InvalidAddressError):
                    logger.error(f"Invalid address format: {e.address}")
                raise

            except APIError as e:
                # Generic API error handling
                logger.error(f"API error: {e}")
                category = get_error_category(e)
                logger.info(f"Error category: {category}")

                if attempt < self.max_retries and is_retryable_error(e):
                    wait_time = should_wait_before_retry(e) or 3.0
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                raise

        return None

    async def subscribe_with_error_handling(self, chain_id: str, pair_addresses: list[str]):
        """
        Subscribe to pair updates with comprehensive error handling.
        """

        def handle_pair_update(pair):
            logger.info(f"Received update for {pair.base_token.symbol}: ${pair.price_usd}")

        try:
            logger.info(f"Subscribing to {len(pair_addresses)} pairs on {chain_id}")
            await self.client.subscribe_pairs(chain_id, pair_addresses, handle_pair_update)

            # Keep the subscription running
            logger.info("Subscription active. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)

        except InvalidChainError as e:
            logger.error(f"Invalid chain ID: {e.chain_id}")
            if e.supported_chains:
                logger.info(f"Supported chains: {', '.join(e.supported_chains)}")

        except SubscriptionError as e:
            logger.error(f"Subscription failed: {e}")
            logger.info(f"Operation: {e.operation}, Type: {e.subscription_type}")

        except StreamError as e:
            logger.error(f"Streaming error: {e}")
            category = get_error_category(e)
            logger.info(f"Stream error category: {category}")

        except KeyboardInterrupt:
            logger.info("Shutting down subscription...")
            await self.client.close_streams()


async def demonstrate_exception_handling():
    """
    Demonstrate various exception handling scenarios.
    """
    client = RobustDexscreenClient(max_retries=2)

    # Example 1: Handle invalid address
    logger.info("=== Example 1: Invalid Address Handling ===")
    try:
        await client.get_pair_with_retry("invalid_address_format")
    except InvalidAddressError as e:
        logger.info(f"✓ Caught InvalidAddressError: {e}")
    except Exception as e:
        logger.info(f"✓ Caught other error: {type(e).__name__}: {e}")

    # Example 2: Valid address (might succeed or fail based on network)
    logger.info("\n=== Example 2: Valid Address Request ===")
    try:
        # Use a known Solana token pair address
        result = await client.get_pair_with_retry("58oQChx4yWmvKdwLLZzBi4ChoCcfbPfnc9XqzKG1wUE6")
        if result:
            logger.info("✓ Successfully fetched pair data")
        else:
            logger.info("i No pair found for this address")
    except Exception as e:
        logger.info(f"✓ Handled error: {type(e).__name__}: {e}")
        logger.info(f"  Error category: {get_error_category(e)}")
        logger.info(f"  Is retryable: {is_retryable_error(e)}")

    # Example 3: Configuration error
    logger.info("\n=== Example 3: Configuration Error Handling ===")
    try:
        # This would trigger if we had invalid configuration
        from dexscreen import InvalidConfigError

        raise InvalidConfigError(
            "Invalid browser impersonation",
            config_key="impersonate",
            config_value="invalid_browser",
            expected_values=["chrome", "firefox", "safari"],
        )
    except InvalidConfigError as e:
        logger.info(f"✓ Caught InvalidConfigError: {e}")
        logger.info(f"  Config key: {e.config_key}")
        logger.info(f"  Invalid value: {e.config_value}")
        logger.info(f"  Valid options: {e.expected_values}")

    logger.info("\n=== Exception Handling Demo Complete ===")


async def main():
    """
    Main function to run the exception handling examples.
    """
    try:
        await demonstrate_exception_handling()
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in demo: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
