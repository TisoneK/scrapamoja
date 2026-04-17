"""
WebSocket notification integration with failure event capture.

This module provides integration between the WebSocket client and
the existing failure event capture system from Epic 3.

Story 5-1: WebSocket Connection for Failure Notifications
- Task 2.2: Integrate with existing failure event capture (from Epic 3)

Story 5-2: Confidence Score Updates via WebSocket
- Task 2: Integrate with adaptive module for score updates
- Task 3: Implement threshold alerting
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type

from src.selectors.fallback.models import FailureEvent
from src.selectors.websocket.client import WebSocketClient
from src.selectors.websocket.config import WebSocketConfig, load_websocket_config
from src.selectors.websocket.models import SelectorSubscription


class FailureNotificationService:
    """
    Service for sending failure notifications via WebSocket.
    
    This service integrates with the existing failure event capture
    from Epic 3 to send real-time notifications when selector
    failures occur.
    
    Usage:
        # Initialize the service
        notification_service = FailureNotificationService()
        
        # Send notification when failure is captured
        await notification_service.notify_failure(failure_event)
    """
    
    _instance: Optional["FailureNotificationService"] = None
    _client: Optional[WebSocketClient] = None
    _config: Optional[WebSocketConfig] = None
    
    def __new__(cls) -> "FailureNotificationService":
        """Singleton pattern to ensure single WebSocket connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the notification service."""
        if self._initialized:
            return
        
        self._logger = logging.getLogger(__name__)
        self._initialized = True
    
    def initialize(
        self,
        config: Optional[WebSocketConfig] = None,
        client: Optional[WebSocketClient] = None,
    ) -> None:
        """
        Initialize the notification service with config and client.
        
        Args:
            config: WebSocket configuration (loads from env if not provided)
            client: Pre-configured WebSocket client (created if not provided)
        """
        self._config = config or load_websocket_config()
        
        if not self._config.enabled:
            self._logger.info("WebSocket notifications are disabled")
            return
        
        self._client = client or WebSocketClient(
            config=self._config,
            logger=self._logger,
        )
        
        self._logger.info(
            f"FailureNotificationService initialized with "
            f"endpoint: {self._config.url}"
        )
    
    @property
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self._config is not None and self._config.enabled
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        if self._client is None:
            return False
        return self._client.connected
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connected or already connected
        """
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        return await self._client.connect()
    
    async def disconnect(self) -> None:
        """Disconnect WebSocket."""
        if self._client:
            await self._client.disconnect()
    
    async def notify_failure(
        self,
        failure_event: FailureEvent,
    ) -> bool:
        """
        Send failure notification via WebSocket (Task 2.2).
        
        This method integrates with existing failure event capture from Epic 3.
        
        Args:
            failure_event: The failure event to notify about
            
        Returns:
            True if notification sent or buffered successfully
        """
        # Check if notifications are enabled
        if not self.is_enabled:
            return False
        
        # Initialize client if needed
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        # Try to connect if not connected
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                self._logger.warning(
                    "Could not connect to WebSocket, buffering notification"
                )
        
        # Convert failure event to notification
        failure_type = failure_event.failure_type.value
        extractor_id = failure_event.context.get("extractor_id", "unknown")
        
        return await self._client.send_failure(
            selector_id=failure_event.selector_id,
            page_url=failure_event.url,
            failure_type=failure_type,
            extractor_id=extractor_id,
            error_message=failure_event.error_message,
            confidence_score=failure_event.confidence_score,
        )
    
    async def notify_failure_simple(
        self,
        selector_id: str,
        page_url: str,
        failure_type: str,
        extractor_id: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Send simple failure notification without full FailureEvent.
        
        Args:
            selector_id: ID/name of the failed selector
            page_url: URL of the page being extracted
            failure_type: Type of failure
            extractor_id: ID of the extractor
            error_message: Optional error message
            
        Returns:
            True if notification sent or buffered successfully
        """
        if not self.is_enabled:
            return False
        
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        if not self._client.connected:
            await self._client.connect()
        
        return await self._client.send_failure(
            selector_id=selector_id,
            page_url=page_url,
            failure_type=failure_type,
            extractor_id=extractor_id,
            error_message=error_message,
        )
    
    async def __aenter__(self) -> "FailureNotificationService":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


# Global instance for easy access
_notification_service: Optional[FailureNotificationService] = None


def get_notification_service() -> FailureNotificationService:
    """
    Get the global notification service instance.
    
    Returns:
        The global FailureNotificationService instance
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = FailureNotificationService()
    return _notification_service


async def notify_failure_event(failure_event: FailureEvent) -> bool:
    """
    Convenience function to notify a failure event.
    
    Args:
        failure_event: The failure event to notify
        
    Returns:
        True if notification sent or buffered successfully
    """
    service = get_notification_service()
    return await service.notify_failure(failure_event)


# Score callback type for adaptive module integration
ScoreChangeCallback = Callable[[str, float, float, str], None]


class ConfidenceScoreNotificationService:
    """
    Service for sending confidence score updates and alerts via WebSocket.
    
    This service integrates with the adaptive module to send real-time
    notifications when selector confidence scores change.
    
    Features:
    - AC1: Confidence Score Change Notification
    - AC2: Periodic Score Refresh Broadcast
    - AC3: Threshold Alert Notifications
    - AC4: Real-Time Score Tracking (<100ms latency target)
    
    Usage:
        # Initialize the service
        score_service = ConfidenceScoreNotificationService()
        
        # Register score change callback
        score_service.register_score_callback(my_callback)
        
        # Notify score change
        await score_service.notify_score_change(
            selector_id="selector_1",
            old_score=0.8,
            new_score=0.6,
            reason="failure_detected"
        )
    """
    
    _instance: Optional["ConfidenceScoreNotificationService"] = None
    _client: Optional[WebSocketClient] = None
    _config: Optional[WebSocketConfig] = None
    
    def __new__(cls) -> "ConfidenceScoreNotificationService":
        """Singleton pattern to ensure single WebSocket connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the confidence score notification service."""
        if self._initialized:
            return
        
        self._logger = logging.getLogger(__name__)
        self._score_callbacks: List[ScoreChangeCallback] = []
        self._refresh_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_scores: Dict[str, float] = {}  # Track last known scores
        self._initialized = True
    
    def initialize(
        self,
        config: Optional[WebSocketConfig] = None,
        client: Optional[WebSocketClient] = None,
    ) -> None:
        """
        Initialize the confidence score notification service.
        
        Args:
            config: WebSocket configuration (loads from env if not provided)
            client: Pre-configured WebSocket client (created if not provided)
        """
        self._config = config or load_websocket_config()
        
        if not self._config.enabled:
            self._logger.info("Confidence score notifications are disabled")
            return
        
        self._client = client or WebSocketClient(
            config=self._config,
            logger=self._logger,
        )
        
        self._logger.info(
            f"ConfidenceScoreNotificationService initialized with "
            f"endpoint: {self._config.url}"
        )
    
    @property
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self._config is not None and self._config.enabled
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        if self._client is None:
            return False
        return self._client.connected
    
    def register_score_callback(self, callback: ScoreChangeCallback) -> None:
        """
        Register a callback for score changes from the adaptive module.
        
        Args:
            callback: Function to call when scores change
        """
        if callback not in self._score_callbacks:
            self._score_callbacks.append(callback)
    
    def unregister_score_callback(self, callback: ScoreChangeCallback) -> None:
        """
        Unregister a score change callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._score_callbacks:
            self._score_callbacks.remove(callback)
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connected or already connected
        """
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        return await self._client.connect()
    
    async def disconnect(self) -> None:
        """Disconnect WebSocket and stop periodic refresh."""
        await self.stop_periodic_refresh()
        if self._client:
            await self._client.disconnect()
    
    async def notify_score_change(
        self,
        selector_id: str,
        old_score: float,
        new_score: float,
        reason: str,
    ) -> bool:
        """
        Send confidence score change notification (AC1).
        
        Args:
            selector_id: ID of the selector
            old_score: Previous confidence score
            new_score: New confidence score
            reason: Reason for score change
            
        Returns:
            True if notification sent successfully
        """
        if not self.is_enabled:
            return False
        
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        # Check if connected, try to connect if not
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                self._logger.warning(
                    "Could not connect to WebSocket for score update"
                )
        
        # Check for threshold breach (AC3)
        is_threshold_breach = False
        if self._config.enable_threshold_alerts:
            is_threshold_breach = self._check_threshold_breach(selector_id, new_score)
            
            # Send alert if threshold breached
            if is_threshold_breach:
                await self._send_threshold_alert(selector_id, new_score, reason)
        
        # Update last known score
        self._last_scores[selector_id] = new_score
        
        # Send score update notification
        return await self._client.send_confidence_score_update(
            selector_id=selector_id,
            old_score=old_score,
            new_score=new_score,
            reason=reason,
            is_threshold_breach=is_threshold_breach,
        )
    
    def _check_threshold_breach(self, selector_id: str, score: float) -> bool:
        """
        Check if score breaches configured thresholds.
        
        Args:
            selector_id: ID of the selector
            score: Current confidence score
            
        Returns:
            True if threshold breached
        """
        if self._config is None:
            return False
        
        # Check against both warning and critical thresholds
        return score <= self._config.score_threshold_warning
    
    async def _send_threshold_alert(
        self,
        selector_id: str,
        score: float,
        reason: str,
    ) -> bool:
        """
        Send threshold alert notification (AC3).
        
        Args:
            selector_id: ID of the selector
            score: Current confidence score
            reason: Reason for score change
            
        Returns:
            True if alert sent successfully
        """
        if self._client is None:
            return False
        
        # Determine alert level based on threshold
        alert_level = "warning"
        threshold = self._config.score_threshold_warning
        
        if score <= self._config.score_threshold_critical:
            alert_level = "critical"
            threshold = self._config.score_threshold_critical
        
        # Generate alert message
        message = (
            f"Selector '{selector_id}' confidence score dropped to {score:.2f} "
            f"({alert_level} level, threshold: {threshold:.2f}). "
            f"Reason: {reason}"
        )
        
        self._logger.warning(f"Threshold alert: {message}")
        
        return await self._client.send_alert(
            selector_id=selector_id,
            alert_level=alert_level,
            message=message,
            current_score=score,
            threshold=threshold,
        )
    
    async def broadcast_scores(
        self,
        scores: List[Dict[str, float]],
        is_delta: bool = False,
    ) -> bool:
        """
        Send periodic confidence score refresh broadcast (AC2).
        
        Args:
            scores: List of {selector_id, score} dictionaries
            is_delta: Whether this is a delta update
            
        Returns:
            True if broadcast sent successfully
        """
        if not self.is_enabled:
            return False
        
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                self._logger.warning(
                    "Could not connect to WebSocket for score refresh"
                )
        
        # Update last known scores
        for score_info in scores:
            if isinstance(score_info, dict):
                selector_id = score_info.get("selector_id")
                score = score_info.get("score")
                if selector_id and score is not None:
                    self._last_scores[selector_id] = score
        
        return await self._client.send_confidence_refresh(
            scores=scores,
            is_delta=is_delta,
        )
    
    async def start_periodic_refresh(
        self,
        get_scores_func: Optional[Callable[[], List[Dict[str, float]]]] = None,
    ) -> None:
        """
        Start periodic confidence score refresh broadcast (AC2).
        
        Args:
            get_scores_func: Optional function to get current scores.
                           If not provided, will use last known scores.
        """
        if self._running:
            return
        
        self._running = True
        self._get_scores_func = get_scores_func
        
        async def _periodic_refresh():
            while self._running:
                try:
                    await asyncio.sleep(self._config.confidence_refresh_interval)
                    
                    # Get scores to broadcast
                    if self._get_scores_func:
                        scores = self._get_scores_func()
                        # Handle both sync and async functions
                        if asyncio.iscoroutine(scores):
                            scores = await scores
                    else:
                        # Use last known scores
                        scores = [
                            {"selector_id": sid, "score": score}
                            for sid, score in self._last_scores.items()
                        ]
                    
                    if scores:
                        await self.broadcast_scores(scores, is_delta=False)
                        self._logger.debug(
                            f"Periodic score refresh: {len(scores)} scores"
                        )
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._logger.error(f"Periodic refresh error: {e}")
        
        self._refresh_task = asyncio.create_task(_periodic_refresh())
        self._logger.info(
            f"Started periodic refresh with interval: "
            f"{self._config.confidence_refresh_interval}s"
        )
    
    async def stop_periodic_refresh(self) -> None:
        """Stop periodic confidence score refresh."""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
        self._logger.info("Stopped periodic refresh")
    
    async def __aenter__(self) -> "ConfidenceScoreNotificationService":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


# Global instance for confidence score notifications
_confidence_score_service: Optional[ConfidenceScoreNotificationService] = None


def get_confidence_score_service() -> ConfidenceScoreNotificationService:
    """
    Get the global confidence score notification service instance.
    
    Returns:
        The global ConfidenceScoreNotificationService instance
    """
    global _confidence_score_service
    if _confidence_score_service is None:
        _confidence_score_service = ConfidenceScoreNotificationService()
    return _confidence_score_service


async def notify_score_change(
    selector_id: str,
    old_score: float,
    new_score: float,
    reason: str,
) -> bool:
    """
    Convenience function to notify a confidence score change.
    
    Args:
        selector_id: ID of the selector
        old_score: Previous confidence score
        new_score: New confidence score
        reason: Reason for score change
        
    Returns:
        True if notification sent successfully
    """
    service = get_confidence_score_service()
    return await service.notify_score_change(
        selector_id=selector_id,
        old_score=old_score,
        new_score=new_score,
        reason=reason,
    )


# === Health Status Notification Service (Story 5.3) ===

# Callback type for health status changes from adaptive module
HealthStatusChangeCallback = Callable[[str, str, str, Optional[float]], None]


class HealthStatusNotificationService:
    """
    Service for sending health status updates and snapshots via WebSocket.
    
    This service integrates with the adaptive module to send real-time
    notifications when selector health status changes.
    
    Features:
    - AC1: Health Status Change Notification
    - AC2: Periodic Health Snapshot Broadcast  
    - AC3: Individual Selector Subscription
    
    Usage:
        # Initialize the service
        health_service = HealthStatusNotificationService()
        
        # Register health status change callback
        health_service.register_health_callback(my_callback)
        
        # Notify health status change
        await health_service.notify_health_status_change(
            selector_id="selector_1",
            old_status="healthy",
            new_status="degraded",
            confidence_score=0.5
        )
    """
    
    _instance: Optional["HealthStatusNotificationService"] = None
    _client: Optional["WebSocketClient"] = None
    _config: Optional[WebSocketConfig] = None
    
    def __new__(cls) -> "HealthStatusNotificationService":
        """Singleton pattern to ensure single WebSocket connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the health status notification service."""
        if self._initialized:
            return
        
        self._logger = logging.getLogger(__name__)
        self._health_callbacks: List[HealthStatusChangeCallback] = []
        self._health_snapshot_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_health_status: Dict[str, str] = {}  # Track last known health status
        self._subscriptions: Dict[str, "SelectorSubscription"] = {}  # Client subscriptions
        self._initialized = True
    
    def initialize(
        self,
        config: Optional[WebSocketConfig] = None,
        client: Optional["WebSocketClient"] = None,
    ) -> None:
        """
        Initialize the health status notification service.
        
        Args:
            config: WebSocket configuration (loads from env if not provided)
            client: Pre-configured WebSocket client (created if not provided)
        """
        self._config = config or load_websocket_config()
        
        if not self._config.enabled:
            self._logger.info("Health status notifications are disabled")
            return
        
        self._client = client or WebSocketClient(
            config=self._config,
            logger=self._logger,
        )
        
        self._logger.info(
            f"HealthStatusNotificationService initialized with "
            f"endpoint: {self._config.url}"
        )
    
    @property
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self._config is not None and self._config.enabled
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        if self._client is None:
            return False
        return self._client.connected
    
    def get_last_health_status(self, selector_id: str) -> Optional[str]:
        """
        Get the last known health status for a selector.
        
        Args:
            selector_id: The selector ID to look up
            
        Returns:
            Last known health status string or None if not known
        """
        return self._last_health_status.get(selector_id)
    
    def get_all_health_statuses(self) -> Dict[str, str]:
        """
        Get all known health statuses.
        
        Returns:
            Dictionary mapping selector_id to health status
        """
        return self._last_health_status.copy()
    
    def register_health_callback(self, callback: HealthStatusChangeCallback) -> None:
        """
        Register a callback for health status changes from the adaptive module.
        
        Args:
            callback: Function to call when health status changes
        """
        if callback not in self._health_callbacks:
            self._health_callbacks.append(callback)
    
    def unregister_health_callback(self, callback: HealthStatusChangeCallback) -> None:
        """
        Unregister a health status change callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._health_callbacks:
            self._health_callbacks.remove(callback)
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connected or already connected
        """
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        return await self._client.connect()
    
    async def disconnect(self) -> None:
        """Disconnect WebSocket and stop periodic snapshot."""
        await self.stop_periodic_snapshot()
        if self._client:
            await self._client.disconnect()
    
    async def notify_health_status_change(
        self,
        selector_id: str,
        old_status: str,
        new_status: str,
        confidence_score: Optional[float] = None,
    ) -> bool:
        """
        Send health status change notification (AC1).
        
        Args:
            selector_id: ID of the selector
            old_status: Previous health status
            new_status: New health status
            confidence_score: Optional current confidence score
            
        Returns:
            True if notification sent successfully
        """
        if not self.is_enabled:
            return False
        
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        # Check if connected, try to connect if not
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                self._logger.warning(
                    "Could not connect to WebSocket for health status update"
                )
        
        # Update last known status
        self._last_health_status[selector_id] = new_status
        
        # Send notification
        result = await self._client.send_health_status_update(
            selector_id=selector_id,
            old_status=old_status,
            new_status=new_status,
            confidence_score=confidence_score,
        )
        
        # Notify registered callbacks
        for callback in self._health_callbacks:
            try:
                callback(selector_id, old_status, new_status, confidence_score)
            except Exception as e:
                self._logger.warning(f"Health callback error: {e}")
        
        return result
    
    async def broadcast_health_snapshot(
        self,
        health_statuses: List[Dict[str, Any]],
    ) -> bool:
        """
        Send periodic health snapshot broadcast (AC2).
        
        Args:
            health_statuses: List of selector health statuses
            
        Returns:
            True if broadcast sent successfully
        """
        if not self.is_enabled:
            return False
        
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            return False
        
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                self._logger.warning(
                    "Could not connect to WebSocket for health snapshot"
                )
        
        # Update last known statuses
        for status in health_statuses:
            selector_id = status.get("selector_id")
            if selector_id:
                self._last_health_status[selector_id] = status.get("status", "unknown")
        
        return await self._client.send_health_snapshot(
            health_statuses=health_statuses,
        )
    
    async def start_periodic_snapshot(
        self,
        get_health_func: Optional[Callable[[], List[Dict[str, Any]]]] = None,
    ) -> None:
        """
        Start periodic health snapshot broadcast (AC2).
        
        Args:
            get_health_func: Optional function to get current health statuses.
                           If not provided, will use last known statuses.
        """
        if self._running:
            return
        
        self._running = True
        self._get_health_func = get_health_func
        
        async def _periodic_snapshot():
            while self._running:
                try:
                    await asyncio.sleep(self._config.health_check_interval)
                    
                    # Get health statuses to broadcast
                    if self._get_health_func:
                        health_statuses = self._get_health_func()
                        # Handle both sync and async functions
                        if asyncio.iscoroutine(health_statuses):
                            health_statuses = await health_statuses
                    else:
                        # Use last known statuses
                        health_statuses = [
                            {"selector_id": sid, "status": status}
                            for sid, status in self._last_health_status.items()
                        ]
                    
                    if health_statuses:
                        await self.broadcast_health_snapshot(health_statuses)
                        self._logger.debug(
                            f"Periodic health snapshot: {len(health_statuses)} statuses"
                        )
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._logger.error(f"Periodic snapshot error: {e}")
        
        self._health_snapshot_task = asyncio.create_task(_periodic_snapshot())
        self._logger.info(
            f"Started periodic health snapshot with interval: "
            f"{self._config.health_check_interval}s"
        )
    
    async def stop_periodic_snapshot(self) -> None:
        """Stop periodic health snapshot broadcast."""
        self._running = False
        if self._health_snapshot_task:
            self._health_snapshot_task.cancel()
            try:
                await self._health_snapshot_task
            except asyncio.CancelledError:
                pass
            self._health_snapshot_task = None
        self._logger.info("Stopped periodic health snapshot")
    
    # === Subscription Management (AC3) ===
    
    def subscribe_client(
        self,
        client_id: str,
        subscription: "SelectorSubscription",
    ) -> None:
        """
        Register a client's subscription for filtered notifications.
        
        Args:
            client_id: Unique identifier for the client
            subscription: The client's subscription preferences
        """
        self._subscriptions[client_id] = subscription
        self._logger.info(f"Client {client_id} subscribed: {subscription}")
    
    def unsubscribe_client(self, client_id: str) -> None:
        """
        Remove a client's subscription.
        
        Args:
            client_id: Unique identifier for the client
        """
        if client_id in self._subscriptions:
            del self._subscriptions[client_id]
            self._logger.info(f"Client {client_id} unsubscribed")
    
    def get_client_subscription(self, client_id: str) -> Optional["SelectorSubscription"]:
        """
        Get a client's subscription.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            The client's subscription or None if not found
        """
        return self._subscriptions.get(client_id)
    
    def should_notify_client(
        self,
        client_id: str,
        selector_id: str,
    ) -> bool:
        """
        Check if a client should be notified about a selector's status.
        
        Args:
            client_id: Unique identifier for the client
            selector_id: The selector ID to check
            
        Returns:
            True if client should be notified
        """
        subscription = self._subscriptions.get(client_id)
        if subscription is None:
            # No subscription = subscribe to all
            return True
        return subscription.matches(selector_id)
    
    async def __aenter__(self) -> "HealthStatusNotificationService":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


# Global instance for health status notifications
_health_status_service: Optional[HealthStatusNotificationService] = None


def get_health_status_service() -> HealthStatusNotificationService:
    """
    Get the global health status notification service instance.
    
    Returns:
        The global HealthStatusNotificationService instance
    """
    global _health_status_service
    if _health_status_service is None:
        _health_status_service = HealthStatusNotificationService()
    return _health_status_service


async def notify_health_status_change(
    selector_id: str,
    old_status: str,
    new_status: str,
    confidence_score: Optional[float] = None,
) -> bool:
    """
    Convenience function to notify a health status change.
    
    Args:
        selector_id: ID of the selector
        old_status: Previous health status
        new_status: New health status
        confidence_score: Optional current confidence score
        
    Returns:
        True if notification sent successfully
    """
    service = get_health_status_service()
    return await service.notify_health_status_change(
        selector_id=selector_id,
        old_status=old_status,
        new_status=new_status,
        confidence_score=confidence_score,
    )
