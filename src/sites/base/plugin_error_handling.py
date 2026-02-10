"""
Plugin error handling system for the plugin framework.

This module provides comprehensive error handling, recovery, and reporting
for plugin operations, including error classification, retry logic, and
failure analysis.
"""

import asyncio
import traceback
import logging
from typing import Dict, Any, List, Optional, Callable, Type, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import weakref
import json

from .plugin_interface import IPlugin, PluginContext, PluginResult, PluginStatus, HookType


class ErrorSeverity(Enum):
    """Error severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category enumeration."""
    INITIALIZATION = "initialization"
    EXECUTION = "execution"
    CONFIGURATION = "configuration"
    PERMISSION = "permission"
    RESOURCE = "resource"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    DEPENDENCY = "dependency"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Recovery action enumeration."""
    RETRY = "retry"
    RESTART = "restart"
    DISABLE = "disable"
    FALLBACK = "fallback"
    IGNORE = "ignore"
    ESCALATE = "escalate"


@dataclass
class PluginError:
    """Plugin error information."""
    plugin_id: str
    error_id: str
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class ErrorPattern:
    """Error pattern for classification."""
    pattern_id: str
    name: str
    description: str
    error_types: List[str]
    patterns: List[str]  # Regex patterns to match
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_actions: List[RecoveryAction]
    retry_config: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: List[ErrorCategory] = field(default_factory=lambda: [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT])


@dataclass
class ErrorReport:
    """Error report for analysis."""
    report_id: str
    plugin_id: str
    time_range: Dict[str, datetime]
    error_count: int
    errors: List[PluginError]
    patterns: List[ErrorPattern]
    recovery_success_rate: float
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class PluginErrorHandler:
    """Plugin error handler."""
    
    def __init__(self):
        """Initialize plugin error handler."""
        # Error storage
        self._errors: Dict[str, List[PluginError]] = {}
        self._error_patterns: Dict[str, ErrorPattern] = {}
        self._recovery_strategies: Dict[str, Callable] = {}
        
        # Retry configuration
        self._default_retry_config = RetryConfig()
        self._plugin_retry_configs: Dict[str, RetryConfig] = {}
        
        # Error statistics
        self._stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }
        
        # Event listeners
        self._error_listeners: List[Callable] = []
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Initialize built-in error patterns
        self._initialize_builtin_patterns()
        
        # Initialize recovery strategies
        self._initialize_recovery_strategies()
    
    def _initialize_builtin_patterns(self) -> None:
        """Initialize built-in error patterns."""
        # Network errors
        self.add_error_pattern(ErrorPattern(
            pattern_id="network_timeout",
            name="Network Timeout",
            description="Network operation timeout",
            error_types=["TimeoutError", "asyncio.TimeoutError"],
            patterns=[r"timeout", r"connection.*timeout", r"network.*timeout"],
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.RETRY],
            retry_config={"max_attempts": 3, "base_delay_seconds": 2.0}
        ))
        
        self.add_error_pattern(ErrorPattern(
            pattern_id="connection_refused",
            name="Connection Refused",
            description="Connection refused by server",
            error_types=["ConnectionRefusedError", "ConnectionError"],
            patterns=[r"connection.*refused", r"connection.*failed"],
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.FALLBACK]
        ))
        
        # File system errors
        self.add_error_pattern(ErrorPattern(
            pattern_id="file_not_found",
            name="File Not Found",
            description="File or directory not found",
            error_types=["FileNotFoundError", "FileNotFoundError"],
            patterns=[r"file.*not.*found", r"no.*such.*file", r"directory.*not.*found"],
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.FALLBACK, RecoveryAction.IGNORE]
        ))
        
        self.add_error_pattern(ErrorPattern(
            pattern_id="permission_denied",
            name="Permission Denied",
            description="Permission denied for operation",
            error_types=["PermissionError", "OSError"],
            patterns=[r"permission.*denied", r"access.*denied", r"operation.*not.*permitted"],
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.HIGH,
            recovery_actions=[RecoveryAction.ESCALATE, RecoveryAction.DISABLE]
        ))
        
        # Resource errors
        self.add_error_pattern(ErrorPattern(
            pattern_id="memory_error",
            name="Memory Error",
            description="Out of memory or memory allocation failed",
            error_types=["MemoryError", "OutOfMemoryError"],
            patterns=[r"memory.*error", r"out.*of.*memory", r"allocation.*failed"],
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            recovery_actions=[RecoveryAction.RESTART, RecoveryAction.DISABLE]
        ))
        
        # Configuration errors
        self.add_error_pattern(ErrorPattern(
            pattern_id="config_validation",
            name="Configuration Validation Error",
            description="Configuration validation failed",
            error_types=["ValueError", "ValidationError"],
            patterns=[r"validation.*failed", r"invalid.*config", r"config.*error"],
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.MEDIUM,
            recovery_actions=[RecoveryAction.FALLBACK, RecoveryAction.ESCALATE]
        ))
    
    def _initialize_recovery_strategies(self) -> None:
        """Initialize recovery strategies."""
        self._recovery_strategies[RecoveryAction.RETRY] = self._retry_recovery
        self._recovery_strategies[RecoveryAction.RESTART] = self._restart_recovery
        self._recovery_strategies[RecoveryAction.DISABLE] = self._disable_recovery
        self._recovery_strategies[RecoveryAction.FALLBACK] = self._fallback_recovery
        self._recovery_strategies[RecoveryAction.IGNORE] = self._ignore_recovery
        self._recovery_strategies[RecoveryAction.ESCALATE] = self._escalate_recovery
    
    async def handle_error(self, plugin_id: str, error: Exception, 
                          context: Optional[Dict[str, Any]] = None) -> PluginError:
        """
        Handle a plugin error.
        
        Args:
            plugin_id: Plugin ID
            error: Exception that occurred
            context: Additional context information
            
        Returns:
            Plugin error object
        """
        # Create error object
        plugin_error = PluginError(
            plugin_id=plugin_id,
            error_id=f"{plugin_id}_{int(datetime.utcnow().timestamp())}",
            error_type=type(error).__name__,
            message=str(error),
            category=self._classify_error(error),
            severity=self._determine_severity(error),
            traceback=traceback.format_exc(),
            context=context or {},
            metadata={
                'error_class': error.__class__.__name__,
                'error_module': error.__class__.__module__
            }
        )
        
        # Store error
        async with self._lock:
            if plugin_id not in self._errors:
                self._errors[plugin_id] = []
            self._errors[plugin_id].append(plugin_error)
            
            # Update statistics
            self._update_statistics(plugin_error)
        
        # Notify listeners
        await self._notify_error_listeners(plugin_error)
        
        # Attempt recovery
        await self._attempt_recovery(plugin_error)
        
        return plugin_error
    
    def add_error_pattern(self, pattern: ErrorPattern) -> None:
        """Add an error pattern."""
        self._error_patterns[pattern.pattern_id] = pattern
    
    def remove_error_pattern(self, pattern_id: str) -> bool:
        """Remove an error pattern."""
        if pattern_id in self._error_patterns:
            del self._error_patterns[pattern_id]
            return True
        return False
    
    def get_error_pattern(self, pattern_id: str) -> Optional[ErrorPattern]:
        """Get an error pattern by ID."""
        return self._error_patterns.get(pattern_id)
    
    def get_all_error_patterns(self) -> Dict[str, ErrorPattern]:
        """Get all error patterns."""
        return self._error_patterns.copy()
    
    def set_retry_config(self, plugin_id: str, config: RetryConfig) -> None:
        """Set retry configuration for a plugin."""
        self._plugin_retry_configs[plugin_id] = config
    
    def get_retry_config(self, plugin_id: str) -> RetryConfig:
        """Get retry configuration for a plugin."""
        return self._plugin_retry_configs.get(plugin_id, self._default_retry_config)
    
    def get_plugin_errors(self, plugin_id: str, 
                         limit: Optional[int] = None,
                         since: Optional[datetime] = None) -> List[PluginError]:
        """Get errors for a plugin."""
        errors = self._errors.get(plugin_id, [])
        
        # Filter by time
        if since:
            errors = [error for error in errors if error.timestamp >= since]
        
        # Limit results
        if limit:
            errors = errors[-limit:]
        
        return errors
    
    def get_all_errors(self, limit: Optional[int] = None,
                      since: Optional[datetime] = None) -> Dict[str, List[PluginError]]:
        """Get all errors."""
        all_errors = {}
        
        for plugin_id, errors in self._errors.items():
            filtered_errors = errors
            
            # Filter by time
            if since:
                filtered_errors = [error for error in filtered_errors if error.timestamp >= since]
            
            # Limit results
            if limit:
                filtered_errors = filtered_errors[-limit:]
            
            if filtered_errors:
                all_errors[plugin_id] = filtered_errors
        
        return all_errors
    
    def clear_errors(self, plugin_id: Optional[str] = None,
                    before: Optional[datetime] = None) -> int:
        """Clear errors."""
        cleared_count = 0
        
        if plugin_id:
            # Clear errors for specific plugin
            if plugin_id in self._errors:
                if before:
                    original_count = len(self._errors[plugin_id])
                    self._errors[plugin_id] = [
                        error for error in self._errors[plugin_id]
                        if error.timestamp >= before
                    ]
                    cleared_count = original_count - len(self._errors[plugin_id])
                else:
                    cleared_count = len(self._errors[plugin_id])
                    del self._errors[plugin_id]
        else:
            # Clear all errors
            if before:
                for pid in list(self._errors.keys()):
                    original_count = len(self._errors[pid])
                    self._errors[pid] = [
                        error for error in self._errors[pid]
                        if error.timestamp >= before
                    ]
                    cleared_count += original_count - len(self._errors[pid])
                    
                    # Remove empty lists
                    if not self._errors[pid]:
                        del self._errors[pid]
            else:
                for errors in self._errors.values():
                    cleared_count += len(errors)
                self._errors.clear()
        
        return cleared_count
    
    def generate_error_report(self, plugin_id: Optional[str] = None,
                            time_range_hours: int = 24) -> ErrorReport:
        """Generate error report."""
        now = datetime.utcnow()
        time_range = {
            'start': now - timedelta(hours=time_range_hours),
            'end': now
        }
        
        # Collect errors
        all_errors = []
        if plugin_id:
            errors = self.get_plugin_errors(plugin_id, since=time_range['start'])
            all_errors.extend(errors)
        else:
            for pid, errors in self.get_all_errors(since=time_range['start']).items():
                all_errors.extend(errors)
        
        # Analyze patterns
        patterns = self._analyze_error_patterns(all_errors)
        
        # Calculate recovery success rate
        recovery_attempts = sum(error.recovery_attempts for error in all_errors)
        successful_recoveries = sum(1 for error in all_errors if error.resolved)
        recovery_success_rate = successful_recoveries / recovery_attempts if recovery_attempts > 0 else 0.0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_errors, patterns)
        
        return ErrorReport(
            report_id=f"report_{int(now.timestamp())}",
            plugin_id=plugin_id or "all",
            time_range=time_range,
            error_count=len(all_errors),
            errors=all_errors,
            patterns=patterns,
            recovery_success_rate=recovery_success_rate,
            recommendations=recommendations
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        stats = self._stats.copy()
        
        # Add error counts by plugin
        stats['errors_by_plugin'] = {
            plugin_id: len(errors) for plugin_id, errors in self._errors.items()
        }
        
        # Add recent error trends
        recent_time = datetime.utcnow() - timedelta(hours=1)
        recent_errors = 0
        for errors in self._errors.values():
            recent_errors += len([error for error in errors if error.timestamp >= recent_time])
        
        stats['recent_errors_last_hour'] = recent_errors
        
        return stats
    
    def add_error_listener(self, listener: Callable[[PluginError], None]) -> None:
        """Add an error listener."""
        self._error_listeners.append(listener)
    
    def remove_error_listener(self, listener: Callable[[PluginError], None]) -> bool:
        """Remove an error listener."""
        try:
            self._error_listeners.remove(listener)
            return True
        except ValueError:
            return False
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify an error into a category."""
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Check against patterns
        for pattern in self._error_patterns.values():
            if error_type in pattern.error_types:
                return pattern.category
            
            for pattern_str in pattern.patterns:
                if pattern_str.lower() in error_message:
                    return pattern.category
        
        # Default classification based on exception type
        if "timeout" in error_type.lower() or "timeout" in error_message:
            return ErrorCategory.TIMEOUT
        elif "connection" in error_type.lower() or "network" in error_type.lower():
            return ErrorCategory.NETWORK
        elif "file" in error_type.lower() or "path" in error_type.lower():
            return ErrorCategory.FILE_SYSTEM
        elif "permission" in error_type.lower() or "access" in error_type.lower():
            return ErrorCategory.PERMISSION
        elif "memory" in error_type.lower() or "resource" in error_type.lower():
            return ErrorCategory.RESOURCE
        elif "config" in error_type.lower() or "validation" in error_type.lower():
            return ErrorCategory.CONFIGURATION
        elif "import" in error_type.lower() or "module" in error_type.lower():
            return ErrorCategory.DEPENDENCY
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity."""
        error_type = type(error).__name__
        
        # Critical errors
        if error_type in ["SystemExit", "KeyboardInterrupt", "MemoryError"]:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if error_type in ["PermissionError", "OSError", "RuntimeError"]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if error_type in ["ValueError", "KeyError", "AttributeError", "ConnectionError"]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        if error_type in ["Warning", "UserWarning"]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _update_statistics(self, error: PluginError) -> None:
        """Update error statistics."""
        self._stats['total_errors'] += 1
        
        # Update by category
        category = error.category.value
        self._stats['errors_by_category'][category] = self._stats['errors_by_category'].get(category, 0) + 1
        
        # Update by severity
        severity = error.severity.value
        self._stats['errors_by_severity'][severity] = self._stats['errors_by_severity'].get(severity, 0) + 1
    
    async def _notify_error_listeners(self, error: PluginError) -> None:
        """Notify error listeners."""
        for listener in self._error_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(error)
                else:
                    listener(error)
            except Exception:
                # Don't let listener errors break error handling
                pass
    
    async def _attempt_recovery(self, error: PluginError) -> None:
        """Attempt error recovery."""
        # Find matching pattern
        matching_pattern = None
        for pattern in self._error_patterns.values():
            if (error.error_type in pattern.error_types or
                any(pattern_str.lower() in error.message.lower() 
                    for pattern_str in pattern.patterns)):
                matching_pattern = pattern
                break
        
        if not matching_pattern:
            return
        
        # Try recovery actions
        for action in matching_pattern.recovery_actions:
            try:
                success = await self._execute_recovery_action(error, action)
                if success:
                    error.resolved = True
                    error.resolution = f"Recovered via {action.value}"
                    self._stats['successful_recoveries'] += 1
                    return
            except Exception:
                pass
        
        self._stats['failed_recoveries'] += 1
    
    async def _execute_recovery_action(self, error: PluginError, action: RecoveryAction) -> bool:
        """Execute a recovery action."""
        if action in self._recovery_strategies:
            return await self._recovery_strategies[action](error)
        return False
    
    async def _retry_recovery(self, error: PluginError) -> bool:
        """Retry recovery action."""
        retry_config = self.get_retry_config(error.plugin_id)
        
        # Check if retry is appropriate for this error category
        if error.category not in retry_config.retry_on:
            return False
        
        # Check if we've exceeded max attempts
        if error.recovery_attempts >= retry_config.max_attempts:
            return False
        
        # Calculate delay
        delay = retry_config.base_delay_seconds * (retry_config.exponential_base ** error.recovery_attempts)
        delay = min(delay, retry_config.max_delay_seconds)
        
        # Add jitter if enabled
        if retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        # Wait and increment attempt count
        await asyncio.sleep(delay)
        error.recovery_attempts += 1
        self._stats['recovery_attempts'] += 1
        
        # Note: Actual retry logic would be implemented by the calling code
        # This just records the attempt and suggests retry
        return True
    
    async def _restart_recovery(self, error: PluginError) -> bool:
        """Restart recovery action."""
        # Note: This would restart the plugin
        # Implementation would depend on the plugin lifecycle manager
        return False
    
    async def _disable_recovery(self, error: PluginError) -> bool:
        """Disable recovery action."""
        # Note: This would disable the plugin
        # Implementation would depend on the plugin lifecycle manager
        return False
    
    async def _fallback_recovery(self, error: PluginError) -> bool:
        """Fallback recovery action."""
        # Note: This would use fallback logic
        # Implementation would be plugin-specific
        return False
    
    async def _ignore_recovery(self, error: PluginError) -> bool:
        """Ignore recovery action."""
        # Simply mark as resolved by ignoring
        return True
    
    async def _escalate_recovery(self, error: PluginError) -> bool:
        """Escalate recovery action."""
        # Note: This would escalate to higher-level handling
        # Implementation would depend on the system architecture
        return False
    
    def _analyze_error_patterns(self, errors: List[PluginError]) -> List[ErrorPattern]:
        """Analyze error patterns in a list of errors."""
        pattern_counts = {}
        
        for error in errors:
            for pattern in self._error_patterns.values():
                if (error.error_type in pattern.error_types or
                    any(pattern_str.lower() in error.message.lower() 
                        for pattern_str in pattern.patterns)):
                    pattern_counts[pattern.pattern_id] = pattern_counts.get(pattern.pattern_id, 0) + 1
        
        # Return patterns sorted by frequency
        sorted_patterns = sorted(
            [(pattern_id, count) for pattern_id, count in pattern_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return [self._error_patterns[pattern_id] for pattern_id, _ in sorted_patterns[:10]]
    
    def _generate_recommendations(self, errors: List[PluginError], 
                                patterns: List[ErrorPattern]) -> List[str]:
        """Generate recommendations based on errors and patterns."""
        recommendations = []
        
        # High error rate recommendation
        if len(errors) > 100:
            recommendations.append("High error rate detected. Consider reviewing plugin configuration and dependencies.")
        
        # Critical errors recommendation
        critical_errors = [error for error in errors if error.severity == ErrorSeverity.CRITICAL]
        if critical_errors:
            recommendations.append(f"{len(critical_errors)} critical errors detected. Immediate attention required.")
        
        # Network errors recommendation
        network_errors = [error for error in errors if error.category == ErrorCategory.NETWORK]
        if len(network_errors) > 10:
            recommendations.append("Multiple network errors detected. Check network connectivity and configuration.")
        
        # Resource errors recommendation
        resource_errors = [error for error in errors if error.category == ErrorCategory.RESOURCE]
        if resource_errors:
            recommendations.append("Resource errors detected. Consider increasing resource limits or optimizing plugin usage.")
        
        # Pattern-specific recommendations
        for pattern in patterns[:3]:  # Top 3 patterns
            if pattern.pattern_id == "network_timeout":
                recommendations.append("Frequent timeout errors. Consider increasing timeout values or improving network reliability.")
            elif pattern.pattern_id == "permission_denied":
                recommendations.append("Permission errors detected. Review file permissions and plugin access rights.")
            elif pattern.pattern_id == "memory_error":
                recommendations.append("Memory errors detected. Consider increasing available memory or optimizing memory usage.")
        
        return recommendations


def error_handler(plugin_id: Optional[str] = None, 
                 recovery_actions: Optional[List[RecoveryAction]] = None,
                 retry_config: Optional[RetryConfig] = None):
    """
    Decorator for automatic error handling.
    
    Args:
        plugin_id: Plugin ID (extracted from self if not provided)
        recovery_actions: List of recovery actions to attempt
        retry_config: Retry configuration
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Extract plugin ID
                pid = plugin_id
                if not pid and args:
                    # Try to get plugin_id from first argument (self)
                    if hasattr(args[0], 'plugin_id'):
                        pid = args[0].plugin_id
                    elif hasattr(args[0], 'metadata') and hasattr(args[0].metadata, 'id'):
                        pid = args[0].metadata.id
                
                # Handle error
                handler = get_plugin_error_handler()
                error = await handler.handle_error(
                    pid or "unknown",
                    e,
                    {
                        'function': func.__name__,
                        'args': str(args)[:100],  # Truncate for safety
                        'kwargs': str(kwargs)[:100]
                    }
                )
                
                # Re-raise if not resolved
                if not error.resolved:
                    raise e
                
                return None
        
        return wrapper
    return decorator


