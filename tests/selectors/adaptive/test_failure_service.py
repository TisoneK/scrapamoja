"""
Tests for the Failure Service and API.

These tests validate the implementation of Story 4.1:
View Proposed Selectors with Visual Preview

Tests cover:
- Failure listing with filtering
- Failure detail retrieval
- Alternative selector registration
- Confidence score calculation
- Approval/Rejection workflows
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.selectors.adaptive.services.failure_service import FailureService, get_failure_service
from src.selectors.adaptive.db.models.failure_event import FailureEvent
from src.selectors.adaptive.services.dom_analyzer import StrategyType


class TestFailureService:
    """Test suite for FailureService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock failure event repository."""
        repo = MagicMock()
        return repo
    
    @pytest.fixture
    def mock_recipe_repo(self):
        """Create a mock recipe repository."""
        repo = MagicMock()
        mock_recipe = MagicMock()
        mock_recipe.recipe_id = "recipe-1"
        mock_recipe.version = 1
        mock_recipe.selectors = {}
        mock_recipe.generation = 1
        repo.get_latest_version.return_value = None  # Default to None
        return repo
    
    @pytest.fixture
    def failure_service(self, mock_repository, mock_recipe_repo):
        """Create a FailureService with mock dependencies."""
        with patch('src.selectors.adaptive.services.failure_service.get_logger') as mock_logger:
            mock_logger.return_value = MagicMock()
            service = FailureService(
                failure_repository=mock_repository,
                confidence_scorer=None,
                blast_radius_calculator=None,
                recipe_repository=mock_recipe_repo,
            )
            service._alternatives = {}  # Reset alternatives
            service._snapshot_references = {}
            return service
    
    def test_register_alternative(self, failure_service):
        """Test registering an alternative selector."""
        failure_id = 1
        
        result = failure_service.register_alternative(
            failure_id=failure_id,
            selector=".match-title-new",
            strategy=StrategyType.CSS,
        )
        
        assert result is not None
        assert result.selector_string == ".match-title-new"
        assert result.strategy_type == StrategyType.CSS
        assert failure_id in failure_service._alternatives
        assert len(failure_service._alternatives[failure_id]) == 1
    
    def test_get_failure_detail_not_found(self, failure_service, mock_repository):
        """Test getting detail for non-existent failure."""
        mock_repository.get_by_id.return_value = None
        
        result = failure_service.get_failure_detail(failure_id=999)
        
        assert result is None
    
    def test_get_failure_detail_with_alternatives(self, failure_service, mock_repository):
        """Test getting failure detail with alternatives."""
        # Setup mock failure event
        mock_failure = MagicMock()
        mock_failure.id = 1
        mock_failure.selector_id = ".match-title"
        mock_failure.recipe_id = "recipe-1"
        mock_failure.sport = "basketball"
        mock_failure.site = "flashscore"
        mock_failure.timestamp = datetime.now(timezone.utc)
        mock_failure.error_type = "empty_result"
        mock_failure.failure_reason = "Element not found"
        mock_failure.severity = "minor"
        
        mock_repository.get_by_id.return_value = mock_failure
        
        # Register an alternative
        failure_service.register_alternative(
            failure_id=1,
            selector=".match-title-v2",
            strategy=StrategyType.CSS,
        )
        
        result = failure_service.get_failure_detail(failure_id=1)
        
        assert result is not None
        assert result["failure_id"] == 1
        assert result["selector_id"] == ".match-title"
        assert result["sport"] == "basketball"
        assert len(result["alternatives"]) == 1
        assert result["alternatives"][0]["selector"] == ".match-title-v2"
    
    def test_list_failures(self, failure_service, mock_repository):
        """Test listing failures with filters."""
        # Setup mock failures
        mock_failure_1 = MagicMock()
        mock_failure_1.id = 1
        mock_failure_1.selector_id = ".match-title"
        mock_failure_1.sport = "basketball"
        mock_failure_1.site = "flashscore"
        mock_failure_1.timestamp = datetime.now(timezone.utc)
        mock_failure_1.error_type = "empty_result"
        mock_failure_1.severity = "minor"
        
        mock_failure_2 = MagicMock()
        mock_failure_2.id = 2
        mock_failure_2.selector_id = ".odds-container"
        mock_failure_2.sport = "football"
        mock_failure_2.site = "flashscore"
        mock_failure_2.timestamp = datetime.now(timezone.utc)
        mock_failure_2.error_type = "exception"
        mock_failure_2.severity = "moderate"
        
        mock_repository.find_with_filters.return_value = [mock_failure_1, mock_failure_2]
        
        results, total = failure_service.list_failures(
            sport="basketball",
            page=1,
            page_size=20,
        )
        
        assert len(results) == 2
        assert results[0]["failure_id"] == 1
        assert results[0]["sport"] == "basketball"
    
    def test_approve_alternative_success(self, failure_service):
        """Test approving an alternative selector."""
        failure_id = 1
        
        # Register an alternative first
        failure_service.register_alternative(
            failure_id=failure_id,
            selector=".match-title-v2",
            strategy=StrategyType.CSS,
        )
        
        result = failure_service.approve_alternative(
            failure_id=failure_id,
            selector=".match-title-v2",
            notes="Looks good",
        )
        
        assert result["success"] is True
        assert "approved" in result["message"].lower()
    
    def test_approve_alternative_not_found(self, failure_service):
        """Test approving non-existent alternative."""
        result = failure_service.approve_alternative(
            failure_id=1,
            selector=".non-existent",
        )
        
        assert result["success"] is False
        assert "no alternative" in result["message"].lower()
    
    def test_reject_alternative_success(self, failure_service):
        """Test rejecting an alternative selector."""
        failure_id = 1
        
        # Register an alternative first
        failure_service.register_alternative(
            failure_id=failure_id,
            selector=".match-title-v2",
            strategy=StrategyType.CSS,
        )
        
        result = failure_service.reject_alternative(
            failure_id=failure_id,
            selector=".match-title-v2",
            reason="Too fragile",
        )
        
        assert result["success"] is True
        assert "rejected" in result["message"].lower()
    
    def test_reject_alternative_not_found(self, failure_service):
        """Test rejecting non-existent alternative."""
        result = failure_service.reject_alternative(
            failure_id=1,
            selector=".non-existent",
            reason="Bad selector",
        )
        
        assert result["success"] is False
        assert "no alternative" in result["message"].lower()


class TestFailureServiceIntegration:
    """Integration tests for FailureService with real components."""
    
    def test_confidence_score_calculation(self):
        """Test that confidence scores are calculated correctly."""
        from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
        from src.selectors.adaptive.services.dom_analyzer import AlternativeSelector, StrategyType
        
        scorer = ConfidenceScorer()
        
        # Test CSS selector - should have higher specificity
        selector = AlternativeSelector(
            selector_string="#match-title",
            strategy_type=StrategyType.CSS,
            confidence_score=0.5,
            element_description="Match title element",
        )
        
        result = scorer.calculate_confidence(selector)
        
        assert result.confidence_score > 0
        assert result.confidence_score <= 1.0
    
    def test_blast_radius_severity_calculation(self):
        """Test blast radius severity calculation."""
        from src.selectors.adaptive.services.blast_radius import BlastRadiusCalculator, SeverityLevel
        
        calculator = BlastRadiusCalculator()
        
        # Test low severity
        severity = calculator._calculate_severity(affected_count=1, sport_count=1)
        assert severity == SeverityLevel.LOW
        
        # Test medium severity
        severity = calculator._calculate_severity(affected_count=4, sport_count=2)
        assert severity == SeverityLevel.MEDIUM
        
        # Test high severity
        severity = calculator._calculate_severity(affected_count=7, sport_count=3)
        assert severity == SeverityLevel.HIGH
        
        # Test critical severity
        severity = calculator._calculate_severity(affected_count=12, sport_count=5)
        assert severity == SeverityLevel.CRITICAL


class TestFailureEventModel:
    """Tests for FailureEvent model."""
    
    def test_to_dict(self):
        """Test FailureEvent serialization."""
        from src.selectors.adaptive.db.models.failure_event import FailureEvent
        
        event = FailureEvent(
            selector_id="test-selector",
            error_type="exception",
            timestamp=datetime.now(timezone.utc),
            sport="basketball",
            site="flashscore",
            failure_reason="Test error",
            severity="minor",
        )
        
        result = event.to_dict()
        
        assert result["selector_id"] == "test-selector"
        assert result["sport"] == "basketball"
        assert result["severity"] == "minor"
        assert "timestamp" in result
    
    def test_from_dict(self):
        """Test FailureEvent deserialization."""
        from src.selectors.adaptive.db.models.failure_event import FailureEvent
        
        data = {
            "selector_id": "test-selector",
            "error_type": "timeout",
            "timestamp": "2024-01-01T12:00:00",
            "sport": "football",
        }
        
        event = FailureEvent.from_dict(data)
        
        assert event.selector_id == "test-selector"
        assert event.error_type == "timeout"
        assert event.sport == "football"


# Run with: pytest tests/selectors/adaptive/test_failure_service.py -v
