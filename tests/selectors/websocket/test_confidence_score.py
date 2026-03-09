"""
Unit tests for confidence score WebSocket notifications.

Story 5-2: Confidence Score Updates via WebSocket
- AC1: Confidence Score Change Notification
- AC2: Periodic Score Refresh Broadcast
- AC3: Threshold Alert Notifications
- AC4: Real-Time Score Tracking
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.selectors.websocket.client import WebSocketClient
from src.selectors.websocket.config import WebSocketConfig
from src.selectors.websocket.models import (
    ConfidenceScoreUpdate,
    AlertNotification,
    ConfidenceScoreRefresh,
    NotificationType,
)
from src.selectors.websocket.integration import ConfidenceScoreNotificationService


# === Test Fixtures ===

@pytest.fixture
def ws_config():
    """Create test WebSocket configuration with threshold settings."""
    return WebSocketConfig(
        url="ws://localhost:8080/notifications",
        max_retries=3,
        base_delay=0.1,
        max_delay=1.0,
        buffer_size=10,
        message_timeout=1.0,
        ping_interval=5.0,
        confidence_refresh_interval=60,
        score_threshold_warning=0.5,
        score_threshold_critical=0.3,
        enable_threshold_alerts=True,
    )


@pytest.fixture
def ws_client(ws_config):
    """Create WebSocket client instance."""
    return WebSocketClient(config=ws_config)


@pytest.fixture
def score_service():
    """Create confidence score notification service instance."""
    service = ConfidenceScoreNotificationService()
    service._instance = None  # Reset singleton
    return service


# === AC1: Confidence Score Update Tests ===

@pytest.mark.unit
def test_confidence_score_update_model():
    """Test AC1: ConfidenceScoreUpdate model creation and serialization."""
    notification = ConfidenceScoreUpdate(
        selector_id="team_name",
        old_score=0.8,
        new_score=0.6,
        reason="failure_detected",
    )
    
    assert notification.selector_id == "team_name"
    assert notification.old_score == 0.8
    assert notification.new_score == 0.6
    assert notification.reason == "failure_detected"
    assert notification.notification_type == "confidence_score_update"
    assert notification.is_threshold_breach is False
    assert notification.message_id is not None
    
    # Test JSON serialization
    json_str = notification.to_json()
    assert json_str is not None
    data = json.loads(json_str)
    assert data["selector_id"] == "team_name"
    assert data["old_score"] == 0.8
    assert data["new_score"] == 0.6


@pytest.mark.unit
def test_confidence_score_update_with_threshold_breach():
    """Test AC1: ConfidenceScoreUpdate with threshold breach flag."""
    notification = ConfidenceScoreUpdate(
        selector_id="team_name",
        old_score=0.6,
        new_score=0.4,
        reason="failure_detected",
        is_threshold_breach=True,
    )
    
    assert notification.is_threshold_breach is True


@pytest.mark.unit
def test_confidence_score_update_json_encoding():
    """Test AC1: ConfidenceScoreUpdate JSON encoding includes timestamp."""
    notification = ConfidenceScoreUpdate(
        selector_id="team_score",
        old_score=0.9,
        new_score=0.7,
        reason="success_accumulated",
    )
    
    json_str = notification.to_json()
    data = json.loads(json_str)
    
    assert "message_id" in data
    assert "timestamp" in data
    assert "notification_type" in data
    assert data["notification_type"] == "confidence_score_update"


# === AC3: Threshold Alert Notification Tests ===

@pytest.mark.unit
def test_alert_notification_model_warning():
    """Test AC3: AlertNotification model for warning level."""
    notification = AlertNotification(
        alert_level="warning",
        selector_id="team_name",
        message="Score dropped below warning threshold",
        current_score=0.45,
        threshold=0.5,
    )
    
    assert notification.alert_level == "warning"
    assert notification.selector_id == "team_name"
    assert notification.current_score == 0.45
    assert notification.threshold == 0.5
    assert notification.notification_type == "alert"
    assert notification.message_id is not None
    
    # Test JSON serialization
    json_str = notification.to_json()
    data = json.loads(json_str)
    assert data["alert_level"] == "warning"


@pytest.mark.unit
def test_alert_notification_model_critical():
    """Test AC3: AlertNotification model for critical level."""
    notification = AlertNotification(
        alert_level="critical",
        selector_id="team_name",
        message="Score dropped below critical threshold",
        current_score=0.25,
        threshold=0.3,
    )
    
    assert notification.alert_level == "critical"
    assert notification.current_score == 0.25


@pytest.mark.unit
def test_alert_notification_json_encoding():
    """Test AC3: AlertNotification JSON encoding."""
    notification = AlertNotification(
        alert_level="warning",
        selector_id="player_name",
        message="Test alert",
        current_score=0.4,
        threshold=0.5,
    )
    
    json_str = notification.to_json()
    data = json.loads(json_str)
    
    assert "message_id" in data
    assert "timestamp" in data
    assert data["selector_id"] == "player_name"
    assert data["alert_level"] == "warning"


# === AC2: Periodic Score Refresh Tests ===

@pytest.mark.unit
def test_confidence_score_refresh_model():
    """Test AC2: ConfidenceScoreRefresh model."""
    scores = [
        {"selector_id": "team_name", "score": 0.8},
        {"selector_id": "player_name", "score": 0.6},
    ]
    
    notification = ConfidenceScoreRefresh(
        scores=scores,
        is_delta=False,
    )
    
    assert len(notification.scores) == 2
    assert notification.is_delta is False
    assert notification.notification_type == "confidence_score_refresh"
    
    # Test JSON serialization
    json_str = notification.to_json()
    data = json.loads(json_str)
    assert len(data["scores"]) == 2


@pytest.mark.unit
def test_confidence_score_refresh_delta():
    """Test AC2: ConfidenceScoreRefresh with delta update."""
    scores = [
        {"selector_id": "team_name", "score": 0.7},
    ]
    
    notification = ConfidenceScoreRefresh(
        scores=scores,
        is_delta=True,
    )
    
    assert notification.is_delta is True


# === WebSocket Client Score Notification Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_confidence_score_update(ws_client):
    """Test sending confidence score update via WebSocket."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.ping = AsyncMock()
    ws_client._websocket = mock_ws
    ws_client._connected = True
    
    result = await ws_client.send_confidence_score_update(
        selector_id="team_name",
        old_score=0.8,
        new_score=0.6,
        reason="failure_detected",
    )
    
    assert result is True
    mock_ws.send.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_alert(ws_client):
    """Test sending alert notification via WebSocket."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.ping = AsyncMock()
    ws_client._websocket = mock_ws
    ws_client._connected = True
    
    result = await ws_client.send_alert(
        selector_id="team_name",
        alert_level="warning",
        message="Score below threshold",
        current_score=0.4,
        threshold=0.5,
    )
    
    assert result is True
    mock_ws.send.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_confidence_refresh(ws_client):
    """Test sending periodic confidence refresh via WebSocket."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.ping = AsyncMock()
    ws_client._websocket = mock_ws
    ws_client._connected = True
    
    scores = [
        {"selector_id": "team_name", "score": 0.8},
    ]
    
    result = await ws_client.send_confidence_refresh(
        scores=scores,
        is_delta=False,
    )
    
    assert result is True
    mock_ws.send.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_notification_buffered_when_disconnected(ws_client):
    """Test AC4: Score notifications are buffered when disconnected."""
    ws_client._connected = False
    
    result = await ws_client.send_confidence_score_update(
        selector_id="team_name",
        old_score=0.8,
        new_score=0.6,
        reason="failure_detected",
    )
    
    assert result is True
    assert hasattr(ws_client, '_score_buffer')
    assert len(ws_client._score_buffer) == 1


