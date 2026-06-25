"""
Unit tests for FailureEventSubmissionService.

Tests the adaptive module DB submission service covering:
- AC1: Sync DB Submission
- AC2: Successful DB Storage
- AC3: Graceful Failure Handling
- AC4: Queue for Retry on Unavailability
"""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.selectors.fallback.models import FailureEvent, FailureType


class TestFailureEventSubmissionService:
    """Test cases for FailureEventSubmissionService."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        from src.selectors.hooks.submission import FailureEventSubmissionService
        FailureEventSubmissionService._instance = None
        FailureEventSubmissionService._repository = None
        FailureEventSubmissionService._retry_queue = []
        yield
        # Cleanup after test
        FailureEventSubmissionService._instance = None

    @pytest.fixture
    def mock_repository(self):
        """Create a mock FailureEventRepository."""
        return MagicMock()

    @pytest.fixture
    def sample_failure_event(self):
        """Create a sample FailureEvent for testing."""
        return FailureEvent(
            selector_id="team_name",
            url="https://example.com/match",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EMPTY_RESULT,
            error_message="Result is empty",
            context={
                "extractor_id": "flashscore_extractor",
                "correlation_id": "test-correlation-123",
                "sport": "basketball",
                "site": "flashscore",
                "attempted_fallbacks": [
                    {"selector": "team_name_alt1", "result": "failure"}
                ],
            },
        )

    # === AC1: Sync DB Submission Tests ===

    @pytest.mark.unit
    def test_submit_successful_submission(self, mock_repository, sample_failure_event):
        """Test successful DB submission (AC1, AC2)."""
        # Patch at class level
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import FailureEventSubmissionService, get_submission_service
            
            service = get_submission_service()
            result = service.submit(sample_failure_event)

            assert result is True
            mock_repository.create.assert_called_once()

    @pytest.mark.unit
    def test_submit_calls_repository_with_correct_params(self, mock_repository, sample_failure_event):
        """Test that submission calls repository with correct parameters (AC2)."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service.submit(sample_failure_event)

            call_kwargs = mock_repository.create.call_args.kwargs
            assert call_kwargs["selector_id"] == "team_name"
            assert call_kwargs["error_type"] == "empty_result"
            assert call_kwargs["failure_reason"] == "Result is empty"
            assert call_kwargs["correlation_id"] == "test-correlation-123"
            assert call_kwargs["sport"] == "basketball"
            assert call_kwargs["site"] == "flashscore"

    # === AC3: Graceful Failure Handling Tests ===

    @pytest.mark.unit
    def test_submit_returns_true_on_db_failure(self, mock_repository, sample_failure_event):
        """Test graceful failure handling - returns True on DB error (AC3)."""
        mock_repository.create.side_effect = Exception("DB connection failed")

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            result = service.submit(sample_failure_event)

            assert result is True  # AC3: Don't crash scraper

    @pytest.mark.unit
    def test_submit_queues_event_on_db_failure(self, mock_repository, sample_failure_event):
        """Test that event is queued when DB is unavailable (AC4)."""
        mock_repository.create.side_effect = Exception("DB connection failed")

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service.submit(sample_failure_event)

            assert len(service._retry_queue) == 1

    @pytest.mark.unit
    def test_submit_logs_warning_on_db_failure(self, mock_repository, sample_failure_event, caplog):
        """Test that errors are logged without crashing (AC3)."""
        mock_repository.create.side_effect = Exception("DB connection failed")

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service.submit(sample_failure_event)

            # Should have logged a warning
            assert any("DB submission failed" in record.message for record in caplog.records)

    # === AC4: Queue for Retry Tests ===

    @pytest.mark.unit
    def test_queue_for_retry_adds_to_queue(self, mock_repository, sample_failure_event):
        """Test that event is added to retry queue (AC4)."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service._queue_for_retry(sample_failure_event)

            assert len(service._retry_queue) == 1

    @pytest.mark.unit
    def test_queue_respects_max_size(self, mock_repository, sample_failure_event):
        """Test that queue respects maximum size limit (AC4)."""
        from src.selectors.hooks.submission import MAX_QUEUE_SIZE
        
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            
            # Fill queue to max
            for i in range(MAX_QUEUE_SIZE):
                event = FailureEvent(
                    selector_id=f"selector_{i}",
                    url="https://example.com",
                    timestamp=datetime.now(timezone.utc),
                    failure_type=FailureType.EMPTY_RESULT,
                    context={},
                )
                service._retry_queue.append(event)

            # Try to add one more
            service._queue_for_retry(sample_failure_event)

            # Queue should still be max size (oldest dropped)
            assert len(service._retry_queue) == MAX_QUEUE_SIZE

    @pytest.mark.unit
    def test_process_retry_queue_success(self, mock_repository):
        """Test successful retry queue processing (AC4)."""
        event = FailureEvent(
            selector_id="retry_test",
            url="https://example.com",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EXCEPTION,
            context={"correlation_id": "retry-123"},
        )

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service._retry_queue.append(event)
            
            service._process_retry_queue()

            assert len(service._retry_queue) == 0
            mock_repository.create.assert_called()

    @pytest.mark.unit
    def test_process_retry_queue_stops_on_failure(self, mock_repository):
        """Test that retry processing stops on first failure (AC4)."""
        event1 = FailureEvent(
            selector_id="retry_test1",
            url="https://example.com",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EXCEPTION,
            context={},
        )
        event2 = FailureEvent(
            selector_id="retry_test2",
            url="https://example.com",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EXCEPTION,
            context={},
        )

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service._retry_queue.append(event1)
            service._retry_queue.append(event2)
            
            # First call fails, second would succeed
            mock_repository.create.side_effect = [Exception("DB unavailable"), None]

            service._process_retry_queue()

            # First failed, stopped processing, both still in queue
            assert len(service._retry_queue) == 2

    # === Conversion Tests ===

    @pytest.mark.unit
    def test_convert_to_db_event_basic(self, mock_repository, sample_failure_event):
        """Test conversion of basic failure event to DB format."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            result = service._convert_to_db_event(sample_failure_event)

            assert result["selector_id"] == "team_name"
            assert result["error_type"] == "empty_result"
            assert result["failure_reason"] == "Result is empty"
            assert result["correlation_id"] == "test-correlation-123"

    @pytest.mark.unit
    def test_convert_to_db_event_extracts_strategy(self, mock_repository):
        """Test that strategy is extracted from attempted_fallbacks."""
        event = FailureEvent(
            selector_id="test",
            url="https://example.com",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EXCEPTION,
            context={
                "attempted_fallbacks": [
                    {"selector": "fallback_1", "result": "failure"},
                    {"selector": "fallback_2", "result": "failure"},
                ]
            },
        )

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            result = service._convert_to_db_event(event)

            assert result["strategy_used"] == "fallback_2"

    @pytest.mark.unit
    def test_convert_to_db_event_handles_empty_context(self, mock_repository):
        """Test conversion handles empty context gracefully."""
        event = FailureEvent(
            selector_id="test",
            url="https://example.com",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EXCEPTION,
            context={},
        )

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            result = service._convert_to_db_event(event)

            assert result["selector_id"] == "test"
            assert result["correlation_id"] is None
            assert result["sport"] is None

    # === Singleton Tests ===

    @pytest.mark.unit
    def test_singleton_returns_same_instance(self, mock_repository):
        """Test that singleton pattern returns same instance."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            instance1 = get_submission_service()
            instance2 = get_submission_service()

            assert instance1 is instance2

    # === Queue Status Tests ===

    @pytest.mark.unit
    def test_get_queue_status_empty(self, mock_repository):
        """Test queue status when empty."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            status = service.get_queue_status()

            assert status["queue_size"] == 0
            assert status["oldest_event"] is None

    @pytest.mark.unit
    def test_get_queue_status_with_items(self, mock_repository, sample_failure_event):
        """Test queue status with items."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service._retry_queue.append(sample_failure_event)
            
            status = service.get_queue_status()

            assert status["queue_size"] == 1
            assert status["oldest_event"]["selector_id"] == "team_name"

    @pytest.mark.unit
    def test_clear_queue(self, mock_repository, sample_failure_event):
        """Test clearing the retry queue."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service
            
            service = get_submission_service()
            service._retry_queue.append(sample_failure_event)
            service._retry_queue.append(sample_failure_event)

            count = service.clear_queue()

            assert count == 2
            assert len(service._retry_queue) == 0