# Global plugin error handler instance
_plugin_error_handler = PluginErrorHandler()


# Convenience functions
async def handle_plugin_error(plugin_id: str, error: Exception, 
                           context: Optional[Dict[str, Any]] = None) -> PluginError:
    """Handle a plugin error."""
    return await _plugin_error_handler.handle_error(plugin_id, error, context)


def get_plugin_errors(plugin_id: str, limit: Optional[int] = None,
                    since: Optional[datetime] = None) -> List[PluginError]:
    """Get errors for a plugin."""
    return _plugin_error_handler.get_plugin_errors(plugin_id, limit, since)


def generate_error_report(plugin_id: Optional[str] = None,
                        time_range_hours: int = 24) -> ErrorReport:
    """Generate error report."""
    return _plugin_error_handler.generate_error_report(plugin_id, time_range_hours)


def get_error_statistics() -> Dict[str, Any]:
    """Get error statistics."""
    return _plugin_error_handler.get_statistics()


def add_error_pattern(pattern: ErrorPattern) -> None:
    """Add an error pattern."""
    _plugin_error_handler.add_error_pattern(pattern)


def set_retry_config(plugin_id: str, config: RetryConfig) -> None:
    """Set retry configuration for a plugin."""
    _plugin_error_handler.set_retry_config(plugin_id, config)


def get_plugin_error_handler() -> PluginErrorHandler:
    """Get the global plugin error handler."""
    return _plugin_error_handler
