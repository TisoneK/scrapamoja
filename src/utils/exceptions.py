"""
Exception hierarchy for Selector Engine.

Provides specific exception types for different failure scenarios as required
by the API contracts and for proper error handling throughout the system.
"""

from typing import Optional, Dict, Any


class SelectorEngineError(Exception):
    """Base exception for selector engine."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        """String representation with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class SelectorNotFoundError(SelectorEngineError):
    """Raised when selector is not found."""
    
    def __init__(self, selector_name: str, context: Optional[Dict[str, Any]] = None):
        self.selector_name = selector_name
        message = f"Selector not found: {selector_name}"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        return f"Selector '{self.selector_name}' not found in registry"


class ResolutionTimeoutError(SelectorEngineError):
    """Raised when resolution times out."""
    
    def __init__(self, selector_name: str, timeout: float, 
                 strategy_used: str = "unknown", context: Optional[Dict[str, Any]] = None):
        self.selector_name = selector_name
        self.timeout = timeout
        self.strategy_used = strategy_used
        message = f"Resolution timeout for {selector_name}: {timeout}ms (strategy: {strategy_used})"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        return (f"Selector '{self.selector_name}' resolution timed out after "
                f"{self.timeout}ms using strategy '{self.strategy_used}'")


class ConfidenceThresholdError(SelectorEngineError):
    """Raised when confidence threshold is not met."""
    
    def __init__(self, selector_name: str, confidence: float, threshold: float,
                 strategy_used: str = "unknown", context: Optional[Dict[str, Any]] = None):
        self.selector_name = selector_name
        self.confidence = confidence
        self.threshold = threshold
        self.strategy_used = strategy_used
        message = (f"Confidence {confidence} below threshold {threshold} "
                   f"for {selector_name} (strategy: {strategy_used})")
        super().__init__(message, context)
    
    def __str__(self) -> str:
        return (f"Selector '{self.selector_name}' confidence {self.confidence:.3f} "
                f"is below threshold {self.threshold:.3f} "
                f"(strategy: '{self.strategy_used}')")


class ContextValidationError(SelectorEngineError):
    """Raised when tab context validation fails."""
    
    def __init__(self, context: str, reason: str, 
                 selector_name: Optional[str] = None, 
                 context_data: Optional[Dict[str, Any]] = None):
        self.context = context
        self.reason = reason
        self.selector_name = selector_name
        self.context_data = context_data or {}
        message = f"Context validation failed for {context}: {reason}"
        if selector_name:
            message += f" (selector: {selector_name})"
        super().__init__(message, context_data)
    
    def __str__(self) -> str:
        base_msg = f"Tab context '{self.context}' validation failed: {self.reason}"
        if self.selector_name:
            base_msg += f" (selector: '{self.selector_name}')"
        return base_msg


