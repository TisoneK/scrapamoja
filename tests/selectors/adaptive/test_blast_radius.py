"""
Unit tests for Blast Radius Service.

Tests the blast radius calculation service for:
- Severity assessment based on confidence scores
- Affected fields detection
- Cascading effects detection
- Recommended actions generation

Story: 6.3 - Blast Radius Calculation
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import List

from src.selectors.adaptive.services.blast_radius_service import (
    BlastRadiusService,
    BlastRadiusConfig,
    BlastRadiusSeverity,
    FieldType,
    DependencyType,
    AffectedFieldData,
    CascadingSelectorData,
    BlastRadiusResult,
    get_blast_radius_service,
)
from src.selectors.adaptive.services.confidence_query_service import (
    ConfidenceQueryService,
    ConfidenceScoreResult,
)
from src.selectors.adaptive.services.health_status_service import (
    HealthStatusService,
)
from src.selectors.adaptive.db.repositories.failure_event_repository import (
    FailureEventRepository,
)
from src.selectors.yaml_loader import YAMLSelectorLoader


class MockConfidenceService:
    """Mock confidence query service."""
    
    def __init__(self, scores=None):
        self._scores = scores or {}
    
    def query_single(self, selector_id):
        score = self._scores.get(selector_id, 0.5)
        return ConfidenceScoreResult(
            selector_id=selector_id,
            confidence_score=score,
            last_updated=datetime.now(timezone.utc),
            is_estimated=False,
        )


class MockYAMLLoader:
    """Mock YAML loader."""
    
    def __init__(self, selectors=None, dependencies=None):
        self._selectors = selectors or {}
        self._dependencies = dependencies or {}
        self._cache = {}
    
    @property
    def _selector_cache(self):
        return self._cache
    
    @_selector_cache.setter
    def _selector_cache(self, value):
        self._cache = value


class MockFailureRepository:
    """Mock failure event repository."""
    
    def __init__(self, events=None):
        self._events = events or {}
    
    def get_by_selector(self, selector_id, limit=None):
        return self._events.get(selector_id, [])


class MockHealthService:
    """Mock health status service."""
    
    def __init__(self, alternatives=None):
        self._alternatives = alternatives or {}
    
    def get_alternatives_from_yaml(self, selector_id):
        return self._alternatives.get(selector_id, [])


class TestSeverityCalculation:
    """Test cases for severity calculation."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BlastRadiusConfig(
            critical_confidence_threshold=0.5,
            major_confidence_threshold=0.8,
            critical_fields=["home_team", "away_team", "score"],
        )
    
    @pytest.fixture
    def service(self, config):
        """Create blast radius service with mocks."""
        mock_confidence = MockConfidenceService()
        mock_health = MockHealthService()
        mock_repository = MockFailureRepository()
        mock_loader = MockYAMLLoader()
        
        return BlastRadiusService(
            confidence_service=mock_confidence,
            health_service=mock_health,
            failure_repository=mock_repository,
            yaml_loader=mock_loader,
            config=config,
        )
    
    def test_severity_critical_low_confidence_primary_field(self, service):
        """Test critical severity with low confidence and primary field."""
        severity = service.calculate_severity(0.3, is_primary_field=True)
        assert severity == BlastRadiusSeverity.CRITICAL
    
    def test_severity_critical_low_confidence_secondary_field(self, service):
        """Test critical severity with low confidence."""
        severity = service.calculate_severity(0.3, is_primary_field=False)
        assert severity == BlastRadiusSeverity.CRITICAL
    
    def test_severity_major_degraded_confidence(self, service):
        """Test major severity with degraded confidence."""
        severity = service.calculate_severity(0.6, is_primary_field=False)
        assert severity == BlastRadiusSeverity.MAJOR
    
    def test_severity_minor_healthy_confidence(self, service):
        """Test minor severity with healthy confidence."""
        severity = service.calculate_severity(0.9, is_primary_field=False)
        assert severity == BlastRadiusSeverity.MINOR
    
    def test_severity_boundary_05_critical(self, service):
        """Test boundary at 0.5 - should be MAJOR (not critical)."""
        severity = service.calculate_severity(0.5, is_primary_field=False)
        assert severity == BlastRadiusSeverity.MAJOR
    
    def test_severity_boundary_08_minor(self, service):
        """Test boundary at 0.8 - should be MINOR."""
        severity = service.calculate_severity(0.8, is_primary_field=False)
        assert severity == BlastRadiusSeverity.MINOR


