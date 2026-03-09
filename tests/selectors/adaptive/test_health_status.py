"""
Unit tests for Health Status Service.

Tests the health status calculation service for:
- Health status calculation from confidence scores
- Dashboard grouping
- Recommended actions
- Alternative selector lookup

Story: 6.2 - Selector Health Status Display
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from src.selectors.adaptive.services.health_status_service import (
    HealthStatusService,
    HealthStatus,
    HealthStatusConfig,
    SelectorHealthInfo,
    HealthDashboardData,
    get_health_status_service,
)
from src.selectors.adaptive.services.confidence_query_service import (
    ConfidenceQueryService,
    ConfidenceScoreResult,
)
from src.selectors.adaptive.db.repositories.failure_event_repository import (
    FailureEventRepository,
)
from src.selectors.yaml_loader import YAMLSelectorLoader


# Mock objects
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
    
    def __init__(self, alternatives=None):
        self._alternatives = alternatives or {}
        self._cache = {}
    
    @property
    def _selector_cache(self):
        return self._cache
    
    @_selector_cache.setter
    def _selector_cache(self, value):
        self._cache = value


class TestHealthStatusCalculation:
    """Test cases for health status calculation."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return HealthStatusConfig(
            healthy_threshold=0.8,
            degraded_threshold=0.5,
            failed_threshold=0.5,
        )
    
    @pytest.fixture
    def service(self, config):
        """Create health status service with mocks."""
        mock_confidence = Mock()
        mock_confidence.query_single = Mock(side_effect=lambda sid: ConfidenceScoreResult(
            selector_id=sid,
            confidence_score=0.9,
            last_updated=datetime.now(timezone.utc),
            is_estimated=False,
        ))
        mock_repository = Mock(spec=FailureEventRepository)
        mock_repository.get_unique_selectors.return_value = []
        mock_repository.get_by_selector.return_value = []
        
        return HealthStatusService(
            confidence_service=mock_confidence,
            failure_repository=mock_repository,
            config=config,
        )
    
    def test_calculate_status_healthy(self, service):
        """Test health status calculation for healthy threshold."""
        # confidence >= 0.8 = healthy
        assert service.calculate_status(0.8) == HealthStatus.HEALTHY
        assert service.calculate_status(0.9) == HealthStatus.HEALTHY
        assert service.calculate_status(1.0) == HealthStatus.HEALTHY
    
    def test_calculate_status_degraded(self, service):
        """Test health status calculation for degraded threshold."""
        # 0.5 <= confidence < 0.8 = degraded
        assert service.calculate_status(0.5) == HealthStatus.DEGRADED
        assert service.calculate_status(0.6) == HealthStatus.DEGRADED
        assert service.calculate_status(0.79) == HealthStatus.DEGRADED
    
    def test_calculate_status_failed(self, service):
        """Test health status calculation for failed threshold."""
        # confidence < 0.5 = failed
        assert service.calculate_status(0.0) == HealthStatus.FAILED
        assert service.calculate_status(0.1) == HealthStatus.FAILED
        assert service.calculate_status(0.49) == HealthStatus.FAILED
    
    def test_calculate_status_boundary_values(self, service):
        """Test boundary values for health status."""
        # Test exact boundary values
        assert service.calculate_status(0.799999) == HealthStatus.DEGRADED
        assert service.calculate_status(0.8) == HealthStatus.HEALTHY
        assert service.calculate_status(0.5) == HealthStatus.DEGRADED
        assert service.calculate_status(0.499999) == HealthStatus.FAILED


class TestRecommendedActions:
    """Test cases for recommended actions."""
    
    @pytest.fixture
    def service(self):
        """Create health status service."""
        mock_confidence = MockConfidenceService()
        mock_repository = Mock(spec=FailureEventRepository)
        mock_repository.get_unique_selectors.return_value = []
        mock_repository.get_by_selector.return_value = []
        
        return HealthStatusService(
            confidence_service=mock_confidence,
            failure_repository=mock_repository,
        )
    
    def test_recommended_action_healthy(self, service):
        """Test recommended action for healthy status."""
        action = service.get_recommended_action(HealthStatus.HEALTHY, [])
        assert "performing well" in action.lower()
    
    def test_recommended_action_degraded(self, service):
        """Test recommended action for degraded status."""
        action = service.get_recommended_action(HealthStatus.DEGRADED, [])
        assert "moderate" in action.lower() or "review" in action.lower()
    
    def test_recommended_action_degraded_with_alternatives(self, service):
        """Test recommended action for degraded status with alternatives."""
        alternatives = ["selector_2", "selector_3"]
        action = service.get_recommended_action(HealthStatus.DEGRADED, alternatives)
        assert "alternatives" in action.lower()
        assert "selector_2" in action
    
    def test_recommended_action_failed(self, service):
        """Test recommended action for failed status."""
        action = service.get_recommended_action(HealthStatus.FAILED, [])
        assert "immediate" in action.lower() or "attention" in action.lower()
    
    def test_recommended_action_failed_with_alternatives(self, service):
        """Test recommended action for failed status with alternatives."""
        alternatives = ["selector_2"]
        action = service.get_recommended_action(HealthStatus.FAILED, alternatives)
        assert "alternatives" in action.lower() or "use" in action.lower()


