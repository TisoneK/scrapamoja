"""
Confidence scoring algorithm for Selector Engine.

Implements weighted confidence scoring combining content validation, position stability,
strategy success history, and performance metrics as specified in the data model documentation.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.models.selector_models import (
    SelectorResult, ElementInfo, ValidationResult, ValidationType,
    StrategyPattern, StrategyType, ConfidenceMetrics
)
from src.selectors.context import DOMContext
from src.selectors.interfaces import IConfidenceScorer
from src.observability.logger import get_logger
from src.utils.exceptions import ValidationError
from src.config.settings import get_config


@dataclass
class ConfidenceWeights:
    """Weights for different confidence factors."""
    content_validation: float = 0.4
    position_stability: float = 0.2
    strategy_history: float = 0.2
    performance_metrics: float = 0.1
    element_visibility: float = 0.05
    element_interactability: float = 0.05


@dataclass
class ScoringContext:
    """Context information for confidence scoring."""
    selector_name: str
    strategy_used: str
    resolution_time: float
    timestamp: datetime
    context: DOMContext
    metadata: Dict[str, Any]


class ConfidenceScorer(IConfidenceScorer):
    """Main confidence scoring implementation."""
    
    def __init__(self):
        self._logger = get_logger("confidence_scorer")
        self._weights = ConfidenceWeights()
        self._strategy_metrics: Dict[str, ConfidenceMetrics] = {}
        self._config = get_config()
    
    def calculate_confidence(self, result: SelectorResult, validations: List[ValidationResult]) -> float:
        """
        Calculate confidence score for selector result.
        
        Args:
            result: Selector resolution result
            validations: List of validation results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not result.success or not result.element_info:
            return 0.0
        
        try:
            # Calculate individual confidence factors
            content_score = self._calculate_content_confidence(result.element_info, validations)
            position_score = self._calculate_position_confidence(result.element_info)
            strategy_score = self._calculate_strategy_confidence(result.selector_name, result.strategy_used)
            performance_score = self._calculate_performance_confidence(result.resolution_time)
            visibility_score = self._calculate_visibility_confidence(result.element_info)
            interactability_score = self._calculate_interactability_confidence(result.element_info)
            
            # Apply weights and combine scores
            confidence = (
                content_score * self._weights.content_validation +
                position_score * self._weights.position_stability +
                strategy_score * self._weights.strategy_history +
                performance_score * self._weights.performance_metrics +
                visibility_score * self._weights.element_visibility +
                interactability_score * self._weights.element_interactability
            )
            
            # Ensure confidence is within bounds
            confidence = max(0.0, min(1.0, confidence))
            
            # Structured logging for confidence decision
            self._logger.info(
                "confidence_decision_made",
                selector_name=result.selector_name,
                strategy_used=result.strategy_used,
                final_confidence=confidence,
                confidence_level=self._determine_confidence_level(confidence),
                decision_factors={
                    "content_validation": {
                        "score": content_score,
                        "weight": self._weights.content_validation,
                        "contribution": content_score * self._weights.content_validation,
                        "validation_count": len(validations),
                        "passed_validations": sum(1 for v in validations if v.passed)
                    },
                    "position_stability": {
                        "score": position_score,
                        "weight": self._weights.position_stability,
                        "contribution": position_score * self._weights.position_stability,
                        "dom_path": result.element_info.dom_path,
                        "css_classes": result.element_info.css_classes[:5]  # Limit for logging
                    },
                    "strategy_history": {
                        "score": strategy_score,
                        "weight": self._weights.strategy_history,
                        "contribution": strategy_score * self._weights.strategy_history,
                        "previous_success_rate": self._get_strategy_success_rate(result.strategy_used)
                    },
                    "performance_metrics": {
                        "score": performance_score,
                        "weight": self._weights.performance_metrics,
                        "contribution": performance_score * self._weights.performance_metrics,
                        "resolution_time": result.resolution_time,
                        "performance_rating": self._get_performance_rating(result.resolution_time)
                    },
                    "element_visibility": {
                        "score": visibility_score,
                        "weight": self._weights.element_visibility,
                        "contribution": visibility_score * self._weights.element_visibility,
                        "is_visible": result.element_info.visibility
                    },
                    "element_interactability": {
                        "score": interactability_score,
                        "weight": self._weights.element_interactability,
                        "contribution": interactability_score * self._weights.element_interactability,
                        "is_interactable": result.element_info.interactable
                    }
                },
                element_info={
                    "tag_name": result.element_info.tag_name,
                    "text_length": len(result.element_info.text_content),
                    "attribute_count": len(result.element_info.attributes),
                    "css_class_count": len(result.element_info.css_classes)
                },
                resolution_metadata={
                    "timestamp": result.timestamp.isoformat() if hasattr(result, 'timestamp') else datetime.utcnow().isoformat(),
                    "validation_results_count": len(result.validation_results),
                    "success": result.success
                }
            )
            
            return confidence
            
        except Exception as e:
            self._logger.error(
                "confidence_calculation_failed",
                selector_name=result.selector_name,
                error=str(e)
            )
            return 0.0
    
    def validate_content(self, element_info: ElementInfo, rules: List[Any]) -> List[ValidationResult]:
        """Validate element content against rules."""
        results = []
        
        for rule in rules:
            try:
                result = self._validate_rule(element_info, rule)
                results.append(result)
            except Exception as e:
                self._logger.warning(
                    "rule_validation_failed",
                    rule_type=getattr(rule, 'type', 'unknown'),
                    error=str(e)
                )
                results.append(ValidationResult(
                    rule_type=getattr(rule, 'type', 'unknown'),
                    passed=False,
                    score=0.0,
                    message=f"Validation error: {e}"
                ))
        
        return results
    
    def get_threshold(self, context: str) -> float:
        """Get confidence threshold for context."""
        return self._config.selector_engine.default_confidence_threshold
    
    def update_strategy_metrics(self, selector_name: str, strategy_id: str, 
                              metrics: ConfidenceMetrics) -> None:
        """Update strategy performance metrics."""
        key = f"{selector_name}.{strategy_id}"
        self._strategy_metrics[key] = metrics
    
    def get_strategy_metrics(self, selector_name: str, strategy_id: str) -> Optional[ConfidenceMetrics]:
        """Get strategy performance metrics."""
        key = f"{selector_name}.{strategy_id}"
        return self._strategy_metrics.get(key)
    
    def _calculate_content_confidence(self, element_info: ElementInfo, 
                                     validations: List[ValidationResult]) -> float:
        """Calculate confidence based on content validation."""
        if not validations:
            # No validation rules, use basic content quality assessment
            return self._assess_basic_content_quality(element_info)
        
        # Weighted average of validation scores
        total_weight = sum(v.weight for v in validations)
        if total_weight == 0:
            return 0.0
        
        weighted_score = sum(v.score * v.weight for v in validations)
        base_confidence = weighted_score / total_weight
        
        # Apply content quality adjustments
        content_quality = self._assess_content_quality(element_info)
        
        # Combine validation results with content quality
        return (base_confidence * 0.7) + (content_quality * 0.3)
    
    def _calculate_position_confidence(self, element_info: ElementInfo) -> float:
        """Calculate confidence based on DOM position stability."""
        try:
            # Analyze DOM path for stability indicators
            dom_path = element_info.dom_path
            
            # Check for stable path indicators
            stability_score = 0.5  # Base score
            
            # Boost for IDs (most stable)
            if 'id=' in dom_path:
                stability_score += 0.3
            
            # Boost for specific classes (moderately stable)
            if '.class.' in dom_path or '.team-name' in dom_path:
                stability_score += 0.2
            
            # Boost for semantic HTML5 elements
            semantic_tags = ['header', 'footer', 'nav', 'main', 'section', 'article', 'aside']
            if any(tag in dom_path for tag in semantic_tags):
                stability_score += 0.1
            
            # Penalize for generic paths
            if dom_path.count('div') > 3:  # Too many nested divs
                stability_score -= 0.2
            
            if dom_path.count(':nth-child') > 1:  # Complex selectors
                stability_score -= 0.1
            
            return max(0.0, min(1.0, stability_score))
            
        except Exception as e:
            self._logger.warning(
                "position_confidence_calculation_failed",
                error=str(e)
            )
            return 0.5  # Default to moderate confidence
    
    def _calculate_strategy_confidence(self, selector_name: str, strategy_id: str) -> float:
        """Calculate confidence based on strategy success history."""
        try:
            metrics = self.get_strategy_metrics(selector_name, strategy_id)
            if not metrics:
                return 0.5  # Default for new strategies
            
            # Use reliability score which combines success rate and confidence
            return metrics.reliability_score
            
        except Exception as e:
            self._logger.warning(
                "strategy_confidence_calculation_failed",
                selector_name=selector_name,
                strategy_id=strategy_id,
                error=str(e)
            )
            return 0.5
    
    def _calculate_performance_confidence(self, resolution_time: float) -> float:
        """Calculate confidence based on performance metrics."""
        try:
            # Performance thresholds (in milliseconds)
            excellent_time = 50.0
            good_time = 100.0
            acceptable_time = 500.0
            slow_time = 1000.0
            
            if resolution_time <= excellent_time:
                return 1.0
            elif resolution_time <= good_time:
                # Linear interpolation between excellent and good
                ratio = (resolution_time - excellent_time) / (good_time - excellent_time)
                return 1.0 - (ratio * 0.1)  # 0.9 to 1.0
            elif resolution_time <= acceptable_time:
                # Linear interpolation between good and acceptable
                ratio = (resolution_time - good_time) / (acceptable_time - good_time)
                return 0.9 - (ratio * 0.4)  # 0.5 to 0.9
            elif resolution_time <= slow_time:
                # Linear interpolation between acceptable and slow
                ratio = (resolution_time - acceptable_time) / (slow_time - acceptable_time)
                return 0.5 - (ratio * 0.3)  # 0.2 to 0.5
            else:
                # Very slow, penalize heavily
                return max(0.0, 0.2 - (resolution_time - slow_time) / 10000)
                
        except Exception as e:
            self._logger.warning(
                "performance_confidence_calculation_failed",
                resolution_time=resolution_time,
                error=str(e)
            )
            return 0.5
    
    def _calculate_visibility_confidence(self, element_info: ElementInfo) -> float:
        """Calculate confidence based on element visibility."""
        return 1.0 if element_info.visibility else 0.0
    
    def _calculate_interactability_confidence(self, element_info: ElementInfo) -> float:
        """Calculate confidence based on element interactability."""
        return 1.0 if element_info.interactable else 0.0
    
    def _validate_rule(self, element_info: ElementInfo, rule: Any) -> ValidationResult:
        """Validate element content against a single rule."""
        try:
            rule_type = getattr(rule, 'type', ValidationType.REGEX)
            
            if rule_type == ValidationType.REGEX:
                return self._validate_regex_rule(element_info, rule)
            elif rule_type == ValidationType.DATA_TYPE:
                return self._validate_data_type_rule(element_info, rule)
            elif rule_type == ValidationType.SEMANTIC:
                return self._validate_semantic_rule(element_info, rule)
            elif rule_type == ValidationType.CUSTOM:
                return self._validate_custom_rule(element_info, rule)
            else:
                return ValidationResult(
                    rule_type=rule_type.value,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported rule type: {rule_type}"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_type=getattr(rule, 'type', 'unknown'),
                passed=False,
                score=0.0,
                message=f"Rule validation error: {e}"
            )
    
    def _validate_regex_rule(self, element_info: ElementInfo, rule: Any) -> ValidationResult:
        """Validate using regex pattern."""
        try:
            pattern = re.compile(rule.pattern)
            content = element_info.text_content.strip()
            
            if pattern.fullmatch(content):
                return ValidationResult(
                    rule_type=ValidationType.REGEX.value,
                    passed=True,
                    score=rule.weight,
                    message="Text matches regex pattern"
                )
            else:
                return ValidationResult(
                    rule_type=ValidationType.REGEX.value,
                    passed=False,
                    score=0.0,
                    message="Text does not match regex pattern"
                )
                
        except re.error as e:
            return ValidationResult(
                rule_type=ValidationType.REGEX.value,
                passed=False,
                score=0.0,
                message=f"Invalid regex pattern: {e}"
            )
    
    def _validate_data_type_rule(self, element_info: ElementInfo, rule: Any) -> ValidationResult:
        """Validate using data type checking."""
        try:
            content = element_info.text_content.strip()
            
            if rule.pattern == "float":
                try:
                    float(content)
                    return ValidationResult(
                        rule_type=ValidationType.DATA_TYPE.value,
                        passed=True,
                        score=rule.weight,
                        message="Content is a valid float"
                    )
                except ValueError:
                    return ValidationResult(
                        rule_type=ValidationType.DATA_TYPE.value,
                        passed=False,
                        score=0.0,
                        message="Content is not a valid float"
                    )
            elif rule.pattern == "int":
                try:
                    int(content)
                    return ValidationResult(
                        rule_type=ValidationType.DATA_TYPE.value,
                        passed=True,
                        score=rule.weight,
                        message="Content is a valid integer"
                    )
                except ValueError:
                    return ValidationResult(
                        rule_type=ValidationType.DATA_TYPE.value,
                        passed=False,
                        score=0.0,
                        message="Content is not a valid integer"
                    )
            elif rule.pattern == "string":
                return ValidationResult(
                    rule_type=ValidationType.DATA_TYPE.value,
                    passed=True,
                    score=rule.weight,
                    message="Content is a valid string"
                )
            elif rule.pattern == "boolean":
                if content.lower() in ['true', 'false', '1', '0', 'yes', 'no']:
                    return ValidationResult(
                        rule_type=ValidationType.DATA_TYPE.value,
                        passed=True,
                        score=rule.weight,
                        message="Content is a valid boolean"
                    )
                else:
                    return ValidationResult(
                        rule_type=ValidationType.DATA_TYPE.value,
                        passed=False,
                        score=0.0,
                        message="Content is not a valid boolean"
                    )
            else:
                return ValidationResult(
                    rule_type=ValidationType.DATA_TYPE.value,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported data type: {rule.pattern}"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=False,
                score=0.0,
                message=f"Data type validation error: {e}"
            )
    
    def _validate_semantic_rule(self, element_info: ElementInfo, rule: Any) -> ValidationResult:
        """Validate using semantic patterns."""
        try:
            content = element_info.text_content.strip().lower()
            
            if rule.pattern == "team_name":
                if self._is_team_name(content):
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=True,
                        score=rule.weight,
                        message="Content appears to be a team name"
                    )
                else:
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=False,
                        score=0.0,
                        message="Content does not appear to be a team name"
                    )
            elif rule.pattern == "score":
                if self._is_score(content):
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=True,
                        score=rule.weight,
                        message="Content appears to be a score"
                    )
                else:
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=False,
                        score=0.0,
                        message="Content does not appear to be a score"
                    )
            elif rule.pattern == "time":
                if self._is_time(content):
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=True,
                        score=rule.weight,
                        message="Content appears to be a time"
                    )
                else:
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=False,
                        score=0.0,
                        message="Content does not appear to be a time"
                    )
            elif rule.pattern == "date":
                if self._is_date(content):
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=True,
                        score=rule.weight,
                        message="Content appears to be a date"
                    )
                else:
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=False,
                        score=0.0,
                        message="Content does not appear to be a date"
                    )
            elif rule.pattern == "odds":
                if self._is_odds(content):
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=True,
                        score=rule.weight,
                        message="Content appears to be odds"
                    )
                else:
                    return ValidationResult(
                        rule_type=ValidationType.SEMANTIC.value,
                        passed=False,
                        score=0.0,
                        message="Content does not appear to be odds"
                    )
            else:
                return ValidationResult(
                    rule_type=ValidationType.SEMANTIC.value,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported semantic pattern: {rule.pattern}"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message=f"Semantic validation error: {e}"
            )
    
    def _validate_custom_rule(self, element_info: ElementInfo, rule: Any) -> ValidationResult:
        """Validate using custom rule logic."""
        try:
            # Custom validation logic would be implemented here
            # For now, return a basic validation
            if hasattr(rule, 'validator') and callable(rule.validator):
                try:
                    result = rule.validator(element_info, rule)
                    if isinstance(result, ValidationResult):
                        return result
                    else:
                        return ValidationResult(
                            rule_type=ValidationType.CUSTOM.value,
                            passed=bool(result),
                            score=rule.weight if result else 0.0,
                            message="Custom validation completed"
                        )
                except Exception as e:
                    return ValidationResult(
                        rule_type=ValidationType.CUSTOM.value,
                        passed=False,
                        score=0.0,
                        message=f"Custom validator error: {e}"
                    )
            else:
                return ValidationResult(
                    rule_type=ValidationType.CUSTOM.value,
                    passed=False,
                    score=0.0,
                    message="No custom validator provided"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_type=ValidationType.CUSTOM.value,
                passed=False,
                score=0.0,
                message=f"Custom validation error: {e}"
            )
    
    def _assess_basic_content_quality(self, element_info: ElementInfo) -> float:
        """Assess basic content quality without validation rules."""
        try:
            content = element_info.text_content.strip()
            
            if not content:
                return 0.0
            
            quality_score = 0.5  # Base score
            
            # Length assessment
            if len(content) >= 3:
                quality_score += 0.1
            if len(content) >= 10:
                quality_score += 0.1
            
            # Character variety assessment
            has_letters = any(c.isalpha() for c in content)
            has_numbers = any(c.isdigit() for c in content)
            has_spaces = ' ' in content
            
            if has_letters and (has_numbers or has_spaces):
                quality_score += 0.1
            
            # No special characters penalty
            if not any(c in content for c in '!@#$%^&*()_+-=[]{}|;:"<>,.?/~`'):
                quality_score += 0.1
            
            # No excessive whitespace
            if not content.count('  ') > 2:
                quality_score += 0.1
            
            return min(1.0, quality_score)
            
        except Exception:
            return 0.5
    
    def _assess_content_quality(self, element_info: ElementInfo) -> float:
        """Assess content quality with various factors."""
        try:
            content = element_info.text_content.strip()
            
            if not content:
                return 0.0
            
            quality_score = 0.5  # Base score
            
            # Text quality factors
            quality_score += self._assess_text_structure(content)
            quality_score += self._assess_text_meaning(content)
            quality_score += self._assess_text_formatting(content)
            
            return min(1.0, quality_score)
            
        except Exception:
            return 0.5
    
    def _assess_text_structure(self, content: str) -> float:
        """Assess text structure quality."""
        score = 0.0
        
        # Proper capitalization
        if content and content[0].isupper():
            score += 0.05
        
        # No leading/trailing whitespace
        if content == content.strip():
            score += 0.05
        
        # No excessive consecutive spaces
        if '  ' not in content:
            score += 0.05
        
        # No excessive special characters
        special_chars = '!@#$%^&*()_+-=[]{}|;:"<>,.?/~`'
        special_count = sum(1 for c in content if c in special_chars)
        if special_count <= 2:
            score += 0.05
        
        return score
    
    def _assess_text_meaning(self, content: str) -> float:
        """Assess text meaning and relevance."""
        score = 0.0
        
        # Common meaningful words
        meaningful_words = {
            'team', 'player', 'score', 'goal', 'match', 'game', 'win', 'lose',
            'home', 'away', 'vs', 'time', 'date', 'name', 'number', 'result'
        }
        
        words = content.lower().split()
        meaningful_count = sum(1 for word in words if word in meaningful_words)
        
        if meaningful_count > 0:
            score += min(0.2, meaningful_count * 0.05)
        
        # Not just numbers or special characters
        if any(c.isalpha() for c in content):
            score += 0.1
        
        return score
    
    def _assess_text_formatting(self, content: str) -> float:
        """Assess text formatting."""
        score = 0.0
        
        # Proper punctuation at end
        if content and content[-1] in '.!?':
            score += 0.05
        
        # Balanced parentheses/brackets
        if content.count('(') == content.count(')'):
            score += 0.05
        if content.count('[') == content.count(']'):
            score += 0.05
        
        return score
    
    def _is_team_name(self, content: str) -> bool:
        """Check if content appears to be a team name."""
        # Basic team name patterns
        if len(content) < 2 or len(content) > 50:
            return False
        
        # Should contain letters and possibly spaces/hyphens
        if not re.match(r'^[a-zA-Z\s\-]+$', content):
            return False
        
        # Should not be just numbers or special characters
        if content.isdigit() or not any(c.isalpha() for c in content):
            return False
        
        return True
    
    def _is_score(self, content: str) -> bool:
        """Check if content appears to be a score."""
        # Common score patterns
        return bool(re.match(r'^\d+$', content))
    
    def _is_time(self, content: str) -> bool:
        """Check if content appears to be a time."""
        # Time patterns: HH:MM, H:MM AM/PM, etc.
        time_patterns = [
            r'^\d{1,2}:\d{2}$',
            r'^\d{1,2}:\d{2}\s*(AM|PM)$',
            r'^\d{1,2}:\d{2}:\d{2}$'
        ]
        
        return any(re.match(pattern, content) for pattern in time_patterns)
    
    def _is_date(self, content: str) -> bool:
        """Check if content appears to be a date."""
        # Date patterns: YYYY-MM-DD, MM/DD/YYYY, etc.
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{1,2}/\d{1,2}/\d{4}$',
            r'^\d{1,2}-\d{1,2}-\d{4}$'
        ]
        
        return any(re.match(pattern, content) for pattern in date_patterns)
    
    def _is_odds(self, content: str) -> bool:
        """Check if content appears to be betting odds."""
        # Odds patterns: decimal (2.50), fractional (5/2), etc.
        odds_patterns = [
            r'^\d+\.\d+$',
            r'^\d+/\d+$'
        ]
        
        return any(re.match(pattern, content) for pattern in odds_patterns)
    
    def _determine_confidence_level(self, confidence: float) -> str:
        """Determine confidence level based on score."""
        if confidence >= 0.95:
            return "perfect"
        elif confidence >= 0.85:
            return "high"
        elif confidence >= 0.70:
            return "medium"
        elif confidence >= 0.50:
            return "low"
        else:
            return "failed"
    
    def _get_strategy_success_rate(self, strategy: str) -> float:
        """Get historical success rate for a strategy."""
        if strategy not in self._strategy_metrics:
            return 0.5  # Default to 50% for unknown strategies
        
        metrics = self._strategy_metrics[strategy]
        if metrics.total_attempts == 0:
            return 0.5
        
        return metrics.successful_attempts / metrics.total_attempts
    
    def _get_performance_rating(self, resolution_time: float) -> str:
        """Get performance rating based on resolution time."""
        if resolution_time < 100:
            return "excellent"
        elif resolution_time < 500:
            return "good"
        elif resolution_time < 1000:
            return "fair"
        elif resolution_time < 2000:
            return "poor"
        else:
            return "very_poor"


# Global confidence scorer instance
confidence_scorer = ConfidenceScorer()


def get_confidence_scorer() -> ConfidenceScorer:
    """Get global confidence scorer instance."""
    return confidence_scorer