# === ConfidenceScoreNotificationService Tests ===

@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_service_threshold_check(score_service, ws_config):
    """Test AC3: Threshold checking logic."""
    score_service.initialize(config=ws_config)
    
    # Should breach warning threshold
    assert score_service._check_threshold_breach("team_name", 0.4) is True
    
    # Should breach critical threshold
    assert score_service._check_threshold_breach("team_name", 0.25) is True
    
    # Should not breach
    assert score_service._check_threshold_breach("team_name", 0.6) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_service_notify_score_change(score_service, ws_config):
    """Test AC1: Score change notification."""
    score_service.initialize(config=ws_config)
    
    mock_client = AsyncMock()
    mock_client.send_confidence_score_update = AsyncMock(return_value=True)
    mock_client.send_alert = AsyncMock(return_value=True)
    mock_client.connected = True
    score_service._client = mock_client
    
    result = await score_service.notify_score_change(
        selector_id="team_name",
        old_score=0.8,
        new_score=0.6,
        reason="failure_detected",
    )
    
    assert result is True
    mock_client.send_confidence_score_update.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_service_threshold_alert_triggered(score_service, ws_config):
    """Test AC3: Threshold alert is triggered when score drops below threshold."""
    score_service.initialize(config=ws_config)
    
    mock_client = AsyncMock()
    mock_client.send_confidence_score_update = AsyncMock(return_value=True)
    mock_client.send_alert = AsyncMock(return_value=True)
    mock_client.connected = True
    score_service._client = mock_client
    
    # Score drops below warning threshold (0.5)
    result = await score_service.notify_score_change(
        selector_id="team_name",
        old_score=0.7,
        new_score=0.4,
        reason="failure_detected",
    )
    
    assert result is True
    # Should trigger alert
    mock_client.send_alert.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_service_broadcast_scores(score_service, ws_config):
    """Test AC2: Broadcasting scores."""
    score_service.initialize(config=ws_config)
    
    mock_client = AsyncMock()
    mock_client.send_confidence_refresh = AsyncMock(return_value=True)
    mock_client.connected = True
    score_service._client = mock_client
    
    scores = [
        {"selector_id": "team_name", "score": 0.8},
        {"selector_id": "player_name", "score": 0.6},
    ]
    
    result = await score_service.broadcast_scores(scores)
    
    assert result is True
    mock_client.send_confidence_refresh.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_service_periodic_refresh(score_service, ws_config):
    """Test AC2: Periodic refresh scheduling."""
    score_service.initialize(config=ws_config)
    
    # Set a short refresh interval for testing
    ws_config.confidence_refresh_interval = 1
    
    mock_client = AsyncMock()
    mock_client.send_confidence_refresh = AsyncMock(return_value=True)
    mock_client.connected = True
    score_service._client = mock_client
    
    # Start periodic refresh with a get_scores_func
    scores_data = [{"selector_id": "team_name", "score": 0.8}]
    
    async def get_scores():
        return scores_data
    
    await score_service.start_periodic_refresh(get_scores_func=get_scores)
    
    # Wait for at least one refresh cycle
    await asyncio.sleep(1.5)
    
    # Check that refresh was called
    assert mock_client.send_confidence_refresh.called
    
    await score_service.stop_periodic_refresh()


# === Integration Tests ===

@pytest.mark.integration
@pytest.mark.asyncio
async def test_score_update_model_serialization_roundtrip():
    """Test model serialization roundtrip."""
    notification = ConfidenceScoreUpdate(
        selector_id="team_name",
        old_score=0.8,
        new_score=0.6,
        reason="failure_detected",
    )
    
    # Serialize to JSON
    json_str = notification.to_json()
    
    # Deserialize back
    data = json.loads(json_str)
    
    # Verify data integrity
    assert data["selector_id"] == "team_name"
    assert data["old_score"] == 0.8
    assert data["new_score"] == 0.6
    assert data["reason"] == "failure_detected"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alert_model_serialization_roundtrip():
    """Test alert model serialization roundtrip."""
    notification = AlertNotification(
        alert_level="critical",
        selector_id="team_name",
        message="Score critically low",
        current_score=0.2,
        threshold=0.3,
    )
    
    json_str = notification.to_json()
    data = json.loads(json_str)
    
    assert data["alert_level"] == "critical"
    assert data["selector_id"] == "team_name"
    assert data["current_score"] == 0.2
