"""
Enhanced selector registry with YAML configuration support.

This module provides an enhanced registry that integrates with the YAML
configuration system for loading, managing, and resolving selectors.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

from .configuration import (
    IConfigurationLoader,
    IInheritanceResolver,
    ISemanticIndex,
    IConfigurationWatcher
)
from ..models.selector_config import (
    SelectorConfiguration,
    SemanticSelector,
    ConfigurationStats,
    ConfigurationState,
    ResolutionContext
)


class EnhancedSelectorRegistry:
    """Enhanced selector registry with YAML configuration support."""
    
    def __init__(self, 
                 config_loader: IConfigurationLoader,
                 inheritance_resolver: IInheritanceResolver,
                 semantic_index: ISemanticIndex,
                 config_watcher: IConfigurationWatcher):
        """Initialize enhanced registry with configuration components."""
        self.config_loader = config_loader
        self.inheritance_resolver = inheritance_resolver
        self.semantic_index = semantic_index
        self.config_watcher = config_watcher
        
        self.state = ConfigurationState()
        self.logger = logging.getLogger(__name__)
        self._correlation_counter = 0
        self._is_initialized = False
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"registry_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def initialize_from_config(self, config_root: Path) -> None:
        """Initialize registry from YAML configuration files."""
        correlation_id = self._generate_correlation_id()
        
        try:
            self.logger.info(f"Initializing registry from {config_root} (correlation: {correlation_id})")
            
            # Load all configurations
            configurations = await self.config_loader.load_configurations_recursive(config_root)
            self.state.loaded_configurations = configurations
            
            # Build semantic index
            self.state.semantic_index = await self.semantic_index.build_index(configurations)
            
            # Start file watching for hot-reload
            await self.config_watcher.start_watching(config_root)
            self.config_watcher.set_change_callback(self._on_configuration_change)
            
            self._is_initialized = True
            self.state.last_reload = datetime.now().isoformat()
            
            stats = self.get_configuration_stats()
            self.logger.info(f"Registry initialized: {stats.total_configurations} configs, {stats.total_selectors} selectors")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize registry: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the registry and cleanup resources."""
        try:
            await self.config_watcher.stop_watching()
            self.state = ConfigurationState()
            self._is_initialized = False
            self.logger.info("Registry shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during registry shutdown: {e}")
    
    def get_selector_by_name(self, semantic_name: str, context: Optional[str] = None) -> Optional[SemanticSelector]:
        """Get selector by semantic name using configuration system."""
        if not self._is_initialized:
            raise RuntimeError("Registry not initialized")
        
        # Look up selector in semantic index
        entry = self.semantic_index.lookup_selector(semantic_name, context)
        if not entry:
            return None
        
        # Resolve selector with inheritance
        return asyncio.run(self.inheritance_resolver.resolve_selector_with_inheritance(
            self.state.loaded_configurations[entry.file_path],
            semantic_name
        ))
    
    def get_available_selectors(self, context: Optional[str] = None) -> List[str]:
        """Get all available selectors for a context."""
        if not self._is_initialized:
            raise RuntimeError("Registry not initialized")
        
        if context:
            entries = self.semantic_index.get_selectors_by_context(context)
            return [entry.semantic_name for entry in entries]
        else:
            return list(self.state.semantic_index.keys())
    
    def validate_selector_context(self, semantic_name: str, context: str) -> bool:
        """Validate that selector is appropriate for context."""
        if not self._is_initialized:
            raise RuntimeError("Registry not initialized")
        
        return self.semantic_index.validate_selector_context(semantic_name, context)
    
    async def reload_configurations(self) -> None:
        """Reload all configurations and update registry."""
        correlation_id = self._generate_correlation_id()
        
        if not self._is_initialized:
            raise RuntimeError("Registry not initialized")
        
        try:
            self.logger.info(f"Reloading configurations (correlation: {correlation_id})")
            
            # Get current config root
            config_root = Path(self.config_watcher.root_path) if self.config_watcher.root_path else None
            if not config_root:
                raise RuntimeError("Cannot determine configuration root")
            
            # Clear caches
            self.inheritance_resolver.clear_cache()
            
            # Reload configurations
            configurations = await self.config_loader.load_configurations_recursive(config_root)
            self.state.loaded_configurations = configurations
            
            # Rebuild semantic index
            self.state.semantic_index = await self.semantic_index.build_index(configurations)
            
            self.state.last_reload = datetime.now().isoformat()
            
            stats = self.get_configuration_stats()
            self.logger.info(f"Configurations reloaded: {stats.total_configurations} configs, {stats.total_selectors} selectors")
            
        except Exception as e:
            self.state.error_count += 1
            self.logger.error(f"Failed to reload configurations: {e}")
            raise
    
    def get_configuration_stats(self) -> ConfigurationStats:
        """Get statistics about loaded configurations."""
        total_selectors = sum(len(config.selectors) for config in self.state.loaded_configurations.values())
        total_templates = sum(len(config.strategy_templates) for config in self.state.loaded_configurations.values())
        inheritance_chains = len(self.inheritance_resolver.get_cache_stats().get("cached_chains", {}))
        
        return ConfigurationStats(
            total_configurations=len(self.state.loaded_configurations),
            total_selectors=total_selectors,
            total_templates=total_templates,
            inheritance_chains=inheritance_chains,
            index_entries=len(self.state.semantic_index),
            last_reload=self.state.last_reload or "",
            error_count=self.state.error_count,
            loading_time_ms=0.0  # Would be tracked during actual loading
        )
    
    def get_index_conflicts(self) -> Dict[str, List['SemanticIndexEntry']]:
        """Get selector name conflicts."""
        if not self._is_initialized:
            raise RuntimeError("Registry not initialized")
        
        return self.semantic_index.find_conflicts()
    
    def get_available_contexts(self) -> List[str]:
        """Get all available contexts."""
        if not self._is_initialized:
            raise RuntimeError("Registry not initialized")
        
        return self.semantic_index.get_available_contexts()
    
    def suggest_selectors(self, partial_name: str, context: Optional[str] = None, limit: int = 10) -> List[str]:
        """Suggest selector names based on partial match."""
        if not self._is_initialized:
            raise RuntimeError("Registry not initialized")
        
        return self.semantic_index.suggest_selectors(partial_name, context, limit)
    
    def get_registry_health(self) -> Dict[str, any]:
        """Get registry health status."""
        return {
            "initialized": self._is_initialized,
            "config_count": len(self.state.loaded_configurations),
            "selector_count": len(self.state.semantic_index),
            "error_count": self.state.error_count,
            "last_reload": self.state.last_reload,
            "watcher_active": self.config_watcher.is_watching if hasattr(self.config_watcher, 'is_watching') else False,
            "inheritance_cache_size": len(self.inheritance_resolver.get_cache_stats().get("cached_chains", {})),
            "conflicts_count": len(self.get_index_conflicts())
        }
    
    async def _on_configuration_change(self, file_path: str, event_type: str) -> None:
        """Handle configuration file changes."""
        correlation_id = self._generate_correlation_id()
        
        try:
            self.logger.debug(f"Configuration change: {event_type} - {file_path} (correlation: {correlation_id})")
            
            if event_type in ["modified", "created"]:
                # Reload the specific configuration
                config = await self.config_loader.reload_configuration(Path(file_path))
                if config:
                    # Update index for this configuration
                    await self.semantic_index.update_index(file_path, config)
                    self.state.loaded_configurations[file_path] = config
                    
                    # Invalidate inheritance cache for this file
                    self.inheritance_resolver.invalidate_cache(file_path)
                    
                    self.logger.info(f"Configuration updated: {file_path}")
                else:
                    self.logger.warning(f"Failed to reload configuration: {file_path}")
            
            elif event_type == "deleted":
                # Remove from index and loaded configurations
                await self.semantic_index.remove_from_index(file_path)
                if file_path in self.state.loaded_configurations:
                    del self.state.loaded_configurations[file_path]
                
                # Invalidate inheritance cache for this file
                self.inheritance_resolver.invalidate_cache(file_path)
                
                self.logger.info(f"Configuration removed: {file_path}")
            
            # Update last reload time
            self.state.last_reload = datetime.now().isoformat()
            
        except Exception as e:
            self.state.error_count += 1
            self.logger.error(f"Error handling configuration change {file_path}: {e}")
    
    def get_configuration_by_file(self, file_path: str) -> Optional[SelectorConfiguration]:
        """Get configuration by file path."""
        return self.state.loaded_configurations.get(file_path)
    
    def get_selectors_by_file(self, file_path: str) -> List[str]:
        """Get selector names from a specific configuration file."""
        config = self.get_configuration_by_file(file_path)
        if config:
            return list(config.selectors.keys())
        return []
    
    def validate_configuration_integrity(self) -> Dict[str, List[str]]:
        """Validate the integrity of loaded configurations."""
        issues = {
            "errors": [],
            "warnings": []
        }
        
        if not self._is_initialized:
            issues["errors"].append("Registry not initialized")
            return issues
        
        # Check for conflicts
        conflicts = self.get_index_conflicts()
        if conflicts:
            issues["warnings"].append(f"Found {len(conflicts)} selector name conflicts")
        
        # Check for empty configurations
        empty_configs = [path for path, config in self.state.loaded_configurations.items() 
                        if not config.selectors and not config.strategy_templates]
        if empty_configs:
            issues["warnings"].append(f"Found {len(empty_configs)} empty configuration files")
        
        # Check inheritance cache consistency
        cache_stats = self.inheritance_resolver.get_cache_stats()
        cached_chains = cache_stats.get("cached_chains", 0)
        loaded_configs = len(self.state.loaded_configurations)
        if cached_chains > loaded_configs * 2:  # Rough heuristic
            issues["warnings"].append("Inheritance cache may be stale")
        
        return issues
    
    async def get_hot_reload_status(self) -> Dict[str, Any]:
        """Get hot-reload status and statistics."""
        if not self._is_initialized:
            return {
                "initialized": False,
                "hot_reload_enabled": False
            }
        
        # Get watcher status
        watcher_status = {}
        if hasattr(self.config_watcher, 'is_watching'):
            watcher_status = {
                "active": self.config_watcher.is_watching,
                "watched_files_count": len(self.config_watcher.get_watched_files())
            }
        
        # Get rollback history if available
        rollback_history = []
        if hasattr(self.config_watcher, 'rollback_manager'):
            rollback_history = self.config_watcher.rollback_manager.get_rollback_history()
        
        return {
            "initialized": True,
            "hot_reload_enabled": True,
            "watcher_status": watcher_status,
            "last_reload": self.state.last_reload,
            "error_count": self.state.error_count,
            "rollback_count": len(rollback_history),
            "recent_rollbacks": rollback_history[-5:] if rollback_history else [],
            "configuration_changes": len(self.state.loaded_configurations)
        }
    
    def get_hot_reload_metrics(self) -> Dict[str, Any]:
        """Get detailed hot-reload performance metrics."""
        if not self._is_initialized:
            return {"initialized": False}
        
        metrics = {
            "total_configurations": len(self.state.loaded_configurations),
            "total_selectors": len(self.state.semantic_index),
            "last_reload_timestamp": self.state.last_reload,
            "error_count": self.state.error_count,
            "inheritance_cache_size": len(self.inheritance_resolver.get_cache_stats().get("cached_chains", {}))
        }
        
        # Add watcher metrics if available
        if hasattr(self.config_watcher, 'get_performance_metrics'):
            watcher_metrics = asyncio.run(self.config_watcher.get_performance_metrics())
            metrics["watcher_metrics"] = watcher_metrics
        
        return metrics
    
    async def export_configuration_data(self) -> Dict[str, Any]:
        """Export configuration data for debugging or analysis."""
        return {
            "state": {
                "loaded_configurations": list(self.state.loaded_configurations.keys()),
                "semantic_index_keys": list(self.state.semantic_index.keys()),
                "last_reload": self.state.last_reload,
                "error_count": self.state.error_count
            },
            "stats": self.get_configuration_stats(),
            "health": self.get_registry_health(),
            "conflicts": {name: [{"context": entry.context, "file": entry.file_path} for entry in entries] 
                        for name, entries in self.get_index_conflicts().items()},
            "contexts": self.get_available_contexts(),
            "index_data": self.semantic_index.export_index_data() if hasattr(self.semantic_index, 'export_index_data') else {}
        }
