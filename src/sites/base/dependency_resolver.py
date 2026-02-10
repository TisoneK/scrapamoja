"""
Component dependency resolution system for managing component dependencies.

This module provides dependency resolution functionality to ensure components
are loaded in the correct order and their dependencies are satisfied.
"""

from typing import Dict, Any, List, Optional, Set, Tuple, Type
from datetime import datetime
import asyncio
import json
from collections import defaultdict, deque

from .component_interface import BaseComponent, ComponentContext, ComponentResult
from .component_discovery import get_component, get_all_components


class DependencyResolver:
    """Component dependency resolution system."""
    
    def __init__(self):
        """Initialize dependency resolver."""
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._resolved_order: List[str] = []
        self._circular_dependencies: List[Tuple[str, str]] = []
        self._resolution_stats: Dict[str, Any] = {}
        
        # Component instances cache
        self._component_instances: Dict[str, BaseComponent] = {}
        self._initialization_order: List[str] = []
        
        # Resolution state
        self._resolution_state = {
            'pending': set(),
            'resolving': set(),
            'resolved': set(),
            'failed': set()
        }
    
    async def resolve_dependencies(self, component_ids: List[str], 
                                 component_context: ComponentContext = None) -> Dict[str, Any]:
        """
        Resolve dependencies for a list of components.
        
        Args:
            component_ids: List of component IDs to resolve
            component_context: Component context for initialization
            
        Returns:
            Resolution results
        """
        try:
            resolution_start = datetime.utcnow()
            
            # Clear previous state
            self._clear_resolution_state()
            
            # Build dependency graph
            await self._build_dependency_graph(component_ids)
            
            # Check for circular dependencies
            circular_deps = self._detect_circular_dependencies()
            if circular_deps:
                return {
                    'success': False,
                    'error': 'Circular dependencies detected',
                    'circular_dependencies': circular_deps,
                    'dependency_graph': dict(self._dependency_graph)
                }
            
            # Resolve dependencies
            resolution_result = await self._resolve_dependency_order(component_ids, component_context)
            
            resolution_end = datetime.utcnow()
            resolution_duration = (resolution_end - resolution_start).total_seconds()
            
            # Update statistics
            self._update_resolution_stats(component_ids, resolution_result, resolution_duration)
            
            return {
                'success': resolution_result['success'],
                'resolved_order': resolution_result['resolved_order'],
                'dependency_graph': dict(self._dependency_graph),
                'reverse_dependency_graph': dict(self._reverse_dependency_graph),
                'resolution_duration_seconds': resolution_duration,
                'resolution_timestamp': resolution_start.isoformat(),
                'components_count': len(component_ids),
                **resolution_result.get('details', {})
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'resolution_timestamp': datetime.utcnow().isoformat()
            }
    
    async def _build_dependency_graph(self, component_ids: List[str]) -> None:
        """Build dependency graph from component metadata."""
        try:
            self._dependency_graph.clear()
            self._reverse_dependency_graph.clear()
            
            for component_id in component_ids:
                self._resolution_state['pending'].add(component_id)
                
                # Get component info
                component_info = get_component_info(component_id)
                if not component_info:
                    continue
                
                # Get dependencies from metadata
                dependencies = component_info.get('metadata', {}).get('dependencies', [])
                
                # Add to dependency graph
                for dependency in dependencies:
                    self._dependency_graph[component_id].add(dependency)
                    self._reverse_dependency_graph[dependency].add(component_id)
            
        except Exception as e:
            print(f"Error building dependency graph: {str(e)}")
    
    def _detect_circular_dependencies(self) -> List[Tuple[str, str]]:
        """Detect circular dependencies using DFS."""
        try:
            visited = set()
            rec_stack = []
            circular_deps = []
            
            def dfs(node: str, parent: str = None) -> None:
                if node in rec_stack:
                    # Found circular dependency
                    cycle_start = rec_stack.index(node)
                    cycle = rec_stack[cycle_start:] + [node]
                    circular_deps.append(tuple(cycle))
                    return
                
                if node in visited:
                    return
                
                visited.add(node)
                rec_stack.append(node)
                
                for neighbor in self._dependency_graph.get(node, set()):
                    dfs(neighbor, node)
                
                rec_stack.pop()
            
            for node in self._dependency_graph:
                if node not in visited:
                    dfs(node)
            
            return circular_deps
            
        except Exception as e:
            print(f"Error detecting circular dependencies: {str(e)}")
            return []
    
    async def _resolve_dependency_order(self, component_ids: List[str], 
                                   component_context: ComponentContext = None) -> Dict[str, Any]:
        """Resolve dependency order using topological sort."""
        try:
            resolved_order = []
            in_degree = {node: len(deps) for node, deps in self._dependency_graph.items()}
            
            # Queue of nodes with no dependencies
            queue = deque([node for node, degree in in_degree.items() if degree == 0])
            
            while queue:
                current = queue.popleft()
                
                if current in resolved_order:
                    continue
                
                resolved_order.append(current)
                self._resolution_state['resolved'].add(current)
                
                # Update in-degree for neighbors
                for neighbor in self._dependency_graph.get(current, set()):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            # Check if all components were resolved
            unresolved = set(component_ids) - set(resolved_order)
            
            if unresolved:
                return {
                    'success': False,
                    'error': f'Unable to resolve dependencies for: {unresolved}',
                    'resolved_order': resolved_order,
                    'unresolved_components': list(unresolved),
                    'details': {
                        'in_degree': in_degree,
                        'unresolved_components': list(unresolved)
                    }
                }
            
            self._resolved_order = resolved_order
            self._initialization_order = resolved_order.copy()
            
            return {
                'success': True,
                'resolved_order': resolved_order,
                'details': {
                    'total_components': len(resolved_order),
                    'dependency_levels': self._calculate_dependency_levels(resolved_order)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'resolved_order': self._resolved_order,
                'details': {}
            }
    
    def _calculate_dependency_levels(self, resolved_order: List[str]) -> Dict[str, int]:
        """Calculate dependency levels for resolved components."""
        try:
            levels = {}
            
            for i, component_id in enumerate(resolved_order):
                # Level is the maximum level of its dependencies plus 1
                max_dep_level = 0
                for dep in self._dependency_graph.get(component_id, set()):
                    if dep in levels:
                        max_dep_level = max(max_dep_level, levels[dep])
                
                levels[component_id] = max_dep_level + 1
            
            return levels
            
        except Exception as e:
            print(f"Error calculating dependency levels: {str(e)}")
            return {}
    
    async def initialize_components(self, component_ids: List[str], 
                                   component_context: ComponentContext = None) -> Dict[str, Any]:
        """Initialize components in dependency order."""
        try:
            initialization_results = {}
            failed_components = []
            
            for component_id in self._resolved_order:
                if component_id not in component_ids:
                    continue
                
                try:
                    self._resolution_state['resolving'].add(component_id)
                    
                    # Get component class
                    component_class = get_component(component_id)
                    if not component_class:
                        failed_components.append(component_id)
                        continue
                    
                    # Create component instance
                    component = component_class()
                    self._component_instances[component_id] = component
                    
                    # Initialize component
                    if component_context:
                        success = await component.initialize(component_context)
                        if not success:
                            failed_components.append(component_id)
                            self._component_instances.pop(component_id, None)
                            continue
                    
                    initialization_results[component_id] = {
                        'success': True,
                        'instance': component,
                        'class_name': component_class.__name__
                    }
                    
                    self._resolution_state['resolved'].add(component_id)
                    
                except Exception as e:
                    failed_components.append(component_id)
                    self._resolution_state['failed'].add(component_id)
                    initialization_results[component_id] = {
                        'success': False,
                        'error': str(e)
                    }
            
            return {
                'success': len(failed_components) == 0,
                'initialization_results': initialization_results,
                'failed_components': failed_components,
                'initialized_count': len(initialization_results) - len(failed_components),
                'failed_count': len(failed_components)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'failed_components': list(self._resolution_state['failed'])
            }
    
    def get_component_instance(self, component_id: str) -> Optional[BaseComponent]:
        """Get a component instance by ID."""
        return self._component_instances.get(component_id)
    
    def get_component_dependencies(self, component_id: str) -> Set[str]:
        """Get dependencies for a specific component."""
        return self._dependency_graph.get(component_id, set())
    
    def get_component_dependents(self, component_id: str) -> Set[str]:
        """Get components that depend on a specific component."""
        return self._reverse_dependency_graph.get(component_id, set())
    
    def get_dependency_chain(self, component_id: str) -> List[str]:
        """Get the full dependency chain for a component."""
        try:
            visited = set()
            chain = []
            
            def dfs(node: str) -> None:
                if node in visited:
                    return
                
                visited.add(node)
                chain.append(node)
                
                for dep in self._dependency_graph.get(node, set()):
                    dfs(dep)
                
                chain.pop()  # Remove current node from chain
            
            dfs(component_id)
            return chain
            
        except Exception:
            return []
    
    def get_dependency_level(self, component_id: str) -> int:
        """Get the dependency level for a component."""
        if self._resolved_order:
            try:
                return self._resolved_order.index(component_id)
            except ValueError:
                return -1
        return -1
    
    def _clear_resolution_state(self) -> None:
        """Clear resolution state."""
        self._resolution_state = {
            'pending': set(),
            'resolving': set(),
            'resolved': set(),
            'failed': set()
        }
    
    def _update_resolution_stats(self, component_ids: List[str], result: Dict[str, Any], duration: float) -> None:
        """Update resolution statistics."""
        try:
            self._resolution_stats['last_resolution_timestamp'] = datetime.utcnow()
            self._resolution_stats['last_resolution_duration_seconds'] = duration
            self._resolution_stats['last_component_count'] = len(component_ids)
            self._resolution_stats['total_resolutions'] = self._resolution_stats.get('total_resolutions', 0) + 1
            
            if result['success']:
                self._resolution_stats['successful_resolutions'] = self._resolution_stats.get('successful_resolutions', 0) + 1
                self._resolution_stats['last_successful_resolution_timestamp'] = datetime.utcnow()
            else:
                self._resolution_stats['failed_resolutions'] = self._resolution_stats.get('failed_resolutions', 0) + 1
            
        except Exception as e:
            print(f"Error updating resolution stats: {str(e)}")
    
    def get_resolution_stats(self) -> Dict[str, Any]:
        """Get resolution statistics."""
        return self._resolution_stats.copy()
    
    def validate_dependencies(self, component_ids: List[str]) -> Dict[str, Any]:
        """Validate dependencies for a list of components."""
        try:
            validation_results = {}
            
            for component_id in component_ids:
                component_info = get_component_info(component_id)
                if not component_info:
                    validation_results[component_id] = {
                        'valid': False,
                        'error': 'Component not found'
                    }
                    continue
                
                metadata = component_info.get('metadata', {})
                dependencies = metadata.get('dependencies', [])
                
                # Check if dependencies exist
                missing_deps = []
                for dep in dependencies:
                    dep_info = get_component_info(dep)
                    if not dep_info:
                        missing_deps.append(dep)
                
                # Check for circular dependencies
                chain = self.get_dependency_chain(component_id)
                has_circular = len(set(chain)) != len(chain)
                
                validation_results[component_id] = {
                    'valid': len(missing_deps) == 0 and not has_circular,
                    'dependencies': dependencies,
                    'missing_dependencies': missing_deps,
                    'has_circular_dependencies': has_circular_dependencies,
                    'dependency_chain': chain if has_circular else []
                }
            
            return {
                'valid': all(result['valid'] for result in validation_results.values()),
                'validation_results': validation_results,
                'total_components': len(component_ids),
                'valid_components': len([r for r in validation_results.values() if r['valid']]),
                'invalid_components': len([r for r in validation_results.values() if not r['valid']]),
                'components_with_missing_deps': [id for id, result in validation_results.items() if result['missing_dependencies']],
                'components_with_circular_deps': [id for id, result in validation_results.items() if result['has_circular_dependencies']]
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'validation_results': {}
            }
    
    def get_dependency_summary(self) -> Dict[str, Any]:
        """Get a summary of all dependencies."""
        try:
            return {
                'total_components': len(self._dependency_graph),
                'total_dependencies': sum(len(deps) for deps in self._dependency_graph.values()),
                'max_dependencies': max(len(deps) for deps in self._dependency_graph.values()) if self._dependency_graph else 0,
                'average_dependencies': sum(len(deps) for deps in self._dependency_graph.values()) / len(self._dependency_graph) if self._dependency_graph else 0,
                'components_with_no_dependencies': [id for id, deps in self._dependency_graph.items() if len(deps) == 0],
                'components_with_dependencies': [id for id, deps in self._dependency_graph.items() if len(deps) > 0],
                'dependency_graph': dict(self._dependency_graph),
                'reverse_dependency_graph': dict(self._reverse_dependency_graph)
            }
            
        except Exception as e:
            return {
                'error': str(e)
            }
    
    def export_dependency_graph(self, format: str = 'json') -> str:
        """Export dependency graph in specified format."""
        try:
            if format == 'json':
                return json.dumps({
                    'dependency_graph': dict(self._dependency_graph),
                    'reverse_dependency_graph': dict(self._reverse_dependency_graph),
                    'resolved_order': self._resolved_order
                }, indent=2)
            elif format == 'dot':
                # Generate DOT format for Graphviz
                dot_lines = ['digraph dependencies {']
                
                # Add nodes
                for node in self._dependency_graph:
                    dot_lines.append(f'  "{node}";')
                
                # Add edges
                for source, targets in self._dependency_graph.items():
                    for target in targets:
                        dot_lines.append(f'  "{source}" -> "{target}";')
                
                dot_lines.append('}')
                return '\n'.join(dot_lines)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            return f"Error exporting dependency graph: {str(e)}"
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            self._component_instances.clear()
            self._resolved_order.clear()
            self._initialization_order.clear()
            self._clear_resolution_state()
        except Exception as e:
            print(f"Error clearing cache: {str(e)}")


# Global dependency resolver instance
_dependency_resolver = DependencyResolver()


# Convenience functions
async def resolve_dependencies(component_ids: List[str], component_context = None) -> Dict[str, Any]:
    """Resolve dependencies for components."""
    return await _dependency_resolver.resolve_dependencies(component_ids, component_context)


def get_component_instance(component_id: str) -> Optional[BaseComponent]:
    """Get a component instance by ID."""
    return _dependency_resolver.get_component_instance(component_id)


def get_component_dependencies(component_id: str) -> Set[str]:
    """Get dependencies for a component."""
    return _dependency_resolver.get_component_dependencies(component_id)


def get_component_dependents(component_id: str) -> Set[str]:
    """Get components that depend on a component."""
    return _dependency_resolver.get_component_dependents(component_id)


def validate_dependencies(component_ids: List[str]) -> Dict[str, Any]:
    """Validate dependencies for components."""
    return _dependency_resolver.validate_dependencies(component_ids)


def get_dependency_summary() -> Dict[str, Any]:
    """Get dependency summary."""
    return _dependency_resolver.get_dependency_summary()


def export_dependency_graph(format: str = 'json') -> str:
    """Export dependency graph."""
    return _dependency_resolver.export_dependency_graph(format)


def clear_cache() -> None:
    """Clear dependency resolver cache."""
    _dependency_resolver.clear_cache()
