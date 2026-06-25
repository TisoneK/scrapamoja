"""
Tests for FailureContextService.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from src.selectors.adaptive.services.failure_context import FailureContextService
from src.selectors.adaptive.db.models.failure_event import FailureEvent
from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository


class TestFailureContextService:
    """Test suite for FailureContextService."""

    @pytest.fixture
    def repository(self):
        """Create a mock repository."""
        return Mock(spec=FailureEventRepository)

    @pytest.fixture
    def service(self, repository):
        """Create a FailureContextService with mock repository."""
        return FailureContextService(repository)

    def test_create_enriched_failure(self, service, repository):
        """Test creating a failure event with context."""
        # Setup mock
        mock_failure = FailureEvent(
            id=1,
            selector_id="test_selector",
            error_type="exception",
            sport="football",
            site="flashscore",
            previous_strategy_used="css_selector",
            confidence_score_at_failure=0.75,
            tab_type="odds",
            page_state={"url": "https://example.com"},
            timestamp=datetime.utcnow(),
        )
        repository.create.return_value = mock_failure

        # Execute
        result = service.create_enriched_failure(
            selector_id="test_selector",
            error_type="exception",
            sport="football",
            site="flashscore",
            previous_strategy_used="css_selector",
            confidence_score_at_failure=0.75,
            tab_type="odds",
            page_state={"url": "https://example.com"},
        )

        # Verify
        assert result is not None
        assert result.selector_id == "test_selector"
        assert result.sport == "football"
        assert result.previous_strategy_used == "css_selector"
        assert result.confidence_score_at_failure == 0.75
        assert result.tab_type == "odds"
        repository.create.assert_called_once()

    def test_enrich_existing_failure(self, service, repository):
        """Test enriching an existing failure with context."""
        # Setup mock
        mock_failure = FailureEvent(
            id=1,
            selector_id="test_selector",
            error_type="exception",
            timestamp=datetime.utcnow(),
        )
        repository.get_by_id.return_value = mock_failure

        # Mock session context
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        repository._get_session.return_value = mock_session

        # Execute
        result = service.enrich_existing_failure(
            failure_id=1,
            previous_strategy_used="xpath",
            confidence_score_at_failure=0.5,
            tab_type="results",
        )

        # Verify
        assert result is not None
        assert result.previous_strategy_used == "xpath"
        assert result.confidence_score_at_failure == 0.5
        assert result.tab_type == "results"

    def test_enrich_nonexistent_failure(self, service, repository):
        """Test enriching a failure that doesn't exist."""
        repository.get_by_id.return_value = None

        result = service.enrich_existing_failure(
            failure_id=999,
            previous_strategy_used="xpath",
        )

        assert result is None

    def test_capture_page_context(self, service):
        """Test capturing page context."""
        # Create mock page
        mock_page = Mock()
        mock_page.viewport_size = {"width": 1920, "height": 1080}
        mock_page.url = "https://example.com/football"

        # Mock evaluate to return scroll position
        mock_page.evaluate = Mock(side_effect=[
            {"x": 0, "y": 100, "documentHeight": 2000, "windowHeight": 1080},
            {"images": 50, "scripts": 10, "links": 100},
        ])

        result = service.capture_page_context(mock_page)

        assert "viewport" in result
        assert result["viewport"]["width"] == 1920
        assert result["viewport"]["height"] == 1080
        assert "scroll_position" in result
        assert result["scroll_position"]["y"] == 100
        assert "page_elements" in result

    def test_capture_page_context_graceful_failure(self, service):
        """Test page context capture handles errors gracefully."""
        mock_page = Mock()
        mock_page.viewport_size = None
        mock_page.url = "https://example.com"
        mock_page.evaluate = Mock(side_effect=Exception("Script error"))

        result = service.capture_page_context(mock_page)

        # Should still return context with capture_error
        assert "capture_error" in result or "url" in result

    def test_truncate_page_state(self, service):
        """Test page state truncation."""
        # Create a large page state
        large_state = {
            "url": "https://example.com",
            "viewport": {"width": 1920, "height": 1080},
            "scroll_position": {"x": 0, "y": 100},
            "page_elements": {"images": 50, "scripts": 10},
            "extra_data": "x" * 20000,  # Very large string
        }

        result = service._truncate_page_state(large_state)

        # Should be truncated to under MAX_PAGE_STATE_SIZE
        import json
        result_json = json.dumps(result)
        assert len(result_json) <= service.MAX_PAGE_STATE_SIZE
        # Should still have priority keys
        assert "url" in result

    def test_truncate_page_state_small(self, service):
        """Test page state truncation with small state."""
        small_state = {"url": "https://example.com", "data": "small"}

        result = service._truncate_page_state(small_state)

        # Should return unchanged
        assert result == small_state

    def test_get_context_summary(self, service, repository):
        """Test getting context summary."""
        mock_failure = FailureEvent(
            id=1,
            selector_id="test_selector",
            sport="football",
            site="flashscore",
            tab_type="odds",
            previous_strategy_used="css",
            confidence_score_at_failure=0.8,
            page_state={"url": "https://example.com"},
            timestamp=datetime.utcnow(),
        )
        repository.get_by_id.return_value = mock_failure

        result = service.get_context_summary(1)

        assert result is not None
        assert result["failure_id"] == 1
        assert result["selector_id"] == "test_selector"
        assert result["sport"] == "football"
        assert result["tab_type"] == "odds"
        assert result["previous_strategy"] == "css"
        assert result["confidence_score"] == 0.8
        assert result["has_page_state"] is True

    def test_get_context_summary_not_found(self, service, repository):
        """Test context summary for nonexistent failure."""
        repository.get_by_id.return_value = None

        result = service.get_context_summary(999)

        assert result is None