class TestDashboardGrouping:
    """Test cases for dashboard grouping."""
    
    @pytest.fixture
    def service(self):
        """Create health status service with mock data."""
        scores = {
            "selector_1": 0.9,  # healthy
            "selector_2": 0.6,  # degraded
            "selector_3": 0.3,  # failed
        }
        mock_confidence = MockConfidenceService(scores)
        mock_repository = Mock(spec=FailureEventRepository)
        mock_repository.get_unique_selectors.return_value = ["selector_1", "selector_2", "selector_3"]
        mock_repository.get_by_selector.return_value = []
        
        return HealthStatusService(
            confidence_service=mock_confidence,
            failure_repository=mock_repository,
        )
    
    def test_dashboard_grouping(self, service):
        """Test dashboard groups selectors correctly."""
        dashboard = service.get_dashboard()
        
        # Check counts
        assert dashboard.total == 3
        assert len(dashboard.healthy) == 1
        assert len(dashboard.degraded) == 1
        assert len(dashboard.failed) == 1
    
    def test_dashboard_healthy_selectors(self, service):
        """Test healthy selectors in dashboard."""
        dashboard = service.get_dashboard()
        
        healthy_ids = [h.selector_id for h in dashboard.healthy]
        assert "selector_1" in healthy_ids
    
    def test_dashboard_degraded_selectors(self, service):
        """Test degraded selectors in dashboard."""
        dashboard = service.get_dashboard()
        
        degraded_ids = [h.selector_id for h in dashboard.degraded]
        assert "selector_2" in degraded_ids
    
    def test_dashboard_failed_selectors(self, service):
        """Test failed selectors in dashboard."""
        dashboard = service.get_dashboard()
        
        failed_ids = [h.selector_id for h in dashboard.failed]
        assert "selector_3" in failed_ids
    
    def test_dashboard_empty(self, service):
        """Test dashboard with no selectors."""
        service.failure_repository.get_unique_selectors.return_value = []
        
        dashboard = service.get_dashboard()
        
        assert dashboard.total == 0
        assert len(dashboard.healthy) == 0
        assert len(dashboard.degraded) == 0
        assert len(dashboard.failed) == 0


class TestSelectorHealthInfo:
    """Test cases for selector health info."""
    
    @pytest.fixture
    def service(self):
        """Create health status service."""
        mock_confidence = MockConfidenceService({"test_selector": 0.7})
        mock_repository = Mock(spec=FailureEventRepository)
        mock_repository.get_by_selector.return_value = []
        
        return HealthStatusService(
            confidence_service=mock_confidence,
            failure_repository=mock_repository,
        )
    
    def test_get_selector_health(self, service):
        """Test getting health info for single selector."""
        health = service.get_selector_health("test_selector")
        
        assert health.selector_id == "test_selector"
        assert health.confidence_score == 0.7
        assert health.status == HealthStatus.DEGRADED
    
    def test_get_selector_health_includes_alternatives(self, service):
        """Test that alternatives are included in health info."""
        # Mock YAML loader with alternatives
        with patch.object(service, 'get_alternatives_from_yaml', return_value=["alt_1", "alt_2"]):
            health = service.get_selector_health("test_selector")
            
            assert len(health.alternatives) == 2
            assert "alt_1" in health.alternatives
    
    def test_get_selector_health_includes_recommendation(self, service):
        """Test that recommendation is included in health info."""
        health = service.get_selector_health("test_selector")
        
        assert health.recommended_action is not None
        assert len(health.recommended_action) > 0


class TestHealthStatusConfig:
    """Test cases for health status configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = HealthStatusConfig()
        
        assert config.healthy_threshold == 0.8
        assert config.degraded_threshold == 0.5
        assert config.failed_threshold == 0.5
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = HealthStatusConfig(
            healthy_threshold=0.9,
            degraded_threshold=0.7,
            failed_threshold=0.3,
        )
        
        assert config.healthy_threshold == 0.9
        assert config.degraded_threshold == 0.7
        assert config.failed_threshold == 0.3


class TestGlobalService:
    """Test cases for global service singleton."""
    
    def test_get_health_status_service(self):
        """Test getting global service instance."""
        service = get_health_status_service()
        
        assert service is not None
        assert isinstance(service, HealthStatusService)
    
    def test_service_is_singleton(self):
        """Test that service returns same instance."""
        service1 = get_health_status_service()
        service2 = get_health_status_service()
        
        assert service1 is service2