class SnapshotError(SelectorEngineError):
    """Raised when snapshot operations fail."""
    
    def __init__(self, operation: str, reason: str, 
                 selector_name: Optional[str] = None,
                 snapshot_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.reason = reason
        self.selector_name = selector_name
        self.snapshot_id = snapshot_id
        message = f"Snapshot {operation} failed: {reason}"
        if selector_name:
            message += f" (selector: {selector_name})"
        if snapshot_id:
            message += f" (snapshot: {snapshot_id})"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        parts = [f"Snapshot {self.operation} failed: {self.reason}"]
        if self.selector_name:
            parts.append(f"selector: '{self.selector_name}'")
        if self.snapshot_id:
            parts.append(f"snapshot: '{self.snapshot_id}'")
        return ", ".join(parts)


class StrategyExecutionError(SelectorEngineError):
    """Raised when strategy execution fails."""
    
    def __init__(self, strategy_id: str, selector_name: str, error: str,
                 execution_time: Optional[float] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.strategy_id = strategy_id
        self.selector_name = selector_name
        self.error = error
        self.execution_time = execution_time
        message = f"Strategy '{strategy_id}' execution failed for {selector_name}: {error}"
        if execution_time is not None:
            message += f" (time: {execution_time}ms)"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        base_msg = (f"Strategy '{self.strategy_id}' failed for selector "
                    f"'{self.selector_name}': {self.error}")
        if self.execution_time is not None:
            base_msg += f" (execution time: {self.execution_time}ms)"
        return base_msg


class ValidationError(SelectorEngineError):
    """Raised when content validation fails."""
    
    def __init__(self, selector_name: str, validation_type: str, 
                 rule_pattern: str, reason: str,
                 element_content: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.selector_name = selector_name
        self.validation_type = validation_type
        self.rule_pattern = rule_pattern
        self.reason = reason
        self.element_content = element_content
        message = (f"Validation failed for {selector_name}: {validation_type} "
                   f"rule '{rule_pattern}' - {reason}")
        super().__init__(message, context)
    
    def __str__(self) -> str:
        return (f"Validation failed for selector '{self.selector_name}': "
                f"{self.validation_type} rule '{self.rule_pattern}' - {self.reason}")


class ConfigurationError(SelectorEngineError):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_section: str, parameter: str, reason: str,
                 current_value: Optional[Any] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.config_section = config_section
        self.parameter = parameter
        self.reason = reason
        self.current_value = current_value
        message = f"Configuration error in {config_section}.{parameter}: {reason}"
        if current_value is not None:
            message += f" (current value: {current_value})"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        base_msg = f"Configuration error in {self.config_section}.{self.parameter}: {self.reason}"
        if self.current_value is not None:
            base_msg += f" (current value: {self.current_value})"
        return base_msg


class DriftDetectionError(SelectorEngineError):
    """Raised when drift detection operations fail."""
    
    def __init__(self, selector_name: str, operation: str, reason: str,
                 time_range: Optional[tuple] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.selector_name = selector_name
        self.operation = operation
        self.reason = reason
        self.time_range = time_range
        message = f"Drift detection {operation} failed for {selector_name}: {reason}"
        if time_range:
            message += f" (range: {time_range[0]} to {time_range[1]})"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        base_msg = f"Drift detection {self.operation} failed for '{self.selector_name}': {self.reason}"
        if self.time_range:
            base_msg += f" (time range: {self.time_range[0]} to {self.time_range[1]})"
        return base_msg


class PerformanceError(SelectorEngineError):
    """Raised when performance thresholds are exceeded."""
    
    def __init__(self, metric_name: str, actual_value: float, threshold: float,
                 selector_name: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.metric_name = metric_name
        self.actual_value = actual_value
        self.threshold = threshold
        self.selector_name = selector_name
        message = (f"Performance threshold exceeded for {metric_name}: "
                   f"{actual_value} > {threshold}")
        if selector_name:
            message += f" (selector: {selector_name})"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        base_msg = (f"Performance threshold exceeded for {self.metric_name}: "
                    f"{self.actual_value} > {self.threshold}")
        if self.selector_name:
            base_msg += f" (selector: '{self.selector_name}')"
        return base_msg


class StorageError(SelectorEngineError):
    """Raised when storage operations fail."""
    
    def __init__(self, operation: str, resource_type: str, resource_id: str,
                 reason: str, context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.reason = reason
        message = f"Storage {operation} failed for {resource_type} {resource_id}: {reason}"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        return (f"Storage {self.operation} failed for {self.resource_type} "
                f"'{self.resource_id}': {self.reason}")


class EvolutionError(SelectorEngineError):
    """Raised when strategy evolution operations fail."""
    
    def __init__(self, selector_name: str, operation: str, reason: str,
                 strategy_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.selector_name = selector_name
        self.operation = operation
        self.reason = reason
        self.strategy_id = strategy_id
        message = f"Strategy evolution {operation} failed for {selector_name}: {reason}"
        if strategy_id:
            message += f" (strategy: {strategy_id})"
        super().__init__(message, context)
    
    def __str__(self) -> str:
        base_msg = f"Strategy evolution {self.operation} failed for '{self.selector_name}': {self.reason}"
        if self.strategy_id:
            base_msg += f" (strategy: '{self.strategy_id}')"
        return base_msg


# Exception factory functions for convenience
def create_selector_not_found_error(selector_name: str, **context) -> SelectorNotFoundError:
    """Create SelectorNotFoundError with context."""
    return SelectorNotFoundError(selector_name, context)


def create_timeout_error(selector_name: str, timeout: float, strategy: str = "unknown", **context) -> ResolutionTimeoutError:
    """Create ResolutionTimeoutError with context."""
    return ResolutionTimeoutError(selector_name, timeout, strategy, context)


def create_confidence_error(selector_name: str, confidence: float, threshold: float, 
                          strategy: str = "unknown", **context) -> ConfidenceThresholdError:
    """Create ConfidenceThresholdError with context."""
    return ConfidenceThresholdError(selector_name, confidence, threshold, strategy, context)


def create_context_error(context: str, reason: str, selector_name: str = None, **context_data) -> ContextValidationError:
    """Create ContextValidationError with context."""
    return ContextValidationError(context, reason, selector_name, context_data)


def create_snapshot_error(operation: str, reason: str, selector_name: str = None, 
                         snapshot_id: str = None, **context) -> SnapshotError:
    """Create SnapshotError with context."""
    return SnapshotError(operation, reason, selector_name, snapshot_id, context)


def create_strategy_error(strategy_id: str, selector_name: str, error: str, 
                         execution_time: float = None, **context) -> StrategyExecutionError:
    """Create StrategyExecutionError with context."""
    return StrategyExecutionError(strategy_id, selector_name, error, execution_time, context)


# Exception handling utilities
def is_selector_error(exception: Exception) -> bool:
    """Check if exception is a selector engine error."""
    return isinstance(exception, SelectorEngineError)


def is_recoverable_error(exception: Exception) -> bool:
    """Check if exception is recoverable (can retry)."""
    recoverable_types = [
        ResolutionTimeoutError,
        StrategyExecutionError,
        SnapshotError,
        PerformanceError
    ]
    return isinstance(exception, tuple(recoverable_types))


def is_fatal_error(exception: Exception) -> bool:
    """Check if exception is fatal (should stop processing)."""
    fatal_types = [
        ConfigurationError,
        SelectorNotFoundError,
        ContextValidationError
    ]
    return isinstance(exception, tuple(fatal_types))


class QualityControlError(SelectorEngineError):
    """Raised when quality control evaluation fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, context)


class ConfidenceValidationError(ValidationError):
    """Raised when confidence score validation fails."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, context=details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class TabContextError(SelectorEngineError):
    """Raised when tab context operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, context=details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class BrowserError(Exception):
    """Base exception for browser-related errors."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class BrowserSessionError(BrowserError):
    """Raised when browser session operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class BrowserManagerError(BrowserError):
    """Raised when browser manager operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.details = details or {}


class BrowserStateError(BrowserError):
    """Raised when browser state operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.details = details or {}


def get_error_severity(exception: Exception) -> str:
    """Get error severity level for logging."""
    if is_fatal_error(exception):
        return "FATAL"
    elif is_recoverable_error(exception):
        return "WARNING"
    elif isinstance(exception, SelectorEngineError):
        return "ERROR"
    else:
        return "CRITICAL"
