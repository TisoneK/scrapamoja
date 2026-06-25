"""
Plugin discovery system for the scraper framework.

This module provides comprehensive plugin discovery capabilities, including
automatic plugin detection, loading, and registration from multiple sources.
"""

import os
import sys
import importlib
import importlib.util
import inspect
from typing import Dict, Any, List, Optional, Type, Set, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json
import yaml

from .plugin_interface import IPlugin, PluginMetadata, PluginType, PluginRegistry, get_plugin_registry


class DiscoverySource(Enum):
    """Plugin discovery source enumeration."""
    FILE_SYSTEM = "file_system"
    PYTHON_PACKAGE = "python_package"
    CONFIGURATION = "configuration"
    REMOTE = "remote"
    BUILTIN = "builtin"


@dataclass
class DiscoveryResult:
    """Plugin discovery result."""
    success: bool
    discovered_plugins: List[str] = field(default_factory=list)
    loaded_plugins: List[str] = field(default_factory=list)
    failed_plugins: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    discovery_time_ms: float = 0.0
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PluginInfo:
    """Plugin information from discovery."""
    plugin_id: str
    plugin_class: Type[IPlugin]
    module_path: str
    source: DiscoverySource
    metadata: PluginMetadata
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    file_path: Optional[str] = None
    package_name: Optional[str] = None


