"""
Unit tests for WebSocket client module.

Story 5-1: WebSocket Connection for Failure Notifications
- Task 4.1: Test WebSocket connection establishment
- Task 4.2: Test failure notification message format
- Task 4.3: Test exponential backoff reconnection
- Task 4.4: Test no duplicate notifications
- Task 4.5: Test buffer flush on reconnection
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.selectors.websocket.client import WebSocketClient
from src.selectors.websocket.config import WebSocketConfig
from src.selectors.websocket.models import FailureNotification


# === Test Fixtures ===

@pytest.fixture
def ws_config():
    """Create test WebSocket configuration."""
    return WebSocketConfig(
        url="ws://localhost:8080/notifications",
        max_retries=3,
        base_delay=0.1,
        max_delay=1.0,
        buffer_size=10,
        message_timeout=1.0,
        ping_interval=5.0,
    )


@pytest.fixture
def ws_client(ws_config):
    """Create WebSocket client instance."""
    return WebSocketClient(config=ws_config)


@pytest.fixture
def sample_notification():
    """Create sample failure notification."""
    return FailureNotification.from_failure_event(
        selector_id="team_name",
        page_url="https://example.com/match",
        failure_type="empty_result",
        extractor_id="flashscore_extractor",
        error_message="Result is empty",
    )


# === AC1: WebSocket Connection Establishment Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_establishment(ws_config):
    """Test AC1: WebSocket connection establishment."""
    client = WebSocketClient(config=ws_config)
    
    # Initially not connected
    assert not client.connected
    
    # Mock websocket
    mock_ws = AsyncMock()
    mock_ws.ping = AsyncMock()
    
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        
        result = await client.connect()
        
        assert result is True
        assert client.connected
        mock_connect.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_with_protocols(ws_config):
    """Test AC1: Connection with custom protocols."""
    ws_config.protocols = ["graphql-ws"]
    
    client = WebSocketClient(config=ws_config)
    mock_ws = AsyncMock()
    
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        
        await client.connect()
        
        # Check protocols were passed
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs.get("protocols") == ["graphql-ws"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_with_headers(ws_config):
    """Test AC1: Connection with custom headers."""
    ws_config.headers = {"Authorization": "Bearer token123"}
    
    client = WebSocketClient(config=ws_config)
    mock_ws = AsyncMock()
    
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        
        await client.connect()
        
        # Check headers were passed
        call_kwargs = mock_connect.call_args[1]
        assert "Authorization" in call_kwargs.get("extra_headers", {})


# === AC2: Failure Notification Message Format Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_message_format(sample_notification):
    """Test AC2: Notification message is valid JSON."""
    json_str = sample_notification.to_json()
    
    # Should be valid JSON
    parsed = json.loads(json_str)
    
    # Should have required fields (AC2)
    assert "message_id" in parsed
    assert "selector_id" in parsed
    assert "page_url" in parsed
    assert "timestamp" in parsed
    assert "failure_type" in parsed
    assert "extractor_id" in parsed


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_includes_all_fields(sample_notification):
    """Test AC2: Notification includes selector_id, page_url, timestamp, failure_type."""
    data = sample_notification.model_dump()
    
    assert data["selector_id"] == "team_name"
    assert data["page_url"] == "https://example.com/match"
    assert data["failure_type"] == "empty_result"
    assert data["extractor_id"] == "flashscore_extractor"
    assert data["error_message"] == "Result is empty"


# === AC4: Exponential Backoff Reconnection Tests ===

@pytest.mark.unit
def test_exponential_backoff_calculation(ws_config):
    """Test AC4: Exponential backoff delay calculation."""
    # Attempt 0: base_delay * 2^0 = 0.1
    assert ws_config.calculate_backoff_delay(0) == 0.1
    
    # Attempt 1: base_delay * 2^1 = 0.2
    assert ws_config.calculate_backoff_delay(1) == 0.2
    
    # Attempt 2: base_delay * 2^2 = 0.4
    assert ws_config.calculate_backoff_delay(2) == 0.4
    
    # Attempt exceeding max_delay should be capped
    assert ws_config.calculate_backoff_delay(10) == 1.0  # max_delay


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reconnection_with_backoff(ws_config):
    """Test AC4: Reconnection follows exponential backoff."""
    ws_config.max_retries = 3
    ws_config.base_delay = 0.05
    
    client = WebSocketClient(config=ws_config)
    client._connected = False
    
    mock_ws = AsyncMock()
    
    connect_count = 0
    
    async def mock_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        if connect_count < 3:
            raise Exception("Connection failed")
        return mock_ws
    
    with patch("websockets.connect", side_effect=mock_connect):
        # First two attempts fail, third succeeds
        with patch.object(client, "_notify_status_change"):
            result = await client._attempt_reconnect()
            assert result is True
            assert connect_count == 3


# === AC5: No Duplicate Notifications Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_duplicate_notifications(sample_notification):
    """Test AC5: Duplicate notifications are not sent."""
    client = WebSocketClient(config=ws_config)
    
    # Track sent messages
    sent_messages = []
    
    async def mock_send(msg):
        sent_messages.append(msg)
    
    client._websocket = MagicMock()
    client._websocket.send = mock_send
    client._connected = True
    
    # Send same notification twice
    await client._send_message(sample_notification)
    await client._send_message(sample_notification)
    
    # Should only be sent once
    assert len(sent_messages) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_message_id_generation():
    """Test AC5: Unique message IDs are generated."""
    notif1 = FailureNotification.from_failure_event(
        selector_id="test",
        page_url="http://test.com",
        failure_type="empty_result",
        extractor_id="test_ext",
    )
    
    notif2 = FailureNotification.from_failure_event(
        selector_id="test",
        page_url="http://test.com",
        failure_type="empty_result",
        extractor_id="test_ext",
    )
    
    # Each should have unique ID
    assert notif1.message_id != notif2.message_id


# === Task 3.2: Buffer Flush on Reconnection Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_buffer_flush_on_reconnection(ws_client, sample_notification):
    """Test Task 3.2: Buffer is flushed on reconnection."""
    ws_client._connected = False
    
    # Buffer some notifications
    await ws_client._buffer_notification(sample_notification)
    await ws_client._buffer_notification(sample_notification)
    
    assert ws_client.buffer_size == 2
    
    # Mock connected websocket
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    ws_client._websocket = mock_ws
    ws_client._connected = True
    
    # Flush buffer
    await ws_client._flush_buffer()
    
    # Buffer should be empty
    assert ws_client.buffer_size == 0
    
    # Messages should have been sent
    assert mock_ws.send.call_count == 2


# === Task 3.1: Buffer Overflow Handling Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_buffer_overflow_handling(ws_config):
    """Test Task 3.3: Buffer overflow is handled gracefully."""
    ws_config.buffer_size = 3
    client = WebSocketClient(config=ws_config)
    
    # Fill buffer beyond capacity
    for i in range(5):
        notif = FailureNotification.from_failure_event(
            selector_id=f"selector_{i}",
            page_url="http://test.com",
            failure_type="empty_result",
            extractor_id="test",
        )
        await client._buffer_notification(notif)
    
    # Buffer should be capped at max size
    assert client.buffer_size == 3


# === Task 4.1: WebSocket Connection Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect(ws_client):
    """Test WebSocket disconnection."""
    mock_ws = AsyncMock()
    ws_client._websocket = mock_ws
    ws_client._connected = True
    
    await ws_client.disconnect()
    
    assert not ws_client.connected
    mock_ws.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_context_manager(ws_config):
    """Test async context manager for session."""
    client = WebSocketClient(config=ws_config)
    mock_ws = AsyncMock()
    
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        
        async with client.session():
            assert client._running
        
        assert not client._running


# === Integration Tests ===

@pytest.mark.unit
def test_websocket_config_from_env():
    """Test loading config from environment variables."""
    import os
    
    # Set environment variables
    os.environ["WEBSOCKET_NOTIFICATION_URL"] = "ws://test:9999/ws"
    os.environ["WEBSOCKET_MAX_RETRIES"] = "10"
    os.environ["WEBSOCKET_BUFFER_SIZE"] = "50"
    
    try:
        from src.selectors.websocket.config import load_websocket_config
        
        config = load_websocket_config()
        
        assert config.url == "ws://test:9999/ws"
        assert config.max_retries == 10
        assert config.buffer_size == 50
        assert config.enabled is True
    finally:
        # Clean up
        os.environ.pop("WEBSOCKET_NOTIFICATION_URL", None)
        os.environ.pop("WEBSOCKET_MAX_RETRIES", None)
        os.environ.pop("WEBSOCKET_BUFFER_SIZE", None)


@pytest.mark.unit
def test_notification_from_failure_event():
    """Test creating notification from failure event data."""
    notif = FailureNotification.from_failure_event(
        selector_id="test_selector",
        page_url="https://test.com/page",
        failure_type="exception",
        extractor_id="test_extractor",
        error_message="Test error",
        confidence_score=0.5,
    )
    
    assert notif.selector_id == "test_selector"
    assert notif.page_url == "https://test.com/page"
    assert notif.failure_type == "exception"
    assert notif.extractor_id == "test_extractor"
    assert notif.error_message == "Test error"
    assert notif.confidence_score == 0.5
    assert notif.message_id is not None


# === AC1: Binary Message Support Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_binary_message_support(ws_client):
    """Test AC1: Binary message support."""
    ws_client._websocket = AsyncMock()
    ws_client._connected = True
    
    binary_data = b"\x00\x01\x02\x03"
    result = await ws_client.send_binary(binary_data)
    
    assert result is True
    ws_client._websocket.send.assert_called_once_with(binary_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_binary_message_when_disconnected(ws_client):
    """Test AC1: Binary message fails when not connected."""
    ws_client._connected = False
    ws_client._websocket = None
    
    result = await ws_client.send_binary(b"test")
    
    assert result is False


# === AC3: Latency Monitoring Tests ===

@pytest.mark.unit
def test_average_latency_tracking(ws_client):
    """Test AC3: Average latency calculation."""
    ws_client._notification_latencies.append(50.0)
    ws_client._notification_latencies.append(100.0)
    ws_client._notification_latencies.append(150.0)
    
    assert ws_client.average_latency_ms == 100.0


@pytest.mark.unit
def test_max_latency_tracking(ws_client):
    """Test AC3: Maximum latency tracking."""
    ws_client._notification_latencies.append(50.0)
    ws_client._notification_latencies.append(200.0)
    ws_client._notification_latencies.append(100.0)
    
    assert ws_client.max_latency_ms == 200.0


@pytest.mark.unit
def test_latency_properties_empty(ws_config):
    """Test AC3: Latency properties return None when empty."""
    from src.selectors.websocket.client import WebSocketClient
    
    client = WebSocketClient(config=ws_config)
    
    assert client.average_latency_ms is None
    assert client.max_latency_ms is None


# === Background Task Management Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_background_task_stored(ws_client):
    """Test that background task is stored for management."""
    mock_ws = AsyncMock()
    
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        
        await ws_client.start_background()
        
        # Task should be stored
        assert ws_client._background_task is not None
        assert isinstance(ws_client._background_task, asyncio.Task)
        
        # Cleanup
        await ws_client.stop_background()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_background_cancels_task(ws_client):
    """Test that stop_background cancels the background task."""
    ws_client._running = True
    
    # Create a mock task that raises CancelledError when awaited
    async def mock_cancel():
        raise asyncio.CancelledError()
    
    ws_client._background_task = asyncio.create_task(mock_cancel())
    
    # Should not raise
    await ws_client.stop_background()
    
    assert ws_client._running is False
