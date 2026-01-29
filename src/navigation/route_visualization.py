"""
Route visualization and analysis capabilities

Provides visualization and analysis tools for navigation routes including graph
visualization, path analysis, performance metrics, and interactive dashboards.
"""

import json
import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import networkx as nx

from .models import RouteGraph, NavigationRoute, PathPlan, RouteType, TraversalMethod
from .logging_config import get_navigation_logger


@dataclass
class RouteAnalysisMetrics:
    """Route analysis metrics"""
    total_routes: int
    route_types: Dict[str, int]
    traversal_methods: Dict[str, int]
    average_confidence: float
    average_risk: float
    average_duration: float
    high_risk_routes: int
    low_confidence_routes: int
    disconnected_nodes: int
    graph_density: float
    clustering_coefficient: float


@dataclass
class PathAnalysisResult:
    """Path analysis result"""
    path_id: str
    source: str
    target: str
    path_length: int
    total_risk: float
    total_duration: float
    confidence_score: float
    route_types: List[str]
    critical_nodes: List[str]
    bottlenecks: List[str]


@dataclass
class VisualizationNode:
    """Visualization node data"""
    id: str
    label: str
    x: float
    y: float
    size: float
    color: str
    type: str
    metadata: Dict[str, Any]


@dataclass
class VisualizationEdge:
    """Visualization edge data"""
    source: str
    target: str
    label: str
    width: float
    color: str
    type: str
    metadata: Dict[str, Any]


