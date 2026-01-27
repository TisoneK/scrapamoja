"""
Selector registry for Selector Engine.

Provides centralized management of semantic selectors with validation,
registration, and lookup capabilities as specified in the API contracts.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from src.models.selector_models import (
    SemanticSelector, StrategyPattern, ValidationRule, ConfidenceMetrics
)
from src.observability.logger import get_logger
from src.observability.events import publish_event
from src.utils.exceptions import (
    SelectorNotFoundError, ValidationError, ConfigurationError
)
from src.config.settings import get_config


@dataclass
class RegistryEntry:
    """Registry entry for a selector."""
    selector: SemanticSelector
    registered_at: datetime
    last_updated: datetime
    usage_count: int = 0
    last_used: Optional[datetime] = None
    metrics: Optional[ConfidenceMetrics] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelectorRegistry:
    """Centralized registry for semantic selectors."""
    
    def __init__(self):
        self._logger = get_logger("selector_registry")
        self._selectors: Dict[str, RegistryEntry] = {}
        self._contexts: Dict[str, List[str]] = {}
        self._config = get_config()
        
        # Registry statistics
        self._total_registrations = 0
        self._total_unregistrations = 0
        self._last_activity = datetime.utcnow()
        
        self._logger.info("SelectorRegistry initialized")
    
    async def register_selector(self, selector: SemanticSelector) -> bool:
        """
        Register a new semantic selector.
        
        Args:
            selector: Semantic selector definition
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate selector
            validation_issues = await self._validate_selector(selector)
            if validation_issues:
                self._logger.warning(
                    "selector_registration_failed_validation",
                    selector_name=selector.name,
                    issues=validation_issues
                )
                return False
            
            # Check for conflicts
            if selector.name in self._selectors:
                existing_entry = self._selectors[selector.name]
                if not self._is_selector_compatible(existing_entry.selector, selector):
                    self._logger.warning(
                        "selector_registration_conflict",
                        selector_name=selector.name,
                        existing_registered_at=existing_entry.registered_at.isoformat()
                    )
                    return False
                else:
                    # Update existing selector
                    await self._update_selector(selector)
                    return True
            
            # Create registry entry
            entry = RegistryEntry(
                selector=selector,
                registered_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                metadata={
                    "source": "manual_registration",
                    "version": "1.0"
                }
            )
            
            # Register selector
            self._selectors[selector.name] = entry
            
            # Update context index
            if selector.context not in self._contexts:
                self._contexts[selector.context] = []
            if selector.name not in self._contexts[selector.context]:
                self._contexts[selector.context].append(selector.name)
            
            # Update statistics
            self._total_registrations += 1
            self._last_activity = datetime.utcnow()
            
            # Publish event
            await publish_event(
                "selector_registered",
                {
                    "selector_name": selector.name,
                    "context": selector.context,
                    "strategies_count": len(selector.strategies),
                    "registered_at": entry.registered_at.isoformat()
                },
                source="selector_registry"
            )
            
            self._logger.info(
                "selector_registered",
                selector_name=selector.name,
                context=selector.context,
                strategies=len(selector.strategies),
                total_selectors=len(self._selectors)
            )
            
            return True
            
        except Exception as e:
            self._logger.error(
                "selector_registration_error",
                selector_name=selector.name,
                error=str(e)
            )
            return False
    
    async def unregister_selector(self, name: str) -> bool:
        """
        Unregister a semantic selector.
        
        Args:
            name: Selector name
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            if name not in self._selectors:
                self._logger.warning(
                    "selector_unregistration_not_found",
                    selector_name=name
                )
                return False
            
            entry = self._selectors[name]
            
            # Remove from context index
            if entry.selector.context in self._contexts:
                if name in self._contexts[entry.selector.context]:
                    self._contexts[entry.selector.context].remove(name)
                
                # Remove empty context
                if not self._contexts[entry.selector.context]:
                    del self._contexts[entry.selector.context]
            
            # Remove from registry
            del self._selectors[name]
            
            # Update statistics
            self._total_unregistrations += 1
            self._last_activity = datetime.utcnow()
            
            # Publish event
            await publish_event(
                "selector_unregistered",
                {
                    "selector_name": name,
                    "context": entry.selector.context,
                    "unregistered_at": datetime.utcnow().isoformat()
                },
                source="selector_registry"
            )
            
            self._logger.info(
                "selector_unregistered",
                selector_name=name,
                total_selectors=len(self._selectors)
            )
            
            return True
            
        except Exception as e:
            self._logger.error(
                "selector_unregistration_error",
                selector_name=name,
                error=str(e)
            )
            return False
    
    def get_selector(self, name: str) -> Optional[SemanticSelector]:
        """Get selector definition by name."""
        entry = self._selectors.get(name)
        return entry.selector if entry else None
    
    def list_selectors(self, context: Optional[str] = None) -> List[str]:
        """
        List registered selectors, optionally filtered by context.
        
        Args:
            context: Optional context filter
            
        Returns:
            List of selector names
        """
        if context:
            return self._contexts.get(context, []).copy()
        else:
            return list(self._selectors.keys())
    
    def list_contexts(self) -> List[str]:
        """List all registered contexts."""
        return list(self._contexts.keys())
    
    def get_selector_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a selector."""
        entry = self._selectors.get(name)
        if not entry:
            return None
        
        return {
            "name": entry.selector.name,
            "description": entry.selector.description,
            "context": entry.selector.context,
            "strategies": [
                {
                    "id": strategy.id,
                    "type": strategy.type.value,
                    "priority": strategy.priority,
                    "config": strategy.config
                }
                for strategy in entry.selector.strategies
            ],
            "validation_rules": [
                {
                    "type": rule.type.value,
                    "pattern": rule.pattern,
                    "required": rule.required,
                    "weight": rule.weight
                }
                for rule in entry.selector.validation_rules
            ],
            "confidence_threshold": entry.selector.confidence_threshold,
            "registered_at": entry.registered_at.isoformat(),
            "last_updated": entry.last_updated.isoformat(),
            "usage_count": entry.usage_count,
            "last_used": entry.last_used.isoformat() if entry.last_used else None,
            "metrics": entry.metrics.to_dict() if entry.metrics else None,
            "metadata": entry.metadata
        }
    
    async def update_selector(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing selector.
        
        Args:
            name: Selector name
            updates: Dictionary of updates
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            if name not in self._selectors:
                self._logger.warning(
                    "selector_update_not_found",
                    selector_name=name
                )
                return False
            
            entry = self._selectors[name]
            
            # Apply updates
            updated_selector = self._apply_updates(entry.selector, updates)
            
            # Validate updated selector
            validation_issues = await self._validate_selector(updated_selector)
            if validation_issues:
                self._logger.warning(
                    "selector_update_failed_validation",
                    selector_name=name,
                    issues=validation_issues
                )
                return False
            
            # Update entry
            entry.selector = updated_selector
            entry.last_updated = datetime.utcnow()
            
            # Update context index if context changed
            if "context" in updates and updates["context"] != entry.selector.context:
                old_context = entry.selector.context
                new_context = updates["context"]
                
                # Remove from old context
                if old_context in self._contexts and name in self._contexts[old_context]:
                    self._contexts[old_context].remove(name)
                    if not self._contexts[old_context]:
                        del self._contexts[old_context]
                
                # Add to new context
                if new_context not in self._contexts:
                    self._contexts[new_context] = []
                if name not in self._contexts[new_context]:
                    self._contexts[new_context].append(name)
            
            # Update statistics
            self._last_activity = datetime.utcnow()
            
            # Publish event
            await publish_event(
                "selector_updated",
                {
                    "selector_name": name,
                    "updates": list(updates.keys()),
                    "updated_at": entry.last_updated.isoformat()
                },
                source="selector_registry"
            )
            
            self._logger.info(
                "selector_updated",
                selector_name=name,
                updates=list(updates.keys())
            )
            
            return True
            
        except Exception as e:
            self._logger.error(
                "selector_update_error",
                selector_name=name,
                error=str(e)
            )
            return False
    
    def record_selector_usage(self, name: str, metrics: Optional[ConfidenceMetrics] = None) -> None:
        """Record selector usage and update metrics."""
        if name not in self._selectors:
            return
        
        entry = self._selectors[name]
        entry.usage_count += 1
        entry.last_used = datetime.utcnow()
        entry.metrics = metrics
        
        self._last_activity = datetime.utcnow()
        
        self._logger.debug(
            "selector_usage_recorded",
            selector_name=name,
            usage_count=entry.usage_count,
            last_used=entry.last_used.isoformat()
        )
    
    def get_usage_statistics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics for selectors."""
        if name:
            if name not in self._selectors:
                return {}
            
            entry = self._selectors[name]
            return {
                "selector_name": name,
                "usage_count": entry.usage_count,
                "last_used": entry.last_used.isoformat() if entry.last_used else None,
                "registered_at": entry.registered_at.isoformat(),
                "last_updated": entry.last_updated.isoformat(),
                "metrics": entry.metrics.to_dict() if entry.metrics else None
            }
        else:
            # Global statistics
            total_usage = sum(entry.usage_count for entry in self._selectors.values())
            most_used = max(self._selectors.values(), key=lambda e: e.usage_count, default=None)
            least_used = min(self._selectors.values(), key=lambda e: e.usage_count, default=None)
            
            return {
                "total_selectors": len(self._selectors),
                "total_contexts": len(self._contexts),
                "total_usage": total_usage,
                "total_registrations": self._total_registrations,
                "total_unregistrations": self._total_unregistrations,
                "last_activity": self._last_activity.isoformat(),
                "most_used_selector": most_used.selector.name if most_used else None,
                "most_used_count": most_used.usage_count if most_used else 0,
                "least_used_selector": least_used.selector.name if least_used else None,
                "least_used_count": least_used.usage_count if least_used else 0,
                "contexts": {
                    context: len(selectors)
                    for context, selectors in self._contexts.items()
                }
            }
    
    async def validate_selector(self, selector: SemanticSelector) -> List[str]:
        """Validate selector definition."""
        issues = []
        
        # Basic validation
        if not selector.name.strip():
            issues.append("Selector name cannot be empty")
        
        if len(selector.name) > 100:
            issues.append("Selector name too long (max 100 characters)")
        
        if not selector.description.strip():
            issues.append("Selector description cannot be empty")
        
        # Validate strategies
        if len(selector.strategies) < 3:
            issues.append("Selector must have at least 3 strategies")
        
        if len(selector.strategies) > 10:
            issues.append("Selector cannot have more than 10 strategies")
        
        # Check for duplicate strategy priorities
        priorities = [s.priority for s in selector.strategies]
        if len(priorities) != len(set(priorities)):
            issues.append("Strategy priorities must be unique")
        
        # Validate individual strategies
        for strategy in selector.strategies:
            strategy_issues = await self._validate_strategy(strategy)
            issues.extend(strategy_issues)
        
        # Validate validation rules
        for rule in selector.validation_rules:
            rule_issues = await self._validate_validation_rule(rule)
            issues.extend(rule_issues)
        
        # Validate confidence threshold
        if not (0.0 <= selector.confidence_threshold <= 1.0):
            issues.append("Confidence threshold must be between 0.0 and 1.0")
        
        # Validate context
        if not selector.context.strip():
            issues.append("Context cannot be empty")
        
        if len(selector.context) > 50:
            issues.append("Context name too long (max 50 characters)")
        
        return issues
    
    async def _validate_strategy(self, strategy: StrategyPattern) -> List[str]:
        """Validate individual strategy."""
        issues = []
        
        if not strategy.id.strip():
            issues.append("Strategy ID cannot be empty")
        
        if not strategy.config:
            issues.append("Strategy config cannot be empty")
        
        # Strategy-specific validation
        if strategy.type.value == "text_anchor":
            if "anchor_text" not in strategy.config:
                issues.append("Text anchor strategy requires 'anchor_text' in config")
        elif strategy.type.value == "attribute_match":
            if "attribute" not in strategy.config:
                issues.append("Attribute match strategy requires 'attribute' in config")
            if "value_pattern" not in strategy.config:
                issues.append("Attribute match strategy requires 'value_pattern' in config")
        elif strategy.type.value == "dom_relationship":
            if "parent_selector" not in strategy.config:
                issues.append("DOM relationship strategy requires 'parent_selector' in config")
            if "relationship_type" not in strategy.config:
                issues.append("DOM relationship strategy requires 'relationship_type' in config")
        elif strategy.type.value == "role_based":
            if "role" not in strategy.config:
                issues.append("Role-based strategy requires 'role' in config")
        
        return issues
    
    async def _validate_validation_rule(self, rule: ValidationRule) -> List[str]:
        """Validate individual validation rule."""
        issues = []
        
        if not rule.pattern.strip():
            issues.append("Validation rule pattern cannot be empty")
        
        if not (0.0 <= rule.weight <= 1.0):
            issues.append("Validation rule weight must be between 0.0 and 1.0")
        
        # Rule-specific validation
        if rule.type.value == "regex":
            try:
                import re
                re.compile(rule.pattern)
            except re.error as e:
                issues.append(f"Invalid regex pattern: {e}")
        
        return issues
    
    def _is_selector_compatible(self, existing: SemanticSelector, new: SemanticSelector) -> bool:
        """Check if new selector is compatible with existing one."""
        # Same name and context - allow update
        if existing.name == new.name and existing.context == new.context:
            return True
        
        # Different context - allow registration
        if existing.context != new.context:
            return True
        
        # Same context but different name - check for conflicts
        # This is a simplified check - in practice, you might want more sophisticated logic
        return False
    
    async def _update_selector(self, selector: SemanticSelector) -> None:
        """Update existing selector."""
        entry = self._selectors[selector.name]
        entry.selector = selector
        entry.last_updated = datetime.utcnow()
        
        self._logger.info(
            "selector_updated_existing",
            selector_name=selector.name,
            updated_at=entry.last_updated.isoformat()
        )
    
    def _apply_updates(self, selector: SemanticSelector, updates: Dict[str, Any]) -> SemanticSelector:
        """Apply updates to selector definition."""
        # Create a copy of the selector
        updated_selector = SemanticSelector(
            name=updates.get("name", selector.name),
            description=updates.get("description", selector.description),
            context=updates.get("context", selector.context),
            strategies=updates.get("strategies", selector.strategies),
            validation_rules=updates.get("validation_rules", selector.validation_rules),
            confidence_threshold=updates.get("confidence_threshold", selector.confidence_threshold)
        )
        
        return updated_selector
    
    async def _validate_selector(self, selector: SemanticSelector) -> List[str]:
        """Validate selector definition."""
        # This is a placeholder - the actual validation is in the public method
        return []


# Global selector registry instance
selector_registry = SelectorRegistry()


def get_selector_registry() -> SelectorRegistry:
    """Get global selector registry instance."""
    return selector_registry