class PluginDiscovery:
    """Plugin discovery system."""
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """Initialize plugin discovery system."""
        self.registry = registry or get_plugin_registry()
        self._discovered_plugins: Dict[str, PluginInfo] = {}
        self._discovery_paths: List[str] = []
        self._discovery_packages: List[str] = []
        self._discovery_config: Dict[str, Any] = {}
        self._discovery_history: List[DiscoveryResult] = []
        
        # Default discovery paths
        self._default_paths = [
            "plugins",
            "src/plugins",
            "plugins/examples",
            "src/sites/shared_components/plugins"
        ]
        
        # Default discovery packages
        self._default_packages = [
            "scraper_plugins",
            "scorewise_plugins"
        ]
        
        # Plugin file patterns
        self._plugin_file_patterns = [
            "*_plugin.py",
            "plugin_*.py",
            "*plugin.py"
        ]
        
        # Plugin class patterns
        self._plugin_class_patterns = [
            "*Plugin",
            "Plugin*"
        ]
        
        # Discovery settings
        self._auto_discover = True
        self._validate_on_discovery = True
        self._recursive_search = True
        self._load_on_discovery = True
    
    def add_discovery_path(self, path: Union[str, Path], recursive: bool = None) -> None:
        """Add a discovery path."""
        path_str = str(path)
        
        if path_str not in self._discovery_paths:
            self._discovery_paths.append(path_str)
        
        if recursive is not None:
            self._recursive_search = recursive
    
    def remove_discovery_path(self, path: Union[str, Path]) -> bool:
        """Remove a discovery path."""
        path_str = str(path)
        
        if path_str in self._discovery_paths:
            self._discovery_paths.remove(path_str)
            return True
        return False
    
    def add_discovery_package(self, package_name: str) -> None:
        """Add a discovery package."""
        if package_name not in self._discovery_packages:
            self._discovery_packages.append(package_name)
    
    def remove_discovery_package(self, package_name: str) -> bool:
        """Remove a discovery package."""
        if package_name in self._discovery_packages:
            self._discovery_packages.remove(package_name)
            return True
        return False
    
    def set_discovery_config(self, config: Dict[str, Any]) -> None:
        """Set discovery configuration."""
        self._discovery_config = config
    
    def discover_plugins(self, sources: Optional[List[DiscoverySource]] = None) -> DiscoveryResult:
        """
        Discover plugins from all configured sources.
        
        Args:
            sources: List of sources to discover from (all if None)
            
        Returns:
            Discovery result
        """
        start_time = datetime.utcnow()
        
        try:
            if sources is None:
                sources = list(DiscoverySource)
            
            result = DiscoveryResult(success=True)
            
            # Discover from each source
            for source in sources:
                source_result = self._discover_from_source(source)
                
                result.discovered_plugins.extend(source_result.discovered_plugins)
                result.loaded_plugins.extend(source_result.loaded_plugins)
                result.failed_plugins.extend(source_result.failed_plugins)
                result.errors.extend(source_result.errors)
                result.warnings.extend(source_result.warnings)
            
            # Calculate discovery time
            end_time = datetime.utcnow()
            result.discovery_time_ms = (end_time - start_time).total_seconds() * 1000
            result.source = ", ".join([s.value for s in sources])
            
            # Store in history
            self._discovery_history.append(result)
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            discovery_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return DiscoveryResult(
                success=False,
                errors=[f"Discovery failed: {str(e)}"],
                discovery_time_ms=discovery_time_ms
            )
    
    def _discover_from_source(self, source: DiscoverySource) -> DiscoveryResult:
        """Discover plugins from a specific source."""
        if source == DiscoverySource.FILE_SYSTEM:
            return self._discover_from_file_system()
        elif source == DiscoverySource.PYTHON_PACKAGE:
            return self._discover_from_python_packages()
        elif source == DiscoverySource.CONFIGURATION:
            return self._discover_from_configuration()
        elif source == DiscoverySource.REMOTE:
            return self._discover_from_remote()
        elif source == DiscoverySource.BUILTIN:
            return self._discover_builtin_plugins()
        else:
            return DiscoveryResult(
                success=False,
                errors=[f"Unknown discovery source: {source}"]
            )
    
    def _discover_from_file_system(self) -> DiscoveryResult:
        """Discover plugins from file system."""
        result = DiscoveryResult(success=True, source="file_system")
        
        # Use default paths if none configured
        paths = self._discovery_paths if self._discovery_paths else self._default_paths
        
        for path_str in paths:
            path = Path(path_str)
            
            if not path.exists():
                result.warnings.append(f"Discovery path does not exist: {path_str}")
                continue
            
            # Discover plugins in path
            path_result = self._discover_from_path(path)
            
            result.discovered_plugins.extend(path_result.discovered_plugins)
            result.loaded_plugins.extend(path_result.loaded_plugins)
            result.failed_plugins.extend(path_result.failed_plugins)
            result.errors.extend(path_result.errors)
            result.warnings.extend(path_result.warnings)
        
        return result
    
    def _discover_from_path(self, path: Path) -> DiscoveryResult:
        """Discover plugins from a specific path."""
        result = DiscoveryResult(success=True)
        
        try:
            # Find plugin files
            plugin_files = []
            
            if self._recursive_search:
                for pattern in self._plugin_file_patterns:
                    plugin_files.extend(path.rglob(pattern))
            else:
                for pattern in self._plugin_file_patterns:
                    plugin_files.extend(path.glob(pattern))
            
            # Remove duplicates
            plugin_files = list(set(plugin_files))
            
            for plugin_file in plugin_files:
                if plugin_file.is_file():
                    file_result = self._discover_from_file(plugin_file)
                    
                    result.discovered_plugins.extend(file_result.discovered_plugins)
                    result.loaded_plugins.extend(file_result.loaded_plugins)
                    result.failed_plugins.extend(file_result.failed_plugins)
                    result.errors.extend(file_result.errors)
                    result.warnings.extend(file_result.warnings)
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Error discovering from path {path}: {str(e)}")
        
        return result
    
    def _discover_from_file(self, file_path: Path) -> DiscoveryResult:
        """Discover plugins from a specific file."""
        result = DiscoveryResult(success=True)
        
        try:
            # Load module from file
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            
            if spec is None:
                result.warnings.append(f"Could not load spec from {file_path}")
                return result
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin classes in module
            plugin_classes = self._find_plugin_classes(module)
            
            for plugin_class in plugin_classes:
                plugin_result = self._process_plugin_class(plugin_class, DiscoverySource.FILE_SYSTEM, str(file_path))
                
                if plugin_result:
                    result.discovered_plugins.append(plugin_result.plugin_id)
                    
                    if self._load_on_discovery:
                        plugin_instance = plugin_result.plugin_class()
                        
                        if self.registry.register_plugin(plugin_instance):
                            result.loaded_plugins.append(plugin_result.plugin_id)
                        else:
                            result.failed_plugins.append({
                                'plugin_id': plugin_result.plugin_id,
                                'error': 'Failed to register plugin'
                            })
                else:
                    result.failed_plugins.append({
                        'plugin_id': plugin_class.__name__,
                        'error': 'Failed to process plugin class'
                    })
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Error discovering from file {file_path}: {str(e)}")
        
        return result
    
    def _discover_from_python_packages(self) -> DiscoveryResult:
        """Discover plugins from Python packages."""
        result = DiscoveryResult(success=True, source="python_package")
        
        # Use default packages if none configured
        packages = self._discovery_packages if self._discovery_packages else self._default_packages
        
        for package_name in packages:
            try:
                package_result = self._discover_from_package(package_name)
                
                result.discovered_plugins.extend(package_result.discovered_plugins)
                result.loaded_plugins.extend(package_result.loaded_plugins)
                result.failed_plugins.extend(package_result.failed_plugins)
                result.errors.extend(package_result.errors)
                result.warnings.extend(package_result.warnings)
                
            except Exception as e:
                result.errors.append(f"Error discovering package {package_name}: {str(e)}")
        
        return result
    
    def _discover_from_package(self, package_name: str) -> DiscoveryResult:
        """Discover plugins from a specific Python package."""
        result = DiscoveryResult(success=True)
        
        try:
            # Import package
            module = importlib.import_module(package_name)
            
            # Get package path
            if hasattr(module, '__path__'):
                package_path = Path(module.__path__[0])
            else:
                package_path = Path(module.__file__).parent
            
            # Discover plugins in package
            path_result = self._discover_from_path(package_path)
            
            result.discovered_plugins.extend(path_result.discovered_plugins)
            result.loaded_plugins.extend(path_result.loaded_plugins)
            result.failed_plugins.extend(path_result.failed_plugins)
            result.errors.extend(path_result.errors)
            result.warnings.extend(path_result.warnings)
            
        except ImportError as e:
            result.success = False
            result.errors.append(f"Failed to import package {package_name}: {str(e)}")
        except Exception as e:
            result.success = False
            result.errors.append(f"Error discovering package {package_name}: {str(e)}")
        
        return result
    
    def _discover_from_configuration(self) -> DiscoveryResult:
        """Discover plugins from configuration."""
        result = DiscoveryResult(success=True, source="configuration")
        
        if not self._discovery_config:
            result.warnings.append("No discovery configuration provided")
            return result
        
        try:
            # Look for plugin configuration files
            config_files = []
            current_dir = Path.cwd()
            
            config_patterns = [
                "plugins.json",
                "plugins.yaml",
                "plugins.yml",
                "config/plugins.json",
                "config/plugins.yaml",
                "config/plugins.yml"
            ]
            
            for pattern in config_patterns:
                config_files.extend(current_dir.glob(pattern))
            
            for config_file in config_files:
                config_result = self._discover_from_config_file(config_file)
                
                result.discovered_plugins.extend(config_result.discovered_plugins)
                result.loaded_plugins.extend(config_result.loaded_plugins)
                result.failed_plugins.extend(config_result.failed_plugins)
                result.errors.extend(config_result.errors)
                result.warnings.extend(config_result.warnings)
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Error discovering from configuration: {str(e)}")
        
        return result
    
    def _discover_from_config_file(self, config_file: Path) -> DiscoveryResult:
        """Discover plugins from a configuration file."""
        result = DiscoveryResult(success=True)
        
        try:
            # Load configuration
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() == '.json':
                    config_data = json.load(f)
                elif config_file.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    result.warnings.append(f"Unsupported config file format: {config_file.suffix}")
                    return result
            
            # Process plugin configurations
            plugins_config = config_data.get('plugins', {})
            
            for plugin_id, plugin_config in plugins_config.items():
                plugin_result = self._discover_from_config_entry(plugin_id, plugin_config)
                
                if plugin_result:
                    result.discovered_plugins.append(plugin_result.plugin_id)
                    
                    if self._load_on_discovery:
                        plugin_instance = plugin_result.plugin_class()
                        
                        if self.registry.register_plugin(plugin_instance):
                            result.loaded_plugins.append(plugin_result.plugin_id)
                        else:
                            result.failed_plugins.append({
                                'plugin_id': plugin_result.plugin_id,
                                'error': 'Failed to register plugin'
                            })
                else:
                    result.failed_plugins.append({
                        'plugin_id': plugin_id,
                        'error': 'Failed to process plugin configuration'
                    })
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Error discovering from config file {config_file}: {str(e)}")
        
        return result
    
    def _discover_from_config_entry(self, plugin_id: str, plugin_config: Dict[str, Any]) -> Optional[PluginInfo]:
        """Discover plugin from configuration entry."""
        try:
            # Get module path
            module_path = plugin_config.get('module_path')
            if not module_path:
                return None
            
            # Load module
            if module_path.endswith('.py'):
                # Load from file
                file_path = Path(module_path)
                spec = importlib.util.spec_from_file_location(plugin_id, file_path)
                
                if spec is None:
                    return None
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # Load from package
                module = importlib.import_module(module_path)
            
            # Find plugin class
            plugin_classes = self._find_plugin_classes(module)
            
            if not plugin_classes:
                return None
            
            # Use first plugin class found
            plugin_class = plugin_classes[0]
            
            # Create metadata from config
            metadata_dict = plugin_config.get('metadata', {})
            metadata = PluginMetadata(
                id=plugin_id,
                name=metadata_dict.get('name', plugin_id),
                version=metadata_dict.get('version', '1.0.0'),
                description=metadata_dict.get('description', ''),
                author=metadata_dict.get('author', 'Unknown'),
                plugin_type=PluginType(metadata_dict.get('type', 'custom')),
                dependencies=metadata_dict.get('dependencies', []),
                permissions=metadata_dict.get('permissions', []),
                hooks=[HookType(hook) for hook in metadata_dict.get('hooks', [])],
                tags=metadata_dict.get('tags', [])
            )
            
            return PluginInfo(
                plugin_id=plugin_id,
                plugin_class=plugin_class,
                module_path=module_path,
                source=DiscoverySource.CONFIGURATION,
                metadata=metadata,
                file_path=module_path
            )
            
        except Exception as e:
            return None
    
    def _discover_from_remote(self) -> DiscoveryResult:
        """Discover plugins from remote sources."""
        result = DiscoveryResult(success=True, source="remote")
        
        # This would implement remote plugin discovery
        # For now, return empty result
        result.warnings.append("Remote discovery not implemented")
        
        return result
    
    def _discover_builtin_plugins(self) -> DiscoveryResult:
        """Discover built-in plugins."""
        result = DiscoveryResult(success=True, source="builtin")
        
        # This would discover built-in plugins
        # For now, return empty result
        result.warnings.append("Built-in discovery not implemented")
        
        return result
    
    def _find_plugin_classes(self, module) -> List[Type[IPlugin]]:
        """Find plugin classes in a module."""
        plugin_classes = []
        
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                # Check if it's a plugin class
                if (issubclass(obj, IPlugin) and 
                    obj != IPlugin and 
                    not inspect.isabstract(obj)):
                    
                    # Check class name patterns
                    class_name = obj.__name__
                    
                    for pattern in self._plugin_class_patterns:
                        if pattern.replace('*', '') in class_name:
                            plugin_classes.append(obj)
                            break
        
        return plugin_classes
    
    def _process_plugin_class(self, plugin_class: Type[IPlugin], 
                             source: DiscoverySource, 
                             file_path: Optional[str] = None) -> Optional[PluginInfo]:
        """Process a discovered plugin class."""
        try:
            # Create temporary instance to get metadata
            temp_instance = plugin_class()
            metadata = temp_instance.metadata
            
            # Validate metadata
            if not self._validate_metadata(metadata):
                return None
            
            # Create plugin info
            plugin_info = PluginInfo(
                plugin_id=metadata.id,
                plugin_class=plugin_class,
                module_path=plugin_class.__module__,
                source=source,
                metadata=metadata,
                file_path=file_path
            )
            
            # Store discovered plugin
            self._discovered_plugins[metadata.id] = plugin_info
            
            return plugin_info
            
        except Exception as e:
            return None
    
    def _validate_metadata(self, metadata: PluginMetadata) -> bool:
        """Validate plugin metadata."""
        if not self._validate_on_discovery:
            return True
        
        # Basic validation
        if not metadata.id or not metadata.name or not metadata.version:
            return False
        
        # Check for required fields
        if not metadata.author:
            return False
        
        return True
    
    def get_discovered_plugins(self) -> Dict[str, PluginInfo]:
        """Get all discovered plugins."""
        return self._discovered_plugins.copy()
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin information."""
        return self._discovered_plugins.get(plugin_id)
    
    def rediscover_all(self) -> DiscoveryResult:
        """Rediscover all plugins."""
        # Clear discovered plugins
        self._discovered_plugins.clear()
        
        # Perform discovery
        return self.discover_plugins()
    
    def rediscover_source(self, source: DiscoverySource) -> DiscoveryResult:
        """Rediscover plugins from a specific source."""
        # Clear plugins from this source
        plugins_to_remove = [
            plugin_id for plugin_id, plugin_info in self._discovered_plugins.items()
            if plugin_info.source == source
        ]
        
        for plugin_id in plugins_to_remove:
            del self._discovered_plugins[plugin_id]
        
        # Rediscover from source
        return self._discover_from_source(source)
    
    def get_discovery_history(self, limit: Optional[int] = None) -> List[DiscoveryResult]:
        """Get discovery history."""
        if limit:
            return self._discovery_history[-limit:]
        return self._discovery_history.copy()
    
    def clear_history(self) -> None:
        """Clear discovery history."""
        self._discovery_history.clear()
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery statistics."""
        stats = {
            'total_discovered': len(self._discovered_plugins),
            'discovery_paths': len(self._discovery_paths),
            'discovery_packages': len(self._discovery_packages),
            'discovery_history_count': len(self._discovery_history),
            'sources': {}
        }
        
        # Count by source
        for plugin_info in self._discovered_plugins.values():
            source = plugin_info.source.value
            stats['sources'][source] = stats['sources'].get(source, 0) + 1
        
        # Count by type
        stats['types'] = {}
        for plugin_info in self._discovered_plugins.values():
            plugin_type = plugin_info.metadata.plugin_type.value
            stats['types'][plugin_type] = stats['types'].get(plugin_type, 0) + 1
        
        return stats
    
    def export_discovery_config(self) -> Dict[str, Any]:
        """Export discovery configuration."""
        return {
            'discovery_paths': self._discovery_paths,
            'discovery_packages': self._discovery_packages,
            'discovery_config': self._discovery_config,
            'auto_discover': self._auto_discover,
            'validate_on_discovery': self._validate_on_discovery,
            'recursive_search': self._recursive_search,
            'load_on_discovery': self._load_on_discovery,
            'plugin_file_patterns': self._plugin_file_patterns,
            'plugin_class_patterns': self._plugin_class_patterns
        }
    
    def import_discovery_config(self, config: Dict[str, Any]) -> None:
        """Import discovery configuration."""
        self._discovery_paths = config.get('discovery_paths', [])
        self._discovery_packages = config.get('discovery_packages', [])
        self._discovery_config = config.get('discovery_config', {})
        self._auto_discover = config.get('auto_discover', True)
        self._validate_on_discovery = config.get('validate_on_discovery', True)
        self._recursive_search = config.get('recursive_search', True)
        self._load_on_discovery = config.get('load_on_discovery', True)
        self._plugin_file_patterns = config.get('plugin_file_patterns', self._plugin_file_patterns)
        self._plugin_class_patterns = config.get('plugin_class_patterns', self._plugin_class_patterns)


