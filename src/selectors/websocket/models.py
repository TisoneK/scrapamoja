"""
Notification message models for WebSocket failure notifications.

This module defines the data models for failure notifications
sent via WebSocket as specified in Story 5-1.

Story 5-1: WebSocket Connection for Failure Notifications
- AC2: Failure notification includes selector_id, page_url, timestamp, failure_type
- AC5: Unique message ID for deduplication
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field


class FailureType(str, Enum):
    """
    Types of selector failures that trigger notifications.
    
    Maps to FailureType from fallback/models.py.
    """
    EMPTY_RESULT = "empty_result"
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILED = "validation_failed"


class FailureNotification(BaseModel):
    """
    Model for failure notification messages sent via WebSocket.
    
    Attributes:
        message_id: Unique UUID for deduplication (AC5)
        selector_id: ID/name of the failed selector
        page_url: URL of the page being extracted
        timestamp: ISO8601 timestamp of the failure
        failure_type: Type of failure (empty_result, exception, timeout, etc.)
        extractor_id: ID of the extractor running the selector
        error_message: Optional error message from the failure
        confidence_score: Optional confidence score if available
    """
    
    message_id: str = Field(
        description="Unique UUID for message deduplication",
        default_factory=lambda: str(uuid.uuid4())
    )
    selector_id: str = Field(
        description="ID/name of the failed selector"
    )
    page_url: str = Field(
        description="URL of the page being extracted"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of the failure",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    failure_type: str = Field(
        description="Type of failure (empty_result, exception, timeout)"
    )
    extractor_id: str = Field(
        description="ID of the extractor running the selector"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Optional error message from the failure"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="Optional confidence score if available"
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def from_failure_event(
        cls,
        selector_id: str,
        page_url: str,
        failure_type: str,
        extractor_id: str,
        error_message: Optional[str] = None,
        confidence_score: Optional[float] = None,
    ) -> "FailureNotification":
        """
        Create a FailureNotification from failure event data.
        
        Args:
            selector_id: ID/name of the failed selector
            page_url: URL of the page being extracted
            failure_type: Type of failure
            extractor_id: ID of the extractor running the selector
            error_message: Optional error message
            confidence_score: Optional confidence score
            
        Returns:
            FailureNotification instance
        """
        return cls(
            message_id=str(uuid.uuid4()),
            selector_id=selector_id,
            page_url=page_url,
            timestamp=datetime.now(timezone.utc),
            failure_type=failure_type,
            extractor_id=extractor_id,
            error_message=error_message,
            confidence_score=confidence_score,
        )
    
    def to_json(self) -> str:
        """
        Convert notification to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()


class NotificationAcknowledgment(BaseModel):
    """
    Model for WebSocket acknowledgment messages.
    
    Sent by server to acknowledge receipt of a notification.
    """
    acknowledged_message_id: str = Field(
        description="ID of the message being acknowledged"
    )
    status: str = Field(
        description="Status of acknowledgment (received, processed, error)"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of acknowledgment",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    error: Optional[str] = Field(
        default=None,
        description="Optional error message if status is error"
    )


class ConnectionStatus(BaseModel):
    """
    Model for WebSocket connection status updates.
    """
    status: str = Field(
        description="Connection status (connected, disconnected, reconnecting)"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of status change",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    retry_count: Optional[int] = Field(
        default=None,
        description="Current retry count if reconnecting"
    )
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message if applicable"
    )


class NotificationType(str, Enum):
    """
    Types of notifications that can be sent via WebSocket.
    
    Used for dispatching different notification types to handlers.
    """
    FAILURE = "failure"
    CONFIDENCE_SCORE_UPDATE = "confidence_score_update"
    CONFIDENCE_SCORE_REFRESH = "confidence_score_refresh"
    ALERT = "alert"
    CONNECTION_STATUS = "connection_status"
    HEALTH_STATUS_UPDATE = "health_status_update"
    HEALTH_SNAPSHOT = "health_snapshot"


