"""
Intelligent path planning

Calculate optimal navigation paths between any two points in web applications,
considering detection risk and success probability.
Conforms to Constitution Principle I - Selector-First Engineering.
"""

import asyncio
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime

from .interfaces import IPathPlanning
from .models import PathPlan, RouteStep, NavigationContext, NavigationRoute
from .exceptions import PathPlanningError
from .integrations.stealth_integration import StealthSystemIntegration
from .logging_config import get_navigation_logger, set_correlation_id, generate_correlation_id


class PathPlanning(IPathPlanning):
    """Intelligent path planning implementation"""
    
    def __init__(
        self,
        stealth_system_client=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize path planning with dependencies"""
        self.logger = get_navigation_logger("path_planning")
        self.config = config or {}
        
        # Initialize stealth integration
        self.stealth_integration = StealthSystemIntegration(stealth_system_client)
        
        # Planning state
        self._correlation_id: Optional[str] = None
        
        # Algorithm weights for path evaluation
        self.risk_weight = self.config.get("risk_weight", 0.4)
        self.time_weight = self.config.get("time_weight", 0.3)
        self.success_weight = self.config.get("success_weight", 0.3)
        
        # NetworkX graph cache
        self._route_graph_cache: Optional[nx.DiGraph] = None
        self._graph_cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = self.config.get("graph_cache_ttl", 300)  # 5 minutes
    
    async def plan_optimal_path(
        self,
        source_context: str,
        target_destination: str,
        risk_tolerance: float = 0.3
    ) -> PathPlan:
        """Calculate optimal navigation path"""
        start_time = datetime.utcnow()
        
        # Generate correlation ID for this planning session
        self._correlation_id = generate_correlation_id()
        set_correlation_id(self._correlation_id)
        
        self.logger.path_planning_start(source_context, target_destination)
        
        try:
            # Create path plan
            plan = PathPlan(
                plan_id=f"plan_{self._correlation_id}",
                source_context=source_context,
                target_destination=target_destination
            )
            
            # This would integrate with route discovery to get available routes
            # For now, create a placeholder implementation
            route_graph = await self._get_route_graph()
            
            # Find optimal path using algorithms
            optimal_path = await self._find_optimal_path(
                route_graph, 
                source_context, 
                target_destination,
                risk_tolerance
            )
            
            if not optimal_path:
                raise PathPlanningError(
                    f"No path found from {source_context} to {target_destination}",
                    "NO_PATH_FOUND",
                    {
                        "source_context": source_context,
                        "target_destination": target_destination,
                        "correlation_id": self._correlation_id
                    }
                )
            
            # Create route steps from path
            route_steps = await self._create_route_steps(optimal_path)
            plan.route_sequence = route_steps
            
            # Calculate path metrics
            await self._calculate_path_metrics(plan)
            
            # Generate alternative paths
            alternatives = await self.generate_alternatives(plan, 3)
            plan.fallback_plans = [alt.plan_id for alt in alternatives]
            
            # Update plan metadata
            planning_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            plan.plan_metadata.planning_algorithm = "hybrid_dijkstra_astar"
            plan.plan_metadata.risk_tolerance = risk_tolerance
            plan.plan_metadata.alternative_count = len(alternatives)
            
            self.logger.path_planning_complete(
                len(route_steps),
                plan.total_risk_score,
                planning_duration
            )
            
            return plan
            
        except Exception as e:
            self.logger.error(
                f"Path planning failed: {str(e)}",
                source_context=source_context,
                target_destination=target_destination,
                correlation_id=self._correlation_id
            )
            raise PathPlanningError(
                f"Failed to plan path from {source_context} to {target_destination}: {str(e)}",
                "PATH_PLANNING_FAILED",
                {
                    "source_context": source_context,
                    "target_destination": target_destination,
                    "correlation_id": self._correlation_id
                }
            )
    
    async def evaluate_path_risk(
        self,
        path_plan: PathPlan
    ) -> float:
        """Evaluate detection risk for navigation path"""
        try:
            set_correlation_id(self._correlation_id)
            
            if not path_plan.route_sequence:
                return 0.0
            
            total_risk = 0.0
            route_risks = []
            
            # Evaluate risk for each step in the path
            for step in path_plan.route_sequence:
                step_risk = await self._evaluate_step_risk(step)
                route_risks.append(step_risk)
                total_risk += step_risk
            
            # Calculate average risk with weighting for longer paths
            path_length_factor = len(path_plan.route_sequence) / 10.0  # Normalize to 10 steps
            average_risk = total_risk / len(path_plan.route_sequence)
            weighted_risk = average_risk * (1 + path_length_factor * 0.1)
            
            # Ensure risk is within bounds
            final_risk = min(1.0, max(0.0, weighted_risk))
            
            self.logger.debug(
                "Path risk evaluation completed",
                plan_id=path_plan.plan_id,
                step_count=len(path_plan.route_sequence),
                average_risk=average_risk,
                weighted_risk=weighted_risk,
                final_risk=final_risk
            )
            
            return final_risk
            
        except Exception as e:
            self.logger.error(
                f"Path risk evaluation failed: {str(e)}",
                plan_id=path_plan.plan_id
            )
            raise PathPlanningError(
                f"Failed to evaluate path risk for {path_plan.plan_id}: {str(e)}",
                "RISK_EVALUATION_FAILED",
                {"plan_id": path_plan.plan_id}
            )
    
    async def generate_alternatives(
        self,
        primary_plan: PathPlan,
        max_alternatives: int = 3
    ) -> List[PathPlan]:
        """Generate alternative navigation paths"""
        try:
            set_correlation_id(self._correlation_id)
            
            alternatives = []
            route_graph = await self._get_route_graph()
            
            # Generate alternative paths using different strategies
            alternative_strategies = [
                "minimize_risk",
                "minimize_time", 
                "maximize_success",
                "balanced"
            ]
            
            for strategy in alternative_strategies[:max_alternatives]:
                try:
                    alt_plan = await self._generate_alternative_path(
                        route_graph,
                        primary_plan.source_context,
                        primary_plan.target_destination,
                        strategy
                    )
                    
                    if alt_plan and alt_plan.plan_id != primary_plan.plan_id:
                        alternatives.append(alt_plan)
                        
                except Exception as e:
                    self.logger.warning(
                        f"Failed to generate alternative path with strategy {strategy}: {str(e)}",
                        strategy=strategy
                    )
            
            self.logger.debug(
                "Alternative paths generated",
                primary_plan_id=primary_plan.plan_id,
                alternatives_count=len(alternatives),
                strategies_used=[alt.plan_metadata.get("strategy", "unknown") for alt in alternatives]
            )
            
            return alternatives
            
        except Exception as e:
            self.logger.error(
                f"Alternative path generation failed: {str(e)}",
                primary_plan_id=primary_plan.plan_id
            )
            raise PathPlanningError(
                f"Failed to generate alternatives for {primary_plan.plan_id}: {str(e)}",
                "ALTERNATIVE_GENERATION_FAILED",
                {"primary_plan_id": primary_plan.plan_id}
            )
    
    async def _get_route_graph(self) -> Any:
        """Get route graph for planning"""
        # This would integrate with route discovery to get the current route graph
        # For now, return a placeholder implementation
        
        # Create a simple test graph
        graph = nx.DiGraph()
        
        # Add some test nodes and edges
        nodes = ["home", "about", "contact", "products", "cart", "checkout"]
        for node in nodes:
            graph.add_node(node)
        
        # Add edges with weights (risk + time)
        edges = [
            ("home", "about", 1.2),
            ("home", "products", 1.0),
            ("home", "contact", 1.1),
            ("products", "cart", 1.5),
            ("cart", "checkout", 1.8),
            ("about", "contact", 1.3)
        ]
        
        for source, target, weight in edges:
            graph.add_edge(source, target, weight=weight)
        
        return graph
    
    async def _find_optimal_path(
        self,
        route_graph,
        source: str,
        target: str,
        risk_tolerance: float
    ) -> List[str]:
        """Find optimal path using hybrid algorithm"""
        try:
            # Try Dijkstra first for shortest path
            try:
                dijkstra_path = nx.dijkstra_path(route_graph, source, target)
                dijkstra_weight = nx.dijkstra_path_length(route_graph, source, target)
            except nx.NetworkXNoPath:
                dijkstra_path = None
                dijkstra_weight = float('inf')
            
            # Try A* for heuristic optimization
            try:
                astar_path = nx.astar_path(route_graph, source, target)
                astar_weight = sum(
                    route_graph[u][v]['weight'] 
                    for u, v in zip(astar_path[:-1], astar_path[1:])
                )
            except (nx.NetworkXNoPath, AttributeError):
                astar_path = None
                astar_weight = float('inf')
            
            # Choose best path based on criteria
            if dijkstra_path and astar_path:
                # Compare paths based on multiple factors
                dijkstra_score = await self._evaluate_path_score(
                    dijkstra_path, dijkstra_weight, risk_tolerance
                )
                astar_score = await self._evaluate_path_score(
                    astar_path, astar_weight, risk_tolerance
                )
                
                if astar_score > dijkstra_score:
                    return astar_path
                else:
                    return dijkstra_path
            elif dijkstra_path:
                return dijkstra_path
            elif astar_path:
                return astar_path
            else:
                return []
                
        except Exception as e:
            self.logger.error(
                f"Optimal path finding failed: {str(e)}",
                source=source,
                target=target
            )
            raise PathPlanningError(
                f"Failed to find optimal path from {source} to {target}: {str(e)}",
                "OPTIMAL_PATH_FAILED",
                {"source": source, "target": target}
            )
    
    async def _evaluate_path_score(
        self,
        path: List[str],
        weight: float,
        risk_tolerance: float
    ) -> float:
        """Evaluate path score based on multiple criteria"""
        # Calculate path length penalty
        length_penalty = len(path) * 0.1
        
        # Calculate risk penalty
        risk_penalty = max(0, weight - risk_tolerance) * 2.0
        
        # Calculate time penalty (weight is time-based)
        time_penalty = weight * 0.5
        
        # Combined score (lower is better)
        total_score = weight + length_penalty + risk_penalty + time_penalty
        
        return 1.0 / (1.0 + total_score)  # Convert to higher-is-better
    
    async def _create_route_steps(self, path: List[str]) -> List[RouteStep]:
        """Create route steps from path"""
        steps = []
        
        for i, (source, target) in enumerate(zip(path[:-1], path[1:])):
            step = RouteStep(
                step_number=i + 1,
                route_id=f"{source}_to_{target}",
                action_type="navigate",
                target_url=target,
                expected_delay=1.0,  # Default delay
                step_description=f"Navigate from {source} to {target}"
            )
            steps.append(step)
        
        return steps
    
    async def _calculate_path_metrics(self, plan: PathPlan) -> None:
        """Calculate path metrics"""
        if not plan.route_sequence:
            plan.estimated_duration = 0.0
            plan.total_risk_score = 0.0
            return
        
        # Calculate estimated duration
        total_duration = sum(step.expected_delay for step in plan.route_sequence)
        plan.estimated_duration = total_duration
        
        # Calculate total risk score
        total_risk = 0.0
        for step in plan.route_sequence:
            step_risk = await self._evaluate_step_risk(step)
            total_risk += step_risk
        
        plan.total_risk_score = total_risk / len(plan.route_sequence)
    
    async def _evaluate_step_risk(self, step: RouteStep) -> float:
        """Evaluate risk for individual step"""
        # Get timing patterns for this interaction type
        timing_patterns = await self.stealth_integration.get_timing_patterns(
            step.action_type
        )
        
        # Base risk assessment
        base_risk = 0.1  # Low base risk
        
        # Adjust risk based on step characteristics
        if step.action_type == "form_submit":
            base_risk += 0.2
        elif step.action_type == "javascript_execution":
            base_risk += 0.3
        elif step.action_type == "navigate":
            base_risk += 0.1
        
        # Adjust based on timing
        if step.expected_delay < timing_patterns.get("min_delay", 0.5):
            base_risk += 0.2  # Too fast is suspicious
        
        # Ensure risk is within bounds
        return min(1.0, max(0.0, base_risk))
    
    async def _generate_alternative_path(
        self,
        route_graph,
        source: str,
        target: str,
        strategy: str
    ) -> Optional[PathPlan]:
        """Generate alternative path using specific strategy"""
        try:
            plan = PathPlan(
                plan_id=f"alt_{strategy}_{self._correlation_id}_{hash(strategy) % 1000}",
                source_context=source,
                target_destination=target
            )
            
            if strategy == "minimize_risk":
                path = await self._find_min_risk_path(route_graph, source, target)
            elif strategy == "minimize_time":
                path = await self._find_fastest_path(route_graph, source, target)
            elif strategy == "maximize_success":
                path = await self._find_most_reliable_path(route_graph, source, target)
            elif strategy == "balanced":
                path = await self._find_balanced_path(route_graph, source, target)
            else:
                return None
            
            if not path:
                return None
            
            # Create route steps
            route_steps = await self._create_route_steps(path)
            plan.route_sequence = route_steps
            
            # Calculate metrics
            await self._calculate_path_metrics(plan)
            
            # Set strategy in metadata
            plan.plan_metadata.planning_algorithm = f"alternative_{strategy}"
            plan.plan_metadata.strategy = strategy
            
            return plan
            
        except Exception as e:
            self.logger.warning(
                f"Failed to generate alternative path with strategy {strategy}: {str(e)}",
                strategy=strategy
            )
            return None
    
    async def _find_min_risk_path(self, route_graph, source, target):
        """Find path with minimum risk"""
        # Modify edge weights to prioritize low-risk paths
        modified_graph = route_graph.copy()
        
        for u, v, data in modified_graph.edges(data=True):
            # Increase weight for higher-risk edges
            modified_graph[u][v]['weight'] = data['weight'] * 1.5
        
        try:
            return nx.dijkstra_path(modified_graph, source, target)
        except nx.NetworkXNoPath:
            return []
    
    async def _find_fastest_path(self, route_graph, source, target):
        """Find fastest path"""
        try:
            return nx.dijkstra_path(route_graph, source, target)
        except nx.NetworkXNoPath:
            return []
    
    async def _find_most_reliable_path(self, route_graph, source, target):
        """Find most reliable path"""
        # Use shortest path as proxy for reliability
        try:
            return nx.shortest_path(route_graph, source, target)
        except nx.NetworkXNoPath:
            return []
    
    async def _find_balanced_path(self, route_graph, source, target):
        """Find balanced path"""
        # Use standard Dijkstra for balanced approach
        try:
            return nx.dijkstra_path(route_graph, source, target)
        except nx.NetworkXNoPath:
            return []
    
    # NetworkX Graph Integration Methods
    
    async def build_route_graph(
        self,
        routes: List[NavigationRoute],
        connections: Optional[Dict[str, Dict[str, float]]] = None
    ) -> nx.DiGraph:
        """Build NetworkX graph from routes and connections"""
        graph = nx.DiGraph()
        
        # Add nodes (routes)
        for route in routes:
            graph.add_node(route.route_id, route=route)
        
        # Add edges (connections)
        if connections:
            for source_id, target_connections in connections.items():
                for target_id, weight in target_connections.items():
                    if source_id in graph.nodes and target_id in graph.nodes:
                        graph.add_edge(source_id, target_id, weight=weight)
        
        return graph
    
    async def update_route_graph(
        self,
        graph: nx.DiGraph,
        new_routes: List[NavigationRoute],
        new_connections: Optional[Dict[str, Dict[str, float]]] = None
    ) -> nx.DiGraph:
        """Update existing route graph with new routes and connections"""
        updated_graph = graph.copy()
        
        # Add new routes
        for route in new_routes:
            if route.route_id not in updated_graph.nodes:
                updated_graph.add_node(route.route_id, route=route)
        
        # Add new connections
        if new_connections:
            for source_id, target_connections in new_connections.items():
                for target_id, weight in target_connections.items():
                    if source_id in updated_graph.nodes and target_id in updated_graph.nodes:
                        updated_graph.add_edge(source_id, target_id, weight=weight)
        
        return updated_graph
    
    def get_graph_statistics(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Get comprehensive graph statistics"""
        stats = {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "is_directed": graph.is_directed(),
            "is_connected": nx.is_weakly_connected(graph),
            "density": nx.density(graph),
            "average_clustering": nx.average_clustering(graph.to_undirected()),
            "number_of_components": nx.number_weakly_connected_components(graph)
        }
        
        # Calculate centrality measures
        if graph.number_of_nodes() > 0:
            try:
                in_degree_centrality = nx.in_degree_centrality(graph)
                out_degree_centrality = nx.out_degree_centrality(graph)
                betweenness_centrality = nx.betweenness_centrality(graph)
                closeness_centrality = nx.closeness_centrality(graph)
                
                stats["centrality"] = {
                    "max_in_degree": max(in_degree_centrality.values()) if in_degree_centrality else 0,
                    "max_out_degree": max(out_degree_centrality.values()) if out_degree_centrality else 0,
                    "max_betweenness": max(betweenness_centrality.values()) if betweenness_centrality else 0,
                    "max_closeness": max(closeness_centrality.values()) if closeness_centrality else 0
                }
            except Exception:
                stats["centrality"] = {"error": "Failed to calculate centrality measures"}
        
        return stats
    
    # Advanced Path Algorithms
    
    async def find_k_shortest_paths(
        self,
        graph: nx.DiGraph,
        source: str,
        target: str,
        k: int = 3
    ) -> List[List[str]]:
        """Find k shortest paths between source and target"""
        try:
            paths = list(nx.shortest_simple_paths(graph, source, target, cutoff=k))
            return paths[:k]
        except nx.NetworkXNoPath:
            return []
    
    async def find_all_simple_paths(
        self,
        graph: nx.DiGraph,
        source: str,
        target: str,
        max_length: int = 10
    ) -> List[List[str]]:
        """Find all simple paths between source and target"""
        try:
            paths = list(nx.all_simple_paths(graph, source, target, cutoff=max_length))
            return paths
        except nx.NetworkXNoPath:
            return []
    
    async def calculate_path_weights(
        self,
        graph: nx.DiGraph,
        paths: List[List[str]]
    ) -> List[float]:
        """Calculate total weights for multiple paths"""
        weights = []
        
        for path in paths:
            if len(path) < 2:
                weights.append(0.0)
                continue
            
            total_weight = 0.0
            for i in range(len(path) - 1):
                source = path[i]
                target = path[i + 1]
                
                if graph.has_edge(source, target):
                    total_weight += graph[source][target].get('weight', 1.0)
                else:
                    total_weight = float('inf')
                    break
            
            weights.append(total_weight)
        
        return weights
    
    async def find_minimum_spanning_tree(
        self,
        graph: nx.DiGraph
    ) -> nx.Graph:
        """Find minimum spanning tree of directed graph"""
        try:
            # Convert to undirected for MST
            undirected_graph = graph.to_undirected()
            mst = nx.minimum_spanning_tree(undirected_graph)
            return mst
        except Exception:
            return nx.Graph()
    
    async def find_strongly_connected_components(
        self,
        graph: nx.DiGraph
    ) -> List[Set[str]]:
        """Find strongly connected components"""
        return list(nx.strongly_connected_components(graph))
    
    async def calculate_page_rank(
        self,
        graph: nx.DiGraph,
        alpha: float = 0.85,
        max_iter: int = 100
    ) -> Dict[str, float]:
        """Calculate PageRank for all nodes"""
        try:
            page_rank = nx.pagerank(graph, alpha=alpha, max_iter=max_iter)
            return page_rank
        except Exception:
            return {}
    
    # Path Optimization Methods
    
    async def optimize_path_for_speed(
        self,
        graph: nx.DiGraph,
        source: str,
        target: str
    ) -> List[str]:
        """Find fastest path (minimum time)"""
        try:
            return nx.dijkstra_path(graph, source, target, weight='time')
        except (nx.NetworkXNoPath, KeyError):
            return []
    
    async def optimize_path_for_safety(
        self,
        graph: nx.DiGraph,
        source: str,
        target: str
    ) -> List[str]:
        """Find safest path (minimum risk)"""
        try:
            # Create modified graph with risk weights
            safe_graph = graph.copy()
            
            for u, v, data in safe_graph.edges(data=True):
                # Increase weight for higher-risk edges
                risk_weight = data.get('risk', 0.1)
                safe_weight = data.get('weight', 1.0) * (1 + risk_weight * 2)
                safe_graph[u][v]['weight'] = safe_weight
            
            return nx.dijkstra_path(safe_graph, source, target)
        except (nx.NetworkXNoPath, KeyError):
            return []
    
    async def optimize_path_for_reliability(
        self,
        graph: nx.DiGraph,
        source: str,
        target: str
    ) -> List[str]:
        """Find most reliable path (highest success rate)"""
        try:
            # Create modified graph with reliability weights
            reliable_graph = graph.copy()
            
            for u, v, data in reliable_graph.edges(data=True):
                # Decrease weight for higher reliability
                reliability = data.get('reliability', 0.8)
                reliable_weight = data.get('weight', 1.0) * (2.0 - reliability)
                reliable_graph[u][v]['weight'] = reliable_weight
            
            return nx.dijkstra_path(reliable_graph, source, target)
        except (nx.NetworkXNoPath, KeyError):
            return []
    
    # Graph Analysis Methods
    
    async def analyze_path_complexity(
        self,
        graph: nx.DiGraph,
        path: List[str]
    ) -> Dict[str, Any]:
        """Analyze complexity of a path"""
        if not path:
            return {"complexity_score": 0.0, "length": 0}
        
        complexity_factors = {
            "length": len(path),
            "cycles": self._count_cycles_in_path(graph, path),
            "branches": self._count_branches_at_nodes(graph, path),
            "backtracks": self._count_backtracks(graph, path)
        }
        
        # Calculate complexity score
        complexity_score = (
            complexity_factors["length"] * 0.3 +
            complexity_factors["cycles"] * 0.4 +
            complexity_factors["branches"] * 0.2 +
            complexity_factors["backtracks"] * 0.1
        )
        
        return {
            "complexity_score": complexity_score,
            "factors": complexity_factors
        }
    
    def _count_cycles_in_path(self, graph: nx.DiGraph, path: List[str]) -> int:
        """Count cycles in a path"""
        cycles = 0
        try:
            # Simple cycle detection
            for i in range(len(path)):
                for j in range(i + 1, len(path)):
                    if graph.has_edge(path[j], path[i]):
                        cycles += 1
        except:
            pass
        return cycles
    
    def _count_branches_at_nodes(self, graph: nx.DiGraph, path: List[str]) -> int:
        """Count number of branches at path nodes"""
        branches = 0
        for node in path:
            branches += graph.out_degree(node) - 1  # Subtract 1 for the path edge
        return max(0, branches)
    
    def _count_backtracks(self, graph: nx.DiGraph, path: List[str]) -> int:
        """Count backtracks in path"""
        backtracks = 0
        for i in range(len(path) - 1):
            current = path[i]
            next_node = path[i + 1]
            
            # Check if there's an edge that goes backwards in the path
            for j in range(i):
                if path[j] == next_node and graph.has_edge(current, path[j]):
                    backtracks += 1
                    break
        
        return backtracks
