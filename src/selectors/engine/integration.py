"""
Integration module for YAML configuration system with existing SelectorEngine.

This module provides integration capabilities to connect the YAML-based selector
configuration system with the existing SelectorEngine implementation.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .configuration import (
    ConfigurationLoader,
    ConfigurationValidator,
    InheritanceResolver,
    SemanticIndex,
    create_configuration_watcher
)
from .registry import EnhancedSelectorRegistry
from .resolver import EnhancedSelectorResolver
from ..models.selector_config import ResolutionContext
from ..models.selector_models import SemanticSelector as ExistingSemanticSelector, SelectorResult


class ConfigurationSystemIntegration:
    """Integration layer for YAML configuration system."""
    
    def __init__(self):
        """Initialize the configuration system integration."""
        self.logger = logging.getLogger(__name__)
        self._correlation_counter = 0
        
        # Initialize configuration components
        self.config_loader = ConfigurationLoader()
        self.config_validator = ConfigurationValidator()
        self.inheritance_resolver = InheritanceResolver()
        self.semantic_index = SemanticIndex()
        self.config_watcher = create_configuration_watcher()
        
        # Initialize enhanced registry and resolver
        self.enhanced_registry = EnhancedSelectorRegistry(
            self.config_loader,
            self.inheritance_resolver,
            self.semantic_index,
            self.config_watcher
        )
        self.enhanced_resolver = EnhancedSelectorResolver(self.enhanced_registry)
        
        self._is_initialized = False
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"config_integration_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def initialize(self, config_root: Path) -> None:
        """Initialize the configuration system."""
        correlation_id = self._generate_correlation_id()
        
        try:
            self.logger.info(f"Initializing configuration system integration from {config_root} (correlation: {correlation_id})")
            
            # Initialize enhanced registry
            await self.enhanced_registry.initialize_from_config(config_root)
            
            self._is_initialized = True
            self.logger.info("Configuration system integration initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration system integration: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the configuration system."""
        try:
            await self.enhanced_registry.shutdown()
            self._is_initialized = False
            self.logger.info("Configuration system integration shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during configuration system shutdown: {e}")
    
    def convert_to_existing_selector(self, config_selector: 'SemanticSelector') -> ExistingSemanticSelector:
        """Convert configuration selector to existing selector model."""
        from ..models.selector_models import StrategyPattern, ValidationRule as ExistingValidationRule
        
        # Convert strategies
        strategies = []
        for config_strategy in config_selector.strategies:
            strategy = StrategyPattern(
                type=config_strategy.type,
                parameters=config_strategy.parameters,
                priority=config_strategy.priority
            )
            strategies.append(strategy)
        
        # Convert validation rule if present
        validation_rule = None
        if config_selector.validation:
            validation_rule = ExistingValidationRule(
                required=config_selector.validation.required,
                type=config_selector.validation.type,
                min_length=config_selector.validation.min_length,
                max_length=config_selector.validation.max_length,
                pattern=config_selector.validation.pattern
            )
        
        # Create existing selector model
        return ExistingSemanticSelector(
            name=config_selector.name,
            description=config_selector.description,
            context=config_selector.context,
            strategies=strategies,
            validation=validation_rule
        )
    
    async def resolve_selector_with_config(self, 
                                         semantic_name: str,
                                         page_type: str,
                                         section: str,
                                         tab_context: Optional[str] = None,
                                         navigation_history: Optional[List[str]] = None) -> SelectorResult:
        """Resolve selector using configuration system."""
        if not self._is_initialized:
            raise RuntimeError("Configuration system not initialized")
        
        # Create resolution context
        resolution_context = ResolutionContext(
            current_page=page_type,
            current_section=section,
            tab_context=tab_context,
            navigation_history=navigation_history or []
        )
        
        # Resolve using enhanced resolver
        config_result = await self.enhanced_resolver.resolve_selector(
            semantic_name,
            resolution_context
        )
        
        # Convert to existing selector model
        existing_selector = self.convert_to_existing_selector(config_result.selector)
        
        # Create existing selector result
        return SelectorResult(
            selector=existing_selector,
            value=None,  # Would be filled by actual DOM resolution
            confidence=config_result.confidence_score,
            strategies_used=[s.type for s in config_result.resolved_strategies],
            resolution_time_ms=config_result.resolution_time_ms,
            context_used=config_result.context_used
        )
    
    def get_available_selectors(self, page_type: str, section: str) -> List[str]:
        """Get available selectors for a page and section."""
        if not self._is_initialized:
            raise RuntimeError("Configuration system not initialized")
        
        context = f"{page_type}.{section}"
        return self.enhanced_registry.get_available_selectors(context)
    
    def validate_selector_context(self, semantic_name: str, page_type: str, section: str) -> bool:
        """Validate selector context."""
        if not self._is_initialized:
            raise RuntimeError("Configuration system not initialized")
        
        context = f"{page_type}.{section}"
        return self.enhanced_registry.validate_selector_context(semantic_name, context)
    
    def get_configuration_stats(self) -> Dict[str, Any]:
        """Get configuration system statistics."""
        if not self._is_initialized:
            return {"initialized": False}
        
        stats = self.enhanced_registry.get_configuration_stats()
        return {
            "initialized": True,
            "total_configurations": stats.total_configurations,
            "total_selectors": stats.total_selectors,
            "total_templates": stats.total_templates,
            "inheritance_chains": stats.inheritance_chains,
            "index_entries": stats.index_entries,
            "last_reload": stats.last_reload,
            "error_count": stats.error_count
        }
    
    def get_integration_health(self) -> Dict[str, Any]:
        """Get integration health status."""
        if not self._is_initialized:
            return {
                "healthy": False,
                "reason": "Not initialized"
            }
        
        registry_health = self.enhanced_registry.get_registry_health()
        
        return {
            "healthy": registry_health["error_count"] == 0 and registry_health["initialized"],
            "registry_health": registry_health,
            "resolver_stats": self.enhanced_resolver.get_resolver_stats(),
            "watcher_status": {
                "active": self.config_watcher.is_watching if hasattr(self.config_watcher, 'is_watching') else False
            }
        }
    
    async def reload_configurations(self) -> None:
        """Reload all configurations."""
        if not self._is_initialized:
            raise RuntimeError("Configuration system not initialized")
        
        await self.enhanced_registry.reload_configurations()
    
    def export_configuration_data(self) -> Dict[str, Any]:
        """Export configuration data for debugging."""
        if not self._is_initialized:
            return {"initialized": False}
        
        return asyncio.run(self.enhanced_registry.export_configuration_data())


