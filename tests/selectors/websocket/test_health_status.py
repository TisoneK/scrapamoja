"""
Unit tests for health status notification models.

Story 5.3: Selector Health Status Streaming
- AC1: Health Status Change Notification
- AC2: Periodic Health Snapshot Broadcast
- AC3: Individual Selector Subscription
"""

import pytest
from datetime import datetime, timezone

from src.selectors.websocket.models import (
    HealthStatus,
    HealthStatusUpdate,
    SelectorHealthStatus,
    HealthSnapshot,
    SelectorSubscription,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Test that all expected health status values exist."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.FAILED.value == "failed"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthStatusUpdate:
    """Tests for HealthStatusUpdate model."""

    def test_health_status_update_model(self):
        """Test HealthStatusUpdate model creation."""
        update = HealthStatusUpdate(
            selector_id="selector_1",
            old_status=HealthStatus.HEALTHY,
            new_status=HealthStatus.DEGRADED,
            confidence_score=0.5,
        )
        
        assert update.selector_id == "selector_1"
        assert update.old_status == HealthStatus.HEALTHY
        assert update.new_status == HealthStatus.DEGRADED
        assert update.confidence_score == 0.5
        assert update.notification_type == "health_status_update"
        assert update.message_id is not None

    def test_health_status_update_json_encoding(self):
        """Test HealthStatusUpdate JSON serialization."""
        update = HealthStatusUpdate(
            selector_id="selector_1",
            old_status=HealthStatus.HEALTHY,
            new_status=HealthStatus.DEGRADED,
            confidence_score=0.5,
        )
        
        json_str = update.to_json()
        assert "selector_1" in json_str
        assert "health" in json_str
        assert "healthy" in json_str
        assert "degraded" in json_str

    def test_health_status_update_with_none_confidence(self):
        """Test HealthStatusUpdate without confidence score."""
        update = HealthStatusUpdate(
            selector_id="selector_1",
            old_status=HealthStatus.HEALTHY,
            new_status=HealthStatus.FAILED,
        )
        
        assert update.confidence_score is None

    def test_health_status_update_model_serialization_roundtrip(self):
        """Test that HealthStatusUpdate can be serialized and deserialized."""
        import json
        original = HealthStatusUpdate(
            selector_id="test_selector",
            old_status=HealthStatus.DEGRADED,
            new_status=HealthStatus.HEALTHY,
            confidence_score=0.8,
        )
        
        # Serialize
        json_str = original.to_json()
        
        # Deserialize
        data = json.loads(json_str)
        
        assert data["selector_id"] == "test_selector"
        assert data["old_status"] == "degraded"
        assert data["new_status"] == "healthy"
        assert data["confidence_score"] == 0.8


class TestSelectorHealthStatus:
    """Tests for SelectorHealthStatus model."""

    def test_selector_health_status_model(self):
        """Test SelectorHealthStatus model creation."""
        status = SelectorHealthStatus(
            selector_id="selector_1",
            status=HealthStatus.HEALTHY,
            confidence_score=0.9,
        )
        
        assert status.selector_id == "selector_1"
        assert status.status == HealthStatus.HEALTHY
        assert status.confidence_score == 0.9

    def test_selector_health_status_default_timestamp(self):
        """Test that default timestamp is set."""
        status = SelectorHealthStatus(
            selector_id="selector_1",
            status=HealthStatus.DEGRADED,
        )
        
        assert status.last_updated is not None


class TestHealthSnapshot:
    """Tests for HealthSnapshot model."""

    def test_health_snapshot_model(self):
        """Test HealthSnapshot model creation."""
        snapshot = HealthSnapshot(
            snapshot=[
                SelectorHealthStatus(
                    selector_id="selector_1",
                    status=HealthStatus.HEALTHY,
                    confidence_score=0.9,
                ),
                SelectorHealthStatus(
                    selector_id="selector_2",
                    status=HealthStatus.DEGRADED,
                    confidence_score=0.5,
                ),
            ]
        )
        
        assert len(snapshot.snapshot) == 2
        assert snapshot.notification_type == "health_snapshot"
        assert snapshot.message_id is not None

    def test_health_snapshot_json_encoding(self):
        """Test HealthSnapshot JSON serialization."""
        snapshot = HealthSnapshot(
            snapshot=[
                SelectorHealthStatus(
                    selector_id="selector_1",
                    status=HealthStatus.HEALTHY,
                ),
            ]
        )
        
        json_str = snapshot.to_json()
        assert "selector_1" in json_str
        assert "health_snapshot" in json_str
        assert "healthy" in json_str


class TestSelectorSubscription:
    """Tests for SelectorSubscription model."""

    def test_subscription_all_selectors(self):
        """Test subscription with None (all selectors)."""
        sub = SelectorSubscription(selector_ids=None)
        
        assert sub.selector_ids is None
        assert sub.matches("any_selector") is True

    def test_subscription_specific_selectors(self):
        """Test subscription with specific selectors."""
        sub = SelectorSubscription(
            selector_ids=["selector_1", "selector_2"],
            include_snapshot=True,
        )
        
        assert sub.matches("selector_1") is True
        assert sub.matches("selector_2") is True
        assert sub.matches("selector_3") is False

    def test_subscription_default_include_snapshot(self):
        """Test default include_snapshot value."""
        sub = SelectorSubscription()
        
        assert sub.include_snapshot is True

    def test_subscription_empty_list(self):
        """Test subscription with empty list."""
        sub = SelectorSubscription(selector_ids=[])
        
        # Empty list means no selectors
        assert sub.matches("any_selector") is False
