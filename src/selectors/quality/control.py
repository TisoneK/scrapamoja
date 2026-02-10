"""
Quality control automation for Selector Engine.

Provides automated quality gate enforcement, adaptive threshold adjustment,
and comprehensive quality monitoring as specified in the API contracts.
"""

import asyncio
import json
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path

from src.observability.logger import get_logger
from src.observability.events import publish_event
from src.utils.exceptions import (
    QualityControlError, ValidationError, ConfigurationError,
    ConfidenceThresholdError
)
from src.models.selector_models import (
    SemanticSelector, SelectorResult, ValidationResult, ValidationRule
)
from src.selectors.context import DOMContext
from src.selectors.confidence.thresholds import get_threshold_manager
from src.config.settings import get_config


@dataclass
class QualityGateResult:
    """Result of quality gate evaluation."""
    selector_name: str
    context: str
    passed: bool
    confidence_score: float
    resolution_time: float
    validation_score: float
    strategies_used: int
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QualityMetrics:
    """Quality metrics for a selector."""
    selector_name: str
    total_evaluations: int
    pass_rate: float
    average_confidence: float
    average_resolution_time: float
    average_validation_score: float
    last_evaluation: Optional[datetime]
    last_violation: Optional[datetime]
    violation_count: int
    trend_direction: str  # "improving", "declining", "stable"
    trend_confidence: float


@dataclass
class QualityAlert:
    """Quality alert notification."""
    selector_name: str
    issue_type: str
    severity: str  # "info", "warning", "error", "critical"
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    context: str


@dataclass
class AdaptiveQualityResult:
    """Result of adaptive quality evaluation."""
    selector_name: str
    original_threshold: float
    adapted_threshold: float
    adaptation_reason: str
    adaptation_confidence: float
    performance_metrics: Dict[str, Any]
    passed: bool


