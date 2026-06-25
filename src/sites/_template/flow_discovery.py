"""
Flow discovery utilities for recursive subfolder scanning and hierarchical flow organization.

This module provides utilities for discovering flows in complex directory structures,
supporting both flat and hierarchical flow organization patterns.
"""

import os
import importlib
import inspect
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
import logging

logger = logging.getLogger(__name__)


class FlowDiscovery:
    """Advanced flow discovery with recursive scanning and hierarchical organization."""
    
    def __init__(self, base_path: str):
        """
        Initialize flow discovery.
        
        Args:
            base_path: Base path for flow discovery
        """
        self.base_path = Path(base_path)
        self.discovered_flows = {}
        self.hierarchy = {}
    
    def discover_flows(self, pattern: str = 'standard') -> Dict[str, Any]:
        """
        Discover flows based on pattern type.
        
        Args:
            pattern: Pattern type ('simple', 'standard', 'complex', 'legacy')
            
        Returns:
            Dictionary of discovered flows with metadata
        """
        if pattern == 'simple':
            return self._discover_simple_flows()
        elif pattern == 'standard':
            return self._discover_standard_flows()
        elif pattern == 'complex':
            return self._discover_complex_flows()
        elif pattern == 'legacy':
            return self._discover_legacy_flows()
        else:
            logger.warning(f"Unknown pattern: {pattern}, using standard discovery")
            return self._discover_standard_flows()
    
    def _discover_simple_flows(self) -> Dict[str, Any]:
        """Discover flows for simple pattern (single flow.py)."""
        flows = {}
        
        # Look for main flow.py
        flow_file = self.base_path / 'flow.py'
        if flow_file.exists():
            flow_info = self._analyze_flow_file(flow_file)
            flows['main'] = flow_info
        
        return {
            'pattern': 'simple',
            'flows': flows,
            'hierarchy': {'main': flow_file}
        }
    
    def _discover_standard_flows(self) -> Dict[str, Any]:
        """Discover flows for standard pattern (flow.py + flows/)."""
        flows = {}
        hierarchy = {}
        
        # Main flow.py
        flow_file = self.base_path / 'flow.py'
        if flow_file.exists():
            flow_info = self._analyze_flow_file(flow_file)
            flows['main'] = flow_info
            hierarchy['main'] = flow_file
        
        # Flows directory
        flows_dir = self.base_path / 'flows'
        if flows_dir.exists():
            flows_hierarchy = self._discover_flows_directory(flows_dir)
            flows.update(flows_hierarchy['flows'])
            hierarchy.update(flows_hierarchy['hierarchy'])
        
        return {
            'pattern': 'standard',
            'flows': flows,
            'hierarchy': hierarchy
        }
    
    def _discover_complex_flows(self) -> Dict[str, Any]:
        """Discover flows for complex pattern (domain-separated flows)."""
        flows = {}
        hierarchy = {}
        
        # Flows directory with domain subfolders
        flows_dir = self.base_path / 'flows'
        if flows_dir.exists():
            # Discover domain-based flows
            domain_flows = self._discover_domain_flows(flows_dir)
            flows.update(domain_flows['flows'])
            hierarchy.update(domain_flows['hierarchy'])
        
        return {
            'pattern': 'complex',
            'flows': flows,
            'hierarchy': hierarchy,
            'domains': domain_flows.get('domains', {})
        }
    
    def _discover_legacy_flows(self) -> Dict[str, Any]:
        """Discover flows for legacy pattern (flat flows/)."""
        flows = {}
        hierarchy = {}
        
        # Flows directory (flat structure)
        flows_dir = self.base_path / 'flows'
        if flows_dir.exists():
            flows_hierarchy = self._discover_flows_directory(flows_dir)
            flows.update(flows_hierarchy['flows'])
            hierarchy.update(flows_hierarchy['hierarchy'])
        
        return {
            'pattern': 'legacy',
            'flows': flows,
            'hierarchy': hierarchy
        }
    
    def _discover_flows_directory(self, flows_dir: Path) -> Dict[str, Any]:
        """Discover all flows in a directory recursively."""
        flows = {}
        hierarchy = {}
        
        for item in flows_dir.iterdir():
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            
            if item.is_file() and item.suffix == '.py':
                # Direct Python file in flows/
                flow_name = item.stem
                flow_info = self._analyze_flow_file(item)
                flows[flow_name] = flow_info
                hierarchy[flow_name] = item
                
            elif item.is_dir():
                # Subdirectory (could be domain or just organization)
                subflows = self._discover_flows_directory(item)
                flows.update(subflows['flows'])
                hierarchy[item.name] = {
                    'type': 'directory',
                    'path': item,
                    'flows': subflows['hierarchy']
                }
        
        return {
            'flows': flows,
            'hierarchy': hierarchy
        }
    
    def _discover_domain_flows(self, flows_dir: Path) -> Dict[str, Any]:
        """Discover domain-separated flows for complex pattern."""
        flows = {}
        hierarchy = {}
        domains = {}
        
        # Standard domain directories
        expected_domains = ['navigation', 'extraction', 'filtering', 'authentication']
        
        for item in flows_dir.iterdir():
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            
            if item.is_dir():
                domain_name = item.name
                domain_info = {
                    'type': 'domain',
                    'path': item,
                    'flows': {}
                }
                
                # Discover flows in this domain directory
                for flow_file in item.glob('*.py'):
                    if flow_file.name == '__init__.py':
                        continue
                    
                    flow_name = flow_file.stem
                    flow_info = self._analyze_flow_file(flow_file)
                    flows[f"{domain_name}.{flow_name}"] = flow_info
                    domain_info['flows'][flow_name] = flow_file
                
                hierarchy[domain_name] = domain_info
                domains[domain_name] = domain_info['flows']
        
        return {
            'flows': flows,
            'hierarchy': hierarchy,
            'domains': domains
        }
    
    def _analyze_flow_file(self, flow_file: Path) -> Dict[str, Any]:
        """Analyze a flow file and extract metadata."""
        try:
            # Read file content
            with open(flow_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract basic metadata
            flow_info = {
                'path': str(flow_file),
                'name': flow_file.stem,
                'size': flow_file.stat().st_size,
                'modified': flow_file.stat().st_mtime,
                'content_length': len(content),
                'classes': [],
                'functions': [],
                'imports': [],
                'docstring': None
            }
            
            # Extract classes
            import ast
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        flow_info['classes'].append(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        flow_info['functions'].append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if isinstance(alias, ast.alias):
                                flow_info['imports'].append(alias.asname)
                            else:
                                flow_info['imports'].append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module_name = node.module
                        for alias in node.names:
                            if isinstance(alias, ast.alias):
                                flow_info['imports'].append(f"{module_name}.{alias.asname}")
                            else:
                                flow_info['imports'].append(f"{module_name}.{alias.name}")
                
                # Extract docstring from first class or module
                if tree.body:
                    first_node = tree.body[0]
                    if isinstance(first_node, ast.ClassDef) and ast.get_docstring(first_node):
                        flow_info['docstring'] = ast.get_docstring(first_node)
                    elif isinstance(first_node, ast.Expr) and ast.get_docstring(tree):
                        flow_info['docstring'] = ast.get_docstring(tree)
                        
            except SyntaxError as e:
                logger.warning(f"Syntax error in {flow_file}: {e}")
                flow_info['syntax_error'] = str(e)
            
            return flow_info
            
        except Exception as e:
            logger.error(f"Failed to analyze flow file {flow_file}: {e}")
            return {
                'path': str(flow_file),
                'name': flow_file.stem,
                'error': str(e)
            }
    
    def get_flow_hierarchy(self) -> Dict[str, Any]:
        """Get the complete flow hierarchy."""
        return self.hierarchy
    
    def get_flows_by_domain(self, domain: str) -> List[str]:
        """Get all flows in a specific domain."""
        domain_flows = []
        
        for flow_name, flow_info in self.discovered_flows.items():
            if '.' in flow_name and flow_name.split('.')[0] == domain:
                domain_flows.append(flow_name)
        
        return domain_flows
    
    def get_flows_by_type(self, flow_type: str) -> List[str]:
        """Get flows by type (class name pattern)."""
        matching_flows = []
        
        for flow_name, flow_info in self.discovered_flows.items():
            if 'classes' in flow_info:
                for class_name in flow_info['classes']:
                    if flow_type.lower() in class_name.lower():
                        matching_flows.append(flow_name)
                        break
        
        return matching_flows
    
    def validate_flow_structure(self, pattern: str) -> Dict[str, Any]:
        """Validate the flow structure for the given pattern."""
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        discovered = self.discover_flows(pattern)
        
        if pattern == 'simple':
            # Simple pattern should have main flow.py
            if 'main' not in discovered['flows']:
                validation_result['errors'].append("Simple pattern missing main flow.py")
                validation_result['valid'] = False
            elif len(discovered['flows']) > 1:
                validation_result['warnings'].append("Simple pattern has additional flows, consider standard pattern")
        
        elif pattern == 'standard':
            # Standard pattern should have flow.py and optional flows/
            if 'main' not in discovered['flows']:
                validation_result['errors'].append("Standard pattern missing main flow.py")
                validation_result['valid'] = False
            
            # Check for common flow types
            common_flows = ['search', 'pagination', 'extraction']
            found_flows = list(discovered['flows'].keys())
            missing_common = [f for f in common_flows if f not in found_flows]
            if missing_common:
                validation_result['recommendations'].append(f"Consider adding common flows: {', '.join(missing_common)}")
        
        elif pattern == 'complex':
            # Complex pattern should have domain-separated flows
            expected_domains = ['navigation', 'extraction']
            found_domains = list(discovered.get('domains', {}).keys())
            missing_domains = [d for d in expected_domains if d not in found_domains]
            
            if missing_domains:
                validation_result['errors'].append(f"Complex pattern missing required domains: {', '.join(missing_domains)}")
                validation_result['valid'] = False
            
            # Check for domain flow completeness
            for domain_name, domain_flows in discovered.get('domains', {}).items():
                if not domain_flows:
                    validation_result['warnings'].append(f"Domain '{domain_name}' has no flows")
        
        return validation_result
    
    def generate_flow_imports(self, pattern: str) -> str:
        """Generate import statements for discovered flows."""
        discovered = self.discover_flows(pattern)
        imports = []
        
        if pattern == 'simple':
            if 'main' in discovered['flows']:
                imports.append("from .flow import *")
        
        elif pattern == 'standard':
            # Main flow
            if 'main' in discovered['flows']:
                imports.append("from .flow import *")
            
            # Additional flows
            for flow_name in discovered['flows']:
                if flow_name != 'main':
                    imports.append(f"from .flows.{flow_name} import *")
        
        elif pattern == 'complex':
            # Domain-based imports with hierarchical namespacing
            for domain_name in discovered.get('domains', {}):
                imports.append(f"from .flows.{domain_name} import *")
        
        return '\n'.join(imports)
    
    def generate_flow_registry(self, pattern: str) -> str:
        """Generate flow registry code with hierarchical namespacing."""
        discovered = self.discover_flows(pattern)
        registry_entries = []
        
        if pattern == 'simple':
            if 'main' in discovered['flows']:
                flow_info = discovered['flows']['main']
                class_names = flow_info.get('classes', [])
                for class_name in class_names:
                    registry_entries.append(f"    '{class_name}': {class_name},")
        
        elif pattern == 'standard':
            # Main flow
            if 'main' in discovered['flows']:
                flow_info = discovered['flows']['main']
                class_names = flow_info.get('classes', [])
                for class_name in class_names:
                    registry_entries.append(f"    '{class_name}': {class_name},")
            
            # Additional flows
            for flow_name, flow_info in discovered['flows'].items():
                if flow_name != 'main':
                    class_names = flow_info.get('classes', [])
                    for class_name in class_names:
                        registry_entries.append(f"    '{flow_name}': {class_name},")
        
        elif pattern == 'complex':
            # Domain-based registry with hierarchical namespacing
            for domain_name, domain_flows in discovered.get('domains', {}).items():
                for flow_name, flow_info in domain_flows.items():
                    class_names = flow_info.get('classes', [])
                    for class_name in class_names:
                        # Create hierarchical name: domain.flow_name
                        hierarchical_name = f"{domain_name}.{flow_name}"
                        registry_entries.append(f"    '{hierarchical_name}': {class_name},")
        
        if registry_entries:
            return f"FLOW_REGISTRY = {{\n{', '.join(registry_entries)}\n}}"
        
        return "FLOW_REGISTRY = {}"
    
    def get_hierarchical_flow_name(self, flow_name: str, domain: str = None) -> str:
        """
        Generate hierarchical flow name with domain prefix.
        
        Args:
            flow_name: Base flow name
            domain: Optional domain prefix
            
        Returns:
            Hierarchical flow name
        """
        if domain:
            return f"{domain}.{flow_name}"
        return flow_name
    
    def parse_hierarchical_name(self, full_name: str) -> tuple:
        """
        Parse hierarchical flow name into domain and flow name.
        
        Args:
            full_name: Full hierarchical flow name (e.g., "navigation.match_nav")
            
        Returns:
            Tuple of (domain, flow_name)
        """
        if '.' in full_name:
            parts = full_name.split('.', 1)  # Split only on first dot
            if len(parts) == 2:
                return parts[0], parts[1]
        
        return None, full_name
    
    def get_domain_flows(self, domain: str) -> Dict[str, Any]:
        """Get all flows in a specific domain."""
        domain_flows = {}
        
        for flow_name, flow_info in self.discovered_flows.items():
            parsed_domain, flow_base_name = self.parse_hierarchical_name(flow_name)
            
            if parsed_domain == domain:
                domain_flows[flow_base_name] = flow_info
            elif '.' not in flow_name and domain == 'root':  # Non-hierarchical flows
                domain_flows[flow_name] = flow_info
        
        return domain_flows
    
    def get_flow_domains(self) -> List[str]:
        """Get list of all domains in discovered flows."""
        domains = set()
        
        for flow_name in self.discovered_flows.keys():
            parsed_domain, _ = self.parse_hierarchical_name(flow_name)
            if parsed_domain:
                domains.add(parsed_domain)
        
        return sorted(list(domains))
    
    def create_domain_registry(self) -> Dict[str, Any]:
        """Create domain-based registry for complex patterns."""
        domain_registry = {}
        
        for domain in self.get_flow_domains():
            domain_flows = self.get_domain_flows(domain)
            if domain_flows:
                domain_registry[domain] = domain_flows
        
        return domain_registry
    
    def generate_domain_init_files(self, output_dir: Path) -> None:
        """Generate __init__.py files for domain organization."""
        try:
            domains = self.get_flow_domains()
            
            # Create main flows/__init__.py
            flows_init = output_dir / 'flows' / '__init__.py'
            flows_init.parent.mkdir(parents=True, exist_ok=True)
            
            with open(flows_init, 'w') as f:
                f.write('"""')
                f.write('"""Flows module with domain-based organization."""')
                f.write('"""\n\n')
                
                # Import each domain
                for domain in domains:
                    f.write(f'from .{domain} import {domain.title()}_DOMAIN_FLOWS\n')
                
                f.write('\n# Domain registries\n')
                for domain in domains:
                    f.write(f'{domain.upper()}_DOMAIN_FLOWS = {{}}\n')
                
                f.write('\n# Combined registry\n')
                f.write('DOMAIN_FLOWS = {}\n')
                f.write('for domain in DOMAIN_REGISTRIES:\n')
                f.write('    DOMAIN_FLOWS.update(domain)\n')
            
            # Create domain-specific __init__.py files
            for domain in domains:
                domain_dir = output_dir / 'flows' / domain
                domain_init = domain_dir / '__init__.py'
                domain_dir.mkdir(parents=True, exist_ok=True)
                
                domain_flows = self.get_domain_flows(domain)
                
                with open(domain_init, 'w') as f:
                    f.write(f'"""')
                    f.write(f'"""{domain.title()} domain flows."""')
                    f.write('"""\n\n')
                    
                    # Import flows in this domain
                    for flow_name in domain_flows.keys():
                        f.write(f'from .{flow_name} import *\n')
                    
                    f.write(f'\n# {domain.title()} domain registry\n')
                    f.write(f'{domain.upper()}_DOMAIN_FLOWS = {{\n')
                    
                    for flow_name, flow_info in domain_flows.items():
                        class_names = flow_info.get('classes', [])
                        for class_name in class_names:
                            f.write(f"    '{flow_name}': {class_name},\n")
                    
                    f.write('}\n')
            
            logger.info(f"Generated domain __init__.py files for {len(domains)} domains")
            
        except Exception as e:
            logger.error(f"Failed to generate domain __init__.py files: {e}")
    
    def create_domain_registry(self) -> Dict[str, Any]:
        """Create domain-based registry for complex patterns."""
        domain_registry = {}
        
        for domain in self.get_flow_domains():
            domain_flows = self.get_domain_flows(domain)
            if domain_flows:
                domain_registry[domain] = domain_flows
        
        return domain_registry
    
    def register_domain_flows(self, domain_flows: Dict[str, Any]) -> None:
        """Register domain flows with metadata."""
        for domain, flows in domain_flows.items():
            logger.info(f"Registering {len(flows)} flows for {domain} domain")
            
            # Validate each flow before registration
            for flow_name, flow_info in flows.items():
                if 'classes' not in flow_info or not flow_info['classes']:
                    logger.warning(f"Flow {flow_name} has no classes to register")
                    continue
                
                # Register each class
                for class_name in flow_info['classes']:
                    full_name = f"{domain}.{class_name}"
                    logger.debug(f"Registering flow class: {full_name}")
    
    def get_flow_metadata(self, flow_name: str) -> Dict[str, Any]:
        """Get comprehensive metadata for a specific flow."""
        if flow_name not in self.discovered_flows:
            return {'error': f'Flow {flow_name} not found'}
        
        flow_info = self.discovered_flows[flow_name]
        
        # Extract additional metadata
        metadata = {
            'name': flow_name,
            'path': flow_info.get('path'),
            'size': flow_info.get('size'),
            'modified': flow_info.get('modified'),
            'content_length': flow_info.get('content_length'),
            'classes': flow_info.get('classes', []),
            'functions': flow_info.get('functions', []),
            'imports': flow_info.get('imports', []),
            'docstring': flow_info.get('docstring'),
            'domain': None,
            'type': None
        }
        
        # Determine domain and type
        if '.' in flow_name:
            domain, base_name = self.parse_hierarchical_name(flow_name)
            metadata['domain'] = domain
            metadata['type'] = 'domain_flow'
        else:
            metadata['type'] = 'main_flow' if flow_name == 'main' else 'standard_flow'
        
        # Add hierarchy information
        if self.hierarchy:
            for parent_path, node in self.hierarchy.items():
                if flow_name in str(node):
                    metadata['parent'] = parent_path
                    metadata['hierarchy_level'] = len(parent_path.split('/')) if parent_path else 0
                    break
        
        return metadata
    
    def get_domain_summary(self) -> Dict[str, Any]:
        """Get summary of all discovered domains."""
        domains = self.get_flow_domains()
        summary = {}
        
        for domain in domains:
            domain_flows = self.get_domain_flows(domain)
            summary[domain] = {
                'flow_count': len(domain_flows),
                'flows': list(domain_flows.keys()),
                'total_classes': sum(
                    len(flow_info.get('classes', [])) 
                    for flow_info in domain_flows.values()
                ),
                'total_functions': sum(
                    len(flow_info.get('functions', [])) 
                    for flow_info in domain_flows.values()
                )
            }
        
        return summary
    
    def export_registry_config(self, output_file: str) -> None:
        """Export registry configuration for debugging and documentation."""
        try:
            config = {
                'discovered_flows': self.discovered_flows,
                'hierarchy': self.hierarchy,
                'domains': self.get_flow_domains(),
                'domain_summary': self.get_domain_summary(),
                'timestamp': time.time()
            }
            
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            logger.info(f"Exported registry configuration to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to export registry configuration: {e}")
    
    def validate_registry_integrity(self) -> Dict[str, Any]:
        """Validate the integrity of the flow registry."""
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'issues': []
        }
        
        # Check for duplicate flow names
        flow_names = list(self.discovered_flows.keys())
        duplicate_names = [name for name in flow_names if flow_names.count(name) > 1]
        
        if duplicate_names:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Duplicate flow names: {', '.join(duplicate_names)}")
        
        # Check for missing required domains
        expected_domains = ['navigation', 'extraction']
        found_domains = self.get_flow_domains()
        missing_domains = [d for d in expected_domains if d not in found_domains]
        
        if missing_domains:
            validation_result['warnings'].append(f"Missing required domains: {', '.join(missing_domains)}")
        
        # Check for empty domains
        for domain in found_domains:
            domain_flows = self.get_domain_flows(domain)
            if not domain_flows:
                validation_result['warnings'].append(f"Empty domain: {domain}")
        
        # Check for circular dependencies
        circular_deps = self._check_circular_dependencies()
        if circular_deps:
            validation_result['errors'].append(f"Circular dependencies detected: {', '.join(circular_deps)}")
        
        return validation_result
    
    def _check_circular_dependencies(self) -> List[str]:
        """Check for circular dependencies in flow imports."""
        dependencies = {}
        circular_deps = []
        
        # Build dependency graph
        for flow_name, flow_info in self.discovered_flows.items():
            imports = flow_info.get('imports', [])
            dependencies[flow_name] = imports
        
        # Check for circular dependencies
        for flow_name in dependencies:
            if self._has_circular_dependency(flow_name, dependencies, set()):
                circular_deps.append(flow_name)
        
        return circular_deps
    
    def _has_circular_dependency(self, flow_name: str, dependencies: Dict[str, List[str]], visited: set) -> bool:
        """Check if a flow has circular dependencies."""
        if flow_name in visited:
            return True
        
        visited.add(flow_name)
        
        for dep in dependencies.get(flow_name, []):
            if dep in self.discovered_flows:
                if self._has_circular_dependency(dep, dependencies, visited.copy()):
                    return True
        
        visited.remove(flow_name)
        return False
        """Validate hierarchical flow structure."""
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Check for domain consistency
        domains = self.get_flow_domains()
        expected_domains = ['navigation', 'extraction', 'filtering', 'authentication']
        
        missing_domains = [d for d in expected_domains if d not in domains]
        if missing_domains:
            validation_result['warnings'].append(
                f"Missing expected domains: {', '.join(missing_domains)}"
            )
        
        # Check for flow naming consistency
        for flow_name in self.discovered_flows.keys():
            if '.' in flow_name:
                domain, base_name = self.parse_hierarchical_name(flow_name)
                if not domain:
                    validation_result['warnings'].append(
                        f"Invalid hierarchical name format: {flow_name}"
                    )
        
        # Check for domain flow completeness
        for domain in domains:
            domain_flows = self.get_domain_flows(domain)
            if not domain_flows:
                validation_result['warnings'].append(
                    f"Domain '{domain}' has no flows"
                )
        
        return validation_result
    
    def cache_discovery(self, cache_file: Optional[str] = None) -> None:
        """Cache discovery results to avoid repeated scanning."""
        if cache_file:
            cache_path = Path(cache_file)
            try:
                import json
                cache_data = {
                    'discovered_flows': self.discovered_flows,
                    'hierarchy': self.hierarchy,
                    'timestamp': time.time()
                }
                
                with open(cache_path, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                
                logger.info(f"Cached flow discovery to {cache_path}")
            except Exception as e:
                logger.error(f"Failed to cache discovery: {e}")
    
    def load_cached_discovery(self, cache_file: Optional[str] = None) -> bool:
        """Load cached discovery results."""
        if not cache_file:
            return False
        
        cache_path = Path(cache_file)
        if not cache_path.exists():
            return False
        
        try:
            import json
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check cache age (24 hours)
            cache_age = time.time() - cache_data.get('timestamp', 0)
            if cache_age > 86400:  # 24 hours
                return False
            
            self.discovered_flows = cache_data.get('discovered_flows', {})
            self.hierarchy = cache_data.get('hierarchy', {})
            
            logger.info(f"Loaded cached flow discovery from {cache_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cached discovery: {e}")
            return False


def discover_flows_recursive(base_path: str, pattern: str = 'standard') -> Dict[str, Any]:
    """
    Convenience function for recursive flow discovery.
    
    Args:
        base_path: Base path for flow discovery
        pattern: Pattern type for discovery
        
    Returns:
        Dictionary of discovered flows
    """
    discovery = FlowDiscovery(base_path)
    return discovery.discover_flows(pattern)


def validate_flow_structure(base_path: str, pattern: str) -> Dict[str, Any]:
    """
    Convenience function for flow structure validation.
    
    Args:
        base_path: Base path to validate
        pattern: Pattern type to validate against
        
    Returns:
        Validation results
    """
    discovery = FlowDiscovery(base_path)
    return discovery.validate_flow_structure(pattern)
