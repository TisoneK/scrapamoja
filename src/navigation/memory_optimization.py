"""
Memory usage optimization for large route graphs

Provides memory-efficient data structures and algorithms for handling large navigation
graphs with millions of nodes and edges while maintaining performance.
"""

import gc
import sys
import weakref
from typing import Dict, List, Set, Any, Optional, Tuple, Iterator
from dataclasses import dataclass, field
from collections import defaultdict, deque
import networkx as nx
import pickle
import zlib
from pathlib import Path

from .logging_config import get_navigation_logger


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_nodes: int = 0
    total_edges: int = 0
    memory_usage_mb: float = 0.0
    graph_size_mb: float = 0.0
    cache_size_mb: float = 0.0
    optimization_ratio: float = 0.0


class MemoryOptimizedRouteGraph:
    """Memory-optimized route graph implementation"""
    
    def __init__(self, max_memory_mb: int = 512):
        """Initialize memory-optimized graph"""
        self.logger = get_navigation_logger("memory_optimized_graph")
        self.max_memory_mb = max_memory_mb
        
        # Use memory-efficient data structures
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._node_data: Dict[str, Dict[str, Any]] = {}
        self._edge_data: Dict[Tuple[str, str], Dict[str, Any]] = {}
        
        # Memory management
        self._node_cache: Dict[str, Dict[str, Any]] = {}
        self._edge_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._cache_max_size = 1000
        
        # Statistics
        self._stats = MemoryStats()
        
        self.logger.info(
            "Memory-optimized route graph initialized",
            max_memory_mb=max_memory_mb
        )
    
    def add_node(self, node_id: str, **attributes) -> None:
        """Add node with memory optimization"""
        if node_id not in self._adjacency:
            self._adjacency[node_id] = set()
            self._reverse_adjacency[node_id] = set()
            self._stats.total_nodes += 1
        
        # Store only essential attributes
        essential_attrs = {}
        for key, value in attributes.items():
            if self._is_essential_attribute(key, value):
                essential_attrs[key] = value
        
        self._node_data[node_id] = essential_attrs
        
        # Check memory usage
        if self._should_optimize():
            self._optimize_memory()
    
    def add_edge(self, source: str, target: str, **attributes) -> None:
        """Add edge with memory optimization"""
        # Add nodes if they don't exist
        if source not in self._adjacency:
            self.add_node(source)
        if target not in self._adjacency:
            self.add_node(target)
        
        # Add edge
        self._adjacency[source].add(target)
        self._reverse_adjacency[target].add(source)
        self._stats.total_edges += 1
        
        # Store essential edge attributes
        edge_key = (source, target)
        essential_attrs = {}
        for key, value in attributes.items():
            if self._is_essential_attribute(key, value):
                essential_attrs[key] = value
        
        self._edge_data[edge_key] = essential_attrs
        
        # Check memory usage
        if self._should_optimize():
            self._optimize_memory()
    
    def get_neighbors(self, node_id: str) -> Set[str]:
        """Get neighbors of node"""
        return self._adjacency.get(node_id, set())
    
    def get_predecessors(self, node_id: str) -> Set[str]:
        """Get predecessors of node"""
        return self._reverse_adjacency.get(node_id, set())
    
    def get_node_data(self, node_id: str) -> Dict[str, Any]:
        """Get node data with caching"""
        if node_id in self._node_cache:
            return self._node_cache[node_id]
        
        data = self._node_data.get(node_id, {})
        
        # Cache frequently accessed data
        if len(self._node_cache) < self._cache_max_size:
            self._node_cache[node_id] = data
        
        return data
    
    def get_edge_data(self, source: str, target: str) -> Dict[str, Any]:
        """Get edge data with caching"""
        edge_key = (source, target)
        
        if edge_key in self._edge_cache:
            return self._edge_cache[edge_key]
        
        data = self._edge_data.get(edge_key, {})
        
        # Cache frequently accessed data
        if len(self._edge_cache) < self._cache_max_size:
            self._edge_cache[edge_key] = data
        
        return data
    
    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest path using memory-efficient BFS"""
        if source not in self._adjacency or target not in self._adjacency:
            return None
        
        # Use deque for memory efficiency
        queue = deque([(source, [source])])
        visited = {source}
        
        while queue:
            current, path = queue.popleft()
            
            if current == target:
                return path
            
            for neighbor in self._adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def find_all_paths(self, source: str, target: str, max_depth: int = 10) -> Iterator[List[str]]:
        """Find all paths up to max_depth using memory-efficient DFS"""
        if source not in self._adjacency or target not in self._adjacency:
            return
        
        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(path) > max_depth:
                return
            
            if current == target:
                yield path.copy()
                return
            
            for neighbor in self._adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    
                    yield from dfs(neighbor, path, visited)
                    
                    path.pop()
                    visited.remove(neighbor)
        
        yield from dfs(source, [source], {source})
    
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        # Calculate memory usage
        graph_size = sys.getsizeof(self._adjacency) + sys.getsizeof(self._reverse_adjacency)
        graph_size += sys.getsizeof(self._node_data) + sys.getsizeof(self._edge_data)
        
        cache_size = sys.getsizeof(self._node_cache) + sys.getsizeof(self._edge_cache)
        
        total_memory = graph_size + cache_size
        
        self._stats.memory_usage_mb = total_memory / (1024 * 1024)
        self._stats.graph_size_mb = graph_size / (1024 * 1024)
        self._stats.cache_size_mb = cache_size / (1024 * 1024)
        
        # Calculate optimization ratio
        if self._stats.total_nodes > 0:
            self._stats.optimization_ratio = (
                (self._stats.total_nodes * 100) / self._stats.memory_usage_mb
            )
        
        return self._stats
    
    def optimize_memory(self) -> None:
        """Force memory optimization"""
        self._optimize_memory()
        gc.collect()
    
    def _is_essential_attribute(self, key: str, value: Any) -> bool:
        """Check if attribute is essential for navigation"""
        essential_keys = {
            'url', 'title', 'page_type', 'action_type', 'target_url',
            'risk_score', 'expected_delay', 'step_description',
            'route_id', 'step_number', 'weight', 'cost'
        }
        
        # Skip large attributes
        if isinstance(value, (str, bytes)) and len(value) > 1000:
            return False
        
        # Skip complex objects
        if isinstance(value, (dict, list, set)) and len(value) > 100:
            return False
        
        return key in essential_keys or isinstance(value, (int, float, bool))
    
    def _should_optimize(self) -> bool:
        """Check if memory optimization should be triggered"""
        stats = self.get_memory_stats()
        return stats.memory_usage_mb > self.max_memory_mb * 0.8
    
    def _optimize_memory(self) -> None:
        """Perform memory optimization"""
        self.logger.info("Starting memory optimization")
        
        # Clear caches
        self._node_cache.clear()
        self._edge_cache.clear()
        
        # Compress node data
        compressed_nodes = {}
        for node_id, data in self._node_data.items():
            compressed_data = self._compress_data(data)
            compressed_nodes[node_id] = compressed_data
        
        self._node_data = compressed_nodes
        
        # Compress edge data
        compressed_edges = {}
        for edge_key, data in self._edge_data.items():
            compressed_data = self._compress_data(data)
            compressed_edges[edge_key] = compressed_data
        
        self._edge_data = compressed_edges
        
        # Remove unused nodes (degree 0)
        unused_nodes = []
        for node_id in self._adjacency:
            if not self._adjacency[node_id] and not self._reverse_adjacency[node_id]:
                unused_nodes.append(node_id)
        
        for node_id in unused_nodes:
            del self._adjacency[node_id]
            del self._reverse_adjacency[node_id]
            if node_id in self._node_data:
                del self._node_data[node_id]
            self._stats.total_nodes -= 1
        
        # Force garbage collection
        gc.collect()
        
        self.logger.info(
            "Memory optimization completed",
            nodes_removed=len(unused_nodes),
            memory_usage_mb=self.get_memory_stats().memory_usage_mb
        )
    
    def _compress_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress data to reduce memory usage"""
        compressed = {}
        
        for key, value in data.items():
            # Convert to more memory-efficient types
            if isinstance(value, float):
                compressed[key] = round(value, 6)  # Reduce precision
            elif isinstance(value, str) and len(value) > 100:
                # Compress long strings
                compressed[key] = zlib.compress(value.encode())[:100]  # Truncate
            else:
                compressed[key] = value
        
        return compressed
    
    def save_to_disk(self, file_path: str) -> None:
        """Save graph to disk with compression"""
        try:
            graph_data = {
                'adjacency': dict(self._adjacency),
                'reverse_adjacency': dict(self._reverse_adjacency),
                'node_data': self._node_data,
                'edge_data': self._edge_data,
                'stats': self._stats
            }
            
            # Compress data
            compressed_data = zlib.compress(pickle.dumps(graph_data))
            
            with open(file_path, 'wb') as f:
                f.write(compressed_data)
            
            self.logger.info(
                "Graph saved to disk",
                file_path=file_path,
                size_mb=len(compressed_data) / (1024 * 1024)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save graph to disk: {e}")
            raise
    
    def load_from_disk(self, file_path: str) -> None:
        """Load graph from disk"""
        try:
            with open(file_path, 'rb') as f:
                compressed_data = f.read()
            
            # Decompress data
            graph_data = pickle.loads(zlib.decompress(compressed_data))
            
            self._adjacency = defaultdict(set, graph_data['adjacency'])
            self._reverse_adjacency = defaultdict(set, graph_data['reverse_adjacency'])
            self._node_data = graph_data['node_data']
            self._edge_data = graph_data['edge_data']
            self._stats = graph_data['stats']
            
            self.logger.info(
                "Graph loaded from disk",
                file_path=file_path,
                nodes=self._stats.total_nodes,
                edges=self._stats.total_edges
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load graph from disk: {e}")
            raise
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self._node_cache.clear()
        self._edge_cache.clear()
        gc.collect()
        
        self.logger.info("Graph caches cleared")


class RouteGraphOptimizer:
    """Optimizer for large route graphs"""
    
    def __init__(self, graph: MemoryOptimizedRouteGraph):
        """Initialize optimizer"""
        self.graph = graph
        self.logger = get_navigation_logger("route_graph_optimizer")
    
    def remove_duplicate_edges(self) -> int:
        """Remove duplicate edges and return count removed"""
        removed_count = 0
        
        for source in list(self.graph._adjacency.keys()):
            neighbors = self.graph._adjacency[source]
            unique_neighbors = set(neighbors)
            
            if len(neighbors) != len(unique_neighbors):
                self.graph._adjacency[source] = unique_neighbors
                removed_count += len(neighbors) - len(unique_neighbors)
        
        self.logger.info(
            "Duplicate edges removed",
            count=removed_count
        )
        
        return removed_count
    
    def remove_isolated_nodes(self) -> int:
        """Remove isolated nodes and return count removed"""
        isolated_nodes = []
        
        for node_id in list(self.graph._adjacency.keys()):
            if not self.graph._adjacency[node_id] and not self.graph._reverse_adjacency[node_id]:
                isolated_nodes.append(node_id)
        
        for node_id in isolated_nodes:
            del self.graph._adjacency[node_id]
            del self.graph._reverse_adjacency[node_id]
            if node_id in self.graph._node_data:
                del self.graph._node_data[node_id]
        
        self.logger.info(
            "Isolated nodes removed",
            count=len(isolated_nodes)
        )
        
        return len(isolated_nodes)
    
    def compress_node_attributes(self) -> int:
        """Compress node attributes and return count compressed"""
        compressed_count = 0
        
        for node_id, data in self.graph._node_data.items():
            original_size = sys.getsizeof(data)
            compressed_data = self.graph._compress_data(data)
            
            if sys.getsizeof(compressed_data) < original_size:
                self.graph._node_data[node_id] = compressed_data
                compressed_count += 1
        
        self.logger.info(
            "Node attributes compressed",
            count=compressed_count
        )
        
        return compressed_count
    
    def optimize_graph_structure(self) -> Dict[str, int]:
        """Perform comprehensive graph optimization"""
        results = {
            "duplicate_edges_removed": self.remove_duplicate_edges(),
            "isolated_nodes_removed": self.remove_isolated_nodes(),
            "node_attributes_compressed": self.compress_node_attributes()
        }
        
        # Force garbage collection
        gc.collect()
        
        self.logger.info(
            "Graph optimization completed",
            results=results
        )
        
        return results
    
    def create_graph_summary(self) -> Dict[str, Any]:
        """Create summary of graph structure"""
        stats = self.graph.get_memory_stats()
        
        # Calculate degree statistics
        degrees = []
        for node_id in self.graph._adjacency:
            degree = len(self.graph._adjacency[node_id]) + len(self.graph._reverse_adjacency[node_id])
            degrees.append(degree)
        
        degree_stats = {}
        if degrees:
            degree_stats = {
                "min_degree": min(degrees),
                "max_degree": max(degrees),
                "avg_degree": sum(degrees) / len(degrees)
            }
        
        return {
            "memory_stats": stats,
            "degree_statistics": degree_stats,
            "graph_density": (2 * stats.total_edges) / (stats.total_nodes * (stats.total_nodes - 1)) if stats.total_nodes > 1 else 0
        }


def create_memory_optimized_graph(max_memory_mb: int = 512) -> MemoryOptimizedRouteGraph:
    """Create memory-optimized route graph"""
    return MemoryOptimizedRouteGraph(max_memory_mb)


def optimize_large_graph(graph: MemoryOptimizedRouteGraph) -> Dict[str, int]:
    """Optimize large route graph"""
    optimizer = RouteGraphOptimizer(graph)
    return optimizer.optimize_graph_structure()
