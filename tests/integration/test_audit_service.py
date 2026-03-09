"""
Integration tests for Audit Service.

Tests the audit logging functionality for recording human decisions.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from src.selectors.adaptive.services.audit_service import AuditLogger, record_human_decision
from src.selectors.adaptive.db.models.audit_event import AuditEvent


@pytest.mark.integration
class TestAuditLogger:
    """Test suite for AuditLogger service."""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger with in-memory database for testing."""
        return AuditLogger(db_path=":memory:")
    
    @pytest.fixture
    def sample_context(self) -> Dict[str, Any]:
        """Sample context snapshot for testing."""
        return {
            "url": "https://example.com",
            "page_title": "Test Page",
            "selector_type": "css",
            "confidence_score": 0.85,
            "failure_reason": "element_not_found",
            "dom_snapshot": {
                "element_id": "test-button",
                "element_class": "btn btn-primary",
                "element_text": "Submit"
            }
        }
    
    def test_record_approval_decision(self, audit_logger, sample_context):
        """Test recording an approval decision."""
        # Record approval
        audit_event = audit_logger.record_approval(
            selector="#submit-button",
            user_id="test_user",
            selector_id="css_submit_button_001",
            context_snapshot=sample_context,
            confidence_at_time=0.85,
            notes="Approved based on visual confirmation"
        )
        
        # Verify audit event was created
        assert audit_event is not None
        assert audit_event.id is not None
        assert audit_event.action_type == "selector_approved"
        assert audit_event.selector == "#submit-button"
        assert audit_event.user_id == "test_user"
        assert audit_event.selector_id == "css_submit_button_001"
        assert audit_event.context_snapshot == sample_context
        assert audit_event.confidence_at_time == 0.85
        assert audit_event.after_state == "#submit-button"
        assert audit_event.notes == "Approved based on visual confirmation"
        assert audit_event.timestamp is not None
    
    def test_record_rejection_decision(self, audit_logger, sample_context):
        """Test recording a rejection decision."""
        # Record rejection
        audit_event = audit_logger.record_rejection(
            selector=".wrong-selector",
            user_id="test_user",
            reason="Element not found on page",
            selector_id="css_wrong_selector_001",
            context_snapshot=sample_context,
            confidence_at_time=0.32,
            suggested_alternative=".correct-selector",
            notes="User suggested alternative based on inspection"
        )
        
        # Verify audit event was created
        assert audit_event is not None
        assert audit_event.action_type == "selector_rejected"
        assert audit_event.selector == ".wrong-selector"
        assert audit_event.user_id == "test_user"
        assert audit_event.reason == "Element not found on page"
        assert audit_event.before_state == ".wrong-selector"
        assert audit_event.suggested_alternative == ".correct-selector"
        assert audit_event.confidence_at_time == 0.32
    
    def test_record_flagging_decision(self, audit_logger, sample_context):
        """Test recording a flagging decision."""
        # Record flagging
        audit_event = audit_logger.record_flagging(
            selector="#ambiguous-element",
            user_id="test_user",
            selector_id="css_ambiguous_element_001",
            context_snapshot=sample_context,
            confidence_at_time=0.45,
            notes="Flagged for developer review due to ambiguity"
        )
        
        # Verify audit event was created
        assert audit_event is not None
        assert audit_event.action_type == "selector_flagged"
        assert audit_event.selector == "#ambiguous-element"
        assert audit_event.user_id == "test_user"
        assert audit_event.confidence_at_time == 0.45
    
    def test_record_custom_selector_creation(self, audit_logger, sample_context):
        """Test recording custom selector creation."""
        # Record custom selector creation
        audit_event = audit_logger.record_custom_selector_creation(
            selector="div[data-testid='custom-button']",
            user_id="test_user",
            selector_id="custom_data_testid_001",
            context_snapshot=sample_context,
            confidence_at_time=0.92,
            notes="Created custom selector using data-testid"
        )
        
        # Verify audit event was created
        assert audit_event is not None
        assert audit_event.action_type == "custom_selector_created"
        assert audit_event.selector == "div[data-testid='custom-button']"
        assert audit_event.user_id == "test_user"
        assert audit_event.after_state == "div[data-testid='custom-button']"
        assert audit_event.confidence_at_time == 0.92
    
    def test_record_decision_with_failure_id(self, audit_logger, sample_context):
        """Test recording decision associated with failure event."""
        # Record decision with failure context
        audit_event = audit_logger.record_decision(
            action_type="selector_approved",
            selector="#fixed-selector",
            user_id="test_user",
            failure_id=123,
            context_snapshot=sample_context,
            before_state="#broken-selector",
            after_state="#fixed-selector"
        )
        
        # Verify audit event was created with failure context
        assert audit_event is not None
        assert audit_event.failure_id == 123
        assert audit_event.before_state == "#broken-selector"
        assert audit_event.after_state == "#fixed-selector"
    
    def test_invalid_action_type_raises_error(self, audit_logger):
        """Test that invalid action types raise ValueError."""
        with pytest.raises(ValueError, match="Invalid action_type"):
            audit_logger.record_decision(
                action_type="invalid_action",
                selector="#test",
                user_id="test_user"
            )
    
    def test_get_decision_history_by_user(self, audit_logger, sample_context):
        """Test getting decision history for a specific user."""
        # Record multiple decisions for different users
        audit_logger.record_approval(
            selector="#selector1",
            user_id="user1",
            context_snapshot=sample_context
        )
        audit_logger.record_rejection(
            selector="#selector2",
            user_id="user1",
            reason="Test rejection",
            context_snapshot=sample_context
        )
        audit_logger.record_approval(
            selector="#selector3",
            user_id="user2",
            context_snapshot=sample_context
        )
        
        # Get history for user1
        user1_history = audit_logger.get_decision_history(user_id="user1")
        
        # Verify only user1 decisions are returned
        assert len(user1_history) == 2
        for event in user1_history:
            assert event.user_id == "user1"
    
    def test_get_decision_history_by_action_type(self, audit_logger, sample_context):
        """Test getting decision history filtered by action type."""
        # Record different types of decisions
        audit_logger.record_approval(
            selector="#selector1",
            user_id="user1",
            context_snapshot=sample_context
        )
        audit_logger.record_rejection(
            selector="#selector2",
            user_id="user1",
            reason="Test rejection",
            context_snapshot=sample_context
        )
        audit_logger.record_approval(
            selector="#selector3",
            user_id="user2",
            context_snapshot=sample_context
        )
        
        # Get history for approvals only
        approval_history = audit_logger.get_decision_history(action_type="selector_approved")
        
        # Verify only approvals are returned
        assert len(approval_history) == 2
        for event in approval_history:
            assert event.action_type == "selector_approved"
    
    def test_get_audit_statistics(self, audit_logger, sample_context):
        """Test getting audit statistics."""
        # Record various decisions
        audit_logger.record_approval(
            selector="#selector1",
            user_id="user1",
            context_snapshot=sample_context,
            confidence_at_time=0.8
        )
        audit_logger.record_rejection(
            selector="#selector2",
            user_id="user1",
            reason="Test rejection",
            context_snapshot=sample_context
        )
        audit_logger.record_flagging(
            selector="#selector3",
            user_id="user2",
            context_snapshot=sample_context
        )
        
        # Get statistics
        stats = audit_logger.get_audit_statistics()
        
        # Verify statistics
        assert stats["total_events"] == 3
        assert stats["action_counts"]["selector_approved"] == 1
        assert stats["action_counts"]["selector_rejected"] == 1
        assert stats["action_counts"]["selector_flagged"] == 1
        assert stats["average_approval_confidence"] == 0.8
    
    def test_to_dict_conversion(self, audit_logger, sample_context):
        """Test conversion of audit event to dictionary."""
        # Record decision
        audit_event = audit_logger.record_approval(
            selector="#test-selector",
            user_id="test_user",
            selector_id="test_001",
            context_snapshot=sample_context,
            confidence_at_time=0.75
        )
        
        # Convert to dictionary
        event_dict = audit_event.to_dict()
        
        # Verify dictionary structure
        assert isinstance(event_dict, dict)
        assert event_dict["id"] == audit_event.id
        assert event_dict["action_type"] == "selector_approved"
        assert event_dict["selector"] == "#test-selector"
        assert event_dict["user_id"] == "test_user"
        assert event_dict["selector_id"] == "test_001"
        assert event_dict["context_snapshot"] == sample_context
        assert event_dict["confidence_at_time"] == 0.75
        assert "timestamp" in event_dict
        assert "created_at" in event_dict


@pytest.mark.integration
class TestConvenienceFunctions:
    """Test convenience functions for audit logging."""
    
    def test_record_human_decision_function(self):
        """Test the convenience record_human_decision function."""
        # This would test the global function, but for isolation in tests,
        # we'll verify it exists and can be called
        assert callable(record_human_decision)
        
        # Note: Testing the global function would require mocking the global
        # audit logger instance, which is better done in unit tests


@pytest.mark.integration
class TestAuditServicePerformance:
    """Performance tests for audit service."""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger with in-memory database for testing."""
        return AuditLogger(db_path=":memory:")
    
    def test_high_volume_logging_performance(self, audit_logger):
        """Test that audit logging can handle high volume without blocking."""
        import time
        
        # Record multiple decisions and measure time
        start_time = time.time()
        
        for i in range(100):
            audit_logger.record_approval(
                selector=f"#selector-{i}",
                user_id="test_user",
                notes=f"Batch approval {i}"
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 records in reasonable time (less than 5 seconds)
        assert duration < 5.0, f"High volume logging took too long: {duration}s"
        
        # Verify all records were created
        stats = audit_logger.get_audit_statistics()
        assert stats["total_events"] == 100