class HealthStatus(str, Enum):
    """
    Health status values for selectors.
    
    Used to categorize selector health based on confidence scores
    and failure patterns.
    """
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class HealthStatusUpdate(BaseModel):
    """
    Model for health status change notifications sent via WebSocket.
    
    Sent when a selector's health status changes in the adaptive module.
    
    Attributes:
        message_id: Unique UUID for deduplication
        notification_type: Type of notification (health_status_update)
        selector_id: ID/name of the selector
        old_status: Previous health status
        new_status: New health status
        timestamp: ISO8601 timestamp of the update
        confidence_score: Optional current confidence score
    """

    message_id: str = Field(
        description="Unique UUID for message deduplication",
        default_factory=lambda: str(uuid.uuid4())
    )
    notification_type: str = Field(
        default="health_status_update",
        description="Type of notification"
    )
    selector_id: str = Field(
        description="ID/name of the selector"
    )
    old_status: HealthStatus = Field(
        description="Previous health status"
    )
    new_status: HealthStatus = Field(
        description="New health status"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of the update",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="Current confidence score if available",
        ge=0.0,
        le=1.0
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_json(self) -> str:
        """
        Convert notification to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()


class SelectorHealthStatus(BaseModel):
    """
    Model for individual selector health status.
    
    Used in health snapshot broadcasts.
    
    Attributes:
        selector_id: ID/name of the selector
        status: Current health status
        confidence_score: Optional current confidence score
        last_updated: ISO8601 timestamp of last update
    """

    selector_id: str = Field(
        description="ID/name of the selector"
    )
    status: HealthStatus = Field(
        description="Current health status"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="Current confidence score",
        ge=0.0,
        le=1.0
    )
    last_updated: datetime = Field(
        description="ISO8601 timestamp of last update",
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthSnapshot(BaseModel):
    """
    Model for periodic health snapshot broadcasts sent via WebSocket.
    
    Sent periodically with current health status for all selectors.
    
    Attributes:
        message_id: Unique UUID for deduplication
        notification_type: Type of notification (health_snapshot)
        snapshot: List of selector health statuses
        timestamp: ISO8601 timestamp of the snapshot
    """

    message_id: str = Field(
        description="Unique UUID for message deduplication",
        default_factory=lambda: str(uuid.uuid4())
    )
    notification_type: str = Field(
        default="health_snapshot",
        description="Type of notification"
    )
    snapshot: list[SelectorHealthStatus] = Field(
        description="List of selector health statuses"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of the snapshot",
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_json(self) -> str:
        """
        Convert notification to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()


class SelectorSubscription(BaseModel):
    """
    Model for client selector subscriptions.
    
    Allows clients to subscribe to specific selectors for filtered notifications.
    
    Attributes:
        selector_ids: List of selector IDs to subscribe to (None = all selectors)
        include_snapshot: Whether to include periodic health snapshots
    """

    selector_ids: Optional[list[str]] = Field(
        default=None,
        description="List of selector IDs to subscribe to (None = all)"
    )
    include_snapshot: bool = Field(
        default=True,
        description="Whether to include periodic health snapshots"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False

    def matches(self, selector_id: str) -> bool:
        """
        Check if this subscription matches the given selector ID.
        
        Args:
            selector_id: The selector ID to check
            
        Returns:
            True if subscription matches, False otherwise
        """
        # If selector_ids is None, subscribe to all
        if self.selector_ids is None:
            return True
        return selector_id in self.selector_ids


class ConfidenceScoreUpdate(BaseModel):
    """
    Model for confidence score update notifications sent via WebSocket.
    
    Sent when a selector's confidence score changes in the adaptive module.
    
    Attributes:
        message_id: Unique UUID for deduplication
        notification_type: Type of notification (confidence_score_update)
        selector_id: ID/name of the selector
        old_score: Previous confidence score (0.0-1.0)
        new_score: New confidence score (0.0-1.0)
        reason: Reason for score change (failure_detected, success_accumulated, manual_adjustment)
        timestamp: ISO8601 timestamp of the update
        is_threshold_breach: Whether this update breached a threshold
    """
    
    message_id: str = Field(
        description="Unique UUID for message deduplication",
        default_factory=lambda: str(uuid.uuid4())
    )
    notification_type: str = Field(
        default="confidence_score_update",
        description="Type of notification"
    )
    selector_id: str = Field(
        description="ID/name of the selector"
    )
    old_score: float = Field(
        description="Previous confidence score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    new_score: float = Field(
        description="New confidence score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    reason: str = Field(
        description="Reason for score change"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of the update",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_threshold_breach: bool = Field(
        default=False,
        description="Whether this update breached a threshold"
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self) -> str:
        """
        Convert notification to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()


class AlertNotification(BaseModel):
    """
    Model for threshold alert notifications sent via WebSocket.
    
    Sent when a selector's confidence score drops below a configurable threshold.
    
    Attributes:
        message_id: Unique UUID for deduplication
        notification_type: Type of notification (alert)
        alert_level: Alert severity level (warning, critical)
        selector_id: ID/name of the selector
        message: Human-readable alert message
        current_score: Current confidence score
        threshold: Threshold that was breached
        timestamp: ISO8601 timestamp of the alert
    """
    
    message_id: str = Field(
        description="Unique UUID for message deduplication",
        default_factory=lambda: str(uuid.uuid4())
    )
    notification_type: str = Field(
        default="alert",
        description="Type of notification"
    )
    alert_level: str = Field(
        description="Alert severity level (warning, critical)"
    )
    selector_id: str = Field(
        description="ID/name of the selector"
    )
    message: str = Field(
        description="Human-readable alert message"
    )
    current_score: float = Field(
        description="Current confidence score",
        ge=0.0,
        le=1.0
    )
    threshold: float = Field(
        description="Threshold that was breached",
        ge=0.0,
        le=1.0
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of the alert",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self) -> str:
        """
        Convert notification to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()


class ConfidenceScoreRefresh(BaseModel):
    """
    Model for periodic confidence score refresh broadcasts sent via WebSocket.
    
    Sent periodically with updated scores for all selectors.
    
    Attributes:
        message_id: Unique UUID for deduplication
        notification_type: Type of notification (confidence_score_refresh)
        scores: List of selector confidence scores
        timestamp: ISO8601 timestamp of the refresh
        is_delta: Whether this is a delta update (vs full refresh)
    """
    
    message_id: str = Field(
        description="Unique UUID for message deduplication",
        default_factory=lambda: str(uuid.uuid4())
    )
    notification_type: str = Field(
        default="confidence_score_refresh",
        description="Type of notification"
    )
    scores: list[dict] = Field(
        description="List of selector confidence scores"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of the refresh",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_delta: bool = Field(
        default=False,
        description="Whether this is a delta update vs full refresh"
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self) -> str:
        """
        Convert notification to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()


class BlastRadiusSeverity(str, Enum):
    """
    Severity levels for blast radius assessment.
    
    Used in blast radius notifications.
    """
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class BlastRadiusUpdate(BaseModel):
    """
    Model for blast radius update notifications sent via WebSocket.
    
    Sent when a selector fails and blast radius is calculated.
    Includes information about affected fields, records, and severity.
    
    Attributes:
        message_id: Unique UUID for deduplication
        notification_type: Type of notification (blast_radius_update)
        failed_selector: The selector ID that failed
        severity: Severity level (critical/major/minor)
        affected_fields: List of data fields impacted
        affected_records: Count of records affected
        timestamp: ISO8601 timestamp of the update
        confidence_score: Current confidence score
        recommended_actions: List of recommended actions
    """

    message_id: str = Field(
        description="Unique UUID for message deduplication",
        default_factory=lambda: str(uuid.uuid4())
    )
    notification_type: str = Field(
        default="blast_radius_update",
        description="Type of notification"
    )
    failed_selector: str = Field(
        description="The selector ID that failed"
    )
    severity: BlastRadiusSeverity = Field(
        description="Severity level of the blast radius"
    )
    affected_fields: list[str] = Field(
        default_factory=list,
        description="List of data fields impacted"
    )
    affected_records: int = Field(
        default=0,
        description="Count of records affected"
    )
    timestamp: datetime = Field(
        description="ISO8601 timestamp of the update",
        default_factory=lambda: datetime.now(timezone.utc)
    )
    confidence_score: float = Field(
        description="Current confidence score",
        ge=0.0,
        le=1.0
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="List of recommended actions"
    )
    cascading_selectors: list[str] = Field(
        default_factory=list,
        description="List of related selectors potentially impacted (AC3)"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_json(self) -> str:
        """
        Convert notification to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()
