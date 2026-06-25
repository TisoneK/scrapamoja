"""
Unit tests for FailureEventRepository.
"""

import pytest
from datetime import datetime, timedelta

from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository


class TestFailureEventRepository:
    """Test suite for FailureEventRepository."""
    
    @pytest.fixture
    def repository(self):
        """Create in-memory repository for testing."""
        return FailureEventRepository(db_path=":memory:")
    
    def test_create_failure_event(self, repository):
        """Test creating a failure event."""
        event = repository.create(
            selector_id="test-selector",
            error_type="exception",
            failure_reason="Test error",
        )
        
        assert event.id is not None
        assert event.selector_id == "test-selector"
        assert event.error_type == "exception"
        assert event.failure_reason == "Test error"
    
    def test_create_failure_event_with_all_fields(self, repository):
        """Test creating a failure event with all fields."""
        event = repository.create(
            selector_id="test-selector",
            error_type="timeout",
            recipe_id="recipe-1",
            sport="football",
            site="example.com",
            failure_reason="Timeout",
            strategy_used="css",
            resolution_time=30000.0,
            severity="moderate",
            correlation_id="corr-123",
        )
        
        assert event.selector_id == "test-selector"
        assert event.error_type == "timeout"
        assert event.recipe_id == "recipe-1"
        assert event.sport == "football"
        assert event.site == "example.com"
        assert event.severity == "moderate"
    
    def test_get_by_id(self, repository):
        """Test retrieving a failure event by ID."""
        created_event = repository.create(
            selector_id="test-selector",
            error_type="exception",
        )
        
        retrieved_event = repository.get_by_id(created_event.id)
        
        assert retrieved_event is not None
        assert retrieved_event.id == created_event.id
        assert retrieved_event.selector_id == "test-selector"
    
    def test_get_by_id_not_found(self, repository):
        """Test retrieving non-existent event returns None."""
        result = repository.get_by_id(99999)
        assert result is None
    
    def test_get_by_selector(self, repository):
        """Test retrieving failure events by selector."""
        # Create multiple events
        repository.create(selector_id="selector-1", error_type="exception")
        repository.create(selector_id="selector-1", error_type="timeout")
        repository.create(selector_id="selector-2", error_type="empty_result")
        
        events = repository.get_by_selector("selector-1")
        
        assert len(events) == 2
        assert all(e.selector_id == "selector-1" for e in events)
    
    def test_get_by_recipe(self, repository):
        """Test retrieving failure events by recipe."""
        repository.create(selector_id="s1", error_type="exception", recipe_id="recipe-1")
        repository.create(selector_id="s2", error_type="timeout", recipe_id="recipe-1")
        repository.create(selector_id="s3", error_type="empty_result", recipe_id="recipe-2")
        
        events = repository.get_by_recipe("recipe-1")
        
        assert len(events) == 2
        assert all(e.recipe_id == "recipe-1" for e in events)
    
    def test_get_by_sport_site(self, repository):
        """Test retrieving failure events by sport and site."""
        repository.create(selector_id="s1", error_type="exception", sport="football", site="site1.com")
        repository.create(selector_id="s2", error_type="timeout", sport="football", site="site2.com")
        repository.create(selector_id="s3", error_type="empty_result", sport="basketball", site="site1.com")
        
        # Filter by sport
        events = repository.get_by_sport_site(sport="football")
        assert len(events) == 2
        
        # Filter by site
        events = repository.get_by_sport_site(site="site1.com")
        assert len(events) == 2
        
        # Filter by both
        events = repository.get_by_sport_site(sport="football", site="site1.com")
        assert len(events) == 1
    
    def test_get_by_date_range(self, repository):
        """Test retrieving failure events within date range."""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        # Create events with different timestamps
        event1 = repository.create(
            selector_id="s1", 
            error_type="exception",
            timestamp=yesterday
        )
        event2 = repository.create(
            selector_id="s2", 
            error_type="timeout",
            timestamp=now
        )
        
        # Query for events in range
        events = repository.get_by_date_range(
            start_time=yesterday - timedelta(hours=1),
            end_time=now + timedelta(hours=1)
        )
        
        assert len(events) == 2
    
    def test_count_by_selector(self, repository):
        """Test counting failure events for a selector."""
        repository.create(selector_id="selector-1", error_type="exception")
        repository.create(selector_id="selector-1", error_type="timeout")
        repository.create(selector_id="selector-2", error_type="empty_result")
        
        count = repository.count_by_selector("selector-1")
        assert count == 2
    
    def test_count_by_error_type(self, repository):
        """Test counting failure events by error type."""
        repository.create(selector_id="s1", error_type="exception")
        repository.create(selector_id="s2", error_type="exception")
        repository.create(selector_id="s3", error_type="timeout")
        
        exception_count = repository.count_by_error_type("exception")
        timeout_count = repository.count_by_error_type("timeout")
        
        assert exception_count == 2
        assert timeout_count == 1
    
    def test_get_recent_failures(self, repository):
        """Test retrieving recent failure events."""
        for i in range(15):
            repository.create(selector_id=f"selector-{i}", error_type="exception")
        
        recent = repository.get_recent_failures(limit=10)
        
        assert len(recent) == 10
    
    def test_get_recent_failures_with_filters(self, repository):
        """Test retrieving recent failure events with filters."""
        repository.create(selector_id="s1", error_type="exception", sport="football")
        repository.create(selector_id="s2", error_type="timeout", sport="basketball")
        repository.create(selector_id="s3", error_type="empty_result", sport="football")
        
        recent = repository.get_recent_failures(limit=10, sport="football")
        
        assert len(recent) == 2
        assert all(e.sport == "football" for e in recent)
    
    def test_delete_by_id(self, repository):
        """Test deleting a failure event by ID."""
        event = repository.create(selector_id="test-selector", error_type="exception")
        
        result = repository.delete_by_id(event.id)
        
        assert result is True
        assert repository.get_by_id(event.id) is None
    
    def test_delete_by_id_not_found(self, repository):
        """Test deleting non-existent event returns False."""
        result = repository.delete_by_id(99999)
        assert result is False
    
    def test_delete_old_events(self, repository):
        """Test deleting events older than specified date."""
        now = datetime.utcnow()
        old_date = now - timedelta(days=30)
        
        # Create old event
        repository.create(selector_id="old-selector", error_type="exception", timestamp=old_date)
        
        # Create recent event
        repository.create(selector_id="recent-selector", error_type="timeout", timestamp=now)
        
        # Delete old events
        deleted_count = repository.delete_old_events(before=now - timedelta(days=7))
        
        assert deleted_count == 1
        
        # Recent event should still exist
        recent = repository.get_recent_failures(limit=10)
        assert len(recent) == 1
        assert recent[0].selector_id == "recent-selector"


