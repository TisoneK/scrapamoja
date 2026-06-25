"""
Failure Analyzer

Analyzes failure patterns, trends, and root causes to provide intelligent
abort decisions with comprehensive failure classification and prediction.
"""

import re
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass, field

from ..models.abort import AbortTrigger, AbortSeverity, AbortMetrics
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id


class FailureType(Enum):
    """Types of failures."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    VALIDATION = "validation"
    SYSTEM = "system"
    MEMORY = "memory"
    DISK = "disk"
    DATABASE = "database"
    BROWSER = "browser"
    UNKNOWN = "unknown"


class FailureSeverity(Enum):
    """Severity levels for failures."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailurePattern:
    """Pattern of failures for analysis."""
    failure_type: FailureType
    pattern: str
    frequency: int
    severity: FailureSeverity
    first_seen: datetime
    last_seen: datetime
    affected_operations: List[str] = field(default_factory=list)
    suggested_action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "failure_type": self.failure_type.value,
            "pattern": self.pattern,
            "frequency": self.frequency,
            "severity": self.severity.value,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "affected_operations": self.affected_operations,
            "suggested_action": self.suggested_action
        }


@dataclass
class FailureAnalysis:
    """Comprehensive failure analysis result."""
    total_failures: int
    failure_rate: float
    failure_types: Dict[str, int]
    failure_patterns: List[FailurePattern]
    critical_failures: List[Dict[str, Any]]
    consecutive_failures: int
    failure_trend: str  # increasing, decreasing, stable
    predicted_failures: int
    recommendations: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_failures": self.total_failures,
            "failure_rate": self.failure_rate,
            "failure_types": self.failure_types,
            "failure_patterns": [p.to_dict() for p in self.failure_patterns],
            "critical_failures": self.critical_failures,
            "consecutive_failures": self.consecutive_failures,
            "failure_trend": self.failure_trend,
            "predicted_failures": self.predicted_failures,
            "recommendations": self.recommendations,
            "analysis_timestamp": self.analysis_timestamp.isoformat()
        }