class QualityControlManager:
    """Manages quality control automation and monitoring."""
    
    def __init__(self):
        self._logger = get_logger("quality_control")
        self._config = get_config()
        self._threshold_manager = get_threshold_manager()
        
        # Quality gates configuration
        self._quality_gates: Dict[str, Dict[str, Any]] = {
            "production": {
                "min_confidence": 0.85,
                "max_resolution_time": 1000.0,
                "min_validation_score": 0.9,
                "required_strategies": 2,
                "max_violations": 0
            },
            "staging": {
                "min_confidence": 0.75,
                "max_resolution_time": 1500.0,
                "min_validation_score": 0.8,
                "required_strategies": 2,
                "max_violations": 1
            },
            "development": {
                "min_confidence": 0.6,
                "max_resolution_time": 2000.0,
                "min_validation_score": 0.7,
                "required_strategies": 1,
                "max_violations": 2
            },
            "testing": {
                "min_confidence": 0.5,
                "max_resolution_time": 3000.0,
                "min_validation_score": 0.6,
                "required_strategies": 1,
                "max_violations": 3
            }
        }
        
        # Quality metrics storage
        self._quality_metrics: Dict[str, QualityMetrics] = {}
        self._evaluation_history: List[QualityGateResult] = []
        self._alerts: List[QualityAlert] = []
        
        # Alert handlers
        self._alert_handlers: List[Callable] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load existing metrics
        self._load_metrics()
        
        self._logger.info("QualityControlManager initialized")
    
    async def evaluate_quality(self, selector: SemanticSelector, context: DOMContext,
                             gate_name: str = "production") -> QualityGateResult:
        """
        Evaluate selector quality against quality gate.
        
        Args:
            selector: Selector to evaluate
            context: DOM context for evaluation
            gate_name: Quality gate name
            
        Returns:
            Quality gate evaluation result
        """
        try:
            # Get quality gate configuration
            gate_config = self._quality_gates.get(gate_name, self._quality_gates["production"])
            
            # Resolve selector to get actual metrics
            from src.selectors.engine import SelectorEngine
            engine = SelectorEngine()
            
            # Register selector if not already registered
            if selector.name not in engine._selector_registry:
                await engine.register_selector(selector)
            
            # Resolve selector
            result = await engine.resolve(selector.name, context)
            
            # Evaluate against quality gate
            violations = []
            recommendations = []
            
            # Check confidence score
            if result.confidence_score < gate_config["min_confidence"]:
                violations.append({
                    "type": "low_confidence",
                    "actual": result.confidence_score,
                    "required": gate_config["min_confidence"],
                    "severity": "error" if result.confidence_score < gate_config["min_confidence"] * 0.8 else "warning"
                })
                recommendations.append(f"Improve selector confidence from {result.confidence_score:.2f} to {gate_config['min_confidence']:.2f}")
            
            # Check resolution time
            if result.resolution_time > gate_config["max_resolution_time"]:
                violations.append({
                    "type": "slow_resolution",
                    "actual": result.resolution_time,
                    "required": gate_config["max_resolution_time"],
                    "severity": "warning"
                })
                recommendations.append(f"Optimize resolution time from {result.resolution_time:.0f}ms to {gate_config['max_resolution_time']:.0f}ms")
            
            # Check validation score
            validation_score = self._calculate_validation_score(result.validation_results)
            if validation_score < gate_config["min_validation_score"]:
                violations.append({
                    "type": "validation_failed",
                    "actual": validation_score,
                    "required": gate_config["min_validation_score"],
                    "severity": "error"
                })
                recommendations.append(f"Improve validation rules to achieve score of {gate_config['min_validation_score']:.2f}")
            
            # Check strategies used (simulated)
            strategies_used = len(selector.strategies)
            if strategies_used < gate_config["required_strategies"]:
                violations.append({
                    "type": "insufficient_strategies",
                    "actual": strategies_used,
                    "required": gate_config["required_strategies"],
                    "severity": "warning"
                })
                recommendations.append(f"Add {gate_config['required_strategies'] - strategies_used} more strategies")
            
            # Determine if passed
            passed = len(violations) <= gate_config["max_violations"] and not any(
                v["severity"] == "error" for v in violations
            )
            
            # Create result
            quality_result = QualityGateResult(
                selector_name=selector.name,
                context=gate_name,
                passed=passed,
                confidence_score=result.confidence_score,
                resolution_time=result.resolution_time,
                validation_score=validation_score,
                strategies_used=strategies_used,
                violations=violations,
                recommendations=recommendations
            )
            
            # Store result and update metrics
            self._store_quality_result(quality_result)
            
            # Trigger alerts for critical issues
            if violations:
                await self._trigger_alerts(selector.name, violations, gate_name)
            
            # Publish event
            await publish_event(
                "quality_evaluated",
                {
                    "selector_name": selector.name,
                    "context": gate_name,
                    "passed": passed,
                    "confidence_score": result.confidence_score,
                    "violations": len(violations),
                    "evaluated_at": quality_result.evaluated_at.isoformat()
                },
                source="quality_control"
            )
            
            self._logger.info(
                "quality_evaluation_completed",
                selector_name=selector.name,
                context=gate_name,
                passed=passed,
                confidence_score=result.confidence_score,
                violations=len(violations)
            )
            
            return quality_result
            
        except Exception as e:
            self._logger.error(
                "quality_evaluation_failed",
                selector_name=selector.name,
                context=gate_name,
                error=str(e)
            )
            raise QualityControlError(f"Quality evaluation failed: {str(e)}")
    
    async def evaluate_adaptive_quality(self, selector: SemanticSelector, context: DOMContext,
                                       performance_history: List[Dict[str, Any]]) -> AdaptiveQualityResult:
        """
        Evaluate quality with adaptive threshold adjustment.
        
        Args:
            selector: Selector to evaluate
            context: DOM context
            performance_history: Historical performance data
            
        Returns:
            Adaptive quality evaluation result
        """
        try:
            # Get base threshold
            base_threshold = self._threshold_manager.get_threshold("production")
            
            # Calculate adaptive threshold
            adapted_threshold = self._threshold_manager.get_adaptive_threshold(
                "adaptive", performance_history
            )
            
            # Evaluate with adapted threshold
            quality_result = await self.evaluate_quality(selector, context, "adaptive")
            
            # Update adaptive threshold
            self._threshold_manager.set_custom_threshold(
                "adaptive", adapted_threshold, 
                reason=f"Adaptive adjustment based on {len(performance_history)} historical evaluations"
            )
            
            # Determine adaptation reason
            adaptation_reason = self._determine_adaptation_reason(
                base_threshold, adapted_threshold, performance_history
            )
            
            # Calculate adaptation confidence
            adaptation_confidence = min(1.0, len(performance_history) / 50.0)  # More data = higher confidence
            
            # Create result
            adaptive_result = AdaptiveQualityResult(
                selector_name=selector.name,
                original_threshold=base_threshold,
                adapted_threshold=adapted_threshold,
                adaptation_reason=adaptation_reason,
                adaptation_confidence=adaptation_confidence,
                performance_metrics={
                    "avg_confidence": sum(p.get("confidence", 0) for p in performance_history) / len(performance_history),
                    "avg_resolution_time": sum(p.get("resolution_time", 0) for p in performance_history) / len(performance_history),
                    "success_rate": sum(1 for p in performance_history if p.get("success", False)) / len(performance_history)
                },
                passed=quality_result.passed
            )
            
            self._logger.info(
                "adaptive_quality_evaluation_completed",
                selector_name=selector.name,
                original_threshold=base_threshold,
                adapted_threshold=adapted_threshold,
                adaptation_reason=adaptation_reason,
                passed=quality_result.passed
            )
            
            return adaptive_result
            
        except Exception as e:
            self._logger.error(
                "adaptive_quality_evaluation_failed",
                selector_name=selector.name,
                error=str(e)
            )
            raise QualityControlError(f"Adaptive quality evaluation failed: {str(e)}")
    
    async def evaluate_batch_quality(self, selectors: List[SemanticSelector], context: DOMContext,
                                    gate_name: str = "production") -> List[QualityGateResult]:
        """
        Evaluate quality for multiple selectors in batch.
        
        Args:
            selectors: List of selectors to evaluate
            context: DOM context
            gate_name: Quality gate name
            
        Returns:
            List of quality gate results
        """
        try:
            # Evaluate all selectors concurrently
            tasks = [
                self.evaluate_quality(selector, context, gate_name)
                for selector in selectors
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self._logger.error(
                        "batch_quality_evaluation_failed",
                        selector_name=selectors[i].name,
                        error=str(result)
                    )
                else:
                    successful_results.append(result)
            
            self._logger.info(
                "batch_quality_evaluation_completed",
                total_selectors=len(selectors),
                successful=len(successful_results),
                failed=len(selectors) - len(successful_results)
            )
            
            return successful_results
            
        except Exception as e:
            self._logger.error(
                "batch_quality_evaluation_failed",
                total_selectors=len(selectors),
                error=str(e)
            )
            raise QualityControlError(f"Batch quality evaluation failed: {str(e)}")
    
    def set_quality_gate(self, gate_name: str, config: Dict[str, Any]) -> None:
        """
        Set quality gate configuration.
        
        Args:
            gate_name: Gate name
            config: Gate configuration
        """
        with self._lock:
            # Validate configuration
            required_keys = ["min_confidence", "max_resolution_time", "min_validation_score"]
            for key in required_keys:
                if key not in config:
                    raise ValidationError(f"Missing required key: {key}")
            
            self._quality_gates[gate_name] = config.copy()
            
            self._logger.info(
                "quality_gate_set",
                gate_name=gate_name,
                config_keys=list(config.keys())
            )
    
    def get_quality_metrics(self, selector_name: str) -> QualityMetrics:
        """
        Get quality metrics for a selector.
        
        Args:
            selector_name: Selector name
            
        Returns:
            Quality metrics
        """
        with self._lock:
            if selector_name not in self._quality_metrics:
                # Create default metrics
                metrics = QualityMetrics(
                    selector_name=selector_name,
                    total_evaluations=0,
                    pass_rate=0.0,
                    average_confidence=0.0,
                    average_resolution_time=0.0,
                    average_validation_score=0.0,
                    last_evaluation=None,
                    last_violation=None,
                    violation_count=0,
                    trend_direction="stable",
                    trend_confidence=0.0
                )
                self._quality_metrics[selector_name] = metrics
            
            return self._quality_metrics[selector_name]
    
    def generate_quality_report(self, gate_name: str = "production") -> Dict[str, Any]:
        """
        Generate comprehensive quality report.
        
        Args:
            gate_name: Quality gate name
            
        Returns:
            Quality report
        """
        with self._lock:
            # Filter results by gate
            gate_results = [
                r for r in self._evaluation_history
                if r.context == gate_name
            ]
            
            if not gate_results:
                return {
                    "gate_name": gate_name,
                    "summary": {
                        "total_selectors": 0,
                        "pass_rate": 0.0,
                        "average_confidence": 0.0,
                        "average_resolution_time": 0.0
                    },
                    "selectors": [],
                    "metrics": {},
                    "recommendations": ["No evaluations available for this gate"]
                }
            
            # Calculate summary statistics
            total_selectors = len(set(r.selector_name for r in gate_results))
            passed_evaluations = sum(1 for r in gate_results if r.passed)
            pass_rate = passed_evaluations / len(gate_results) if gate_results else 0.0
            avg_confidence = sum(r.confidence_score for r in gate_results) / len(gate_results) if gate_results else 0.0
            avg_resolution_time = sum(r.resolution_time for r in gate_results) / len(gate_results) if gate_results else 0.0
            
            # Group by selector
            selector_results = {}
            for result in gate_results:
                if result.selector_name not in selector_results:
                    selector_results[result.selector_name] = []
                selector_results[result.selector_name].append(result)
            
            # Generate recommendations
            recommendations = []
            if pass_rate < 0.8:
                recommendations.append(f"Overall pass rate ({pass_rate:.1%}) is below 80%")
            if avg_confidence < 0.7:
                recommendations.append(f"Average confidence ({avg_confidence:.2f}) is below 0.7")
            if avg_resolution_time > 1000:
                recommendations.append(f"Average resolution time ({avg_resolution_time:.0f}ms) is above 1000ms")
            
            return {
                "gate_name": gate_name,
                "summary": {
                    "total_selectors": total_selectors,
                    "total_evaluations": len(gate_results),
                    "pass_rate": pass_rate,
                    "average_confidence": avg_confidence,
                    "average_resolution_time": avg_resolution_time
                },
                "selectors": [
                    {
                        "name": selector_name,
                        "evaluations": len(results),
                        "pass_rate": sum(1 for r in results if r.passed) / len(results),
                        "avg_confidence": sum(r.confidence_score for r in results) / len(results),
                        "avg_resolution_time": sum(r.resolution_time for r in results) / len(results),
                        "last_evaluation": max(r.evaluated_at for r in results).isoformat()
                    }
                    for selector_name, results in selector_results.items()
                ],
                "metrics": {
                    name: {
                        "total_evaluations": metrics.total_evaluations,
                        "pass_rate": metrics.pass_rate,
                        "average_confidence": metrics.average_confidence,
                        "trend_direction": metrics.trend_direction
                    }
                    for name, metrics in self._quality_metrics.items()
                    if name in selector_results
                },
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
    
    def set_alert_handler(self, handler: Callable) -> None:
        """
        Set alert handler for quality issues.
        
        Args:
            handler: Alert handler function
        """
        self._alert_handlers.append(handler)
        
        self._logger.info(
            "alert_handler_set",
            handler_name=handler.__name__
        )
    
    def get_alerts(self, since: Optional[datetime] = None,
                   severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get quality alerts.
        
        Args:
            since: Optional start time filter
            severity: Optional severity filter
            
        Returns:
            List of alerts
        """
        with self._lock:
            alerts = []
            
            for alert in self._alerts:
                # Apply filters
                if since and alert.timestamp < since:
                    continue
                if severity and alert.severity != severity:
                    continue
                
                alerts.append({
                    "selector_name": alert.selector_name,
                    "issue_type": alert.issue_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "details": alert.details,
                    "timestamp": alert.timestamp.isoformat(),
                    "context": alert.context
                })
            
            return alerts
    
    def _calculate_validation_score(self, validation_results: List[ValidationResult]) -> float:
        """Calculate overall validation score."""
        if not validation_results:
            return 0.0
        
        total_weight = sum(r.weight for r in validation_results)
        if total_weight == 0:
            return 0.0
        
        weighted_score = sum(r.score * r.weight for r in validation_results)
        return weighted_score / total_weight
    
    def _store_quality_result(self, result: QualityGateResult) -> None:
        """Store quality result and update metrics."""
        with self._lock:
            self._evaluation_history.append(result)
            
            # Update selector metrics
            if result.selector_name not in self._quality_metrics:
                self._quality_metrics[result.selector_name] = QualityMetrics(
                    selector_name=result.selector_name,
                    total_evaluations=0,
                    pass_rate=0.0,
                    average_confidence=0.0,
                    average_resolution_time=0.0,
                    average_validation_score=0.0,
                    last_evaluation=None,
                    last_violation=None,
                    violation_count=0,
                    trend_direction="stable",
                    trend_confidence=0.0
                )
            
            metrics = self._quality_metrics[result.selector_name]
            metrics.total_evaluations += 1
            metrics.last_evaluation = result.evaluated_at
            
            # Update averages
            if metrics.total_evaluations == 1:
                metrics.average_confidence = result.confidence_score
                metrics.average_resolution_time = result.resolution_time
                metrics.average_validation_score = result.validation_score
            else:
                # Weighted average
                metrics.average_confidence = (
                    (metrics.average_confidence * (metrics.total_evaluations - 1) + result.confidence_score) /
                    metrics.total_evaluations
                )
                metrics.average_resolution_time = (
                    (metrics.average_resolution_time * (metrics.total_evaluations - 1) + result.resolution_time) /
                    metrics.total_evaluations
                )
                metrics.average_validation_score = (
                    (metrics.average_validation_score * (metrics.total_evaluations - 1) + result.validation_score) /
                    metrics.total_evaluations
                )
            
            # Update pass rate
            passed_count = sum(1 for r in self._evaluation_history if r.selector_name == result.selector_name and r.passed)
            metrics.pass_rate = passed_count / metrics.total_evaluations
            
            # Update violation tracking
            if not result.passed:
                metrics.violation_count += 1
                metrics.last_violation = result.evaluated_at
            
            # Calculate trend (simplified)
            if metrics.total_evaluations >= 5:
                recent_results = [
                    r for r in self._evaluation_history[-10:]
                    if r.selector_name == result.selector_name
                ]
                if len(recent_results) >= 3:
                    recent_confidence = sum(r.confidence_score for r in recent_results[-3:]) / 3
                    older_confidence = sum(r.confidence_score for r in recent_results[-6:-3]) / 3 if len(recent_results) >= 6 else recent_confidence
                    
                    if recent_confidence > older_confidence + 0.05:
                        metrics.trend_direction = "improving"
                    elif recent_confidence < older_confidence - 0.05:
                        metrics.trend_direction = "declining"
                    else:
                        metrics.trend_direction = "stable"
                    
                    metrics.trend_confidence = min(1.0, len(recent_results) / 10.0)
        
        # Save metrics periodically
        if len(self._evaluation_history) % 10 == 0:
            self._save_metrics()
    
    async def _trigger_alerts(self, selector_name: str, violations: List[Dict[str, Any]], context: str) -> None:
        """Trigger alerts for quality violations."""
        for violation in violations:
            alert = QualityAlert(
                selector_name=selector_name,
                issue_type=violation["type"],
                severity=violation["severity"],
                message=f"Quality violation: {violation['type']} - {violation.get('actual', 'N/A')} vs {violation.get('required', 'N/A')}",
                details=violation,
                timestamp=datetime.utcnow(),
                context=context
            )
            
            self._alerts.append(alert)
            
            # Call alert handlers
            for handler in self._alert_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert)
                    else:
                        handler(alert)
                except Exception as e:
                    self._logger.error(
                        "alert_handler_failed",
                        handler_name=handler.__name__,
                        error=str(e)
                    )
    
    def _determine_adaptation_reason(self, base_threshold: float, adapted_threshold: float,
                                   performance_history: List[Dict[str, Any]]) -> str:
        """Determine reason for threshold adaptation."""
        if adapted_threshold < base_threshold:
            if len(performance_history) >= 10:
                success_rate = sum(1 for p in performance_history if p.get("success", False)) / len(performance_history)
                avg_confidence = sum(p.get("confidence", 0) for p in performance_history) / len(performance_history)
                
                if success_rate > 0.9 and avg_confidence > 0.85:
                    return "High performance - relaxing threshold"
                elif avg_confidence > 0.8:
                    return "Good confidence - moderate relaxation"
                else:
                    return "Performance-based adjustment"
            else:
                return "Insufficient data - conservative adjustment"
        else:
            return "Performance concerns - tightening threshold"
    
    def _load_metrics(self) -> None:
        """Load quality metrics from storage."""
        try:
            storage_path = Path("data/quality_metrics.json")
            if storage_path.exists():
                with open(storage_path, 'r') as f:
                    data = json.load(f)
                
                # Convert dictionaries back to QualityMetrics objects
                for selector_name, metrics_data in data.get("metrics", {}).items():
                    self._quality_metrics[selector_name] = QualityMetrics(
                        selector_name=selector_name,
                        total_evaluations=metrics_data["total_evaluations"],
                        pass_rate=metrics_data["pass_rate"],
                        average_confidence=metrics_data["average_confidence"],
                        average_resolution_time=metrics_data["average_resolution_time"],
                        average_validation_score=metrics_data["average_validation_score"],
                        last_evaluation=datetime.fromisoformat(metrics_data["last_evaluation"]) if metrics_data["last_evaluation"] else None,
                        last_violation=datetime.fromisoformat(metrics_data["last_violation"]) if metrics_data["last_violation"] else None,
                        violation_count=metrics_data["violation_count"],
                        trend_direction=metrics_data["trend_direction"],
                        trend_confidence=metrics_data["trend_confidence"]
                    )
                
                self._logger.info(
                    "quality_metrics_loaded",
                    selectors_loaded=len(self._quality_metrics)
                )
        except Exception as e:
            self._logger.warning(
                "quality_metrics_load_failed",
                error=str(e)
            )
    
    def _save_metrics(self) -> None:
        """Save quality metrics to storage."""
        try:
            # Ensure directory exists
            storage_path = Path("data")
            storage_path.mkdir(exist_ok=True)
            
            # Convert to serializable format
            metrics_data = {
                "metrics": {
                    selector_name: {
                        "total_evaluations": metrics.total_evaluations,
                        "pass_rate": metrics.pass_rate,
                        "average_confidence": metrics.average_confidence,
                        "average_resolution_time": metrics.average_resolution_time,
                        "average_validation_score": metrics.average_validation_score,
                        "last_evaluation": metrics.last_evaluation.isoformat() if metrics.last_evaluation else None,
                        "last_violation": metrics.last_violation.isoformat() if metrics.last_violation else None,
                        "violation_count": metrics.violation_count,
                        "trend_direction": metrics.trend_direction,
                        "trend_confidence": metrics.trend_confidence
                    }
                    for selector_name, metrics in self._quality_metrics.items()
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Save to file
            metrics_file = storage_path / "quality_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            self._logger.debug("quality_metrics_saved")
        except Exception as e:
            self._logger.error(
                "quality_metrics_save_failed",
                error=str(e)
            )


# Global quality control manager instance
quality_control_manager = QualityControlManager()


def get_quality_control_manager() -> QualityControlManager:
    """Get global quality control manager instance."""
    return quality_control_manager
