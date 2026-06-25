"""
Health Status WebSocket notification integration.

This module provides integration between the WebSocket client and
the health status service for real-time health status updates.

Story 6-2: Selector Health Status Display
- Task 4: Integrate with WebSocket for real-time updates
"""

import logging
from typing import Optional

from src.selectors.websocket.client import WebSocketClient
from src.selectors.websocket.config import WebSocketConfig, load_websocket_config

logger = logging.getLogger(__name__)


class HealthStatusNotificationService:
    """
    Service for sending health status updates via WebSocket.
    
    This service integrates with the existing WebSocket infrastructure
    to push real-time health status changes.
    
    Usage:
        # Initialize the service
        health_service = HealthStatusNotificationService()
        
        # Notify health status change
        await health_service.notify_health_status_change(
            selector_id="selector_1",
            old_status="healthy",
            new_status="degraded",
            confidence_score=0.6
        )
    """
    
    _instance: Optional["HealthStatusNotificationService"] = None
    _client: Optional[WebSocketClient] = None
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
        self._initialized = True
    
    def initialize(
        self,
        config: Optional[WebSocketConfig] = None,
        client: Optional[WebSocketClient] = None,
    ) -> None:
        """
        Initialize the health status notification service.
        
        Args:
            config: WebSocket configuration (loads from env if not provided)
            client: Pre-configured WebSocket client (created if not provided)
        """
        self._config = config or load_websocket_config()
        
        if not self._config.enabled:
            self._logger.info("WebSocket health notifications are disabled")
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
    
    async def notify_health_status_change(
        self,
        selector_id: str,
        old_status: Optional[str],
        new_status: str,
        confidence_score: float,
    ) -> bool:
        """
        Send health status change notification via WebSocket.
        
        Args:
            selector_id: ID of the selector
            old_status: Previous health status (string: healthy, degraded, failed)
            new_status: New health status (string: healthy, degraded, failed)
            confidence_score: Current confidence score
            
        Returns:
            True if notification sent successfully
        """
        if not self.is_enabled:
            self._logger.debug("Health notifications are disabled")
            return False
        
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            self._logger.warning("WebSocket client not available")
            return False
        
        # Check if connected, try to connect if not
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                self._logger.warning(
                    "Could not connect to WebSocket for health status update"
                )
                return False
        
        # Use the existing WebSocket client method
        try:
            return await self._client.send_health_status_update(
                selector_id=selector_id,
                old_status=old_status or "unknown",
                new_status=new_status,
                confidence_score=confidence_score,
            )
        except Exception as e:
            self._logger.error(
                "Failed to send health status notification",
                selector_id=selector_id,
                error=str(e)
            )
            return False
    
    async def notify_health_snapshot(self, health_statuses: list) -> bool:
        """
        Send full health snapshot notification.
        
        This notifies subscribers with the current health status of all selectors.
        
        Args:
            health_statuses: List of dicts with selector_id, status, confidence_score
            
        Returns:
            True if notification sent successfully
        """
        if not self.is_enabled:
            self._logger.debug("Health notifications are disabled")
            return False
        
        if self._client is None:
            self.initialize()
        
        if self._client is None:
            self._logger.warning("WebSocket client not available")
            return False
        
        # Check if connected
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                self._logger.warning(
                    "Could not connect to WebSocket for health snapshot"
                )
                return False
        
        try:
            return await self._client.send_health_snapshot(
                health_statuses=health_statuses,
            )
        except Exception as e:
            self._logger.error(
                "Failed to send health snapshot notification",
                error=str(e)
            )
            return False


# Global instance for easy access
_health_notification_service: Optional[HealthStatusNotificationService] = None


def get_health_notification_service() -> HealthStatusNotificationService:
    """
    Get the global health notification service instance.
    
    Returns:
        The global HealthStatusNotificationService instance
    """
    global _health_notification_service
    if _health_notification_service is None:
        _health_notification_service = HealthStatusNotificationService()
    return _health_notification_service


async def notify_health_status_change(
    selector_id: str,
    old_status: Optional[str],
    new_status: str,
    confidence_score: float,
) -> bool:
    """
    Convenience function to notify a health status change.
    
    Args:
        selector_id: The selector ID
        old_status: Previous health status (string)
        new_status: New health status (string)
        confidence_score: Current confidence score
        
    Returns:
        True if notification sent successfully
    """
    service = get_health_notification_service()
    return await service.notify_health_status_change(
        selector_id=selector_id,
        old_status=old_status,
        new_status=new_status,
        confidence_score=confidence_score,
    )
