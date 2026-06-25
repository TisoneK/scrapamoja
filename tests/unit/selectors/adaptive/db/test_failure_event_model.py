"""
Unit tests for FailureEvent SQLAlchemy model.
"""

import pytest
from datetime import datetime

from src.selectors.adaptive.db.models.recipe import Base
from src.selectors.adaptive.db.models.failure_event import FailureEvent, ErrorType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestFailureEventModel:
    """Test suite for FailureEvent model."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_create_failure_event_with_required_fields(self, session):
        """Test creating a failure event with required fields only."""
        event = FailureEvent(
            selector_id="test-selector",
            error_type="exception",
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        
        assert event.id is not None
        assert event.selector_id == "test-selector"
        assert event.error_type == "exception"
        assert event.timestamp is not None
        assert event.created_at is not None
    
    def test_create_failure_event_with_all_fields(self, session):
        """Test creating a failure event with all fields."""
        event = FailureEvent(
            selector_id="test-selector",
            error_type="timeout",
            recipe_id="recipe-1",
            sport="football",
            site="example.com",
            failure_reason="Timeout after 30 seconds",
            strategy_used="css",
            resolution_time=30000.0,
            severity="moderate",
            correlation_id="corr-123",
            # NEW: Context fields for Story 2.3
            previous_strategy_used="xpath",
            confidence_score_at_failure=0.75,
            tab_type="odds",
            page_state={"scroll_position": {"x": 0, "y": 100}},
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        
        assert event.selector_id == "test-selector"
        assert event.error_type == "timeout"
        assert event.recipe_id == "recipe-1"
        assert event.sport == "football"
        assert event.site == "example.com"
        assert event.failure_reason == "Timeout after 30 seconds"
        assert event.strategy_used == "css"
        assert event.resolution_time == 30000.0
        assert event.severity == "moderate"
        assert event.correlation_id == "corr-123"
        # New context fields
        assert event.previous_strategy_used == "xpath"
        assert event.confidence_score_at_failure == 0.75
        assert event.tab_type == "odds"
        assert event.page_state == {"scroll_position": {"x": 0, "y": 100}}
    
    def test_failure_event_to_dict(self, session):
        """Test converting failure event to dictionary."""
        event = FailureEvent(
            selector_id="test-selector",
            error_type="empty_result",
            recipe_id="recipe-1",
            sport="basketball",
            severity="minor",
            # New context fields
            previous_strategy_used="css",
            confidence_score_at_failure=0.65,
            tab_type="results",
            page_state={"viewport": {"width": 1920, "height": 1080}},
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        
        result = event.to_dict()
        
        assert result["selector_id"] == "test-selector"
        assert result["error_type"] == "empty_result"
        assert result["recipe_id"] == "recipe-1"
        assert result["sport"] == "basketball"
        assert result["severity"] == "minor"
        # New context fields
        assert result["previous_strategy_used"] == "css"
        assert result["confidence_score_at_failure"] == 0.65
        assert result["tab_type"] == "results"
        assert result["page_state"] == {"viewport": {"width": 1920, "height": 1080}}
        assert "id" in result
        assert "timestamp" in result
    
    def test_failure_event_from_dict(self):
        """Test creating failure event from dictionary."""
        data = {
            "selector_id": "test-selector",
            "error_type": "exception",
            "recipe_id": "recipe-2",
            "sport": "tennis",
            "site": "sports.com",
            "failure_reason": "Element not found",
            "strategy_used": "xpath",
            "resolution_time": 1500.0,
            "severity": "moderate",
            # New context fields
            "previous_strategy_used": "css",
            "confidence_score_at_failure": 0.8,
            "tab_type": "schedule",
            "page_state": {"url": "https://example.com"},
        }
        
        event = FailureEvent.from_dict(data)
        
        assert event.selector_id == "test-selector"
        assert event.error_type == "exception"
        assert event.recipe_id == "recipe-2"
        assert event.sport == "tennis"
        assert event.site == "sports.com"
        assert event.failure_reason == "Element not found"
        assert event.strategy_used == "xpath"
        assert event.resolution_time == 1500.0
        assert event.severity == "moderate"
        # New context fields
        assert event.previous_strategy_used == "css"
        assert event.confidence_score_at_failure == 0.8
        assert event.tab_type == "schedule"
        assert event.page_state == {"url": "https://example.com"}
    
    def test_failure_event_repr(self, session):
        """Test failure event string representation."""
        event = FailureEvent(
            selector_id="test-selector",
            error_type="validation",
        )
        session.add(event)
        session.commit()
        
        assert "test-selector" in repr(event)
        assert "validation" in repr(event)
    
    def test_optional_fields_default_to_none(self, session):
        """Test that optional fields default to None."""
        event = FailureEvent(
            selector_id="test-selector",
            error_type="exception",
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        
        assert event.recipe_id is None
        assert event.sport is None
        assert event.site is None
        assert event.failure_reason is None
        assert event.strategy_used is None
        assert event.resolution_time is None
        assert event.correlation_id is None
        # New context fields
        assert event.previous_strategy_used is None
        assert event.confidence_score_at_failure is None
        assert event.tab_type is None
        assert event.page_state is None
    
    def test_default_severity(self, session):
        """Test that default severity is minor."""
        event = FailureEvent(
            selector_id="test-selector",
            error_type="empty_result",
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        
        assert event.severity == "minor"


class TestErrorType:
    """Tests for ErrorType enum-like class."""
    
    def test_valid_error_types(self):
        """Test that valid error types are recognized."""
        assert ErrorType.is_valid("empty_result") is True
        assert ErrorType.is_valid("exception") is True
        assert ErrorType.is_valid("timeout") is True
        assert ErrorType.is_valid("validation") is True
    
    def test_invalid_error_types(self):
        """Test that invalid error types are rejected."""
        assert ErrorType.is_valid("invalid") is False
        assert ErrorType.is_valid("") is False
        assert ErrorType.is_valid("ERROR") is False
    
    def test_default_severity_for_error_types(self):
        """Test that each error type maps to correct default severity."""
        assert ErrorType.get_default_severity("empty_result") == "minor"
        assert ErrorType.get_default_severity("exception") == "moderate"
        assert ErrorType.get_default_severity("timeout") == "moderate"
        assert ErrorType.get_default_severity("validation") == "minor"
    
    def test_default_severity_for_unknown_type(self):
        """Test that unknown error type defaults to minor."""
        assert ErrorType.get_default_severity("unknown") == "minor"
