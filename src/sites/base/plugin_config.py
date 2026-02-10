"""
Plugin configuration management system.

This module provides comprehensive configuration management for plugins, including
configuration loading, validation, merging, and persistence.
"""

import os
import json
import yaml
import asyncio
from typing import Dict, Any, List, Optional, Union, Type, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import weakref

from .plugin_interface import IPlugin, PluginMetadata, PluginType, get_plugin_registry
from .config_schemas import ConfigSchema, ConfigValidator
from .config_loader import ConfigLoader
from .config_merger import ConfigMerger


class ConfigFormat(Enum):
    """Configuration format enumeration."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    INI = "ini"
    ENV = "env"


class ConfigScope(Enum):
    """Configuration scope enumeration."""
    GLOBAL = "global"
    PLUGIN_TYPE = "plugin_type"
    PLUGIN = "plugin"
    INSTANCE = "instance"
    SESSION = "session"


@dataclass
class ConfigSource:
    """Configuration source definition."""
    source_id: str
    source_type: ConfigFormat
    source_path: Optional[str] = None
    source_data: Optional[Dict[str, Any]] = None
    priority: int = 0
    enabled: bool = True
    auto_reload: bool = False
    reload_interval_seconds: int = 60
    last_loaded: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigEntry:
    """Configuration entry."""
    plugin_id: str
    scope: ConfigScope
    config_data: Dict[str, Any]
    source_id: Optional[str] = None
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigValidationResult:
    """Configuration validation result."""
    valid: bool
    plugin_id: str
    scope: ConfigScope
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    validation_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PluginConfigManager:
    """Plugin configuration manager."""
    
    def __init__(self):
        """Initialize plugin configuration manager."""
        self.registry = get_plugin_registry()
        
        # Configuration storage
        self._configs: Dict[str, ConfigEntry] = {}
        self._config_sources: Dict[str, ConfigSource] = {}
        self._config_schemas: Dict[str, ConfigSchema] = {}
        
        # Configuration management
        self._config_loader = ConfigLoader()
        self._config_merger = ConfigMerger()
        self._config_validator = ConfigValidator()
        
        # Caching
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Auto-reload
        self._auto_reload_enabled = True
        self._reload_tasks: Dict[str, asyncio.Task] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'total_configs': 0,
            'total_sources': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_count': 0,
            'validation_failures': 0,
            'reload_count': 0,
            'last_reload': None
        }
        
        # Event listeners
        self._event_listeners: Dict[str, List[Callable]] = {}
        
        # Default configuration directories
        self._config_directories = [
            "config/plugins",
            "src/config/plugins",
            "plugins/config",
            ".config/plugins"
        ]
    
    def add_config_source(self, source: ConfigSource) -> bool:
        """
        Add a configuration source.
        
        Args:
            source: Configuration source
            
        Returns:
            True if added successfully
        """
        with self._lock:
            if source.source_id in self._config_sources:
                return False
            
            self._config_sources[source.source_id] = source
            self._stats['total_sources'] += 1
            
            # Load configuration if source has data
            if source.source_data or source.source_path:
                asyncio.create_task(self._load_config_source(source.source_id))
            
            # Start auto-reload if enabled
            if source.auto_reload and self._auto_reload_enabled:
                asyncio.create_task(self._start_auto_reload(source.source_id))
            
            # Emit event
            self._emit_event('config_source_added', {
                'source_id': source.source_id,
                'source_type': source.source_type.value,
                'priority': source.priority
            })
            
            return True
    
    def remove_config_source(self, source_id: str) -> bool:
        """
        Remove a configuration source.
        
        Args:
            source_id: Source ID
            
        Returns:
            True if removed successfully
        """
        with self._lock:
            if source_id not in self._config_sources:
                return False
            
            source = self._config_sources[source_id]
            
            # Stop auto-reload
            if source_id in self._reload_tasks:
                self._reload_tasks[source_id].cancel()
                del self._reload_tasks[source_id]
            
            # Remove configurations from this source
            configs_to_remove = [
                config_id for config_id, config in self._configs.items()
                if config.source_id == source_id
            ]
            
            for config_id in configs_to_remove:
                del self._configs[config_id]
            
            # Remove source
            del self._config_sources[source_id]
            self._stats['total_sources'] -= 1
            
            # Clear cache
            self._clear_cache()
            
            # Emit event
            self._emit_event('config_source_removed', {
                'source_id': source_id
            })
            
            return True
    
    def get_config_source(self, source_id: str) -> Optional[ConfigSource]:
        """Get a configuration source by ID."""
        return self._config_sources.get(source_id)
    
    def get_all_config_sources(self) -> Dict[str, ConfigSource]:
        """Get all configuration sources."""
        with self._lock:
            return self._config_sources.copy()
    
    async def load_plugin_config(self, plugin_id: str, scope: ConfigScope = ConfigScope.PLUGIN,
                               source_id: Optional[str] = None) -> bool:
        """
        Load configuration for a plugin.
        
        Args:
            plugin_id: Plugin ID
            scope: Configuration scope
            source_id: Optional source ID
            
        Returns:
            True if loaded successfully
        """
        try:
            # Get plugin metadata
            plugin = self.registry.get_plugin(plugin_id)
            if not plugin:
                return False
            
            metadata = plugin.metadata
            
            # Determine configuration sources to load from
            sources_to_load = []
            
            if source_id:
                sources_to_load.append(source_id)
            else:
                # Load from all enabled sources
                for source_id, source in self._config_sources.items():
                    if source.enabled:
                        sources_to_load.append(source_id)
            
            # Sort by priority
            sources_to_load.sort(key=lambda sid: self._config_sources[sid].priority, reverse=True)
            
            # Load and merge configurations
            merged_config = {}
            loaded_from = []
            
            for sid in sources_to_load:
                source = self._config_sources[sid]
                
                try:
                    config_data = await self._load_config_from_source(sid, plugin_id, scope)
                    if config_data:
                        merged_config = self._config_merger.merge_configs(
                            merged_config, config_data, strategy="override"
                        )
                        loaded_from.append(sid)
                except Exception as e:
                    # Log error but continue with other sources
                    self._emit_event('config_load_error', {
                        'plugin_id': plugin_id,
                        'source_id': sid,
                        'error': str(e)
                    })
            
            # Create configuration entry
            config_entry = ConfigEntry(
                plugin_id=plugin_id,
                scope=scope,
                config_data=merged_config,
                source_id=loaded_from[0] if loaded_from else None,
                metadata={
                    'loaded_from': loaded_from,
                    'plugin_type': metadata.plugin_type.value,
                    'plugin_version': metadata.version
                }
            )
            
            # Store configuration
            config_key = f"{plugin_id}_{scope.value}"
            with self._lock:
                self._configs[config_key] = config_entry
                self._stats['total_configs'] += 1
            
            # Clear cache
            self._clear_cache_for_plugin(plugin_id)
            
            # Emit event
            self._emit_event('config_loaded', {
                'plugin_id': plugin_id,
                'scope': scope.value,
                'sources': loaded_from,
                'config_size': len(merged_config)
            })
            
            return True
            
        except Exception as e:
            self._emit_event('config_load_failed', {
                'plugin_id': plugin_id,
                'scope': scope.value,
                'error': str(e)
            })
            return False
    
    async def save_plugin_config(self, plugin_id: str, config_data: Dict[str, Any],
                               scope: ConfigScope = ConfigScope.PLUGIN,
                               source_id: Optional[str] = None) -> bool:
        """
        Save configuration for a plugin.
        
        Args:
            plugin_id: Plugin ID
            config_data: Configuration data
            scope: Configuration scope
            source_id: Optional source ID to save to
            
        Returns:
            True if saved successfully
        """
        try:
            # Validate configuration
            validation_result = await self.validate_plugin_config(plugin_id, config_data, scope)
            if not validation_result.valid:
                return False
            
            # Create configuration entry
            config_entry = ConfigEntry(
                plugin_id=plugin_id,
                scope=scope,
                config_data=config_data,
                source_id=source_id,
                updated_at=datetime.utcnow()
            )
            
            # Store configuration
            config_key = f"{plugin_id}_{scope.value}"
            with self._lock:
                self._configs[config_key] = config_entry
            
            # Save to source if specified
            if source_id and source_id in self._config_sources:
                source = self._config_sources[source_id]
                if source.source_path:
                    await self._save_config_to_source(source_id, plugin_id, config_data, scope)
            
            # Clear cache
            self._clear_cache_for_plugin(plugin_id)
            
            # Emit event
            self._emit_event('config_saved', {
                'plugin_id': plugin_id,
                'scope': scope.value,
                'source_id': source_id,
                'config_size': len(config_data)
            })
            
            return True
            
        except Exception as e:
            self._emit_event('config_save_failed', {
                'plugin_id': plugin_id,
                'scope': scope.value,
                'error': str(e)
            })
            return False
    
    def get_plugin_config(self, plugin_id: str, scope: ConfigScope = ConfigScope.PLUGIN,
                         use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a plugin.
        
        Args:
            plugin_id: Plugin ID
            scope: Configuration scope
            use_cache: Whether to use cached configuration
            
        Returns:
            Configuration data or None
        """
        config_key = f"{plugin_id}_{scope.value}"
        
        # Check cache first
        if use_cache:
            cached_config = self._get_from_cache(config_key)
            if cached_config is not None:
                self._stats['cache_hits'] += 1
                return cached_config
            else:
                self._stats['cache_misses'] += 1
        
        # Get from storage
        with self._lock:
            config_entry = self._configs.get(config_key)
            if config_entry:
                # Update cache
                self._set_cache(config_key, config_entry.config_data)
                return config_entry.config_data.copy()
        
        return None
    
    async def validate_plugin_config(self, plugin_id: str, config_data: Dict[str, Any],
                                   scope: ConfigScope) -> ConfigValidationResult:
        """
        Validate plugin configuration.
        
        Args:
            plugin_id: Plugin ID
            config_data: Configuration data
            scope: Configuration scope
            
        Returns:
            Validation result
        """
        start_time = datetime.utcnow()
        
        try:
            # Get plugin metadata
            plugin = self.registry.get_plugin(plugin_id)
            if not plugin:
                return ConfigValidationResult(
                    valid=False,
                    plugin_id=plugin_id,
                    scope=scope,
                    errors=[f"Plugin {plugin_id} not found"]
                )
            
            metadata = plugin.metadata
            
            # Get schema for plugin type
            schema = self._get_plugin_schema(metadata.plugin_type)
            
            # Validate configuration
            if schema:
                validation_result = self._config_validator.validate(config_data, schema)
            else:
                # Basic validation
                validation_result = self._perform_basic_validation(config_data, metadata)
            
            # Update statistics
            self._stats['validation_count'] += 1
            if not validation_result.valid:
                self._stats['validation_failures'] += 1
            
            # Create result
            validation_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ConfigValidationResult(
                valid=validation_result.valid,
                plugin_id=plugin_id,
                scope=scope,
                errors=validation_result.errors,
                warnings=validation_result.warnings,
                suggestions=validation_result.suggestions,
                validation_time_ms=validation_time_ms
            )
            
        except Exception as e:
            validation_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ConfigValidationResult(
                valid=False,
                plugin_id=plugin_id,
                scope=scope,
                errors=[f"Validation failed: {str(e)}"],
                validation_time_ms=validation_time_ms
            )
    
    async def reload_config(self, source_id: Optional[str] = None) -> bool:
        """
        Reload configuration from sources.
        
        Args:
            source_id: Optional source ID to reload (all if None)
            
        Returns:
            True if reloaded successfully
        """
        try:
            sources_to_reload = []
            
            if source_id:
                if source_id in self._config_sources:
                    sources_to_reload.append(source_id)
            else:
                sources_to_reload = list(self._config_sources.keys())
            
            success_count = 0
            
            for sid in sources_to_reload:
                try:
                    await self._load_config_source(sid)
                    success_count += 1
                except Exception as e:
                    self._emit_event('config_reload_error', {
                        'source_id': sid,
                        'error': str(e)
                    })
            
            # Update statistics
            self._stats['reload_count'] += 1
            self._stats['last_reload'] = datetime.utcnow()
            
            # Clear cache
            self._clear_cache()
            
            # Emit event
            self._emit_event('config_reloaded', {
                'sources_reloaded': sources_to_reload,
                'success_count': success_count
            })
            
            return success_count > 0
            
        except Exception as e:
            self._emit_event('config_reload_failed', {
                'error': str(e)
            })
            return False
    
    def get_config_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        with self._lock:
            stats = self._stats.copy()
            
            # Add configuration counts by scope
            stats['configs_by_scope'] = {}
            for config in self._configs.values():
                scope = config.scope.value
                stats['configs_by_scope'][scope] = stats['configs_by_scope'].get(scope, 0) + 1
            
            # Add source statistics
            stats['sources_by_type'] = {}
            for source in self._config_sources.values():
                source_type = source.source_type.value
                stats['sources_by_type'][source_type] = stats['sources_by_type'].get(source_type, 0) + 1
            
            # Cache statistics
            stats['cache_size'] = len(self._config_cache)
            stats['cache_hit_rate'] = (
                self._stats['cache_hits'] / (self._stats['cache_hits'] + self._stats['cache_misses'])
                if (self._stats['cache_hits'] + self._stats['cache_misses']) > 0 else 0
            )
            
            return stats
    
    def export_configurations(self, plugin_id: Optional[str] = None,
                            scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
        """
        Export configurations.
        
        Args:
            plugin_id: Optional plugin ID filter
            scope: Optional scope filter
            
        Returns:
            Exported configurations
        """
        with self._lock:
            exported = {}
            
            for config_key, config in self._configs.items():
                # Apply filters
                if plugin_id and config.plugin_id != plugin_id:
                    continue
                
                if scope and config.scope != scope:
                    continue
                
                exported[config_key] = {
                    'plugin_id': config.plugin_id,
                    'scope': config.scope.value,
                    'config_data': config.config_data,
                    'source_id': config.source_id,
                    'version': config.version,
                    'created_at': config.created_at.isoformat(),
                    'updated_at': config.updated_at.isoformat(),
                    'expires_at': config.expires_at.isoformat() if config.expires_at else None,
                    'tags': config.tags,
                    'metadata': config.metadata
                }
            
            return {
                'configurations': exported,
                'sources': {
                    source_id: {
                        'source_type': source.source_type.value,
                        'source_path': source.source_path,
                        'priority': source.priority,
                        'enabled': source.enabled,
                        'auto_reload': source.auto_reload,
                        'metadata': source.metadata
                    }
                    for source_id, source in self._config_sources.items()
                },
                'statistics': self.get_config_statistics(),
                'exported_at': datetime.utcnow().isoformat()
            }
    
    async def import_configurations(self, import_data: Dict[str, Any],
                                 overwrite: bool = False) -> bool:
        """
        Import configurations.
        
        Args:
            import_data: Import data
            overwrite: Whether to overwrite existing configurations
            
        Returns:
            True if imported successfully
        """
        try:
            # Import configurations
            for config_key, config_data in import_data.get('configurations', {}).items():
                if not overwrite and config_key in self._configs:
                    continue
                
                config_entry = ConfigEntry(
                    plugin_id=config_data['plugin_id'],
                    scope=ConfigScope(config_data['scope']),
                    config_data=config_data['config_data'],
                    source_id=config_data.get('source_id'),
                    version=config_data.get('version', '1.0.0'),
                    created_at=datetime.fromisoformat(config_data['created_at']) if config_data.get('created_at') else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(config_data['updated_at']) if config_data.get('updated_at') else datetime.utcnow(),
                    expires_at=datetime.fromisoformat(config_data['expires_at']) if config_data.get('expires_at') else None,
                    tags=config_data.get('tags', []),
                    metadata=config_data.get('metadata', {})
                )
                
                self._configs[config_key] = config_entry
            
            # Import sources
            for source_id, source_data in import_data.get('sources', {}).items():
                if not overwrite and source_id in self._config_sources:
                    continue
                
                source = ConfigSource(
                    source_id=source_id,
                    source_type=ConfigFormat(source_data['source_type']),
                    source_path=source_data.get('source_path'),
                    priority=source_data.get('priority', 0),
                    enabled=source_data.get('enabled', True),
                    auto_reload=source_data.get('auto_reload', False),
                    metadata=source_data.get('metadata', {})
                )
                
                self._config_sources[source_id] = source
            
            # Clear cache
            self._clear_cache()
            
            # Emit event
            self._emit_event('configurations_imported', {
                'config_count': len(import_data.get('configurations', {})),
                'source_count': len(import_data.get('sources', {}))
            })
            
            return True
            
        except Exception as e:
            self._emit_event('configurations_import_failed', {
                'error': str(e)
            })
            return False
    
    def add_event_listener(self, event: str, listener: Callable) -> None:
        """Add an event listener."""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        
        self._event_listeners[event].append(listener)
    
    def remove_event_listener(self, event: str, listener: Callable) -> bool:
        """Remove an event listener."""
        if event in self._event_listeners:
            try:
                self._event_listeners[event].remove(listener)
                return True
            except ValueError:
                pass
        
        return False
    
    def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to listeners."""
        if event in self._event_listeners:
            for listener in self._event_listeners[event]:
                try:
                    listener(data)
                except Exception as e:
                    # Log error but continue
                    pass
    
    async def _load_config_source(self, source_id: str) -> None:
        """Load configuration from a source."""
        source = self._config_sources[source_id]
        
        if source.source_path:
            # Load from file
            config_data = await self._config_loader.load_from_file(source.source_path)
        elif source.source_data:
            # Use provided data
            config_data = source.source_data
        else:
            return
        
        # Update source metadata
        source.last_loaded = datetime.utcnow()
        if source.source_path:
            try:
                file_path = Path(source.source_path)
                if file_path.exists():
                    source.last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            except Exception:
                pass
    
    async def _load_config_from_source(self, source_id: str, plugin_id: str, 
                                     scope: ConfigScope) -> Optional[Dict[str, Any]]:
        """Load configuration for a specific plugin from a source."""
        source = self._config_sources[source_id]
        
        if source.source_path:
            # Load from file and extract plugin-specific config
            full_config = await self._config_loader.load_from_file(source.source_path)
            
            # Navigate to plugin-specific configuration
            config_path = [scope.value, plugin_id]
            current = full_config
            
            for key in config_path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            return current if isinstance(current, dict) else None
        
        elif source.source_data:
            # Extract from provided data
            config_path = [scope.value, plugin_id]
            current = source.source_data
            
            for key in config_path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            return current if isinstance(current, dict) else None
        
        return None
    
    async def _save_config_to_source(self, source_id: str, plugin_id: str,
                                   config_data: Dict[str, Any], scope: ConfigScope) -> None:
        """Save configuration to a source."""
        source = self._config_sources[source_id]
        
        if not source.source_path:
            return
        
        # Load existing configuration
        existing_config = {}
        if os.path.exists(source.source_path):
            existing_config = await self._config_loader.load_from_file(source.source_path)
        
        # Update configuration
        if scope.value not in existing_config:
            existing_config[scope.value] = {}
        
        existing_config[scope.value][plugin_id] = config_data
        
        # Save to file
        await self._config_loader.save_to_file(source.source_path, existing_config)
    
    def _get_plugin_schema(self, plugin_type: PluginType) -> Optional[ConfigSchema]:
        """Get configuration schema for a plugin type."""
        return self._config_schemas.get(plugin_type.value)
    
    def _perform_basic_validation(self, config_data: Dict[str, Any], 
                                metadata: PluginMetadata) -> ConfigValidationResult:
        """Perform basic configuration validation."""
        errors = []
        warnings = []
        suggestions = []
        
        # Check if configuration is a dictionary
        if not isinstance(config_data, dict):
            errors.append("Configuration must be a dictionary")
            return ConfigValidationResult(
                valid=False,
                plugin_id=metadata.id,
                scope=ConfigScope.PLUGIN,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
        
        # Check for required fields based on plugin type
        if metadata.plugin_type == PluginType.EXTRACTION:
            if 'selectors' not in config_data:
                warnings.append("No selectors defined for extraction plugin")
            elif not isinstance(config_data['selectors'], dict):
                errors.append("Selectors must be a dictionary")
        
        # Check for common configuration issues
        if 'enabled' in config_data and not isinstance(config_data['enabled'], bool):
            errors.append("'enabled' must be a boolean")
        
        if 'timeout' in config_data:
            try:
                timeout = float(config_data['timeout'])
                if timeout <= 0:
                    errors.append("'timeout' must be positive")
            except (ValueError, TypeError):
                errors.append("'timeout' must be a number")
        
        return ConfigValidationResult(
            valid=len(errors) == 0,
            plugin_id=metadata.id,
            scope=ConfigScope.PLUGIN,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get configuration from cache."""
        if key in self._config_cache:
            timestamp = self._cache_timestamps.get(key)
            if timestamp and datetime.utcnow() - timestamp < self._cache_ttl:
                return self._config_cache[key].copy()
            else:
                # Expired, remove from cache
                del self._config_cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
        
        return None
    
    def _set_cache(self, key: str, config_data: Dict[str, Any]) -> None:
        """Set configuration in cache."""
        self._config_cache[key] = config_data.copy()
        self._cache_timestamps[key] = datetime.utcnow()
    
    def _clear_cache(self) -> None:
        """Clear all cache."""
        self._config_cache.clear()
        self._cache_timestamps.clear()
    
    def _clear_cache_for_plugin(self, plugin_id: str) -> None:
        """Clear cache for a specific plugin."""
        keys_to_remove = [key for key in self._config_cache.keys() if key.startswith(plugin_id)]
        
        for key in keys_to_remove:
            del self._config_cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
    
    async def _start_auto_reload(self, source_id: str) -> None:
        """Start auto-reload for a source."""
        source = self._config_sources[source_id]
        
        if not source.auto_reload:
            return
        
        while True:
            try:
                await asyncio.sleep(source.reload_interval_seconds)
                
                # Check if source needs reload
                if source.source_path:
                    file_path = Path(source.source_path)
                    if file_path.exists():
                        current_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if (not source.last_modified or 
                            current_modified > source.last_modified):
                            
                            await self._load_config_source(source_id)
                            self._stats['reload_count'] += 1
                            
                            self._emit_event('config_auto_reloaded', {
                                'source_id': source_id,
                                'modified_time': current_modified.isoformat()
                            })
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                pass
    
    def cleanup(self) -> None:
        """Clean up configuration manager."""
        # Cancel auto-reload tasks
        for task in self._reload_tasks.values():
            task.cancel()
        
        self._reload_tasks.clear()
        
        # Clear data
        self._configs.clear()
        self._config_sources.clear()
        self._config_schemas.clear()
        self._config_cache.clear()
        self._cache_timestamps.clear()
        
        # Clear event listeners
        self._event_listeners.clear()
        
        # Reset statistics
        self._stats = {
            'total_configs': 0,
            'total_sources': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_count': 0,
            'validation_failures': 0,
            'reload_count': 0,
            'last_reload': None
        }


# Global plugin configuration manager instance
_plugin_config_manager = PluginConfigManager()


# Convenience functions
def add_config_source(source: ConfigSource) -> bool:
    """Add a configuration source."""
    return _plugin_config_manager.add_config_source(source)


def remove_config_source(source_id: str) -> bool:
    """Remove a configuration source."""
    return _plugin_config_manager.remove_config_source(source_id)


def get_config_source(source_id: str) -> Optional[ConfigSource]:
    """Get a configuration source by ID."""
    return _plugin_config_manager.get_config_source(source_id)


async def load_plugin_config(plugin_id: str, scope: ConfigScope = ConfigScope.PLUGIN,
                           source_id: Optional[str] = None) -> bool:
    """Load configuration for a plugin."""
    return await _plugin_config_manager.load_plugin_config(plugin_id, scope, source_id)


async def save_plugin_config(plugin_id: str, config_data: Dict[str, Any],
                           scope: ConfigScope = ConfigScope.PLUGIN,
                           source_id: Optional[str] = None) -> bool:
    """Save configuration for a plugin."""
    return await _plugin_config_manager.save_plugin_config(plugin_id, config_data, scope, source_id)


def get_plugin_config(plugin_id: str, scope: ConfigScope = ConfigScope.PLUGIN,
                     use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """Get configuration for a plugin."""
    return _plugin_config_manager.get_plugin_config(plugin_id, scope, use_cache)


async def validate_plugin_config(plugin_id: str, config_data: Dict[str, Any],
                               scope: ConfigScope) -> ConfigValidationResult:
    """Validate plugin configuration."""
    return await _plugin_config_manager.validate_plugin_config(plugin_id, config_data, scope)


async def reload_config(source_id: Optional[str] = None) -> bool:
    """Reload configuration from sources."""
    return await _plugin_config_manager.reload_config(source_id)


def get_config_statistics() -> Dict[str, Any]:
    """Get configuration statistics."""
    return _plugin_config_manager.get_config_statistics()


def export_configurations(plugin_id: Optional[str] = None,
                        scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
    """Export configurations."""
    return _plugin_config_manager.export_configurations(plugin_id, scope)


async def import_configurations(import_data: Dict[str, Any],
                             overwrite: bool = False) -> bool:
    """Import configurations."""
    return await _plugin_config_manager.import_configurations(import_data, overwrite)


def get_plugin_config_manager() -> PluginConfigManager:
    """Get the global plugin configuration manager."""
    return _plugin_config_manager
