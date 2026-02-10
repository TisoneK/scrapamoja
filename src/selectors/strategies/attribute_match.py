"""
Attribute match strategy implementation for Selector Engine.

Implements element location based on attribute matching with support for
regex patterns and element tag filtering as specified in the strategy pattern interface.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.selector_models import (
    StrategyType, SelectorResult, ElementInfo, ValidationResult,
    ValidationRule, ValidationType, SemanticSelector
)
from src.selectors.context import DOMContext
from src.selectors.strategies.base import BaseStrategyPattern
from src.utils.exceptions import StrategyExecutionError


class AttributeMatchStrategy(BaseStrategyPattern):
    """Strategy for finding elements based on attribute matching."""
    
    def __init__(self, strategy_id: str, priority: int = 1, config: Optional[Dict[str, Any]] = None):
        """
        Initialize attribute match strategy.
        
        Args:
            strategy_id: Unique identifier for this strategy
            priority: Priority order (lower = higher priority)
            config: Strategy configuration dictionary
        """
        super().__init__(strategy_id, StrategyType.ATTRIBUTE_MATCH, priority)
        
        # Store configuration
        self._config = config or {}
        
        # Validate configuration
        issues = self.validate_config(self._config)
        if issues:
            raise ValueError(f"Invalid attribute match strategy configuration: {issues}")
    
    async def attempt_resolution(self, selector: SemanticSelector, context: DOMContext) -> SelectorResult:
        """
        Attempt to resolve selector using attribute match strategy.
        
        Args:
            selector: Semantic selector definition
            context: DOM context for resolution
            
        Returns:
            SelectorResult with resolution outcome
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract configuration
            attribute = self._config.get("attribute", "")
            value_pattern = self._config.get("value_pattern", "")
            element_tag = self._config.get("element_tag", "")
            case_sensitive = self._config.get("case_sensitive", False)
            
            # Validate required configuration
            if not attribute.strip():
                return self._create_failure_result(
                    selector.name, "attribute not configured", 
                    datetime.utcnow() - start_time
                )
            
            if not value_pattern.strip():
                return self._create_failure_result(
                    selector.name, "value_pattern not configured",
                    datetime.utcnow() - start_time
                )
            
            # Find element using attribute matching
            element = await self._find_element_by_attribute(
                context, attribute, value_pattern, element_tag, case_sensitive
            )
            
            if not element:
                return self._create_failure_result(
                    selector.name, f"No element found with {attribute}='{value_pattern}'",
                    datetime.utcnow() - start_time
                )
            
            # Extract element information
            element_info = await self._extract_element_info(element)
            
            # Calculate confidence
            validation_results = await self._validate_element_content(element_info, selector.validation_rules)
            base_confidence = self._calculate_base_confidence(element_info, validation_results)
            
            # Apply attribute-specific confidence adjustments
            confidence = self._apply_attribute_confidence_adjustments(
                base_confidence, element_info, attribute, value_pattern
            )
            
            # Apply performance penalty
            resolution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            final_confidence = self._apply_strategy_performance_penalty(confidence, resolution_time)
            
            # Create success result
            result = SelectorResult(
                selector_name=selector.name,
                strategy_used=self._strategy_id,
                element_info=element_info,
                confidence_score=final_confidence,
                resolution_time=resolution_time,
                validation_results=validation_results,
                success=True,
                timestamp=datetime.utcnow()
            )
            
            # Update metrics
            self.update_metrics(True, resolution_time)
            self._log_resolution_attempt(selector.name, True, resolution_time, final_confidence)
            
            return result
            
        except Exception as e:
            resolution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update metrics
            self.update_metrics(False, resolution_time)
            self._log_resolution_attempt(selector.name, False, resolution_time, 0.0, str(e))
            
            # Create failure result
            return self._create_failure_result(
                selector.name, f"Strategy execution failed: {e}",
                resolution_time
            )
    
    def _validate_strategy_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate attribute match strategy configuration."""
        issues = []
        
        # Check required fields
        if "attribute" not in config:
            issues.append("attribute is required for attribute match strategy")
        elif not config["attribute"].strip():
            issues.append("attribute cannot be empty")
        
        if "value_pattern" not in config:
            issues.append("value_pattern is required for attribute match strategy")
        elif not config["value_pattern"].strip():
            issues.append("value_pattern cannot be empty")
        
        # Validate optional fields
        if "element_tag" in config and config["element_tag"] and not config["element_tag"].strip():
            issues.append("element_tag cannot be empty if specified")
        
        if "case_sensitive" in config and not isinstance(config["case_sensitive"], bool):
            issues.append("case_sensitive must be a boolean")
        
        # Validate regex pattern if specified
        if "use_regex" in config and config["use_regex"]:
            try:
                re.compile(config["value_pattern"])
            except re.error as e:
                issues.append(f"Invalid regex pattern: {e}")
        
        return issues
    
    async def _find_element_by_attribute(self, context: DOMContext,
                                         attribute: str,
                                         value_pattern: str,
                                         element_tag: Optional[str] = None,
                                         case_sensitive: bool = False) -> Optional[Any]:
        """Find element by attribute matching."""
        try:
            # Build CSS selector
            if element_tag:
                base_selector = f"{element_tag}"
            else:
                base_selector = "*"
            
            # Find all elements with the specified attribute
            elements = await context.page.query_selector_all(f"{base_selector}[{attribute}]")
            
            best_element = None
            best_score = 0.0
            
            use_regex = self._config.get("use_regex", False)
            
            for element in elements:
                try:
                    # Get attribute value
                    attr_value = await element.get_attribute(attribute)
                    if attr_value is None:
                        continue
                    
                    # Check if attribute value matches pattern
                    match_score = self._calculate_attribute_match_score(
                        attr_value, value_pattern, case_sensitive, use_regex
                    )
                    
                    if match_score > 0:
                        # Validate element is usable
                        if await self._validate_element_found(element):
                            # Update best match
                            if match_score > best_score:
                                best_score = match_score
                                best_element = element
                
                except Exception:
                    continue  # Skip elements that can't be evaluated
            
            return best_element
            
        except Exception as e:
            self._logger.error(
                "attribute_match_search_failed",
                strategy_id=self._strategy_id,
                attribute=attribute,
                value_pattern=value_pattern,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    def _calculate_attribute_match_score(self, attr_value: str, value_pattern: str,
                                        case_sensitive: bool, use_regex: bool) -> float:
        """Calculate match score between attribute value and pattern."""
        if not case_sensitive:
            attr_value = attr_value.lower()
            value_pattern = value_pattern.lower()
        
        if use_regex:
            try:
                pattern = re.compile(value_pattern)
                if pattern.fullmatch(attr_value):
                    return 1.0
                elif pattern.search(attr_value):
                    # Partial match gets lower score
                    return 0.7
                else:
                    return 0.0
            except re.error:
                # Fallback to string matching if regex is invalid
                use_regex = False
        
        if not use_regex:
            # Exact match gets highest score
            if attr_value == value_pattern:
                return 1.0
            
            # Contains match gets good score
            if value_pattern in attr_value:
                # Score based on how close the match is
                start_pos = attr_value.find(value_pattern)
                length_ratio = len(value_pattern) / len(attr_value)
                position_ratio = 1.0 - (start_pos / len(attr_value))
                
                return (length_ratio * 0.6) + (position_ratio * 0.4)
            
            # Word boundary match
            words_attr = attr_value.split()
            words_pattern = value_pattern.split()
            
            common_words = set(words_attr) & set(words_pattern)
            if common_words:
                return len(common_words) / max(len(words_attr), len(words_pattern))
        
        return 0.0
    
    async def _validate_element_content(self, element_info: ElementInfo, 
                                       validation_rules: List[ValidationRule]) -> List[ValidationResult]:
        """Validate element content against rules."""
        results = []
        
        for rule in validation_rules:
            try:
                if rule.type == ValidationType.REGEX:
                    result = self._validate_regex_rule(element_info, rule)
                elif rule.type == ValidationType.DATA_TYPE:
                    result = self._validate_data_type_rule(element_info, rule)
                elif rule.type == ValidationType.SEMANTIC:
                    result = self._validate_semantic_rule(element_info, rule)
                else:
                    result = ValidationResult(
                        rule_type=rule.type.value,
                        passed=False,
                        score=0.0,
                        message=f"Unsupported validation type: {rule.type}"
                    )
                
                results.append(result)
                
            except Exception as e:
                results.append(ValidationResult(
                    rule_type=rule.type.value,
                    passed=False,
                    score=0.0,
                    message=f"Validation error: {e}"
                ))
        
        return results
    
    def _validate_regex_rule(self, element_info: ElementInfo, rule: ValidationRule) -> ValidationResult:
        """Validate element content using regex rule."""
        try:
            pattern = re.compile(rule.pattern)
            match = pattern.fullmatch(element_info.text_content.strip())
            
            if match:
                return ValidationResult(
                    rule_type=rule.type.value,
                    passed=True,
                    score=rule.weight,
                    message="Text matches regex pattern"
                )
            else:
                return ValidationResult(
                    rule_type=rule.type.value,
                    passed=False,
                    score=0.0,
                    message="Text does not match regex pattern"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_type=rule.type.value,
                passed=False,
                score=0.0,
                message=f"Regex validation error: {e}"
            )
    
    def _validate_data_type_rule(self, element_info: ElementInfo, rule: ValidationRule) -> ValidationResult:
        """Validate element content using data type rule."""
        try:
            content = element_info.text_content.strip()
            
            if rule.pattern == "float":
                try:
                    float(content)
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=True,
                        score=rule.weight,
                        message="Content is a valid float"
                    )
                except ValueError:
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=False,
                        score=0.0,
                        message="Content is not a valid float"
                    )
            elif rule.pattern == "int":
                try:
                    int(content)
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=True,
                        score=rule.weight,
                        message="Content is a valid integer"
                    )
                except ValueError:
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=False,
                        score=0.0,
                        message="Content is not a valid integer"
                    )
            elif rule.pattern == "string":
                return ValidationResult(
                    rule_type=rule.type.value,
                    passed=True,
                    score=rule.weight,
                    message="Content is a valid string"
                )
            else:
                return ValidationResult(
                    rule_type=rule.type.value,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported data type: {rule.pattern}"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_type=rule.type.value,
                passed=False,
                score=0.0,
                message=f"Data type validation error: {e}"
            )
    
    def _validate_semantic_rule(self, element_info: ElementInfo, rule: ValidationRule) -> ValidationResult:
        """Validate element content using semantic rule."""
        try:
            content = element_info.text_content.strip().lower()
            
            if rule.pattern == "team_name":
                # Check if content looks like a team name
                if len(content) > 2 and re.match(r'^[a-zA-Z\s\-]+$', content):
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=True,
                        score=rule.weight,
                        message="Content appears to be a team name"
                    )
                else:
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=False,
                        score=0.0,
                        message="Content does not appear to be a team name"
                    )
            elif rule.pattern == "score":
                # Check if content looks like a score
                if re.match(r'^\d+$', content):
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=True,
                        score=rule.weight,
                        message="Content appears to be a score"
                    )
                else:
                    return ValidationResult(
                        rule_type=rule.type.value,
                        passed=False,
                        score=0.0,
                        message="Content does not appear to be a score"
                    )
            else:
                return ValidationResult(
                    rule_type=rule.type.value,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported semantic pattern: {rule.pattern}"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_type=rule.type.value,
                passed=False,
                score=0.0,
                message=f"Semantic validation error: {e}"
            )
    
    def _apply_attribute_confidence_adjustments(self, base_confidence: float, element_info: ElementInfo,
                                              attribute: str, value_pattern: str) -> float:
        """Apply attribute-specific confidence adjustments."""
        confidence = base_confidence
        
        # Boost confidence for exact attribute matches
        attr_value = element_info.get_attribute(attribute, "")
        if attr_value == value_pattern:
            confidence *= 1.1
        elif value_pattern in attr_value:
            confidence *= 1.05
        
        # Boost confidence for semantic attributes
        semantic_attributes = ['id', 'class', 'data-*', 'role', 'aria-*']
        if any(semantic_attr in attribute for semantic_attr in ['id', 'class', 'role']):
            confidence *= 1.05
        elif attribute.startswith('data-'):
            confidence *= 1.03
        
        # Boost confidence for appropriate element tags
        appropriate_tags = {
            'id': ['div', 'span', 'section', 'article', 'header', 'footer'],
            'class': ['div', 'span', 'section', 'article', 'p', 'h1', 'h2', 'h3'],
            'data-team': ['span', 'div', 'td', 'th'],
            'data-score': ['span', 'div', 'td', 'th'],
        }
        
        if attribute in appropriate_tags and element_info.tag_name in appropriate_tags[attribute]:
            confidence *= 1.05
        elif attribute in appropriate_tags:
            confidence *= 0.95
        
        # Ensure confidence stays within bounds
        return max(0.0, min(1.0, confidence))
    
    def _create_failure_result(self, selector_name: str, failure_reason: str, resolution_time: float) -> SelectorResult:
        """Create a failure result."""
        return SelectorResult(
            selector_name=selector_name,
            strategy_used=self._strategy_id,
            element_info=None,
            confidence_score=0.0,
            resolution_time=resolution_time,
            validation_results=[],
            success=False,
            timestamp=datetime.utcnow(),
            failure_reason=failure_reason
        )
