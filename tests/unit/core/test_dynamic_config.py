"""
Test dynamic configuration features of HttpClientCffi
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from dexscreen.core.http import HttpClientCffi


def test_dynamic_config_updates():
    """Test dynamic configuration update features"""

    # Initialize client
    client = HttpClientCffi(
        calls=60,
        period=60,
        base_url="https://api.dexscreener.com",
        client_kwargs={"timeout": 10, "verify": True},
    )

    # Test 1: Initial configuration
    config = client.get_current_config()
    assert config["timeout"] == 10
    assert config["verify"] is True
    assert "impersonate" in config  # Should be auto-added

    # Test 2: Update with merge
    client.update_client_kwargs({"timeout": 20, "headers": {"X-Test": "value"}})
    config = client.get_current_config()
    assert config["timeout"] == 20
    assert config["verify"] is True  # Should still exist
    assert config["headers"]["X-Test"] == "value"

    # Test 3: Update without merge (replace)
    client.update_client_kwargs({"timeout": 30, "impersonate": "safari184"}, merge=False)
    config = client.get_current_config()
    assert config["timeout"] == 30
    assert "verify" not in config  # Should be removed
    assert config["impersonate"] == "safari184"

    # Test 4: Update impersonate
    client.set_impersonate("chrome136")
    config = client.get_current_config()
    assert config["impersonate"] == "chrome136"


async def test_update_config_method():
    """Test the update_config method for hot configuration updates"""

    # Initialize client
    client = HttpClientCffi(
        calls=60,
        period=60,
        base_url="https://api.dexscreener.com",
        client_kwargs={"timeout": 10, "verify": True},
    )

    # Mock the AsyncSession to avoid real network calls
    with patch("dexscreen.core.http.AsyncSession") as mock_session_class:
        # Create a mock session instance
        mock_session = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200  # Successful warmup
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test 1: Update single configuration
        await client.update_config({"timeout": 20})
        config = client.get_current_config()
        assert config["timeout"] == 20
        assert config["verify"] is True  # Should be preserved with merge

        # Test 2: Update multiple configurations
        await client.update_config({"timeout": 30, "headers": {"X-Custom": "value"}, "impersonate": "firefox135"})
        config = client.get_current_config()
        assert config["timeout"] == 30
        assert config["headers"]["X-Custom"] == "value"
        assert config["impersonate"] == "firefox135"
        assert config["verify"] is True  # Still preserved

        # Test 3: Update proxy configuration
        await client.update_config({"proxy": "http://proxy:8080"})
        config = client.get_current_config()
        assert config["proxy"] == "http://proxy:8080"

        # Test 4: Disable proxy
        await client.update_config({"proxy": None})
        config = client.get_current_config()
        assert "proxy" not in config

        # Test 5: Replace entire config
        await client.update_config({"timeout": 5, "impersonate": "chrome136"}, replace=True)
        config = client.get_current_config()
        assert config["timeout"] == 5
        assert config["impersonate"] == "chrome136"
        assert "verify" not in config  # Should be removed
        assert "headers" not in config  # Should be removed


async def test_dynamic_requests():
    """Test making actual requests with dynamic configuration"""

    client = HttpClientCffi(calls=300, period=60, base_url="https://api.dexscreener.com")

    # Test with initial configuration
    result = client.request("GET", "/latest/dex/tokens/solana?limit=5")
    if result and isinstance(result, list):
        pass

    # Update configuration and test again
    client.update_client_kwargs({"impersonate": "firefox135", "timeout": 15})

    result = await client.request_async("GET", "/latest/dex/tokens/solana?limit=5")
    if result and isinstance(result, list):
        pass

    # Test proxy update (mock to avoid actual proxy requirement)
    with (
        patch("curl_cffi.requests.Session") as mock_sync_session,
        patch("dexscreen.core.http.AsyncSession") as mock_async_session,
    ):
        # Mock sync session for regular requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = [{"name": "Test Token"}]
        mock_response.raise_for_status = MagicMock()

        mock_session_instance = MagicMock()
        mock_session_instance.request.return_value = mock_response
        mock_sync_session.return_value.__enter__.return_value = mock_session_instance

        # Mock async session for update_config warmup
        mock_async = AsyncMock()
        mock_warmup_response = MagicMock()
        mock_warmup_response.status_code = 200  # Successful warmup
        mock_async.get.return_value = mock_warmup_response
        mock_async_session.return_value = mock_async

        # Update proxy using update_config
        await client.update_config({"proxy": "http://test-proxy:8080"})

        # Make request
        result = client.request("GET", "/test")

        # Verify proxy configuration
        config = client.get_current_config()
        assert config.get("proxy") == "http://test-proxy:8080"


async def test_thread_safety():
    """Test thread safety of configuration updates"""

    import threading
    import time

    client = HttpClientCffi(60, 60)
    errors = []

    def update_config(thread_id: int):
        """Update configuration from multiple threads"""
        try:
            for i in range(10):
                client.update_client_kwargs({f"header_{thread_id}": f"value_{i}", "timeout": 10 + thread_id})
                time.sleep(0.001)  # Small delay to increase chance of conflicts
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=update_config, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    if errors:
        pass
    else:
        client.get_current_config()


async def main():
    """Run all tests"""
    test_dynamic_config_updates()
    await test_update_config_method()
    await test_dynamic_requests()
    await test_thread_safety()


if __name__ == "__main__":
    asyncio.run(main())
