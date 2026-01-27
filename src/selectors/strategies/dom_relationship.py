"""
DOM relationship strategy implementation for Selector Engine.

Implements element location based on DOM relationships (parent, child, sibling, etc.)
as specified in the strategy pattern interface.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.selector_models import (
    StrategyType, SelectorResult, ElementInfo, ValidationResult,
    ValidationRule, ValidationType, SemanticSelector
)
from src.selectors.context import DOMContext
from src.selectors.strategies.base import BaseStrategyPattern
from src.utils.exceptions import StrategyExecutionError


class DOMRelationshipStrategy(BaseStrategyPattern):
    """Strategy for finding elements based on DOM relationships."""
    
    def __init__(self, strategy_id: str, priority: int = 1, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DOM relationship strategy.
        
        Args:
            strategy_id: Unique identifier for this strategy
            priority: Priority order (lower = higher priority)
            config: Strategy configuration dictionary
        """
        super().__init__(strategy_id, StrategyType.DOM_RELATIONSHIP, priority)
        
        # Store configuration
        self._config = config or {}
        
        # Validate configuration
        issues = self.validate_config(self._config)
        if issues:
            raise ValueError(f"Invalid DOM relationship strategy configuration: {issues}")
    
    async def attempt_resolution(self, selector: SemanticSelector, context: DOMContext) -> SelectorResult:
        """
        Attempt to resolve selector using DOM relationship strategy.
        
        Args:
            selector: Semantic selector definition
            context: DOM context for resolution
            
        Returns:
            SelectorResult with resolution outcome
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract configuration
            parent_selector = self._config.get("parent_selector", "")
            relationship_type = self._config.get("relationship_type", "child")
            child_index = self._config.get("child_index", 0)
            element_tag = self._config.get("element_tag", "")
            
            # Validate required configuration
            if not parent_selector.strip():
                return self._create_failure_result(
                    selector.name, "parent_selector not configured", 
                    datetime.utcnow() - start_time
                )
            
            if not relationship_type.strip():
                return self._create_failure_result(
                    selector.name, "relationship_type not configured",
                    datetime.utcnow() - start_time
                )
            
            # Find element using DOM relationship
            element = await self._find_element_by_dom_relationship(
                context, parent_selector, relationship_type, child_index, element_tag
            )
            
            if not element:
                return self._create_failure_result(
                    selector.name, f"No element found with {relationship_type} relationship to '{parent_selector}'",
                    datetime.utcnow() - start_time
                )
            
            # Extract element information
            element_info = await self._extract_element_info(element)
            
            # Calculate confidence
            validation_results = await self._validate_element_content(element_info, selector.validation_rules)
            base_confidence = self._calculate_base_confidence(element_info, validation_results)
            
            # Apply relationship-specific confidence adjustments
            confidence = self._apply_relationship_confidence_adjustments(
                base_confidence, element_info, relationship_type
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
        """Validate DOM relationship strategy configuration."""
        issues = []
        
        # Check required fields
        if "parent_selector" not in config:
            issues.append("parent_selector is required for DOM relationship strategy")
        elif not config["parent_selector"].strip():
            issues.append("parent_selector cannot be empty")
        
        if "relationship_type" not in config:
            issues.append("relationship_type is required for DOM relationship strategy")
        
        # Validate relationship type
        valid_relationships = ["child", "descendant", "sibling", "parent", "ancestor"]
        if config["relationship_type"] not in valid_relationships:
            issues.append(f"relationship_type must be one of: {valid_relationships}")
        
        # Validate child_index for child relationship
        if config["relationship_type"] == "child" and "child_index" in config:
            try:
                child_index = int(config["child_index"])
                if child_index < 0:
                    issues.append("child_index must be >= 0")
            except (ValueError, TypeError):
                issues.append("child_index must be a non-negative integer")
        
        # Validate optional fields
        if "element_tag" in config and config["element_tag"] and not config["element_tag"].strip():
            issues.append("element_tag cannot be empty if specified")
        
        return issues
    
    async def _find_element_by_dom_relationship(self, context: DOMContext,
                                                parent_selector: str,
                                                relationship_type: str,
                                                child_index: int = 0,
                                                element_tag: Optional[str] = None) -> Optional[Any]:
        """Find element by DOM relationship."""
        try:
            # Find parent/anchor element
            parent = await context.page.query_selector(parent_selector)
            if not parent:
                return None
            
            # Find element based on relationship type
            if relationship_type == "child":
                return await self._find_child_element(parent, child_index, element_tag)
            elif relationship_type == "descendant":
                return await self._find_descendant_element(parent, element_tag)
            elif relationship_type == "sibling":
                return await self._find_sibling_element(parent, element_tag)
            elif relationship_type == "parent":
                return await self._find_parent_element(parent, element_tag)
            elif relationship_type == "ancestor":
                return await self._find_ancestor_element(parent, element_tag)
            else:
                return None
                
        except Exception as e:
            self._logger.error(
                "dom_relationship_search_failed",
                strategy_id=self._strategy_id,
                parent_selector=parent_selector,
                relationship_type=relationship_type,
                child_index=child_index,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    async def _find_child_element(self, parent: Any, child_index: int, element_tag: Optional[str] = None) -> Optional[Any]:
        """Find child element by index."""
        try:
            # Get direct children
            children = await parent.query_selector_all(f"> {element_tag if element_tag else '*'}")
            
            if child_index < len(children):
                element = children[child_index]
                if await self._validate_element_found(element):
                    return element
            
            return None
            
        except Exception as e:
            self._logger.error(
                "child_element_search_failed",
                strategy_id=self._strategy_id,
                child_index=child_index,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    async def _find_descendant_element(self, parent: Any, element_tag: Optional[str] = None) -> Optional[Any]:
        """Find descendant element by tag."""
        try:
            # Get all descendants
            if element_tag:
                descendants = await parent.query_selector_all(element_tag)
            else:
                descendants = await parent.query_selector_all("*")
            
            # Return the first valid descendant
            for descendant in descendants:
                if await self._validate_element_found(descendant):
                    return descendant
            
            return None
            
        except Exception as e:
            self._logger.error(
                "descendant_element_search_failed",
                strategy_id=self._strategy_id,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    async def _find_sibling_element(self, parent: Any, element_tag: Optional[str] = None) -> Optional[Any]:
        """Find sibling element."""
        try:
            # Get parent of the given element
            grandparent = await parent.evaluate("el => el.parentElement")
            if not grandparent:
                return None
            
            # Get siblings (children of grandparent)
            if element_tag:
                siblings = await grandparent.query_selector_all(f"> {element_tag}")
            else:
                siblings = await grandparent.query_selector_all("> *")
            
            # Find siblings that are not the original element
            for sibling in siblings:
                if await sibling.evaluate("el => el !== arguments[0]", parent):
                    if await self._validate_element_found(sibling):
                        return sibling
            
            return None
            
        except Exception as e:
            self._logger.error(
                "sibling_element_search_failed",
                strategy_id=self._strategy_id,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    async def _find_parent_element(self, child: Any, element_tag: Optional[str] = None) -> Optional[Any]:
        """Find parent element."""
        try:
            # Get parent
            parent = await child.evaluate("el => el.parentElement")
            if not parent:
                return None
            
            # Check if parent matches tag requirement
            if element_tag:
                tag_matches = await parent.evaluate(f"el => el.tagName.toLowerCase() === '{element_tag}'")
                if not tag_matches:
                    return None
            
            if await self._validate_element_found(parent):
                return parent
            
            return None
            
        except Exception as e:
            self._logger.error(
                "parent_element_search_failed",
                strategy_id=self._strategy_id,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    async def _find_ancestor_element(self, child: Any, element_tag: Optional[str] = None) -> Optional[Any]:
        """Find ancestor element."""
        try:
            # Walk up the DOM tree
            current = child
            max_depth = 10  # Prevent infinite loops
            
            for _ in range(max_depth):
                current = await current.evaluate("el => el.parentElement")
                if not current:
                    break
                
                # Check if this ancestor matches tag requirement
                if element_tag:
                    tag_matches = await current.evaluate(f"el => el.tagName.toLowerCase() === '{element_tag}'")
                    if tag_matches and await self._validate_element_found(current):
                        return current
                elif await self._validate_element_found(current):
                    return current
            
            return None
            
        except Exception as e:
            self._logger.error(
                "ancestor_element_search_failed",
                strategy_id=self._strategy_id,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
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
            import re
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
                import re
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
                import re
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
    
    def _apply_relationship_confidence_adjustments(self, base_confidence: float, element_info: ElementInfo,
                                                   relationship_type: str) -> float:
        """Apply relationship-specific confidence adjustments."""
        confidence = base_confidence
        
        # Boost confidence for direct relationships
        if relationship_type in ["child", "parent"]:
            confidence *= 1.1
        elif relationship_type in ["sibling"]:
            confidence *= 1.05
        elif relationship_type in ["descendant", "ancestor"]:
            confidence *= 1.02
        
        # Boost confidence for appropriate element tags based on relationship
        relationship_tags = {
            "child": ["span", "div", "p", "li", "td", "th"],
            "parent": ["div", "section", "article", "ul", "ol", "table"],
            "sibling": ["span", "div", "li", "td", "th"],
            "descendant": ["span", "div", "p", "a", "img"],
            "ancestor": ["div", "section", "article", "body", "html"]
        }
        
        if relationship_type in relationship_tags and element_info.tag_name in relationship_tags[relationship_type]:
            confidence *= 1.05
        elif relationship_type in relationship_tags:
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