class TestFieldTypeDetection:
    """Test cases for field type detection."""
    
    @pytest.fixture
    def service(self):
        """Create blast radius service."""
        return BlastRadiusService()
    
    def test_primary_field_type(self, service):
        """Test primary field type detection."""
        assert service.get_field_type("home_team") == FieldType.PRIMARY
        assert service.get_field_type("away_team") == FieldType.PRIMARY
        assert service.get_field_type("score") == FieldType.PRIMARY
        assert service.get_field_type("match_time") == FieldType.PRIMARY
    
    def test_secondary_field_type(self, service):
        """Test secondary field type detection."""
        assert service.get_field_type("odds") == FieldType.SECONDARY
        assert service.get_field_type("weather") == FieldType.SECONDARY
        assert service.get_field_type("venue") == FieldType.SECONDARY
    
    def test_auxiliary_field_type(self, service):
        """Test auxiliary field type detection."""
        assert service.get_field_type("highlights") == FieldType.AUXILIARY
        assert service.get_field_type("statistics") == FieldType.AUXILIARY
        assert service.get_field_type("unknown_field") == FieldType.AUXILIARY


class TestRecommendedActions:
    """Test cases for recommended actions generation."""
    
    @pytest.fixture
    def service(self):
        """Create blast radius service."""
        return BlastRadiusService()
    
    def test_critical_recommended_actions(self, service):
        """Test recommended actions for critical severity."""
        actions = service.get_recommended_actions(
            BlastRadiusSeverity.CRITICAL,
            ["alt_selector1", "alt_selector2"]
        )
        assert "URGENT" in actions[0]
        assert "alt_selector1" in actions[1]
    
    def test_critical_no_alternatives(self, service):
        """Test recommended actions for critical with no alternatives."""
        actions = service.get_recommended_actions(
            BlastRadiusSeverity.CRITICAL,
            []
        )
        assert "No alternatives available" in actions[1]
    
    def test_major_recommended_actions(self, service):
        """Test recommended actions for major severity."""
        actions = service.get_recommended_actions(
            BlastRadiusSeverity.MAJOR,
            ["alt1", "alt2"]
        )
        assert "degraded" in actions[0].lower()
        assert "Alternatives available" in actions[2]
    
    def test_minor_recommended_actions(self, service):
        """Test recommended actions for minor severity."""
        actions = service.get_recommended_actions(
            BlastRadiusSeverity.MINOR,
            []
        )
        assert "adequately" in actions[0].lower()
        assert "no immediate action" in actions[1].lower()


class TestCascadingSelectors:
    """Test cases for cascading selector detection."""
    
    @pytest.fixture
    def service(self):
        """Create blast radius service."""
        return BlastRadiusService()
    
    def test_empty_cascading_selectors(self, service):
        """Test empty cascading selectors."""
        selectors = service.get_cascading_selectors("unknown_selector")
        assert selectors == []


class TestBlastRadiusCalculation:
    """Test cases for blast radius calculation."""
    
    @pytest.fixture
    def mock_selector(self):
        """Create a mock selector."""
        mock = MagicMock()
        mock.id = "home_team"
        mock.metadata = {"extracted_fields": ["home_team", "away_team"]}
        mock.hints = None
        return mock
    
    @pytest.fixture
    def service_with_mocks(self, mock_selector):
        """Create blast radius service with proper mocks."""
        mock_confidence = MockConfidenceService({"home_team": 0.3})
        mock_health = MockHealthService({"home_team": ["alt_home_team"]})
        
        # Create mock failure events
        mock_events = [
            Mock(timestamp=datetime.now(timezone.utc)),
            Mock(timestamp=datetime.now(timezone.utc)),
        ]
        mock_repository = MockFailureRepository({"home_team": mock_events})
        
        # Create mock YAML loader with selector
        mock_loader = MockYAMLLoader()
        mock_loader._cache = {"path/to/selector.yaml": mock_selector}
        
        return BlastRadiusService(
            confidence_service=mock_confidence,
            health_service=mock_health,
            failure_repository=mock_repository,
            yaml_loader=mock_loader,
        )
    
    def test_calculate_blast_radius_returns_result(self, service_with_mocks):
        """Test blast radius calculation returns result."""
        result = service_with_mocks.calculate_blast_radius("home_team")
        
        assert isinstance(result, BlastRadiusResult)
        assert result.failed_selector == "home_team"
        assert result.confidence_score == 0.3
    
    def test_calculate_blast_radius_critical_severity(self, service_with_mocks):
        """Test blast radius calculation returns critical severity."""
        result = service_with_mocks.calculate_blast_radius("home_team")
        
        assert result.severity == BlastRadiusSeverity.CRITICAL
    
    def test_calculate_blast_radius_affected_records(self, service_with_mocks):
        """Test blast radius affected records count."""
        result = service_with_mocks.calculate_blast_radius("home_team")
        
        # Should have 2 events
        assert result.affected_records == 2
    
    def test_calculate_blast_radius_recommended_actions(self, service_with_mocks):
        """Test blast radius includes recommended actions."""
        result = service_with_mocks.calculate_blast_radius(
            "home_team",
            include_recommended_actions=True
        )
        
        assert len(result.recommended_actions) > 0
        assert "URGENT" in result.recommended_actions[0]


