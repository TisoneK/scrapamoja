"""
Component metadata management system for the component framework.

This module provides metadata management functionality for components, including
metadata extraction, validation, and management utilities.
"""

from typing import Dict, Any, Optional, List, Type, Set
from datetime import datetime
import json
from pathlib import Path

from .component_interface import BaseComponent
from .component_discovery import get_component_info, get_all_components


class ComponentMetadataManager:
    """Component metadata management system."""
    
    def __init__(self):
        """Initialize component metadata manager."""
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._metadata_timestamps: Dict[str, datetime] = {}
        self._validation_rules: Dict[str, List[Dict[str, Any]]] = {}
        
        # Default validation rules
        self._default_validation_rules = [
            {
                'name': {
                    'required': True,
                    'type': 'string',
                    'min_length': 1,
                    'max_length': 100
                },
                'id': {
                    'required': True,
                    'type': 'string',
                    'pattern': r'^[ a-zA-Z0-9_-]+$'
                },
                'version': {
                    'required': True,
                    'type': 'string',
                    'pattern': r'^\d+\.\d+\.\d+$'
                },
                'type': {
                    'required': True,
                    'type': 'string',
                    'enum': ['component', 'processor', 'validator', 'flow']
                },
                'description': {
                    'required': False,
                    'type': 'string',
                    'max_length': 500
                },
                'supported_sites': {
                    'required': False,
                    'type': 'list',
                    'items': {'type': 'string'}
                },
                'features': {
                    'required': False,
                    'type': 'list',
                    'items': {'type': 'string'}
                },
                'dependencies': {
                    'required': False,
                    'type': 'list',
                    'items': {'type': 'string'}
                },
                'configuration_required': {
                    'required': False,
                    'type': 'list',
                    'items': {'type': 'string'}
                },
                'optional_configuration': {
                    'required': False,
                    'type': 'list',
                    'items': {'type': 'string'}
                }
            }
        ]
    
    async def extract_metadata(self, component_class: Type, component_id: str = None) -> Dict[str, Any]:
        """Extract metadata from a component class."""
        try:
            # If component_id is provided, check if it matches the class
            if component_id and component_class.__name__ != component_id:
                return {}
            
            metadata = {}
            
            # Extract from class attributes
            if hasattr(component_class, 'COMPONENT_METADATA'):
                metadata.update(component_class.COMPONENT_METADATA)
            
            # Extract from class docstring
            if component_class.__doc__:
                metadata['docstring'] = component_class.__doc__
            
            # Extract from class attributes
            if hasattr(component_class, 'component_id'):
                metadata['id'] = component_class.component_id
            if hasattr(component_class, 'name'):
                metadata['name'] = component_class.name
            if hasattr(component_class, 'version'):
                metadata['version'] = component_class.version
            if hasattr(component_class, 'component_type'):
                metadata['type'] = component_class.component_type
            if hasattr(component_class, 'description'):
                metadata['description'] = component_class.description
            if hasattr(component_class, 'supported_sites'):
                metadata['supported_sites'] = component_class.supported_sites
            if hasattr(component_class, 'features'):
                metadata['features'] = component_class.features
            if hasattr(component_class, 'dependencies'):
                metadata['dependencies'] = component_class.dependencies
            if hasattr(component_class, 'configuration_required'):
                metadata['configuration_required'] = component_class.configuration_required
            if hasattr(component_class, 'optional_configuration'):
                metadata['optional_configuration'] = component_class.optional_configuration
            
            # Extract from class methods
            methods = []
            for method_name in dir(component_class):
                if not method_name.startswith('_'):
                    method = getattr(component_class, method_name)
                    if callable(method):
                        methods.append({
                            'name': method_name,
                            'signature': str(method.__signature__) if hasattr(method, '__signature__') else '',
                            'docstring': method.__doc__ if hasattr(method, '__doc__') else ''
                        })
            
            metadata['methods'] = methods
            
            # Add class information
            metadata['class_name'] = component_class.__name__
            metadata['module_path'] = component_class.__module__
            metadata['file_path'] = component_class.__file__ if hasattr(component_class, '__file__') else ''
            
            # Add extraction timestamp
            metadata['extracted_at'] = datetime.utcnow().isoformat()
            
            return metadata
            
        except Exception as e:
            print(f"Error extracting metadata for {component_class.__name__}: {str(e)}")
            return {}
    
    def validate_metadata(self, metadata: Dict[str, Any], component_id: str = None) -> Dict[str, Any]:
        """Validate component metadata against validation rules."""
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Apply validation rules
            for rule_name, rule in self._validation_rules:
                if rule_name not in metadata:
                    if rule['required']:
                        validation_result['errors'].append(f"Missing required field: {rule_name}")
                    continue
                
                field_value = metadata.get(rule_name)
                rule_type = rule['type']
                
                # Type validation
                if rule_type == 'string':
                    if not isinstance(field_value, str):
                        validation_result['errors'].append(f"Field {rule_name} must be a string")
                    elif len(field_value) < rule.get('min_length', 0):
                        validation_result['errors'].append(f"Field {rule_name} must be at least {rule['min_length']} characters")
                    elif len(field_value) > rule.get('max_length', 1000):
                        validation_result['errors'].append(f"Field {rule_name} must be at most {rule['max_length']} characters")
                elif rule.get('pattern') and not self._match_pattern(field_value, rule['pattern']):
                        validation_result['errors'].append(f"Field {rule_name} does not match pattern: {rule['pattern']}")
                
                elif rule_type == 'list':
                    if not isinstance(field_value, list):
                        validation_result['errors'].append(f"Field {rule_name} must be a list")
                    elif rule.get('items') and field_value:
                        for item in field_value:
                            if not isinstance(item, str):
                                validation_result['errors'].append(f"Field {rule_name} items must be strings")
                
                elif rule_type == 'enum':
                    if field_value not in rule.get('enum', []):
                        validation_result['errors'].append(f"Field {rule_name} must be one of: {rule['enum']}")
                
                elif rule_type == 'bool':
                    if not isinstance(field_value, bool):
                        validation_result['errors']. append(f"Field {rule_name} must be a boolean")
            
            # Add warnings for recommended fields
            recommended_fields = ['name', 'description', 'supported_sites', 'features']
            for field in recommended_fields:
                if field not in metadata:
                    validation_result['warnings'].append(f"Recommended field not found: {field}")
            
            validation_result['component_id'] = component_id
            validation_result['validation_timestamp'] = datetime.utcnow().isoformat()
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'validation_timestamp': datetime.utcnow().isoformat()
            }
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """Check if a value matches a regex pattern."""
        try:
            import re
            return bool(re.match(pattern, value))
        except Exception:
            return False
    
    def cache_metadata(self, component_id: str, metadata: Dict[str, Any]) -> None:
        """Cache metadata for a component."""
        try:
            self._metadata_cache[component_id] = metadata
            self._metadata_timestamps[component_id] = datetime.utcnow()
        except Exception as e:
            print(f"Error caching metadata for {component_id}: {str(e)}")
    
    def get_cached_metadata(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get cached metadata for a component."""
        return self._metadata_cache.get(component_id)
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached metadata."""
        return self._metadata_cache.copy()
    
    def get_metadata_by_type(self, component_type: str) -> Dict[str, Dict[str, Any]]:
        """Get all metadata for components of a specific type."""
        try:
            all_components = get_all_components()
            type_metadata = {}
            
            for component_id, component_class in all_components.get(component_type, {}).items():
                metadata = self.get_cached_metadata(component_id)
                if metadata:
                    type_metadata[component_id] = metadata
            
            return type_metadata
            
        except Exception:
            return {}
    
    def search_metadata(self, query: str, component_type: str = None, 
                      metadata_type: str = None) -> List[Dict[str, Any]]:
        """Search metadata by query and type."""
        try:
            all_metadata = self.get_all_metadata()
            results = []
            
            for component_id, metadata in all_metadata.items():
                # Filter by component type if specified
                if component_type and metadata.get('type') != component_type:
                    continue
                
                # Filter by metadata type if specified
                if metadata_type and metadata_type not in metadata:
                    continue
                
                # Search in all fields
                search_text = query.lower()
                match_found = False
                
                for field_name, field_value in metadata.items():
                    if search_text in str(field_value).lower():
                        match_found = True
                        break
                
                if match_found:
                    results.append({
                        'component_id': component_id,
                        'metadata': metadata,
                        'match_fields': [field_name for field_name, field_value in metadata.items() if search_text in str(field_value).lower()],
                        'match_type': metadata_type or 'all'
                    })
            
            return results
            
        except Exception:
            return []
    
    def update_metadata(self, component_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update metadata for a component."""
        try:
            if component_id in self._metadata_cache:
                self._metadata_cache[component_id].update(updates)
                self._metadata_timestamps[component_id] = datetime.utcnow()
            
            return self.get_cached_metadata(component_id)
            
        except Exception as e:
            print(f"Error updating metadata for {component_id}: {str(e)}")
            return {}
    
    def delete_metadata(self, component_id: str) -> bool:
        """Delete cached metadata for a component."""
        try:
            if component_id in self._metadata_cache:
                    del self._metadata_cache[component_id]
                    if component_id in self._metadata_timestamps:
                        del self._metadata_timestamps[component_id]
                    return True
            return False
            
        except Exception:
            return False
    
    def get_metadata_age(self, component_id: str) -> Optional[timedelta]:
        """Get age of cached metadata."""
        try:
            if component_id in self._metadata_timestamps:
                return datetime.utcnow() - self._metadata_timestamps[component_id]
            return None
            
        except Exception:
            return None
    
    def cleanup_expired_metadata(self, max_age_days: int = 30) -> int:
        """Clean up expired metadata."""
        try:
            expired_count = 0
            current_time = datetime.utcnow()
            
            expired_components = []
            for component_id, timestamp in self._metadata_timestamps.items():
                age = current_time - timestamp
                if age.days > max_age_days:
                    expired_components.append(component_id)
            
            for component_id in expired_components:
                self.delete_metadata(component_id)
            
            return expired_count
            
        except Exception:
            return 0
    
    def export_metadata(self, format: str = 'json') -> str:
        """Export all metadata to specified format."""
        try:
            if format == 'json':
                return json.dumps(self._metadata_cache, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            return f"Error exporting metadata: {str(e)}"
    
    def get_metadata_stats(self) -> Dict[str, Any]:
        """Get metadata statistics."""
        try:
            return {
                'total_components': len(self._metadata_cache),
                'cached_components': list(self._metadata_cache.keys()),
                'cache_timestamps': {
                    component_id: timestamp.isoformat()
                    for component_id, timestamp in self._metadata_timestamps.items()
                },
                'oldest_timestamp': min(self._metadata_timestamps.values()) if self._metadata_timestamps else None,
                'newest_timestamp': max(self._metadata_timestamps.values()) if self._metadata_timestamps else None
            }
            
        except Exception:
            return {}
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        try:
            return {
                'validation_rules_count': len(self._validation_rules),
                'validation_rules': self._validation_rules
            }
        except Exception:
            return {}


# Global metadata manager instance
_metadata_manager = ComponentMetadataManager()


# Convenience functions
def extract_metadata(component_class: Type, component_id: str = None) -> Dict[str, Any]:
    """Extract metadata from a component class."""
    return _metadata_manager.extract_metadata(component_class, component_id)


def validate_metadata(metadata: Dict[str, Any], component_id: str = None) -> Dict[str, Any]:
    """Validate component metadata."""
    return _metadata_manager.validate_metadata(metadata, component_id)


def get_metadata(component_id: str) -> Optional[Dict[str, Any]]:
    """Get cached metadata for a component."""
    return _metadata_manager.get_cached_metadata(component_id)


def get_all_metadata() -> Dict[str, Dict[str, Any]]:
    """Get all cached metadata."""
    return _metadata_manager.get_all_metadata()


def search_metadata(query: str, component_type: str = None, metadata_type: str = None) -> List[Dict[str, Any]]:
    """Search metadata by query and type."""
    return _metadata_manager.search_metadata(query, component_type, metadata_type)


def update_metadata(component_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update metadata for a component."""
    return _metadata_manager.update_metadata(component_id, updates)


def delete_metadata(component_id: str) -> bool:
    """Delete cached metadata for a component."""
    return _metadata_manager.delete_metadata(component_id)


def export_metadata(format: str = 'json') -> str:
    """Export all metadata to specified format."""
    return _metadata_manager.export_metadata(format)


def get_metadata_stats() -> Dict[str, Any]:
    """Get metadata statistics."""
    return _metadata_manager.get_metadata_stats()


def cleanup_expired_metadata(max_age_days: int = 30) -> int:
    """Clean up expired metadata."""
    return _metadata_manager.cleanup_expired_metadata(max_age_days)


# Factory functions for creating component instances with metadata
def create_component_with_metadata(component_class: Type, component_id: str = None) -> Type:
    """Create a component instance with metadata extraction."""
    async def create_instance():
        component = component_class()
        
        # Extract and cache metadata
        metadata = await _metadata_manager.extract_metadata(component_class, component_id)
        if metadata:
            # Set metadata as attribute
            component._metadata = metadata
        
        return component
    
    return create_instance


# Component factory with metadata extraction
def create_component_with_metadata_sync(component_class: Type, component_id: str = None) -> Type:
    """Create a component instance with metadata extraction (synchronous)."""
    component = component_class()
    
    # Extract and cache metadata
    metadata = _metadata_manager.extract_metadata(component_class, component_id)
    if metadata:
        # Set metadata as attribute
        component._metadata = metadata
    
    return component
