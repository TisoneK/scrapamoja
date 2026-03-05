"""
Unit tests for FailureDetectorService.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from src.selectors.adaptive.services.failure_detector import FailureDetectorService
from src.selectors.adaptive.db.models.failure_event import ErrorType


class TestFailureDetectorService:
    """Tests for FailureDetectorService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock failure event repository."""
        repo = MagicMock()
        # Mock create to return a mock event
        mock_event = MagicMock()
        mock_event.id = 1
        mock_event.selector_id = "test-selector"
        repo.create.return_value = mock_event
        return repo
    
    @pytest.fixture
    def mock_stability_service(self):
        """Create a mock stability scoring service."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_repository):
        """Create a FailureDetectorService instance."""
        return FailureDetectorService(failure_repository=mock_repository)
    
    @pytest.fixture
    def service_with_stability(self, mock_repository, mock_stability_service):
        """Create a FailureDetectorService with stability service."""
        return FailureDetectorService(
            failure_repository=mock_repository,
            stability_service=mock_stability_service,
        )
    
    def test_initialization(self, service, mock_repository):
        """Test service initialization with default values."""
        assert service.repository is mock_repository
        assert service.stability_service is None
        assert service.timeout_threshold == 30.0
    
    def test_initialization_custom_params(self, mock_repository):
        """Test service initialization with custom parameters."""
        service = FailureDetectorService(
            failure_repository=mock_repository,
            timeout_threshold=60.0,
        )
        assert service.timeout_threshold == 60.0
    
    def test_initialization_with_sla_enforcement(self, mock_repository):
        """Test service initialization with SLA enforcement."""
        service = FailureDetectorService(
            failure_repository=mock_repository,
            enforce_sla=True,
        )
        assert service.enforce_sla is True
        assert service.SLA_THRESHOLD_SECONDS == 1.0
    
    def test_initialization_sla_disabled(self, mock_repository):
        """Test service initialization with SLA disabled."""
        service = FailureDetectorService(
            failure_repository=mock_repository,
            enforce_sla=False,
        )
        assert service.enforce_sla is False
        
        # Test default SLA stats
        stats = service.get_sla_stats()
        assert stats['total_processed'] == 0
        assert stats['sla_violations'] == 0
        assert stats['compliance_rate'] == 100.0
    
    # Tests for sport/site parameters
    @pytest.mark.asyncio
    async def test_on_selector_failed_with_sport_and_site(self, service, mock_repository):
        """Test that on_selector_failed includes sport and site in the event."""
        await service.on_selector_failed(
            selector_name="test-selector",
            strategy="css",
            failure_reason="Test error",
            resolution_time=5.0,
            recipe_id="recipe-1",
            sport="football",
            site="flashscore.com",
        )
        
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["sport"] == "football"
        assert call_kwargs["site"] == "flashscore.com"
        assert call_kwargs["recipe_id"] == "recipe-1"
    
    # Tests for SLA verification
    @pytest.mark.asyncio
    async def test_sla_tracking_enabled_by_default(self, service):
        """Test that SLA tracking is enabled by default."""
        assert service.enforce_sla is True
        assert hasattr(service, '_sla_violations')
        assert hasattr(service, '_total_processed')
    
    @pytest.mark.asyncio
    async def test_sla_stats_initialization(self, service):
        """Test SLA stats are initialized correctly."""
        stats = service.get_sla_stats()
        assert stats['total_processed'] == 0
        assert stats['sla_violations'] == 0
        assert stats['compliance_rate'] == 100.0
        assert stats['sla_threshold_seconds'] == 1.0
    
    # Tests for classify_error_type
    def test_classify_timeout_by_time(self, service):
        """Test that timeout is classified when resolution time exceeds threshold."""
        error_type = service.classify_error_type("some error", "css", 35.0)
        assert error_type == ErrorType.TIMEOUT
    
    def test_classify_empty_result(self, service):
        """Test classification of empty result errors."""
        error_type = service.classify_error_type("No elements found", "css", 5.0)
        assert error_type == ErrorType.EMPTY_RESULT
        
        error_type = service.classify_error_type("Empty result", "xpath", 5.0)
        assert error_type == ErrorType.EMPTY_RESULT
    
    def test_classify_validation_error(self, service):
        """Test classification of validation errors."""
        error_type = service.classify_error_type("Validation failed", "css", 5.0)
        assert error_type == ErrorType.VALIDATION
        
        error_type = service.classify_error_type("Invalid selector", "css", 5.0)
        assert error_type == ErrorType.VALIDATION
    
    def test_classify_exception(self, service):
        """Test classification of exception errors."""
        error_type = service.classify_error_type("Exception occurred", "css", 5.0)
        assert error_type == ErrorType.EXCEPTION
    
    def test_classify_not_found(self, service):
        """Test classification of not found errors."""
        error_type = service.classify_error_type("Element not found", "css", 5.0)
        assert error_type == ErrorType.EMPTY_RESULT
        
        error_type = service.classify_error_type("Could not resolve", "xpath", 5.0)
        assert error_type == ErrorType.EMPTY_RESULT
    
    # Tests for determine_severity
    def test_determine_severity_empty_result_is_minor(self, service):
        """Test that empty_result defaults to minor severity."""
        severity = service.determine_severity(ErrorType.EMPTY_RESULT, 5.0)
        assert severity == "minor"
    
    def test_determine_severity_exception_is_moderate(self, service):
        """Test that exception defaults to moderate severity."""
        severity = service.determine_severity(ErrorType.EXCEPTION, 5.0)
        assert severity == "moderate"
    
    def test_determine_severity_timeout_time_based(self, service):
        """Test that timeout severity depends on resolution time."""
        # Below threshold
        severity = service.determine_severity(ErrorType.TIMEOUT, 30.0)
        assert severity == "moderate"
        
        # Above critical threshold
        severity = service.determine_severity(ErrorType.TIMEOUT, 120.0)
        assert severity == "critical"
    
    def test_determine_severity_very_slow_is_critical(self, service):
        """Test that very slow resolutions are marked critical."""
        severity = service.determine_severity(ErrorType.EXCEPTION, 150.0)
        assert severity == "critical"
    
    # Tests for on_selector_failed
    @pytest.mark.asyncio
    async def test_on_selector_failed_creates_event(self, service, mock_repository):
        """Test that on_selector_failed creates a failure event."""
        event = await service.on_selector_failed(
            selector_name="test-selector",
            strategy="css",
            failure_reason="Test error",
            resolution_time=5.0,
        )
        
        mock_repository.create.assert_called_once()
        assert event is not None
    
    @pytest.mark.asyncio
    async def test_on_selector_failed_with_context(self, service, mock_repository):
        """Test that on_selector_failed includes context."""
        await service.on_selector_failed(
            selector_name="test-selector",
            strategy="css",
            failure_reason="Test error",
            resolution_time=5.0,
            recipe_id="recipe-1",
            sport="football",
            site="example.com",
            correlation_id="corr-123",
        )
        
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["selector_id"] == "test-selector"
        assert call_kwargs["recipe_id"] == "recipe-1"
        assert call_kwargs["sport"] == "football"
        assert call_kwargs["site"] == "example.com"
        assert call_kwargs["correlation_id"] == "corr-123"
    
    @pytest.mark.asyncio
    async def test_on_selector_failed_triggers_stability(self, service_with_stability, mock_stability_service):
        """Test that on_selector_failed triggers stability scoring."""
        await service_with_stability.on_selector_failed(
            selector_name="test-selector",
            strategy="css",
            failure_reason="Test error",
            resolution_time=5.0,
            recipe_id="recipe-1",
        )
        
        mock_stability_service.on_selector_failure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_selector_failed_no_stability_update_without_recipe(self, service_with_stability, mock_stability_service):
        """Test that stability is not updated without recipe_id."""
        await service_with_stability.on_selector_failed(
            selector_name="test-selector",
            strategy="css",
            failure_reason="Test error",
            resolution_time=5.0,
            recipe_id=None,
        )
        
        mock_stability_service.on_selector_failure.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_selector_failed_no_stability_without_service(self, service, mock_repository):
        """Test that stability is not updated without stability service."""
        # Service without stability service should not fail
        event = await service.on_selector_failed(
            selector_name="test-selector",
            strategy="css",
            failure_reason="Test error",
            resolution_time=5.0,
            recipe_id="recipe-1",
        )
        
        assert event is not None
    
    # Tests for get_failure_statistics
    def test_get_failure_statistics(self, service, mock_repository):
        """Test get_failure_statistics returns correct data."""
        # Mock repository to return some failures
        mock_failures = [
            MagicMock(selector_id="s1", error_type="exception", severity="moderate", recipe_id="r1"),
            MagicMock(selector_id="s1", error_type="timeout", severity="critical", recipe_id="r1"),
            MagicMock(selector_id="s2", error_type="empty_result", severity="minor", recipe_id=None),
        ]
        mock_repository.get_recent_failures.return_value = mock_failures
        
        stats = service.get_failure_statistics()
        
        assert stats["total_failures"] == 3
        assert "exception" in stats["error_type_distribution"]
        assert "timeout" in stats["error_type_distribution"]
        assert "empty_result" in stats["error_type_distribution"]
    
    def test_get_failure_statistics_with_filters(self, service, mock_repository):
        """Test get_failure_statistics with filters."""
        mock_failures = [
            MagicMock(selector_id="s1", error_type="exception", severity="moderate", recipe_id="r1"),
        ]
        mock_repository.get_recent_failures.return_value = mock_failures
        
        stats = service.get_failure_statistics(selector_id="s1", recipe_id="r1")
        
        # Verify filters are applied (the service filters after getting from repo)
        assert stats["total_failures"] == 1


