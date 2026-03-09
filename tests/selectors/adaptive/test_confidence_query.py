"""
Unit tests for Confidence Query Service.

Tests the confidence score query API service for:
- Single selector query
- Batch selector query
- Paginated query
- Default score handling

Story: 6.1 - Confidence Score Query API
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.selectors.adaptive.services.confidence_query_service import (
    ConfidenceQueryService,
    ConfidenceScoreResult,
    BatchConfidenceResult,
    PaginatedConfidenceResult,
    ConfidenceQueryConfig,
    get_confidence_query_service,
)
from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository


# Mock FailureEvent for testing
class MockFailureEvent:
    """Mock FailureEvent for testing."""

    def __init__(self, selector_id: str, error_type: str = "exception", timestamp: datetime = None):
        self.selector_id = selector_id
        self.error_type = error_type
        self.timestamp = timestamp or datetime.utcnow()
        self.recipe_id = "test_recipe"
        self.sport = "football"
        self.site = "flashscore"


class TestConfidenceQueryService:
    """Test cases for ConfidenceQueryService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock failure event repository."""
        return Mock(spec=FailureEventRepository)

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = ConfidenceQueryConfig()
        config.default_confidence_score = 0.5
        config.default_page_size = 10
        config.max_page_size = 100
        config.cache_ttl = 30
        return config

    @pytest.fixture
    def service(self, mock_repository, config):
        """Create a confidence query service with mocks."""
        return ConfidenceQueryService(
            failure_repository=mock_repository,
            config=config,
        )

    def test_query_single_selector_with_history(self, service, mock_repository):
        """Test single selector query with failure history."""
        # Arrange
        selector_id = "test_selector"
        mock_events = [
            MockFailureEvent(selector_id, error_type="exception"),
            MockFailureEvent(selector_id, error_type=""),  # Success (no error)
            MockFailureEvent(selector_id, error_type="exception"),
        ]
        mock_repository.get_by_selector.return_value = mock_events

        # Act
        result = service.query_single(selector_id)

        # Assert
        assert result.selector_id == selector_id
        assert 0.0 <= result.confidence_score <= 1.0
        assert isinstance(result.last_updated, datetime)
        assert result.is_estimated is False
        mock_repository.get_by_selector.assert_called_once_with(selector_id, limit=100)

    def test_query_single_selector_no_history(self, service, mock_repository):
        """Test single selector query with no history returns default."""
        # Arrange
        selector_id = "unknown_selector"
        mock_repository.get_by_selector.return_value = []

        # Act
        result = service.query_single(selector_id)

        # Assert
        assert result.selector_id == selector_id
        assert result.confidence_score == 0.5  # Default score
        assert result.is_estimated is True

    def test_query_batch_selectors(self, service, mock_repository):
        """Test batch selector query."""
        # Arrange
        selector_ids = ["selector_1", "selector_2"]

        def mock_get_by_selector(selector_id, limit=None):
            if selector_id == "selector_1":
                return [
                    MockFailureEvent(selector_id, error_type=""),
                    MockFailureEvent(selector_id, error_type=""),
                ]  # 100% success
            elif selector_id == "selector_2":
                return [
                    MockFailureEvent(selector_id, error_type="exception"),
                ]  # 0% success
            else:
                return []  # Unknown

        mock_repository.get_by_selector.side_effect = mock_get_by_selector

        # Act
        result = service.query_batch(selector_ids)

        # Assert
        assert len(result.results) == 2
        assert result.results["selector_1"].confidence_score > result.results["selector_2"].confidence_score

    def test_query_all_paginated(self, service, mock_repository):
        """Test paginated query of all selectors."""
        # Arrange
        mock_selectors = ["selector_1", "selector_2", "selector_3", "selector_4", "selector_5"]
        mock_repository.get_unique_selectors.return_value = mock_selectors

        def mock_get_by_selector(selector_id, limit=None):
            return [MockFailureEvent(selector_id, error_type="")]

        mock_repository.get_by_selector.side_effect = mock_get_by_selector

        # Act
        result = service.query_all_paginated(page=1, page_size=2)

        # Assert
        assert len(result.results) == 2
        assert result.total == 5
        assert result.page == 1
        assert result.page_size == 2
        assert result.total_pages == 3  # ceil(5/2)

    def test_cache_functionality(self, service, mock_repository):
        """Test that caching works correctly."""
        # Arrange
        selector_id = "cached_selector"
        mock_repository.get_by_selector.return_value = [
            MockFailureEvent(selector_id, error_type="")
        ]

        # First call - should hit repository
        result1 = service.query_single(selector_id)

        # Second call - should hit cache
        result2 = service.query_single(selector_id)

        # Assert
        assert mock_repository.get_by_selector.call_count == 1  # Only called once

    def test_clear_cache(self, service, mock_repository):
        """Test cache clearing."""
        # Arrange
        selector_id = "test_selector"
        mock_repository.get_by_selector.return_value = [
            MockFailureEvent(selector_id, error_type="")
        ]

        # First call to populate cache
        service.query_single(selector_id)

        # Act
        service.clear_cache()

        # Second call - should hit repository again
        service.query_single(selector_id)

        # Assert
        assert mock_repository.get_by_selector.call_count == 2


class TestConfidenceScoreResult:
    """Test cases for ConfidenceScoreResult dataclass."""

    def test_create_result(self):
        """Test creating a confidence score result."""
        result = ConfidenceScoreResult(
            selector_id="test_selector",
            confidence_score=0.8,
            last_updated=datetime.utcnow(),
            is_estimated=False,
        )

        assert result.selector_id == "test_selector"
        assert result.confidence_score == 0.8
        assert result.is_estimated is False


class TestConfidenceQueryConfig:
    """Test cases for ConfidenceQueryConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ConfidenceQueryConfig()

        assert config.default_confidence_score == 0.5
        assert config.default_page_size == 50
        assert config.max_page_size == 100
        assert config.cache_ttl == 30

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ConfidenceQueryConfig()
        config.default_confidence_score = 0.7
        config.default_page_size = 25
        config.max_page_size = 50
        config.cache_ttl = 60

        assert config.default_confidence_score == 0.7
        assert config.default_page_size == 25
        assert config.max_page_size == 50
        assert config.cache_ttl == 60


