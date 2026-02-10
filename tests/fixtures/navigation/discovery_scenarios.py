"""
Integration test fixtures for route discovery

Test scenarios for Navigation & Routing Intelligence route discovery functionality.
"""

from typing import Dict, List, Any
from src.navigation.models import NavigationRoute, RouteType, TraversalMethod


class DiscoveryTestScenarios:
    """Test scenarios for route discovery"""
    
    @staticmethod
    def get_simple_website_scenario() -> Dict[str, Any]:
        """Simple website with basic navigation"""
        return {
            "name": "simple_website",
            "base_url": "https://example.com",
            "expected_routes": [
                {
                    "source": "https://example.com",
                    "destination": "https://example.com/about",
                    "type": "link",
                    "method": "click"
                },
                {
                    "source": "https://example.com", 
                    "destination": "https://example.com/contact",
                    "type": "link",
                    "method": "click"
                },
                {
                    "source": "https://example.com",
                    "destination": "https://example.com/search",
                    "type": "form",
                    "method": "form_submit"
                }
            ],
            "max_depth": 2,
            "expected_route_count": 3
        }
    
    @staticmethod
    def get_single_page_app_scenario() -> Dict[str, Any]:
        """Single-page application with client-side routing"""
        return {
            "name": "spa_application",
            "base_url": "https://app.example.com",
            "expected_routes": [
                {
                    "source": "https://app.example.com",
                    "destination": "https://app.example.com/#/dashboard",
                    "type": "client_side",
                    "method": "client_route"
                },
                {
                    "source": "https://app.example.com",
                    "destination": "https://app.example.com/#/profile",
                    "type": "client_side", 
                    "method": "client_route"
                },
                {
                    "source": "https://app.example.com",
                    "destination": "https://app.example.com/#/settings",
                    "type": "client_side",
                    "method": "client_route"
                }
            ],
            "max_depth": 1,
            "include_client_routes": True,
            "expected_route_count": 3
        }
    
    @staticmethod
    def get_ecommerce_site_scenario() -> Dict[str, Any]:
        """E-commerce site with complex navigation"""
        return {
            "name": "ecommerce_site",
            "base_url": "https://shop.example.com",
            "expected_routes": [
                {
                    "source": "https://shop.example.com",
                    "destination": "https://shop.example.com/products",
                    "type": "link",
                    "method": "click"
                },
                {
                    "source": "https://shop.example.com/products",
                    "destination": "https://shop.example.com/products/electronics",
                    "type": "link",
                    "method": "click"
                },
                {
                    "source": "https://shop.example.com/products",
                    "destination": "https://shop.example.com/products/clothing",
                    "type": "link",
                    "method": "click"
                },
                {
                    "source": "https://shop.example.com/products/electronics",
                    "destination": "https://shop.example.com/cart",
                    "type": "form",
                    "method": "form_submit"
                }
            ],
            "max_depth": 3,
            "expected_route_count": 4
        }
    
    @staticmethod
    def get_authentication_protected_scenario() -> Dict[str, Any]:
        """Site with authentication-protected routes"""
        return {
            "name": "auth_protected_site",
            "base_url": "https://secure.example.com",
            "expected_routes": [
                {
                    "source": "https://secure.example.com",
                    "destination": "https://secure.example.com/login",
                    "type": "link",
                    "method": "click"
                },
                {
                    "source": "https://secure.example.com/login",
                    "destination": "https://secure.example.com/dashboard",
                    "type": "form",
                    "method": "form_submit"
                },
                {
                    "source": "https://secure.example.com/dashboard",
                    "destination": "https://secure.example.com/profile",
                    "type": "link",
                    "method": "click"
                }
            ],
            "max_depth": 2,
            "expected_route_count": 3,
            "requires_auth": True
        }
    
    @staticmethod
    def get_javascript_heavy_scenario() -> Dict[str, Any]:
        """JavaScript-heavy site with dynamic navigation"""
        return {
            "name": "javascript_heavy_site",
            "base_url": "https://dynamic.example.com",
            "expected_routes": [
                {
                    "source": "https://dynamic.example.com",
                    "destination": "https://dynamic.example.com/section1",
                    "type": "javascript",
                    "method": "js_exec"
                },
                {
                    "source": "https://dynamic.example.com",
                    "destination": "https://dynamic.example.com/section2",
                    "type": "javascript",
                    "method": "js_exec"
                }
            ],
            "max_depth": 2,
            "expected_route_count": 2,
            "has_dynamic_content": True
        }


