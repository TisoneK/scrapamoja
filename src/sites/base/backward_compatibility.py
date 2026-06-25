"""
Backward compatibility layer for existing sites to use modular components.

This module provides compatibility adapters and migration utilities to ensure
existing flat template sites can seamlessly transition to the modular architecture
without breaking existing functionality.
"""

import asyncio
import warnings
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import inspect

from .component_interface import IComponent, ComponentContext, ComponentResult
from .component_manager import ComponentManager
from .plugin_interface import PluginRegistry, get_plugin_registry


class CompatibilityMode(Enum):
    """Compatibility mode enumeration."""
    LEGACY = "legacy"           # Use old behavior with warnings
    HYBRID = "hybrid"           # Mix old and new components
    MODERN = "modern"           # Force new components only
    MIGRATION = "migration"     # Actively migrate to new components


@dataclass
class CompatibilityConfig:
    """Compatibility configuration."""
    mode: CompatibilityMode = CompatibilityMode.HYBRID
    enable_warnings: bool = True
    auto_migrate: bool = False
    migration_log_file: Optional[str] = None
    fallback_to_legacy: bool = True
    component_mappings: Dict[str, str] = None  # old_name -> new_name
    
    def __post_init__(self):
        if self.component_mappings is None:
            self.component_mappings = {}


class LegacyComponentAdapter:
    """Adapter for legacy components to work with the new modular system."""
    
    def __init__(self, legacy_component, new_component_class=None):
        """Initialize the adapter."""
        self.legacy_component = legacy_component
        self.new_component_class = new_component_class
        self.compatibility_warnings = []
        self.migration_suggestions = []
    
    async def adapt_to_modular(self, context: ComponentContext) -> ComponentResult:
        """Adapt legacy component to modular interface."""
        try:
            # Check if legacy component has compatible methods
            if hasattr(self.legacy_component, 'execute'):
                # Try to call legacy execute method
                if inspect.iscoroutinefunction(self.legacy_component.execute):
                    result = await self.legacy_component.execute(context)
                else:
                    result = self.legacy_component.execute(context)
                
                # Convert to ComponentResult if needed
                if not isinstance(result, ComponentResult):
                    result = ComponentResult(
                        success=True,
                        data=result if isinstance(result, dict) else {"result": result}
                    )
                
                self._log_compatibility_info("execute", "Successfully adapted")
                return result
            
            elif hasattr(self.legacy_component, 'run'):
                # Try to call legacy run method
                if inspect.iscoroutinefunction(self.legacy_component.run):
                    result = await self.legacy_component.run(context)
                else:
                    result = self.legacy_component.run(context)
                
                result = ComponentResult(
                    success=True,
                    data=result if isinstance(result, dict) else {"result": result}
                )
                
                self._log_compatibility_info("run", "Successfully adapted")
                return result
            
            else:
                # Try to infer behavior from component name/type
                return await self._infer_and_execute(context)
                
        except Exception as e:
            self._log_compatibility_error("adaptation", str(e))
            return ComponentResult(
                success=False,
                errors=[f"Legacy component adaptation failed: {str(e)}"],
                metadata={"legacy_component": str(type(self.legacy_component))}
            )
    
    async def _infer_and_execute(self, context: ComponentContext) -> ComponentResult:
        """Infer component behavior and execute accordingly."""
        component_name = type(self.legacy_component).__name__.lower()
        
        # Try to infer behavior from component name
        if 'extractor' in component_name or 'scraper' in component_name:
            return await self._infer_extraction(context)
        elif 'validator' in component_name:
            return await self._infer_validation(context)
        elif 'transformer' in component_name or 'processor' in component_name:
            return await self._infer_transformation(context)
        else:
            # Default behavior
            return ComponentResult(
                success=True,
                data={"legacy_result": str(self.legacy_component)},
                metadata={"inferred_behavior": True}
            )
    
    async def _infer_extraction(self, context: ComponentContext) -> ComponentResult:
        """Infer extraction behavior."""
        try:
            # Try common extraction methods
            if hasattr(self.legacy_component, 'extract'):
                if inspect.iscoroutinefunction(self.legacy_component.extract):
                    result = await self.legacy_component.extract(context)
                else:
                    result = self.legacy_component.extract(context)
            elif hasattr(self.legacy_component, 'scrape'):
                if inspect.iscoroutinefunction(self.legacy_component.scrape):
                    result = await self.legacy_component.scrape(context)
                else:
                    result = self.legacy_component.scrape(context)
            else:
                result = {"extracted": True, "source": "legacy_component"}
            
            self._log_compatibility_info("extraction", "Successfully inferred")
            return ComponentResult(success=True, data=result)
            
        except Exception as e:
            return ComponentResult(
                success=False,
                errors=[f"Extraction inference failed: {str(e)}"]
            )
    
    async def _infer_validation(self, context: ComponentContext) -> ComponentResult:
        """Infer validation behavior."""
        try:
            data = context.data.get("input_data", {})
            
            if hasattr(self.legacy_component, 'validate'):
                if inspect.iscoroutinefunction(self.legacy_component.validate):
                    result = await self.legacy_component.validate(data)
                else:
                    result = self.legacy_component.validate(data)
            else:
                # Default validation
                result = {"valid": True, "message": "Legacy validation passed"}
            
            self._log_compatibility_info("validation", "Successfully inferred")
            return ComponentResult(success=True, data=result)
            
        except Exception as e:
            return ComponentResult(
                success=False,
                errors=[f"Validation inference failed: {str(e)}"]
            )
    
    async def _infer_transformation(self, context: ComponentContext) -> ComponentResult:
        """Infer transformation behavior."""
        try:
            data = context.data.get("input_data", {})
            
            if hasattr(self.legacy_component, 'transform'):
                if inspect.iscoroutinefunction(self.legacy_component.transform):
                    result = await self.legacy_component.transform(data)
                else:
                    result = self.legacy_component.transform(data)
            elif hasattr(self.legacy_component, 'process'):
                if inspect.iscoroutinefunction(self.legacy_component.process):
                    result = await self.legacy_component.process(data)
                else:
                    result = self.legacy_component.process(data)
            else:
                # Default transformation
                result = {"transformed": True, "original": data}
            
            self._log_compatibility_info("transformation", "Successfully inferred")
            return ComponentResult(success=True, data=result)
            
        except Exception as e:
            return ComponentResult(
                success=False,
                errors=[f"Transformation inference failed: {str(e)}"]
            )
    
    def _log_compatibility_info(self, operation: str, message: str):
        """Log compatibility information."""
        info = f"Legacy component {operation}: {message}"
        self.compatibility_warnings.append(info)
        
        # Add migration suggestion
        if self.new_component_class:
            suggestion = f"Consider migrating to {self.new_component_class.__name__}"
            self.migration_suggestions.append(suggestion)
    
    def _log_compatibility_error(self, operation: str, error: str):
        """Log compatibility error."""
        error_msg = f"Legacy component {operation} error: {error}"
        self.compatibility_warnings.append(error_msg)


