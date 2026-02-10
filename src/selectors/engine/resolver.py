"""
Enhanced selector resolver with configuration system integration.

This module provides an enhanced resolver that integrates with the YAML
configuration system for semantic selector resolution with context awareness.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .registry import EnhancedSelectorRegistry
from ..models.selector_config import (
    SemanticSelector,
    StrategyDefinition,
    ResolutionContext,
    SelectorResult,
    ConfidenceConfig
)


class EnhancedSelectorResolver:
    """Enhanced selector resolver with configuration system integration."""
    
    def __init__(self, registry: EnhancedSelectorRegistry):
        """Initialize resolver with enhanced registry."""
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        self._correlation_counter = 0
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"resolver_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def resolve_selector(self, 
                             semantic_name: str, 
                             context: ResolutionContext,
                             dom_context: Optional[Any] = None) -> SelectorResult:
        """Resolve selector using configuration system."""
        correlation_id = self._generate_correlation_id()
        start_time = datetime.now()
        
        try:
            self.logger.debug(f"Resolving selector '{semantic_name}' in context '{context.current_page}.{context.current_section}' (correlation: {correlation_id})")
            
            # Get selector by name with context awareness
            selector = self.registry.get_selector_by_name(semantic_name, f"{context.current_page}.{context.current_section}")
            if not selector:
                # Try broader context
                selector = self.registry.get_selector_by_name(semantic_name, context.current_page)
            
            if not selector:
                raise ValueError(f"Selector '{semantic_name}' not found for context '{context.current_page}.{context.current_section}'")
            
            # Validate selector context
            full_context = f"{context.current_page}.{context.current_section}"
            if not self.registry.validate_selector_context(semantic_name, full_context):
                self.logger.warning(f"Selector '{semantic_name}' may not be appropriate for context '{full_context}'")
            
            # Resolve strategies with inheritance applied
            resolved_strategies = []
            confidence_scores = []
            
            for strategy in selector.strategies:
                try:
                    # Resolve strategy template if referenced
                    if hasattr(strategy, 'template') and strategy.template:
                        # This would resolve template from inheritance chain
                        # For now, use the strategy as-is
                        resolved_strategy = strategy
                    else:
                        resolved_strategy = strategy
                    
                    resolved_strategies.append(resolved_strategy)
                    
                    # Calculate confidence score (simplified implementation)
                    confidence = self._calculate_strategy_confidence(resolved_strategy, selector, context)
                    confidence_scores.append(confidence)
                    
                except Exception as e:
                    self.logger.warning(f"Error resolving strategy {strategy.type}: {e}")
                    continue
            
            if not resolved_strategies:
                raise ValueError(f"No valid strategies found for selector '{semantic_name}'")
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(confidence_scores, selector)
            
            # Determine which template was applied (if any)
            template_applied = None
            if selector.strategies and hasattr(selector.strategies[0], 'template'):
                template_applied = selector.strategies[0].template
            
            resolution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            result = SelectorResult(
                selector=selector,
                resolved_strategies=resolved_strategies,
                confidence_score=overall_confidence,
                resolution_time_ms=resolution_time_ms,
                context_used=full_context,
                template_applied=template_applied
            )
            
            self.logger.debug(f"Selector resolved: '{semantic_name}' with confidence {overall_confidence:.3f} in {resolution_time_ms:.1f}ms")
            
            return result
            
        except Exception as e:
            resolution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Failed to resolve selector '{semantic_name}': {e}")
            raise
    
    def get_available_selectors(self, context: str) -> List[str]:
        """Get all available selectors for a context."""
        return self.registry.get_available_selectors(context)
    
    def validate_selector_context(self, semantic_name: str, context: str) -> bool:
        """Validate that selector is appropriate for context."""
        return self.registry.validate_selector_context(semantic_name, context)
    
    def suggest_selectors(self, partial_name: str, context: Optional[str] = None, limit: int = 10) -> List[str]:
        """Suggest selector names based on partial match."""
        return self.registry.suggest_selectors(partial_name, context, limit)
    
    def _calculate_strategy_confidence(self, 
                                      strategy: StrategyDefinition, 
                                      selector: SemanticSelector,
                                      context: ResolutionContext) -> float:
        """Calculate confidence score for a strategy."""
        base_confidence = 0.5  # Base confidence
        
        # Strategy type confidence weights
        strategy_weights = {
            "text_anchor": 0.8,
            "attribute_match": 0.9,
            "css_selector": 0.7,
            "xpath": 0.6,
            "dom_relationship": 0.8,
            "role_based": 0.9
        }
        
        strategy_weight = strategy_weights.get(strategy.type, 0.5)
        
        # Context relevance boost
        context_boost = 0.0
        if selector.context and context.current_section:
            if selector.context == f"{context.current_page}.{context.current_section}":
                context_boost = 0.2
            elif selector.context == context.current_page:
                context_boost = 0.1
        
        # Priority adjustment (lower priority = higher confidence)
        priority_adjustment = max(0, (5 - strategy.priority) * 0.05)
        
        # Apply selector confidence configuration if available
        selector_confidence = 0.0
        if selector.confidence and selector.confidence.threshold is not None:
            selector_confidence = selector.confidence.threshold
        
        # Calculate final confidence
        confidence = base_confidence + strategy_weight + context_boost + priority_adjustment + selector_confidence
        confidence = min(1.0, max(0.0, confidence))  # Clamp between 0 and 1
        
        return confidence
    
    def _calculate_overall_confidence(self, 
                                    strategy_confidences: List[float],
                                    selector: SemanticSelector) -> float:
        """Calculate overall confidence from strategy confidences."""
        if not strategy_confidences:
            return 0.0
        
        # Use weighted average based on strategy priorities
        # Higher priority strategies (lower priority number) have more weight
        weights = []
        for i, confidence in enumerate(strategy_confidences):
            # Weight inversely proportional to priority (1/priority)
            weight = 1.0 / (i + 1)  # Simplified: earlier strategies have higher weight
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(strategy_confidences)] * len(strategy_confidences)
        
        # Calculate weighted average
        overall_confidence = sum(confidence * weight for confidence, weight in zip(strategy_confidences, weights))
        
        # Apply selector confidence threshold if available
        if selector.confidence and selector.confidence.threshold is not None:
            overall_confidence = max(overall_confidence, selector.confidence.threshold)
        
        return min(1.0, max(0.0, overall_confidence))
    
    async def resolve_multiple_selectors(self, 
                                       selector_names: List[str],
                                       context: ResolutionContext,
                                       dom_context: Optional[Any] = None) -> Dict[str, SelectorResult]:
        """Resolve multiple selectors in parallel."""
        if not selector_names:
            return {}
        
        # Create resolution tasks
        tasks = []
        for name in selector_names:
            task = self.resolve_selector(name, context, dom_context)
            tasks.append((name, task))
        
        # Execute tasks in parallel
        results = {}
        errors = {}
        
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (name, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                errors[name] = result
                self.logger.error(f"Failed to resolve selector '{name}': {result}")
            else:
                results[name] = result
        
        # Log summary
        self.logger.info(f"Resolved {len(results)}/{len(selector_names)} selectors successfully")
        if errors:
            self.logger.warning(f"Failed to resolve {len(errors)} selectors: {list(errors.keys())}")
        
        return results
    
    def get_resolver_stats(self) -> Dict[str, Any]:
        """Get resolver statistics."""
        return {
            "total_resolutions": self._correlation_counter,
            "registry_health": self.registry.get_registry_health(),
            "available_contexts": self.registry.get_available_contexts(),
            "total_selectors": len(self.registry.get_available_selectors()),
            "conflicts": len(self.registry.get_index_conflicts())
        }
    
    async def validate_resolution_capability(self, 
                                          selector_names: List[str],
                                          context: ResolutionContext) -> Dict[str, Any]:
        """Validate if the resolver can handle the requested selectors."""
        validation_result = {
            "can_resolve": True,
            "missing_selectors": [],
            "context_issues": [],
            "warnings": []
        }
        
        full_context = f"{context.current_page}.{context.current_section}"
        
        for name in selector_names:
            # Check if selector exists
            selector = self.registry.get_selector_by_name(name, full_context)
            if not selector:
                selector = self.registry.get_selector_by_name(name, context.current_page)
                if not selector:
                    validation_result["missing_selectors"].append(name)
                    validation_result["can_resolve"] = False
                else:
                    validation_result["warnings"].append(f"Selector '{name}' only available in broader context '{context.current_page}'")
            
            # Check context validity
            if selector and not self.registry.validate_selector_context(name, full_context):
                validation_result["context_issues"].append(f"Selector '{name}' may not be appropriate for context '{full_context}'")
        
        return validation_result
    
    def explain_resolution(self, 
                         semantic_name: str,
                         context: ResolutionContext) -> Dict[str, Any]:
        """Explain how a selector would be resolved."""
        explanation = {
            "semantic_name": semantic_name,
            "requested_context": f"{context.current_page}.{context.current_section}",
            "resolution_steps": []
        }
        
        # Step 1: Look up selector
        full_context = f"{context.current_page}.{context.current_section}"
        selector = self.registry.get_selector_by_name(semantic_name, full_context)
        
        if not selector:
            # Try broader context
            selector = self.registry.get_selector_by_name(semantic_name, context.current_page)
            if selector:
                explanation["resolution_steps"].append({
                    "step": "context_fallback",
                    "description": f"Selector found in broader context '{context.current_page}'",
                    "context_used": context.current_page
                })
            else:
                explanation["resolution_steps"].append({
                    "step": "lookup_failed",
                    "description": f"Selector '{semantic_name}' not found",
                    "available_contexts": self.registry.get_available_contexts()
                })
                return explanation
        else:
            explanation["resolution_steps"].append({
                "step": "direct_lookup",
                "description": f"Selector found in exact context '{full_context}'",
                "context_used": full_context
            })
        
        # Step 2: Validate context
        if self.registry.validate_selector_context(semantic_name, full_context):
            explanation["resolution_steps"].append({
                "step": "context_validation",
                "description": "Context validation passed",
                "valid": True
            })
        else:
            explanation["resolution_steps"].append({
                "step": "context_validation",
                "description": "Context validation warning - selector may not be optimal for this context",
                "valid": False
            })
        
        # Step 3: Strategy resolution
        explanation["resolution_steps"].append({
            "step": "strategy_resolution",
            "description": f"Found {len(selector.strategies)} strategies",
            "strategies": [
                {
                    "type": strategy.type,
                    "priority": strategy.priority,
                    "has_template": hasattr(strategy, 'template') and strategy.template is not None
                }
                for strategy in selector.strategies
            ]
        })
        
        # Step 4: Inheritance resolution
        explanation["resolution_steps"].append({
            "step": "inheritance_resolution",
            "description": "Inheritance will be applied to resolve templates and defaults",
            "has_validation": selector.validation is not None,
            "has_confidence": selector.confidence is not None
        })
        
        return explanation