# Global integration instance
_integration_instance: Optional[ConfigurationSystemIntegration] = None


def get_configuration_integration() -> ConfigurationSystemIntegration:
    """Get the global configuration system integration instance."""
    global _integration_instance
    
    if _integration_instance is None:
        _integration_instance = ConfigurationSystemIntegration()
    
    return _integration_instance


async def initialize_configuration_system(config_root: Path) -> None:
    """Initialize the global configuration system."""
    integration = get_configuration_integration()
    await integration.initialize(config_root)


async def shutdown_configuration_system() -> None:
    """Shutdown the global configuration system."""
    integration = get_configuration_integration()
    await integration.shutdown()


# Convenience functions for integration with existing SelectorEngine
def resolve_selector_from_config(semantic_name: str, page_type: str, section: str, **kwargs) -> SelectorResult:
    """Resolve selector using configuration system (synchronous wrapper)."""
    integration = get_configuration_integration()
    
    if not integration._is_initialized:
        raise RuntimeError("Configuration system not initialized")
    
    # This would need to be called from an async context
    # For now, raise an error to indicate async requirement
    raise RuntimeError("resolve_selector_from_config must be called from async context")


def get_config_selectors(page_type: str, section: str) -> List[str]:
    """Get available selectors from configuration system."""
    integration = get_configuration_integration()
    return integration.get_available_selectors(page_type, section)


def is_config_selector_valid(semantic_name: str, page_type: str, section: str) -> bool:
    """Validate selector context using configuration system."""
    integration = get_configuration_integration()
    return integration.validate_selector_context(semantic_name, page_type, section)


# SelectorEngine extension class
class ConfigurationAwareSelectorEngine:
    """Extension for existing SelectorEngine to support YAML configurations."""
    
    def __init__(self, existing_engine, config_root: Optional[Path] = None):
        """Initialize the configuration-aware engine."""
        self.existing_engine = existing_engine
        self.config_integration = get_configuration_integration()
        self.logger = logging.getLogger(__name__)
        
        if config_root:
            # Initialize configuration system if provided
            asyncio.create_task(self.config_integration.initialize(config_root))
    
    async def resolve_with_config(self, 
                                semantic_name: str,
                                page_type: str,
                                section: str,
                                **kwargs) -> SelectorResult:
        """Resolve selector using configuration system first, fallback to existing engine."""
        try:
            # Try configuration system first
            return await self.config_integration.resolve_selector_with_config(
                semantic_name, page_type, section, **kwargs
            )
        except Exception as e:
            self.logger.warning(f"Configuration system resolution failed for '{semantic_name}': {e}")
            
            # Fallback to existing engine
            return await self.existing_engine.resolve_selector(semantic_name, **kwargs)
    
    def get_available_config_selectors(self, page_type: str, section: str) -> List[str]:
        """Get selectors from configuration system."""
        return self.config_integration.get_available_selectors(page_type, section)
    
    def get_all_available_selectors(self, page_type: str, section: str) -> List[str]:
        """Get selectors from both configuration system and existing engine."""
        config_selectors = set(self.get_available_config_selectors(page_type, section))
        
        # Get selectors from existing engine (would need to be implemented)
        existing_selectors = set()  # Placeholder
        
        return list(config_selectors.union(existing_selectors))
    
    async def initialize_config_system(self, config_root: Path) -> None:
        """Initialize the configuration system."""
        await self.config_integration.initialize(config_root)
    
    async def shutdown_config_system(self) -> None:
        """Shutdown the configuration system."""
        await self.config_integration.shutdown()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get health status of both systems."""
        return {
            "configuration_system": self.config_integration.get_integration_health(),
            "existing_engine": {
                "status": "active"  # Would need to be implemented
            }
        }
