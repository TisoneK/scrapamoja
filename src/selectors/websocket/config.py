"""
WebSocket configuration for failure notifications.

This module defines the configuration model for WebSocket client
connections as specified in Story 5-1.

Story 5-1: WebSocket Connection for Failure Notifications
- AC4: Automatic Reconnection with exponential backoff
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class WebSocketConfig(BaseModel):
    """
    Configuration for WebSocket client connection.
    
    Attributes:
        url: WebSocket endpoint URL (e.g., ws://localhost:8080/notifications)
        max_retries: Maximum number of reconnection attempts (default: 5)
        base_delay: Initial delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay in seconds for exponential backoff (default: 60.0)
        buffer_size: Maximum number of messages to buffer during disconnection (default: 100)
        message_timeout: Timeout in seconds for sending messages (default: 10.0)
        ping_interval: Interval in seconds for ping/pong keep-alive (default: 30.0)
        protocols: Optional list of WebSocket sub-protocols
        headers: Optional dict of custom headers for the connection
        enabled: Whether WebSocket notifications are enabled (default: True)
    """
    
    url: str = Field(
        description="WebSocket endpoint URL for failure notifications"
    )
    max_retries: int = Field(
        default=5,
        ge=0,
        description="Maximum number of reconnection attempts"
    )
    base_delay: float = Field(
        default=1.0,
        gt=0,
        description="Initial delay in seconds for exponential backoff"
    )
    max_delay: float = Field(
        default=60.0,
        gt=0,
        description="Maximum delay in seconds for exponential backoff"
    )
    buffer_size: int = Field(
        default=100,
        ge=1,
        description="Maximum number of messages to buffer during disconnection"
    )
    message_timeout: float = Field(
        default=10.0,
        gt=0,
        description="Timeout in seconds for sending messages"
    )
    ping_interval: float = Field(
        default=30.0,
        gt=0,
        description="Interval in seconds for ping/pong keep-alive"
    )
    protocols: Optional[list[str]] = Field(
        default=None,
        description="Optional list of WebSocket sub-protocols"
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional dict of custom headers for the connection"
    )
    enabled: bool = Field(
        default=True,
        description="Whether WebSocket notifications are enabled"
    )
    confidence_refresh_interval: int = Field(
        default=60,
        ge=10,
        description="Interval in seconds for confidence score refresh broadcast"
    )
    score_threshold_warning: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Warning threshold for confidence scores"
    )
    score_threshold_critical: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Critical threshold for confidence scores"
    )
    enable_threshold_alerts: bool = Field(
        default=True,
        description="Whether to send threshold breach alerts"
    )
    health_check_interval: int = Field(
        default=30,
        ge=10,
        description="Interval in seconds for health status snapshot broadcast"
    )
    health_status_healthy_min: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for healthy status"
    )
    health_status_degraded_min: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for degraded status"
    )
    health_status_failed_max: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Maximum confidence score for failed status"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
        extra = "forbid"

    def calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff.
        
        Args:
            attempt: The current reconnection attempt number (0-indexed)
            
        Returns:
            Delay in seconds for this attempt
        """
        import math
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)

    def get_health_status_from_confidence(self, confidence_score: Optional[float]) -> str:
        """
        Determine health status from confidence score.
        
        Args:
            confidence_score: Confidence score (0.0-1.0)
            
        Returns:
            Health status string: "healthy", "degraded", "failed", or "unknown"
        """
        if confidence_score is None:
            return "unknown"
        if confidence_score < 0:
            # Negative confidence scores should be treated as unknown
            return "unknown"
        if confidence_score >= self.health_status_healthy_min:
            return "healthy"
        elif confidence_score >= self.health_status_degraded_min:
            return "degraded"
        else:
            return "failed"


def load_websocket_config() -> WebSocketConfig:
    """
    Load WebSocket configuration from environment or defaults.
    
    This function attempts to load configuration from environment variables
    with fallback to default values.
    
    Returns:
        WebSocketConfig with loaded configuration
    """
    import os
    
    # Try to load from environment
    url = os.environ.get("WEBSOCKET_NOTIFICATION_URL", "")
    
    if not url:
        # WebSocket disabled by default if no URL configured
        return WebSocketConfig(
            url="ws://localhost:8080/notifications",
            enabled=False
        )
    
    return WebSocketConfig(
        url=url,
        max_retries=int(os.environ.get("WEBSOCKET_MAX_RETRIES", "5")),
        base_delay=float(os.environ.get("WEBSOCKET_BASE_DELAY", "1.0")),
        max_delay=float(os.environ.get("WEBSOCKET_MAX_DELAY", "60.0")),
        buffer_size=int(os.environ.get("WEBSOCKET_BUFFER_SIZE", "100")),
        message_timeout=float(os.environ.get("WEBSOCKET_MESSAGE_TIMEOUT", "10.0")),
        ping_interval=float(os.environ.get("WEBSOCKET_PING_INTERVAL", "30.0")),
        confidence_refresh_interval=int(os.environ.get("WEBSOCKET_CONFIDENCE_REFRESH_INTERVAL", "60")),
        score_threshold_warning=float(os.environ.get("WEBSOCKET_SCORE_THRESHOLD_WARNING", "0.5")),
        score_threshold_critical=float(os.environ.get("WEBSOCKET_SCORE_THRESHOLD_CRITICAL", "0.3")),
        enable_threshold_alerts=os.environ.get("WEBSOCKET_ENABLE_THRESHOLD_ALERTS", "true").lower() == "true",
        health_check_interval=int(os.environ.get("WEBSOCKET_HEALTH_CHECK_INTERVAL", "30")),
        health_status_healthy_min=float(os.environ.get("WEBSOCKET_HEALTH_STATUS_HEALTHY_MIN", "0.7")),
        health_status_degraded_min=float(os.environ.get("WEBSOCKET_HEALTH_STATUS_DEGRADED_MIN", "0.4")),
        health_status_failed_max=float(os.environ.get("WEBSOCKET_HEALTH_STATUS_FAILED_MAX", "0.3")),
        enabled=True,
    )
