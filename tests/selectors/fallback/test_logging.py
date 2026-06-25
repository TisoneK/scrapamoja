"""
Tests for Story 1.4: Fallback Attempt Logging

This module tests the fallback attempt logging functionality as defined in:
- AC1: Fallback Attempt Logging - Log all fallback attempts with selector ID, page URL, timestamp, attempted selectors in order, final result
- AC2: Fallback Success Logging - Log which fallback succeeded and the extracted value
- AC3: Fallback Failure Logging - Log all failed selectors with failure reasons

These tests verify:
- FallbackAttemptLog model creation and serialization
- SelectorAttempt model with value redaction
- Logging integration with @with_fallback decorator
- Success and failure logging scenarios
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.selectors.fallback.logging import FallbackAttemptLogger, get_fallback_logger
from src.selectors.fallback.models import (
    FallbackAttemptLog,
    FallbackResult,
    SelectorAttempt,
    FallbackStatus,
    FailureType,
    FailureEvent,
)


class TestSelectorAttempt:
    """Test suite for SelectorAttempt model."""
    
    def test_selector_attempt_success(self):
        """Test SelectorAttempt creation for success case."""
        attempt = SelectorAttempt(
            name="primary_selector",
            result="success",
            value="extracted text content",
            resolution_time_ms=150.5
        )
        
        assert attempt.name == "primary_selector"
        assert attempt.result == "success"
        assert attempt.value == "extracted text content"
        assert attempt.resolution_time_ms == 150.5
    
    def test_selector_attempt_failure(self):
        """Test SelectorAttempt creation for failure case."""
        attempt = SelectorAttempt(
            name="fallback_selector",
            result="failure",
            reason="empty_result",
            resolution_time_ms=50.2
        )
        
        assert attempt.name == "fallback_selector"
        assert attempt.result == "failure"
        assert attempt.reason == "empty_result"
        assert attempt.value is None
    
    def test_selector_attempt_to_dict(self):
        """Test SelectorAttempt serialization to dict."""
        attempt = SelectorAttempt(
            name="test_selector",
            result="success",
            value="test value",
            resolution_time_ms=100.0
        )
        
        result = attempt.to_dict()
        
        assert result["name"] == "test_selector"
        assert result["result"] == "success"
        assert result["value"] == "test value"
        assert result["resolution_time_ms"] == 100.0
    
    def test_value_redaction_sensitive(self):
        """Test that sensitive values are redacted."""
        attempt = SelectorAttempt(
            name="test",
            result="success",
            value="password123"
        )
        
        # Values containing "password" should be redacted
        # This is handled in _redact_value
        result = attempt._redact_value("password123")
        assert result == "[REDACTED]"
    
    def test_value_redaction_long_value(self):
        """Test that long values are truncated."""
        long_value = "a" * 200
        attempt = SelectorAttempt(
            name="test",
            result="success",
            value=long_value
        )
        
        # Call static method directly
        result = SelectorAttempt._redact_value(long_value)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) <= 103  # 100 + "..."
    
    def test_value_redaction_normal(self):
        """Test that normal values are not modified."""
        normal_value = "normal text content"
        attempt = SelectorAttempt(
            name="test",
            result="success",
            value=normal_value
        )
        
        result = attempt._redact_value(normal_value)
        assert result == normal_value


class TestFallbackAttemptLog:
    """Test suite for FallbackAttemptLog model."""
    
    def test_fallback_attempt_log_success(self):
        """Test FallbackAttemptLog creation for success case (AC1, AC2)."""
        attempted_selectors = [
            SelectorAttempt(name="primary", result="failure", reason="empty"),
            SelectorAttempt(name="fallback1", result="success", value="extracted value"),
        ]
        
        log = FallbackAttemptLog(
            selector_id="price_main",
            page_url="https://example.com/product",
            timestamp=datetime.now(timezone.utc),
            attempted_selectors=attempted_selectors,
            final_result="success",
            total_time_ms=250.5
        )
        
        assert log.selector_id == "price_main"
        assert log.page_url == "https://example.com/product"
        assert log.final_result == "success"
        assert len(log.attempted_selectors) == 2
    
    def test_fallback_attempt_log_failure(self):
        """Test FallbackAttemptLog creation for failure case (AC1, AC3)."""
        attempted_selectors = [
            SelectorAttempt(name="primary", result="failure", reason="empty_result"),
            SelectorAttempt(name="fallback1", result="failure", reason="exception"),
        ]
        
        log = FallbackAttemptLog(
            selector_id="title_main",
            page_url="https://example.com/page",
            timestamp=datetime.now(timezone.utc),
            attempted_selectors=attempted_selectors,
            final_result="failure",
            total_time_ms=500.0
        )
        
        assert log.final_result == "failure"
        assert log.successful_selector is None
    
    def test_successful_selector_property(self):
        """Test the successful_selector property (AC2)."""
        attempted_selectors = [
            SelectorAttempt(name="primary", result="failure", reason="empty"),
            SelectorAttempt(name="fallback1", result="failure", reason="low_confidence"),
            SelectorAttempt(name="fallback2", result="success", value="final value"),
        ]
        
        log = FallbackAttemptLog(
            selector_id="test",
            page_url="https://example.com",
            timestamp=datetime.now(timezone.utc),
            attempted_selectors=attempted_selectors,
            final_result="success",
            total_time_ms=300.0
        )
        
        assert log.successful_selector == "fallback2"
    
    def test_failed_selectors_property(self):
        """Test the failed_selectors property (AC3)."""
        attempted_selectors = [
            SelectorAttempt(name="primary", result="failure", reason="empty_result"),
            SelectorAttempt(name="fallback1", result="failure", reason="exception"),
            SelectorAttempt(name="fallback2", result="success", value="value"),
        ]
        
        log = FallbackAttemptLog(
            selector_id="test",
            page_url="https://example.com",
            timestamp=datetime.now(timezone.utc),
            attempted_selectors=attempted_selectors,
            final_result="success",
            total_time_ms=300.0
        )
        
        failed = log.failed_selectors
        assert len(failed) == 2
        assert {"name": "primary", "reason": "empty_result"} in failed
        assert {"name": "fallback1", "reason": "exception"} in failed
    
    def test_to_dict_complete(self):
        """Test full serialization of FallbackAttemptLog."""
        attempted_selectors = [
            SelectorAttempt(name="primary", result="failure", reason="empty"),
            SelectorAttempt(name="fallback1", result="success", value="result"),
        ]
        
        log = FallbackAttemptLog(
            selector_id="test_id",
            page_url="https://example.com",
            timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            attempted_selectors=attempted_selectors,
            final_result="success",
            total_time_ms=200.0,
            correlation_id="test-correlation-123"
        )
        
        result = log.to_dict()
        
        assert result["selector_id"] == "test_id"
        assert result["page_url"] == "https://example.com"
        assert result["final_result"] == "success"
        assert result["total_time_ms"] == 200.0
        assert result["correlation_id"] == "test-correlation-123"
        assert len(result["attempted_selectors"]) == 2


class TestFallbackAttemptLogger:
    """Test suite for FallbackAttemptLogger class."""
    
    @pytest.fixture
    def logger(self):
        """Fixture providing a FallbackAttemptLogger instance."""
        return FallbackAttemptLogger()
    
    @pytest.fixture
    def mock_fallback_result_success(self):
        """Fixture providing a mock FallbackResult for success case."""
        result = FallbackResult(
            primary_selector="price_main",
            primary_success=False,
            fallback_executed=True,
            fallback_success=True,
            final_result=MagicMock(text_content="$99.99"),
            chain_duration=0.25
        )
        result.fallback_attempt = MagicMock()
        result.fallback_attempt.fallback_selector = "fallback_price"
        result.fallback_attempt.resolution_time = 0.15
        return result
    
    @pytest.fixture
    def mock_fallback_result_failure(self):
        """Fixture providing a mock FallbackResult for failure case."""
        failure_event = FailureEvent(
            selector_id="title_main",
            url="https://example.com/page",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EMPTY_RESULT,
            error_message="Element not found"
        )
        
        result = FallbackResult(
            primary_selector="title_main",
            primary_success=False,
            fallback_executed=True,
            fallback_success=False,
            final_result=None,
            chain_duration=0.5,
            failure_event=failure_event
        )
        result.fallback_attempt = MagicMock()
        result.fallback_attempt.fallback_selector = "fallback_title"
        result.fallback_attempt.error = "Timeout"
        result.fallback_attempt.resolution_time = 0.3
        return result
    
    def test_logger_initialization(self, logger):
        """Test FallbackAttemptLogger can be initialized."""
        assert logger is not None
        assert logger._logger is not None
    
    def test_get_fallback_logger_singleton(self):
        """Test that get_fallback_logger returns singleton."""
        logger1 = get_fallback_logger()
        logger2 = get_fallback_logger()
        assert logger1 is logger2
    
    def test_log_fallback_attempt_success(self, logger, mock_fallback_result_success):
        """Test logging a successful fallback attempt (AC1, AC2)."""
        with patch.object(logger, '_logger') as mock_logger:
            log_entry = logger.log_fallback_attempt(
                fallback_result=mock_fallback_result_success,
                page_url="https://example.com/product"
            )
            
            assert log_entry.final_result == "success"
            assert log_entry.successful_selector is not None
            mock_logger.info.assert_called_once()
    
    def test_log_fallback_attempt_failure(self, logger, mock_fallback_result_failure):
        """Test logging a failed fallback attempt (AC1, AC3)."""
        with patch.object(logger, '_logger') as mock_logger:
            log_entry = logger.log_fallback_attempt(
                fallback_result=mock_fallback_result_failure,
                page_url="https://example.com/page"
            )
            
            assert log_entry.final_result == "failure"
            assert log_entry.successful_selector is None
            assert len(log_entry.failed_selectors) > 0
            mock_logger.warning.assert_called_once()
    
    def test_log_primary_only_success(self, logger):
        """Test logging primary selector success without fallback."""
        mock_result = MagicMock()
        mock_result.text_content = "Primary Value"
        
        with patch.object(logger, '_logger') as mock_logger:
            log_entry = logger.log_primary_only_success(
                selector_id="title_primary",
                page_url="https://example.com",
                result=mock_result,
                resolution_time_ms=50.0
            )
            
            assert log_entry.final_result == "success"
            assert len(log_entry.attempted_selectors) == 1
            assert log_entry.attempted_selectors[0].name == "title_primary"
            assert log_entry.attempted_selectors[0].result == "success"
            mock_logger.info.assert_called_once()
    
    def test_extract_value_for_log_with_text_content(self, logger):
        """Test value extraction from result with text_content."""
        mock_result = MagicMock()
        mock_result.text_content = "Test Value"
        
        value = logger._extract_value_for_log(mock_result)
        assert value == "Test Value"
    
    def test_extract_value_for_log_with_text_attribute(self, logger):
        """Test value extraction from result with text attribute."""
        # Use a real class instead of MagicMock to avoid mock behavior issues
        class MockResult:
            text_content = None
            text = "Text Attribute Value"
        
        value = logger._extract_value_for_log(MockResult())
        assert value == "Text Attribute Value"
    
    def test_extract_value_for_log_with_dict(self, logger):
        """Test value extraction from dict result."""
        result = {"text_content": "Dict Value"}
        
        value = logger._extract_value_for_log(result)
        assert value == "Dict Value"
    
    def test_extract_value_for_log_redacts_sensitive(self, logger):
        """Test that sensitive values are redacted in extraction."""
        # Use a real class instead of MagicMock
        class MockResult:
            text_content = None
            text = "my_secret_token"
        
        value = logger._extract_value_for_log(MockResult())
        assert value == "[REDACTED]"


class TestLoggingIntegration:
    """Integration tests for logging with FallbackResult."""
    
    def test_fallback_result_has_attempted_selectors_field(self):
        """Test that FallbackResult has attempted_selectors field."""
        result = FallbackResult(
            primary_selector="test",
            primary_success=True,
            fallback_executed=False,
            fallback_success=False,
            final_result=None,
            chain_duration=0.1
        )
        
        # Should have attempted_selectors field (added for this story)
        assert hasattr(result, 'attempted_selectors')
    
    def test_fallback_result_to_dict_includes_attempted_selectors(self):
        """Test FallbackResult.to_dict includes attempted_selectors."""
        result = FallbackResult(
            primary_selector="test",
            primary_success=True,
            fallback_executed=False,
            fallback_success=False,
            final_result=None,
            chain_duration=0.1
        )
        
        result_dict = result.to_dict()
        assert "attempted_selectors" in result_dict
