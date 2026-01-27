"""
Confidence threshold management for Selector Engine.

Provides dynamic threshold management with context-aware adjustments,
persistence, and adaptive learning capabilities as specified in the API contracts.
"""

import asyncio
import json
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from src.observability.logger import get_logger
from src.observability.events import publish_event
from src.utils.exceptions import ValidationError, ConfigurationError
from src.config.settings import get_config


@dataclass
class ThresholdChange:
    """Represents a threshold change event."""
    context: str
    sub_context: Optional[str]
    old_threshold: Optional[float]
    new_threshold: float
    changed_at: datetime
    changed_by: str
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThresholdViolation:
    """Represents a confidence threshold violation."""
    selector_name: str
    context: str
    actual_confidence: float
    required_threshold: float
    violation_amount: float
    severity: str  # "warning", "error", "critical"
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdaptiveThresholdResult:
    """Result of adaptive threshold calculation."""
    context: str
    original_threshold: float
    adapted_threshold: float
    adaptation_reason: str
    confidence_delta: float
    performance_metrics: Dict[str, Any]
    adaptation_confidence: float


class ConfidenceThresholdManager:
    """Manages confidence thresholds with context-aware adjustments."""
    
    def __init__(self):
        self._logger = get_logger("confidence_thresholds")
        self._config = get_config()
        
        # Threshold storage
        self._thresholds: Dict[str, Dict[str, float]] = {}
        self._context_thresholds: Dict[str, Dict[str, Dict[str, float]]] = {}
        
        # Change tracking
        self._change_history: List[ThresholdChange] = []
        self._violations: List[ThresholdViolation] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Default thresholds
        self._default_thresholds = {
            "production": 0.85,
            "staging": 0.75,
            "development": 0.65,
            "testing": 0.5,
            "research": 0.4
        }
        
        # Load existing thresholds
        self._load_thresholds()
        
        self._logger.info("ConfidenceThresholdManager initialized")
    
    def get_threshold(self, context: str, sub_context: Optional[str] = None) -> float:
        """
        Get confidence threshold for context.
        
        Args:
            context: Main context (production, development, etc.)
            sub_context: Optional sub-context for more specific thresholds
            
        Returns:
            Confidence threshold value (0.0 to 1.0)
        """
        with self._lock:
            # Check sub-context specific threshold first
            if sub_context and context in self._context_thresholds:
                if sub_context in self._context_thresholds[context]:
                    return self._context_thresholds[context][sub_context]
            
            # Check context-specific threshold
            if context in self._thresholds:
                return self._thresholds[context]
            
            # Fall back to default threshold
            if context in self._default_thresholds:
                return self._default_thresholds[context]
            
            # Default to development threshold
            return self._default_thresholds["development"]
    
    def set_custom_threshold(self, context: str, threshold: float, 
                             sub_context: Optional[str] = None, reason: str = "Custom threshold") -> bool:
        """
        Set custom confidence threshold.
        
        Args:
            context: Context name
            threshold: Threshold value (0.0 to 1.0)
            sub_context: Optional sub-context
            reason: Reason for change
            
        Returns:
            True if successful, False otherwise
        """
        if not self.validate_threshold(threshold):
            self._logger.warning(
                "invalid_threshold",
                context=context,
                sub_context=sub_context,
                threshold=threshold,
                reason="Invalid threshold value"
            )
            return False
        
        with self._lock:
            old_threshold = None
            
            # Store threshold
            if sub_context:
                if context not in self._context_thresholds:
                    self._context_thresholds[context] = {}
                old_threshold = self._context_thresholds[context].get(sub_context)
                self._context_thresholds[context][sub_context] = threshold
            else:
                old_threshold = self._thresholds.get(context)
                self._thresholds[context] = threshold
            
            # Track change
            change = ThresholdChange(
                context=context,
                sub_context=sub_context,
                old_threshold=old_threshold,
                new_threshold=threshold,
                changed_at=datetime.utcnow(),
                changed_by="user",
                reason=reason
            )
            self._change_history.append(change)
            
            # Persist changes
            self._save_thresholds()
            
            # Publish event
            asyncio.create_task(
                publish_event(
                    "threshold_changed",
                    {
                        "context": context,
                        "sub_context": sub_context,
                        "old_threshold": old_threshold,
                        "new_threshold": threshold,
                        "reason": reason,
                        "changed_at": change.changed_at.isoformat()
                    },
                    source="confidence_thresholds"
                )
            )
            
            self._logger.info(
                "threshold_set",
                context=context,
                sub_context=sub_context,
                old_threshold=old_threshold,
                new_threshold=threshold,
                reason=reason
            )
            
            return True
    
    def set_context_threshold(self, context: str, sub_context: str, threshold: float,
                             reason: str = "Context-specific threshold") -> bool:
        """
        Set context-specific threshold.
        
        Args:
            context: Main context
            sub_context: Sub-context
            threshold: Threshold value
            reason: Reason for change
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_custom_threshold(context, threshold, sub_context, reason)
    
    def validate_threshold(self, threshold: float) -> bool:
        """
        Validate threshold value.
        
        Args:
            threshold: Threshold value to validate
            
        Returns:
            True if valid, False otherwise
        """
        return 0.0 <= threshold <= 1.0
    
    def get_threshold_history(self, context: str, sub_context: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get threshold change history.
        
        Args:
            context: Context name
            sub_context: Optional sub-context
            limit: Maximum number of changes to return
            
        Returns:
            List of threshold changes
        """
        with self._lock:
            history = []
            
            for change in self._change_history:
                if change.context == context:
                    if sub_context is None or change.sub_context == sub_context:
                        history.append({
                            "context": change.context,
                            "sub_context": change.sub_context,
                            "old_threshold": change.old_threshold,
                            "new_threshold": change.new_threshold,
                            "changed_at": change.changed_at.isoformat(),
                            "changed_by": change.changed_by,
                            "reason": change.reason
                        })
            
            # Return most recent changes
            return history[-limit:] if len(history) > limit else history
    
    def get_all_thresholds(self) -> Dict[str, Any]:
        """
        Get all configured thresholds.
        
        Returns:
            Dictionary of all thresholds
        """
        with self._lock:
            return {
                "default_thresholds": self._default_thresholds.copy(),
                "custom_thresholds": self._thresholds.copy(),
                "context_thresholds": {
                    context: sub_contexts.copy()
                    for context, sub_contexts in self._context_thresholds.items()
                }
            }
    
    def filter_by_threshold(self, results: List[Any], context: str,
                           sub_context: Optional[str] = None) -> List[Any]:
        """
        Filter results based on confidence threshold.
        
        Args:
            results: List of selector results
            context: Context for threshold
            sub_context: Optional sub-context
            
        Returns:
            Filtered list of results
        """
        threshold = self.get_threshold(context, sub_context)
        
        filtered_results = []
        violations = []
        
        for result in results:
            if hasattr(result, 'confidence_score'):
                if result.confidence_score >= threshold:
                    filtered_results.append(result)
                else:
                    # Track violation
                    violation = ThresholdViolation(
                        selector_name=getattr(result, 'selector_name', 'unknown'),
                        context=context,
                        actual_confidence=result.confidence_score,
                        required_threshold=threshold,
                        violation_amount=threshold - result.confidence_score,
                        severity=self._calculate_violation_severity(
                            result.confidence_score, threshold
                        ),
                        timestamp=datetime.utcnow(),
                        metadata={"result_type": type(result).__name__}
                    )
                    violations.append(violation)
        
        # Store violations
        if violations:
            with self._lock:
                self._violations.extend(violations)
        
        return filtered_results
    
    def check_threshold_violation(self, result: Any, context: str,
                               sub_context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if result violates confidence threshold.
        
        Args:
            result: Selector result to check
            context: Context for threshold
            sub_context: Optional sub-context
            
        Returns:
            Violation details or None if no violation
        """
        if not hasattr(result, 'confidence_score'):
            return None
        
        threshold = self.get_threshold(context, sub_context)
        
        if result.confidence_score < threshold:
            violation = ThresholdViolation(
                selector_name=getattr(result, 'selector_name', 'unknown'),
                context=context,
                actual_confidence=result.confidence_score,
                required_threshold=threshold,
                violation_amount=threshold - result.confidence_score,
                severity=self._calculate_violation_severity(
                    result.confidence_score, threshold
                ),
                timestamp=datetime.utcnow(),
                metadata={"result_type": type(result).__name__}
            )
            
            # Store violation
            with self._lock:
                self._violations.append(violation)
            
            return {
                "selector_name": violation.selector_name,
                "context": violation.context,
                "actual_confidence": violation.actual_confidence,
                "required_threshold": violation.required_threshold,
                "violation_amount": violation.violation_amount,
                "severity": violation.severity,
                "timestamp": violation.timestamp.isoformat()
            }
        
        return None
    
    def get_adaptive_threshold(self, context: str, performance_data: Dict[str, Any]) -> float:
        """
        Get adaptive threshold based on performance data.
        
        Args:
            context: Context name
            performance_data: Performance metrics
            
        Returns:
            Adapted threshold value
        """
        base_threshold = self.get_threshold(context)
        
        # Calculate adaptation factors
        success_rate = performance_data.get("success_rate", 0.5)
        avg_confidence = performance_data.get("avg_confidence", 0.5)
        total_attempts = performance_data.get("total_attempts", 0)
        
        # Only adapt with sufficient data
        if total_attempts < 10:
            return base_threshold
        
        # Calculate adaptation
        adaptation_factor = 0.0
        
        # High success rate -> lower threshold (more permissive)
        if success_rate > 0.9:
            adaptation_factor -= 0.1 * (success_rate - 0.9)
        
        # High average confidence -> lower threshold
        if avg_confidence > 0.85:
            adaptation_factor -= 0.05 * (avg_confidence - 0.85)
        
        # Low success rate -> higher threshold (more strict)
        if success_rate < 0.7:
            adaptation_factor += 0.1 * (0.7 - success_rate)
        
        # Apply adaptation with bounds
        adapted_threshold = base_threshold + adaptation_factor
        adapted_threshold = max(0.4, min(0.95, adapted_threshold))
        
        self._logger.debug(
            "adaptive_threshold_calculated",
            context=context,
            base_threshold=base_threshold,
            adapted_threshold=adapted_threshold,
            adaptation_factor=adaptation_factor,
            success_rate=success_rate,
            avg_confidence=avg_confidence
        )
        
        return adapted_threshold
    
    def get_violations(self, context: Optional[str] = None,
                       since: Optional[datetime] = None,
                       severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get threshold violations.
        
        Args:
            context: Optional context filter
            since: Optional start time filter
            severity: Optional severity filter
            
        Returns:
            List of violations
        """
        with self._lock:
            violations = []
            
            for violation in self._violations:
                # Apply filters
                if context and violation.context != context:
                    continue
                if since and violation.timestamp < since:
                    continue
                if severity and violation.severity != severity:
                    continue
                
                violations.append({
                    "selector_name": violation.selector_name,
                    "context": violation.context,
                    "actual_confidence": violation.actual_confidence,
                    "required_threshold": violation.required_threshold,
                    "violation_amount": violation.violation_amount,
                    "severity": violation.severity,
                    "timestamp": violation.timestamp.isoformat(),
                    "metadata": violation.metadata
                })
            
            return violations
    
    def get_violation_statistics(self, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Get violation statistics.
        
        Args:
            context: Optional context filter
            
        Returns:
            Statistics dictionary
        """
        violations = self.get_violations(context)
        
        if not violations:
            return {
                "total_violations": 0,
                "by_severity": {},
                "by_context": {},
                "recent_violations": []
            }
        
        # Calculate statistics
        by_severity = {}
        by_context = {}
        
        for violation in violations:
            severity = violation["severity"]
            ctx = violation["context"]
            
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_context[ctx] = by_context.get(ctx, 0) + 1
        
        # Get recent violations (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_violations = [
            v for v in violations
            if datetime.fromisoformat(v["timestamp"]) > recent_cutoff
        ]
        
        return {
            "total_violations": len(violations),
            "by_severity": by_severity,
            "by_context": by_context,
            "recent_violations": len(recent_violations),
            "violation_rate": len(violations) / max(1, len(self._change_history))
        }
    
    def _calculate_violation_severity(self, actual_confidence: float, 
                                    required_threshold: float) -> str:
        """Calculate violation severity based on confidence difference."""
        violation_amount = required_threshold - actual_confidence
        
        if violation_amount >= 0.3:
            return "critical"
        elif violation_amount >= 0.2:
            return "error"
        elif violation_amount >= 0.1:
            return "warning"
        else:
            return "info"
    
    def _load_thresholds(self) -> None:
        """Load thresholds from storage."""
        try:
            # Try to load from file
            storage_path = Path("data/thresholds.json")
            if storage_path.exists():
                with open(storage_path, 'r') as f:
                    data = json.load(f)
                
                self._thresholds = data.get("custom_thresholds", {})
                self._context_thresholds = data.get("context_thresholds", {})
                
                self._logger.info(
                    "thresholds_loaded",
                    custom_thresholds=len(self._thresholds),
                    context_thresholds=len(self._context_thresholds)
                )
        except Exception as e:
            self._logger.warning(
                "thresholds_load_failed",
                error=str(e)
            )
    
    def _save_thresholds(self) -> None:
        """Save thresholds to storage."""
        try:
            # Ensure directory exists
            storage_path = Path("data")
            storage_path.mkdir(exist_ok=True)
            
            # Save to file
            thresholds_file = storage_path / "thresholds.json"
            data = {
                "custom_thresholds": self._thresholds,
                "context_thresholds": self._context_thresholds,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            with open(thresholds_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self._logger.debug("thresholds_saved")
        except Exception as e:
            self._logger.error(
                "thresholds_save_failed",
                error=str(e)
            )


# Global threshold manager instance
threshold_manager = ConfidenceThresholdManager()


def get_threshold_manager() -> ConfidenceThresholdManager:
    """Get global threshold manager instance."""
    return threshold_manager
