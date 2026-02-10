"""
Confidence Score Collector

Specialized collector for quality metrics and confidence scores with
statistical analysis and trend tracking capabilities.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from statistics import mean, median, stdev
import math

from ..models import QualityMetrics
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryCollectionError
from ..configuration.logging import get_logger


@dataclass
class QualityStats:
    """Statistics for quality metrics."""
    total_measurements: int = 0
    successful_measurements: int = 0
    failed_measurements: int = 0
    success_rate: float = 0.0
    average_confidence: float = 0.0
    median_confidence: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 0.0
    std_deviation_confidence: float = 0.0
    confidence_distribution: Dict[str, int] = None
    elements_found_stats: Dict[str, float] = None
    last_measurement: Optional[datetime] = None
    
    def __post_init__(self):
        if self.confidence_distribution is None:
            self.confidence_distribution = {
                "very_low": 0,    # 0.0-0.2
                "low": 0,         # 0.2-0.4
                "medium": 0,      # 0.4-0.6
                "high": 0,        # 0.6-0.8
                "very_high": 0    # 0.8-1.0
            }
        if self.elements_found_stats is None:
            self.elements_found_stats = {}


class QualityCollector:
    """
    Specialized collector for quality metrics and confidence scores.
    
    Provides comprehensive quality tracking, confidence analysis,
    and success rate monitoring for selector operations.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize quality collector.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("quality_collector")
        
        # Quality configuration
        self.max_samples = config.get("max_quality_samples", 10000)
        self.confidence_thresholds = config.get("confidence_thresholds", {
            "very_low": 0.2,
            "low": 0.4,
            "medium": 0.6,
            "high": 0.8,
            "very_high": 1.0
        })
        
        # Quality storage
        self._quality_samples: List[Dict[str, Any]] = []
        self._quality_stats: Dict[str, QualityStats] = {}
        self._stats_lock = asyncio.Lock()
        
        # Quality thresholds
        self._thresholds = {
            "confidence_score": config.get("confidence_score_threshold", 0.5),
            "success_rate": config.get("success_rate_threshold", 0.8),
            "elements_found": config.get("elements_found_threshold", 1)
        }
        
        # Collection state
        self._enabled = True
        self._collection_count = 0
        self._error_count = 0
    
    async def collect_quality_metrics(
        self,
        selector_name: str,
        operation_type: str,
        success: bool,
        confidence_score: Optional[float] = None,
        elements_found: Optional[int] = None,
        strategy_success_rate: Optional[float] = None,
        drift_detected: Optional[bool] = None,
        fallback_used: Optional[bool] = None,
        validation_passed: Optional[bool] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> QualityMetrics:
        """
        Collect quality metrics for an operation.
        
        Args:
            selector_name: Name of selector
            operation_type: Type of operation
            success: Whether operation was successful
            confidence_score: Confidence score (0.0-1.0)
            elements_found: Number of elements found
            strategy_success_rate: Strategy success rate
            drift_detected: Whether drift was detected
            fallback_used: Whether fallback was used
            validation_passed: Whether validation passed
            additional_metrics: Additional quality metrics
            
        Returns:
            QualityMetrics instance
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            if not self._enabled:
                raise TelemetryCollectionError(
                    "Quality collector is disabled",
                    error_code="TEL-401"
                )
            
            # Validate confidence score
            if confidence_score is not None:
                confidence_score = max(0.0, min(1.0, confidence_score))
            
            # Create quality metrics
            metrics = QualityMetrics(
                confidence_score=confidence_score,
                success=success,
                elements_found=elements_found,
                strategy_success_rate=strategy_success_rate,
                drift_detected=drift_detected,
                fallback_used=fallback_used,
                validation_passed=validation_passed
            )
            
            # Store quality sample
            await self._store_quality_sample(
                selector_name,
                operation_type,
                metrics,
                additional_metrics
            )
            
            # Update statistics
            await self._update_statistics(selector_name, metrics)
            
            self._collection_count += 1
            
            self.logger.debug(
                "Quality metrics collected",
                selector_name=selector_name,
                operation_type=operation_type,
                success=success,
                confidence_score=confidence_score
            )
            
            return metrics
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(
                "Failed to collect quality metrics",
                selector_name=selector_name,
                operation_type=operation_type,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect quality metrics: {e}",
                error_code="TEL-402"
            )
    
    async def analyze_confidence_trends(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze confidence score trends over time.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            Confidence trend analysis
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if len(samples) < 2:
                return {"trend": "insufficient_data"}
            
            # Extract confidence scores
            confidence_scores = [
                sample["metrics"].get("confidence_score", 0)
                for sample in samples
                if sample["metrics"].get("confidence_score") is not None
            ]
            
            if len(confidence_scores) < 2:
                return {"trend": "insufficient_data"}
            
            # Calculate trend
            first_score = confidence_scores[0]
            last_score = confidence_scores[-1]
            
            if first_score == 0:
                trend_direction = "stable"
            else:
                percent_change = ((last_score - first_score) / first_score) * 100
                
                if abs(percent_change) < 5:
                    trend_direction = "stable"
                elif percent_change > 0:
                    trend_direction = "improving"
                else:
                    trend_direction = "degrading"
            
            # Calculate moving average
            window_size = min(10, len(confidence_scores))
            moving_averages = []
            
            for i in range(len(confidence_scores) - window_size + 1):
                window = confidence_scores[i:i + window_size]
                moving_averages.append(mean(window))
            
            return {
                "trend": trend_direction,
                "percent_change": percent_change if first_score > 0 else 0,
                "first_score": first_score,
                "last_score": last_score,
                "average_score": mean(confidence_scores),
                "median_score": median(confidence_scores),
                "min_score": min(confidence_scores),
                "max_score": max(confidence_scores),
                "samples_analyzed": len(confidence_scores),
                "moving_averages": moving_averages[-5:] if moving_averages else []
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze confidence trends",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def detect_quality_anomalies(
        self,
        selector_name: Optional[str] = None,
        confidence_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Detect quality anomalies based on confidence scores and success rates.
        
        Args:
            selector_name: Optional selector filter
            confidence_threshold: Threshold for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []
            
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name)
            
            if len(samples) < 10:
                return anomalies  # Not enough data for anomaly detection
            
            # Group by selector for individual analysis
            selector_samples = {}
            for sample in samples:
                sel_name = sample["selector_name"]
                if sel_name not in selector_samples:
                    selector_samples[sel_name] = []
                selector_samples[sel_name].append(sample)
            
            # Analyze each selector
            for sel_name, sel_samples in selector_samples.items():
                if len(sel_samples) < 5:
                    continue
                
                # Extract confidence scores
                confidence_scores = [
                    sample["metrics"].get("confidence_score", 0)
                    for sample in sel_samples
                    if sample["metrics"].get("confidence_score") is not None
                ]
                
                if not confidence_scores:
                    continue
                
                # Calculate statistics
                avg_confidence = mean(confidence_scores)
                
                # Detect low confidence anomalies
                if avg_confidence < confidence_threshold:
                    anomalies.append({
                        "selector_name": sel_name,
                        "anomaly_type": "low_confidence",
                        "average_confidence": avg_confidence,
                        "threshold": confidence_threshold,
                        "samples_count": len(confidence_scores),
                        "severity": "high" if avg_confidence < 0.1 else "medium",
                        "recent_samples": confidence_scores[-5:]
                    })
                
                # Detect sudden confidence drops
                if len(confidence_scores) >= 10:
                    recent_avg = mean(confidence_scores[-5:])
                    historical_avg = mean(confidence_scores[:-5])
                    
                    if historical_avg > 0 and recent_avg < historical_avg * 0.5:
                        anomalies.append({
                            "selector_name": sel_name,
                            "anomaly_type": "confidence_drop",
                            "recent_average": recent_avg,
                            "historical_average": historical_avg,
                            "drop_percentage": ((historical_avg - recent_avg) / historical_avg) * 100,
                            "severity": "high" if recent_avg < 0.2 else "medium"
                        })
                
                # Detect success rate anomalies
                success_count = sum(
                    1 for sample in sel_samples
                    if sample["metrics"].get("success", False)
                )
                success_rate = success_count / len(sel_samples)
                
                if success_rate < 0.5:  # Less than 50% success rate
                    anomalies.append({
                        "selector_name": sel_name,
                        "anomaly_type": "low_success_rate",
                        "success_rate": success_rate,
                        "success_count": success_count,
                        "total_count": len(sel_samples),
                        "severity": "high" if success_rate < 0.2 else "medium"
                    })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(
                "Failed to detect quality anomalies",
                selector_name=selector_name,
                error=str(e)
            )
            return []
    
    async def get_quality_distribution(
        self,
        selector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get distribution of confidence scores.
        
        Args:
            selector_name: Optional selector filter
            
        Returns:
            Confidence score distribution
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name)
            
            if not samples:
                return {}
            
            # Extract confidence scores
            confidence_scores = [
                sample["metrics"].get("confidence_score", 0)
                for sample in samples
                if sample["metrics"].get("confidence_score") is not None
            ]
            
            if not confidence_scores:
                return {}
            
            # Calculate distribution
            distribution = {
                "very_low": 0,    # 0.0-0.2
                "low": 0,         # 0.2-0.4
                "medium": 0,      # 0.4-0.6
                "high": 0,        # 0.6-0.8
                "very_high": 0    # 0.8-1.0
            }
            
            for score in confidence_scores:
                if score < 0.2:
                    distribution["very_low"] += 1
                elif score < 0.4:
                    distribution["low"] += 1
                elif score < 0.6:
                    distribution["medium"] += 1
                elif score < 0.8:
                    distribution["high"] += 1
                else:
                    distribution["very_high"] += 1
            
            # Convert to percentages
            total_scores = len(confidence_scores)
            distribution_percentages = {
                key: (count / total_scores) * 100
                for key, count in distribution.items()
            }
            
            return {
                "total_scores": total_scores,
                "distribution": distribution,
                "distribution_percentages": distribution_percentages,
                "average_score": mean(confidence_scores),
                "median_score": median(confidence_scores),
                "min_score": min(confidence_scores),
                "max_score": max(confidence_scores)
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get quality distribution",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_success_rate_analysis(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze success rates over time.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            Success rate analysis
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Group samples by time periods
            time_periods = self._group_samples_by_time_period(samples)
            
            # Calculate success rates for each period
            success_rates = []
            for period_samples in time_periods:
                success_count = sum(
                    1 for sample in period_samples
                    if sample["metrics"].get("success", False)
                )
                success_rate = success_count / len(period_samples)
                success_rates.append(success_rate)
            
            if not success_rates:
                return {}
            
            # Calculate trend
            if len(success_rates) >= 2:
                first_rate = success_rates[0]
                last_rate = success_rates[-1]
                
                if first_rate == 0:
                    trend = "stable"
                else:
                    percent_change = ((last_rate - first_rate) / first_rate) * 100
                    
                    if abs(percent_change) < 5:
                        trend = "stable"
                    elif percent_change > 0:
                        trend = "improving"
                    else:
                        trend = "declining"
            else:
                trend = "insufficient_data"
            
            return {
                "trend": trend,
                "average_success_rate": mean(success_rates),
                "min_success_rate": min(success_rates),
                "max_success_rate": max(success_rates),
                "periods_analyzed": len(success_rates),
                "success_rates": success_rates,
                "total_samples": len(samples)
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get success rate analysis",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_quality_statistics(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive quality statistics.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for statistics
            
        Returns:
            Quality statistics
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Extract metrics
            confidence_scores = [
                sample["metrics"].get("confidence_score", 0)
                for sample in samples
                if sample["metrics"].get("confidence_score") is not None
            ]
            
            success_count = sum(
                1 for sample in samples
                if sample["metrics"].get("success", False)
            )
            
            elements_found = [
                sample["metrics"].get("elements_found", 0)
                for sample in samples
                if sample["metrics"].get("elements_found") is not None
            ]
            
            # Calculate statistics
            stats = {
                "total_samples": len(samples),
                "successful_samples": success_count,
                "failed_samples": len(samples) - success_count,
                "success_rate": success_count / len(samples),
                "samples_with_confidence": len(confidence_scores),
                "samples_with_elements": len(elements_found)
            }
            
            if confidence_scores:
                stats.update({
                    "average_confidence": mean(confidence_scores),
                    "median_confidence": median(confidence_scores),
                    "min_confidence": min(confidence_scores),
                    "max_confidence": max(confidence_scores),
                    "std_deviation_confidence": stdev(confidence_scores) if len(confidence_scores) > 1 else 0
                })
            
            if elements_found:
                stats.update({
                    "average_elements_found": mean(elements_found),
                    "median_elements_found": median(elements_found),
                    "min_elements_found": min(elements_found),
                    "max_elements_found": max(elements_found)
                })
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Failed to get quality statistics",
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
        return {
            "total_collections": self._collection_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._collection_count),
            "samples_stored": len(self._quality_samples),
            "selectors_tracked": len(set(s["selector_name"] for s in self._quality_samples)),
            "enabled": self._enabled,
            "max_samples": self.max_samples
        }
    
    async def enable_collection(self) -> None:
        """Enable quality collection."""
        self._enabled = True
        self.logger.info("Quality collection enabled")
    
    async def disable_collection(self) -> None:
        """Disable quality collection."""
        self._enabled = False
        self.logger.info("Quality collection disabled")
    
    async def clear_samples(self, selector_name: Optional[str] = None) -> int:
        """
        Clear quality samples.
        
        Args:
            selector_name: Optional selector filter
            
        Returns:
            Number of samples cleared
        """
        async with self._stats_lock:
            if selector_name:
                original_count = len(self._quality_samples)
                self._quality_samples = [
                    sample for sample in self._quality_samples
                    if sample["selector_name"] != selector_name
                ]
                cleared_count = original_count - len(self._quality_samples)
                
                # Clear selector statistics
                if selector_name in self._quality_stats:
                    del self._quality_stats[selector_name]
            else:
                cleared_count = len(self._quality_samples)
                self._quality_samples.clear()
                self._quality_stats.clear()
            
            self.logger.info(
                "Quality samples cleared",
                selector_name=selector_name or "all",
                cleared_count=cleared_count
            )
            
            return cleared_count
    
    # Private methods
    
    async def _store_quality_sample(
        self,
        selector_name: str,
        operation_type: str,
        metrics: QualityMetrics,
        additional_metrics: Optional[Dict[str, Any]]
    ) -> None:
        """Store quality sample."""
        sample = {
            "selector_name": selector_name,
            "operation_type": operation_type,
            "metrics": metrics.to_dict(),
            "additional_metrics": additional_metrics or {},
            "timestamp": datetime.utcnow()
        }
        
        async with self._stats_lock:
            self._quality_samples.append(sample)
            
            # Limit sample size
            if len(self._quality_samples) > self.max_samples:
                self._quality_samples = self._quality_samples[-self.max_samples:]
    
    async def _update_statistics(self, selector_name: str, metrics: QualityMetrics) -> None:
        """Update quality statistics for selector."""
        async with self._stats_lock:
            if selector_name not in self._quality_stats:
                self._quality_stats[selector_name] = QualityStats()
            
            stats = self._quality_stats[selector_name]
            
            # Update basic stats
            stats.total_measurements += 1
            stats.last_measurement = datetime.utcnow()
            
            if metrics.success:
                stats.successful_measurements += 1
            else:
                stats.failed_measurements += 1
            
            # Update success rate
            stats.success_rate = stats.successful_measurements / stats.total_measurements
            
            # Update confidence statistics
            if metrics.confidence_score is not None:
                await self._update_confidence_stats(selector_name, metrics.confidence_score)
            
            # Update elements found statistics
            if metrics.elements_found is not None:
                await self._update_elements_stats(selector_name, metrics.elements_found)
    
    async def _update_confidence_stats(self, selector_name: str, confidence_score: float) -> None:
        """Update confidence statistics for selector."""
        stats = self._quality_stats[selector_name]
        
        # Get all confidence scores for this selector
        confidence_scores = [
            sample["metrics"].get("confidence_score", 0)
            for sample in self._quality_samples
            if sample["selector_name"] == selector_name and
            sample["metrics"].get("confidence_score") is not None
        ]
        
        if confidence_scores:
            stats.average_confidence = mean(confidence_scores)
            stats.median_confidence = median(confidence_scores)
            stats.min_confidence = min(confidence_scores)
            stats.max_confidence = max(confidence_scores)
            
            if len(confidence_scores) > 1:
                stats.std_deviation_confidence = stdev(confidence_scores)
            
            # Update distribution
            stats.confidence_distribution = {
                "very_low": 0,
                "low": 0,
                "medium": 0,
                "high": 0,
                "very_high": 0
            }
            
            for score in confidence_scores:
                if score < 0.2:
                    stats.confidence_distribution["very_low"] += 1
                elif score < 0.4:
                    stats.confidence_distribution["low"] += 1
                elif score < 0.6:
                    stats.confidence_distribution["medium"] += 1
                elif score < 0.8:
                    stats.confidence_distribution["high"] += 1
                else:
                    stats.confidence_distribution["very_high"] += 1
    
    async def _update_elements_stats(self, selector_name: str, elements_found: int) -> None:
        """Update elements found statistics for selector."""
        stats = self._quality_stats[selector_name]
        
        # Get all elements found for this selector
        elements_counts = [
            sample["metrics"].get("elements_found", 0)
            for sample in self._quality_samples
            if sample["selector_name"] == selector_name and
            sample["metrics"].get("elements_found") is not None
        ]
        
        if elements_counts:
            stats.elements_found_stats = {
                "average": mean(elements_counts),
                "median": median(elements_counts),
                "min": min(elements_counts),
                "max": max(elements_counts),
                "total": sum(elements_counts)
            }
    
    async def _get_filtered_samples(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered quality samples."""
        samples = self._quality_samples.copy()
        
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
    
    def _group_samples_by_time_period(self, samples: List[Dict[str, Any]], period_minutes: int = 30) -> List[List[Dict[str, Any]]]:
        """Group samples by time periods."""
        if not samples:
            return []
        
        # Sort samples by timestamp
        sorted_samples = sorted(samples, key=lambda x: x["timestamp"])
        
        # Group by time period
        periods = []
        current_period = []
        period_start = sorted_samples[0]["timestamp"]
        period_end = period_start + timedelta(minutes=period_minutes)
        
        for sample in sorted_samples:
            if sample["timestamp"] <= period_end:
                current_period.append(sample)
            else:
                if current_period:
                    periods.append(current_period)
                current_period = [sample]
                period_start = sample["timestamp"]
                period_end = period_start + timedelta(minutes=period_minutes)
        
        if current_period:
            periods.append(current_period)
        
        return periods
