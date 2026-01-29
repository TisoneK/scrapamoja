"""
Alert Severity Classifier

Intelligent alert severity classification with rule-based
and machine learning approaches for accurate severity assessment.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import math

from ..interfaces import Alert, AlertSeverity
from ..models import TelemetryEvent, PerformanceMetrics, QualityMetrics
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class ClassificationMethod(Enum):
    """Classification method types."""
    RULE_BASED = "rule_based"
    STATISTICAL = "statistical"
    ML_BASED = "ml_based"
    HYBRID = "hybrid"


class SeverityFactor(Enum):
    """Factors that influence severity classification."""
    METRIC_DEVIATION = "metric_deviation"
    TREND_IMPACT = "trend_impact"
    FREQUENCY_IMPACT = "frequency_impact"
    BUSINESS_IMPACT = "business_impact"
    SYSTEM_IMPACT = "system_impact"
    USER_IMPACT = "user_impact"


@dataclass
class SeverityRule:
    """Rule for severity classification."""
    rule_id: str
    name: str
    description: str
    metric_name: str
    conditions: List[Dict[str, Any]]
    severity: AlertSeverity
    weight: float = 1.0
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SeverityClassification:
    """Result of severity classification."""
    alert_id: str
    metric_name: str
    current_value: float
    baseline_value: float
    deviation_ratio: float
    classified_severity: AlertSeverity
    confidence: float
    classification_method: ClassificationMethod
    factors: Dict[SeverityFactor, float]
    applied_rules: List[str]
    reasoning: str
    classification_time: datetime
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeverityStatistics:
    """Statistics for severity classification."""
    total_classifications: int = 0
    classifications_by_severity: Dict[str, int] = field(default_factory=dict)
    classifications_by_method: Dict[str, int] = field(default_factory=dict)
    average_confidence: float = 0.0
    most_common_severity: str = ""
    most_common_method: str = ""
    rule_effectiveness: Dict[str, float] = field(default_factory=dict)
    last_classification: Optional[datetime] = None


class SeverityClassifier:
    """
    Intelligent alert severity classifier with multiple approaches.
    
    Provides comprehensive severity classification using rule-based,
    statistical, and machine learning approaches.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize severity classifier.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("severity_classifier")
        
        # Classifier configuration
        self.enabled = config.get("severity_classification_enabled", True)
        self.default_method = ClassificationMethod(config.get("default_classification_method", "hybrid"))
        self.confidence_threshold = config.get("classification_confidence_threshold", 0.7)
        
        # Data storage
        self._severity_rules: Dict[str, SeverityRule] = {}
        self._classification_history: List[SeverityClassification] = []
        self._metric_baselines: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._classification_lock = asyncio.Lock()
        
        # Statistics
        self._statistics = SeverityStatistics()
        
        # Initialize default rules
        self._initialize_default_rules()
    
    async def classify_alert_severity(
        self,
        alert: Alert,
        event: Optional[TelemetryEvent] = None,
        custom_rules: Optional[List[SeverityRule]] = None
    ) -> SeverityClassification:
        """
        Classify the severity of an alert.
        
        Args:
            alert: Alert to classify
            event: Optional telemetry event for context
            custom_rules: Optional custom classification rules
            
        Returns:
            Severity classification result
            
        Raises:
            TelemetryAlertingError: If classification fails
        """
        if not self.enabled:
            # Return default classification
            return SeverityClassification(
                alert_id=alert.alert_id,
                metric_name=alert.metric_name or "unknown",
                current_value=getattr(alert, 'current_value', 0.0),
                baseline_value=0.0,
                deviation_ratio=1.0,
                classified_severity=alert.severity,
                confidence=0.5,
                classification_method=ClassificationMethod.RULE_BASED,
                factors={},
                applied_rules=[],
                reasoning="Classification disabled",
                classification_time=datetime.utcnow()
            )
        
        try:
            async with self._classification_lock:
                # Extract metric information
                metric_name = alert.metric_name or "unknown"
                current_value = getattr(alert, 'current_value', 0.0)
                
                # Update baseline data
                if event:
                    await self._update_baseline_data(metric_name, event)
                
                # Get baseline value
                baseline_value = await self._get_baseline_value(metric_name)
                
                # Calculate deviation ratio
                deviation_ratio = self._calculate_deviation_ratio(current_value, baseline_value)
                
                # Get rules to apply
                rules_to_apply = []
                
                # Add default rules
                for rule in self._severity_rules.values():
                    if rule.enabled and rule.metric_name == metric_name:
                        rules_to_apply.append(rule)
                
                # Add custom rules
                if custom_rules:
                    rules_to_apply.extend(custom_rules)
                
                # Classify using default method
                classification = await self._classify_with_method(
                    self.default_method,
                    alert,
                    metric_name,
                    current_value,
                    baseline_value,
                    deviation_ratio,
                    rules_to_apply,
                    event
                )
                
                # Store classification
                self._classification_history.append(classification)
                self._update_statistics(classification)
                
                # Limit history size
                if len(self._classification_history) > 10000:
                    self._classification_history = self._classification_history[-10000:]
                
                self.logger.debug(
                    "Alert severity classified",
                    alert_id=alert.alert_id,
                    metric_name=metric_name,
                    classified_severity=classification.classified_severity.value,
                    confidence=classification.confidence
                )
                
                return classification
                
        except Exception as e:
            self.logger.error(
                "Failed to classify alert severity",
                alert_id=alert.alert_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to classify alert severity: {e}",
                error_code="TEL-810"
            )
    
    async def classify_with_method(
        self,
        method: ClassificationMethod,
        alert: Alert,
        event: Optional[TelemetryEvent] = None
    ) -> SeverityClassification:
        """
        Classify alert severity using specific method.
        
        Args:
            method: Classification method to use
            alert: Alert to classify
            event: Optional telemetry event for context
            
        Returns:
            Severity classification result
        """
        try:
            async with self._classification_lock:
                # Extract metric information
                metric_name = alert.metric_name or "unknown"
                current_value = getattr(alert, 'current_value', 0.0)
                baseline_value = await self._get_baseline_value(metric_name)
                deviation_ratio = self._calculate_deviation_ratio(current_value, baseline_value)
                
                # Get applicable rules
                rules_to_apply = [
                    rule for rule in self._severity_rules.values()
                    if rule.enabled and rule.metric_name == metric_name
                ]
                
                return await self._classify_with_method(
                    method,
                    alert,
                    metric_name,
                    current_value,
                    baseline_value,
                    deviation_ratio,
                    rules_to_apply,
                    event
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to classify with method",
                method=method.value,
                alert_id=alert.alert_id,
                error=str(e)
            )
            raise
    
    async def add_severity_rule(self, rule: SeverityRule) -> bool:
        """
        Add a severity classification rule.
        
        Args:
            rule: Severity rule to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._classification_lock:
                self._severity_rules[rule.rule_id] = rule
            
            self.logger.info(
                "Severity rule added",
                rule_id=rule.rule_id,
                metric_name=rule.metric_name,
                severity=rule.severity.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add severity rule",
                rule_id=rule.rule_id,
                error=str(e)
            )
            return False
    
    async def remove_severity_rule(self, rule_id: str) -> bool:
        """
        Remove a severity classification rule.
        
        Args:
            rule_id: Rule ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._classification_lock:
                if rule_id in self._severity_rules:
                    del self._severity_rules[rule_id]
                    
                    self.logger.info(
                        "Severity rule removed",
                        rule_id=rule_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove severity rule",
                rule_id=rule_id,
                error=str(e)
            )
            return False
    
    async def get_classification_statistics(self) -> Dict[str, Any]:
        """
        Get severity classification statistics.
        
        Returns:
            Classification statistics
        """
        try:
            async with self._classification_lock:
                return {
                    "total_classifications": self._statistics.total_classifications,
                    "classifications_by_severity": dict(self._statistics.classifications_by_severity),
                    "classifications_by_method": dict(self._statistics.classifications_by_method),
                    "average_confidence": self._statistics.average_confidence,
                    "most_common_severity": self._statistics.most_common_severity,
                    "most_common_method": self._statistics.most_common_method,
                    "rule_effectiveness": dict(self._statistics.rule_effectiveness),
                    "last_classification": self._statistics.last_classification,
                    "active_rules": len([r for r in self._severity_rules.values() if r.enabled]),
                    "total_rules": len(self._severity_rules),
                    "metrics_tracked": len(self._metric_baselines)
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get classification statistics",
                error=str(e)
            )
            return {}
    
    async def get_classification_history(
        self,
        severity: Optional[AlertSeverity] = None,
        method: Optional[ClassificationMethod] = None,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[SeverityClassification]:
        """
        Get classification history with filtering.
        
        Args:
            severity: Optional severity filter
            method: Optional method filter
            limit: Optional limit on number of results
            time_window: Optional time window for results
            
        Returns:
            List of classification results
        """
        try:
            async with self._classification_lock:
                results = self._classification_history.copy()
                
                # Apply filters
                if severity:
                    results = [r for r in results if r.classified_severity == severity]
                
                if method:
                    results = [r for r in results if r.classification_method == method]
                
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    results = [r for r in results if r.classification_time >= cutoff_time]
                
                # Sort by timestamp (newest first)
                results.sort(key=lambda x: x.classification_time, reverse=True)
                
                # Apply limit
                if limit:
                    results = results[:limit]
                
                return results
                
        except Exception as e:
            self.logger.error(
                "Failed to get classification history",
                error=str(e)
            )
            return []
    
    async def get_all_rules(self) -> List[SeverityRule]:
        """
        Get all severity classification rules.
        
        Returns:
            List of all rules
        """
        try:
            async with self._classification_lock:
                return list(self._severity_rules.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all rules",
                error=str(e)
            )
            return []
    
    # Private methods
    
    def _initialize_default_rules(self) -> None:
        """Initialize default severity classification rules."""
        default_rules = [
            SeverityRule(
                rule_id="resolution_time_critical",
                name="Critical Resolution Time",
                description="Classify as critical when resolution time exceeds 10 seconds",
                metric_name="resolution_time_ms",
                conditions=[
                    {"operator": ">", "value": 10000}
                ],
                severity=AlertSeverity.CRITICAL,
                weight=2.0
            ),
            SeverityRule(
                rule_id="resolution_time_error",
                name="Error Resolution Time",
                description="Classify as error when resolution time exceeds 5 seconds",
                metric_name="resolution_time_ms",
                conditions=[
                    {"operator": ">", "value": 5000}
                ],
                severity=AlertSeverity.ERROR,
                weight=1.5
            ),
            SeverityRule(
                rule_id="confidence_score_critical",
                name="Critical Confidence Score",
                description="Classify as critical when confidence score below 0.2",
                metric_name="confidence_score",
                conditions=[
                    {"operator": "<", "value": 0.2}
                ],
                severity=AlertSeverity.CRITICAL,
                weight=2.0
            ),
            SeverityRule(
                rule_id="confidence_score_error",
                name="Error Confidence Score",
                description="Classify as error when confidence score below 0.4",
                metric_name="confidence_score",
                conditions=[
                    {"operator": "<", "value": 0.4}
                ],
                severity=AlertSeverity.ERROR,
                weight=1.5
            ),
            SeverityRule(
                rule_id="error_rate_critical",
                name="Critical Error Rate",
                description="Classify as critical when error rate exceeds 25%",
                metric_name="error_rate",
                conditions=[
                    {"operator": ">", "value": 0.25}
                ],
                severity=AlertSeverity.CRITICAL,
                weight=2.0
            ),
            SeverityRule(
                rule_id="memory_usage_critical",
                name="Critical Memory Usage",
                description="Classify as critical when memory usage exceeds 1GB",
                metric_name="memory_usage_mb",
                conditions=[
                    {"operator": ">", "value": 1024}
                ],
                severity=AlertSeverity.CRITICAL,
                weight=1.8
            ),
            SeverityRule(
                rule_id="cpu_usage_critical",
                name="Critical CPU Usage",
                description="Classify as critical when CPU usage exceeds 95%",
                metric_name="cpu_usage_percent",
                conditions=[
                    {"operator": ">", "value": 95}
                ],
                severity=AlertSeverity.CRITICAL,
                weight=1.8
            )
        ]
        
        for rule in default_rules:
            self._severity_rules[rule.rule_id] = rule
    
    async def _classify_with_method(
        self,
        method: ClassificationMethod,
        alert: Alert,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        deviation_ratio: float,
        rules: List[SeverityRule],
        event: Optional[TelemetryEvent]
    ) -> SeverityClassification:
        """Classify using specific method."""
        if method == ClassificationMethod.RULE_BASED:
            return await self._classify_rule_based(
                alert, metric_name, current_value, baseline_value, deviation_ratio, rules, event
            )
        elif method == ClassificationMethod.STATISTICAL:
            return await self._classify_statistical(
                alert, metric_name, current_value, baseline_value, deviation_ratio, event
            )
        elif method == ClassificationMethod.ML_BASED:
            return await self._classify_ml_based(
                alert, metric_name, current_value, baseline_value, deviation_ratio, event
            )
        elif method == ClassificationMethod.HYBRID:
            return await self._classify_hybrid(
                alert, metric_name, current_value, baseline_value, deviation_ratio, rules, event
            )
        else:
            raise TelemetryAlertingError(
                f"Unsupported classification method: {method.value}",
                error_code="TEL-811"
            )
    
    async def _classify_rule_based(
        self,
        alert: Alert,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        deviation_ratio: float,
        rules: List[SeverityRule],
        event: Optional[TelemetryEvent]
    ) -> SeverityClassification:
        """Classify using rule-based approach."""
        applied_rules = []
        severity_scores = defaultdict(float)
        
        # Evaluate rules
        for rule in rules:
            if self._evaluate_rule_conditions(rule.conditions, current_value):
                applied_rules.append(rule.rule_id)
                severity_scores[rule.severity] += rule.weight
        
        # Determine severity
        if severity_scores:
            # Find severity with highest score
            max_severity = max(severity_scores.items(), key=lambda x: x[1])
            classified_severity = max_severity[0]
            confidence = min(1.0, max_severity[1] / 2.0)  # Normalize to 0-1
        else:
            # Default classification based on deviation
            classified_severity, confidence = self._default_severity_classification(deviation_ratio)
        
        # Calculate factors
        factors = {
            SeverityFactor.METRIC_DEVIATION: min(1.0, deviation_ratio / 3.0)
        }
        
        reasoning = f"Rule-based classification: {len(applied_rules)} rules applied"
        if applied_rules:
            reasoning += f" ({', '.join(applied_rules)})"
        
        return SeverityClassification(
            alert_id=alert.alert_id,
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            deviation_ratio=deviation_ratio,
            classified_severity=classified_severity,
            confidence=confidence,
            classification_method=ClassificationMethod.RULE_BASED,
            factors=factors,
            applied_rules=applied_rules,
            reasoning=reasoning,
            classification_time=datetime.utcnow(),
            context={
                "selector_name": getattr(event, 'selector_name', None) if event else None,
                "correlation_id": getattr(event, 'correlation_id', None) if event else None
            }
        )
    
    async def _classify_statistical(
        self,
        alert: Alert,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        deviation_ratio: float,
        event: Optional[TelemetryEvent]
    ) -> SeverityClassification:
        """Classify using statistical approach."""
        factors = {}
        
        # Get historical data for statistical analysis
        if metric_name in self._metric_baselines:
            historical_values = [item["value"] for item in self._metric_baselines[metric_name]]
            
            if len(historical_values) >= 10:
                # Calculate statistical measures
                mean_value = statistics.mean(historical_values)
                std_dev = statistics.stdev(historical_values)
                
                # Z-score based classification
                if std_dev > 0:
                    z_score = abs(current_value - mean_value) / std_dev
                    
                    if z_score > 4:
                        classified_severity = AlertSeverity.CRITICAL
                        confidence = min(1.0, z_score / 6.0)
                    elif z_score > 3:
                        classified_severity = AlertSeverity.ERROR
                        confidence = min(1.0, z_score / 5.0)
                    elif z_score > 2:
                        classified_severity = AlertSeverity.WARNING
                        confidence = min(1.0, z_score / 4.0)
                    else:
                        classified_severity = AlertSeverity.INFO
                        confidence = 0.5
                    
                    factors[SeverityFactor.METRIC_DEVIATION] = min(1.0, z_score / 4.0)
                else:
                    classified_severity, confidence = self._default_severity_classification(deviation_ratio)
                    factors[SeverityFactor.METRIC_DEVIATION] = min(1.0, deviation_ratio / 3.0)
            else:
                classified_severity, confidence = self._default_severity_classification(deviation_ratio)
                factors[SeverityFactor.METRIC_DEVIATION] = min(1.0, deviation_ratio / 3.0)
        else:
            classified_severity, confidence = self._default_severity_classification(deviation_ratio)
            factors[SeverityFactor.METRIC_DEVIATION] = min(1.0, deviation_ratio / 3.0)
        
        reasoning = f"Statistical classification based on deviation ratio {deviation_ratio:.2f}"
        
        return SeverityClassification(
            alert_id=alert.alert_id,
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            deviation_ratio=deviation_ratio,
            classified_severity=classified_severity,
            confidence=confidence,
            classification_method=ClassificationMethod.STATISTICAL,
            factors=factors,
            applied_rules=[],
            reasoning=reasoning,
            classification_time=datetime.utcnow(),
            context={
                "selector_name": getattr(event, 'selector_name', None) if event else None,
                "correlation_id": getattr(event, 'correlation_id', None) if event else None
            }
        )
    
    async def _classify_ml_based(
        self,
        alert: Alert,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        deviation_ratio: float,
        event: Optional[TelemetryEvent]
    ) -> SeverityClassification:
        """Classify using machine learning approach (simplified)."""
        # In a real implementation, this would use a trained ML model
        # For now, we'll use a simplified heuristic approach
        
        factors = {}
        
        # Feature engineering
        features = {
            "deviation_ratio": deviation_ratio,
            "absolute_deviation": abs(current_value - baseline_value),
            "relative_change": (current_value - baseline_value) / baseline_value if baseline_value != 0 else 0
        }
        
        # Get historical context
        if metric_name in self._metric_baselines:
            historical_values = [item["value"] for item in self._metric_baselines[metric_name]]
            
            if len(historical_values) >= 20:
                # Calculate trend
                recent_values = historical_values[-10:]
                older_values = historical_values[-20:-10]
                
                recent_avg = statistics.mean(recent_values)
                older_avg = statistics.mean(older_values)
                
                trend_factor = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0
                features["trend_factor"] = trend_factor
                
                # Calculate volatility
                volatility = statistics.stdev(historical_values)
                features["volatility"] = volatility
                
                factors[SeverityFactor.TREND_IMPACT] = min(1.0, abs(trend_factor) * 2)
        
        # Simplified ML scoring (heuristic)
        score = 0
        
        # Deviation score
        if deviation_ratio > 3:
            score += 0.4
        elif deviation_ratio > 2:
            score += 0.3
        elif deviation_ratio > 1.5:
            score += 0.2
        elif deviation_ratio > 1:
            score += 0.1
        
        # Trend score
        if "trend_factor" in features:
            if abs(features["trend_factor"]) > 0.2:
                score += 0.3
            elif abs(features["trend_factor"]) > 0.1:
                score += 0.2
            elif abs(features["trend_factor"]) > 0.05:
                score += 0.1
        
        # Volatility score
        if "volatility" in features:
            if features["volatility"] > baseline_value * 0.5:
                score += 0.3
            elif features["volatility"] > baseline_value * 0.3:
                score += 0.2
            elif features["volatility"] > baseline_value * 0.1:
                score += 0.1
        
        # Determine severity based on score
        if score > 0.8:
            classified_severity = AlertSeverity.CRITICAL
        elif score > 0.6:
            classified_severity = AlertSeverity.ERROR
        elif score > 0.4:
            classified_severity = AlertSeverity.WARNING
        else:
            classified_severity = AlertSeverity.INFO
        
        confidence = min(1.0, score)
        
        reasoning = f"ML-based classification with score {score:.2f}"
        
        return SeverityClassification(
            alert_id=alert.alert_id,
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            deviation_ratio=deviation_ratio,
            classified_severity=classified_severity,
            confidence=confidence,
            classification_method=ClassificationMethod.ML_BASED,
            factors=factors,
            applied_rules=[],
            reasoning=reasoning,
            classification_time=datetime.utcnow(),
            context={
                "selector_name": getattr(event, 'selector_name', None) if event else None,
                "correlation_id": getattr(event, 'correlation_id', None) if event else None,
                "features": features
            }
        )
    
    async def _classify_hybrid(
        self,
        alert: Alert,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        deviation_ratio: float,
        rules: List[SeverityRule],
        event: Optional[TelemetryEvent]
    ) -> SeverityClassification:
        """Classify using hybrid approach combining multiple methods."""
        # Get classifications from different methods
        rule_classification = await self._classify_rule_based(
            alert, metric_name, current_value, baseline_value, deviation_ratio, rules, event
        )
        statistical_classification = await self._classify_statistical(
            alert, metric_name, current_value, baseline_value, deviation_ratio, event
        )
        ml_classification = await self._classify_ml_based(
            alert, metric_name, current_value, baseline_value, deviation_ratio, event
        )
        
        # Combine classifications with weights
        severity_votes = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.ERROR: 0,
            AlertSeverity.WARNING: 0,
            AlertSeverity.INFO: 0
        }
        
        confidence_weighted_votes = {
            AlertSeverity.CRITICAL: 0.0,
            AlertSeverity.ERROR: 0.0,
            AlertSeverity.WARNING: 0.0,
            AlertSeverity.INFO: 0.0
        }
        
        # Weight votes by confidence
        classifications = [rule_classification, statistical_classification, ml_classification]
        weights = [0.4, 0.3, 0.3]  # Rule-based gets higher weight
        
        for classification, weight in zip(classifications, weights):
            severity_votes[classification.classified_severity] += 1
            confidence_weighted_votes[classification.classified_severity] += classification.confidence * weight
        
        # Determine final severity
        max_severity = max(confidence_weighted_votes.items(), key=lambda x: x[1])
        classified_severity = max_severity[0]
        confidence = min(1.0, max_severity[1])
        
        # Combine factors
        combined_factors = {}
        for classification in classifications:
            for factor, value in classification.factors.items():
                if factor not in combined_factors:
                    combined_factors[factor] = []
                combined_factors[factor].append(value)
        
        # Average factors
        for factor, values in combined_factors.items():
            combined_factors[factor] = statistics.mean(values)
        
        # Combine applied rules
        applied_rules = list(set(rule_classification.applied_rules))
        
        reasoning = f"Hybrid classification: rule={rule_classification.classified_severity.value}, " \
                   f"stat={statistical_classification.classified_severity.value}, " \
                   f"ml={ml_classification.classified_severity.value}"
        
        return SeverityClassification(
            alert_id=alert.alert_id,
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            deviation_ratio=deviation_ratio,
            classified_severity=classified_severity,
            confidence=confidence,
            classification_method=ClassificationMethod.HYBRID,
            factors=combined_factors,
            applied_rules=applied_rules,
            reasoning=reasoning,
            classification_time=datetime.utcnow(),
            context={
                "selector_name": getattr(event, 'selector_name', None) if event else None,
                "correlation_id": getattr(event, 'correlation_id', None) if event else None,
                "rule_severity": rule_classification.classified_severity.value,
                "statistical_severity": statistical_classification.classified_severity.value,
                "ml_severity": ml_classification.classified_severity.value
            }
        )
    
    def _evaluate_rule_conditions(self, conditions: List[Dict[str, Any]], value: float) -> bool:
        """Evaluate rule conditions."""
        for condition in conditions:
            operator = condition.get("operator")
            threshold = condition.get("value")
            
            if operator == ">" and value <= threshold:
                return False
            elif operator == "<" and value >= threshold:
                return False
            elif operator == ">=" and value < threshold:
                return False
            elif operator == "<=" and value > threshold:
                return False
            elif operator == "==" and abs(value - threshold) > 0.001:
                return False
            elif operator == "!=" and abs(value - threshold) < 0.001:
                return False
        
        return True
    
    def _default_severity_classification(self, deviation_ratio: float) -> Tuple[AlertSeverity, float]:
        """Default severity classification based on deviation ratio."""
        if deviation_ratio > 5:
            return AlertSeverity.CRITICAL, 0.9
        elif deviation_ratio > 3:
            return AlertSeverity.ERROR, 0.8
        elif deviation_ratio > 2:
            return AlertSeverity.WARNING, 0.7
        elif deviation_ratio > 1.5:
            return AlertSeverity.INFO, 0.6
        else:
            return AlertSeverity.INFO, 0.5
    
    async def _update_baseline_data(self, metric_name: str, event: TelemetryEvent) -> None:
        """Update baseline data for a metric."""
        # Extract metric value from event
        value = None
        
        if event.performance_metrics:
            perf = event.performance_metrics
            if metric_name == "resolution_time_ms":
                value = perf.resolution_time_ms
            elif metric_name == "strategy_execution_time_ms":
                value = perf.strategy_execution_time_ms
            elif metric_name == "total_duration_ms":
                value = perf.total_duration_ms
            elif metric_name == "memory_usage_mb":
                value = perf.memory_usage_mb
            elif metric_name == "cpu_usage_percent":
                value = perf.cpu_usage_percent
            elif metric_name == "network_requests_count":
                value = perf.network_requests_count
            elif metric_name == "dom_operations_count":
                value = perf.dom_operations_count
        
        if event.quality_metrics:
            quality = event.quality_metrics
            if metric_name == "confidence_score":
                value = quality.confidence_score
            elif metric_name == "success_rate":
                value = 1.0 if quality.success else 0.0
            elif metric_name == "elements_found":
                value = float(quality.elements_found) if quality.elements_found is not None else None
            elif metric_name == "strategy_success_rate":
                value = quality.strategy_success_rate
        
        if value is not None:
            self._metric_baselines[metric_name].append({
                "value": value,
                "timestamp": event.timestamp
            })
    
    async def _get_baseline_value(self, metric_name: str) -> float:
        """Get baseline value for a metric."""
        if metric_name in self._metric_baselines:
            values = [item["value"] for item in self._metric_baselines[metric_name]]
            if values:
                return statistics.mean(values)
        
        return 0.0
    
    def _calculate_deviation_ratio(self, current_value: float, baseline_value: float) -> float:
        """Calculate deviation ratio."""
        if baseline_value == 0:
            return 1.0 if current_value != 0 else 0.0
        
        return abs(current_value - baseline_value) / baseline_value
    
    def _update_statistics(self, classification: SeverityClassification) -> None:
        """Update classification statistics."""
        self._statistics.total_classifications += 1
        self._statistics.last_classification = classification.classification_time
        
        # Update by severity
        severity_name = classification.classified_severity.value
        if severity_name not in self._statistics.classifications_by_severity:
            self._statistics.classifications_by_severity[severity_name] = 0
        self._statistics.classifications_by_severity[severity_name] += 1
        
        # Update by method
        method_name = classification.classification_method.value
        if method_name not in self._statistics.classifications_by_method:
            self._statistics.classifications_by_method[method_name] = 0
        self._statistics.classifications_by_method[method_name] += 1
        
        # Update average confidence
        total_classifications = self._statistics.total_classifications
        current_avg = self._statistics.average_confidence
        new_avg = ((current_avg * (total_classifications - 1)) + classification.confidence) / total_classifications
        self._statistics.average_confidence = new_avg
        
        # Update most common
        if self._statistics.classifications_by_severity:
            self._statistics.most_common_severity = max(
                self._statistics.classifications_by_severity,
                key=self._statistics.classifications_by_severity.get
            )
        
        if self._statistics.classifications_by_method:
            self._statistics.most_common_method = max(
                self._statistics.classifications_by_method,
                key=self._statistics.classifications_by_method.get
            )
