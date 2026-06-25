"""
Performance monitoring framework for Selector Engine.

Provides metrics collection, analysis, and reporting capabilities as required
by the Scorewise Constitution for production resilience.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

from src.models.selector_models import (
    SelectorResult, ConfidenceMetrics, PerformanceTrend, TrendDirection
)
from src.observability.logger import get_logger, CorrelationContext
from src.utils.exceptions import PerformanceError


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricAggregates:
    """Aggregated metrics for a time period."""
    selector_name: str
    metric_type: str
    time_range: Tuple[datetime, datetime]
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    success_rate: float
    avg_confidence: float
    avg_resolution_time: float
    confidence_trend: TrendDirection
    min_confidence: float
    max_confidence: float


class MetricsCollector:
    """Collects and stores performance metrics."""
    
    def __init__(self, max_points: int = 10000):
        self._max_points = max_points
        self._metrics: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self._logger = get_logger("metrics_collector")
    
    async def record_metric(self, selector_name: str, metric_type: str, 
                           value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a metric data point."""
        try:
            point = MetricPoint(
                timestamp=datetime.utcnow(),
                value=value,
                metadata=metadata or {}
            )
            
            # Add to metrics store
            selector_metrics = self._metrics[selector_name][metric_type]
            selector_metrics.append(point)
            
            # Maintain max size
            if len(selector_metrics) > self._max_points:
                selector_metrics.popleft()
            
            self._logger.debug(
                "metric_recorded",
                selector_name=selector_name,
                metric_type=metric_type,
                value=value
            )
            
        except Exception as e:
            self._logger.error(
                "metric_recording_failed",
                selector_name=selector_name,
                metric_type=metric_type,
                error=str(e)
            )
    
    def get_metrics(self, selector_name: str, metric_type: str, 
                   time_range: Tuple[datetime, datetime]) -> List[MetricPoint]:
        """Get metrics for a selector within a time range."""
        try:
            if selector_name not in self._metrics or metric_type not in self._metrics[selector_name]:
                return []
            
            metrics = self._metrics[selector_name][metric_type]
            filtered_metrics = [
                point for point in metrics
                if time_range[0] <= point.timestamp <= time_range[1]
            ]
            
            return filtered_metrics
            
        except Exception as e:
            self._logger.error(
                "metrics_retrieval_failed",
                selector_name=selector_name,
                metric_type=metric_type,
                error=str(e)
            )
            return []
    
    def calculate_aggregates(self, selector_name: str, 
                           time_range: Tuple[datetime, datetime]) -> MetricAggregates:
        """Calculate aggregated metrics for a selector."""
        try:
            # Get confidence metrics
            confidence_metrics = self.get_metrics(selector_name, "confidence_score", time_range)
            
            if not confidence_metrics:
                return MetricAggregates(
                    selector_name=selector_name,
                    metric_type="confidence_score",
                    time_range=time_range,
                    total_attempts=0,
                    successful_attempts=0,
                    failed_attempts=0,
                    success_rate=0.0,
                    avg_confidence=0.0,
                    avg_resolution_time=0.0,
                    confidence_trend=TrendDirection.STABLE,
                    min_confidence=0.0,
                    max_confidence=0.0
                )
            
            # Calculate aggregates
            confidence_values = [m.value for m in confidence_metrics]
            total_attempts = len(confidence_metrics)
            successful_attempts = sum(1 for m in confidence_metrics if m.value >= 0.5)
            failed_attempts = total_attempts - successful_attempts
            success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
            avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
            
            # Get resolution times
            resolution_times = []
            for metric in confidence_metrics:
                if "resolution_time" in metric.metadata:
                    resolution_times.append(metric.metadata["resolution_time"])
            
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0
            
            # Calculate trend
            trend = self._calculate_trend(confidence_values)
            
            return MetricAggregates(
                selector_name=selector_name,
                metric_type="confidence_score",
                time_range=time_range,
                total_attempts=total_attempts,
                successful_attempts=successful_attempts,
                failed_attempts=failed_attempts,
                success_rate=success_rate,
                avg_confidence=avg_confidence,
                avg_resolution_time=avg_resolution_time,
                confidence_trend=trend,
                min_confidence=min(confidence_values) if confidence_values else 0.0,
                max_confidence=max(confidence_values) if confidence_values else 0.0
            )
            
        except Exception as e:
            self._logger.error(
                "aggregates_calculation_failed",
                selector_name=selector_name,
                error=str(e)
            )
            raise PerformanceError(
                "aggregates", "calculation", f"Failed to calculate aggregates: {e}"
            )
    
    def get_all_selectors(self) -> List[str]:
        """Get all selector names that have metrics."""
        return list(self._metrics.keys())
    
    def get_top_performers(self, limit: int, metric: str, 
                          time_range: Tuple[datetime, datetime]) -> List[Tuple[str, float]]:
        """Get top performing selectors by metric."""
        try:
            selector_performance = []
            
            for selector_name in self.get_all_selectors():
                aggregates = self.calculate_aggregates(selector_name, time_range)
                
                if metric == "success_rate":
                    value = aggregates.success_rate
                elif metric == "avg_confidence":
                    value = aggregates.avg_confidence
                else:
                    continue
                
                selector_performance.append((selector_name, value))
            
            # Sort by performance (descending)
            selector_performance.sort(key=lambda x: x[1], reverse=True)
            
            return selector_performance[:limit]
            
        except Exception as e:
            self._logger.error(
                "top_performers_retrieval_failed",
                error=str(e)
            )
            return []
    
    def get_underperformers(self, limit: int, metric: str, 
                           time_range: Tuple[datetime, datetime]) -> List[Tuple[str, float]]:
        """Get underperforming selectors by metric."""
        try:
            selector_performance = []
            
            for selector_name in self.get_all_selectors():
                aggregates = self.calculate_aggregates(selector_name, time_range)
                
                if metric == "success_rate":
                    value = aggregates.success_rate
                elif metric == "avg_confidence":
                    value = aggregates.avg_confidence
                else:
                    continue
                
                selector_performance.append((selector_name, value))
            
            # Sort by performance (ascending)
            selector_performance.sort(key=lambda x: x[1])
            
            return selector_performance[:limit]
            
        except Exception as e:
            self._logger.error(
                "underperformers_retrieval_failed",
                error=str(e)
            )
            return []
    
    def _calculate_trend(self, values: List[float]) -> TrendDirection:
        """Calculate trend direction from values."""
        if len(values) < 3:
            return TrendDirection.STABLE
        
        # Simple trend calculation
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if not first_half or not second_half:
            return TrendDirection.STABLE
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 0.05:
            return TrendDirection.IMPROVING
        elif second_avg < first_avg - 0.05:
            return TrendDirection.DECLINING
        else:
            return TrendDirection.STABLE