class TestFailureEventRepositoryFiltering:
    """Test suite for FailureEventRepository filtering and aggregation (Story 2.3)."""
    
    @pytest.fixture
    def repository(self):
        """Create in-memory repository for testing."""
        return FailureEventRepository(db_path=":memory:")
    
    @pytest.fixture
    def sample_data(self, repository):
        """Create sample data for filtering tests."""
        now = datetime.utcnow()
        
        # Create events with different sports, error types, and sites
        repository.create(
            selector_id="odds-selector",
            error_type="exception",
            sport="football",
            site="bet365.com",
            tab_type="odds",
            previous_strategy_used="css",
            confidence_score_at_failure=0.7,
            timestamp=now - timedelta(days=1),
        )
        repository.create(
            selector_id="results-selector",
            error_type="empty_result",
            sport="football",
            site="bet365.com",
            tab_type="results",
            previous_strategy_used="xpath",
            confidence_score_at_failure=0.5,
            timestamp=now - timedelta(days=2),
        )
        repository.create(
            selector_id="schedule-selector",
            error_type="timeout",
            sport="basketball",
            site="espn.com",
            tab_type="schedule",
            previous_strategy_used="css",
            confidence_score_at_failure=0.8,
            timestamp=now - timedelta(days=3),
        )
        repository.create(
            selector_id="tennis-odds",
            error_type="exception",
            sport="tennis",
            site="bet365.com",
            tab_type="odds",
            previous_strategy_used="xpath",
            confidence_score_at_failure=0.6,
            timestamp=now - timedelta(days=1),
        )
    
    def test_find_with_filters_by_sport(self, repository, sample_data):
        """Test filtering failures by sport."""
        events = repository.find_with_filters(sport="football")
        
        assert len(events) == 2
        assert all(e.sport == "football" for e in events)
    
    def test_find_with_filters_by_tab_type(self, repository, sample_data):
        """Test filtering failures by tab type."""
        events = repository.find_with_filters(tab_type="odds")
        
        assert len(events) == 2
        assert all(e.tab_type == "odds" for e in events)
    
    def test_find_with_filters_by_date_range(self, repository, sample_data):
        """Test filtering failures by date range."""
        now = datetime.utcnow()
        events = repository.find_with_filters(
            date_from=now - timedelta(days=1, hours=12),
            date_to=now,
        )
        
        assert len(events) == 2  # football and tennis from day 1
    
    def test_find_with_filters_by_error_type(self, repository, sample_data):
        """Test filtering failures by error type."""
        events = repository.find_with_filters(error_type="exception")
        
        assert len(events) == 2
        assert all(e.error_type == "exception" for e in events)
    
    def test_find_with_filters_combined(self, repository, sample_data):
        """Test filtering with multiple filters combined."""
        events = repository.find_with_filters(
            sport="football",
            site="bet365.com",
        )
        
        assert len(events) == 2
        assert all(e.sport == "football" for e in events)
        assert all(e.site == "bet365.com" for e in events)
    
    def test_aggregate_by_sport(self, repository, sample_data):
        """Test aggregating failures by sport."""
        result = repository.aggregate_by_sport()
        
        assert result["football"] == 2
        assert result["basketball"] == 1
        assert result["tennis"] == 1
    
    def test_aggregate_by_error_type(self, repository, sample_data):
        """Test aggregating failures by error type."""
        result = repository.aggregate_by_error_type()
        
        assert result["exception"] == 2
        assert result["empty_result"] == 1
        assert result["timeout"] == 1
    
    def test_aggregate_by_site(self, repository, sample_data):
        """Test aggregating failures by site."""
        result = repository.aggregate_by_site()
        
        assert result["bet365.com"] == 3
        assert result["espn.com"] == 1
    
    def test_create_with_context_fields(self, repository):
        """Test creating failure event with new context fields."""
        event = repository.create(
            selector_id="test-selector",
            error_type="exception",
            sport="football",
            site="example.com",
            previous_strategy_used="css",
            confidence_score_at_failure=0.75,
            tab_type="odds",
            page_state={"scroll_position": {"x": 0, "y": 100}},
        )
        
        assert event.previous_strategy_used == "css"
        assert event.confidence_score_at_failure == 0.75
        assert event.tab_type == "odds"
        assert event.page_state == {"scroll_position": {"x": 0, "y": 100}}
