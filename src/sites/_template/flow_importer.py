"""
Flow import utilities for hybrid patterns and dynamic flow loading.

This module provides utilities for importing flows from different architectural patterns,
supporting both traditional flat imports and hierarchical domain-based imports.
"""

import os
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Union
import logging
from .flow_discovery import FlowDiscovery

logger = logging.getLogger(__name__)


class FlowImporter:
    """Advanced flow importer supporting hybrid patterns and dynamic loading."""
    
    def __init__(self, base_path: str, pattern: str = 'standard'):
        """
        Initialize flow importer.
        
        Args:
            base_path: Base path for flow discovery
            pattern: Pattern type for import strategy
        """
        self.base_path = Path(base_path)
        self.pattern = pattern
        self.discovery = FlowDiscovery(base_path)
        self.import_cache = {}
        self.flow_registry = {}
        
        # Discover flows based on pattern
        self.discovered_flows = self.discovery.discover_flows(pattern)
        self._build_flow_registry()
    
    def _build_flow_registry(self) -> None:
        """Build flow registry from discovered flows."""
        self.flow_registry = {}
        
        if self.pattern == 'simple':
            # Simple pattern: main flow only
            if 'main' in self.discovered_flows:
                main_flow_info = self.discovered_flows['main']
                for class_name in main_flow_info.get('classes', []):
                    self.flow_registry[class_name] = {
                        'class_name': class_name,
                        'module_path': main_flow_info['path'],
                        'flow_type': 'main',
                        'domain': None
                    }
        
        elif self.pattern == 'standard':
            # Standard pattern: main flow + additional flows
            if 'main' in self.discovered_flows:
                main_flow_info = self.discovered_flows['main']
                for class_name in main_flow_info.get('classes', []):
                    self.flow_registry[class_name] = {
                        'class_name': class_name,
                        'module_path': main_flow_info['path'],
                        'flow_type': 'main',
                        'domain': None
                    }
            
            # Additional flows
            for flow_name, flow_info in self.discovered_flows.items():
                if flow_name != 'main':
                    for class_name in flow_info.get('classes', []):
                        self.flow_registry[class_name] = {
                            'class_name': class_name,
                            'module_path': flow_info['path'],
                            'flow_type': 'additional',
                            'domain': None
                        }
        
        elif self.pattern == 'complex':
            # Complex pattern: domain-based flows
            domains = self.discovered_flows.get('domains', {})
            
            for domain_name, domain_flows in domains.items():
                for flow_name, flow_info in domain_flows.items():
                    for class_name in flow_info.get('classes', []):
                        full_name = f"{domain_name}.{flow_name}"
                        self.flow_registry[full_name] = {
                            'class_name': class_name,
                            'module_path': flow_info['path'],
                            'flow_type': 'domain',
                            'domain': domain_name,
                            'hierarchical_name': full_name
                        }
        
        elif self.pattern == 'legacy':
            # Legacy pattern: flat flows structure
            for flow_name, flow_info in self.discovered_flows.items():
                for class_name in flow_info.get('classes', []):
                    self.flow_registry[class_name] = {
                        'class_name': class_name,
                        'module_path': flow_info['path'],
                        'flow_type': 'legacy',
                        'domain': None
                    }
        
        logger.info(f"Built flow registry with {len(self.flow_registry)} entries for {self.pattern} pattern")
    
    def import_flow(self, flow_name: str, lazy: bool = False) -> Type:
        """
        Import a flow class dynamically.
        
        Args:
            flow_name: Name of the flow to import
            lazy: Whether to import lazily (cache the module)
            
        Returns:
            Imported flow class
            
        Raises:
            ImportError: If flow cannot be imported
        """
        if flow_name in self.import_cache:
            return self.import_cache[flow_name]
        
        if flow_name not in self.flow_registry:
            raise ImportError(f"Flow '{flow_name}' not found in registry")
        
        flow_info = self.flow_registry[flow_name]
        module_path = flow_info['module_path']
        
        try:
            if lazy:
                # Lazy import: cache the module
                if module_path not in sys.modules:
                    spec = importlib.util.spec_from_file_location(str(module_path))
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_path] = module
                    self.import_cache[flow_name] = module
                    return getattr(module, flow_info['class_name'])
                else:
                    return importlib.import_module(module_path)
            else:
                # Eager import
                spec = importlib.util.spec_from_file_location(str(module_path))
                module = importlib.util.module_from_spec(spec)
                return getattr(module, flow_info['class_name'])
                
        except Exception as e:
            logger.error(f"Failed to import flow '{flow_name}': {e}")
            raise ImportError(f"Could not import flow '{flow_name}': {e}")
    
    def import_domain_flows(self, domain: str) -> Dict[str, Type]:
        """
        Import all flows from a specific domain.
        
        Args:
            domain: Domain name to import flows from
            
        Returns:
            Dictionary of flow name -> flow class
        """
        domain_flows = {}
        
        for flow_name, flow_info in self.flow_registry.items():
            if flow_info.get('domain') == domain:
                try:
                    flow_class = self.import_flow(flow_name)
                    domain_flows[flow_name] = flow_class
                except ImportError as e:
                    logger.warning(f"Failed to import {flow_name} from {domain} domain: {e}")
        
        return domain_flows
    
    def import_all_flows(self) -> Dict[str, Type]:
        """
        Import all discovered flows.
        
        Returns:
            Dictionary of flow name -> flow class
        """
        all_flows = {}
        
        for flow_name in self.flow_registry.keys():
            try:
                flow_class = self.import_flow(flow_name)
                all_flows[flow_name] = flow_class
            except ImportError as e:
                logger.warning(f"Failed to import flow '{flow_name}': {e}")
        
        return all_flows
    
    def get_flow_info(self, flow_name: str) -> Dict[str, Any]:
        """
        Get information about a specific flow.
        
        Args:
            flow_name: Name of the flow
            
        Returns:
            Flow information dictionary
        """
        return self.flow_registry.get(flow_name, {})
    
    def list_available_flows(self) -> List[str]:
        """
        List all available flow names.
        
        Returns:
            List of flow names
        """
        return list(self.flow_registry.keys())
    
    def list_flows_by_type(self, flow_type: str) -> List[str]:
        """
        List flows by type (main, additional, domain, legacy).
        
        Args:
            flow_type: Type of flows to list
            
        Returns:
            List of flow names
        """
        return [
            flow_name for flow_name, flow_info in self.flow_registry.items()
            if flow_info.get('flow_type') == flow_type
        ]
    
    def list_flows_by_domain(self, domain: str) -> List[str]:
        """
        List flows by domain.
        
        Args:
            domain: Domain name to filter flows
            
        Returns:
            List of flow names in the domain
        """
        return [
            flow_name for flow_name, flow_info in self.flow_registry.items()
            if flow_info.get('domain') == domain
        ]
    
    def get_hierarchical_flows(self) -> Dict[str, Dict[str, Type]]:
        """
        Get flows organized by domain hierarchy.
        
        Returns:
            Dictionary of domain -> {flow_name: flow_class}
        """
        hierarchy = {}
        
        for flow_name, flow_info in self.flow_registry.items():
            domain = flow_info.get('domain')
            if domain:
                if domain not in hierarchy:
                    hierarchy[domain] = {}
                hierarchy[domain][flow_name] = flow_info['class_name']
        
        return hierarchy
    
    def validate_imports(self) -> Dict[str, Any]:
        """
        Validate all flow imports for potential issues.
        
        Returns:
            Validation results
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'missing_flows': [],
            'failed_imports': []
        }
        
        # Check for missing expected flows
        if self.pattern == 'simple':
            expected_flows = ['main']
        elif self.pattern == 'standard':
            expected_flows = ['main']  # Additional flows are optional
        elif self.pattern == 'complex':
            # Complex pattern should have domain flows
            domains = set()
            for flow_info in self.flow_registry.values():
                if flow_info.get('domain'):
                    domains.add(flow_info['domain'])
            
            expected_domains = ['navigation', 'extraction']
            missing_domains = [d for d in expected_domains if d not in domains]
            if missing_domains:
                validation_result['warnings'].append(f"Missing expected domains: {', '.join(missing_domains)}")
            
            # Check for flows in missing domains
            for domain in missing_domains:
                domain_flows = self.list_flows_by_domain(domain)
                if not domain_flows:
                    validation_result['missing_flows'].extend([
                        f"{domain}.{flow}" for flow in ['match_nav', 'live_nav', 'competition_nav']
                    ])
                else:
                    validation_result['missing_flows'].extend([
                        f"{domain}.{flow}" for flow in ['match_extract', 'odds_extract', 'stats_extract']
                    ])
        
        # Check for import failures
        for flow_name in self.flow_registry.keys():
            try:
                self.import_flow(flow_name)
            except ImportError as e:
                validation_result['failed_imports'].append(f"{flow_name}: {e}")
        
        if validation_result['failed_imports']:
            validation_result['valid'] = False
        
        return validation_result
    
    def generate_import_code(self, output_file: str = None) -> str:
        """
        Generate import code for the current pattern.
        
        Args:
            output_file: Optional file to write code to
            
        Returns:
            Generated import code
        """
        imports = []
        
        if self.pattern == 'simple':
            imports.append("from .flow import *")
        
        elif self.pattern == 'standard':
            if 'main' in self.discovered_flows:
                imports.append("from .flow import *")
            
            for flow_name in self.discovered_flows.keys():
                if flow_name != 'main':
                    imports.append(f"from .flows.{flow_name} import *")
        
        elif self.pattern == 'complex':
            # Domain-based imports
            domains = set()
            for flow_info in self.flow_registry.values():
                if flow_info.get('domain'):
                    domains.add(flow_info['domain'])
            
            for domain in domains:
                imports.append(f"from .flows.{domain} import *")
        
        elif self.pattern == 'legacy':
            for flow_name in self.discovered_flows.keys():
                imports.append(f"from .flows.{flow_name} import *")
        
        code = '\n'.join(imports)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(code)
            logger.info(f"Generated import code for {self.pattern} pattern: {output_file}")
        
        return code
    
    def create_flow_manager(self) -> 'FlowManager':
        """
        Create a flow manager instance for the current pattern.
        
        Returns:
            FlowManager instance
        """
        return FlowManager(self)
    
    def reload_flows(self) -> None:
        """Reload all flows by clearing cache and rebuilding registry."""
        logger.info("Reloading flows...")
        
        # Clear cache
        self.import_cache.clear()
        
        # Re-discover and rebuild
        self.discovered_flows = self.discovery.discover_flows(self.pattern)
        self._build_flow_registry()
        
        logger.info(f"Reloaded {len(self.flow_registry)} flows for {self.pattern} pattern")


class FlowManager:
    """Manager class for handling flows with different patterns."""
    
    def __init__(self, importer: FlowImporter):
        """
        Initialize flow manager.
        
        Args:
            importer: FlowImporter instance
        """
        self.importer = importer
        self._flows = {}
        self._domains = {}
        
        # Import all flows
        self._load_all_flows()
    
    def _load_all_flows(self) -> None:
        """Load all flows using the importer."""
        try:
            all_flows = self.importer.import_all_flows()
            self._flows = all_flows
            
            # Organize by domain for complex patterns
            if self.importer.pattern == 'complex':
                self._domains = self.importer.get_hierarchical_flows()
            
            logger.info(f"Loaded {len(all_flows)} flows")
            
        except Exception as e:
            logger.error(f"Failed to load flows: {e}")
    
    def get_flow(self, flow_name: str) -> Optional[Type]:
        """
        Get a specific flow by name.
        
        Args:
            flow_name: Name of the flow
            
        Returns:
            Flow class or None if not found
        """
        return self._flows.get(flow_name)
    
    def get_domain_flows(self, domain: str) -> Dict[str, Type]:
        """
        Get all flows in a specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Dictionary of flow name -> flow class
        """
        if self.importer.pattern == 'complex':
            return self._domains.get(domain, {})
        else:
            # For non-complex patterns, filter by domain if available
            domain_flows = {}
            for flow_name, flow_class in self._flows.items():
                flow_info = self.importer.get_flow_info(flow_name)
                if flow_info.get('domain') == domain:
                    domain_flows[flow_name] = flow_class
            
            return domain_flows
        
        return {}
    
    def list_flows(self) -> List[str]:
        """List all available flow names."""
        return list(self._flows.keys())
    
    def list_domains(self) -> List[str]:
        """List all available domains (complex pattern only)."""
        return list(self._domains.keys())
    
    def validate_flows(self) -> Dict[str, Any]:
        """Validate all loaded flows."""
        return self.importer.validate_imports()
    
    def reload(self) -> None:
        """Reload all flows."""
        self.importer.reload_flows()
        self._load_all_flows()


def create_flow_importer(base_path: str, pattern: str = 'standard') -> FlowImporter:
    """
    Convenience function to create a flow importer.
    
    Args:
        base_path: Base path for flow discovery
        pattern: Pattern type for import strategy
        
    Returns:
        FlowImporter instance
    """
    return FlowImporter(base_path, pattern)


def import_flows_from_pattern(base_path: str, pattern: str = 'standard') -> FlowManager:
    """
    Convenience function to create a flow manager and import flows.
    
    Args:
        base_path: Base path for flow discovery
        pattern: Pattern type for import strategy
        
    Returns:
        FlowManager instance with loaded flows
    """
    importer = FlowImporter(base_path, pattern)
    return FlowManager(importer)