# Global plugin discovery instance
_plugin_discovery = PluginDiscovery()


# Convenience functions
def add_discovery_path(path: Union[str, Path], recursive: bool = None) -> None:
    """Add a discovery path."""
    _plugin_discovery.add_discovery_path(path, recursive)


def remove_discovery_path(path: Union[str, Path]) -> bool:
    """Remove a discovery path."""
    return _plugin_discovery.remove_discovery_path(path)


def add_discovery_package(package_name: str) -> None:
    """Add a discovery package."""
    _plugin_discovery.add_discovery_package(package_name)


def discover_plugins(sources: Optional[List[DiscoverySource]] = None) -> DiscoveryResult:
    """Discover plugins."""
    return _plugin_discovery.discover_plugins(sources)


def get_discovered_plugins() -> Dict[str, PluginInfo]:
    """Get all discovered plugins."""
    return _plugin_discovery.get_discovered_plugins()


def get_plugin_info(plugin_id: str) -> Optional[PluginInfo]:
    """Get plugin information."""
    return _plugin_discovery.get_plugin_info(plugin_id)


def rediscover_all() -> DiscoveryResult:
    """Rediscover all plugins."""
    return _plugin_discovery.rediscover_all()


def get_discovery_stats() -> Dict[str, Any]:
    """Get discovery statistics."""
    return _plugin_discovery.get_discovery_stats()


def get_plugin_discovery() -> PluginDiscovery:
    """Get the global plugin discovery instance."""
    return _plugin_discovery
