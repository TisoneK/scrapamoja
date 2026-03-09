"""
Unit tests for PostExtractionValidator.

Tests the validation layer hook for selector failure detection,
covering AC1 (empty_result), AC2 (exception), AC3 (timeout), and AC4 (failure event fields).

Story 3-1: Selector Failure Event Capture
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from src.selectors.hooks.post_extraction import PostExtractionValidator, create_failure_event
from src.selectors.fallback.models import FailureEvent, FailureType, FallbackResult


class TestPostExtractionValidator:
    """Test cases for PostExtractionValidator."""

    @pytest.fixture
    def validator(self):
        """Create a PostExtractionValidator instance for testing."""
        return PostExtractionValidator()

    # === AC1: Empty Result Detection Tests ===

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "result",
        [
            None,
            "",
            [],
            {},
            (),
            set(),
        ],
        ids=["None", "empty_string", "empty_list", "empty_dict", "empty_tuple", "empty_set"],
    )
    def test_is_empty_result_returns_true_for_empty_values(self, validator, result):
        """Test that is_empty_result returns True for empty values (AC1)."""
        assert validator.is_empty_result(result) is True

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "result",
        [
            "some text",
            [1, 2, 3],
            {"key": "value"},
            (1, 2),
            {1, 2},
            0,
            False,
            "0",  # String zero is not empty
        ],
        ids=[
            "non_empty_string",
            "non_empty_list",
            "non_empty_dict",
            "non_empty_tuple",
            "non_empty_set",
            "zero",
            "false",
            "string_zero",
        ],
    )
    def test_is_empty_result_returns_false_for_non_empty_values(self, validator, result):
        """Test that is_empty_result returns False for non-empty values."""
        assert validator.is_empty_result(result) is False

    @pytest.mark.unit
    def test_validate_result_returns_failure_event_for_none(self, validator):
        """Test empty_result detection for None (AC1)."""
        failure = validator.validate_result(
            result=None,
            selector_id="team_name",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
        )

        assert failure is not None
        assert failure.selector_id == "team_name"
        assert failure.url == "https://example.com/match"
        assert failure.failure_type == FailureType.EMPTY_RESULT
        assert failure.context["extractor_id"] == "flashscore_extractor"

    @pytest.mark.unit
    def test_validate_result_returns_failure_event_for_empty_string(self, validator):
        """Test empty_result detection for empty string (AC1)."""
        failure = validator.validate_result(
            result="",
            selector_id="team_name",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
        )

        assert failure is not None
        assert failure.failure_type == FailureType.EMPTY_RESULT

    @pytest.mark.unit
    def test_validate_result_returns_failure_event_for_empty_list(self, validator):
        """Test empty_result detection for empty list (AC1)."""
        failure = validator.validate_result(
            result=[],
            selector_id="team_name",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
        )

        assert failure is not None
        assert failure.failure_type == FailureType.EMPTY_RESULT

    # === AC2: Exception Detection Tests ===

    @pytest.mark.unit
    def test_validate_result_returns_failure_event_for_exception(self, validator):
        """Test exception detection (AC2)."""
        original_exception = ValueError("Selector not found")

        failure = validator.validate_result(
            result=None,
            selector_id="team_name",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
            exception=original_exception,
        )

        assert failure is not None
        assert failure.failure_type == FailureType.EXCEPTION
        assert "ValueError" in failure.error_message or "Selector not found" in failure.error_message

    @pytest.mark.unit
    def test_validate_result_returns_failure_event_for_various_exception_types(self, validator):
        """Test exception detection with various exception types (AC2)."""
        exception_types = [
            (ValueError("Invalid selector"), "Invalid selector"),
            (RuntimeError("Execution failed"), "Execution failed"),
            (KeyError("missing_key"), "missing_key"),
            (AttributeError("no attribute"), "no attribute"),
        ]

        for exception, expected_message in exception_types:
            failure = validator.validate_result(
                result=None,
                selector_id="test_selector",
                page_url="https://example.com",
                extractor_id="test_extractor",
                exception=exception,
            )

            assert failure is not None
            assert failure.failure_type == FailureType.EXCEPTION
            assert expected_message in failure.error_message

    @pytest.mark.unit
    def test_validate_result_exception_without_message(self, validator):
        """Test exception detection when exception has no message (AC2)."""
        exception = Exception()

        failure = validator.validate_result(
            result=None,
            selector_id="test_selector",
            page_url="https://example.com",
            extractor_id="test_extractor",
            exception=exception,
        )

        assert failure is not None
        assert failure.failure_type == FailureType.EXCEPTION
        assert failure.error_message == "Exception"  # Should use exception type name

    # === AC3: Timeout Detection Tests ===

    @pytest.mark.unit
    def test_validate_result_returns_failure_event_for_timeout(self, validator):
        """Test timeout detection (AC3)."""
        timeout_exception = asyncio.TimeoutError()

        failure = validator.validate_result(
            result=None,
            selector_id="team_name",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
            exception=timeout_exception,
        )

        assert failure is not None
        assert failure.failure_type == FailureType.TIMEOUT

    @pytest.mark.unit
    def test_validate_result_timeout_error_class(self, validator):
        """Test that asyncio.TimeoutError is correctly detected as timeout (AC3)."""
        failure = validator.validate_result(
            result=None,
            selector_id="test_selector",
            page_url="https://example.com",
            extractor_id="test_extractor",
            exception=asyncio.TimeoutError("Request timed out"),
        )

        assert failure is not None
        assert failure.failure_type == FailureType.TIMEOUT

    @pytest.mark.unit
    def test_validate_result_returns_failure_event_for_builtin_timeout(self, validator):
        """Test that builtin TimeoutError is correctly detected as timeout (AC3)."""
        failure = validator.validate_result(
            result=None,
            selector_id="test_selector",
            page_url="https://example.com",
            extractor_id="test_extractor",
            exception=TimeoutError("Request timed out"),
        )

        assert failure is not None
        assert failure.failure_type == FailureType.TIMEOUT

    # === AC4: Failure Event Fields Tests ===

    @pytest.mark.unit
    def test_validate_result_populates_all_required_fields(self, validator):
        """Test that failure event includes all required fields (AC4)."""
        failure = validator.validate_result(
            result=None,
            selector_id="team_name",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
        )

        # Verify all required AC4 fields are populated
        assert failure.selector_id == "team_name"
        assert failure.url == "https://example.com/match"
        assert failure.timestamp is not None
        assert failure.failure_type == FailureType.EMPTY_RESULT
        assert failure.context["extractor_id"] == "flashscore_extractor"

    @pytest.mark.unit
    def test_validate_result_returns_none_for_successful_result(self, validator):
        """Test that validator returns None for successful extraction."""
        result = "Valid extraction result"

        failure = validator.validate_result(
            result=result,
            selector_id="team_name",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
        )

        assert failure is None

    @pytest.mark.unit
    def test_validate_result_returns_none_for_valid_list(self, validator):
        """Test that validator returns None for non-empty list."""
        result = ["item1", "item2", "item3"]

        failure = validator.validate_result(
            result=result,
            selector_id="team_names",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
        )

        assert failure is None

    @pytest.mark.unit
    def test_validate_result_returns_none_for_valid_dict(self, validator):
        """Test that validator returns None for non-empty dict."""
        result = {"team": " Arsenal", "score": "2"}

        failure = validator.validate_result(
            result=result,
            selector_id="match_info",
            page_url="https://example.com/match",
            extractor_id="flashscore_extractor",
        )

        assert failure is None

    # === Edge Cases ===

    @pytest.mark.unit
    def test_validate_result_with_empty_page_url(self, validator):
        """Test that validator handles empty page_url gracefully."""
        failure = validator.validate_result(
            result=None,
            selector_id="team_name",
            page_url="",
            extractor_id="flashscore_extractor",
        )

        assert failure is not None
        assert failure.url == ""

    @pytest.mark.unit
    def test_detect_failure_type_returns_none_for_valid_result(self, validator):
        """Test that detect_failure_type returns None for valid results."""
        result = "Valid result"

        failure_type = validator.detect_failure_type(result, None)

        assert failure_type is None

    @pytest.mark.unit
    def test_detect_failure_type_exception_takes_precedence(self, validator):
        """Test that exception detection takes precedence over empty result."""
        # Even with empty result, exception should be detected
        failure_type = validator.detect_failure_type(
            result=None,
            exception=ValueError("Error occurred"),
        )

        assert failure_type == FailureType.EXCEPTION


class TestCreateFailureEvent:
    """Test cases for create_failure_event helper function."""

    @pytest.mark.unit
    def test_create_failure_event_with_all_parameters(self):
        """Test creating failure event with all parameters."""
        from datetime import datetime, timezone

        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
            error_message="No teams found",
        )

        assert failure.selector_id == "team_name"
        assert failure.url == "https://example.com/match"
        assert failure.failure_type == FailureType.EMPTY_RESULT
        assert failure.error_message == "No teams found"
        assert failure.context["extractor_id"] == "flashscore_extractor"
        assert failure.timestamp is not None

    @pytest.mark.unit
    def test_create_failure_event_without_error_message(self):
        """Test creating failure event without optional error_message."""
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )

        assert failure.error_message is None
        assert failure.context["extractor_id"] == "flashscore_extractor"

    @pytest.mark.unit
    def test_create_failure_event_for_exception_type(self):
        """Test creating failure event for exception type."""
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EXCEPTION,
            extractor_id="flashscore_extractor",
            error_message="ValueError: Invalid selector",
        )

        assert failure.failure_type == FailureType.EXCEPTION

    @pytest.mark.unit
    def test_create_failure_event_for_timeout_type(self):
        """Test creating failure event for timeout type."""
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.TIMEOUT,
            extractor_id="flashscore_extractor",
            error_message="Timeout after 30s",
        )

        assert failure.failure_type == FailureType.TIMEOUT


# === Story 3-2: Full Context Failure Logging Tests ===


class TestCorrelationIdManagement:
    """Test cases for correlation ID management (Story 3-2, AC4)."""

    @pytest.mark.unit
    def test_get_or_create_correlation_id_creates_new_id(self):
        """Test that get_or_create_correlation_id creates a new ID when none exists."""
        from src.selectors.hooks.post_extraction import (
            get_or_create_correlation_id,
            clear_correlation_id,
        )
        
        clear_correlation_id()  # Clear any existing ID
        correlation_id = get_or_create_correlation_id()
        
        assert correlation_id is not None
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0

    @pytest.mark.unit
    def test_get_or_create_correlation_id_reuses_existing_id(self):
        """Test that get_or_create_correlation_id reuses existing ID."""
        from src.selectors.hooks.post_extraction import (
            get_or_create_correlation_id,
            set_correlation_id,
            clear_correlation_id,
        )
        
        clear_correlation_id()
        expected_id = "test-correlation-id-12345"
        set_correlation_id(expected_id)
        
        correlation_id = get_or_create_correlation_id()
        
        assert correlation_id == expected_id

    @pytest.mark.unit
    def test_set_and_clear_correlation_id(self):
        """Test setting and clearing correlation ID."""
        from src.selectors.hooks.post_extraction import (
            get_or_create_correlation_id,
            set_correlation_id,
            clear_correlation_id,
        )
        
        clear_correlation_id()
        assert get_or_create_correlation_id() is not None
        
        clear_correlation_id()
        # After clearing, a new ID should be created
        new_id = get_or_create_correlation_id()
        assert new_id is not None


class TestAttemptedFallbacksCapture:
    """Test cases for attempted_fallbacks capture (Story 3-2, AC1, AC2)."""

    @pytest.mark.unit
    def test_add_fallback_context_to_failure_with_fallback_result(self):
        """Test adding fallback context to failure event (AC2)."""
        from datetime import datetime, timezone
        from src.selectors.hooks.post_extraction import (
            add_fallback_context_to_failure,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        # Create mock fallback result with attempted_selectors
        fallback_result = FallbackResult(
            primary_selector="team_name",
            primary_success=False,
            fallback_executed=True,
            fallback_success=True,
            final_result="Test Result",
            attempted_selectors=[
                {
                    "name": "team_name",
                    "result": "failure",
                    "reason": "Empty result",
                    "value": None,
                    "resolution_time_ms": 100.0,
                },
                {
                    "name": "team_name_fallback",
                    "result": "success",
                    "reason": None,
                    "value": "Test Result",
                    "resolution_time_ms": 50.0,
                },
            ],
        )
        
        result = add_fallback_context_to_failure(failure, fallback_result)
        
        assert "attempted_fallbacks" in result.context
        assert len(result.context["attempted_fallbacks"]) == 2
        assert result.context["attempted_fallbacks"][0]["selector"] == "team_name"
        assert result.context["attempted_fallbacks"][0]["result"] == "failure"
        assert result.context["attempted_fallbacks"][1]["selector"] == "team_name_fallback"
        assert result.context["attempted_fallbacks"][1]["result"] == "success"

    @pytest.mark.unit
    def test_add_fallback_context_to_failure_without_fallback_result(self):
        """Test adding fallback context when no fallback result provided (AC1)."""
        from src.selectors.hooks.post_extraction import (
            add_fallback_context_to_failure,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        result = add_fallback_context_to_failure(failure, None)
        
        assert "attempted_fallbacks" in result.context
        assert result.context["attempted_fallbacks"] == []

    @pytest.mark.unit
    def test_add_fallback_context_to_failure_preserves_existing_context(self):
        """Test that adding fallback context preserves existing context fields."""
        from src.selectors.hooks.post_extraction import (
            add_fallback_context_to_failure,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        failure.context["existing_field"] = "existing_value"
        
        result = add_fallback_context_to_failure(failure, None)
        
        assert result.context["existing_field"] == "existing_value"
        assert result.context["extractor_id"] == "flashscore_extractor"


class TestISO8601Timestamps:
    """Test cases for ISO8601 timestamp format (Story 3-2, AC3)."""

    @pytest.mark.unit
    def test_create_full_context_failure_event_uses_iso8601(self):
        """Test that create_full_context_failure_event uses ISO8601 format (AC3)."""
        from src.selectors.hooks.post_extraction import (
            create_full_context_failure_event,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        result = create_full_context_failure_event(failure, None)
        
        # Verify timestamp is in ISO8601 format
        assert result.timestamp is not None
        assert hasattr(result.timestamp, 'isoformat')

    @pytest.mark.unit
    def test_add_fallback_context_includes_iso8601_timestamp(self):
        """Test that attempted_fallbacks includes ISO8601 timestamps (AC3)."""
        from src.selectors.hooks.post_extraction import (
            add_fallback_context_to_failure,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        fallback_result = FallbackResult(
            primary_selector="team_name",
            primary_success=False,
            fallback_executed=False,
            fallback_success=False,
            final_result=None,
            attempted_selectors=[
                {"name": "team_name", "result": "failure", "reason": "Empty"},
            ],
        )
        
        result = add_fallback_context_to_failure(failure, fallback_result)
        
        assert len(result.context["attempted_fallbacks"]) == 1
        assert "timestamp" in result.context["attempted_fallbacks"][0]


class TestCorrelationIdInLogs:
    """Test cases for correlation ID in logs (Story 3-2, AC4)."""

    @pytest.mark.unit
    def test_add_correlation_to_failure_adds_correlation_id(self):
        """Test adding correlation ID to failure event (AC4)."""
        from src.selectors.hooks.post_extraction import (
            add_correlation_to_failure,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        result = add_correlation_to_failure(failure, "test-correlation-123")
        
        assert "correlation_id" in result.context
        assert result.context["correlation_id"] == "test-correlation-123"

    @pytest.mark.unit
    def test_add_correlation_to_failure_auto_creates_id(self):
        """Test that correlation ID is auto-created if not provided (AC4)."""
        from src.selectors.hooks.post_extraction import (
            add_correlation_to_failure,
            create_failure_event,
            clear_correlation_id,
        )
        
        clear_correlation_id()
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        result = add_correlation_to_failure(failure)
        
        assert "correlation_id" in result.context
        assert result.context["correlation_id"] is not None

    @pytest.mark.unit
    def test_create_full_context_failure_event_includes_correlation_id(self):
        """Test that create_full_context_failure_event includes correlation ID (AC4)."""
        from src.selectors.hooks.post_extraction import (
            create_full_context_failure_event,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        result = create_full_context_failure_event(failure, None, "custom-correlation-id")
        
        assert "correlation_id" in result.context
        assert result.context["correlation_id"] == "custom-correlation-id"


class TestFailureEventLogger:
    """Test cases for FailureEventLogger (Story 3-2, AC4)."""

    @pytest.mark.unit
    def test_failure_event_logger_sets_warning_level(self):
        """Test that FailureEventLogger sets WARNING for single failure (AC4)."""
        from src.selectors.hooks.post_extraction import (
            create_full_context_failure_event,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        # Create without fallback_result (no fallback executed)
        result = create_full_context_failure_event(failure, None)
        
        assert result.context.get("log_level") == "WARNING"

    @pytest.mark.unit
    def test_failure_event_logger_sets_error_level(self):
        """Test that FailureEventLogger sets ERROR when fallback executed but failed (AC4)."""
        from src.selectors.hooks.post_extraction import (
            create_full_context_failure_event,
            create_failure_event,
        )
        
        failure = create_failure_event(
            selector_id="team_name",
            page_url="https://example.com/match",
            failure_type=FailureType.EMPTY_RESULT,
            extractor_id="flashscore_extractor",
        )
        
        # Create with fallback_result where fallback was executed
        fallback_result = FallbackResult(
            primary_selector="team_name",
            primary_success=False,
            fallback_executed=True,
            fallback_success=False,
            final_result=None,
            attempted_selectors=[],
        )
        
        result = create_full_context_failure_event(failure, fallback_result)
        
        assert result.context.get("log_level") == "ERROR"
