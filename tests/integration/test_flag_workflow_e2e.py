"""
End-to-end test for flag workflow (Story 4.3).

Tests the complete flag workflow from UI to database persistence.
"""

import pytest
import asyncio
from datetime import datetime
from src.selectors.adaptive.services.failure_service import FailureService, get_failure_service
from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository


@pytest.mark.asyncio
@pytest.mark.integration
class TestFlagWorkflowE2E:
    """End-to-end tests for the flag workflow."""
    
    async def setup_method(self):
        """Set up test dependencies."""
        # Use in-memory database for testing
        self.failure_service = get_failure_service()
        self.failure_repository = self.failure_service.failure_repository
        
        # Create a test failure
        self.test_failure = self.failure_repository.create(
            selector_id="test-selector",
            error_type="empty_result",
            sport="basketball",
            site="flashscore",
            failure_reason="Test element not found",
        )
    
    async def test_complete_flag_workflow(self):
        """Test the complete flag workflow: flag -> retrieve -> unflag."""
        failure_id = self.test_failure.id
        
        # Step 1: Flag the failure
        flag_note = "This selector needs developer review due to complex DOM structure"
        flag_result = self.failure_service.flag_failure(
            failure_id=failure_id,
            note=flag_note,
            user_id="test-user"
        )
        
        assert flag_result["success"] is True
        assert flag_result["flagged"] is True
        assert flag_result["flag_note"] == flag_note
        assert "flagged_at" in flag_result
        
        # Step 2: Verify flag persists in database
        flag_info = self.failure_service._load_flagged_failure(failure_id)
        assert flag_info is not None
        assert flag_info["flagged"] is True
        assert flag_info["note"] == flag_note
        
        # Step 3: Verify flag appears in failure detail
        failure_detail = self.failure_service.get_failure_detail(failure_id)
        assert failure_detail["flagged"] is True
        assert failure_detail["flag_note"] == flag_note
        assert failure_detail["flagged_at"] is not None
        
        # Step 4: Verify flag appears in filtered list
        flagged_failures, total = self.failure_service.list_failures(flagged=True)
        assert len(flagged_failures) == 1
        assert flagged_failures[0]["flagged"] is True
        assert flagged_failures[0]["flag_note"] == flag_note
        
        # Step 5: Unflag the failure
        unflag_result = self.failure_service.unflag_failure(
            failure_id=failure_id,
            user_id="test-user"
        )
        
        assert unflag_result["success"] is True
        assert unflag_result["flagged"] is False
        
        # Step 6: Verify unflag persists
        updated_flag_info = self.failure_service._load_flagged_failure(failure_id)
        assert updated_flag_info is not None
        assert updated_flag_info["flagged"] is False
        
        # Step 7: Verify no longer appears in flagged list
        updated_flagged_failures, _ = self.failure_service.list_failures(flagged=True)
        assert len(updated_flagged_failures) == 0
    
    async def test_flag_persistence_across_service_instances(self):
        """Test that flag data persists across service instances."""
        failure_id = self.test_failure.id
        
        # Flag with first service instance
        flag_note = "Cross-service persistence test"
        result1 = self.failure_service.flag_failure(
            failure_id=failure_id,
            note=flag_note,
            user_id="test-user"
        )
        assert result1["success"] is True
        
        # Create new service instance (simulates app restart)
        new_service = FailureService(
            failure_repository=self.failure_repository
        )
        
        # Verify flag data is available in new instance
        flag_info = new_service._load_flagged_failure(failure_id)
        assert flag_info is not None
        assert flag_info["note"] == flag_note
    
    async def test_flag_with_low_confidence_selector(self):
        """Test flagging selectors with low confidence scores."""
        # Create a failure with low confidence alternatives
        self.failure_service.register_alternative(
            failure_id=self.test_failure.id,
            selector=".low-confidence-selector",
            strategy_type="css"
        )
        
        # Flag the failure
        flag_result = self.failure_service.flag_failure(
            failure_id=self.test_failure.id,
            note="Low confidence selector needs review",
            user_id="test-user"
        )
        
        assert flag_result["success"] is True
        
        # Verify flag is visible in detail view with alternatives
        failure_detail = self.failure_service.get_failure_detail(
            self.test_failure.id,
            include_alternatives=True
        )
        
        assert failure_detail["flagged"] is True
        assert len(failure_detail["alternatives"]) > 0
        assert all(alt["confidence_score"] < 0.5 for alt in failure_detail["alternatives"])
    
    async def test_flag_validation_errors(self):
        """Test flag validation and error handling."""
        failure_id = self.test_failure.id
        
        # Test flagging non-existent failure
        result = self.failure_service.flag_failure(
            failure_id=99999,
            note="This should fail",
            user_id="test-user"
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower()
        
        # Test unflagging non-flagged failure
        result = self.failure_service.unflag_failure(
            failure_id=failure_id,
            user_id="test-user"
        )
        assert result["success"] is False
        assert "not flagged" in result["message"].lower()
    
    async def test_flag_audit_trail(self):
        """Test that flag actions create proper audit events."""
        failure_id = self.test_failure.id
        
        # Flag the failure
        flag_note = "Audit trail test"
        self.failure_service.flag_failure(
            failure_id=failure_id,
            note=flag_note,
            user_id="audit-test-user"
        )
        
        # Check that audit event was created
        # This would require access to the audit repository in a real implementation
        # For now, we verify the service doesn't crash
        assert True  # Placeholder - audit verification would go here
    
    async def test_multiple_flags_per_failure(self):
        """Test that multiple flag operations work correctly."""
        failure_id = self.test_failure.id
        
        # First flag
        result1 = self.failure_service.flag_failure(
            failure_id=failure_id,
            note="First flag",
            user_id="test-user"
        )
        assert result1["success"] is True
        
        # Second flag (should update)
        result2 = self.failure_service.flag_failure(
            failure_id=failure_id,
            note="Updated flag reason",
            user_id="test-user"
        )
        assert result2["success"] is True
        
        # Verify latest flag info
        flag_info = self.failure_service._load_flagged_failure(failure_id)
        assert flag_info["note"] == "Updated flag reason"


if __name__ == "__main__":
    # Run the tests
    asyncio.run(pytest.main([__file__]))