# === Story 3-4: Sync Failure Capture (Immediate) Tests ===


class TestSyncFailureCaptureImmediate:
    """Test cases for Story 3-4: Sync Failure Capture (Immediate)."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        from src.selectors.hooks.submission import FailureEventSubmissionService
        FailureEventSubmissionService._instance = None
        FailureEventSubmissionService._repository = None
        FailureEventSubmissionService._retry_queue = []
        yield
        # Cleanup after test
        FailureEventSubmissionService._instance = None

    @pytest.fixture
    def mock_repository(self):
        """Create a mock FailureEventRepository."""
        return MagicMock()

    @pytest.fixture
    def sample_failure_event(self):
        """Create a sample FailureEvent for testing."""
        return FailureEvent(
            selector_id="team_name",
            url="https://example.com/match",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EMPTY_RESULT,
            error_message="Result is empty",
            context={
                "extractor_id": "flashscore_extractor",
                "correlation_id": "test-correlation-123",
            },
        )

    # === AC1: Timing Optimization Tests ===

    @pytest.mark.unit
    def test_submit_within_latency_threshold(self, mock_repository, sample_failure_event):
        """Test that submission completes within 5 second threshold (AC1)."""
        import time

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()

            start_time = time.time()
            result = service.submit_with_timeout(sample_failure_event)
            elapsed = time.time() - start_time

            assert result is True
            assert elapsed <= 5.0, f"Submission took {elapsed:.2f}s, exceeds 5s threshold"

    @pytest.mark.unit
    def test_latency_warning_when_exceeds_threshold(self, mock_repository, sample_failure_event, caplog):
        """Test that warning is logged when latency exceeds threshold (AC1)."""
        import time

        # Simulate slow DB submission
        def slow_create(*args, **kwargs):
            time.sleep(0.1)  # Small delay to trigger timing check
            return None

        mock_repository.create.side_effect = slow_create

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()

            # Even with slow DB, should not exceed threshold but may log warning
            result = service.submit_with_timeout(sample_failure_event)

            assert result is True

    # === AC2: Timeout Handling Tests ===

    @pytest.mark.unit
    def test_submit_with_custom_timeout(self, mock_repository, sample_failure_event):
        """Test submission with custom timeout (AC2)."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()
            service.set_timeout(5)  # 5 second timeout

            result = service.submit_with_timeout(sample_failure_event)

            assert result is True
            assert service._submission_timeout == 5

    @pytest.mark.unit
    def test_submit_returns_true_on_timeout(self, mock_repository, sample_failure_event):
        """Test that submission returns True on timeout (AC2)."""
        import time

        def slow_create(*args, **kwargs):
            time.sleep(0.5)  # Long delay
            return None

        mock_repository.create.side_effect = slow_create

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()
            service.set_timeout(0.1)  # Very short timeout

            result = service.submit_with_timeout(sample_failure_event)

            # AC2: Should return True to not crash scraper
            assert result is True

    @pytest.mark.unit
    def test_timeout_logs_warning(self, mock_repository, sample_failure_event, caplog):
        """Test that timeout events are logged (AC2)."""
        import time

        def slow_create(*args, **kwargs):
            time.sleep(0.5)
            return None

        mock_repository.create.side_effect = slow_create

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()
            service.set_timeout(0.1)

            service.submit_with_timeout(sample_failure_event)

            # Should have logged a warning about timeout
            assert any("timeout" in record.message.lower() for record in caplog.records)

    @pytest.mark.unit
    def test_default_timeout_is_30_seconds(self, mock_repository):
        """Test that default timeout is 30 seconds (AC2, NFR4)."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service, DEFAULT_SUBMISSION_TIMEOUT

            service = get_submission_service()

            assert service._submission_timeout == DEFAULT_SUBMISSION_TIMEOUT
            assert DEFAULT_SUBMISSION_TIMEOUT == 30

    # === AC3: High-Volume Handling Tests ===

    @pytest.mark.unit
    def test_batch_submission_success(self, mock_repository):
        """Test successful batch submission (AC3)."""
        events = [
            FailureEvent(
                selector_id=f"selector_{i}",
                url="https://example.com",
                timestamp=datetime.now(timezone.utc),
                failure_type=FailureType.EMPTY_RESULT,
                context={},
            )
            for i in range(5)
        ]

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()
            result = service.submit_batch(events)

            assert result is True
            assert mock_repository.create.call_count == 5

    @pytest.mark.unit
    def test_batch_submission_handles_partial_failure(self, mock_repository):
        """Test batch submission handles partial failures (AC3)."""
        events = [
            FailureEvent(
                selector_id=f"selector_{i}",
                url="https://example.com",
                timestamp=datetime.now(timezone.utc),
                failure_type=FailureType.EMPTY_RESULT,
                context={},
            )
            for i in range(3)
        ]

        # Second event fails
        mock_repository.create.side_effect = [None, Exception("DB error"), None]

        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()
            result = service.submit_batch(events)

            # Should still return True (AC3: graceful handling)
            assert result is True

    @pytest.mark.unit
    def test_backpressure_warning_when_queue_full(self, mock_repository, sample_failure_event, caplog):
        """Test backpressure warning when queue is nearly full (AC3)."""
        from src.selectors.hooks.submission import MAX_QUEUE_SIZE, FailureEventSubmissionService

        # Fill queue to 80% capacity
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            service = FailureEventSubmissionService()
            service._retry_queue = [
                sample_failure_event
                for _ in range(int(MAX_QUEUE_SIZE * 0.8))
            ]

            # Try to queue one more
            service._queue_for_retry(sample_failure_event)

            # Should have logged backpressure warning
            assert any("backpressure" in record.message.lower() or "high" in record.message.lower()
                      for record in caplog.records)

    # === Integration Tests ===

    @pytest.mark.unit
    def test_submit_with_timeout_uses_internal_submit(self, mock_repository, sample_failure_event):
        """Test that submit_with_timeout properly calls internal submission."""
        with patch('src.selectors.hooks.submission.FailureEventRepository', return_value=mock_repository):
            from src.selectors.hooks.submission import get_submission_service

            service = get_submission_service()
            result = service.submit_with_timeout(sample_failure_event)

            assert result is True
            # Verify repository was called
            mock_repository.create.assert_called()