class TestBatchBlastRadius:
    """Test cases for batch blast radius calculation."""
    
    @pytest.fixture
    def service_with_mocks(self):
        """Create blast radius service with mocks."""
        mock_confidence = MockConfidenceService({
            "selector1": 0.3,
            "selector2": 0.7,
            "selector3": 0.9,
        })
        mock_health = MockHealthService()
        mock_repository = MockFailureRepository()
        mock_loader = MockYAMLLoader()
        
        return BlastRadiusService(
            confidence_service=mock_confidence,
            health_service=mock_health,
            failure_repository=mock_repository,
            yaml_loader=mock_loader,
        )
    
    def test_batch_calculation(self, service_with_mocks):
        """Test batch blast radius calculation."""
        results = service_with_mocks.calculate_batch_blast_radius(
            ["selector1", "selector2", "selector3"]
        )
        
        assert len(results) == 3
        assert "selector1" in results
        assert "selector2" in results
        assert "selector3" in results
    
    def test_batch_severity_distribution(self, service_with_mocks):
        """Test batch severity distribution."""
        results = service_with_mocks.calculate_batch_blast_radius(
            ["selector1", "selector2", "selector3"]
        )
        
        # selector1: 0.3 -> critical
        assert results["selector1"].severity == BlastRadiusSeverity.CRITICAL
        # selector2: 0.7 -> major
        assert results["selector2"].severity == BlastRadiusSeverity.MAJOR
        # selector3: 0.9 -> minor
        assert results["selector3"].severity == BlastRadiusSeverity.MINOR


class TestBlastRadiusSummary:
    """Test cases for blast radius summary."""
    
    @pytest.fixture
    def service_with_mocks(self):
        """Create blast radius service with mocks."""
        mock_confidence = MockConfidenceService({
            "selector1": 0.3,
            "selector2": 0.7,
            "selector3": 0.9,
        })
        mock_health = MockHealthService()
        mock_repository = MockFailureRepository()
        mock_loader = MockYAMLLoader()
        
        return BlastRadiusService(
            confidence_service=mock_confidence,
            health_service=mock_health,
            failure_repository=mock_repository,
            yaml_loader=mock_loader,
        )
    
    def test_summary_calculation(self, service_with_mocks):
        """Test blast radius summary calculation."""
        summary = service_with_mocks.get_blast_radius_summary(
            ["selector1", "selector2", "selector3"]
        )
        
        assert summary["selectors_analyzed"] == 3
        assert summary["critical_count"] == 1
        assert summary["major_count"] == 1
        assert summary["minor_count"] == 1
        assert summary["total_affected_records"] >= 0


class TestServiceIntegration:
    """Test cases for service singleton pattern."""
    
    def test_get_service_returns_singleton(self):
        """Test that get_blast_radius_service returns singleton."""
        service1 = get_blast_radius_service()
        service2 = get_blast_radius_service()
        
        assert service1 is service2
    
    def test_clear_cache(self):
        """Test cache clearing."""
        service = get_blast_radius_service()
        # Add something to cache (internal)
        service._dependency_cache["test"] = []
        
        service.clear_cache()
        
        assert len(service._dependency_cache) == 0
