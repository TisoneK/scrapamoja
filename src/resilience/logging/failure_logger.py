"""
Failure Event Logging

Specialized logging for failure events with detailed context, correlation tracking,
and structured output for debugging and analysis.
"""

import json
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.failure_event import FailureEvent, FailureSeverity, FailureCategory, RecoveryAction
from ..correlation import get_correlation_id
from .resilience_logger import ResilienceLogger


class FailureLogger:
    """Specialized logger for failure events with enhanced context tracking."""
    
    def __init__(self, name: str = "failure_logger"):
        """
        Initialize failure logger.
        
        Args:
            name: Logger name
        """
        self.logger = ResilienceLogger(name)
    
    def log_failure_event(
        self,
        failure: FailureEvent,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a failure event with comprehensive context.
        
        Args:
            failure: The failure event to log
            additional_context: Additional context information
        """
        context = {
            "failure_id": failure.id,
            "severity": failure.severity.value,
            "category": failure.category.value,
            "source": failure.source,
            "resolved": failure.resolved,
            "resolution_time": failure.resolution_time,
            "job_id": failure.job_id,
            "component": failure.component,
            "operation": failure.operation,
            "recovery_action": failure.recovery_action.value if failure.recovery_action else None,
            **failure.context,
            **(additional_context or {})
        }
        
        # Determine log level based on severity
        if failure.severity == FailureSeverity.CRITICAL:
            self.logger.critical(
                f"CRITICAL FAILURE: {failure.message}",
                event_type="failure_event",
                correlation_id=failure.correlation_id,
                context=context,
                component=failure.source
            )
        elif failure.severity == FailureSeverity.HIGH:
            self.logger.error(
                f"HIGH SEVERITY FAILURE: {failure.message}",
                event_type="failure_event",
                correlation_id=failure.correlation_id,
                context=context,
                component=failure.source
            )
        elif failure.severity == FailureSeverity.MEDIUM:
            self.logger.warning(
                f"MEDIUM SEVERITY FAILURE: {failure.message}",
                event_type="failure_event",
                correlation_id=failure.correlation_id,
                context=context,
                component=failure.source
            )
        else:
            self.logger.info(
                f"LOW SEVERITY FAILURE: {failure.message}",
                event_type="failure_event",
                correlation_id=failure.correlation_id,
                context=context,
                component=failure.source
            )
    
    def log_failure_with_stack_trace(
        self,
        failure: FailureEvent,
        stack_trace: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a failure event with stack trace information.
        
        Args:
            failure: The failure event to log
            stack_trace: Stack trace string (uses current if not provided)
            additional_context: Additional context information
        """
        if stack_trace is None:
            stack_trace = traceback.format_exc()
        
        context = {
            "stack_trace": stack_trace,
            **(additional_context or {})
        }
        
        self.log_failure_event(failure, context)
    
    def log_failure_pattern(
        self,
        failure_type: str,
        message: str,
        severity: str = "medium",
        category: str = "application",
        source: str = "resilience",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a failure pattern and return the failure ID.
        
        Args:
            failure_type: Type of failure
            message: Failure message
            severity: Severity level
            category: Failure category
            source: Source component
            context: Additional context
            
        Returns:
            Generated failure ID
        """
        failure = FailureEvent(
            severity=FailureSeverity(severity),
            category=FailureCategory(category),
            source=source,
            message=message,
            context=context or {}
        )
        
        self.log_failure_event(failure)
        return failure.id
    
    def log_failure_batch(
        self,
        failures: list[FailureEvent],
        batch_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log multiple failure events as a batch.
        
        Args:
            failures: List of failure events
            batch_context: Context for the entire batch
        """
        batch_info = {
            "batch_size": len(failures),
            "batch_timestamp": datetime.utcnow().isoformat(),
            **(batch_context or {})
        }
        
        for i, failure in enumerate(failures):
            context = {
                "batch_index": i,
                "batch_info": batch_info
            }
            self.log_failure_event(failure, context)
    
    def log_failure_statistics(
        self,
        statistics: Dict[str, Any],
        time_range: Optional[str] = None
    ) -> None:
        """
        Log failure statistics.
        
        Args:
            statistics: Failure statistics dictionary
            time_range: Time range for the statistics
        """
        context = {
            "time_range": time_range,
            "statistics": statistics
        }
        
        self.logger.info(
            f"Failure Statistics: {statistics.get('total_failures', 0)} total failures",
            event_type="failure_statistics",
            context=context,
            component="failure_logger"
        )
    
    def log_failure_recovery(
        self,
        failure: FailureEvent,
        recovery_action: RecoveryAction,
        recovery_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log failure recovery information.
        
        Args:
            failure: The original failure event
            recovery_action: Recovery action taken
            recovery_details: Additional recovery details
        """
        context = {
            "original_failure_id": failure.id,
            "recovery_action": recovery_action.value,
            "recovery_details": recovery_details or {},
            "original_message": failure.message,
            "original_category": failure.category.value,
            "original_severity": failure.severity.value
        }
        
        self.logger.info(
            f"Failure recovered: {failure.message} -> {recovery_action.value}",
            event_type="failure_recovery",
            correlation_id=failure.correlation_id,
            context=context,
            component=failure.source
        )
    
    def log_failure_analysis(
        self,
        analysis: Dict[str, Any],
        failure_id: Optional[str] = None
    ) -> None:
        """
        Log failure analysis results.
        
        Args:
            analysis: Analysis results
            failure_id: Associated failure ID
        """
        context = {
            "failure_id": failure_id,
            "analysis": analysis
        }
        
        self.logger.info(
            f"Failure analysis completed: {analysis.get('conclusion', 'No conclusion')}",
            event_type="failure_analysis",
            correlation_id=get_correlation_id(),
            context=context,
            component="failure_logger"
        )
    
    def log_failure_trend(
        self,
        trend_data: Dict[str, Any],
        time_period: str
    ) -> None:
        """
        Log failure trend information.
        
        Args:
            trend_data: Trend analysis data
            time_period: Time period for the trend
        """
        context = {
            "time_period": time_period,
            "trend_data": trend_data
        }
        
        self.logger.info(
            f"Failure trend analysis for {time_period}: {trend_data.get('trend', 'stable')}",
            event_type="failure_trend",
            correlation_id=get_correlation_id(),
            context=context,
            component="failure_logger"
        )
    
    def create_failure_report(
        self,
        failures: list[FailureEvent],
        report_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a comprehensive failure report.
        
        Args:
            failures: List of failure events
            report_context: Additional context for the report
            
        Returns:
            Comprehensive failure report
        """
        if not failures:
            return {
                "report_timestamp": datetime.utcnow().isoformat(),
                "total_failures": 0,
                "failures_by_severity": {},
                "failures_by_category": {},
                "resolved_failures": 0,
                "unresolved_failures": 0,
                "average_resolution_time": 0,
                "context": report_context or {}
            }
        
        # Calculate statistics
        total_failures = len(failures)
        failures_by_severity = {}
        failures_by_category = {}
        resolved_failures = 0
        unresolved_failures = 0
        resolution_times = []
        
        for failure in failures:
            # Count by severity
            severity = failure.severity.value
            failures_by_severity[severity] = failures_by_severity.get(severity, 0) + 1
            
            # Count by category
            category = failure.category.value
            failures_by_category[category] = failures_by_category.get(category, 0) + 1
            
            # Count resolved/unresolved
            if failure.resolved:
                resolved_failures += 1
                if failure.resolution_time:
                    resolution_times.append(failure.resolution_time)
            else:
                unresolved_failures += 1
        
        # Calculate average resolution time
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "total_failures": total_failures,
            "failures_by_severity": failures_by_severity,
            "failures_by_category": failures_by_category,
            "resolved_failures": resolved_failures,
            "unresolved_failures": unresolved_failures,
            "average_resolution_time": avg_resolution_time,
            "resolution_rate": (resolved_failures / total_failures) * 100 if total_failures > 0 else 0,
            "context": report_context or {},
            "failure_details": [failure.to_dict() for failure in failures]
        }
        
        # Log the report
        self.log_failure_statistics(
            {
                "total_failures": total_failures,
                "resolved_failures": resolved_failures,
                "unresolved_failures": unresolved_failures,
                "resolution_rate": report["resolution_rate"],
                "average_resolution_time": avg_resolution_time
            },
            "failure_report"
        )
        
        return report


# Global failure logger instance
_failure_logger = FailureLogger()


def log_failure_event(
    failure: FailureEvent,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log a failure event using the global failure logger."""
    _failure_logger.log_failure_event(failure, additional_context)


def log_failure_pattern(
    failure_type: str,
    message: str,
    severity: str = "medium",
    category: str = "application",
    source: str = "resilience",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Log a failure pattern using the global failure logger."""
    return _failure_logger.log_failure_pattern(
        failure_type, message, severity, category, source, context
    )


def log_failure_recovery(
    failure: FailureEvent,
    recovery_action: RecoveryAction,
    recovery_details: Optional[Dict[str, Any]] = None
) -> None:
    """Log failure recovery using the global failure logger."""
    _failure_logger.log_failure_recovery(failure, recovery_action, recovery_details)


def create_failure_report(
    failures: list[FailureEvent],
    report_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a failure report using the global failure logger."""
    return _failure_logger.create_failure_report(failures, report_context)
