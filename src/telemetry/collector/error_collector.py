"""
Error Data Collector

Specialized collector for error data with classification,
trend analysis, and recovery pattern tracking.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, Counter
import traceback

from ..models import ErrorData
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryCollectionError
from ..configuration.logging import get_logger


@dataclass
class ErrorStats:
    """Statistics for error data."""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = None
    errors_by_selector: Dict[str, int] = None
    retry_attempts: int = 0
    fallback_attempts: int = 0
    recovery_successful: int = 0
    recovery_failed: int = 0
    average_retry_attempts: float = 0.0
    most_common_error: str = ""
    error_rate: float = 0.0
    last_error: Optional[datetime] = None
    
    def __post_init__(self):
        if self.errors_by_type is None:
            self.errors_by_type = {}
        if self.errors_by_selector is None:
            self.errors_by_selector = {}


@dataclass
class ErrorPattern:
    """Pattern information for recurring errors."""
    error_type: str
    selector_name: str
    frequency: int
    time_pattern: str
    recovery_success_rate: float
    average_retry_attempts: float
    last_occurrence: datetime
    severity: str


class ErrorCollector:
    """
    Specialized collector for error data with classification and analysis.
    
    Provides comprehensive error tracking, pattern analysis,
    and recovery monitoring for selector operations.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize error collector.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("error_collector")
        
        # Error configuration
        self.max_samples = config.get("max_error_samples", 10000)
        self.error_classification = config.get("error_classification", {
            "timeout": ["TimeoutError", "asyncio.TimeoutError"],
            "network": ["ConnectionError", "NetworkError", "RequestException"],
            "parsing": ["ValueError", "ParseError", "JSONDecodeError"],
            "selector": ["SelectorError", "ElementNotFoundError"],
            "browser": ["BrowserError", "PageError", "ExecutionContextError"],
            "validation": ["ValidationError", "SchemaError"],
            "system": ["MemoryError", "OSError", "IOError"]
        })
        
        # Error storage
        self._error_samples: List[Dict[str, Any]] = []
        self._error_stats: ErrorStats = ErrorStats()
        self._stats_lock = asyncio.Lock()
        
        # Error patterns cache
        self._error_patterns: List[ErrorPattern] = []
        self._patterns_cache_time: Optional[datetime] = None
        
        # Collection state
        self._enabled = True
        self._collection_count = 0
        self._error_count = 0
    
    async def collect_error_data(
        self,
        selector_name: str,
        operation_type: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        retry_attempts: int = 0,
        fallback_attempts: int = 0,
        recovery_successful: Optional[bool] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ErrorData:
        """
        Collect error data for an operation.
        
        Args:
            selector_name: Name of selector
            operation_type: Type of operation
            error_type: Type of error
            error_message: Error message
            stack_trace: Optional stack trace
            retry_attempts: Number of retry attempts
            fallback_attempts: Number of fallback attempts
            recovery_successful: Whether recovery was successful
            additional_context: Additional error context
            
        Returns:
            ErrorData instance
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            if not self._enabled:
                raise TelemetryCollectionError(
                    "Error collector is disabled",
                    error_code="TEL-601"
                )
            
            # Classify error
            classified_type = self._classify_error(error_type)
            
            # Create error data
            error_data = ErrorData(
                error_type=error_type,
                error_message=error_message,
                stack_trace=stack_trace,
                retry_attempts=retry_attempts,
                fallback_attempts=fallback_attempts,
                recovery_successful=recovery_successful
            )
            
            # Store error sample
            await self._store_error_sample(
                selector_name,
                operation_type,
                classified_type,
                error_data,
                additional_context
            )
            
            # Update statistics
            await self._update_statistics(selector_name, classified_type, error_data)
            
            self._collection_count += 1
            
            self.logger.warning(
                "Error data collected",
                selector_name=selector_name,
                operation_type=operation_type,
                error_type=error_type,
                classified_type=classified_type,
                retry_attempts=retry_attempts
            )
            
            return error_data
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(
                "Failed to collect error data",
                selector_name=selector_name,
                error_type=error_type,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect error data: {e}",
                error_code="TEL-602"
            )
    
    async def analyze_error_patterns(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[ErrorPattern]:
        """
        Analyze error patterns and recurring issues.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            List of error patterns
        """
        try:
            # Check cache
            cache_key = f"{selector_name}_{time_window}"
            if (self._patterns_cache_time and 
                datetime.utcnow() - self._patterns_cache_time < timedelta(minutes=5)):
                return self._error_patterns
            
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return []
            
            # Group errors by type and selector
            error_groups = defaultdict(list)
            
            for sample in samples:
                key = (sample["classified_type"], sample["selector_name"])
                error_groups[key].append(sample)
            
            # Analyze each group for patterns
            patterns = []
            
            for (error_type, sel_name), group_samples in error_groups.items():
                if len(group_samples) < 3:  # Need at least 3 occurrences for pattern
                    continue
                
                pattern = await self._analyze_error_group(
                    error_type,
                    sel_name,
                    group_samples
                )
                
                if pattern:
                    patterns.append(pattern)
            
            # Sort by frequency
            patterns.sort(key=lambda x: x.frequency, reverse=True)
            
            # Update cache
            self._error_patterns = patterns
            self._patterns_cache_time = datetime.utcnow()
            
            return patterns
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze error patterns",
                selector_name=selector_name,
                error=str(e)
            )
            return []
    
    async def get_error_trends(
        self,
        selector_name: Optional[str] = None,
        time_window: timedelta = timedelta(hours=24)
    ) -> Dict[str, Any]:
        """
        Analyze error trends over time.
        
        Args:
            selector_name: Optional selector filter
            time_window: Time window for trend analysis
            
        Returns:
            Error trend analysis
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Group by hour
            hourly_errors = defaultdict(int)
            hourly_types = defaultdict(lambda: defaultdict(int))
            
            for sample in samples:
                hour = sample["timestamp"].hour
                error_type = sample["classified_type"]
                
                hourly_errors[hour] += 1
                hourly_types[hour][error_type] += 1
            
            # Calculate trend
            hours = sorted(hourly_errors.keys())
            if len(hours) < 2:
                return {"trend": "insufficient_data"}
            
            # Simple trend calculation
            recent_avg = mean([hourly_errors[h] for h in hours[-4:]])  # Last 4 hours
            historical_avg = mean([hourly_errors[h] for h in hours[:-4]])  # Earlier hours
            
            if historical_avg == 0:
                trend = "stable"
            else:
                percent_change = ((recent_avg - historical_avg) / historical_avg) * 100
                
                if abs(percent_change) < 10:
                    trend = "stable"
                elif percent_change > 0:
                    trend = "increasing"
                else:
                    trend = "decreasing"
            
            # Peak hours
            peak_hour = max(hourly_errors, key=hourly_errors.get)
            
            return {
                "trend": trend,
                "percent_change": percent_change if historical_avg > 0 else 0,
                "hourly_distribution": dict(hourly_errors),
                "hourly_types": {hour: dict(types) for hour, types in hourly_types.items()},
                "peak_hour": peak_hour,
                "peak_errors": hourly_errors[peak_hour],
                "total_errors": sum(hourly_errors.values()),
                "average_per_hour": mean(hourly_errors.values()) if hourly_errors else 0
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get error trends",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_recovery_analysis(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze recovery patterns and effectiveness.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            Recovery analysis
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Extract recovery data
            recovery_data = []
            
            for sample in samples:
                error_data = sample["error_data"]
                if error_data.get("recovery_successful") is not None:
                    recovery_data.append({
                        "error_type": sample["classified_type"],
                        "selector_name": sample["selector_name"],
                        "retry_attempts": error_data.get("retry_attempts", 0),
                        "fallback_attempts": error_data.get("fallback_attempts", 0),
                        "recovery_successful": error_data.get("recovery_successful", False)
                    })
            
            if not recovery_data:
                return {}
            
            # Calculate recovery statistics
            total_recoveries = len(recovery_data)
            successful_recoveries = sum(1 for r in recovery_data if r["recovery_successful"])
            failed_recoveries = total_recoveries - successful_recoveries
            
            # Group by error type
            recovery_by_type = defaultdict(lambda: {"successful": 0, "total": 0})
            
            for recovery in recovery_data:
                error_type = recovery["error_type"]
                recovery_by_type[error_type]["total"] += 1
                if recovery["recovery_successful"]:
                    recovery_by_type[error_type]["successful"] += 1
            
            # Calculate success rates by type
            recovery_rates = {}
            for error_type, data in recovery_by_type.items():
                if data["total"] > 0:
                    recovery_rates[error_type] = data["successful"] / data["total"]
            
            # Retry and fallback statistics
            retry_attempts = [r["retry_attempts"] for r in recovery_data]
            fallback_attempts = [r["fallback_attempts"] for r in recovery_data]
            
            return {
                "total_recovery_attempts": total_recoveries,
                "successful_recoveries": successful_recoveries,
                "failed_recoveries": failed_recoveries,
                "overall_recovery_rate": successful_recoveries / total_recoveries,
                "recovery_rates_by_type": recovery_rates,
                "retry_statistics": {
                    "total_attempts": sum(retry_attempts),
                    "average_attempts": mean(retry_attempts) if retry_attempts else 0,
                    "max_attempts": max(retry_attempts) if retry_attempts else 0
                },
                "fallback_statistics": {
                    "total_attempts": sum(fallback_attempts),
                    "average_attempts": mean(fallback_attempts) if fallback_attempts else 0,
                    "max_attempts": max(fallback_attempts) if fallback_attempts else 0
                }
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get recovery analysis",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_error_classification(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get error classification breakdown.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            Error classification breakdown
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Classify errors
            classified_errors = defaultdict(int)
            original_types = defaultdict(int)
            
            for sample in samples:
                classified = sample["classified_type"]
                original = sample["error_data"].get("error_type", "unknown")
                
                classified_errors[classified] += 1
                original_types[original] += 1
            
            # Calculate percentages
            total_errors = len(samples)
            
            classified_percentages = {
                error_type: (count / total_errors) * 100
                for error_type, count in classified_errors.items()
            }
            
            original_percentages = {
                error_type: (count / total_errors) * 100
                for error_type, count in original_types.items()
            }
            
            return {
                "total_errors": total_errors,
                "classified_errors": dict(classified_errors),
                "original_errors": dict(original_types),
                "classified_percentages": classified_percentages,
                "original_percentages": original_percentages,
                "most_common_classified": max(classified_errors, key=classified_errors.get) if classified_errors else "",
                "most_common_original": max(original_types, key=original_types.get) if original_types else ""
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get error classification",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_error_statistics(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive error statistics.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for statistics
            
        Returns:
            Error statistics
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Extract statistics
            error_types = [sample["classified_type"] for sample in samples]
            selectors = [sample["selector_name"] for sample in samples]
            
            retry_attempts = [
                sample["error_data"].get("retry_attempts", 0)
                for sample in samples
            ]
            
            fallback_attempts = [
                sample["error_data"].get("fallback_attempts", 0)
                for sample in samples
            ]
            
            recovery_successful = [
                sample["error_data"].get("recovery_successful", False)
                for sample in samples
                if sample["error_data"].get("recovery_successful") is not None
            ]
            
            # Calculate statistics
            stats = {
                "total_errors": len(samples),
                "unique_error_types": len(set(error_types)),
                "unique_selectors": len(set(selectors)),
                "total_retry_attempts": sum(retry_attempts),
                "total_fallback_attempts": sum(fallback_attempts),
                "average_retry_attempts": mean(retry_attempts) if retry_attempts else 0,
                "average_fallback_attempts": mean(fallback_attempts) if fallback_attempts else 0
            }
            
            if recovery_successful:
                successful_recoveries = sum(recovery_successful)
                stats.update({
                    "recovery_attempts": len(recovery_successful),
                    "successful_recoveries": successful_recoveries,
                    "recovery_rate": successful_recoveries / len(recovery_successful)
                })
            
            # Error type distribution
            error_type_counts = Counter(error_types)
            stats["error_type_distribution"] = dict(error_type_counts)
            stats["most_common_error_type"] = error_type_counts.most_common(1)[0][0] if error_type_counts else ""
            
            # Selector error distribution
            selector_counts = Counter(selectors)
            stats["selector_error_distribution"] = dict(selector_counts)
            stats["most_affected_selector"] = selector_counts.most_common(1)[0][0] if selector_counts else ""
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Failed to get error statistics",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Collection statistics
        """
        async with self._stats_lock:
            return {
                "total_collections": self._collection_count,
                "error_count": self._error_count,
                "error_rate": self._error_count / max(1, self._collection_count),
                "samples_stored": len(self._error_samples),
                "selectors_tracked": len(set(s["selector_name"] for s in self._error_samples)),
                "error_types_tracked": len(set(s["classified_type"] for s in self._error_samples)),
                "enabled": self._enabled,
                "max_samples": self.max_samples,
                "total_errors": self._error_stats.total_errors,
                "most_common_error": self._error_stats.most_common_error
            }
    
    async def enable_collection(self) -> None:
        """Enable error collection."""
        self._enabled = True
        self.logger.info("Error collection enabled")
    
    async def disable_collection(self) -> None:
        """Disable error collection."""
        self._enabled = False
        self.logger.info("Error collection disabled")
    
    async def clear_samples(self, selector_name: Optional[str] = None) -> int:
        """
        Clear error samples.
        
        Args:
            selector_name: Optional selector filter
            
        Returns:
            Number of samples cleared
        """
        async with self._stats_lock:
            if selector_name:
                original_count = len(self._error_samples)
                self._error_samples = [
                    sample for sample in self._error_samples
                    if sample["selector_name"] != selector_name
                ]
                cleared_count = original_count - len(self._error_samples)
            else:
                cleared_count = len(self._error_samples)
                self._error_samples.clear()
                self._error_stats = ErrorStats()
            
            self.logger.info(
                "Error samples cleared",
                selector_name=selector_name or "all",
                cleared_count=cleared_count
            )
            
            return cleared_count
    
    # Private methods
    
    def _classify_error(self, error_type: str) -> str:
        """Classify error type into categories."""
        error_type_lower = error_type.lower()
        
        for category, types in self.error_classification.items():
            for error_class in types:
                if error_class.lower() in error_type_lower:
                    return category
        
        return "unknown"
    
    async def _store_error_sample(
        self,
        selector_name: str,
        operation_type: str,
        classified_type: str,
        error_data: ErrorData,
        additional_context: Optional[Dict[str, Any]]
    ) -> None:
        """Store error sample."""
        sample = {
            "selector_name": selector_name,
            "operation_type": operation_type,
            "classified_type": classified_type,
            "error_data": error_data.to_dict(),
            "additional_context": additional_context or {},
            "timestamp": datetime.utcnow()
        }
        
        async with self._stats_lock:
            self._error_samples.append(sample)
            
            # Limit sample size
            if len(self._error_samples) > self.max_samples:
                self._error_samples = self._error_samples[-self.max_samples:]
    
    async def _update_statistics(
        self,
        selector_name: str,
        classified_type: str,
        error_data: ErrorData
    ) -> None:
        """Update error statistics."""
        async with self._stats_lock:
            self._error_stats.total_errors += 1
            self._error_stats.last_error = datetime.utcnow()
            
            # Update error type counts
            if classified_type not in self._error_stats.errors_by_type:
                self._error_stats.errors_by_type[classified_type] = 0
            self._error_stats.errors_by_type[classified_type] += 1
            
            # Update selector error counts
            if selector_name not in self._error_stats.errors_by_selector:
                self._error_stats.errors_by_selector[selector_name] = 0
            self._error_stats.errors_by_selector[selector_name] += 1
            
            # Update retry and fallback statistics
            self._error_stats.retry_attempts += error_data.retry_attempts
            self._error_stats.fallback_attempts += error_data.fallback_attempts
            
            # Update recovery statistics
            if error_data.recovery_successful is not None:
                if error_data.recovery_successful:
                    self._error_stats.recovery_successful += 1
                else:
                    self._error_stats.recovery_failed += 1
            
            # Calculate average retry attempts
            if self._error_stats.total_errors > 0:
                self._error_stats.average_retry_attempts = (
                    self._error_stats.retry_attempts / self._error_stats.total_errors
                )
            
            # Update most common error
            if self._error_stats.errors_by_type:
                self._error_stats.most_common_error = max(
                    self._error_stats.errors_by_type,
                    key=self._error_stats.errors_by_type.get
                )
    
    async def _analyze_error_group(
        self,
        error_type: str,
        selector_name: str,
        group_samples: List[Dict[str, Any]]
    ) -> Optional[ErrorPattern]:
        """Analyze a group of errors for patterns."""
        try:
            if len(group_samples) < 3:
                return None
            
            # Calculate frequency
            frequency = len(group_samples)
            
            # Analyze time pattern
            timestamps = [sample["timestamp"] for sample in group_samples]
            time_span = max(timestamps) - min(timestamps)
            
            if time_span.total_seconds() < 3600:  # Less than 1 hour
                time_pattern = "clustered"
            elif time_span.total_seconds() < 86400:  # Less than 1 day
                time_pattern = "daily"
            else:
                time_pattern = "sporadic"
            
            # Calculate recovery success rate
            recovery_successful = [
                sample["error_data"].get("recovery_successful", False)
                for sample in group_samples
                if sample["error_data"].get("recovery_successful") is not None
            ]
            
            if recovery_successful:
                recovery_success_rate = sum(recovery_successful) / len(recovery_successful)
            else:
                recovery_success_rate = 0.0
            
            # Calculate average retry attempts
            retry_attempts = [
                sample["error_data"].get("retry_attempts", 0)
                for sample in group_samples
            ]
            
            average_retry_attempts = mean(retry_attempts) if retry_attempts else 0.0
            
            # Determine severity
            if recovery_success_rate < 0.3 and average_retry_attempts > 2:
                severity = "high"
            elif recovery_success_rate < 0.6 or average_retry_attempts > 1:
                severity = "medium"
            else:
                severity = "low"
            
            return ErrorPattern(
                error_type=error_type,
                selector_name=selector_name,
                frequency=frequency,
                time_pattern=time_pattern,
                recovery_success_rate=recovery_success_rate,
                average_retry_attempts=average_retry_attempts,
                last_occurrence=max(timestamps),
                severity=severity
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze error group",
                error_type=error_type,
                selector_name=selector_name,
                error=str(e)
            )
            return None
    
    async def _get_filtered_samples(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered error samples."""
        samples = self._error_samples.copy()
        
        if selector_name:
            samples = [
                sample for sample in samples
                if sample["selector_name"] == selector_name
            ]
        
        if time_window:
            cutoff_time = datetime.utcnow() - time_window
            samples = [
                sample for sample in samples
                if sample["timestamp"] >= cutoff_time
            ]
        
        return samples
