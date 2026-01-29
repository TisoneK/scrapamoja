"""
RouteGraph entity

Network of interconnected navigation routes with weighted relationships and traversal costs.
Conforms to Constitution Principle III - Deep Modularity.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import json
import networkx as nx

from .route import NavigationRoute


@dataclass
class GraphMetadata:
    """Metadata for route graph creation and analysis"""
    
    created_by: str = "navigation_system"
    creation_method: str = "dom_discovery"
    max_depth: int = 3
    total_pages_analyzed: int = 0
    discovery_duration_seconds: float = 0.0
    graph_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            'created_by': self.created_by,
            'creation_method': self.creation_method,
            'max_depth': self.max_depth,
            'total_pages_analyzed': self.total_pages_analyzed,
            'discovery_duration_seconds': self.discovery_duration_seconds,
            'graph_version': self.graph_version
        }


@dataclass
class RouteGraph:
    """Network of interconnected navigation routes"""
    
    # Core identification
    graph_id: str
    
    # Route storage
    routes: Dict[str, NavigationRoute] = field(default_factory=dict)
    
    # Graph structure (using NetworkX for algorithms)
    _networkx_graph: Optional[nx.DiGraph] = field(default=None, init=False)
    
    # Adjacency matrix for quick lookups
    adjacency_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Metadata
    graph_metadata: GraphMetadata = field(default_factory=GraphMetadata)
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self) -> None:
        """Initialize graph after dataclass creation"""
        self._networkx_graph = nx.DiGraph()
        self._validate_graph()
    
    def _validate_graph(self) -> None:
        """Validate graph data according to business rules"""
        if not self.graph_id:
            raise ValueError("Graph ID cannot be empty")
        
        # Validate that all route IDs in adjacency matrix exist in routes
        for source_id, connections in self.adjacency_matrix.items():
            if source_id not in self.routes:
                raise ValueError(f"Source route {source_id} not found in routes")
            
            for target_id, weight in connections.items():
                if target_id not in self.routes:
                    raise ValueError(f"Target route {target_id} not found in routes")
                
                if not isinstance(weight, (int, float)) or weight <= 0:
                    raise ValueError(f"Invalid weight {weight} for connection {source_id}->{target_id}")
    
    def add_route(self, route: NavigationRoute) -> None:
        """Add a route to the graph"""
        if route.route_id in self.routes:
            raise ValueError(f"Route {route.route_id} already exists in graph")
        
        self.routes[route.route_id] = route
        self._networkx_graph.add_node(route.route_id, route=route)
        self.last_updated = datetime.utcnow()
    
    def remove_route(self, route_id: str) -> None:
        """Remove a route from the graph"""
        if route_id not in self.routes:
            raise ValueError(f"Route {route_id} not found in graph")
        
        del self.routes[route_id]
        self._networkx_graph.remove_node(route_id)
        
        # Remove from adjacency matrix
        if route_id in self.adjacency_matrix:
            del self.adjacency_matrix[route_id]
        
        for source_id in self.adjacency_matrix:
            if route_id in self.adjacency_matrix[source_id]:
                del self.adjacency_matrix[source_id][route_id]
        
        self.last_updated = datetime.utcnow()
    
    def add_connection(
        self, 
        source_route_id: str, 
        target_route_id: str, 
        weight: float = 1.0
    ) -> None:
        """Add a weighted connection between routes"""
        if source_route_id not in self.routes:
            raise ValueError(f"Source route {source_route_id} not found")
        
        if target_route_id not in self.routes:
            raise ValueError(f"Target route {target_route_id} not found")
        
        if weight <= 0:
            raise ValueError("Connection weight must be positive")
        
        # Add to NetworkX graph
        self._networkx_graph.add_edge(
            source_route_id, 
            target_route_id, 
            weight=weight
        )
        
        # Add to adjacency matrix
        if source_route_id not in self.adjacency_matrix:
            self.adjacency_matrix[source_route_id] = {}
        
        self.adjacency_matrix[source_route_id][target_route_id] = weight
        self.last_updated = datetime.utcnow()
    
    def remove_connection(self, source_route_id: str, target_route_id: str) -> None:
        """Remove a connection between routes"""
        if source_route_id not in self.adjacency_matrix:
            return
        
        if target_route_id in self.adjacency_matrix[source_route_id]:
            del self.adjacency_matrix[source_route_id][target_route_id]
        
        # Remove from NetworkX graph
        if self._networkx_graph.has_edge(source_route_id, target_route_id):
            self._networkx_graph.remove_edge(source_route_id, target_route_id)
        
        self.last_updated = datetime.utcnow()
    
    def get_route(self, route_id: str) -> Optional[NavigationRoute]:
        """Get a route by ID"""
        return self.routes.get(route_id)
    
    def get_connections(self, route_id: str) -> Dict[str, float]:
        """Get all outgoing connections from a route"""
        return self.adjacency_matrix.get(route_id, {})
    
    def get_incoming_connections(self, route_id: str) -> Dict[str, float]:
        """Get all incoming connections to a route"""
        incoming = {}
        for source_id, connections in self.adjacency_matrix.items():
            if route_id in connections:
                incoming[source_id] = connections[route_id]
        return incoming
    
    def find_shortest_path(
        self, 
        source_route_id: str, 
        target_route_id: str
    ) -> Optional[List[str]]:
        """Find shortest path between routes using Dijkstra's algorithm"""
        try:
            path = nx.shortest_path(
                self._networkx_graph, 
                source_route_id, 
                target_route_id, 
                weight='weight'
            )
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def find_all_paths(
        self, 
        source_route_id: str, 
        target_route_id: str,
        max_length: int = 10
    ) -> List[List[str]]:
        """Find all simple paths between routes"""
        try:
            paths = list(nx.all_simple_paths(
                self._networkx_graph,
                source_route_id,
                target_route_id,
                cutoff=max_length
            ))
            return paths
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    def calculate_path_weight(self, path: List[str]) -> float:
        """Calculate total weight of a path"""
        if len(path) < 2:
            return 0.0
        
        total_weight = 0.0
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            if target in self.adjacency_matrix.get(source, {}):
                total_weight += self.adjacency_matrix[source][target]
            else:
                # No direct connection found
                return float('inf')
        
        return total_weight
    
    def get_connected_components(self) -> List[Set[str]]:
        """Get all connected components in the graph"""
        return list(nx.weakly_connected_components(self._networkx_graph))
    
    def is_connected(self) -> bool:
        """Check if the graph is fully connected"""
        return nx.is_weakly_connected(self._networkx_graph)
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """Get statistics about the route graph"""
        total_routes = len(self.routes)
        total_connections = sum(len(connections) for connections in self.adjacency_matrix.values())
        
        # Calculate degree statistics
        in_degrees = dict(self._networkx_graph.in_degree())
        out_degrees = dict(self._networkx_graph.out_degree())
        
        avg_in_degree = sum(in_degrees.values()) / total_routes if total_routes > 0 else 0
        avg_out_degree = sum(out_degrees.values()) / total_routes if total_routes > 0 else 0
        
        # Risk distribution
        risk_scores = [route.detection_risk for route in self.routes.values()]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        max_risk = max(risk_scores) if risk_scores else 0
        min_risk = min(risk_scores) if risk_scores else 0
        
        return {
            'total_routes': total_routes,
            'total_connections': total_connections,
            'connected_components': len(self.get_connected_components()),
            'is_connected': self.is_connected(),
            'average_in_degree': avg_in_degree,
            'average_out_degree': avg_out_degree,
            'average_detection_risk': avg_risk,
            'max_detection_risk': max_risk,
            'min_detection_risk': min_risk,
            'production_ready_routes': sum(1 for route in self.routes.values() if route.is_production_ready()),
            'preferred_routes': sum(1 for route in self.routes.values() if route.is_preferred_route())
        }
    
    def filter_routes_by_risk(self, max_risk: float) -> List[NavigationRoute]:
        """Get routes with detection risk below threshold"""
        return [route for route in self.routes.values() if route.detection_risk <= max_risk]
    
    def filter_routes_by_confidence(self, min_confidence: float) -> List[NavigationRoute]:
        """Get routes with selector confidence above threshold"""
        return [route for route in self.routes.values() if route.selector_confidence >= min_confidence]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary representation"""
        return {
            'graph_id': self.graph_id,
            'routes': {
                route_id: route.to_dict()
                for route_id, route in self.routes.items()
            },
            'adjacency_matrix': self.adjacency_matrix,
            'graph_metadata': self.graph_metadata.to_dict(),
            'last_updated': self.last_updated.isoformat(),
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteGraph':
        """Create graph from dictionary representation"""
        graph = cls(
            graph_id=data['graph_id'],
            adjacency_matrix=data.get('adjacency_matrix', {}),
            graph_metadata=GraphMetadata(**data.get('graph_metadata', {}))
        )
        
        # Add routes
        for route_id, route_data in data.get('routes', {}).items():
            from .route import NavigationRoute
            route = NavigationRoute.from_dict(route_data)
            graph.routes[route_id] = route
            graph._networkx_graph.add_node(route_id, route=route)
        
        # Add connections to NetworkX graph
        for source_id, connections in graph.adjacency_matrix.items():
            for target_id, weight in connections.items():
                graph._networkx_graph.add_edge(source_id, target_id, weight=weight)
        
        # Set timestamps
        if 'created_at' in data:
            graph.created_at = datetime.fromisoformat(data['created_at'])
        if 'last_updated' in data:
            graph.last_updated = datetime.fromisoformat(data['last_updated'])
        
        return graph
    
    def to_json(self) -> str:
        """Convert graph to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RouteGraph':
        """Create graph from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
