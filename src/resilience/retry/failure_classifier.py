"""
Failure Classifier for Retry Operations

Specialized failure classification for retry decisions, focusing on
transient vs permanent failure detection with retry-specific patterns.
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from ..models.retry_policy import RetryCondition
from ..failure_classifier import FailureType, FailureCategory, FailureSeverity
from ..exceptions import RetryConfigurationError


class RetryDecision(Enum):
    """Retry decision outcomes."""
    RETRY = "retry"
    NO_RETRY = "no_retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_WITH_LIMIT = "retry_with_limit"
    CIRCUIT_BREAK = "circuit_break"


class RetryFailureClassifier:
    """Specialized failure classifier for retry operations."""
    
    def __init__(self):
        """Initialize retry failure classifier."""
        # Transient failure patterns specific to retry operations
        self.retry_transient_patterns = [
            # Network-related
            r"connection.*refused",
            r"connection.*reset",
            r"connection.*timeout",
            r"connection.*lost",
            r"network.*unreachable",
            r"host.*unreachable",
            r"dns.*resolution.*failed",
            r"socket.*timeout",
            r"socket.*error",
            r"ssl.*handshake.*failed",
            r"tls.*handshake.*failed",
            
            # HTTP-related
            r"timeout",
            r"request.*timeout",
            r"response.*timeout",
            r"read.*timeout",
            r"write.*timeout",
            r"operation.*timeout",
            r"502.*bad.*gateway",
            r"503.*service.*unavailable",
            r"504.*gateway.*timeout",
            r"507.*insufficient.*storage",
            r"509.*bandwidth.*limit.*exceeded",
            r"520.*unknown.*error",
            r"521.*web.*server.*down",
            r"522.*connection.*timed.*out",
            r"523.*origin.*unreachable",
            r"524.*a.*timeout.*occurred",
            
            # Rate limiting
            r"rate.*limit",
            r"too.*many.*requests",
            r"throttled",
            r"quota.*exceeded",
            r"limit.*exceeded",
            r"429.*too.*many.*requests",
            
            # Temporary service issues
            r"service.*unavailable",
            r"service.*temporarily.*unavailable",
            r"temporary.*failure",
            r"temporary.*error",
            r"try.*again.*later",
            r"service.*overloaded",
            r"server.*busy",
            r"queue.*full",
            r"backpressure",
            
            # Browser-specific
            r"browser.*timeout",
            r"page.*timeout",
            r"element.*not.*found.*temporary",
            r"selector.*timeout",
            r"navigation.*timeout",
            r"load.*timeout",
            r"script.*timeout",
            r"playwright.*timeout",
            
            # System-related
            r"resource.*temporarily.*unavailable",
            r"system.*temporarily.*unavailable",
            r"disk.*full.*temporary",
            r"memory.*pressure",
            r"cpu.*overload",
            r"process.*busy"
        ]
        
        # Permanent failure patterns specific to retry operations
        self.retry_permanent_patterns = [
            # Authentication/Authorization
            r"401.*unauthorized",
            r"403.*forbidden",
            r"authentication.*failed",
            r"authorization.*failed",
            r"access.*denied",
            r"permission.*denied",
            r"invalid.*credentials",
            r"invalid.*token",
            r"token.*expired",
            r"account.*locked",
            r"account.*suspended",
            r"api.*key.*invalid",
            r"api.*key.*expired",
            
            # Not found
            r"404.*not.*found",
            r"410.*gone",
            r"resource.*not.*found",
            r"endpoint.*not.*found",
            r"page.*not.*found",
            r"element.*not.*found",
            r"selector.*not.*found",
            
            # Client errors
            r"400.*bad.*request",
            r"405.*method.*not.*allowed",
            r"406.*not.*acceptable",
            r"409.*conflict",
            r"413.*payload.*too.*large",
            r"414.*uri.*too.*long",
            r"415.*unsupported.*media.*type",
            r"416.*range.*not.*satisfiable",
            r"417.*expectation.*failed",
            r"422.*unprocessable.*entity",
            r"423.*locked",
            r"425.*too.*early",
            r"426.*upgrade.*required",
            r"428.*precondition.*required",
            r"431.*request.*header.*fields.*too.*large",
            r"451.*unavailable.*for.*legal.*reasons",
            
            # Configuration/Validation errors
            r"invalid.*request",
            r"malformed.*request",
            r"schema.*validation.*failed",
            r"data.*validation.*failed",
            r"parameter.*missing",
            r"parameter.*invalid",
            r"required.*field.*missing",
            r"business.*logic.*error",
            r"configuration.*error",
            r"dependency.*missing",
            r"invalid.*parameter",
            r"parsing.*error",
            r"syntax.*error",
            
            # Browser-specific permanent errors
            r"browser.*crashed",
            r"browser.*closed",
            r"page.*crashed",
            r"context.*destroyed",
            r"target.*closed",
            r"session.*closed",
            r"connection.*closed",
            
            # System permanent errors
            r"file.*not.*found",
            r"directory.*not.*found",
            r"permission.*denied",
            r"access.*denied",
            r"disk.*full",
            r"out.*of.*memory",
            r"system.*error",
            r"operating.*system.*error",
            r"hardware.*error"
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_transient_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.retry_transient_patterns
        ]
        self.compiled_permanent_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.retry_permanent_patterns
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
            431,  # Request Header Fields Too Large
            451,  # Unavailable For Legal Reasons
        ]
    
    def classify_for_retry(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[RetryDecision, Dict[str, Any]]:
        """
        Classify a failure for retry decision.
        
        Args:
            error: The exception to classify
            context: Additional context information
            
        Returns:
            Tuple of (retry_decision, classification_details)
        """
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Extract status code if available
        status_code = self._extract_status_code(error, context)
        
        # Check permanent patterns first (more specific)
        if self._matches_permanent_patterns(error_message, error_type_name):
            return (
                RetryDecision.NO_RETRY,
                {
                    "failure_type": "permanent",
                    "reason": "Permanent failure pattern detected",
                    "status_code": status_code,
                    "recommendation": "Do not retry"
                }
            )
        
        # Check transient patterns
        if self._matches_transient_patterns(error_message, error_type_name):
            return (
                RetryDecision.RETRY_WITH_BACKOFF,
                {
                    "failure_type": "transient",
                    "reason": "Transient failure pattern detected",
                    "status_code": status_code,
                    "recommendation": "Retry with backoff"
                }
            )
        
        # Check HTTP status codes
        if status_code:
            if status_code in self.retryable_status_codes:
                return (
                    RetryDecision.RETRY_WITH_BACKOFF,
                    {
                        "failure_type": "transient",
                        "reason": f"Retryable HTTP status code: {status_code}",
                        "status_code": status_code,
                        "recommendation": "Retry with backoff"
                    }
                )
            elif status_code in self.non_retryable_status_codes:
                return (
                    RetryDecision.NO_RETRY,
                    {
                        "failure_type": "permanent",
                        "reason": f"Non-retryable HTTP status code: {status_code}",
                        "status_code": status_code,
                        "recommendation": "Do not retry"
                    }
                )
        
        # Default classification based on error type
        return self._classify_by_error_type_for_retry(error, context)
    
    def should_retry(
        self,
        error: Exception,
        retry_conditions: List[RetryCondition],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if an error should be retried based on conditions.
        
        Args:
            error: The exception to check
            retry_conditions: List of retry conditions
            context: Additional context
            
        Returns:
            True if should retry, False otherwise
        """
        if not retry_conditions:
            return True
        
        retry_decision, details = self.classify_for_retry(error, context)
        
        for condition in retry_conditions:
            if condition == RetryCondition.TRANSIENT_FAILURE:
                if details["failure_type"] == "transient":
                    return True
            elif condition == RetryCondition.SPECIFIC_ERROR_CODES:
                status_code = self._extract_status_code(error, context)
                if status_code and status_code in self.retryable_status_codes:
                    return True
            elif condition == RetryCondition.TIME_BASED:
                # Time-based conditions would be checked by the retry manager
                return True
            elif condition == RetryCondition.CUSTOM:
                # Custom conditions would be checked by the retry manager
                if context and context.get("custom_retry_condition", False):
                    return True
        
        return False
    
    def get_retry_recommendation(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed retry recommendation for a failure.
        
        Args:
            error: The exception to analyze
            context: Additional context information
            
        Returns:
            Detailed retry recommendation
        """
        retry_decision, details = self.classify_for_retry(error, context)
        
        recommendation = {
            "should_retry": retry_decision in [RetryDecision.RETRY, RetryDecision.RETRY_WITH_BACKOFF, RetryDecision.RETRY_WITH_LIMIT],
            "retry_decision": retry_decision.value,
            "failure_type": details["failure_type"],
            "reason": details["reason"],
            "recommendation": details["recommendation"],
            "status_code": details.get("status_code"),
            "suggested_backoff": self._get_suggested_backoff(error, context),
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
        status_match = re.search(r'\b([4-5]\d{2})\b', error_message)
        if status_match:
            return int(status_match.group(1))
        
        # Check error attributes
        if hasattr(error, 'status_code'):
            return error.status_code
        if hasattr(error, 'code'):
            return error.code
        
        return None
    
    def _classify_by_error_type_for_retry(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[RetryDecision, Dict[str, Any]]:
        """Classify failure based on error type for retry decisions."""
        error_type_name = type(error).__name__
        
        # Network-related exceptions
        network_exceptions = [
            "ConnectionError", "TimeoutError", "HTTPError", "RequestException",
            "URLError", "SSLError", "ProxyError", "ConnectTimeout"
        ]
        
        if any(exc in error_type_name for exc in network_exceptions):
            return (
                RetryDecision.RETRY_WITH_BACKOFF,
                {
                    "failure_type": "transient",
                    "reason": "Network-related exception",
                    "recommendation": "Retry with exponential backoff"
                }
            )
        
        # Browser-related exceptions
        browser_exceptions = [
            "PlaywrightError", "TimeoutError", "ElementHandleError",
            "PageError", "BrowserError"
        ]
        
        if any(exc in error_type_name for exc in browser_exceptions):
            return (
                RetryDecision.RETRY_WITH_BACKOFF,
                {
                    "failure_type": "transient",
                    "reason": "Browser-related exception",
                    "recommendation": "Retry with backoff"
                }
            )
        
        # System-related exceptions
        system_exceptions = [
            "OSError", "IOError", "PermissionError", "FileNotFoundError",
            "MemoryError", "SystemError"
        ]
        
        if any(exc in error_type_name for exc in system_exceptions):
            return (
                RetryDecision.NO_RETRY,
                {
                    "failure_type": "permanent",
                    "reason": "System-related exception",
                    "recommendation": "Do not retry"
                }
            )
        
        # Default classification
        return (
            RetryDecision.RETRY_WITH_LIMIT,
            {
                "failure_type": "unknown",
                "reason": "Unknown error type",
                "recommendation": "Retry with limited attempts"
            }
        )
    
    def _get_suggested_backoff(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get suggested backoff configuration."""
        error_message = str(error).lower()
        
        # Check for rate limiting
        if "rate limit" in error_message or "too many requests" in error_message:
            return {
                "strategy": "exponential_with_jitter",
                "base_delay": 60.0,
                "max_delay": 300.0,
                "multiplier": 2.0,
                "jitter_factor": 0.2
            }
        
        # Check for timeout
        if "timeout" in error_message:
            return {
                "strategy": "exponential_with_jitter",
                "base_delay": 2.0,
                "max_delay": 60.0,
                "multiplier": 2.0,
                "jitter_factor": 0.1
            }
        
        # Default backoff
        return {
            "strategy": "exponential_with_jitter",
            "base_delay": 1.0,
            "max_delay": 30.0,
            "multiplier": 2.0,
            "jitter_factor": 0.1
        }
    
    def _get_max_retries(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> int:
        """Get maximum number of retries recommended."""
        error_message = str(error).lower()
        
        # More retries for rate limiting
        if "rate limit" in error_message:
            return 10
        
        # Standard retries for other transient failures
        if "timeout" in error_message:
            return 5
        
        # Default retries
        return 3
    
    def _get_backoff_strategy(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Get recommended backoff strategy."""
        error_message = str(error).lower()
        
        if "rate limit" in error_message:
            return "exponential_with_jitter"
        elif "timeout" in error_message:
            return "exponential_with_jitter"
        else:
            return "exponential"


# Global retry failure classifier instance
_retry_failure_classifier = RetryFailureClassifier()


def classify_for_retry(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[RetryDecision, Dict[str, Any]]:
    """Classify a failure for retry decision using the global classifier."""
    return _retry_failure_classifier.classify_for_retry(error, context)


def should_retry(
    error: Exception,
    retry_conditions: List[RetryCondition],
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """Check if an error should be retried using the global classifier."""
    return _retry_failure_classifier.should_retry(error, retry_conditions, context)


def get_retry_recommendation(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Get retry recommendation using the global classifier."""
    return _retry_failure_classifier.get_retry_recommendation(error, context)