class MockRouteElements:
    """Mock navigation elements for testing"""
    
    @staticmethod
    def get_link_elements(base_url: str) -> List[Dict[str, Any]]:
        """Get mock link elements"""
        return [
            {
                "type": "link",
                "url": f"{base_url}/about",
                "text": "About Us",
                "selector": "a[href='/about']"
            },
            {
                "type": "link",
                "url": f"{base_url}/contact",
                "text": "Contact",
                "selector": "a[href='/contact']"
            },
            {
                "type": "nav",
                "url": f"{base_url}/services",
                "text": "Services",
                "selector": ".nav a[href='/services']"
            }
        ]
    
    @staticmethod
    def get_form_elements(base_url: str) -> List[Dict[str, Any]]:
        """Get mock form elements"""
        return [
            {
                "type": "form",
                "url": f"{base_url}/search",
                "text": "Search",
                "selector": "form[action='/search']"
            },
            {
                "type": "form",
                "url": f"{base_url}/submit",
                "text": "Submit",
                "selector": "form[action='/submit']"
            }
        ]
    
    @staticmethod
    def get_client_side_elements(base_url: str) -> List[Dict[str, Any]]:
        """Get mock client-side routing elements"""
        return [
            {
                "type": "client",
                "url": f"{base_url}#/dashboard",
                "text": "Dashboard",
                "selector": "[href='#/dashboard']"
            },
            {
                "type": "client",
                "url": f"{base_url}#/profile",
                "text": "Profile",
                "selector": "[href='#/profile']"
            }
        ]


class ExpectedRouteGraphs:
    """Expected route graphs for validation"""
    
    @staticmethod
    def get_simple_graph() -> Dict[str, Any]:
        """Expected simple route graph structure"""
        return {
            "nodes": ["home", "about", "contact"],
            "edges": [
                {"from": "home", "to": "about", "weight": 1.0},
                {"from": "home", "to": "contact", "weight": 1.0}
            ],
            "connected_components": 1,
            "is_connected": True
        }
    
    @staticmethod
    def get_complex_graph() -> Dict[str, Any]:
        """Expected complex route graph structure"""
        return {
            "nodes": ["home", "products", "electronics", "clothing", "cart"],
            "edges": [
                {"from": "home", "to": "products", "weight": 1.0},
                {"from": "products", "to": "electronics", "weight": 1.2},
                {"from": "products", "to": "clothing", "weight": 1.1},
                {"from": "electronics", "to": "cart", "weight": 1.5},
                {"from": "clothing", "to": "cart", "weight": 1.4}
            ],
            "connected_components": 1,
            "is_connected": True
        }


class DiscoveryValidationHelpers:
    """Helpers for validating discovery results"""
    
    @staticmethod
    def validate_route_structure(route: NavigationRoute) -> bool:
        """Validate basic route structure"""
        return (
            route.route_id is not None and
            route.source_url is not None and
            route.destination_url is not None and
            route.route_type is not None and
            route.traversal_method is not None
        )
    
    @staticmethod
    def validate_route_graph(graph) -> bool:
        """Validate basic route graph structure"""
        return (
            graph.graph_id is not None and
            len(graph.routes) > 0 and
            hasattr(graph, 'adjacency_matrix')
        )
    
    @staticmethod
    def validate_discovery_metrics(
        discovered_count: int,
        expected_count: int,
        tolerance: float = 0.1
    ) -> bool:
        """Validate discovery metrics within tolerance"""
        if expected_count == 0:
            return discovered_count == 0
        
        ratio = discovered_count / expected_count
        return abs(ratio - 1.0) <= tolerance
    
    @staticmethod
    def validate_route_connections(graph) -> bool:
        """Validate route connections in graph"""
        # Check that adjacency matrix references existing routes
        for source_id, connections in graph.adjacency_matrix.items():
            if source_id not in graph.routes:
                return False
            
            for target_id in connections.keys():
                if target_id not in graph.routes:
                    return False
        
        return True
    
    @staticmethod
    def validate_risk_scores(routes: List[NavigationRoute]) -> bool:
        """Validate risk scores are within bounds"""
        for route in routes:
            if not (0.0 <= route.detection_risk <= 1.0):
                return False
        return True
    
    @staticmethod
    def validate_confidence_scores(routes: List[NavigationRoute]) -> bool:
        """Validate confidence scores are within bounds"""
        for route in routes:
            if not (0.0 <= route.selector_confidence <= 1.0):
                return False
        return True
