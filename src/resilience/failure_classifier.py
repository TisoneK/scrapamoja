"""
Failure Classification Logic

Classifies failures as transient or permanent based on error patterns,
status codes, and other characteristics to determine appropriate recovery strategies.
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from .models.failure_event import FailureCategory, FailureSeverity
from .exceptions import ResilienceException


class FailureType(Enum):
    """Classification of failure types."""
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class FailureClassifier:
    """Classifies failures based on patterns and characteristics."""
    
    def __init__(self):
        """Initialize failure classifier with default patterns."""
        # Transient failure patterns (temporary issues that can be resolved)
        self.transient_patterns = [
            r"timeout",
            r"connection.*refused",
            r"connection.*reset",
            r"connection.*timeout",
            r"network.*unreachable",
            r"host.*unreachable",
            r"temporary.*failure",
            r"service.*unavailable",
            r"rate.*limit",
            r"too.*many.*requests",
            r"throttled",
            r"socket.*timeout",
            r"read.*timeout",
            r"write.*timeout",
            r"operation.*timeout",
            r"resource.*temporarily.*unavailable",
            r"server.*busy",
            r"try.*again.*later",
            r"service.*overloaded",
            r"queue.*full",
            r"backpressure",
            r"circuit.*breaker.*open"
        ]
        
        # Permanent failure patterns (issues that won't resolve with retries)
        self.permanent_patterns = [
            r"404.*not.*found",
            r"403.*forbidden",
            r"401.*unauthorized",
            r"authentication.*failed",
            r"permission.*denied",
            r"access.*denied",
            r"invalid.*credentials",
            r"account.*locked",
            r"account.*suspended",
            r"api.*key.*invalid",
            r"quota.*exceeded",
            r"limit.*exceeded.*permanently",
            r"feature.*not.*available",
            r"endpoint.*not.*found",
            r"method.*not.*allowed",
            r"unsupported.*operation",
            r"invalid.*request",
            r"malformed.*request",
            r"schema.*validation.*failed",
            r"data.*validation.*failed",
            r"business.*logic.*error",
            r"configuration.*error",
            r"dependency.*missing",
            r"required.*field.*missing",
            r"invalid.*parameter",
            r"parsing.*error",
            r"syntax.*error"
        ]
        
        # HTTP status codes for retry decisions
        self.retryable_status_codes = [
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
            507,  # Insufficient Storage
            509,  # Bandwidth Limit Exceeded
            520,  # Unknown Error (Cloudflare)
            521,  # Web Server Is Down (Cloudflare)
            522,  # Connection Timed Out (Cloudflare)
            523,  # Origin Is Unreachable (Cloudflare)
            524,  # A Timeout Occurred (Cloudflare)
        ]
        
        self.non_retryable_status_codes = [
            400,  # Bad Request
            401,  # Unauthorized
            403,  # Forbidden
            404,  # Not Found
            405,  # Method Not Allowed
            406,  # Not Acceptable
            409,  # Conflict
            410,  # Gone
            413,  # Payload Too Large
            414,  # URI Too Long
            415,  # Unsupported Media Type
            416,  # Range Not Satisfiable
            417,  # Expectation Failed
            422,  # Unprocessable Entity
            423,  # Locked
            425,  # Too Early
            426,  # Upgrade Required
            428,  # Precondition Required
            429,  # Too Many Requests (sometimes retryable, depends on headers)
            431,  # Request Header Fields Too Large
            451,  # Unavailable For Legal Reasons
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_transient_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.transient_patterns
        ]
        self.compiled_permanent_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.permanent_patterns
        ]
    
    def classify_failure(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[FailureType, FailureCategory, FailureSeverity]:
        """
        Classify a failure as transient or permanent.
        
        Args:
            error: The exception to classify
            context: Additional context information
            
        Returns:
            Tuple of (failure_type, category, severity)
        """
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Check for permanent patterns first (more specific)
        if self._matches_permanent_patterns(error_message, error_type_name):
            return (
                FailureType.PERMANENT,
                self._determine_category(error, context),
                self._determine_severity(error, context, is_permanent=True)
            )
        
        # Check for transient patterns
        if self._matches_transient_patterns(error_message, error_type_name):
            return (
                FailureType.TRANSIENT,
                self._determine_category(error, context),
                self._determine_severity(error, context, is_permanent=False)
            )
        
        # Check HTTP status codes if available
        status_code = self._extract_status_code(error, context)
        if status_code:
            if status_code in self.retryable_status_codes:
                return (
                    FailureType.TRANSIENT,
                    FailureCategory.NETWORK,
                    self._determine_severity_from_status_code(status_code)
                )
            elif status_code in self.non_retryable_status_codes:
                return (
                    FailureType.PERMANENT,
                    FailureCategory.EXTERNAL,
                    self._determine_severity_from_status_code(status_code)
                )
        
        # Default classification based on error type
        return self._classify_by_error_type(error, context)
    
    def is_transient(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a failure is transient.
        
        Args:
            error: The exception to check
            context: Additional context information
            
        Returns:
            True if transient, False otherwise
        """
        failure_type, _, _ = self.classify_failure(error, context)
        return failure_type == FailureType.TRANSIENT
    
    def is_permanent(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a failure is permanent.
        
        Args:
            error: The exception to check
            context: Additional context information
            
        Returns:
            True if permanent, False otherwise
        """
        failure_type, _, _ = self.classify_failure(error, context)
        return failure_type == FailureType.PERMANENT
    
    def get_retry_recommendation(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get retry recommendation for a failure.
        
        Args:
            error: The exception to analyze
            context: Additional context information
            
        Returns:
            Retry recommendation with details
        """
        failure_type, category, severity = self.classify_failure(error, context)
        
        recommendation = {
            "should_retry": failure_type == FailureType.TRANSIENT,
            "failure_type": failure_type.value,
            "category": category.value,
            "severity": severity.value,
            "reason": self._get_classification_reason(error, context),
            "suggested_delay": self._get_suggested_delay(error, context),
            "max_retries": self._get_max_retries(error, context),
            "backoff_strategy": self._get_backoff_strategy(error, context)
        }
        
        return recommendation
    
    def _matches_transient_patterns(self, error_message: str, error_type_name: str) -> bool:
        """Check if error matches transient patterns."""
        # Check error message
        for pattern in self.compiled_transient_patterns:
            if pattern.search(error_message):
                return True
        
        # Check error type name
        for pattern in self.compiled_transient_patterns:
            if pattern.search(error_type_name):
                return True
        
        return False
    
    def _matches_permanent_patterns(self, error_message: str, error_type_name: str) -> bool:
        """Check if error matches permanent patterns."""
        # Check error message
        for pattern in self.compiled_permanent_patterns:
            if pattern.search(error_message):
                return True
        
        # Check error type name
        for pattern in self.compiled_permanent_patterns:
            if pattern.search(error_type_name):
                return True
        
        return False
    
    def _determine_category(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> FailureCategory:
        """Determine the failure category."""
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Check for network-related indicators
        network_indicators = [
            "connection", "network", "socket", "timeout", "http", "url",
            "request", "response", "dns", "proxy", "firewall"
        ]
        
        if any(indicator in error_message for indicator in network_indicators):
            return FailureCategory.NETWORK
        
        # Check for browser-related indicators
        browser_indicators = [
            "browser", "playwright", "page", "element", "selector",
            "click", "navigate", "screenshot", "javascript", "dom"
        ]
        
        if any(indicator in error_message for indicator in browser_indicators):
            return FailureCategory.BROWSER
        
        # Check for system-related indicators
        system_indicators = [
            "memory", "disk", "cpu", "process", "file", "permission",
            "oserror", "system", "resource"
        ]
        
        if any(indicator in error_message for indicator in system_indicators):
            return FailureCategory.SYSTEM
        
        # Check for external service indicators
        external_indicators = [
            "api", "service", "external", "third-party", "dependency"
        ]
        
        if any(indicator in error_message for indicator in external_indicators):
            return FailureCategory.EXTERNAL
        
        # Default to application
        return FailureCategory.APPLICATION
    
    def _determine_severity(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]],
        is_permanent: bool
    ) -> FailureSeverity:
        """Determine the failure severity."""
        error_message = str(error).lower()
        
        # Critical indicators
        critical_indicators = [
            "critical", "fatal", "crash", "corruption", "security",
            "authentication", "authorization", "permission denied"
        ]
        
        if any(indicator in error_message for indicator in critical_indicators):
            return FailureSeverity.CRITICAL
        
        # High severity indicators
        high_indicators = [
            "error", "exception", "failed", "failure", "unable",
            "cannot", "invalid", "malformed"
        ]
        
        if any(indicator in error_message for indicator in high_indicators):
            return FailureSeverity.HIGH
        
        # Medium severity for permanent failures
        if is_permanent:
            return FailureSeverity.MEDIUM
        
        # Low severity for transient issues
        low_indicators = [
            "warning", "slow", "degraded", "retry", "timeout"
        ]
        
        if any(indicator in error_message for indicator in low_indicators):
            return FailureSeverity.LOW
        
        # Default to medium
        return FailureSeverity.MEDIUM
    
    def _determine_severity_from_status_code(self, status_code: int) -> FailureSeverity:
        """Determine severity from HTTP status code."""
        if status_code >= 500:
            return FailureSeverity.HIGH
        elif status_code >= 400:
            return FailureSeverity.MEDIUM
        else:
            return FailureSeverity.LOW
    
    def _extract_status_code(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Optional[int]:
        """Extract HTTP status code from error or context."""
        # Check context first
        if context:
            status_code = context.get("status_code")
            if status_code is not None:
                return int(status_code)
        
        # Check error message for status codes
        error_message = str(error)
        import re
        status_match = re.search(r'\b([4-5]\d{2})\b', error_message)
        if status_match:
            return int(status_match.group(1))
        
        # Check error attributes
        if hasattr(error, 'status_code'):
            return error.status_code
        if hasattr(error, 'code'):
            return error.code
        
        return None
    
    def _classify_by_error_type(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[FailureType, FailureCategory, FailureSeverity]:
        """Classify failure based on error type when patterns don't match."""
        error_type_name = type(error).__name__
        
        # Network-related exceptions
        network_exceptions = [
            "ConnectionError", "TimeoutError", "HTTPError", "RequestException",
            "URLError", "SSLError", "ProxyError", "ConnectTimeout"
        ]
        
        if any(exc in error_type_name for exc in network_exceptions):
            return (
                FailureType.TRANSIENT,
                FailureCategory.NETWORK,
                FailureSeverity.MEDIUM
            )
        
        # Browser-related exceptions
        browser_exceptions = [
            "PlaywrightError", "TimeoutError", "ElementHandleError",
            "PageError", "BrowserError"
        ]
        
        if any(exc in error_type_name for exc in browser_exceptions):
            return (
                FailureType.TRANSIENT,
                FailureCategory.BROWSER,
                FailureSeverity.MEDIUM
            )
        
        # System-related exceptions
        system_exceptions = [
            "OSError", "IOError", "PermissionError", "FileNotFoundError",
            "MemoryError", "SystemError"
        ]
        
        if any(exc in error_type_name for exc in system_exceptions):
            return (
                FailureType.PERMANENT,
                FailureCategory.SYSTEM,
                FailureSeverity.HIGH
            )
        
        # Default classification
        return (
            FailureType.UNKNOWN,
            FailureCategory.APPLICATION,
            FailureSeverity.MEDIUM
        )
    
    def _get_classification_reason(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Get the reason for the classification."""
        failure_type, category, _ = self.classify_failure(error, context)
        
        if failure_type == FailureType.TRANSIENT:
            return "Failure appears to be temporary and may resolve with retries"
        elif failure_type == FailureType.PERMANENT:
            return "Failure appears to be permanent and retries are unlikely to succeed"
        else:
            return "Failure type could not be definitively classified"
    
    def _get_suggested_delay(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """Get suggested delay before retry."""
        failure_type, _, _ = self.classify_failure(error, context)
        
        if failure_type == FailureType.TRANSIENT:
            # Check for rate limiting
            error_message = str(error).lower()
            if "rate limit" in error_message or "too many requests" in error_message:
                return 60.0  # Longer delay for rate limiting
            
            # Check for timeout
            if "timeout" in error_message:
                return 5.0  # Moderate delay for timeouts
            
            return 1.0  # Default delay for other transient failures
        
        return 0.0  # No delay for permanent failures
    
    def _get_max_retries(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> int:
        """Get maximum number of retries recommended."""
        failure_type, _, _ = self.classify_failure(error, context)
        
        if failure_type == FailureType.TRANSIENT:
            error_message = str(error).lower()
            
            # More retries for rate limiting
            if "rate limit" in error_message:
                return 10
            
            # Standard retries for other transient failures
            return 5
        
        return 0  # No retries for permanent failures
    
    def _get_backoff_strategy(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Get recommended backoff strategy."""
        failure_type, _, _ = self.classify_failure(error, context)
        
        if failure_type == FailureType.TRANSIENT:
            error_message = str(error).lower()
            
            if "rate limit" in error_message:
                return "exponential_with_jitter"
            elif "timeout" in error_message:
                return "linear"
            else:
                return "exponential"
        
        return "none"


# Global failure classifier instance
_failure_classifier = FailureClassifier()


def classify_failure(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[FailureType, FailureCategory, FailureSeverity]:
    """Classify a failure using the global classifier."""
    return _failure_classifier.classify_failure(error, context)


def is_transient_failure(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """Check if a failure is transient using the global classifier."""
    return _failure_classifier.is_transient(error, context)


def is_permanent_failure(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """Check if a failure is permanent using the global classifier."""
    return _failure_classifier.is_permanent(error, context)


def get_retry_recommendation(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Get retry recommendation using the global classifier."""
    return _failure_classifier.get_retry_recommendation(error, context)
