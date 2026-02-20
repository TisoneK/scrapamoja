"""
Component discovery system for finding and loading shared components.

This module provides automatic discovery of shared components across the
scraper framework, enabling dynamic component loading and management.
"""

import os
import sys
import importlib
import inspect
from typing import Dict, Any, List, Optional, Type, Set
from pathlib import Path
from datetime import datetime
import json

from src.observability.logger import get_logger
from .component_interface import BaseComponent, BaseProcessor, BaseValidator, BaseFlow

# Module logger
logger = get_logger(__name__)


class ComponentDiscovery:
    """Component discovery system for finding and loading shared components."""
    
    def __init__(self):
        """Initialize component discovery system."""
        self._component_registry: Dict[str, Type[BaseComponent]] = {}
        self._processor_registry: Dict[str, Type[BaseProcessor]] = {}
        self._validator_registry: Dict[str, Type[BaseValidator]] = {}
        self._flow_registry: Dict[str, Type[BaseFlow]] = {}
        
        self._discovered_modules: Set[str] = set()
        self._discovery_timestamps: Dict[str, datetime] = {}
        
        # Search paths for components
        self._search_paths = [
            Path(__file__).parent.parent / 'shared_components',
            Path(__file__).parent.parent / '_template' / 'components',
            Path(__file__).parent.parent / '_template' / 'processors',
            Path(__file__).parent.parent / '_template' / 'validators',
            Path(__file__).parent.parent / '_template' / 'flows'
        ]
    
    async def discover_components(self, force_rediscovery: bool = False) -> Dict[str, Any]:
        """
        Discover all available components in the system.
        
        Args:
            force_rediscovery: Force rediscovery even if components are already discovered
            
        Returns:
            Discovery results with component information
        """
        try:
            discovery_start = datetime.utcnow()
            
            # Clear registries if forcing rediscovery
            if force_rediscovery:
                self._clear_registries()
            
            # Discover components from all search paths
            discovered_components = {}
            
            for search_path in self._search_paths:
                if search_path.exists():
                    path_components = await self._discover_components_in_path(search_path)
                    discovered_components.update(path_components)
            
            # Load component metadata
            component_metadata = await self._load_component_metadata(discovered_components)
            
            discovery_end = datetime.utcnow()
            discovery_duration = (discovery_end - discovery_start).total_seconds()
            
            return {
                'success': True,
                'discovered_components': discovered_components,
                'component_metadata': component_metadata,
                'component_counts': {
                    'total': len(discovered_components),
                    'components': len(self._component_registry),
                    'processors': len(self._processor_registry),
                    'validators': len(self._validator_registry),
                    'flows': len(self._flow_registry)
                },
                'discovery_duration_seconds': discovery_duration,
                'discovery_timestamp': discovery_start.isoformat(),
                'search_paths': [str(p) for p in self._search_paths]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'discovery_timestamp': datetime.utcnow().isoformat()
            }
    
    async def _discover_components_in_path(self, search_path: Path) -> Dict[str, Any]:
        """Discover components in a specific path."""
        try:
            discovered = {}
            
            # Look for Python files
            for py_file in search_path.rglob("*.py"):
                if py_file.name == "__init__.py":
                    continue  # Skip __init__.py files
                
                # Skip test files
                if py_file.name.startswith("test_"):
                    continue
                
                # Skip files in __pycache__
                if "__pycache__" in py_file.parts:
                    continue
                
                # Try to load the module and discover components
                try:
                    module_info = await self._analyze_module_file(py_file)
                    if module_info:
                        discovered.update(module_info)
                except Exception as e:
                    # Log error but continue with other files
                    logger.warning("Failed to analyze module file", file=str(py_file), error=str(e))
            
            return discovered
            
        except Exception as e:
            logger.error("Error discovering components", search_path=str(search_path), error=str(e))
            return {}
    
    async def _analyze_module_file(self, module_file: Path) -> Dict[str, Any]:
        """Analyze a Python module file for components."""
        try:
            # Convert path to module path
            module_path = self._path_to_module_path(module_file)
            if not module_path:
                return {}
            
            # Check if already discovered
            if module_path in self._discovered_modules:
                return {}
            
            # Import the module
            try:
                spec = importlib.util.spec_from_file_location(module_path, module_file)
                module = importlib.util.module_from_spec(spec)
                
                # Analyze module for component classes
                module_info = await self._analyze_module(module, module_path)
                
                # Mark as discovered
                self._discovered_modules.add(module_path)
                self._discovery_timestamps[module_path] = datetime.utcnow()
                
                return module_info
                
            except ImportError as e:
                logger.warning("Failed to import module", module_path=module_path, error=str(e))
                return {}
            
        except Exception as e:
            logger.error("Error analyzing module file", module_file=str(module_file), error=str(e))
            return {}
    
    async def _analyze_module(self, module, module_path: str) -> Dict[str, Any]:
        """Analyze a module for component classes."""
        try:
            module_info = {
                'module_path': module_path,
                'module_name': module.__name__,
                'file_path': str(module.__file__) if hasattr(module, '__file__') else None,
                'components': []
            }
            
            # Get all classes in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Skip imported classes
                if obj.__module__ != module.__name__:
                    continue
                
                # Check if it's a component class
                component_info = await self._analyze_component_class(obj, name, module_path)
                if component_info:
                    module_info['components'].append(component_info)
                    
                    # Register in appropriate registry
                    await self._register_component(obj, component_info)
            
            return module_info
            
        except Exception as e:
            logger.error("Error analyzing module", module_path=module_path, error=str(e))
            return {}
    
    async def _analyze_component_class(self, cls: Type, name: str, module_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a class to determine if it's a component."""
        try:
            # Check if it inherits from base component classes
            base_classes = [BaseComponent, BaseProcessor, BaseValidator, BaseFlow]
            
            component_type = None
            for base_class in base_classes:
                if issubclass(cls, base_class):
                    if base_class == BaseComponent:
                        component_type = 'component'
                    elif base_class == BaseProcessor:
                        component_type = 'processor'
                    elif base_class == BaseValidator:
                        component_type = 'validator'
                    elif base_class == BaseFlow:
                        component_type = 'flow'
                    break
            
            if not component_type:
                return None
            
            # Get component metadata
            metadata = await self._extract_component_metadata(cls)
            
            # Get component configuration
            config = await self._extract_component_configuration(cls)
            
            return {
                'class_name': name,
                'class_type': component_type,
                'module_path': module_path,
                'full_class_name': f"{module_path}.{name}",
                'metadata': metadata,
                'configuration': config,
                'docstring': cls.__doc__,
                'methods': [method for method in dir(cls) if not method.startswith('_')]
            }
            
        except Exception as e:
            logger.error("Error analyzing component class", class_name=name, error=str(e))
            return None
    
    async def _extract_component_metadata(self, cls: Type) -> Dict[str, Any]:
        """Extract metadata from a component class."""
        try:
            metadata = {}
            
            # Look for COMPONENT_METADATA constant
            if hasattr(cls, 'COMPONENT_METADATA'):
                metadata = cls.COMPONENT_METADATA.copy()
            else:
                # Try to extract basic metadata from class attributes
                metadata = {
                    'id': getattr(cls, 'component_id', cls.__name__.lower()),
                    'name': getattr(cls, 'name', cls.__name__),
                    'version': getattr(cls, 'version', '1.0.0'),
                    'type': getattr(cls, 'component_type', 'unknown'),
                    'description': getattr(cls, 'description', cls.__doc__ or ''),
                    'supported_sites': getattr(cls, 'supported_sites', []),
                    'features': getattr(cls, 'features', []),
                    'dependencies': getattr(cls, 'dependencies', []),
                    'configuration_required': getattr(cls, 'configuration_required', []),
                    'optional_configuration': getattr(cls, 'optional_configuration', [])
                }
            
            return metadata
            
        except Exception:
            return {}
    
    async def _extract_component_configuration(self, cls: Type) -> Dict[str, Any]:
        """Extract configuration from a component class."""
        try:
            config = {}
            
            # Look for default configuration
            if hasattr(cls, 'get_default_config'):
                try:
                    if inspect.iscoroutinefunction(cls.get_default_config):
                        config = await cls.get_default_config()
                    else:
                        config = cls.get_default_config()
                except Exception:
                    pass
            
            # Look for configuration schema
            if hasattr(cls, 'get_config_schema'):
                try:
                    if inspect.iscoroutinefunction(cls.get_config_schema):
                        schema = await cls.get_config_schema()
                    else:
                        schema = cls.get_config_schema()
                    config['schema'] = schema
                except Exception:
                    pass
            
            return config
            
        except Exception:
            return {}
    
    async def _register_component(self, cls: Type, component_info: Dict[str, Any]) -> None:
        """Register a component in the appropriate registry."""
        try:
            component_type = component_info['class_type']
            
            if component_type == 'component':
                self._component_registry[component_info['class_name']] = cls
            elif component_type == 'processor':
                self._processor_registry[component_info['class_name']] = cls
            elif component_type == 'validator':
                self._validator_registry[component_info['class_name']] = cls
            elif component_type == 'flow':
                self._flow_registry[component_info['class_name']] = cls
            
        except Exception as e:
            logger.error("Error registering component", class_name=component_info['class_name'], error=str(e))
    
    def _path_to_module_path(self, file_path: Path) -> Optional[str]:
        """Convert a file path to a Python module path."""
        try:
            # Get relative path from project root
            project_root = Path(__file__).parent.parent.parent
            relative_path = file_path.relative_to(project_root)
            
            # Convert to module path
            module_parts = list(relative_path.parts)
            
            # Remove .py extension
            if module_parts[-1].endswith('.py'):
                module_parts[-1] = module_parts[-1][:-3]
            
            # Join with dots
            module_path = '.'.join(module_parts)
            
            return module_path
            
        except Exception:
            return None
    
    async def _load_component_metadata(self, discovered_components: Dict[str, Any]) -> Dict[str, Any]:
        """Load metadata for all discovered components."""
        try:
            metadata = {}
            
            for module_path, module_info in discovered_components.items():
                for component in module_info['components']:
                    component_id = component['metadata'].get('id', component['class_name'])
                    metadata[component_id] = {
                        'class_name': component['class_name'],
                        'module_path': component['module_path'],
                        'full_class_name': component['full_class_name'],
                        'type': component['class_type'],
                        'metadata': component['metadata'],
                        'configuration': component['configuration'],
                        'docstring': component['docstring'],
                        'methods': component['methods']
                    }
            
            return metadata
            
        except Exception as e:
            logger.error("Error loading component metadata", error=str(e))
            return {}
    
    def get_component_class(self, component_id: str, component_type: str = None) -> Optional[Type]:
        """Get a component class by ID and type."""
        try:
            if component_type == 'component' or component_type is None:
                return self._component_registry.get(component_id)
            elif component_type == 'processor':
                return self._processor_registry.get(component_id)
            elif component_type == 'validator':
                return self._validator_registry.get(component_id)
            elif component_type == 'flow':
                return self._flow_registry.get(component_id)
            else:
                return None
        except Exception:
            return None
    
    def get_components_by_type(self, component_type: str) -> Dict[str, Type]:
        """Get all components of a specific type."""
        try:
            if component_type == 'component':
                return self._component_registry.copy()
            elif component_type == 'processor':
                return self._processor_registry.copy()
            elif component_type == 'validator':
                return self._validator_registry.copy()
            elif component_type == 'flow':
                return self._flow_registry.copy()
            else:
                return {}
        except Exception:
            return {}
    
    def get_all_components(self) -> Dict[str, Dict[str, Type]]:
        """Get all components grouped by type."""
        try:
            return {
                'components': self._component_registry.copy(),
                'processors': self._processor_registry.copy(),
                'validators': self._validator_registry.copy(),
                'flows': self._flow_registry.copy()
            }
        except Exception:
            return {}
    
    def search_components(self, query: str, component_type: str = None) -> List[Dict[str, Any]]:
        """Search for components by name, description, or metadata."""
        try:
            results = []
            all_components = self.get_all_components()
            
            search_types = [component_type] if component_type else ['component', 'processor', 'validator', 'flow']
            
            for comp_type in search_types:
                if comp_type not in all_components:
                    continue
                
                for component_id, component_class in all_components[comp_type].items():
                    # Get component metadata
                    metadata = {}
                    if hasattr(component_class, 'COMPONENT_METADATA'):
                        metadata = component_class.COMPONENT_METADATA
                    
                    # Search in name, description, and metadata
                    search_text = query.lower()
                    
                    # Check component ID
                    if search_text in component_id.lower():
                        results.append({
                            'component_id': component_id,
                            'component_type': comp_type,
                            'class_name': component_class.__name__,
                            'module_path': component_class.__module__,
                            'metadata': metadata,
                            'match_type': 'id'
                        })
                        continue
                    
                    # Check metadata
                    if metadata:
                        # Search in name
                        if search_text in metadata.get('name', '').lower():
                            results.append({
                                'component_id': component_id,
                                'component_type': comp_type,
                                'class_name': component_class.__name__,
                                'module_path': component_class.__module__,
                                'metadata': metadata,
                                'match_type': 'name'
                            })
                            continue
                        
                        # Search in description
                        if search_text in metadata.get('description', '').lower():
                            results.append({
                                'component_id': component_id,
                                'component_type': comp_type,
                                'class_name': component_class.__name__,
                                'module_path': component_class.__module__,
                                'metadata': metadata,
                                'match_type': 'description'
                            })
                            continue
                        
                        # Search in features
                        features = metadata.get('features', [])
                        for feature in features:
                            if search_text in feature.lower():
                                results.append({
                                    'component_id': component_id,
                                    'component_type': comp_type,
                                    'class_name': component_class.__name__,
                                    'module_path': component_class.__module__,
                                    'metadata': metadata,
                                    'match_type': 'feature'
                                })
                                break
                    
                    # Check docstring
                    if component_class.__doc__ and search_text in component_class.__doc__.lower():
                        results.append({
                            'component_id': component_id,
                            'component_type': comp_type,
                            'class_name': component_class.__name__,
                            'module_path': component_class.__module__,
                            'metadata': metadata,
                            'match_type': 'docstring'
                        })
            
            return results
            
        except Exception as e:
            logger.error("Error searching components", error=str(e))
            return []
    
    def get_component_info(self, component_id: str, component_type: str = None) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific component."""
        try:
            component_class = self.get_component_class(component_id, component_type)
            if not component_class:
                return None
            
            # Get metadata
            metadata = {}
            if hasattr(component_class, 'COMPONENT_METADATA'):
                metadata = component_class.COMPONENT_METADATA
            
            # Get configuration
            config = {}
            if hasattr(component_class, 'get_default_config'):
                if inspect.iscoroutinefunction(component_class.get_default_config):
                    # For async methods, we can't easily call them here without an event loop
                    try:
                        import asyncio
                        config = asyncio.run(component_class.get_default_config())
                    except:
                        config = {}
                else:
                    config = component_class.get_default_config()
            
            # Get methods
            methods = []
            for method_name in dir(component_class):
                if not method_name.startswith('_'):
                    method = getattr(component_class, method_name)
                    if callable(method):
                        methods.append({
                            'name': method_name,
                            'signature': str(inspect.signature(method)),
                            'docstring': method.__doc__
                        })
            
            return {
                'component_id': component_id,
                'component_type': component_type,
                'class_name': component_class.__name__,
                'module_path': component_class.__module__,
                'metadata': metadata,
                'configuration': config,
                'methods': methods,
                'docstring': component_class.__doc__
            }
            
        except Exception as e:
            logger.error("Error getting component info", component_id=component_id, error=str(e))
            return None
    
    def _clear_registries(self) -> None:
        """Clear all component registries."""
        self._component_registry.clear()
        self._processor_registry.clear()
        self._validator_registry.clear()
        self._flow_registry.clear()
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery statistics."""
        try:
            return {
                'discovered_modules_count': len(self._discovered_modules),
                'discovered_modules': list(self._discovered_modules),
                'discovery_timestamps': {
                    module: timestamp.isoformat()
                    for module, timestamp in self._discovery_timestamps.items()
                },
                'registry_counts': {
                    'components': len(self._component_registry),
                    'processors': len(self._processor_registry),
                    'validators': len(self._validator_registry),
                    'flows': len(self._flow_registry)
                },
                'search_paths': [str(p) for p in self._search_paths]
            }
        except Exception:
            return {}


# Global component discovery instance
_component_discovery = ComponentDiscovery()


# Convenience functions
async def discover_components(force_rediscovery: bool = False) -> Dict[str, Any]:
    """Discover all components in the system."""
    return await _component_discovery.discover_components(force_rediscovery)


def get_component(component_id: str, component_type: str = None) -> Optional[Type]:
    """Get a component class by ID and type."""
    return _component_discovery.get_component_class(component_id, component_type)


def get_components_by_type(component_type: str) -> Dict[str, Type]:
    """Get all components of a specific type."""
    return _component_discovery.get_components_by_type(component_type)


def search_components(query: str, component_type: str = None) -> List[Dict[str, Any]]:
    """Search for components by name, description, or metadata."""
    return _component_discovery.search_components(query, component_type)


def get_component_info(component_id: str, component_type: str = None) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific component."""
    return _component_discovery.get_component_info(component_id, component_type)


def get_all_components() -> Dict[str, Dict[str, Type]]:
    """Get all components grouped by type."""
    return _component_discovery.get_all_components()


def get_discovery_stats() -> Dict[str, Any]:
    """Get discovery statistics."""
    return _component_discovery.get_discovery_stats()
