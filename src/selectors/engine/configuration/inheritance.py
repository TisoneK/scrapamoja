"""
Inheritance resolution for YAML selector configurations.

This module provides functionality for resolving configuration inheritance
from parent folders, including context defaults, validation rules, and strategy templates.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from ...models.selector_config import (
    SelectorConfiguration,
    ContextDefaults,
    ValidationDefaults,
    StrategyTemplate,
    InheritanceChain,
    ConfigurationState
)


class InheritanceException(Exception):
    """Exception raised when inheritance resolution fails."""
    
    def __init__(self, message: str, file_path: str, circular_refs: List[str], correlation_id: str):
        self.message = message
        self.file_path = file_path
        self.circular_references = circular_refs
        self.correlation_id = correlation_id
        super().__init__(message)


class IInheritanceResolver(ABC):
    """Interface for resolving configuration inheritance."""
    
    @abstractmethod
    async def resolve_inheritance_chain(self, config_path: str) -> InheritanceChain:
        """Resolve the complete inheritance chain for a configuration."""
        pass
    
    @abstractmethod
    def merge_context_defaults(self, parents: List[ContextDefaults]) -> ContextDefaults:
        """Merge context defaults from parent configurations."""
        pass
    
    @abstractmethod
    def merge_validation_defaults(self, parents: List[ValidationDefaults]) -> ValidationDefaults:
        """Merge validation defaults from parent configurations."""
        pass
    
    @abstractmethod
    def resolve_strategy_template(self, template_name: str, chain: InheritanceChain) -> StrategyTemplate:
        """Resolve a strategy template from the inheritance chain."""
        pass
    
    @abstractmethod
    def detect_circular_references(self, config_path: str) -> List[str]:
        """Detect circular inheritance references."""
        pass


class InheritanceResolver(IInheritanceResolver):
    """Implementation for resolving configuration inheritance."""
    
    def __init__(self):
        """Initialize the inheritance resolver."""
        self._inheritance_cache: Dict[str, InheritanceChain] = {}
        self._correlation_counter = 0
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"inheritance_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def resolve_inheritance_chain(self, config_path: str) -> InheritanceChain:
        """Resolve the complete inheritance chain for a configuration."""
        correlation_id = self._generate_correlation_id()
        
        # Check cache first
        if config_path in self._inheritance_cache:
            return self._inheritance_cache[config_path]
        
        try:
            # Find parent configurations
            parent_paths = self._find_parent_paths(config_path)
            
            # Detect circular references
            circular_refs = self.detect_circular_references(config_path)
            if circular_refs:
                raise InheritanceException(
                    f"Circular inheritance detected: {' -> '.join(circular_refs)}",
                    config_path,
                    circular_refs,
                    correlation_id
                )
            
            # Load parent configurations (this would typically use the ConfigurationLoader)
            parent_configs = await self._load_parent_configurations(parent_paths, correlation_id)
            
            # Merge context defaults
            context_defaults = self._merge_context_defaults_from_configs(parent_configs)
            
            # Merge validation defaults
            validation_defaults = self._merge_validation_defaults_from_configs(parent_configs)
            
            # Collect all available templates
            available_templates = self._collect_templates_from_configs(parent_configs)
            
            # Create inheritance chain
            chain = InheritanceChain(
                child_path=config_path,
                parent_paths=parent_paths,
                resolved_context=context_defaults,
                resolved_validation=validation_defaults,
                available_templates=available_templates
            )
            
            # Cache the result
            self._inheritance_cache[config_path] = chain
            
            return chain
            
        except Exception as e:
            if isinstance(e, InheritanceException):
                raise
            raise InheritanceException(
                f"Error resolving inheritance for {config_path}: {str(e)}",
                config_path,
                [],
                correlation_id
            )
    
    def merge_context_defaults(self, parents: List[ContextDefaults]) -> ContextDefaults:
        """Merge context defaults from parent configurations."""
        if not parents:
            raise ValueError("No parent context defaults provided")
        
        # Start with the first parent as base
        merged = ContextDefaults(
            page_type=parents[0].page_type,
            wait_strategy=parents[0].wait_strategy,
            timeout=parents[0].timeout,
            section=parents[0].section
        )
        
        # Apply overrides from subsequent parents (later parents override earlier ones)
        for parent in parents[1:]:
            if parent.wait_strategy != merged.wait_strategy:
                merged.wait_strategy = parent.wait_strategy
            
            if parent.timeout != merged.timeout:
                merged.timeout = parent.timeout
            
            if parent.section is not None:
                merged.section = parent.section
        
        return merged
    
    def merge_validation_defaults(self, parents: List[ValidationDefaults]) -> ValidationDefaults:
        """Merge validation defaults from parent configurations."""
        if not parents:
            raise ValueError("No parent validation defaults provided")
        
        # Start with the first parent as base
        merged = ValidationDefaults(
            required=parents[0].required,
            type=parents[0].type,
            min_length=parents[0].min_length,
            max_length=parents[0].max_length,
            pattern=parents[0].pattern
        )
        
        # Apply overrides from subsequent parents (later parents override earlier ones)
        for parent in parents[1:]:
            if parent.required is not None:
                merged.required = parent.required
            
            if parent.type is not None:
                merged.type = parent.type
            
            if parent.min_length is not None:
                merged.min_length = parent.min_length
            
            if parent.max_length is not None:
                merged.max_length = parent.max_length
            
            if parent.pattern is not None:
                merged.pattern = parent.pattern
        
        return merged
    
    def resolve_strategy_template(self, template_name: str, chain: InheritanceChain) -> StrategyTemplate:
        """Resolve a strategy template from the inheritance chain."""
        if template_name in chain.available_templates:
            return chain.available_templates[template_name]
        
        raise ValueError(f"Strategy template '{template_name}' not found in inheritance chain")
    
    def detect_circular_references(self, config_path: str) -> List[str]:
        """Detect circular inheritance references."""
        visited = set()
        path_stack = []
        
        def check_path(current_path: str) -> List[str]:
            if current_path in visited:
                # Found circular reference - return the cycle
                cycle_start = path_stack.index(current_path)
                return path_stack[cycle_start:] + [current_path]
            
            visited.add(current_path)
            path_stack.append(current_path)
            
            # Find parent paths
            parent_paths = self._find_parent_paths(current_path)
            
            for parent_path in parent_paths:
                cycle = check_path(parent_path)
                if cycle:
                    return cycle
            
            path_stack.pop()
            return []
        
        return check_path(config_path)
    
    def _find_parent_paths(self, config_path: str) -> List[str]:
        """Find parent configuration paths based on directory hierarchy."""
        config_file = Path(config_path)
        parent_paths = []
        
        # Get parent directory
        parent_dir = config_file.parent
        
        # Look for _context.yaml files in parent directories
        while parent_dir.name and parent_dir.name != 'config':
            context_file = parent_dir / '_context.yaml'
            if context_file.exists():
                parent_paths.append(str(context_file))
            
            # Move up one directory
            parent_dir = parent_dir.parent
        
        return parent_paths
    
    async def _load_parent_configurations(self, parent_paths: List[str], correlation_id: str) -> List[SelectorConfiguration]:
        """Load parent configurations from paths."""
        # This would typically use the ConfigurationLoader
        # For now, return empty list as this is a placeholder implementation
        return []
    
    def _merge_context_defaults_from_configs(self, parent_configs: List[SelectorConfiguration]) -> ContextDefaults:
        """Merge context defaults from parent configurations."""
        parent_contexts = []
        
        for config in parent_configs:
            if config.context_defaults:
                parent_contexts.append(config.context_defaults)
        
        if not parent_contexts:
            # Return default context defaults if no parents have them
            return ContextDefaults(
                page_type="unknown",
                wait_strategy="network_idle",
                timeout=10000
            )
        
        return self.merge_context_defaults(parent_contexts)
    
    def _merge_validation_defaults_from_configs(self, parent_configs: List[SelectorConfiguration]) -> ValidationDefaults:
        """Merge validation defaults from parent configurations."""
        parent_validations = []
        
        for config in parent_configs:
            if config.validation_defaults:
                parent_validations.append(config.validation_defaults)
        
        if not parent_validations:
            # Return default validation defaults if no parents have them
            return ValidationDefaults(
                required=False,
                type="string"
            )
        
        return self.merge_validation_defaults(parent_validations)
    
    def _collect_templates_from_configs(self, parent_configs: List[SelectorConfiguration]) -> Dict[str, StrategyTemplate]:
        """Collect all available strategy templates from parent configurations."""
        templates = {}
        
        # Collect templates from all parents (later parents override earlier ones)
        for config in parent_configs:
            templates.update(config.strategy_templates)
        
        return templates
    
    def detect_inheritance_conflicts(self, config_path: str) -> Dict[str, List[str]]:
        """Detect inheritance conflicts in the inheritance chain."""
        correlation_id = self._generate_correlation_id()
        
        try:
            # Resolve inheritance chain
            chain = asyncio.run(self.resolve_inheritance_chain(config_path))
            
            conflicts = {
                "context_defaults": [],
                "validation_defaults": [],
                "strategy_templates": [],
                "selector_conflicts": []
            }
            
            # Check for context defaults conflicts
            if chain.parent_paths:
                context_conflicts = self._detect_context_conflicts(chain)
                conflicts["context_defaults"] = context_conflicts
            
            # Check for validation defaults conflicts
            if chain.parent_paths:
                validation_conflicts = self._detect_validation_conflicts(chain)
                conflicts["validation_defaults"] = validation_conflicts
            
            # Check for strategy template conflicts
            template_conflicts = self._detect_template_conflicts(chain)
            conflicts["strategy_templates"] = template_conflicts
            
            return conflicts
            
        except Exception as e:
            self.logger.error(f"Error detecting inheritance conflicts for {config_path}: {e}")
            return {
                "error": str(e),
                "context_defaults": [],
                "validation_defaults": [],
                "strategy_templates": [],
                "selector_conflicts": []
            }
    
    def _detect_context_conflicts(self, chain: InheritanceChain) -> List[str]:
        """Detect context defaults conflicts in inheritance chain."""
        conflicts = []
        
        # This would analyze parent configurations for conflicting context defaults
        # For now, return empty list as placeholder
        return conflicts
    
    def _detect_validation_conflicts(self, chain: InheritanceChain) -> List[str]:
        """Detect validation defaults conflicts in inheritance chain."""
        conflicts = []
        
        # This would analyze parent configurations for conflicting validation defaults
        # For now, return empty list as placeholder
        return conflicts
    
    def _detect_template_conflicts(self, chain: InheritanceChain) -> List[str]:
        """Detect strategy template conflicts in inheritance chain."""
        conflicts = []
        
        # Check for template name conflicts
        template_names = list(chain.available_templates.keys())
        if len(template_names) != len(set(template_names)):
            # Find duplicate template names
            seen = set()
            duplicates = set()
            for name in template_names:
                if name in seen:
                    duplicates.add(name)
                seen.add(name)
            
            for duplicate in duplicates:
                conflicts.append(f"Strategy template '{duplicate}' defined in multiple parent configurations")
        
        return conflicts
    
    def validate_inheritance_chain(self, config_path: str) -> Dict[str, any]:
        """Validate the inheritance chain for a configuration."""
        correlation_id = self._generate_correlation_id()
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "chain_info": {}
        }
        
        try:
            # Check for circular references
            circular_refs = self.detect_circular_references(config_path)
            if circular_refs:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Circular inheritance detected: {' -> '.join(circular_refs)}")
            
            # Resolve inheritance chain
            chain = asyncio.run(self.resolve_inheritance_chain(config_path))
            
            validation_result["chain_info"] = {
                "parent_count": len(chain.parent_paths),
                "available_templates": len(chain.available_templates),
                "has_context_defaults": chain.resolved_context is not None,
                "has_validation_defaults": chain.resolved_validation is not None
            }
            
            # Check for inheritance conflicts
            conflicts = self.detect_inheritance_conflicts(config_path)
            if any(conflicts.values()):
                for conflict_type, conflict_list in conflicts.items():
                    if conflict_list:
                        validation_result["warnings"].extend([f"{conflict_type}: {conflict}" for conflict in conflict_list])
            
            return validation_result
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Inheritance validation failed: {str(e)}")
            return validation_result
    
    def clear_cache(self):
        """Clear the inheritance cache."""
        self._inheritance_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get inheritance cache statistics."""
        return {
            "cached_chains": len(self._inheritance_cache),
            "total_resolutions": self._correlation_counter
        }
    
    def invalidate_cache(self, config_path: str):
        """Invalidate cache entry for a specific configuration."""
        if config_path in self._inheritance_cache:
            del self._inheritance_cache[config_path]
    
    def invalidate_cache_by_directory(self, directory: str):
        """Invalidate cache entries for configurations in a directory."""
        dir_path = Path(directory)
        keys_to_remove = []
        
        for cached_path in self._inheritance_cache.keys():
            cached_file = Path(cached_path)
            if dir_path in cached_file.parents:
                keys_to_remove.append(cached_path)
        
        for key in keys_to_remove:
            del self._inheritance_cache[key]
    
    async def resolve_selector_with_inheritance(self, 
                                              selector_config: SelectorConfiguration,
                                              selector_name: str) -> 'SemanticSelector':
        """Resolve a selector with inheritance applied."""
        # Resolve inheritance chain
        chain = await self.resolve_inheritance_chain(selector_config.file_path)
        
        # Get the selector
        if selector_name not in selector_config.selectors:
            raise ValueError(f"Selector '{selector_name}' not found in configuration")
        
        selector = selector_config.selectors[selector_name]
        
        # Apply inheritance to selector
        resolved_selector = self._apply_inheritance_to_selector(selector, chain)
        
        return resolved_selector
    
    def _apply_inheritance_to_selector(self, selector: 'SemanticSelector', chain: InheritanceChain) -> 'SemanticSelector':
        """Apply inheritance to a semantic selector."""
        from ...models.selector_config import SemanticSelector, StrategyDefinition, ValidationRule, ConfidenceConfig
        
        # Apply validation defaults
        resolved_validation = None
        if selector.validation:
            resolved_validation = selector.validation.merge_with_defaults(chain.resolved_validation)
        elif chain.resolved_validation:
            resolved_validation = chain.resolved_validation
        
        # Apply confidence defaults (no inheritance for confidence, just validation)
        resolved_confidence = selector.confidence
        
        # Resolve strategy templates
        resolved_strategies = []
        for strategy in selector.strategies:
            if strategy.template:
                # Resolve template and apply parameters
                template = self.resolve_strategy_template(strategy.template, chain)
                resolved_strategy = template.to_strategy_definition(
                    override_parameters=strategy.parameters,
                    priority=strategy.priority
                )
                resolved_strategies.append(resolved_strategy)
            else:
                resolved_strategies.append(strategy)
        
        return SemanticSelector(
            name=selector.name,
            description=selector.description,
            context=selector.context,
            strategies=resolved_strategies,
            validation=resolved_validation,
            confidence=resolved_confidence
        )
