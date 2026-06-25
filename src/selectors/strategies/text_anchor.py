"""
Text anchor strategy implementation for Selector Engine.

Implements text-based element location using anchor text and proximity selectors
as specified in the strategy pattern interface.
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


class TextAnchorStrategy(BaseStrategyPattern):
    """Strategy for finding elements based on text anchor and proximity."""
    
    def __init__(self, strategy_id: str, priority: int = 1, config: Optional[Dict[str, Any]] = None):
        """
        Initialize text anchor strategy.
        
        Args:
            strategy_id: Unique identifier for this strategy
            priority: Priority order (lower = higher priority)
            config: Strategy configuration dictionary
        """
        super().__init__(strategy_id, StrategyType.TEXT_ANCHOR, priority)
        
        # Store configuration
        self._config = config or {}
        
        # Validate configuration
        issues = self.validate_config(self._config)
        if issues:
            raise ValueError(f"Invalid text anchor strategy configuration: {issues}")
    
    async def attempt_resolution(self, selector: SemanticSelector, context: DOMContext) -> SelectorResult:
        """
        Attempt to resolve selector using text anchor strategy.
        
        Args:
            selector: Semantic selector definition
            context: DOM context for resolution
            
        Returns:
            SelectorResult with resolution outcome
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract configuration
            anchor_text = self._config.get("anchor_text", "")
            proximity_selector = self._config.get("proximity_selector", "")
            case_sensitive = self._config.get("case_sensitive", False)
            
            # Validate required configuration
            if not anchor_text.strip():
                return self._create_failure_result(
                    selector.name, "anchor_text not configured", 
                    datetime.utcnow() - start_time
                )
            
            # Find element using text anchor
            element = await self._find_element_by_text_anchor(
                context, anchor_text, proximity_selector, case_sensitive
            )
            
            if not element:
                return self._create_failure_result(
                    selector.name, f"Anchor text '{anchor_text}' not found",
                    datetime.utcnow() - start_time
                )
            
            # Extract element information
            element_info = await self._extract_element_info(element)
            
            # Calculate confidence
            validation_results = await self._validate_element_content(element_info, selector.validation_rules)
            base_confidence = self._calculate_base_confidence(element_info, validation_results)
            
            # Apply text-specific confidence adjustments
            confidence = self._apply_text_confidence_adjustments(
                base_confidence, element_info, anchor_text, case_sensitive
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
        """Validate text anchor strategy configuration."""
        issues = []
        
        # Check required fields
        if "anchor_text" not in config:
            issues.append("anchor_text is required for text anchor strategy")
        elif not config["anchor_text"].strip():
            issues.append("anchor_text cannot be empty")
        
        # Validate optional fields
        if "proximity_selector" in config and not config["proximity_selector"].strip():
            issues.append("proximity_selector cannot be empty if specified")
        
        if "case_sensitive" in config and not isinstance(config["case_sensitive"], bool):
            issues.append("case_sensitive must be a boolean")
        
        # Validate max_distance if specified
        if "max_distance" in config:
            try:
                max_distance = int(config["max_distance"])
                if max_distance < 0:
                    issues.append("max_distance must be >= 0")
            except (ValueError, TypeError):
                issues.append("max_distance must be a non-negative integer")
        
        return issues
    
    async def _find_element_by_text_anchor(self, context: DOMContext, 
                                           anchor_text: str,
                                           proximity_selector: Optional[str] = None,
                                           case_sensitive: bool = False) -> Optional[Any]:
        """Find element by text anchor with optional proximity selector."""
        try:
            # Search for anchor text in the page
            page_content = await context.page.content()
            
            # Prepare search text
            search_text = anchor_text if case_sensitive else anchor_text.lower()
            
            # Find all elements containing the anchor text
            elements = await context.page.query_selector_all("*")
            
            best_element = None
            best_score = 0.0
            
            for element in elements:
                try:
                    # Get element text content
                    element_text = await element.evaluate("el => el.textContent || ''")
                    search_content = element_text if case_sensitive else element_text.lower()
                    
                    # Check if anchor text is present
                    if search_text in search_content:
                        # Calculate match score based on text similarity
                        match_score = self._calculate_text_similarity(search_text, anchor_text, case_sensitive)
                        
                        # Apply proximity selector if specified
                        if proximity_selector:
                            if await self._matches_proximity_selector(element, proximity_selector, context):
                                match_score *= 1.2  # Boost score for proximity match
                            else:
                                continue  # Skip if doesn't match proximity
                        
                        # Update best match
                        if match_score > best_score:
                            best_score = match_score
                            best_element = element
                
                except Exception:
                    continue  # Skip elements that can't be evaluated
            
            return best_element
            
        except Exception as e:
            self._logger.error(
                "text_anchor_search_failed",
                strategy_id=self._strategy_id,
                anchor_text=anchor_text,
                proximity_selector=proximity_selector,
                error=str(e)
            )
            return None
    
    def _calculate_text_similarity(self, element_text: str, anchor_text: str, case_sensitive: bool) -> float:
        """Calculate similarity score between element text and anchor text."""
        if not case_sensitive:
            element_text = element_text.lower()
            anchor_text = anchor_text.lower()
        
        # Exact match gets highest score
        if element_text == anchor_text:
            return 1.0
        
        # Contains match gets good score
        if anchor_text in element_text:
            # Score based on how close the match is
            start_pos = element_text.find(anchor_text)
            length_ratio = len(anchor_text) / len(element_text)
            position_ratio = 1.0 - (start_pos / len(element_text))
            
            return (length_ratio * 0.6) + (position_ratio * 0.4)
        
        # Partial match gets lower score
        words_element = element_text.split()
        words_anchor = anchor_text.split()
        
        common_words = set(words_element) & set(words_anchor)
        if common_words:
            return len(common_words) / max(len(words_element), len(words_anchor))
        
        return 0.0
    
    async def _matches_proximity_selector(self, element: Any, proximity_selector: str, context: DOMContext) -> bool:
        """Check if element matches proximity selector criteria."""
        try:
            # Check if element itself matches
            if await element.evaluate(f"el => el.matches('{proximity_selector}')"):
                return True
            
            # Check if element is near an element that matches
            parent = await element.evaluate("el => el.parentElement")
            if parent:
                if await parent.evaluate(f"el => el.matches('{proximity_selector}')"):
                    return True
            
            # Check siblings
            siblings = await element.evaluate("el => Array.from(el.parentElement?.children || [])")
            for sibling in siblings:
                if await sibling.evaluate(f"el => el.matches('{proximity_selector}')"):
                    return True
            
            return False
            
        except Exception:
            return False
    
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
    
    def _apply_text_confidence_adjustments(self, base_confidence: float, element_info: ElementInfo,
                                        anchor_text: str, case_sensitive: bool) -> float:
        """Apply text-specific confidence adjustments."""
        confidence = base_confidence
        
        # Boost confidence for exact text matches
        if element_info.text_content.strip() == anchor_text:
            confidence *= 1.1
        elif element_info.text_content.strip().lower() == anchor_text.lower():
            confidence *= 1.05
        
        # Penalize for case sensitivity mismatches
        if not case_sensitive and element_info.text_content != anchor_text:
            confidence *= 0.95
        
        # Boost confidence for appropriate element tags
        text_tags = ['span', 'div', 'p', 'h1', 'h2', 'h3', 'td', 'th']
        if element_info.tag_name in text_tags:
            confidence *= 1.05
        else:
            confidence *= 0.9
        
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