class TestErrorTypeClassification:
    """Test error type classification edge cases."""
    
    @pytest.fixture
    def service(self):
        """Create service with mock repository."""
        mock_repo = MagicMock()
        return FailureDetectorService(failure_repository=mock_repo)
    
    def test_empty_reason_string(self, service):
        """Test classification with empty reason."""
        error_type = service.classify_error_type("", "css", 5.0)
        assert error_type == ErrorType.EXCEPTION
    
    def test_none_reason_string(self, service):
        """Test classification with None reason."""
        error_type = service.classify_error_type(None, "css", 5.0)
        assert error_type == ErrorType.EXCEPTION
    
    def test_case_insensitive_matching(self, service):
        """Test that matching is case insensitive."""
        error_type = service.classify_error_type("EXCEPTION OCCURRED", "css", 5.0)
        assert error_type == ErrorType.EXCEPTION
        
        # Timeout classification by reason needs high resolution time
        error_type = service.classify_error_type("TIMEOUT ERROR", "css", 35.0)
        assert error_type == ErrorType.TIMEOUT


class TestSeverityDetermination:
    """Test severity determination edge cases."""
    
    @pytest.fixture
    def service(self):
        """Create service with mock repository."""
        mock_repo = MagicMock()
        return FailureDetectorService(failure_repository=mock_repo)
    
    def test_unknown_error_type_defaults_to_minor(self, service):
        """Test that unknown error type defaults to minor."""
        severity = service.determine_severity("unknown_type", 5.0)
        assert severity == "minor"
    
    def test_zero_resolution_time(self, service):
        """Test severity with zero resolution time."""
        severity = service.determine_severity(ErrorType.EXCEPTION, 0.0)
        assert severity == "moderate"
