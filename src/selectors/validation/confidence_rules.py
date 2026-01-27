"""
Confidence score validation rules for Selector Engine.

Provides comprehensive confidence validation with context-aware adjustments,
trend analysis, and anomaly detection as specified in the API contracts.
"""

import asyncio
import json
import math
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path

from src.observability.logger import get_logger
from src.observability.events import publish_event
from src.utils.exceptions import (
    ConfidenceValidationError, ValidationError, ConfigurationError
)
from src.models.selector_models import (
    SelectorResult, ElementInfo, ValidationResult, ValidationType,
    StrategyPattern, StrategyType, SemanticSelector
)
from src.config.settings import get_config


@dataclass
class ConfidenceValidationResult:
    """Result of confidence score validation."""
    is_valid: bool
    confidence_score: float
    validation_level: str  # "perfect", "high", "medium", "low", "failed"
    risk_level: str  # "low", "medium", "high", "critical"
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)
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
class ConsistencyResult:
    """Result of confidence consistency analysis."""
    is_consistent: bool
    variance: float
    average_confidence: float
    confidence_range: Tuple[float, float]
    sample_size: int
    trend_direction: str  # "stable", "improving", "declining"
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TrendAnalysis:
    """Result of confidence trend analysis."""
    trend_direction: str  # "improving", "declining", "stable"
    trend_strength: float  # 0.0 to 1.0
    confidence_change: float  # Change in confidence over time
    recommendation: str
    confidence: float  # Confidence in trend analysis
    analyzed_period: str
    data_points: int


@dataclass
class AnomalyDetection:
    """Result of anomaly detection."""
    has_anomalies: bool
    anomalies: List[Dict[str, Any]]
    anomaly_score: float  # Overall anomaly score
    detected_patterns: List[str]
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RuleValidation:
    """Result of rule-based validation."""
    is_valid: bool
    violations: List[Dict[str, Any]]
    applied_rules: List[str]
    rule_compliance_score: float
    context_adjustments: Dict[str, Any]


