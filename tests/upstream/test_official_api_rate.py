"""
Test script to validate rate limits for all API endpoints
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from curl_cffi import AsyncSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    """Result of a single request"""

    endpoint_name: str
    request_id: int
    request_time: float
    response_time: Optional[float]
    status_code: Optional[int]
    error: Optional[str]


@dataclass
class EndpointConfig:
    """Configuration for each endpoint"""

    name: str
    url: str
    rate_limit: int  # 60 or 300 rpm
    requests_per_second: int  # 5 for all
    test_duration: int  # 12 or 60 seconds


# Define all endpoints with their configurations
ENDPOINTS = [
    # 300 RPM endpoints (5 requests/second, 60 seconds)
    EndpointConfig(
        name="Get Single Pair",
        url="https://api.dexscreener.com/latest/dex/pairs/solana/JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        rate_limit=300,
        requests_per_second=5,
        test_duration=60,
    ),
    EndpointConfig(
        name="Get Token Pairs",
        url="https://api.dexscreener.com/tokens/v1/solana/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        rate_limit=300,
        requests_per_second=5,
        test_duration=60,
    ),
]


async def send_request(
    session: AsyncSession, endpoint: EndpointConfig, request_id: int, start_time: float
) -> RequestResult:
    """Send a single request and record the result"""
    request_time = time.time()

    try:
        response = await session.get(endpoint.url)
        response_end = time.time()
        response_time = response_end - request_time

        return RequestResult(
            endpoint_name=endpoint.name,
            request_id=request_id,
            request_time=request_time,
            response_time=response_time,
            status_code=response.status_code,
            error=None if response.status_code == 200 else f"HTTP {response.status_code}",
        )
    except Exception as e:
        return RequestResult(
            endpoint_name=endpoint.name,
            request_id=request_id,
            request_time=request_time,
            response_time=None,
            status_code=None,
            error=str(e),
        )


async def test_endpoint_continuously(
    session: AsyncSession, endpoint: EndpointConfig, results_list: list[RequestResult]
) -> None:
    """Continuously test a single endpoint - true async pattern"""
    logger.info(
        f"Starting {endpoint.name} - {endpoint.rate_limit} RPM limit, {endpoint.requests_per_second} req/s for {endpoint.test_duration}s"
    )

    start_time = time.time()
    request_id = 0
    interval = 1.0 / endpoint.requests_per_second  # Time between requests

    # Create a task that sends requests at regular intervals
    async def send_requests():
        nonlocal request_id
        next_send_time = start_time

        while time.time() - start_time < endpoint.test_duration:
            request_id += 1

            # Send request without waiting (fire and forget)
            asyncio.create_task(send_and_store_result(session, endpoint, request_id, start_time, results_list))

            # Calculate next send time
            next_send_time += interval
            sleep_time = max(0, next_send_time - time.time())

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                # If behind schedule, update next send time
                next_send_time = time.time()

    await send_requests()


async def send_and_store_result(
    session: AsyncSession,
    endpoint: EndpointConfig,
    request_id: int,
    start_time: float,
    results_list: list[RequestResult],
) -> None:
    """Send request and store result in the list"""
    result = await send_request(session, endpoint, request_id, start_time)
    results_list.append(result)


def analyze_results(results: list[RequestResult], endpoint: EndpointConfig) -> dict:
    """Analyze test results for an endpoint"""
    total_requests = len(results)
    successful_requests = [r for r in results if r.status_code == 200]
    failed_requests = [r for r in results if r.status_code != 200]

    analysis = {
        "endpoint": endpoint.name,
        "rate_limit": endpoint.rate_limit,
        "total_requests": total_requests,
        "expected_requests": endpoint.requests_per_second * endpoint.test_duration,
        "successful_requests": len(successful_requests),
        "failed_requests": len(failed_requests),
        "success_rate": len(successful_requests) / total_requests * 100 if total_requests > 0 else 0,
    }

    # Analyze response times for successful requests
    if successful_requests:
        response_times = [r.response_time for r in successful_requests if r.response_time is not None]
        if response_times:
            analysis["avg_response_time"] = sum(response_times) / len(response_times)
            analysis["min_response_time"] = min(response_times)
            analysis["max_response_time"] = max(response_times)

    # Analyze failures by status code
    if failed_requests:
        status_codes = defaultdict(int)
        for r in failed_requests:
            if r.status_code:
                status_codes[r.status_code] += 1
            else:
                status_codes["error"] += 1
        analysis["failure_breakdown"] = dict(status_codes)

    # Calculate actual request rate
    if results:
        request_times = sorted([r.request_time for r in results])
        duration = request_times[-1] - request_times[0]
        if duration > 0:
            analysis["actual_requests_per_second"] = len(results) / duration

    return analysis


async def test_all_endpoints():
    """Test all endpoints with true async concurrency"""
    async with AsyncSession(impersonate="chrome") as session:
        logger.info("=" * 80)
        logger.info("Starting rate limit tests for all endpoints")
        logger.info("=" * 80)

        # Create shared results lists for each endpoint
        results = [[] for _ in ENDPOINTS]

        # Start all tests concurrently using true async pattern
        all_tasks = []

        # Start 300 RPM endpoint tests
        logger.info("\n### Starting 300 RPM endpoints (5 req/s for 60 seconds each) ###")
        for i, endpoint in enumerate(ENDPOINTS):
            task = asyncio.create_task(test_endpoint_continuously(session, endpoint, results[i]))
            all_tasks.append(task)

        # Wait for all tests to complete
        logger.info("\nAll tests running concurrently...")
        await asyncio.gather(*all_tasks)

        # Allow a bit of time for any remaining requests to complete
        await asyncio.sleep(2)

        # Analyze and display results
        logger.info("\n" + "=" * 80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 80)

        # Analyze 300 RPM endpoints
        logger.info("\n### 300 RPM Endpoints Results (60 seconds test) ###")
        total_success = 0
        total_requests = 0

        for endpoint, endpoint_results in zip(ENDPOINTS, results):
            analysis = analyze_results(endpoint_results, endpoint)
            total_success += analysis["successful_requests"]
            total_requests += analysis["total_requests"]

            logger.info(f"\n{analysis['endpoint']}:")
            logger.info(f"  Total requests: {analysis['total_requests']} (expected: {analysis['expected_requests']})")
            logger.info(f"  Successful: {analysis['successful_requests']} ({analysis['success_rate']:.1f}%)")
            logger.info(f"  Failed: {analysis['failed_requests']}")

            if "avg_response_time" in analysis:
                logger.info(f"  Avg response time: {analysis['avg_response_time']:.3f}s")

            if "actual_requests_per_second" in analysis:
                logger.info(f"  Actual rate: {analysis['actual_requests_per_second']:.2f} req/s")

            if "failure_breakdown" in analysis:
                logger.info(f"  Failures: {analysis['failure_breakdown']}")

        logger.info(
            f"\n300 RPM Total: {total_success}/{total_requests} successful ({total_success / total_requests * 100:.1f}%)"
        )

        # Overall summary
        logger.info("\n" + "=" * 80)
        logger.info("OVERALL SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total requests sent: {total_requests}")
        logger.info(f"Total successful: {total_success}")
        logger.info(f"Overall success rate: {total_success / total_requests * 100:.1f}%")

        # Rate limit analysis
        logger.info("\n### Rate Limit Analysis ###")
        logger.info(
            f"300 RPM endpoints: Expected {300 * len(ENDPOINTS)} requests total in 60s across {len(ENDPOINTS)} endpoints"
        )
        logger.info(f"  Actual: {total_requests} requests")
        logger.info(f"  Rate limit hit: {'Yes' if total_success < total_requests else 'No'}")


if __name__ == "__main__":
    asyncio.run(test_all_endpoints())
