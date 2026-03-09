"""
WebSocket client module for failure notifications.

This module provides WebSocket client functionality for real-time
failure notification streaming as specified in Story 5-1.

Story 5-1: WebSocket Connection for Failure Notifications
- AC1: WebSocket Connection Establishment
- AC2: Failure Notification Sending
- AC3: Real-Time Streaming
- AC4: Automatic Reconnection
- AC5: No Duplicate Notifications

Story 5-2: Confidence Score Updates via WebSocket
- AC1: Confidence Score Change Notification
- AC2: Periodic Score Refresh Broadcast
- AC3: Threshold Alert Notifications
- AC4: Real-Time Score Tracking
"""

from src.selectors.websocket.client import WebSocketClient
from src.selectors.websocket.config import WebSocketConfig
from src.selectors.websocket.models import (
    FailureNotification,
    ConfidenceScoreUpdate,
    AlertNotification,
    ConfidenceScoreRefresh,
    NotificationType,
    HealthStatus,
    HealthStatusUpdate,
    SelectorHealthStatus,
    HealthSnapshot,
    SelectorSubscription,
)
from src.selectors.websocket.integration import (
    ConfidenceScoreNotificationService,
    get_confidence_score_service,
    notify_score_change,
    HealthStatusNotificationService,
    get_health_status_service,
    notify_health_status_change,
)

__all__ = [
    "WebSocketClient",
    "WebSocketConfig",
    "FailureNotification",
    "ConfidenceScoreUpdate",
    "AlertNotification",
    "ConfidenceScoreRefresh",
    "NotificationType",
    "HealthStatus",
    "HealthStatusUpdate",
    "SelectorHealthStatus",
    "HealthSnapshot",
    "SelectorSubscription",
    "ConfidenceScoreNotificationService",
    "get_confidence_score_service",
    "notify_score_change",
    "HealthStatusNotificationService",
    "get_health_status_service",
    "notify_health_status_change",
]