class ConfidenceValidator:
    """Validates confidence scores with comprehensive rule engine."""
    
    def __init__(self):
        self._logger = get_logger("confidence_validator")
        self._config = get_config()
        
        # Validation rules
        self._validation_rules = {
            "min_confidence": 0.0,
            "max_confidence": 1.0,
            "min_validation_score": 0.5,
            "max_resolution_time": 5000.0,
            "required_validation_types": ["regex"],
            "forbidden_attributes": ["hidden", "disabled", "aria-hidden"],
            "min_visibility": True,
            "min_interactability": False
        }
        
        # Context-specific adjustments
        self._context_adjustments = {
            "production": {
                "min_confidence": 0.8,
                "min_validation_score": 0.9,
                "max_resolution_time": 1000.0
            },
            "staging": {
                "min_confidence": 0.7,
                "min_validation_score": 0.8,
                "max_resolution_time": 1500.0
            },
            "development": {
                "min_confidence": 0.6,
                "min_validation_score": 0.7,
                "max_resolution_time": 2000.0
            },
            "testing": {
                "min_confidence": 0.5,
                "min_validation_score": 0.6,
                "max_resolution_time": 3000.0
            }
        }
        
        # Validation history
        self._validation_history: List[ConfidenceValidationResult] = []
        self._violations: List[ThresholdViolation] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load existing history
        self._load_history()
        
        self._logger.info("ConfidenceValidator initialized")
    
    def validate_confidence_score(self, result: SelectorResult) -> ConfidenceValidationResult:
        """
        Validate confidence score against comprehensive rules.
        
        Args:
            result: Selector result to validate
            
        Returns:
            Confidence validation result
        """
        try:
            violations = []
            recommendations = []
            
            # Basic confidence score validation
            if result.confidence_score < 0.0 or result.confidence_score > 1.0:
                violations.append({
                    "type": "invalid_confidence_range",
                    "actual": result.confidence_score,
                    "expected": "0.0 to 1.0",
                    "severity": "critical"
                })
                recommendations.append("Confidence score must be between 0.0 and 1.0")
            
            # Determine validation level
            validation_level = self._determine_validation_level(result.confidence_score)
            risk_level = self._determine_risk_level(result.confidence_score, violations)
            
            # Validate element info if available
            if result.element_info:
                element_violations = self._validate_element_info(result.element_info)
                violations.extend(element_violations)
                
                # Add recommendations based on element validation
                if element_violations:
                    recommendations.extend(self._get_element_recommendations(element_violations))
            
            # Validate validation results
            if result.validation_results:
                validation_violations = self._validate_validation_results(result.validation_results)
                violations.extend(validation_violations)
            
            # Validate performance
            performance_violations = self._validate_performance(result)
            violations.extend(performance_violations)
            
            # Determine overall validity
            is_valid = len(violations) == 0 or all(v["severity"] in ["info", "warning"] for v in violations)
            
            # Create result
            validation_result = ConfidenceValidationResult(
                is_valid=is_valid,
                confidence_score=result.confidence_score,
                validation_level=validation_level,
                risk_level=risk_level,
                violations=violations,
                recommendations=recommendations,
                metadata={
                    "selector_name": getattr(result, 'selector_name', 'unknown'),
                    "strategy_used": getattr(result, 'strategy_used', 'unknown'),
                    "resolution_time": getattr(result, 'resolution_time', 0.0)
                }
            )
            
            # Store result
            self._store_validation_result(validation_result)
            
            self._logger.info(
                "confidence_validation_completed",
                confidence_score=result.confidence_score,
                validation_level=validation_level,
                is_valid=is_valid,
                violations=len(violations)
            )
            
            return validation_result
            
        except Exception as e:
            self._logger.error(
                "confidence_validation_failed",
                error=str(e)
            )
            raise ConfidenceValidationError(f"Confidence validation failed: {str(e)}")
    
    def validate_against_threshold(self, result: SelectorResult, threshold: float) -> RuleValidation:
        """
        Validate result against specific threshold.
        
        Args:
            result: Selector result to validate
            threshold: Threshold to validate against
            
        Returns:
            Rule validation result
        """
        try:
            violations = []
            applied_rules = ["threshold_validation"]
            
            # Check threshold violation
            if result.confidence_score < threshold:
                violations.append({
                    "rule": "threshold_violation",
                    "actual": result.confidence_score,
                    "required": threshold,
                    "violation_amount": threshold - result.confidence_score,
                    "severity": self._calculate_threshold_severity(result.confidence_score, threshold)
                })
            
            # Calculate compliance score
            compliance_score = max(0.0, min(1.0, result.confidence_score / threshold))
            
            return RuleValidation(
                is_valid=len(violations) == 0,
                violations=violations,
                applied_rules=applied_rules,
                rule_compliance_score=compliance_score,
                context_adjustments={}
            )
            
        except Exception as e:
            self._logger.error(
                "threshold_validation_failed",
                error=str(e)
            )
            raise ConfidenceValidationError(f"Threshold validation failed: {str(e)}")
    
    def validate_against_rules(self, result: SelectorResult, rules: Dict[str, Any]) -> RuleValidation:
        """
        Validate result against custom rules.
        
        Args:
            result: Selector result to validate
            rules: Custom validation rules
            
        Returns:
            Rule validation result
        """
        try:
            violations = []
            applied_rules = []
            
            # Apply each rule
            for rule_name, rule_config in rules.items():
                applied_rules.append(rule_name)
                
                if rule_name == "min_confidence":
                    if result.confidence_score < rule_config:
                        violations.append({
                            "rule": rule_name,
                            "actual": result.confidence_score,
                            "required": rule_config,
                            "severity": "error"
                        })
                
                elif rule_name == "max_resolution_time":
                    if result.resolution_time > rule_config:
                        violations.append({
                            "rule": rule_name,
                            "actual": result.resolution_time,
                            "required": rule_config,
                            "severity": "warning"
                        })
                
                elif rule_name == "min_validation_score":
                    validation_score = self._calculate_validation_score(result.validation_results)
                    if validation_score < rule_config:
                        violations.append({
                            "rule": rule_name,
                            "actual": validation_score,
                            "required": rule_config,
                            "severity": "error"
                        })
                
                elif rule_name == "required_validation_types":
                    validation_types = set(vr.rule_type for vr in result.validation_results)
                    required_types = set(rule_config)
                    missing_types = required_types - validation_types
                    if missing_types:
                        violations.append({
                            "rule": rule_name,
                            "actual": list(validation_types),
                            "required": list(required_types),
                            "missing": list(missing_types),
                            "severity": "warning"
                        })
                
                elif rule_name == "forbidden_attributes":
                    if result.element_info:
                        element_attrs = set(result.element_info.attributes.keys())
                        forbidden_attrs = set(rule_config)
                        found_forbidden = element_attrs & forbidden_attrs
                        if found_forbidden:
                            violations.append({
                                "rule": rule_name,
                                "found": list(found_forbidden),
                                "forbidden": list(forbidden_attrs),
                                "severity": "error"
                            })
            
            # Calculate compliance score
            total_rules = len(rules)
            passed_rules = total_rules - len(violations)
            compliance_score = passed_rules / total_rules if total_rules > 0 else 0.0
            
            return RuleValidation(
                is_valid=len(violations) == 0,
                violations=violations,
                applied_rules=applied_rules,
                rule_compliance_score=compliance_score,
                context_adjustments={}
            )
            
        except Exception as e:
            self._logger.error(
                "rules_validation_failed",
                error=str(e)
            )
            raise ConfidenceValidationError(f"Rules validation failed: {str(e)}")
    
    def validate_with_context(self, result: SelectorResult, context: Dict[str, Any]) -> ConfidenceValidationResult:
        """
        Validate result with context-aware adjustments.
        
        Args:
            result: Selector result to validate
            context: Context information
            
        Returns:
            Context-aware validation result
        """
        try:
            # Get base validation
            base_result = self.validate_confidence_score(result)
            
            # Apply context adjustments
            environment = context.get("environment", "development")
            page_type = context.get("page_type", "normal")
            time_of_day = context.get("time_of_day", "normal")
            user_impact = context.get("user_impact", "medium")
            
            # Get context-specific rules
            context_rules = self._context_adjustments.get(environment, {})
            
            # Adjust thresholds based on context
            adjusted_threshold = context_rules.get("min_confidence", 0.6)
            
            # Additional context-based adjustments
            if page_type == "critical":
                adjusted_threshold += 0.1
            if user_impact == "high":
                adjusted_threshold += 0.1
            if time_of_day == "peak_hours":
                adjusted_threshold += 0.05
            
            # Cap adjusted threshold
            adjusted_threshold = min(0.95, adjusted_threshold)
            
            # Re-validate with adjusted threshold
            threshold_result = self.validate_against_threshold(result, adjusted_threshold)
            
            # Merge results
            if not threshold_result.is_valid:
                base_result.violations.extend(threshold_result.violations)
                base_result.is_valid = False
                base_result.risk_level = "high"
                base_result.recommendations.append(f"Context requires higher confidence: {adjusted_threshold:.2f}")
            
            # Add context metadata
            base_result.metadata.update({
                "context": context,
                "adjusted_threshold": adjusted_threshold,
                "context_factors": {
                    "environment": environment,
                    "page_type": page_type,
                    "time_of_day": time_of_day,
                    "user_impact": user_impact
                }
            })
            
            return base_result
            
        except Exception as e:
            self._logger.error(
                "context_validation_failed",
                error=str(e)
            )
            raise ConfidenceValidationError(f"Context validation failed: {str(e)}")
    
    def validate_consistency(self, results: List[SelectorResult]) -> ConsistencyResult:
        """
        Validate confidence score consistency across multiple results.
        
        Args:
            results: List of selector results
            
        Returns:
            Consistency validation result
        """
        try:
            if len(results) < 3:
                return ConsistencyResult(
                    is_consistent=True,
                    variance=0.0,
                    average_confidence=0.0,
                    confidence_range=(0.0, 0.0),
                    sample_size=len(results),
                    trend_direction="stable",
                    recommendations=["Insufficient data for consistency analysis"]
                )
            
            # Calculate statistics
            confidence_scores = [r.confidence_score for r in results]
            average_confidence = sum(confidence_scores) / len(confidence_scores)
            
            # Calculate variance
            variance = sum((score - average_confidence) ** 2 for score in confidence_scores) / len(confidence_scores)
            std_deviation = math.sqrt(variance)
            
            # Determine consistency
            is_consistent = std_deviation < 0.1  # Low variance indicates consistency
            
            # Determine confidence range
            min_confidence = min(confidence_scores)
            max_confidence = max(confidence_scores)
            confidence_range = (min_confidence, max_confidence)
            
            # Analyze trend
            trend_direction = self._analyze_simple_trend(confidence_scores)
            
            # Generate recommendations
            recommendations = []
            if not is_consistent:
                recommendations.append(f"High variance detected (σ={std_deviation:.3f})")
                recommendations.append("Consider investigating strategy performance")
            
            if max_confidence - min_confidence > 0.3:
                recommendations.append("Large confidence range indicates inconsistent performance")
            
            return ConsistencyResult(
                is_consistent=is_consistent,
                variance=variance,
                average_confidence=average_confidence,
                confidence_range=confidence_range,
                sample_size=len(results),
                trend_direction=trend_direction,
                recommendations=recommendations
            )
            
        except Exception as e:
            self._logger.error(
                "consistency_validation_failed",
                error=str(e)
            )
            raise ConfidenceValidationError(f"Consistency validation failed: {str(e)}")
    
    def analyze_trend(self, results: List[SelectorResult]) -> TrendAnalysis:
        """
        Analyze confidence score trend over time.
        
        Args:
            results: List of selector results ordered by timestamp
            
        Returns:
            Trend analysis result
        """
        try:
            if len(results) < 5:
                return TrendAnalysis(
                    trend_direction="stable",
                    trend_strength=0.0,
                    confidence_change=0.0,
                    recommendation="Insufficient data for trend analysis",
                    confidence=0.0,
                    analyzed_period="insufficient",
                    data_points=len(results)
                )
            
            # Extract confidence scores and timestamps
            confidence_scores = [r.confidence_score for r in results]
            timestamps = [r.timestamp for r in results]
            
            # Calculate trend using linear regression
            n = len(confidence_scores)
            x_values = list(range(n))  # Use indices as x values
            
            # Calculate linear regression
            sum_x = sum(x_values)
            sum_y = sum(confidence_scores)
            sum_xy = sum(x * y for x, y in zip(x_values, confidence_scores))
            sum_x2 = sum(x * x for x in x_values)
            
            # Calculate slope (trend)
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # Determine trend direction and strength
            if abs(slope) < 0.01:
                trend_direction = "stable"
                trend_strength = 0.0
            elif slope > 0:
                trend_direction = "improving"
                trend_strength = min(1.0, abs(slope) * 10)
            else:
                trend_direction = "declining"
                trend_strength = min(1.0, abs(slope) * 10)
            
            # Calculate confidence change
            confidence_change = confidence_scores[-1] - confidence_scores[0]
            
            # Generate recommendation
            if trend_direction == "declining" and trend_strength > 0.5:
                recommendation = "Investigate declining confidence trend"
            elif trend_direction == "improving" and trend_strength > 0.5:
                recommendation = "Maintain current strategy performance"
            else:
                recommendation = "Monitor confidence trends"
            
            # Calculate confidence in analysis
            analysis_confidence = min(1.0, len(results) / 20.0)
            
            # Determine analyzed period
            if timestamps:
                time_span = timestamps[-1] - timestamps[0]
                analyzed_period = f"{time_span.days} days" if time_span.days > 0 else f"{time_span.seconds // 3600} hours"
            else:
                analyzed_period = "unknown"
            
            return TrendAnalysis(
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                confidence_change=confidence_change,
                recommendation=recommendation,
                confidence=analysis_confidence,
                analyzed_period=analyzed_period,
                data_points=len(results)
            )
            
        except Exception as e:
            self._logger.error(
                "trend_analysis_failed",
                error=str(e)
            )
            raise ConfidenceValidationError(f"Trend analysis failed: {str(e)}")
    
    def detect_anomalies(self, results: List[SelectorResult]) -> AnomalyDetection:
        """
        Detect anomalies in confidence scores.
        
        Args:
            results: List of selector results
            
        Returns:
            Anomaly detection result
        """
        try:
            anomalies = []
            detected_patterns = []
            
            if len(results) < 10:
                return AnomalyDetection(
                    has_anomalies=False,
                    anomalies=[],
                    anomaly_score=0.0,
                    detected_patterns=[],
                    recommendations=["Insufficient data for anomaly detection"]
                )
            
            # Calculate statistics
            confidence_scores = [r.confidence_score for r in results]
            mean_confidence = sum(confidence_scores) / len(confidence_scores)
            std_confidence = math.sqrt(sum((score - mean_confidence) ** 2 for score in confidence_scores) / len(confidence_scores))
            
            # Detect anomalies using z-score
            z_scores = [(score - mean_confidence) / std_confidence if std_confidence > 0 else 0 for score in confidence_scores]
            
            # Find significant anomalies (|z-score| > 2)
            anomaly_threshold = 2.0
            for i, (result, z_score) in enumerate(zip(results, z_scores)):
                if abs(z_score) > anomaly_threshold:
                    anomaly = {
                        "index": i,
                        "selector_name": getattr(result, 'selector_name', 'unknown'),
                        "confidence_score": result.confidence_score,
                        "z_score": z_score,
                        "severity": "high" if abs(z_score) > 3 else "medium",
                        "timestamp": getattr(result, 'timestamp', datetime.utcnow()).isoformat()
                    }
                    anomalies.append(anomaly)
            
            # Detect patterns
            if len(anomalies) > 0:
                detected_patterns.append("statistical_outliers")
            
            # Calculate overall anomaly score
            anomaly_score = len(anomalies) / len(results)
            
            # Generate recommendations
            recommendations = []
            if anomalies:
                recommendations.append(f"Found {len(anomalies)} statistical anomalies")
                recommendations.append("Investigate outlier performance")
            
            return AnomalyDetection(
                has_anomalies=len(anomalies) > 0,
                anomalies=anomalies,
                anomaly_score=anomaly_score,
                detected_patterns=detected_patterns,
                recommendations=recommendations
            )
            
        except Exception as e:
            self._logger.error(
                "anomaly_detection_failed",
                error=str(e)
            )
            raise ConfidenceValidationError(f"Anomaly detection failed: {str(e)}")
    
    def _determine_validation_level(self, confidence_score: float) -> str:
        """Determine validation level based on confidence score."""
        if confidence_score >= 0.95:
            return "perfect"
        elif confidence_score >= 0.85:
            return "high"
        elif confidence_score >= 0.70:
            return "medium"
        elif confidence_score >= 0.50:
            return "low"
        else:
            return "failed"
    
    def _determine_risk_level(self, confidence_score: float, violations: List[Dict[str, Any]]) -> str:
        """Determine risk level based on confidence and violations."""
        if confidence_score < 0.3 or any(v.get("severity") == "critical" for v in violations):
            return "critical"
        elif confidence_score < 0.5 or any(v.get("severity") == "error" for v in violations):
            return "high"
        elif confidence_score < 0.7 or any(v.get("severity") == "warning" for v in violations):
            return "medium"
        else:
            return "low"
    
    def _validate_element_info(self, element_info: ElementInfo) -> List[Dict[str, Any]]:
        """Validate element information."""
        violations = []
        
        # Check visibility
        if not element_info.visibility:
            violations.append({
                "type": "element_not_visible",
                "severity": "warning"
            })
        
        # Check interactability
        if not element_info.interactable:
            violations.append({
                "type": "element_not_interactable",
                "severity": "info"
            })
        
        # Check for suspicious attributes
        suspicious_attrs = ["hidden", "disabled", "aria-hidden"]
        for attr in suspicious_attrs:
            if attr in element_info.attributes:
                violations.append({
                    "type": "suspicious_attribute",
                    "attribute": attr,
                    "severity": "warning"
                })
        
        # Check CSS classes
        if "hidden" in element_info.css_classes:
            violations.append({
                "type": "hidden_element",
                "severity": "warning"
            })
        
        return violations
    
    def _validate_validation_results(self, validation_results: List[ValidationResult]) -> List[Dict[str, Any]]:
        """Validate validation results."""
        violations = []
        
        if not validation_results:
            violations.append({
                "type": "no_validation_results",
                "severity": "warning"
            })
            return violations
        
        # Check for failed validations
        failed_validations = [vr for vr in validation_results if not vr.passed]
        if failed_validations:
            violations.append({
                "type": "validation_failures",
                "count": len(failed_validations),
                "severity": "error"
            })
        
        # Check validation scores
        low_score_validations = [vr for vr in validation_results if vr.score < 0.5]
        if low_score_validations:
            violations.append({
                "type": "low_validation_scores",
                "count": len(low_score_validations),
                "severity": "warning"
            })
        
        return violations
    
    def _validate_performance(self, result: SelectorResult) -> List[Dict[str, Any]]:
        """Validate performance metrics."""
        violations = []
        
        # Check resolution time
        if result.resolution_time > 5000:  # 5 seconds
            violations.append({
                "type": "slow_resolution",
                "actual": result.resolution_time,
                "threshold": 5000,
                "severity": "warning"
            })
        elif result.resolution_time > 10000:  # 10 seconds
            violations.append({
                "type": "very_slow_resolution",
                "actual": result.resolution_time,
                "threshold": 10000,
                "severity": "error"
            })
        
        return violations
    
    def _calculate_validation_score(self, validation_results: List[ValidationResult]) -> float:
        """Calculate overall validation score."""
        if not validation_results:
            return 0.0
        
        total_weight = sum(vr.weight for vr in validation_results)
        if total_weight == 0:
            return 0.0
        
        weighted_score = sum(vr.score * vr.weight for vr in validation_results)
        return weighted_score / total_weight
    
    def _calculate_threshold_severity(self, actual: float, required: float) -> str:
        """Calculate threshold violation severity."""
        violation_amount = required - actual
        
        if violation_amount >= 0.3:
            return "critical"
        elif violation_amount >= 0.2:
            return "error"
        elif violation_amount >= 0.1:
            return "warning"
        else:
            return "info"
    
    def _analyze_simple_trend(self, values: List[float]) -> str:
        """Simple trend analysis."""
        if len(values) < 3:
            return "stable"
        
        # Compare first half with second half
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / (len(values) - mid)
        
        if second_half_avg > first_half_avg + 0.05:
            return "improving"
        elif second_half_avg < first_half_avg - 0.05:
            return "declining"
        else:
            return "stable"
    
    def _get_element_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Get recommendations based on element violations."""
        recommendations = []
        
        for violation in violations:
            if violation["type"] == "element_not_visible":
                recommendations.append("Ensure element is visible for reliable selection")
            elif violation["type"] == "element_not_interactable":
                recommendations.append("Consider interactable elements for better user experience")
            elif violation["type"] == "suspicious_attribute":
                recommendations.append(f"Avoid elements with '{violation['attribute']}' attribute")
            elif violation["type"] == "hidden_element":
                recommendations.append("Avoid hidden elements in selectors")
        
        return recommendations
    
    def _store_validation_result(self, result: ConfidenceValidationResult) -> None:
        """Store validation result in history."""
        with self._lock:
            self._validation_history.append(result)
            
            # Keep only last 1000 results
            if len(self._validation_history) > 1000:
                self._validation_history = self._validation_history[-1000:]
        
        # Save periodically
        if len(self._validation_history) % 50 == 0:
            self._save_history()
    
    def _load_history(self) -> None:
        """Load validation history from storage."""
        try:
            storage_path = Path("data/validation_history.json")
            if storage_path.exists():
                with open(storage_path, 'r') as f:
                    data = json.load(f)
                
                # Convert dictionaries back to ConfidenceValidationResult objects
                for result_data in data.get("history", []):
                    result = ConfidenceValidationResult(
                        is_valid=result_data["is_valid"],
                        confidence_score=result_data["confidence_score"],
                        validation_level=result_data["validation_level"],
                        risk_level=result_data["risk_level"],
                        violations=result_data["violations"],
                        recommendations=result_data["recommendations"],
                        validated_at=datetime.fromisoformat(result_data["validated_at"]),
                        metadata=result_data.get("metadata", {})
                    )
                    self._validation_history.append(result)
                
                self._logger.info(
                    "validation_history_loaded",
                    results_loaded=len(self._validation_history)
                )
        except Exception as e:
            self._logger.warning(
                "validation_history_load_failed",
                error=str(e)
            )
    
    def _save_history(self) -> None:
        """Save validation history to storage."""
        try:
            # Ensure directory exists
            storage_path = Path("data")
            storage_path.mkdir(exist_ok=True)
            
            # Convert to serializable format
            history_data = {
                "history": [
                    {
                        "is_valid": result.is_valid,
                        "confidence_score": result.confidence_score,
                        "validation_level": result.validation_level,
                        "risk_level": result.risk_level,
                        "violations": result.violations,
                        "recommendations": result.recommendations,
                        "validated_at": result.validated_at.isoformat(),
                        "metadata": result.metadata
                    }
                    for result in self._validation_history
                ],
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Save to file
            history_file = storage_path / "validation_history.json"
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            self._logger.debug("validation_history_saved")
        except Exception as e:
            self._logger.error(
                "validation_history_save_failed",
                error=str(e)
            )


# Global confidence validator instance
confidence_validator = ConfidenceValidator()


def get_confidence_validator() -> ConfidenceValidator:
    """Get global confidence validator instance."""
    return confidence_validator