class BackwardCompatibilityManager:
    """Manager for backward compatibility operations."""
    
    def __init__(self, config: Optional[CompatibilityConfig] = None):
        """Initialize the compatibility manager."""
        self.config = config or CompatibilityConfig()
        self.component_manager = ComponentManager()
        self.plugin_registry = get_plugin_registry()
        
        # Compatibility mappings
        self.legacy_adapters: Dict[str, LegacyComponentAdapter] = {}
        self.component_mappings = self.config.component_mappings.copy()
        
        # Migration tracking
        self.migration_log: List[Dict[str, Any]] = []
        self.compatibility_issues: List[Dict[str, Any]] = []
        
        # Initialize default mappings
        self._initialize_default_mappings()
    
    def _initialize_default_mappings(self):
        """Initialize default component mappings."""
        default_mappings = {
            # Legacy extractors
            'title_extractor': 'title_extraction_component',
            'content_extractor': 'content_extraction_component',
            'link_extractor': 'link_extraction_component',
            'image_extractor': 'image_extraction_component',
            
            # Legacy validators
            'data_validator': 'validation_component',
            'content_validator': 'content_validation_component',
            
            # Legacy transformers
            'data_transformer': 'transformation_component',
            'content_processor': 'processing_component',
            
            # Legacy scrapers
            'basic_scraper': 'modular_scraper',
            'simple_scraper': 'modular_scraper',
        }
        
        self.component_mappings.update(default_mappings)
    
    async def adapt_legacy_site(self, site_class, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt a legacy site class to use modular components."""
        try:
            adaptation_result = {
                "success": True,
                "adapted_components": [],
                "warnings": [],
                "migration_suggestions": [],
                "new_config": site_config.copy()
            }
            
            # Analyze legacy site class
            legacy_components = self._analyze_legacy_site(site_class)
            
            # Adapt each component
            for component_name, component_instance in legacy_components.items():
                adapter = LegacyComponentAdapter(component_instance)
                
                # Find corresponding new component
                new_component_name = self.component_mappings.get(component_name)
                if new_component_name:
                    try:
                        new_component_class = self._get_new_component_class(new_component_name)
                        adapter.new_component_class = new_component_class
                    except Exception:
                        pass
                
                # Test adaptation
                test_context = ComponentContext(
                    component_id=component_name,
                    component_metadata=None,
                    framework_context=None,
                    data={"test": True}
                )
                
                adaptation_result_test = await adapter.adapt_to_modular(test_context)
                
                if adaptation_result_test.success:
                    adaptation_result["adapted_components"].append({
                        "name": component_name,
                        "adapter": adapter,
                        "new_component": new_component_name
                    })
                    
                    # Add warnings and suggestions
                    adaptation_result["warnings"].extend(adapter.compatibility_warnings)
                    adaptation_result["migration_suggestions"].extend(adapter.migration_suggestions)
                    
                    # Store adapter for future use
                    self.legacy_adapters[component_name] = adapter
                else:
                    adaptation_result["warnings"].append(
                        f"Failed to adapt component {component_name}: {adaptation_result_test.errors}"
                    )
            
            # Update configuration for modular system
            if self.config.mode in [CompatibilityMode.HYBRID, CompatibilityMode.MODERN]:
                adaptation_result["new_config"] = self._create_modular_config(
                    site_config, adaptation_result["adapted_components"]
                )
            
            # Log migration
            self._log_migration(site_class.__name__, adaptation_result)
            
            return adaptation_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "adapted_components": [],
                "warnings": [],
                "migration_suggestions": []
            }
    
    def _analyze_legacy_site(self, site_class) -> Dict[str, Any]:
        """Analyze a legacy site class to identify components."""
        components = {}
        
        # Look for component-like attributes
        for attr_name in dir(site_class):
            if not attr_name.startswith('_'):
                attr_value = getattr(site_class, attr_name)
                
                # Check if it's a component-like object
                if (hasattr(attr_value, 'execute') or 
                    hasattr(attr_value, 'run') or 
                    hasattr(attr_value, 'extract') or
                    hasattr(attr_value, 'validate') or
                    hasattr(attr_value, 'transform')):
                    components[attr_name] = attr_value
        
        return components
    
    def _get_new_component_class(self, component_name: str):
        """Get the new component class by name."""
        # Try to import from component modules
        try:
            from .components.extraction import TitleExtractionComponent
            if 'title' in component_name:
                return TitleExtractionComponent
        except ImportError:
            pass
        
        try:
            from .components.validation import ValidationComponent
            if 'validation' in component_name:
                return ValidationComponent
        except ImportError:
            pass
        
        try:
            from .components.transformation import TransformationComponent
            if 'transform' in component_name or 'process' in component_name:
                return TransformationComponent
        except ImportError:
            pass
        
        # Return generic component class
        from .component_interface import BaseComponent
        return BaseComponent
    
    def _create_modular_config(self, legacy_config: Dict[str, Any], 
                             adapted_components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create modular configuration from legacy config."""
        modular_config = {
            "components": {},
            "plugins": {},
            "browser": legacy_config.get("browser", {}),
            "selectors": legacy_config.get("selectors", {})
        }
        
        # Add adapted components
        for component_info in adapted_components:
            component_name = component_info["name"]
            new_component_name = component_info.get("new_component", component_name)
            
            modular_config["components"][new_component_name] = {
                "enabled": True,
                "legacy_adapter": True,
                "original_name": component_name
            }
        
        return modular_config
    
    async def execute_legacy_component(self, component_name: str, 
                                      context: ComponentContext) -> ComponentResult:
        """Execute a legacy component through its adapter."""
        if component_name not in self.legacy_adapters:
            return ComponentResult(
                success=False,
                errors=[f"No adapter found for legacy component: {component_name}"]
            )
        
        adapter = self.legacy_adapters[component_name]
        return await adapter.adapt_to_modular(context)
    
    def get_migration_report(self) -> Dict[str, Any]:
        """Get a comprehensive migration report."""
        return {
            "total_adapted_components": len(self.legacy_adapters),
            "component_mappings": self.component_mappings,
            "migration_log": self.migration_log,
            "compatibility_issues": self.compatibility_issues,
            "compatibility_mode": self.config.mode.value,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _log_migration(self, site_name: str, adaptation_result: Dict[str, Any]):
        """Log migration information."""
        log_entry = {
            "site_name": site_name,
            "timestamp": datetime.utcnow().isoformat(),
            "success": adaptation_result["success"],
            "adapted_count": len(adaptation_result["adapted_components"]),
            "warning_count": len(adaptation_result["warnings"]),
            "suggestion_count": len(adaptation_result["migration_suggestions"])
        }
        
        self.migration_log.append(log_entry)
        
        # Log to file if configured
        if self.config.migration_log_file:
            try:
                import json
                with open(self.config.migration_log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception:
                pass
    
    def add_component_mapping(self, legacy_name: str, new_name: str):
        """Add a component mapping."""
        self.component_mappings[legacy_name] = new_name
    
    def remove_component_mapping(self, legacy_name: str) -> bool:
        """Remove a component mapping."""
        if legacy_name in self.component_mappings:
            del self.component_mappings[legacy_name]
            return True
        return False
    
    def get_compatibility_warnings(self) -> List[str]:
        """Get all compatibility warnings."""
        warnings = []
        for adapter in self.legacy_adapters.values():
            warnings.extend(adapter.compatibility_warnings)
        return warnings
    
    def get_migration_suggestions(self) -> List[str]:
        """Get all migration suggestions."""
        suggestions = []
        for adapter in self.legacy_adapters.values():
            suggestions.extend(adapter.migration_suggestions)
        return suggestions


# Global compatibility manager instance
_compatibility_manager = BackwardCompatibilityManager()


# Convenience functions
async def adapt_legacy_site(site_class, site_config: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a legacy site class to use modular components."""
    return await _compatibility_manager.adapt_legacy_site(site_class, site_config)


async def execute_legacy_component(component_name: str, 
                                context: ComponentContext) -> ComponentResult:
    """Execute a legacy component through its adapter."""
    return await _compatibility_manager.execute_legacy_component(component_name, context)


def get_migration_report() -> Dict[str, Any]:
    """Get a comprehensive migration report."""
    return _compatibility_manager.get_migration_report()


def get_compatibility_warnings() -> List[str]:
    """Get all compatibility warnings."""
    return _compatibility_manager.get_compatibility_warnings()


def get_migration_suggestions() -> List[str]:
    """Get all migration suggestions."""
    return _compatibility_manager.get_migration_suggestions()


def set_compatibility_config(config: CompatibilityConfig):
    """Set the compatibility configuration."""
    global _compatibility_manager
    _compatibility_manager = BackwardCompatibilityManager(config)


def get_compatibility_manager() -> BackwardCompatibilityManager:
    """Get the global compatibility manager."""
    return _compatibility_manager


# Decorator for legacy component compatibility
def legacy_compatible(new_component_class=None, mapping_name=None):
    """Decorator to mark a component as legacy compatible."""
    def decorator(cls):
        # Add compatibility metadata
        cls._legacy_compatible = True
        cls._new_component_class = new_component_class
        cls._mapping_name = mapping_name or cls.__name__.lower()
        
        # Register mapping if provided
        if mapping_name:
            _compatibility_manager.add_component_mapping(mapping_name, cls.__name__)
        
        return cls
    
    return decorator


# Context manager for compatibility mode
class CompatibilityContext:
    """Context manager for temporary compatibility mode changes."""
    
    def __init__(self, mode: CompatibilityMode, enable_warnings: bool = True):
        self.mode = mode
        self.enable_warnings = enable_warnings
        self.original_config = None
    
    def __enter__(self):
        self.original_config = _compatibility_manager.config
        _compatibility_manager.config = CompatibilityConfig(
            mode=self.mode,
            enable_warnings=self.enable_warnings
        )
        return _compatibility_manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        _compatibility_manager.config = self.original_config