class RouteAnalyzer:
    """Route analysis and metrics calculator"""
    
    def __init__(self):
        """Initialize route analyzer"""
        self.logger = get_navigation_logger("route_analyzer")
    
    def analyze_routes(self, graph: RouteGraph) -> RouteAnalysisMetrics:
        """Analyze routes and calculate metrics"""
        try:
            self.logger.info(
                "Analyzing routes",
                graph_id=graph.graph_id,
                routes_count=len(graph.routes)
            )
            
            # Calculate basic metrics
            total_routes = len(graph.routes)
            
            # Count route types
            route_types = {}
            for route in graph.routes.values():
                route_types[route.route_type.value] = route_types.get(route.route_type.value, 0) + 1
            
            # Count traversal methods
            traversal_methods = {}
            for route in graph.routes.values():
                traversal_methods[route.traversal_method.value] = traversal_methods.get(route.traversal_method.value, 0) + 1
            
            # Calculate averages
            confidence_scores = [route.confidence_score for route in graph.routes.values()]
            risk_scores = [route.risk_score for route in graph.routes.values()]
            durations = [route.estimated_duration for route in graph.routes.values()]
            
            average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            average_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
            average_duration = sum(durations) / len(durations) if durations else 0.0
            
            # Count problematic routes
            high_risk_routes = len([r for r in graph.routes.values() if r.risk_score > 0.7])
            low_confidence_routes = len([r for r in graph.routes.values() if r.confidence_score < 0.5])
            
            # Graph metrics
            nx_graph = self._create_networkx_graph(graph)
            disconnected_nodes = len(list(nx.isolates(nx_graph)))
            graph_density = nx.density(nx_graph)
            
            # Clustering coefficient
            clustering_coefficient = nx.average_clustering(nx_graph) if len(nx_graph.nodes()) > 1 else 0.0
            
            metrics = RouteAnalysisMetrics(
                total_routes=total_routes,
                route_types=route_types,
                traversal_methods=traversal_methods,
                average_confidence=average_confidence,
                average_risk=average_risk,
                average_duration=average_duration,
                high_risk_routes=high_risk_routes,
                low_confidence_routes=low_confidence_routes,
                disconnected_nodes=disconnected_nodes,
                graph_density=graph_density,
                clustering_coefficient=clustering_coefficient
            )
            
            self.logger.info(
                "Route analysis completed",
                total_routes=total_routes,
                average_confidence=average_confidence,
                average_risk=average_risk
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(
                f"Failed to analyze routes: {str(e)}",
                graph_id=graph.graph_id
            )
            raise
    
    def analyze_paths(self, graph: RouteGraph, source: str, target: str) -> List[PathAnalysisResult]:
        """Analyze all paths between source and target"""
        try:
            self.logger.info(
                "Analyzing paths",
                graph_id=graph.graph_id,
                source=source,
                target=target
            )
            
            nx_graph = self._create_networkx_graph(graph)
            
            if source not in nx_graph or target not in nx_graph:
                return []
            
            # Find all simple paths
            try:
                paths = list(nx.all_simple_paths(nx_graph, source, target, cutoff=10))
            except nx.NetworkXNoPath:
                return []
            
            results = []
            for i, path in enumerate(paths):
                # Calculate path metrics
                path_length = len(path) - 1
                total_risk = 0.0
                total_duration = 0.0
                confidence_scores = []
                route_types = []
                
                for j in range(len(path) - 1):
                    edge_data = nx_graph[path[j]][path[j + 1]]
                    route = edge_data.get('route')
                    
                    if route:
                        total_risk += route.risk_score
                        total_duration += route.estimated_duration
                        confidence_scores.append(route.confidence_score)
                        route_types.append(route.route_type.value)
                
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
                
                # Find critical nodes and bottlenecks
                critical_nodes = self._find_critical_nodes(nx_graph, path)
                bottlenecks = self._find_bottlenecks(nx_graph, path)
                
                result = PathAnalysisResult(
                    path_id=f"path_{i}_{source}_{target}",
                    source=source,
                    target=target,
                    path_length=path_length,
                    total_risk=total_risk,
                    total_duration=total_duration,
                    confidence_score=avg_confidence,
                    route_types=route_types,
                    critical_nodes=critical_nodes,
                    bottlenecks=bottlenecks
                )
                
                results.append(result)
            
            # Sort by confidence score (best first)
            results.sort(key=lambda r: r.confidence_score, reverse=True)
            
            self.logger.info(
                "Path analysis completed",
                paths_found=len(results),
                source=source,
                target=target
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                f"Failed to analyze paths: {str(e)}",
                source=source,
                target=target
            )
            raise
    
    def find_optimal_paths(
        self,
        graph: RouteGraph,
        source: str,
        target: str,
        optimization_criteria: str = "confidence"
    ) -> List[PathAnalysisResult]:
        """Find optimal paths based on criteria"""
        try:
            all_paths = self.analyze_paths(graph, source, target)
            
            if not all_paths:
                return []
            
            # Sort based on optimization criteria
            if optimization_criteria == "confidence":
                all_paths.sort(key=lambda r: r.confidence_score, reverse=True)
            elif optimization_criteria == "risk":
                all_paths.sort(key=lambda r: r.total_risk)
            elif optimization_criteria == "duration":
                all_paths.sort(key=lambda r: r.total_duration)
            elif optimization_criteria == "length":
                all_paths.sort(key=lambda r: r.path_length)
            
            return all_paths[:5]  # Return top 5 optimal paths
            
        except Exception as e:
            self.logger.error(
                f"Failed to find optimal paths: {str(e)}",
                source=source,
                target=target
            )
            raise
    
    def _create_networkx_graph(self, graph: RouteGraph) -> nx.DiGraph:
        """Create NetworkX graph from RouteGraph"""
        nx_graph = nx.DiGraph()
        
        # Add nodes
        for node in graph.nodes:
            nx_graph.add_node(node)
        
        # Add edges with route data
        for route in graph.routes.values():
            if route.source_url in graph.nodes and route.target_url in graph.nodes:
                nx_graph.add_edge(
                    route.source_url,
                    route.target_url,
                    route=route,
                    weight=1.0 - route.confidence_score,  # Lower weight for higher confidence
                    risk=route.risk_score,
                    duration=route.estimated_duration
                )
        
        return nx_graph
    
    def _find_critical_nodes(self, nx_graph: nx.DiGraph, path: List[str]) -> List[str]:
        """Find critical nodes in path"""
        critical_nodes = []
        
        for node in path:
            # Check if node has high betweenness centrality
            try:
                centrality = nx.betweenness_centrality(nx_graph)
                if centrality.get(node, 0) > 0.1:  # Threshold for critical
                    critical_nodes.append(node)
            except:
                pass
        
        return critical_nodes
    
    def _find_bottlenecks(self, nx_graph: nx.DiGraph, path: List[str]) -> List[str]:
        """Find bottleneck nodes in path"""
        bottlenecks = []
        
        for i, node in enumerate(path):
            # Check if node has low degree (potential bottleneck)
            if node in nx_graph:
                in_degree = nx_graph.in_degree(node)
                out_degree = nx_graph.out_degree(node)
                
                if in_degree <= 1 or out_degree <= 1:
                    bottlenecks.append(node)
        
        return bottlenecks


class RouteVisualizer:
    """Route visualization generator"""
    
    def __init__(self):
        """Initialize route visualizer"""
        self.logger = get_navigation_logger("route_visualizer")
    
    def create_visualization_data(
        self,
        graph: RouteGraph,
        layout: str = "spring"
    ) -> Dict[str, Any]:
        """Create visualization data for routes"""
        try:
            self.logger.info(
                "Creating visualization data",
                graph_id=graph.graph_id,
                layout=layout
            )
            
            # Create NetworkX graph
            nx_graph = self._create_networkx_graph(graph)
            
            # Calculate layout
            if layout == "spring":
                pos = nx.spring_layout(nx_graph, k=2, iterations=50)
            elif layout == "circular":
                pos = nx.circular_layout(nx_graph)
            elif layout == "random":
                pos = nx.random_layout(nx_graph)
            else:
                pos = nx.spring_layout(nx_graph)
            
            # Create visualization nodes
            nodes = []
            for node in nx_graph.nodes():
                node_data = self._create_visualization_node(node, pos[node], graph)
                nodes.append(node_data)
            
            # Create visualization edges
            edges = []
            for source, target, data in nx_graph.edges(data=True):
                edge_data = self._create_visualization_edge(source, target, data)
                edges.append(edge_data)
            
            # Calculate graph metrics
            analyzer = RouteAnalyzer()
            metrics = analyzer.analyze_routes(graph)
            
            visualization_data = {
                "graph_id": graph.graph_id,
                "nodes": nodes,
                "edges": edges,
                "layout": layout,
                "metrics": asdict(metrics),
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.logger.info(
                "Visualization data created",
                nodes_count=len(nodes),
                edges_count=len(edges)
            )
            
            return visualization_data
            
        except Exception as e:
            self.logger.error(
                f"Failed to create visualization data: {str(e)}",
                graph_id=graph.graph_id
            )
            raise
    
    def export_to_d3_json(self, graph: RouteGraph, file_path: str) -> None:
        """Export graph to D3.js JSON format"""
        try:
            viz_data = self.create_visualization_data(graph)
            
            # Convert to D3 format
            d3_data = {
                "nodes": [
                    {
                        "id": node["id"],
                        "name": node["label"],
                        "x": node["x"],
                        "y": node["y"],
                        "size": node["size"],
                        "color": node["color"],
                        "type": node["type"]
                    }
                    for node in viz_data["nodes"]
                ],
                "links": [
                    {
                        "source": edge["source"],
                        "target": edge["target"],
                        "value": edge["width"],
                        "label": edge["label"],
                        "color": edge["color"]
                    }
                    for edge in viz_data["edges"]
                ],
                "metrics": viz_data["metrics"]
            }
            
            with open(file_path, 'w') as f:
                json.dump(d3_data, f, indent=2)
            
            self.logger.info(
                "Graph exported to D3 JSON",
                file_path=file_path,
                nodes_count=len(d3_data["nodes"]),
                links_count=len(d3_data["links"])
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to export to D3 JSON: {str(e)}",
                file_path=file_path
            )
            raise
    
    def export_to_cytoscape(self, graph: RouteGraph, file_path: str) -> None:
        """Export graph to Cytoscape JSON format"""
        try:
            viz_data = self.create_visualization_data(graph)
            
            # Convert to Cytoscape format
            cytoscape_data = {
                "elements": {
                    "nodes": [
                        {
                            "data": {
                                "id": node["id"],
                                "label": node["label"],
                                "type": node["type"],
                                "color": node["color"],
                                "size": node["size"]
                            },
                            "position": {
                                "x": node["x"] * 100,  # Scale for Cytoscape
                                "y": node["y"] * 100
                            }
                        }
                        for node in viz_data["nodes"]
                    ],
                    "edges": [
                        {
                            "data": {
                                "id": f"{edge['source']}-{edge['target']}",
                                "source": edge["source"],
                                "target": edge["target"],
                                "label": edge["label"],
                                "type": edge["type"],
                                "color": edge["color"],
                                "width": edge["width"]
                            }
                        }
                        for edge in viz_data["edges"]
                    ]
                },
                "layout": {
                    "name": "preset"
                },
                "style": [
                    {
                        "selector": "node",
                        "style": {
                            "background-color": "data(color)",
                            "width": "data(size)",
                            "height": "data(size)",
                            "label": "data(label)",
                            "font-size": "12px"
                        }
                    },
                    {
                        "selector": "edge",
                        "style": {
                            "line-color": "data(color)",
                            "width": "data(width)",
                            "label": "data(label)",
                            "font-size": "10px"
                        }
                    }
                ]
            }
            
            with open(file_path, 'w') as f:
                json.dump(cytoscape_data, f, indent=2)
            
            self.logger.info(
                "Graph exported to Cytoscape JSON",
                file_path=file_path,
                nodes_count=len(cytoscape_data["elements"]["nodes"]),
                edges_count=len(cytoscape_data["elements"]["edges"])
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to export to Cytoscape JSON: {str(e)}",
                file_path=file_path
            )
            raise
    
    def create_html_dashboard(self, graph: RouteGraph, file_path: str) -> None:
        """Create interactive HTML dashboard"""
        try:
            viz_data = self.create_visualization_data(graph)
            
            # Generate HTML dashboard
            html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Route Analysis Dashboard - {graph_id}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
        }}
        .visualization {{
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 10px;
        }}
        .metrics {{
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 10px;
        }}
        .metric {{
            margin-bottom: 10px;
            padding: 5px;
            background-color: #f5f5f5;
            border-radius: 3px;
        }}
        .node {{
            stroke: #333;
            stroke-width: 1.5px;
        }}
        .link {{
            stroke: #999;
            stroke-opacity: 0.6;
        }}
    </style>
