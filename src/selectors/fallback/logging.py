"""
Fallback attempt logging module.

This module provides structured logging for fallback chain execution,
capturing all attempted selectors, results, and failure reasons.

Usage:
    from src.selectors.fallback.logging import FallbackAttemptLogger
    
    logger = FallbackAttemptLogger()
    logger.log_fallback_attempt(fallback_result, page_url)
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.selectors.fallback.models import (
    FallbackAttemptLog,
    FallbackResult,
    SelectorAttempt,
)


class FallbackAttemptLogger:
    """
    Logger for fallback attempt events.
    
    This class handles structured logging of fallback chain attempts,
    including all attempted selectors, results, and failure reasons.
    """
    
    def __init__(self):
        """Initialize the fallback attempt logger."""
        self._logger = self._get_logger()
    
    def _get_logger(self):
        """Get structured logger for fallback logging operations."""
        try:
            from src.observability.logger import get_logger
            return get_logger("selector_fallback.logging")
        except ImportError:
            import logging
            return logging.getLogger("selector_fallback.logging")
    
    def _get_correlation_id(self) -> Optional[str]:
        """Get correlation ID from context if available."""
        try:
            from src.observability.logger import CorrelationContext
            ctx = CorrelationContext()
            return getattr(ctx, 'correlation_id', None)
        except Exception:
            return None
    
    def _extract_value_for_log(self, result: Any) -> Optional[str]:
        """
        Extract value from result for logging (AC2).
        
        Redacts sensitive data and limits value length.
        """
        if result is None:
            return None
        
        # Try to extract text content (check for None to avoid mock issues)
        value = None
        try:
            if hasattr(result, 'text_content'):
                text_content = result.text_content
                if text_content is not None:
                    value = text_content
        except Exception:
            pass
        
        # Try text attribute if text_content didn't work
        if value is None:
            try:
                if hasattr(result, 'text'):
                    text_attr = result.text
                    # Check if it's a string (not a mock)
                    if text_attr is not None and isinstance(text_attr, str):
                        value = text_attr
            except Exception:
                pass
        
        # Try dict
        if value is None and isinstance(result, dict):
            value = result.get('text_content') or result.get('text')
        
        # Fallback to string conversion
        if value is None:
            value = str(result)
        
        # Redact sensitive values using the SelectorAttempt method
        return SelectorAttempt._redact_value(value)
    
    def _create_selector_attempt(
        self,
        selector_name: str,
        success: bool,
        result: Any,
        error: Optional[str],
        resolution_time_ms: float
    ) -> SelectorAttempt:
        """Create a SelectorAttempt from execution results."""
        if success:
            value = self._extract_value_for_log(result)
            return SelectorAttempt(
                name=selector_name,
                result="success",
                value=value,
                resolution_time_ms=resolution_time_ms
            )
        else:
            return SelectorAttempt(
                name=selector_name,
                result="failure",
                reason=error or "unknown",
                resolution_time_ms=resolution_time_ms
            )
    
    def log_fallback_attempt(
        self,
        fallback_result: FallbackResult,
        page_url: str,
        selector_id: Optional[str] = None
    ) -> FallbackAttemptLog:
        """
        Log a complete fallback chain attempt (AC1, AC2, AC3).
        
        Args:
            fallback_result: The result from fallback chain execution
            page_url: URL of the page being scraped
            selector_id: Optional selector ID (defaults to primary selector)
            
        Returns:
            FallbackAttemptLog with all attempt details
        """
        selector_id = selector_id or fallback_result.primary_selector
        
        # Build list of attempted selectors in order
        attempted_selectors: List[SelectorAttempt] = []
        
        # Add primary selector attempt
        primary_time_ms = fallback_result.chain_duration * 1000
        if fallback_result.primary_success:
            attempted_selectors.append(
                self._create_selector_attempt(
                    selector_name=fallback_result.primary_selector,
                    success=True,
                    result=fallback_result.final_result,
                    error=None,
                    resolution_time_ms=primary_time_ms
                )
            )
        else:
            # Primary failed - get failure reason
            failure_reason = "empty_result"
            if fallback_result.failure_event and fallback_result.failure_event.failure_type:
                failure_reason = fallback_result.failure_event.failure_type.value
            elif fallback_result.failure_event and fallback_result.failure_event.error_message:
                failure_reason = fallback_result.failure_event.error_message
            
            attempted_selectors.append(
                self._create_selector_attempt(
                    selector_name=fallback_result.primary_selector,
                    success=False,
                    result=None,
                    error=failure_reason,
                    resolution_time_ms=primary_time_ms
                )
            )
        
        # Add fallback selector attempts if executed
        if fallback_result.fallback_executed and fallback_result.fallback_attempt:
            fb_time_ms = fallback_result.fallback_attempt.resolution_time * 1000
            attempted_selectors.append(
                self._create_selector_attempt(
                    selector_name=fallback_result.fallback_attempt.fallback_selector,
                    success=fallback_result.fallback_success,
                    result=fallback_result.final_result if fallback_result.fallback_success else None,
                    error=fallback_result.fallback_attempt.error,
                    resolution_time_ms=fb_time_ms
                )
            )
        
        # Determine final result
        final_result = "success" if fallback_result.overall_success else "failure"
        
        # Create the log entry
        log_entry = FallbackAttemptLog(
            selector_id=selector_id,
            page_url=page_url,
            timestamp=datetime.now(timezone.utc),
            attempted_selectors=attempted_selectors,
            final_result=final_result,
            total_time_ms=fallback_result.chain_duration * 1000,
            correlation_id=self._get_correlation_id()
        )
        
        # Log with appropriate level
        if final_result == "success":
            self._logger.info(
                "fallback_attempt_success",
                extra=log_entry.to_dict()
            )
        else:
            self._logger.warning(
                "fallback_attempt_failure",
                extra=log_entry.to_dict()
            )
        
        return log_entry
    
    def log_primary_only_success(
        self,
        selector_id: str,
        page_url: str,
        result: Any,
        resolution_time_ms: float
    ) -> FallbackAttemptLog:
        """
        Log a primary selector success without fallback execution.
        
        Args:
            selector_id: The selector ID
            page_url: URL of the page being scraped
            result: The successful result
            resolution_time_ms: Time taken for resolution
            
        Returns:
            FallbackAttemptLog with success details
        """
        attempted_selectors = [
            self._create_selector_attempt(
                selector_name=selector_id,
                success=True,
                result=result,
                error=None,
                resolution_time_ms=resolution_time_ms
            )
        ]
        
        log_entry = FallbackAttemptLog(
            selector_id=selector_id,
            page_url=page_url,
            timestamp=datetime.now(timezone.utc),
            attempted_selectors=attempted_selectors,
            final_result="success",
            total_time_ms=resolution_time_ms,
            correlation_id=self._get_correlation_id()
        )
        
        self._logger.info(
            "primary_selector_success",
            extra=log_entry.to_dict()
        )
        
        return log_entry


# Module-level singleton for easy access
_fallback_logger: Optional[FallbackAttemptLogger] = None


def get_fallback_logger() -> FallbackAttemptLogger:
    """Get the singleton FallbackAttemptLogger instance."""
    global _fallback_logger
    if _fallback_logger is None:
        _fallback_logger = FallbackAttemptLogger()
    return _fallback_logger
