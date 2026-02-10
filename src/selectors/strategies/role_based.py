"""
Role-based strategy implementation for Selector Engine.

Implements element location based on ARIA roles and semantic attributes
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


class RoleBasedStrategy(BaseStrategyPattern):
    """Strategy for finding elements based on roles and semantic attributes."""
    
    def __init__(self, strategy_id: str, priority: int = 1, config: Optional[Dict[str, Any]] = None):
        """
        Initialize role-based strategy.
        
        Args:
            strategy_id: Unique identifier for this strategy
            priority: Priority order (lower = higher priority)
            config: Strategy configuration dictionary
        """
        super().__init__(strategy_id, StrategyType.ROLE_BASED, priority)
        
        # Store configuration
        self._config = config or {}
        
        # Validate configuration
        issues = self.validate_config(self._config)
        if issues:
            raise ValueError(f"Invalid role-based strategy configuration: {issues}")
    
    async def attempt_resolution(self, selector: SemanticSelector, context: DOMContext) -> SelectorResult:
        """
        Attempt to resolve selector using role-based strategy.
        
        Args:
            selector: Semantic selector definition
            context: DOM context for resolution
            
        Returns:
            SelectorResult with resolution outcome
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract configuration
            role = self._config.get("role", "")
            semantic_attribute = self._config.get("semantic_attribute", "")
            expected_value = self._config.get("expected_value", "")
            element_tag = self._config.get("element_tag", "")
            
            # Validate required configuration
            if not role.strip():
                return self._create_failure_result(
                    selector.name, "role not configured", 
                    datetime.utcnow() - start_time
                )
            
            # Find element using role-based matching
            element = await self._find_element_by_role(
                context, role, semantic_attribute, expected_value, element_tag
            )
            
            if not element:
                return self._create_failure_result(
                    selector.name, f"No element found with role='{role}'",
                    datetime.utcnow() - start_time
                )
            
            # Extract element information
            element_info = await self._extract_element_info(element)
            
            # Calculate confidence
            validation_results = await self._validate_element_content(element_info, selector.validation_rules)
            base_confidence = self._calculate_base_confidence(element_info, validation_results)
            
            # Apply role-specific confidence adjustments
            confidence = self._apply_role_confidence_adjustments(
                base_confidence, element_info, role, semantic_attribute, expected_value
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
        """Validate role-based strategy configuration."""
        issues = []
        
        # Check required fields
        if "role" not in config:
            issues.append("role is required for role-based strategy")
        elif not config["role"].strip():
            issues.append("role cannot be empty")
        
        # Validate optional fields
        if "semantic_attribute" in config and not config["semantic_attribute"].strip():
            issues.append("semantic_attribute cannot be empty if specified")
        
        if "expected_value" in config and not config["expected_value"].strip():
            issues.append("expected_value cannot be empty if specified")
        
        # Validate element_tag if specified
        if "element_tag" in config and config["element_tag"] and not config["element_tag"].strip():
            issues.append("element_tag cannot be empty if specified")
        
        # Validate role against common ARIA roles
        common_roles = [
            "button", "link", "navigation", "main", "header", "footer", "section",
            "article", "aside", "banner", "contentinfo", "search", "tablist",
            "tab", "tabpanel", "dialog", "alert", "status", "log", "marquee",
            "timer", "progressbar", "tooltip", "menu", "menubar", "menuitem",
            "listbox", "option", "tree", "treeitem", "grid", "row", "columnheader",
            "rowheader", "cell", "columnheader", "rowgroup", "list", "listitem",
            "table", "application", "document", "img", "heading", "group",
            "note", "presentation", "region", "rowgroup", "separator", "toolbar"
        ]
        
        if "role" in config and config["role"] not in common_roles:
            # Not an error, but worth noting
            self._logger.warning(
                "uncommon_role_detected",
                strategy_id=self._strategy_id,
                role=config["role"],
                common_roles=common_roles
            )
        
        return issues
    
    async def _find_element_by_role(self, context: DOMContext,
                                   role: str,
                                   semantic_attribute: Optional[str] = None,
                                   expected_value: Optional[str] = None,
                                   element_tag: Optional[str] = None) -> Optional[Any]:
        """Find element by role and optional semantic attribute."""
        try:
            # Build CSS selector for role-based search
            if semantic_attribute and expected_value:
                # Both role and semantic attribute specified
                role_selector = f"{element_tag if element_tag else '*'}[{semantic_attribute}='{expected_value}'][role='{role}']"
            elif semantic_attribute:
                # Only semantic attribute specified
                role_selector = f"{element_tag if element_tag else '*'}[{semantic_attribute}][role='{role}']"
            else:
                # Only role specified
                role_selector = f"{element_tag if element_tag else '*'}[role='{role}']"
            
            elements = await context.page.query_selector_all(role_selector)
            
            best_element = None
            best_score = 0.0
            
            for element in elements:
                try:
                    # Validate element is usable
                    if not await self._validate_element_found(element):
                        continue
                    
                    # Calculate role match score
                    match_score = self._calculate_role_match_score(
                        element, role, semantic_attribute, expected_value
                    )
                    
                    # Update best match
                    if match_score > best_score:
                        best_score = match_score
                        best_element = element
                
                except Exception:
                    continue  # Skip elements that can't be evaluated
            
            return best_element
            
        except Exception as e:
            self._logger.error(
                "role_based_search_failed",
                strategy_id=self._strategy_id,
                role=role,
                semantic_attribute=semantic_attribute,
                expected_value=expected_value,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    def _calculate_role_match_score(self, element: Any, role: str,
                                   semantic_attribute: Optional[str] = None,
                                   expected_value: Optional[str] = None) -> float:
        """Calculate match score for role-based search."""
        score = 0.0
        
        try:
            # Base score for having the correct role
            element_role = element.get_attribute("role")
            if element_role == role:
                score += 0.6
            elif element_role and role in element_role:
                score += 0.4
            
            # Additional score for semantic attribute match
            if semantic_attribute and expected_value:
                attr_value = element.get_attribute(semantic_attribute)
                if attr_value == expected_value:
                    score += 0.4
                elif attr_value and expected_value in attr_value:
                    score += 0.2
            
            # Bonus for accessibility attributes
            aria_label = element.get_attribute("aria-label")
            if aria_label:
                score += 0.1
            
            aria_describedby = element.get_attribute("aria-describedby")
            if aria_describedby:
                score += 0.05
            
            # Ensure score is within bounds
            return min(1.0, score)
            
        except Exception:
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
    
    def _apply_role_confidence_adjustments(self, base_confidence: float, element_info: ElementInfo,
                                         role: str, semantic_attribute: Optional[str] = None,
                                         expected_value: Optional[str] = None) -> float:
        """Apply role-specific confidence adjustments."""
        confidence = base_confidence
        
        # Boost confidence for standard ARIA roles
        standard_roles = [
            "button", "link", "navigation", "main", "header", "footer", "section",
            "article", "aside", "banner", "contentinfo", "search", "tablist"
        ]
        
        if role in standard_roles:
            confidence *= 1.1
        else:
            confidence *= 0.95  # Slightly penalize non-standard roles
        
        # Boost confidence for semantic attributes
        if semantic_attribute:
            semantic_attrs = ["data-team", "data-score", "data-player", "data-match"]
            if any(semantic_attr in semantic_attribute for semantic_attr in semantic_attrs):
                confidence *= 1.05
            elif semantic_attribute.startswith("data-"):
                confidence *= 1.03
        
        # Boost confidence for appropriate element tags
        role_tag_mapping = {
            "button": ["button", "input[type='button']", "a"],
            "link": ["a", "area"],
            "navigation": ["nav"],
            "main": ["main"],
            "header": ["header"],
            "footer": ["footer"],
            "section": ["section"],
            "article": ["article"],
            "aside": ["aside"],
            "banner": ["header"],
            "contentinfo": ["footer"],
            "search": ["form", "div"],
            "tablist": ["div", "ul"],
            "tab": ["button", "a", "div"],
            "dialog": ["div", "dialog"],
            "alert": ["div", "section"],
            "status": ["div", "p"],
            "list": ["ul", "ol"],
            "listitem": ["li"],
            "table": ["table"],
            "img": ["img"],
            "heading": ["h1", "h2", "h3", "h4", "h5", "h6"]
        }
        
        if role in role_tag_mapping and element_info.tag_name in role_tag_mapping[role]:
            confidence *= 1.05
        elif role in role_tag_mapping:
            confidence *= 0.95
        
        # Boost confidence for accessibility features
        if element_info.get_attribute("aria-label"):
            confidence *= 1.02
        if element_info.get_attribute("aria-describedby"):
            confidence *= 1.01
        if element_info.get_attribute("tabindex"):
            confidence *= 1.01
        
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