</head>
<body>
    <h1>Route Analysis Dashboard - {graph_id}</h1>
    
    <div class="dashboard">
        <div class="visualization">
            <svg id="graph" width="800" height="600"></svg>
        </div>
        
        <div class="metrics">
            <h3>Graph Metrics</h3>
            <div class="metric"><strong>Total Routes:</strong> {total_routes}</div>
            <div class="metric"><strong>Avg Confidence:</strong> {avg_confidence:.2f}</div>
            <div class="metric"><strong>Avg Risk:</strong> {avg_risk:.2f}</div>
            <div class="metric"><strong>Graph Density:</strong> {graph_density:.2f}</div>
            <div class="metric"><strong>High Risk Routes:</strong> {high_risk_routes}</div>
            <div class="metric"><strong>Low Confidence Routes:</strong> {low_confidence_routes}</div>
        </div>
    </div>
    
    <script>
        // D3.js visualization code
        const graphData = {viz_data_json};
        
        const svg = d3.select("#graph");
        const width = 800;
        const height = 600;
        
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
        
        const link = svg.append("g")
            .selectAll("line")
            .data(graphData.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke", d => d.color)
            .attr("stroke-width", d => d.width);
        
        const node = svg.append("g")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", d => d.size)
            .attr("fill", d => d.color)
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        const label = svg.append("g")
            .selectAll("text")
            .data(graphData.nodes)
            .enter().append("text")
            .text(d => d.label)
            .attr("font-size", "10px")
            .attr("dx", 12)
            .attr("dy", 4);
        
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            label
                .attr("x", d => d.x)
                .attr("y", d => d.y);
        }});
        
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
    </script>
