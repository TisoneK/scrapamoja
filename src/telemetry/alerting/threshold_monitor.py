"""
Threshold Monitor

Real-time threshold monitoring with configurable thresholds,
dynamic adjustment, and performance tracking.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

from ..interfaces import Alert, AlertSeverity
from ..models import TelemetryEvent, PerformanceMetrics, QualityMetrics
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class ThresholdType(Enum):
    """Threshold type enumeration."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"


class ComparisonOperator(Enum):
    """Comparison operator enumeration."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUALS = "=="
    NOT_EQUALS = "!="


@dataclass
class ThresholdConfig:
    """Threshold configuration."""
    threshold_id: str
    name: str
    description: str
    metric_name: str
    threshold_type: ThresholdType
    comparison: ComparisonOperator
    threshold_value: float
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 5
    evaluation_window_minutes: int = 10
    min_samples: int = 3
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_evaluated: Optional[datetime] = None
    evaluation_count: int = 0
    trigger_count: int = 0


@dataclass
class ThresholdEvaluation:
    """Result of threshold evaluation."""
    threshold_id: str
    metric_name: str
    current_value: float
    threshold_value: float
    comparison: ComparisonOperator
    triggered: bool
    severity: AlertSeverity
    exceedance_ratio: float
    samples_evaluated: int
    evaluation_time: datetime
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThresholdStatistics:
    """Threshold monitoring statistics."""
    total_evaluations: int = 0
    total_triggers: int = 0
    triggers_by_threshold: Dict[str, int] = field(default_factory=dict)
    triggers_by_severity: Dict[str, int] = field(default_factory=dict)
    average_evaluation_time_ms: float = 0.0
    most_triggered_threshold: str = ""
    highest_exceedance_ratio: float = 0.0
    last_evaluation: Optional[datetime] = None


class ThresholdMonitor:
    """
    Real-time threshold monitoring with dynamic adjustment.
    
    Provides comprehensive threshold monitoring with configurable
    thresholds, dynamic adjustment, and performance tracking.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize threshold monitor.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("threshold_monitor")
        
        # Monitor configuration
        self.enabled = config.get("threshold_monitoring_enabled", True)
        self.evaluation_interval_seconds = config.get("threshold_evaluation_interval_seconds", 30)
        self.max_evaluations = config.get("max_threshold_evaluations", 10000)
        
        # Threshold storage
        self._thresholds: Dict[str, ThresholdConfig] = {}
        self._evaluation_history: List[ThresholdEvaluation] = []
        self._threshold_lock = asyncio.Lock()
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._statistics = ThresholdStatistics()
        
        # Callbacks
        self._trigger_callbacks: List[Callable] = []
        self._evaluation_callbacks: List[Callable] = []
        
        # Initialize default thresholds
        self._initialize_default_thresholds()
        
        # Start monitoring if enabled
        if self.enabled:
            self._start_monitoring()
    
    async def add_threshold(self, threshold: ThresholdConfig) -> bool:
        """
        Add a threshold configuration.
        
        Args:
            threshold: Threshold configuration
            
        Returns:
            True if successfully added
        """
        try:
            async with self._threshold_lock:
                self._thresholds[threshold.threshold_id] = threshold
            
            self.logger.info(
                "Threshold added",
                threshold_id=threshold.threshold_id,
                metric_name=threshold.metric_name,
                threshold_value=threshold.threshold_value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add threshold",
                threshold_id=threshold.threshold_id,
                error=str(e)
            )
            return False
    
    async def remove_threshold(self, threshold_id: str) -> bool:
        """
        Remove a threshold configuration.
        
        Args:
            threshold_id: Threshold ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._threshold_lock:
                if threshold_id in self._thresholds:
                    del self._thresholds[threshold_id]
                    
                    self.logger.info(
                        "Threshold removed",
                        threshold_id=threshold_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove threshold",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def update_threshold(self, threshold_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a threshold configuration.
        
        Args:
            threshold_id: Threshold ID to update
            updates: Updates to apply
            
        Returns:
            True if successfully updated
        """
        try:
            async with self._threshold_lock:
                if threshold_id not in self._thresholds:
                    return False
                
                threshold = self._thresholds[threshold_id]
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(threshold, key):
                        setattr(threshold, key, value)
                
                self.logger.info(
                    "Threshold updated",
                    threshold_id=threshold_id,
                    updates=updates
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to update threshold",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def evaluate_threshold(
        self,
        threshold_id: str,
        current_value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ThresholdEvaluation]:
        """
        Evaluate a specific threshold.
        
        Args:
            threshold_id: Threshold ID to evaluate
            current_value: Current metric value
            context: Additional context
            
        Returns:
            Threshold evaluation result or None if threshold not found
        """
        try:
            async with self._threshold_lock:
                if threshold_id not in self._thresholds:
                    return None
                
                threshold = self._thresholds[threshold_id]
                
                if not threshold.enabled:
                    return None
                
                # Check cooldown
                if self._is_in_cooldown(threshold):
                    return None
                
                # Perform evaluation
                evaluation = self._perform_evaluation(threshold, current_value, context)
                
                # Update threshold statistics
                threshold.last_evaluated = evaluation.evaluation_time
                threshold.evaluation_count += 1
                
                if evaluation.triggered:
                    threshold.trigger_count += 1
                    threshold.last_triggered = evaluation.evaluation_time
                
                # Update global statistics
                self._update_statistics(evaluation)
                
                # Store evaluation
                self._evaluation_history.append(evaluation)
                
                # Limit history size
                if len(self._evaluation_history) > self.max_evaluations:
                    self._evaluation_history = self._evaluation_history[-self.max_evaluations:]
                
                # Execute callbacks
                await self._execute_evaluation_callbacks(evaluation)
                
                if evaluation.triggered:
                    await self._execute_trigger_callbacks(evaluation)
                
                return evaluation
                
        except Exception as e:
            self.logger.error(
                "Failed to evaluate threshold",
                threshold_id=threshold_id,
                error=str(e)
            )
            return None
    
    async def evaluate_all_thresholds(
        self,
        metrics: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ThresholdEvaluation]:
        """
        Evaluate all applicable thresholds.
        
        Args:
            metrics: Dictionary of metric values
            context: Additional context
            
        Returns:
            List of threshold evaluations
        """
        try:
            evaluations = []
            
            async with self._threshold_lock:
                for threshold_id, threshold in self._thresholds.items():
                    if not threshold.enabled:
                        continue
                    
                    if threshold.metric_name not in metrics:
                        continue
                    
                    # Check cooldown
                    if self._is_in_cooldown(threshold):
                        continue
                    
                    # Evaluate threshold
                    evaluation = self._perform_evaluation(
                        threshold,
                        metrics[threshold.metric_name],
                        context
                    )
                    
                    if evaluation:
                        evaluations.append(evaluation)
                        
                        # Update threshold statistics
                        threshold.last_evaluated = evaluation.evaluation_time
                        threshold.evaluation_count += 1
                        
                        if evaluation.triggered:
                            threshold.trigger_count += 1
                            threshold.last_triggered = evaluation.evaluation_time
                        
                        # Update global statistics
                        self._update_statistics(evaluation)
                        
                        # Store evaluation
                        self._evaluation_history.append(evaluation)
                        
                        # Execute callbacks
                        await self._execute_evaluation_callbacks(evaluation)
                        
                        if evaluation.triggered:
                            await self._execute_trigger_callbacks(evaluation)
            
            # Limit history size
            if len(self._evaluation_history) > self.max_evaluations:
                self._evaluation_history = self._evaluation_history[-self.max_evaluations:]
            
            return evaluations
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate all thresholds",
                error=str(e)
            )
            return []
    
    async def get_threshold_statistics(self) -> Dict[str, Any]:
        """
        Get threshold monitoring statistics.
        
        Returns:
            Threshold monitoring statistics
        """
        try:
            async with self._threshold_lock:
                stats = {
                    "total_thresholds": len(self._thresholds),
                    "enabled_thresholds": len([t for t in self._thresholds.values() if t.enabled]),
                    "total_evaluations": self._statistics.total_evaluations,
                    "total_triggers": self._statistics.total_triggers,
                    "triggers_by_threshold": dict(self._statistics.triggers_by_threshold),
                    "triggers_by_severity": dict(self._statistics.triggers_by_severity),
                    "average_evaluation_time_ms": self._statistics.average_evaluation_time_ms,
                    "most_triggered_threshold": self._statistics.most_triggered_threshold,
                    "highest_exceedance_ratio": self._statistics.highest_exceedance_ratio,
                    "last_evaluation": self._statistics.last_evaluation,
                    "evaluation_history_size": len(self._evaluation_history)
                }
                
                return stats
                
        except Exception as e:
            self.logger.error(
                "Failed to get threshold statistics",
                error=str(e)
            )
            return {}
    
    async def get_threshold_configurations(self) -> List[ThresholdConfig]:
        """
        Get all threshold configurations.
        
        Returns:
            List of threshold configurations
        """
        try:
            async with self._threshold_lock:
                return list(self._thresholds.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get threshold configurations",
                error=str(e)
            )
            return []
    
    async def get_evaluation_history(
        self,
        threshold_id: Optional[str] = None,
        triggered_only: bool = False,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[ThresholdEvaluation]:
        """
        Get evaluation history with filtering.
        
        Args:
            threshold_id: Optional threshold ID filter
            triggered_only: Filter for triggered evaluations only
            limit: Optional limit on number of evaluations
            time_window: Optional time window for evaluations
            
        Returns:
            List of threshold evaluations
        """
        try:
            async with self._threshold_lock:
                evaluations = self._evaluation_history.copy()
                
                # Apply filters
                if threshold_id:
                    evaluations = [e for e in evaluations if e.threshold_id == threshold_id]
                
                if triggered_only:
                    evaluations = [e for e in evaluations if e.triggered]
                
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    evaluations = [e for e in evaluations if e.evaluation_time >= cutoff_time]
                
                # Sort by timestamp (newest first)
                evaluations.sort(key=lambda x: x.evaluation_time, reverse=True)
                
                # Apply limit
                if limit:
                    evaluations = evaluations[:limit]
                
                return evaluations
                
        except Exception as e:
            self.logger.error(
                "Failed to get evaluation history",
                error=str(e)
            )
            return []
    
    async def adjust_threshold_dynamically(
        self,
        threshold_id: str,
        adjustment_factor: float,
        reason: str
    ) -> bool:
        """
        Dynamically adjust a threshold value.
        
        Args:
            threshold_id: Threshold ID to adjust
            adjustment_factor: Factor to multiply threshold by
            reason: Reason for adjustment
            
        Returns:
            True if successfully adjusted
        """
        try:
            async with self._threshold_lock:
                if threshold_id not in self._thresholds:
                    return False
                
                threshold = self._thresholds[threshold_id]
                
                if threshold.threshold_type != ThresholdType.DYNAMIC:
                    return False
                
                old_value = threshold.threshold_value
                new_value = old_value * adjustment_factor
                
                threshold.threshold_value = new_value
                
                self.logger.info(
                    "Threshold dynamically adjusted",
                    threshold_id=threshold_id,
                    old_value=old_value,
                    new_value=new_value,
                    adjustment_factor=adjustment_factor,
                    reason=reason
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to adjust threshold dynamically",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def enable_monitoring(self) -> None:
        """Enable threshold monitoring."""
        self.enabled = True
        if not self._monitoring_task or self._monitoring_task.done():
            self._start_monitoring()
        
        self.logger.info("Threshold monitoring enabled")
    
    async def disable_monitoring(self) -> None:
        """Disable threshold monitoring."""
        self.enabled = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
        
        self.logger.info("Threshold monitoring disabled")
    
    def add_trigger_callback(self, callback: Callable) -> None:
        """
        Add callback for threshold triggers.
        
        Args:
            callback: Callback function
        """
        self._trigger_callbacks.append(callback)
    
    def add_evaluation_callback(self, callback: Callable) -> None:
        """
        Add callback for threshold evaluations.
        
        Args:
            callback: Callback function
        """
        self._evaluation_callbacks.append(callback)
    
    # Private methods
    
    def _initialize_default_thresholds(self) -> None:
        """Initialize default threshold configurations."""
        default_thresholds = [
            ThresholdConfig(
                threshold_id="resolution_time_high",
                name="High Resolution Time",
                description="Alert when resolution time exceeds 5 seconds",
                metric_name="resolution_time_ms",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.GREATER_THAN,
                threshold_value=5000.0,
                severity=AlertSeverity.WARNING,
                tags=["performance", "resolution"]
            ),
            ThresholdConfig(
                threshold_id="resolution_time_critical",
                name="Critical Resolution Time",
                description="Alert when resolution time exceeds 10 seconds",
                metric_name="resolution_time_ms",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.GREATER_THAN,
                threshold_value=10000.0,
                severity=AlertSeverity.ERROR,
                tags=["performance", "resolution", "critical"]
            ),
            ThresholdConfig(
                threshold_id="confidence_score_low",
                name="Low Confidence Score",
                description="Alert when confidence score falls below 0.5",
                metric_name="confidence_score",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.LESS_THAN,
                threshold_value=0.5,
                severity=AlertSeverity.WARNING,
                tags=["quality", "confidence"]
            ),
            ThresholdConfig(
                threshold_id="confidence_score_critical",
                name="Critical Confidence Score",
                description="Alert when confidence score falls below 0.2",
                metric_name="confidence_score",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.LESS_THAN,
                threshold_value=0.2,
                severity=AlertSeverity.ERROR,
                tags=["quality", "confidence", "critical"]
            ),
            ThresholdConfig(
                threshold_id="error_rate_high",
                name="High Error Rate",
                description="Alert when error rate exceeds 10%",
                metric_name="error_rate",
                threshold_type=ThresholdType.DYNAMIC,
                comparison=ComparisonOperator.GREATER_THAN,
                threshold_value=0.1,
                severity=AlertSeverity.WARNING,
                tags=["error", "rate"]
            ),
            ThresholdConfig(
                threshold_id="strategy_switches_excessive",
                name="Excessive Strategy Switches",
                description="Alert when strategy switches exceed 3",
                metric_name="strategy_switches_count",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.GREATER_THAN,
                threshold_value=3.0,
                severity=AlertSeverity.WARNING,
                tags=["strategy", "switches"]
            )
        ]
        
        for threshold in default_thresholds:
            self._thresholds[threshold.threshold_id] = threshold
    
    def _start_monitoring(self) -> None:
        """Start the monitoring loop."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for evaluation interval or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.evaluation_interval_seconds
                )
                
                if self._shutdown_event.is_set():
                    break
                
                # Perform periodic evaluation
                await self._perform_periodic_evaluation()
                
            except asyncio.TimeoutError:
                # Timeout - continue with next iteration
                continue
            except Exception as e:
                self.logger.error(
                    "Monitoring loop error",
                    error=str(e)
                )
                await asyncio.sleep(1.0)  # Brief pause before retrying
    
    async def _perform_periodic_evaluation(self) -> None:
        """Perform periodic evaluation of dynamic thresholds."""
        try:
            # This would typically evaluate metrics from a metrics collector
            # For now, we'll just log that periodic evaluation occurred
            self.logger.debug("Periodic threshold evaluation completed")
            
        except Exception as e:
            self.logger.error(
                "Failed to perform periodic evaluation",
                error=str(e)
            )
    
    def _perform_evaluation(
        self,
        threshold: ThresholdConfig,
        current_value: float,
        context: Optional[Dict[str, Any]]
    ) -> ThresholdEvaluation:
        """Perform threshold evaluation."""
        evaluation_start = datetime.utcnow()
        
        # Evaluate condition
        triggered = self._evaluate_condition(
            threshold.comparison,
            current_value,
            threshold.threshold_value
        )
        
        # Calculate exceedance ratio
        if triggered:
            if threshold.comparison in [ComparisonOperator.GREATER_THAN, ComparisonOperator.GREATER_EQUAL]:
                exceedance_ratio = current_value / threshold.threshold_value
            elif threshold.comparison in [ComparisonOperator.LESS_THAN, ComparisonOperator.LESS_EQUAL]:
                exceedance_ratio = threshold.threshold_value / current_value
            else:
                exceedance_ratio = 1.0
        else:
            exceedance_ratio = 0.0
        
        return ThresholdEvaluation(
            threshold_id=threshold.threshold_id,
            metric_name=threshold.metric_name,
            current_value=current_value,
            threshold_value=threshold.threshold_value,
            comparison=threshold.comparison,
            triggered=triggered,
            severity=threshold.severity,
            exceedance_ratio=exceedance_ratio,
            samples_evaluated=1,
            evaluation_time=evaluation_start,
            context=context or {}
        )
    
    def _evaluate_condition(
        self,
        comparison: ComparisonOperator,
        current_value: float,
        threshold_value: float
    ) -> bool:
        """Evaluate comparison condition."""
        if comparison == ComparisonOperator.GREATER_THAN:
            return current_value > threshold_value
        elif comparison == ComparisonOperator.LESS_THAN:
            return current_value < threshold_value
        elif comparison == ComparisonOperator.GREATER_EQUAL:
            return current_value >= threshold_value
        elif comparison == ComparisonOperator.LESS_EQUAL:
            return current_value <= threshold_value
        elif comparison == ComparisonOperator.EQUALS:
            return abs(current_value - threshold_value) < 0.001
        elif comparison == ComparisonOperator.NOT_EQUALS:
            return abs(current_value - threshold_value) >= 0.001
        else:
            return False
    
    def _is_in_cooldown(self, threshold: ThresholdConfig) -> bool:
        """Check if threshold is in cooldown period."""
        if not threshold.last_triggered:
            return False
        
        cooldown_end = threshold.last_triggered + timedelta(minutes=threshold.cooldown_minutes)
        return datetime.utcnow() < cooldown_end
    
    def _update_statistics(self, evaluation: ThresholdEvaluation) -> None:
        """Update threshold statistics."""
        self._statistics.total_evaluations += 1
        self._statistics.last_evaluation = evaluation.evaluation_time
        
        if evaluation.triggered:
            self._statistics.total_triggers += 1
            
            # Update triggers by threshold
            if evaluation.threshold_id not in self._statistics.triggers_by_threshold:
                self._statistics.triggers_by_threshold[evaluation.threshold_id] = 0
            self._statistics.triggers_by_threshold[evaluation.threshold_id] += 1
            
            # Update triggers by severity
            severity_name = evaluation.severity.value
            if severity_name not in self._statistics.triggers_by_severity:
                self._statistics.triggers_by_severity[severity_name] = 0
            self._statistics.triggers_by_severity[severity_name] += 1
            
            # Update most triggered threshold
            if self._statistics.triggers_by_threshold:
                self._statistics.most_triggered_threshold = max(
                    self._statistics.triggers_by_threshold,
                    key=self._statistics.triggers_by_threshold.get
                )
            
            # Update highest exceedance ratio
            if evaluation.exceedance_ratio > self._statistics.highest_exceedance_ratio:
                self._statistics.highest_exceedance_ratio = evaluation.exceedance_ratio
    
    async def _execute_trigger_callbacks(self, evaluation: ThresholdEvaluation) -> None:
        """Execute trigger callbacks."""
        for callback in self._trigger_callbacks:
            try:
                await callback(evaluation)
            except Exception as e:
                self.logger.error(
                    "Trigger callback failed",
                    threshold_id=evaluation.threshold_id,
                    error=str(e)
                )
    
    async def _execute_evaluation_callbacks(self, evaluation: ThresholdEvaluation) -> None:
        """Execute evaluation callbacks."""
        for callback in self._evaluation_callbacks:
            try:
                await callback(evaluation)
            except Exception as e:
                self.logger.error(
                    "Evaluation callback failed",
                    threshold_id=evaluation.threshold_id,
                    error=str(e)
                )
