"""
Unit tests for blast radius WebSocket notification models.

Story 6.3: Blast Radius Calculation
- AC3: Cascading Effects
- AC5: Real-Time Blast Radius Updates via WebSocket
"""

import pytest
from datetime import datetime, timezone

from src.selectors.websocket.models import (
    BlastRadiusSeverity,
    BlastRadiusUpdate,
)


class TestBlastRadiusSeverity:
    """Tests for BlastRadiusSeverity enum."""

    def test_blast_radius_severity_values(self):
        """Test that all expected severity values exist."""
        assert BlastRadiusSeverity.CRITICAL.value == "critical"
        assert BlastRadiusSeverity.MAJOR.value == "major"
        assert BlastRadiusSeverity.MINOR.value == "minor"


class TestBlastRadiusUpdate:
    """Tests for BlastRadiusUpdate model (AC5)."""

    def test_blast_radius_update_model_basic(self):
        """Test BlastRadiusUpdate model basic creation."""
        update = BlastRadiusUpdate(
            failed_selector="home_team",
            severity=BlastRadiusSeverity.CRITICAL,
            affected_fields=["home_team", "away_team"],
            affected_records=10,
            confidence_score=0.3,
        )
        
        assert update.failed_selector == "home_team"
        assert update.severity == BlastRadiusSeverity.CRITICAL
        assert update.affected_fields == ["home_team", "away_team"]
        assert update.affected_records == 10
        assert update.confidence_score == 0.3
        assert update.notification_type == "blast_radius_update"
        assert update.message_id is not None
        assert update.timestamp is not None

    def test_blast_radius_update_with_recommended_actions(self):
        """Test BlastRadiusUpdate with recommended actions."""
        actions = [
            "URGENT: Selector requires immediate attention",
            "Consider using alternative selectors: alt_home_team",
        ]
        
        update = BlastRadiusUpdate(
            failed_selector="home_team",
            severity=BlastRadiusSeverity.CRITICAL,
            affected_fields=["home_team"],
            affected_records=5,
            confidence_score=0.2,
            recommended_actions=actions,
        )
        
        assert len(update.recommended_actions) == 2
        assert "URGENT" in update.recommended_actions[0]

    def test_blast_radius_update_with_cascading_selectors(self):
        """Test BlastRadiusUpdate with cascading selectors (AC3)."""
        cascading = ["away_team", "score"]
        
        update = BlastRadiusUpdate(
            failed_selector="home_team",
            severity=BlastRadiusSeverity.MAJOR,
            affected_fields=["home_team"],
            affected_records=8,
            confidence_score=0.6,
            cascading_selectors=cascading,
        )
        
        assert update.cascading_selectors == ["away_team", "score"]

    def test_blast_radius_update_default_cascading_selectors(self):
        """Test BlastRadiusUpdate defaults cascading_selectors to empty list."""
        update = BlastRadiusUpdate(
            failed_selector="home_team",
            severity=BlastRadiusSeverity.MINOR,
            affected_fields=[],
            affected_records=0,
            confidence_score=0.9,
        )
        
        assert update.cascading_selectors == []

    def test_blast_radius_update_json_encoding(self):
        """Test BlastRadiusUpdate JSON serialization."""
        update = BlastRadiusUpdate(
            failed_selector="home_team",
            severity=BlastRadiusSeverity.CRITICAL,
            affected_fields=["home_team", "away_team"],
            affected_records=10,
            confidence_score=0.3,
            recommended_actions=["Action 1"],
            cascading_selectors=["away_team"],
        )
        
        json_str = update.to_json()
        assert "home_team" in json_str
        assert "critical" in json_str
        assert "blast_radius_update" in json_str
        assert "away_team" in json_str  # cascading selectors
        assert "Action 1" in json_str

    def test_blast_radius_update_model_all_severity_levels(self):
        """Test BlastRadiusUpdate with all severity levels."""
        # Critical
        critical = BlastRadiusUpdate(
            failed_selector="selector_1",
            severity=BlastRadiusSeverity.CRITICAL,
            affected_fields=["field1"],
            affected_records=100,
            confidence_score=0.3,
        )
        assert critical.severity == BlastRadiusSeverity.CRITICAL
        
        # Major
        major = BlastRadiusUpdate(
            failed_selector="selector_2",
            severity=BlastRadiusSeverity.MAJOR,
            affected_fields=["field2"],
            affected_records=50,
            confidence_score=0.7,
        )
        assert major.severity == BlastRadiusSeverity.MAJOR
        
        # Minor
        minor = BlastRadiusUpdate(
            failed_selector="selector_3",
            severity=BlastRadiusSeverity.MINOR,
            affected_fields=["field3"],
            affected_records=5,
            confidence_score=0.9,
        )
        assert minor.severity == BlastRadiusSeverity.MINOR

    def test_blast_radius_update_confidence_score_bounds(self):
        """Test BlastRadiusUpdate confidence_score bounds."""
        # Valid scores should work
        update_low = BlastRadiusUpdate(
            failed_selector="test",
            severity=BlastRadiusSeverity.CRITICAL,
            affected_fields=[],
            affected_records=0,
            confidence_score=0.0,
        )
        assert update_low.confidence_score == 0.0
        
        update_high = BlastRadiusUpdate(
            failed_selector="test",
            severity=BlastRadiusSeverity.MINOR,
            affected_fields=[],
            affected_records=0,
            confidence_score=1.0,
        )
        assert update_high.confidence_score == 1.0

    def test_blast_radius_update_model_serialization_roundtrip(self):
        """Test BlastRadiusUpdate serialization and deserialization."""
        import json
        
        original = BlastRadiusUpdate(
            failed_selector="home_team",
            severity=BlastRadiusSeverity.CRITICAL,
            affected_fields=["home_team", "away_team"],
            affected_records=10,
            confidence_score=0.3,
            recommended_actions=["Test action"],
            cascading_selectors=["away_team"],
        )
        
        # Serialize
        json_str = original.to_json()
        
        # Deserialize
        data = json.loads(json_str)
        
        # Verify all fields are preserved
        assert data["failed_selector"] == "home_team"
        assert data["severity"] == "critical"
        assert data["affected_fields"] == ["home_team", "away_team"]
        assert data["affected_records"] == 10
        assert data["confidence_score"] == 0.3
        assert "Test action" in data["recommended_actions"]
        assert "away_team" in data["cascading_selectors"]

    def test_blast_radius_update_with_empty_fields(self):
        """Test BlastRadiusUpdate with empty affected fields."""
        update = BlastRadiusUpdate(
            failed_selector="unknown_selector",
            severity=BlastRadiusSeverity.MINOR,
            affected_fields=[],
            affected_records=0,
            confidence_score=0.95,
        )
        
        assert update.affected_fields == []
        assert update.affected_records == 0

    def test_blast_radius_update_timestamp_default(self):
        """Test that BlastRadiusUpdate has default timestamp."""
        update = BlastRadiusUpdate(
            failed_selector="test",
            severity=BlastRadiusSeverity.MINOR,
            affected_fields=[],
            affected_records=0,
            confidence_score=1.0,
        )
        
        assert update.timestamp is not None
        assert isinstance(update.timestamp, datetime)