class TestGetConfidenceQueryService:
    """Test cases for get_confidence_query_service singleton."""

    def test_returns_singleton(self):
        """Test that get_confidence_query_service returns the same instance."""
        service1 = get_confidence_query_service()
        service2 = get_confidence_query_service()

        assert service1 is service2


# Integration-style tests with real repository
class TestWithRealRepository:
    """Tests using an in-memory repository for integration testing."""

    def test_real_repository_single_query(self):
        """Test with real in-memory repository."""
        # Arrange
        repository = FailureEventRepository(db_path=":memory:")
        service = ConfidenceQueryService(failure_repository=repository)

        # Act - query without any data
        result = service.query_single("unknown")

        # Assert
        assert result.is_estimated is True
        assert result.confidence_score == 0.5

    def test_real_repository_with_data(self):
        """Test with populated in-memory repository."""
        # Arrange
        repository = FailureEventRepository(db_path=":memory:")

        # Add some test events
        repository.create(
            selector_id="test_selector",
            error_type="exception",
            failure_reason="Test failure",
        )
        repository.create(
            selector_id="test_selector",
            error_type="",  # Success
            failure_reason=None,
        )

        service = ConfidenceQueryService(failure_repository=repository)

        # Act
        result = service.query_single("test_selector")

        # Assert
        assert result.selector_id == "test_selector"
        assert result.is_estimated is False
        # 1 success out of 2 = 0.5
        assert result.confidence_score == 0.5


# API schema tests - import directly for testing
class TestConfidenceScoreResponse:
    """Test cases for API response schemas."""

    def test_response_model(self):
        """Test response model creation."""
        from src.selectors.adaptive.api.schemas.confidence import ConfidenceScoreResponse

        response = ConfidenceScoreResponse(
            selector_id="test",
            confidence_score=0.75,
            last_updated=datetime.utcnow(),
            is_estimated=False,
        )

        assert response.selector_id == "test"
        assert response.confidence_score == 0.75
        assert response.is_estimated is False

    def test_batch_response_model(self):
        """Test batch response model."""
        from src.selectors.adaptive.api.schemas.confidence import BatchConfidenceQuery

        query = BatchConfidenceQuery(selector_ids=["a", "b", "c"])
        assert len(query.selector_ids) == 3