class FailureAnalyzer:
    """Analyzes failures to provide intelligent abort decisions."""
    
    def __init__(self):
        """Initialize failure analyzer."""
        self.logger = get_logger("failure_analyzer")
        
        # Failure pattern definitions
        self.failure_patterns = self._initialize_failure_patterns()
        
        # Failure history
        self.failure_history: List[Dict[str, Any]] = []
        self.pattern_cache: Dict[str, FailurePattern] = {}
        
        # Analysis configuration
        self.analysis_window_hours = 24
        self.min_pattern_occurrences = 3
        self.trend_window_hours = 6
        self.prediction_window_hours = 1
    
    def _initialize_failure_patterns(self) -> Dict[FailureType, List[Dict[str, Any]]]:
        """Initialize failure pattern definitions."""
        return {
            FailureType.NETWORK: [
                {
                    "pattern": r"connection.*refused|connection.*timeout|network.*unreachable",
                    "severity": FailureSeverity.HIGH,
                    "suggested_action": "check_network_connectivity"
                },
                {
                    "pattern": r"dns.*resolution.*failed|host.*not.*found",
                    "severity": FailureSeverity.MEDIUM,
                    "suggested_action": "verify_dns_configuration"
                },
                {
                    "pattern": r"ssl.*certificate.*error|tls.*handshake.*failed",
                    "severity": FailureSeverity.MEDIUM,
                    "suggested_action": "check_ssl_certificates"
                }
            ],
            FailureType.TIMEOUT: [
                {
                    "pattern": r"timeout|timed.*out",
                    "severity": FailureSeverity.MEDIUM,
                    "suggested_action": "increase_timeout_thresholds"
                }
            ],
            FailureType.AUTHENTICATION: [
                {
                    "pattern": r"unauthorized|authentication.*failed|invalid.*credentials",
                    "severity": FailureSeverity.HIGH,
                    "suggested_action": "verify_authentication_credentials"
                }
            ],
            FailureType.PERMISSION: [
                {
                    "pattern": r"access.*denied|permission.*denied|forbidden",
                    "severity": FailureSeverity.HIGH,
                    "suggested_action": "check_permissions"
                }
            ],
            FailureType.VALIDATION: [
                {
                    "pattern": r"validation.*error|invalid.*input|malformed.*request",
                    "severity": FailureSeverity.LOW,
                    "suggested_action": "validate_input_data"
                }
            ],
            FailureType.SYSTEM: [
                {
                    "pattern": r"system.*error|internal.*error|kernel.*panic",
                    "severity": FailureSeverity.CRITICAL,
                    "suggested_action": "restart_system"
                }
            ],
            FailureType.MEMORY: [
                {
                    "pattern": r"out.*of.*memory|memory.*exhausted|allocation.*failed",
                    "severity": FailureSeverity.CRITICAL,
                    "suggested_action": "increase_memory_or_restart"
                }
            ],
            FailureType.DISK: [
                {
                    "pattern": r"disk.*full|no.*space.*left|storage.*exhausted",
                    "severity": FailureSeverity.CRITICAL,
                    "suggested_action": "free_disk_space"
                }
            ],
            FailureType.DATABASE: [
                {
                    "pattern": r"database.*connection.*failed|sql.*error|deadlock",
                    "severity": FailureSeverity.HIGH,
                    "suggested_action": "check_database_connection"
                }
            ],
            FailureType.BROWSER: [
                {
                    "pattern": r"browser.*crashed|page.*not.*found|javascript.*error",
                    "severity": FailureSeverity.MEDIUM,
                    "suggested_action": "restart_browser"
                }
            ]
        }
    
    async def analyze_failures(
        self,
        operation_history: List[Dict[str, Any]],
        error_history: List[Dict[str, Any]]
    ) -> FailureAnalysis:
        """
        Analyze failures and provide comprehensive analysis.
        
        Args:
            operation_history: List of operation records
            error_history: List of error records
            
        Returns:
            Comprehensive failure analysis
        """
        try:
            # Update failure history
            self._update_failure_history(operation_history, error_history)
            
            # Extract failures from recent history
            recent_failures = self._get_recent_failures()
            
            if not recent_failures:
                return FailureAnalysis(
                    total_failures=0,
                    failure_rate=0.0,
                    failure_types={},
                    failure_patterns=[],
                    critical_failures=[],
                    consecutive_failures=0,
                    failure_trend="stable",
                    predicted_failures=0,
                    recommendations=[]
                )
            
            # Analyze failure types
            failure_types = self._analyze_failure_types(recent_failures)
            
            # Identify failure patterns
            failure_patterns = self._identify_failure_patterns(recent_failures)
            
            # Identify critical failures
            critical_failures = self._identify_critical_failures(recent_failures)
            
            # Calculate consecutive failures
            consecutive_failures = self._calculate_consecutive_failures(operation_history)
            
            # Analyze failure trend
            failure_trend = self._analyze_failure_trend(recent_failures)
            
            # Predict future failures
            predicted_failures = self._predict_failures(recent_failures)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                failure_types, failure_patterns, critical_failures
            )
            
            # Calculate failure rate
            total_operations = len(operation_history)
            total_failures = len(recent_failures)
            failure_rate = total_failures / total_operations if total_operations > 0 else 0.0
            
            analysis = FailureAnalysis(
                total_failures=total_failures,
                failure_rate=failure_rate,
                failure_types=failure_types,
                failure_patterns=failure_patterns,
                critical_failures=critical_failures,
                consecutive_failures=consecutive_failures,
                failure_trend=failure_trend,
                predicted_failures=predicted_failures,
                recommendations=recommendations
            )
            
            self.logger.info(
                f"Failure analysis completed: {total_failures} failures, {failure_rate:.2%} rate",
                event_type="failure_analysis_completed",
                correlation_id=get_correlation_id(),
                context={
                    "total_failures": total_failures,
                    "failure_rate": failure_rate,
                    "patterns_found": len(failure_patterns),
                    "critical_failures": len(critical_failures)
                },
                component="failure_analyzer"
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(
                f"Failed to analyze failures: {str(e)}",
                event_type="failure_analysis_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="failure_analyzer"
            )
            # Return empty analysis on error
            return FailureAnalysis(
                total_failures=0,
                failure_rate=0.0,
                failure_types={},
                failure_patterns=[],
                critical_failures=[],
                consecutive_failures=0,
                failure_trend="stable",
                predicted_failures=0,
                recommendations=[]
            )
    
    def classify_failure(self, error_message: str) -> Tuple[FailureType, FailureSeverity]:
        """
        Classify a failure based on error message.
        
        Args:
            error_message: Error message to classify
            
        Returns:
            Tuple of (failure_type, severity)
        """
        error_message_lower = error_message.lower()
        
        for failure_type, patterns in self.failure_patterns.items():
            for pattern_info in patterns:
                if re.search(pattern_info["pattern"], error_message_lower, re.IGNORECASE):
                    return failure_type, pattern_info["severity"]
        
        return FailureType.UNKNOWN, FailureSeverity.MEDIUM
    
    def _update_failure_history(
        self,
        operation_history: List[Dict[str, Any]],
        error_history: List[Dict[str, Any]]
    ) -> None:
        """Update internal failure history."""
        # Extract failures from operation history
        for operation in operation_history:
            if not operation.get("success", True):
                failure_info = {
                    "timestamp": operation["timestamp"],
                    "operation_id": operation["id"],
                    "error_type": operation.get("error_type", "unknown"),
                    "error_message": operation.get("error_message", ""),
                    "response_time": operation.get("response_time", 0.0)
                }
                self.failure_history.append(failure_info)
        
        # Add explicit error records
        for error in error_history:
            failure_info = {
                "timestamp": error["timestamp"],
                "operation_id": error.get("operation_id", ""),
                "error_type": error.get("error_type", "unknown"),
                "error_message": error.get("error_message", ""),
                "response_time": 0.0
            }
            self.failure_history.append(failure_info)
        
        # Limit history size
        if len(self.failure_history) > 10000:
            self.failure_history = self.failure_history[-10000:]
    
    def _get_recent_failures(self) -> List[Dict[str, Any]]:
        """Get failures from the analysis window."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.analysis_window_hours)
        
        recent_failures = [
            failure for failure in self.failure_history
            if failure["timestamp"] >= cutoff_time
        ]
        
        return recent_failures
    
    def _analyze_failure_types(self, failures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze failure types and their frequencies."""
        type_counts = Counter()
        
        for failure in failures:
            failure_type, _ = self.classify_failure(failure.get("error_message", ""))
            type_counts[failure_type.value] += 1
        
        return dict(type_counts)
    
    def _identify_failure_patterns(self, failures: List[Dict[str, Any]]) -> List[FailurePattern]:
        """Identify recurring failure patterns."""
        pattern_counts = defaultdict(lambda: {
            "count": 0,
            "first_seen": None,
            "last_seen": None,
            "operations": []
        })
        
        for failure in failures:
            error_message = failure.get("error_message", "")
            failure_type, severity = self.classify_failure(error_message)
            
            # Find matching patterns
            for pattern_info in self.failure_patterns.get(failure_type, []):
                if re.search(pattern_info["pattern"], error_message, re.IGNORECASE):
                    pattern_key = f"{failure_type.value}:{pattern_info['pattern']}"
                    
                    pattern_counts[pattern_key]["count"] += 1
                    pattern_counts[pattern_key]["operations"].append(failure["operation_id"])
                    
                    if pattern_counts[pattern_key]["first_seen"] is None:
                        pattern_counts[pattern_key]["first_seen"] = failure["timestamp"]
                    pattern_counts[pattern_key]["last_seen"] = failure["timestamp"]
        
        # Create FailurePattern objects
        patterns = []
        for pattern_key, info in pattern_counts.items():
            if info["count"] >= self.min_pattern_occurrences:
                failure_type_str, pattern_str = pattern_key.split(":", 1)
                failure_type = FailureType(failure_type_str)
                
                # Find pattern info for severity and suggested action
                pattern_info = None
                for p_info in self.failure_patterns.get(failure_type, []):
                    if p_info["pattern"] == pattern_str:
                        pattern_info = p_info
                        break
                
                if pattern_info:
                    pattern = FailurePattern(
                        failure_type=failure_type,
                        pattern=pattern_str,
                        frequency=info["count"],
                        severity=pattern_info["severity"],
                        first_seen=info["first_seen"],
                        last_seen=info["last_seen"],
                        affected_operations=info["operations"],
                        suggested_action=pattern_info["suggested_action"]
                    )
                    patterns.append(pattern)
        
        # Sort by frequency (descending)
        patterns.sort(key=lambda p: p.frequency, reverse=True)
        
        return patterns
    
    def _identify_critical_failures(self, failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify critical failures that require immediate attention."""
        critical_failures = []
        
        for failure in failures:
            _, severity = self.classify_failure(failure.get("error_message", ""))
            
            if severity == FailureSeverity.CRITICAL:
                critical_failures.append({
                    "timestamp": failure["timestamp"],
                    "operation_id": failure["operation_id"],
                    "error_message": failure["error_message"],
                    "error_type": failure.get("error_type", "unknown")
                })
        
        # Sort by timestamp (most recent first)
        critical_failures.sort(key=lambda f: f["timestamp"], reverse=True)
        
        return critical_failures
    
    def _calculate_consecutive_failures(self, operation_history: List[Dict[str, Any]]) -> int:
        """Calculate consecutive failures."""
        consecutive = 0
        
        # Check from the end of history
        for operation in reversed(operation_history):
            if not operation.get("success", True):
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def _analyze_failure_trend(self, failures: List[Dict[str, Any]]) -> str:
        """Analyze failure trend over time."""
        if len(failures) < 2:
            return "stable"
        
        # Group failures by hour
        hourly_counts = defaultdict(int)
        for failure in failures:
            hour_key = failure["timestamp"].replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour_key] += 1
        
        if len(hourly_counts) < 2:
            return "stable"
        
        # Sort by time
        sorted_hours = sorted(hourly_counts.keys())
        
        # Compare recent vs older periods
        mid_point = len(sorted_hours) // 2
        recent_hours = sorted_hours[mid_point:]
        older_hours = sorted_hours[:mid_point]
        
        recent_avg = sum(hourly_counts[h] for h in recent_hours) / len(recent_hours)
        older_avg = sum(hourly_counts[h] for h in older_hours) / len(older_hours)
        
        if recent_avg > older_avg * 1.2:
            return "increasing"
        elif recent_avg < older_avg * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    def _predict_failures(self, failures: List[Dict[str, Any]]) -> int:
        """Predict number of failures in the next prediction window."""
        if len(failures) < 5:
            return 0
        
        # Calculate failure rate in recent history
        cutoff_time = datetime.utcnow() - timedelta(hours=self.trend_window_hours)
        recent_failures = [
            f for f in failures
            if f["timestamp"] >= cutoff_time
        ]
        
        if not recent_failures:
            return 0
        
        # Calculate hourly failure rate
        hours_elapsed = self.trend_window_hours
        failures_per_hour = len(recent_failures) / hours_elapsed
        
        # Predict for prediction window
        predicted_failures = int(failures_per_hour * self.prediction_window_hours)
        
        return predicted_failures
    
    def _generate_recommendations(
        self,
        failure_types: Dict[str, int],
        failure_patterns: List[FailurePattern],
        critical_failures: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on failure analysis."""
        recommendations = []
        
        # Critical failures recommendation
        if critical_failures:
            recommendations.append(
                f"Immediate attention required: {len(critical_failures)} critical failures detected"
            )
        
        # High failure rate recommendation
        total_failures = sum(failure_types.values())
        if total_failures > 50:
            recommendations.append(
                "High failure rate detected: consider implementing circuit breaker pattern"
            )
        
        # Pattern-based recommendations
        for pattern in failure_patterns[:3]:  # Top 3 patterns
            if pattern.suggested_action:
                recommendations.append(
                    f"Pattern '{pattern.pattern}' ({pattern.frequency} occurrences): {pattern.suggested_action}"
                )
        
        # Failure type recommendations
        if failure_types.get("network", 0) > 10:
            recommendations.append("Network issues detected: verify network connectivity and DNS resolution")
        
        if failure_types.get("memory", 0) > 0:
            recommendations.append("Memory issues detected: consider increasing memory allocation or implementing memory monitoring")
        
        if failure_types.get("browser", 0) > 5:
            recommendations.append("Browser issues detected: implement browser restart policies")
        
        return recommendations


# Global failure analyzer instance
_failure_analyzer = FailureAnalyzer()


def get_failure_analyzer() -> FailureAnalyzer:
    """Get the global failure analyzer instance."""
    return _failure_analyzer


async def analyze_failures(
    operation_history: List[Dict[str, Any]],
    error_history: List[Dict[str, Any]]
) -> FailureAnalysis:
    """Analyze failures using the global analyzer."""
    return await _failure_analyzer.analyze_failures(operation_history, error_history)


def classify_failure(error_message: str) -> Tuple[FailureType, FailureSeverity]:
    """Classify a failure using the global analyzer."""
    return _failure_analyzer.classify_failure(error_message)