</body>
</html>
            """
            
            # Format metrics
            metrics = viz_data["metrics"]
            html_content = html_template.format(
                graph_id=graph.graph_id,
                total_routes=metrics["total_routes"],
                avg_confidence=metrics["average_confidence"],
                avg_risk=metrics["average_risk"],
                graph_density=metrics["graph_density"],
                high_risk_routes=metrics["high_risk_routes"],
                low_confidence_routes=metrics["low_confidence_routes"],
                viz_data_json=json.dumps(viz_data)
            )
            
            with open(file_path, 'w') as f:
                f.write(html_content)
            
            self.logger.info(
                "HTML dashboard created",
                file_path=file_path
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to create HTML dashboard: {str(e)}",
                file_path=file_path
            )
            raise
    
    def _create_networkx_graph(self, graph: RouteGraph) -> nx.DiGraph:
        """Create NetworkX graph from RouteGraph"""
        nx_graph = nx.DiGraph()
        
        # Add nodes
        for node in graph.nodes:
            nx_graph.add_node(node)
        
        # Add edges with route data
        for route in graph.routes.values():
            if route.source_url in graph.nodes and route.target_url in graph.nodes:
                nx_graph.add_edge(
                    route.source_url,
                    route.target_url,
                    route=route
                )
        
        return nx_graph
    
    def _create_visualization_node(self, node_id: str, pos: Tuple[float, float], graph: RouteGraph) -> VisualizationNode:
        """Create visualization node"""
        # Determine node properties based on URL
        node_type = "standard"
        if "login" in node_id.lower():
            node_type = "authentication"
        elif "admin" in node_id.lower():
            node_type = "admin"
        elif "cart" in node_id.lower() or "checkout" in node_id.lower():
            node_type = "ecommerce"
        
        # Set color based on type
        color_map = {
            "standard": "#3498db",
            "authentication": "#e74c3c",
            "admin": "#f39c12",
            "ecommerce": "#27ae60"
        }
        color = color_map.get(node_type, "#3498db")
        
        # Extract label from URL
        label = node_id.split('/')[-1] if '/' in node_id else node_id
        if len(label) > 20:
            label = label[:17] + "..."
        
        return VisualizationNode(
            id=node_id,
            label=label,
            x=pos[0],
            y=pos[1],
            size=10,
            color=color,
            type=node_type,
            metadata={"url": node_id}
        )
    
    def _create_visualization_edge(self, source: str, target: str, data: Dict[str, Any]) -> VisualizationEdge:
        """Create visualization edge"""
        route = data.get('route')
        
        if route:
            # Set edge properties based on route
            width = max(1, route.confidence_score * 5)
            
            # Set color based on risk
            if route.risk_score > 0.7:
                color = "#e74c3c"  # Red for high risk
            elif route.risk_score > 0.4:
                color = "#f39c12"  # Orange for medium risk
            else:
                color = "#27ae60"  # Green for low risk
            
            label = route.route_type.value
            edge_type = route.traversal_method.value
        else:
            width = 1
            color = "#95a5a6"
            label = "unknown"
            edge_type = "unknown"
        
        return VisualizationEdge(
            source=source,
            target=target,
            label=label,
            width=width,
            color=color,
            type=edge_type,
            metadata=data
        )


def create_route_analyzer() -> RouteAnalyzer:
    """Create route analyzer"""
    return RouteAnalyzer()


def create_route_visualizer() -> RouteVisualizer:
    """Create route visualizer"""
    return RouteVisualizer()
