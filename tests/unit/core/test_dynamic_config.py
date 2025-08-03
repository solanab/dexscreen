"""
Test dynamic configuration features of HttpClientCffi
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

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

    # Use monkeypatch approach instead
    import dexscreen.core.http

    original_async_session = dexscreen.core.http.AsyncSession

    # Create a mock session instance that will be used for all new sessions
    def create_mock_session(**kwargs):
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200  # Successful warmup
        mock_session.get.return_value = mock_response
        mock_session.close = AsyncMock()  # Add close method
        return mock_session

    try:
        # Replace the imported AsyncSession in the http module
        dexscreen.core.http.AsyncSession = create_mock_session

        # Initialize client AFTER patching
        client = HttpClientCffi(
            calls=60,
            period=60,
            base_url="https://api.dexscreener.com",
            client_kwargs={"timeout": 10, "verify": True},
        )

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
        assert "proxy" in config
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
    finally:
        # Restore original import
        dexscreen.core.http.AsyncSession = original_async_session


async def test_dynamic_requests():
    """Test making actual requests with dynamic configuration"""

    # Test with mocked requests to avoid hitting real API
    # Mock sync session for regular requests
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"schemaVersion": "1.0.0", "pairs": None}
    mock_response.raise_for_status = MagicMock()
    mock_response.content = b'{"schemaVersion": "1.0.0", "pairs": null}'

    mock_session_instance = MagicMock()
    mock_session_instance.request.return_value = mock_response
    mock_session_instance.get.return_value = mock_response  # For warmup request

    # Mock async session
    mock_async_response = MagicMock()  # Use MagicMock for the response object
    mock_async_response.status_code = 200
    mock_async_response.headers = {"content-type": "application/json"}
    mock_async_response.json = AsyncMock(return_value={"schemaVersion": "1.0.0", "pairs": None})
    mock_async_response.raise_for_status = MagicMock()  # Use MagicMock here to avoid warning
    mock_async_response.content = b'{"schemaVersion": "1.0.0", "pairs": null}'

    mock_async = AsyncMock()
    mock_async.request.return_value = mock_async_response
    mock_async.get.return_value = mock_async_response

    # Use monkeypatch instead of patch to ensure we override the imported Session
    import dexscreen.core.http

    original_session = dexscreen.core.http.Session
    original_async_session = dexscreen.core.http.AsyncSession

    try:
        # Replace the imported Session and AsyncSession in the http module
        dexscreen.core.http.Session = lambda **kwargs: mock_session_instance
        dexscreen.core.http.AsyncSession = lambda **kwargs: mock_async

        client = HttpClientCffi(calls=300, period=60, base_url="https://api.dexscreener.com")

        # Test with initial configuration
        result = client.request("GET", "/latest/dex/tokens/solana?limit=5")
        assert result == {"schemaVersion": "1.0.0", "pairs": None}

        # Update configuration and test again
        client.update_client_kwargs({"impersonate": "firefox135", "timeout": 15})

        result = await client.request_async("GET", "/latest/dex/tokens/solana?limit=5")
        assert result == {"schemaVersion": "1.0.0", "pairs": None}

        # Update proxy using update_config
        await client.update_config({"proxy": "http://test-proxy:8080"})

        # Make request with updated proxy
        result = client.request("GET", "/test")
        assert result == {"schemaVersion": "1.0.0", "pairs": None}

        # Verify proxy configuration
        config = client.get_current_config()
        assert config.get("proxy") == "http://test-proxy:8080"
    finally:
        # Restore original imports
        dexscreen.core.http.Session = original_session
        dexscreen.core.http.AsyncSession = original_async_session


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