class PerformanceMonitor:
    """Main performance monitoring interface."""
    
    def __init__(self):
        self._logger = get_logger("performance_monitor")
        self.collector = MetricsCollector()
        self._storage_path = Path("data/metrics")
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        self._logger.info("PerformanceMonitor initialized")
    
    async def record_resolution(self, result: SelectorResult) -> None:
        """Record a selector resolution result."""
        try:
            # Record basic metrics
            await self.collector.record_metric(
                result.selector_name or "unknown",
                "confidence_score",
                result.confidence_score,
                {
                    "strategy_used": result.strategy_used,
                    "resolution_time": result.resolution_time,
                    "success": result.success,
                    "validation_count": len(result.validation_results)
                }
            )
            
            # Record resolution time
            await self.collector.record_metric(
                result.selector_name or "unknown",
                "resolution_time",
                result.resolution_time,
                {
                    "strategy_used": result.strategy_used,
                    "confidence_score": result.confidence_score,
                    "success": result.success
                }
            )
            
            # Record success/failure
            await self.collector.record_metric(
                result.selector_name or "unknown",
                "success",
                1.0 if result.success else 0.0,
                {
                    "strategy_used": result.strategy_used,
                    "confidence_score": result.confidence_score,
                    "resolution_time": result.resolution_time
                }
            )
            
            self._logger.debug(
                "resolution_recorded",
                selector_name=result.selector_name,
                confidence_score=result.confidence_score,
                success=result.success
            )
            
        except Exception as e:
            self._logger.error(
                "resolution_recording_failed",
                selector_name=result.selector_name,
                error=str(e)
            )
    
    async def record_confidence_metrics(self, selector_name: str, confidence_score: float,
                                     resolution_time: float, validation_score: float,
                                     strategy_used: str, quality_passed: bool,
                                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record confidence-specific metrics for a selector resolution.
        
        Args:
            selector_name: Name of the selector
            confidence_score: Confidence score (0.0 to 1.0)
            resolution_time: Resolution time in milliseconds
            validation_score: Validation score (0.0 to 1.0)
            strategy_used: Strategy that was used
            quality_passed: Whether quality gate was passed
            metadata: Additional metadata
        """
        try:
            # Record basic confidence metric
            await self.collector.record_metric(
                selector_name, "confidence_score", confidence_score, {
                    "strategy_used": strategy_used,
                    "quality_passed": quality_passed,
                    "resolution_time": resolution_time,
                    "validation_score": validation_score,
                    **(metadata or {})
                }
            )
            
            # Record quality gate metric
            await self.collector.record_metric(
                selector_name, "quality_passed", 1.0 if quality_passed else 0.0, {
                    "confidence_score": confidence_score,
                    "strategy_used": strategy_used,
                    "resolution_time": resolution_time
                }
            )
            
            # Record strategy performance
            await self.collector.record_metric(
                selector_name, f"strategy_{strategy_used}_confidence", confidence_score, {
                    "resolution_time": resolution_time,
                    "validation_score": validation_score,
                    "quality_passed": quality_passed
                }
            )
            
            # Record validation score
            await self.collector.record_metric(
                selector_name, "validation_score", validation_score, {
                    "confidence_score": confidence_score,
                    "strategy_used": strategy_used,
                    "resolution_time": resolution_time
                }
            )
            
            self._logger.debug(
                "confidence_metrics_recorded",
                selector_name=selector_name,
                confidence_score=confidence_score,
                strategy_used=strategy_used,
                quality_passed=quality_passed
            )
            
        except Exception as e:
            self._logger.error(
                "confidence_metrics_recording_failed",
                selector_name=selector_name,
                error=str(e)
            )
    
    def get_confidence_metrics(self, selector_name: str, 
                             time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Get confidence metrics for a specific selector.
        
        Args:
            selector_name: Name of the selector
            time_range: Optional time range for filtering
            
        Returns:
            Dictionary with confidence metrics
        """
        try:
            if time_range is None:
                time_range = (datetime.utcnow() - timedelta(hours=24), datetime.utcnow())
            
            # Get confidence metrics
            confidence_metrics = self.collector.get_metrics(selector_name, "confidence_score", time_range)
            quality_metrics = self.collector.get_metrics(selector_name, "quality_passed", time_range)
            validation_metrics = self.collector.get_metrics(selector_name, "validation_score", time_range)
            
            if not confidence_metrics:
                return {
                    "selector_name": selector_name,
                    "time_range": {
                        "start": time_range[0].isoformat(),
                        "end": time_range[1].isoformat()
                    },
                    "total_resolutions": 0,
                    "average_confidence": 0.0,
                    "min_confidence": 0.0,
                    "max_confidence": 0.0,
                    "confidence_trend": "stable",
                    "quality_passed_rate": 0.0,
                    "average_validation_score": 0.0,
                    "strategy_performance": {}
                }
            
            # Calculate confidence statistics
            confidence_values = [m.value for m in confidence_metrics]
            quality_values = [m.value for m in quality_metrics]
            validation_values = [m.value for m in validation_metrics]
            
            # Calculate confidence trend
            trend = self._calculate_confidence_trend(confidence_values)
            
            # Calculate strategy performance
            strategy_performance = defaultdict(list)
            for metric in confidence_metrics:
                strategy = metric.metadata.get("strategy_used", "unknown")
                strategy_performance[strategy].append(metric.value)
            
            strategy_stats = {}
            for strategy, values in strategy_performance.items():
                if values:
                    strategy_stats[strategy] = {
                        "count": len(values),
                        "average_confidence": sum(values) / len(values),
                        "min_confidence": min(values),
                        "max_confidence": max(values)
                    }
            
            return {
                "selector_name": selector_name,
                "time_range": {
                    "start": time_range[0].isoformat(),
                    "end": time_range[1].isoformat()
                },
                "total_resolutions": len(confidence_metrics),
                "average_confidence": sum(confidence_values) / len(confidence_values) if confidence_values else 0.0,
                "min_confidence": min(confidence_values) if confidence_values else 0.0,
                "max_confidence": max(confidence_values) if confidence_values else 0.0,
                "confidence_trend": trend,
                "quality_passed_rate": sum(quality_values) / len(quality_values) if quality_values else 0.0,
                "average_validation_score": sum(validation_values) / len(validation_values) if validation_values else 0.0,
                "strategy_performance": strategy_stats,
                "recent_metrics": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "confidence_score": m.value,
                        "strategy_used": m.metadata.get("strategy_used", "unknown"),
                        "quality_passed": m.metadata.get("quality_passed", False),
                        "resolution_time": m.metadata.get("resolution_time", 0.0)
                    }
                    for m in confidence_metrics[-10:]  # Last 10 metrics
                ]
            }
            
        except Exception as e:
            self._logger.error(
                "confidence_metrics_retrieval_failed",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    def get_confidence_summary(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Get confidence summary across all selectors.
        
        Args:
            time_range: Optional time range for filtering
            
        Returns:
            Dictionary with confidence summary
        """
        try:
            if time_range is None:
                time_range = (datetime.utcnow() - timedelta(hours=24), datetime.utcnow())
            
            # Get all selectors
            all_selectors = self.collector.get_all_selectors()
            
            total_resolutions = 0
            all_confidence_scores = []
            all_quality_passed = []
            all_validation_scores = []
            strategy_performance = defaultdict(list)
            
            for selector_name in all_selectors:
                try:
                    confidence_metrics = self.collector.get_metrics(selector_name, "confidence_score", time_range)
                    quality_metrics = self.collector.get_metrics(selector_name, "quality_passed", time_range)
                    validation_metrics = self.collector.get_metrics(selector_name, "validation_score", time_range)
                    
                    # Aggregate metrics
                    all_confidence_scores.extend([m.value for m in confidence_metrics])
                    all_quality_passed.extend([m.value for m in quality_metrics])
                    all_validation_scores.extend([m.value for m in validation_metrics])
                    total_resolutions += len(confidence_metrics)
                    
                    # Aggregate strategy performance
                    for metric in confidence_metrics:
                        strategy = metric.metadata.get("strategy_used", "unknown")
                        strategy_performance[strategy].append(metric.value)
                        
                except Exception:
                    continue
            
            # Calculate overall statistics
            avg_confidence = sum(all_confidence_scores) / len(all_confidence_scores) if all_confidence_scores else 0.0
            quality_passed_rate = sum(all_quality_passed) / len(all_quality_passed) if all_quality_passed else 0.0
            avg_validation_score = sum(all_validation_scores) / len(all_validation_scores) if all_validation_scores else 0.0
            
            # Calculate confidence distribution
            confidence_distribution = {
                "perfect": sum(1 for score in all_confidence_scores if score >= 0.95),
                "high": sum(1 for score in all_confidence_scores if 0.85 <= score < 0.95),
                "medium": sum(1 for score in all_confidence_scores if 0.70 <= score < 0.85),
                "low": sum(1 for score in all_confidence_scores if 0.50 <= score < 0.70),
                "failed": sum(1 for score in all_confidence_scores if score < 0.50)
            }
            
            # Calculate strategy statistics
            strategy_stats = {}
            for strategy, values in strategy_performance.items():
                if values:
                    strategy_stats[strategy] = {
                        "total_uses": len(values),
                        "average_confidence": sum(values) / len(values),
                        "min_confidence": min(values),
                        "max_confidence": max(values)
                    }
            
            return {
                "summary_period": {
                    "start": time_range[0].isoformat(),
                    "end": time_range[1].isoformat()
                },
                "total_selectors": len(all_selectors),
                "total_resolutions": total_resolutions,
                "overall_statistics": {
                    "average_confidence": avg_confidence,
                    "quality_passed_rate": quality_passed_rate,
                    "average_validation_score": avg_validation_score,
                    "confidence_distribution": confidence_distribution
                },
                "strategy_performance": strategy_stats,
                "confidence_trend": self._calculate_confidence_trend(all_confidence_scores)
            }
            
        except Exception as e:
            self._logger.error(
                "confidence_summary_retrieval_failed",
                error=str(e)
            )
            return {}
    
    def _calculate_confidence_trend(self, confidence_values: List[float]) -> str:
        """Calculate confidence trend from a list of values."""
        if len(confidence_values) < 3:
            return "insufficient_data"
        
        # Simple trend calculation
        first_half = confidence_values[:len(confidence_values)//2]
        second_half = confidence_values[len(confidence_values)//2:]
        
        if not first_half or not second_half:
            return "insufficient_data"
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 0.05:
            return "improving"
        elif second_avg < first_avg - 0.05:
            return "declining"
        else:
            return "stable"
    
    def generate_performance_report(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        try:
            if time_range is None:
                time_range = (datetime.utcnow() - timedelta(hours=24), datetime.utcnow())
            
            # Get all selectors
            all_selectors = self.collector.get_all_selectors()
            
            selector_metrics = {}
            total_successful = 0
            total_failed = 0
            
            for selector_name in all_selectors:
                try:
                    metrics = self.collector.calculate_aggregates(selector_name, time_range)
                    selector_metrics[selector_name] = metrics
                    
                    total_successful += metrics.successful_attempts
                    total_failed += metrics.failed_attempts
                except Exception:
                    continue
            
            # Get top performers and underperformers
            top_performers = self.collector.get_top_performers(10, "success_rate", time_range)
            underperformers = self.collector.get_underperformers(10, "success_rate", time_range)
            
            # Generate report
            report = {
                "report_period": {
                    "start": time_range[0].isoformat(),
                    "end": time_range[1].isoformat()
                },
                "overall_statistics": {
                    "total_selectors": len(all_selectors),
                    "total_attempts": total_successful + total_failed,
                    "total_successful": total_successful,
                    "total_failed": total_failed,
                    "overall_success_rate": total_successful / (total_successful + total_failed) if (total_successful + total_failed) > 0 else 0.0
                },
                "top_performers": [
                    {"selector": name, "success_rate": rate}
                    for name, rate in top_performers
                ],
                "underperformers": [
                    {"selector": name, "success_rate": rate}
                    for name, rate in underperformers
                ],
                "selector_details": {}
            }
            
            # Add detailed metrics for each selector
            for selector_name, metrics in selector_metrics.items():
                report["selector_details"][selector_name] = {
                    "total_attempts": metrics.total_attempts,
                    "success_rate": metrics.success_rate,
                    "avg_confidence": metrics.avg_confidence,
                    "avg_resolution_time": metrics.avg_resolution_time,
                    "confidence_trend": metrics.confidence_trend.value,
                    "min_confidence": metrics.min_confidence,
                    "max_confidence": metrics.max_confidence
                }
            
            return report
            
        except Exception as e:
            self._logger.error(
                "performance_report_generation_failed",
                error=str(e)
            )
            raise PerformanceError(
                "report", "generation", f"Failed to generate performance report: {e}"
            )
    
    async def cleanup_old_metrics(self, days_to_keep: int = 30) -> int:
        """Clean up old metrics data."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
            removed_count = 0
            
            for selector_name in self.collector.get_all_selectors():
                for metric_type in list(self.collector._metrics[selector_name].keys()):
                    metrics = self.collector._metrics[selector_name][metric_type]
                    
                    # Remove old metrics
                    original_length = len(metrics)
                    while metrics and metrics[0].timestamp < cutoff_time:
                        metrics.popleft()
                    
                    removed_count += original_length - len(metrics)
            
            self._logger.info(
                "metrics_cleanup_completed",
                days_kept=days_to_keep,
                metrics_removed=removed_count
            )
            
            return removed_count
            
        except Exception as e:
            self._logger.error(
                "metrics_cleanup_failed",
                error=str(e)
            )
            raise PerformanceError(
                "cleanup", "metrics", f"Failed to cleanup metrics: {e}"
            )


# Browser-specific metrics

@dataclass
class BrowserMetrics:
    """Browser session performance metrics."""
    session_id: str
    browser_type: str
    session_duration_seconds: float = 0.0
    total_pages_created: int = 0
    total_contexts_created: int = 0
    peak_memory_mb: float = 0.0
    average_cpu_percent: float = 0.0
    total_navigation_time: float = 0.0
    failed_operations: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "session_id": self.session_id,
            "browser_type": self.browser_type,
            "session_duration_seconds": self.session_duration_seconds,
            "total_pages_created": self.total_pages_created,
            "total_contexts_created": self.total_contexts_created,
            "peak_memory_mb": self.peak_memory_mb,
            "average_cpu_percent": self.average_cpu_percent,
            "total_navigation_time": self.total_navigation_time,
            "failed_operations": self.failed_operations,
            "created_at": self.created_at.isoformat()
        }


class BrowserMetricsCollector:
    """Collects and manages browser-specific metrics."""
    
    def __init__(self):
        self._logger = get_logger("browser_metrics")
        self._session_metrics: Dict[str, BrowserMetrics] = {}
        self._resource_history: Dict[str, List[MetricPoint]] = defaultdict(list)
    
    def start_session_tracking(self, session_id: str, browser_type: str) -> None:
        """Start tracking metrics for a browser session."""
        self._session_metrics[session_id] = BrowserMetrics(
            session_id=session_id,
            browser_type=browser_type
        )
        
        self._logger.info(
            "browser_metrics_tracking_started",
            session_id=session_id,
            browser_type=browser_type
        )
    
    def record_page_created(self, session_id: str) -> None:
        """Record page creation event."""
        if session_id in self._session_metrics:
            self._session_metrics[session_id].total_pages_created += 1
    
    def record_context_created(self, session_id: str) -> None:
        """Record context creation event."""
        if session_id in self._session_metrics:
            self._session_metrics[session_id].total_contexts_created += 1
    
    def record_resource_usage(self, session_id: str, memory_mb: float, cpu_percent: float) -> None:
        """Record resource usage metrics."""
        if session_id in self._session_metrics:
            # Update peak memory
            if memory_mb > self._session_metrics[session_id].peak_memory_mb:
                self._session_metrics[session_id].peak_memory_mb = memory_mb
            
            # Add to resource history for averaging
            self._resource_history[session_id].append(
                MetricPoint(datetime.utcnow(), cpu_percent, {"type": "cpu"})
            )
            self._resource_history[session_id].append(
                MetricPoint(datetime.utcnow(), memory_mb, {"type": "memory"})
            )
            
            # Keep only last 100 points per session
            if len(self._resource_history[session_id]) > 200:
                self._resource_history[session_id] = self._resource_history[session_id][-200:]
    
    def record_navigation_time(self, session_id: str, navigation_time: float) -> None:
        """Record navigation time."""
        if session_id in self._session_metrics:
            self._session_metrics[session_id].total_navigation_time += navigation_time
    
    def record_failed_operation(self, session_id: str) -> None:
        """Record a failed operation."""
        if session_id in self._session_metrics:
            self._session_metrics[session_id].failed_operations += 1
    
    def finalize_session_metrics(self, session_id: str) -> Optional[BrowserMetrics]:
        """Finalize metrics for a completed session."""
        if session_id not in self._session_metrics:
            return None
        
        metrics = self._session_metrics[session_id]
        
        # Calculate session duration
        duration = (datetime.utcnow() - metrics.created_at).total_seconds()
        metrics.session_duration_seconds = duration
        
        # Calculate average CPU from history
        cpu_points = [p for p in self._resource_history[session_id] if p.metadata.get("type") == "cpu"]
        if cpu_points:
            metrics.average_cpu_percent = sum(p.value for p in cpu_points) / len(cpu_points)
        
        self._logger.info(
            "browser_metrics_finalized",
            session_id=session_id,
            duration_seconds=duration,
            total_pages=metrics.total_pages_created,
            peak_memory_mb=metrics.peak_memory_mb
        )
        
        return metrics
    
    def get_session_metrics(self, session_id: str) -> Optional[BrowserMetrics]:
        """Get metrics for a specific session."""
        return self._session_metrics.get(session_id)
    
    def get_all_session_metrics(self) -> List[BrowserMetrics]:
        """Get metrics for all sessions."""
        return list(self._session_metrics.values())
    
    def cleanup_session_metrics(self, session_id: str) -> None:
        """Clean up metrics for a session."""
        self._session_metrics.pop(session_id, None)
        self._resource_history.pop(session_id, None)
        
        self._logger.debug(
            "browser_metrics_cleaned",
            session_id=session_id
        )


# Global browser metrics collector instance
_browser_metrics_collector = BrowserMetricsCollector()


def get_browser_metrics_collector() -> BrowserMetricsCollector:
    """Get global browser metrics collector instance."""
    return _browser_metrics_collector


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    return performance_monitor
