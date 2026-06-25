"""
Route discovery and analysis

Automatic discovery and analysis of navigation routes within web applications.
Conforms to Constitution Principle I - Selector-First Engineering.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
from pathlib import Path
from dataclasses import dataclass, field
import weakref

from .interfaces import IRouteDiscovery
from .models import NavigationRoute, RouteGraph, RouteType, TraversalMethod, NavigationContext
from .exceptions import RouteDiscoveryError
from .integrations.selector_integration import SelectorEngineIntegration
from .integrations.stealth_integration import StealthSystemIntegration
from .logging_config import get_navigation_logger, set_correlation_id, generate_correlation_id
from .schema_validation import navigation_validator


class RouteDiscovery(IRouteDiscovery):
    """Route discovery and analysis implementation"""
    
    def __init__(
        self,
        selector_engine_client=None,
        stealth_system_client=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize route discovery with timeout and cancellation support"""
        self.logger = get_navigation_logger("route_discovery")
        self.config = config or {}
        
        # Integration clients
        self.selector_engine = SelectorEngineIntegration(selector_engine_client)
        self.stealth_system = StealthSystemIntegration(stealth_system_client)
        
        # Discovery state
        self._discovery_active = False
        self._discovery_tasks: Dict[str, asyncio.Task] = {}
        self._cancellation_tokens: Dict[str, asyncio.Event] = {}
        
        # Timeout configuration
        self.default_timeout = self.config.get("discovery_timeout", 30)
        self.max_concurrent_discoveries = self.config.get("max_concurrent_discoveries", 5)
        
        # Callbacks for progress monitoring
        self._progress_callbacks: Dict[str, Callable] = {}
        
        self.logger.info(
            "Route discovery initialized with timeout support",
            default_timeout=self.default_timeout,
            max_concurrent_discoveries=self.max_concurrent_discoveries
        )
        
        # Initialize integrations
        self.selector_integration = SelectorEngineIntegration(selector_engine_client)
        self.stealth_integration = StealthSystemIntegration(stealth_system_client)
        
        # Discovery state
        self._discovered_routes: Dict[str, NavigationRoute] = {}
        self._visited_urls: Set[str] = set()
        self._correlation_id: Optional[str] = None
    
    async def discover_routes_with_timeout(
        self,
        page_url: str,
        max_depth: int = 3,
        include_client_routes: bool = True,
        timeout: Optional[float] = None
    ) -> RouteGraph:
        """Discover routes with timeout support"""
        discovery_timeout = timeout or self.default_timeout
        discovery_id = f"discovery_{generate_correlation_id()}"
        
        # Create cancellation token
        cancel_event = asyncio.Event()
        self._cancellation_tokens[discovery_id] = cancel_event
        
        try:
            # Use asyncio.wait_for for timeout
            return await asyncio.wait_for(
                self._discover_routes_with_cancellation(
                    discovery_id,
                    page_url,
                    max_depth,
                    include_client_routes,
                    cancel_event
                ),
                timeout=discovery_timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(
                "Route discovery timed out",
                discovery_id=discovery_id,
                timeout=discovery_timeout
            )
            raise RouteDiscoveryError(
                f"Route discovery timed out after {discovery_timeout} seconds",
                "DISCOVERY_TIMEOUT",
                {"discovery_id": discovery_id, "timeout": discovery_timeout}
            )
        finally:
            # Cleanup
            self._cancellation_tokens.pop(discovery_id, None)
    
    async def cancel_discovery(self, discovery_id: str) -> bool:
        """Cancel active route discovery"""
        try:
            if discovery_id in self._cancellation_tokens:
                # Signal cancellation
                self._cancellation_tokens[discovery_id].set()
                
                self.logger.info(
                    "Route discovery cancelled",
                    discovery_id=discovery_id
                )
                
                return True
            else:
                self.logger.warning(
                    "Discovery not found for cancellation",
                    discovery_id=discovery_id
                )
                return False
                
        except Exception as e:
            self.logger.error(
                f"Failed to cancel discovery: {str(e)}",
                discovery_id=discovery_id
            )
            return False
    
    def set_progress_callback(
        self,
        discovery_id: str,
        callback: Callable[[str, int, int], None]
    ) -> None:
        """Set progress callback for discovery"""
        self._progress_callbacks[discovery_id] = callback
    
    def get_active_discoveries(self) -> List[str]:
        """Get list of active discovery IDs"""
        return list(self._cancellation_tokens.keys())
    
    async def _discover_routes_with_cancellation(
        self,
        discovery_id: str,
        page_url: str,
        max_depth: int,
        include_client_routes: bool,
        cancel_event: asyncio.Event
    ) -> RouteGraph:
        """Internal discovery method with cancellation support"""
        # Check cancellation at start
        if cancel_event.is_set():
            raise asyncio.CancelledError()
        
        # Store original correlation ID
        original_correlation_id = self._correlation_id
        
        try:
            # Set discovery correlation ID
            self._correlation_id = discovery_id
            set_correlation_id(discovery_id)
            
            # Call original discovery method
            return await self.discover_routes(page_url, max_depth, include_client_routes)
            
        finally:
            # Restore original correlation ID
            self._correlation_id = original_correlation_id
            if original_correlation_id:
                set_correlation_id(original_correlation_id)
    
    async def discover_routes(
        self, 
        page_url: str,
        max_depth: int = 3,
        include_client_routes: bool = True
    ) -> RouteGraph:
        """Discover all navigable routes from starting page"""
        start_time = datetime.utcnow()
        
        # Generate correlation ID for this discovery session
        self._correlation_id = generate_correlation_id()
        set_correlation_id(self._correlation_id)
        
        self.logger.route_discovery_start(page_url, max_depth)
        
        try:
            # Reset discovery state
            self._discovered_routes.clear()
            self._visited_urls.clear()
            
            # Create route graph
            graph = RouteGraph(
                graph_id=f"discovery_{self._correlation_id}",
                graph_metadata=self._create_discovery_metadata(max_depth)
            )
            
            # Start discovery from root URL
            await self._discover_from_url(page_url, max_depth, include_client_routes)
            
            # Add discovered routes to graph
            for route_id, route in self._discovered_routes.items():
                graph.add_route(route)
            
            # Build connections between routes
            await self._build_route_connections(graph)
            
            # Update graph metadata
            discovery_duration = (datetime.utcnow() - start_time).total_seconds()
            graph.graph_metadata.discovery_duration_seconds = discovery_duration
            graph.graph_metadata.total_pages_analyzed = len(self._visited_urls)
            
            self.logger.route_discovery_complete(
                len(self._discovered_routes), 
                discovery_duration
            )
            
            return graph
            
        except Exception as e:
            self.logger.error(
                f"Route discovery failed: {str(e)}",
                page_url=page_url,
                max_depth=max_depth,
                correlation_id=self._correlation_id
            )
            raise RouteDiscoveryError(
                f"Failed to discover routes from {page_url}: {str(e)}",
                "DISCOVERY_FAILED",
                {
                    "page_url": page_url,
                    "max_depth": max_depth,
                    "correlation_id": self._correlation_id
                }
            )
    
    async def analyze_route_structure(
        self,
        route: NavigationRoute
    ) -> Dict[str, Any]:
        """Analyze route structure and properties"""
        try:
            set_correlation_id(self._correlation_id)
            
            analysis = {
                "route_id": route.route_id,
                "structure_analysis": await self._analyze_route_structure_internal(route),
                "interaction_complexity": await self._assess_interaction_complexity(route),
                "accessibility_factors": await self._assess_accessibility(route),
                "stealth_factors": await self._assess_stealth_factors(route)
            }
            
            self.logger.debug(
                "Route structure analysis completed",
                route_id=route.route_id,
                analysis_keys=list(analysis.keys())
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(
                f"Route structure analysis failed: {str(e)}",
                route_id=route.route_id
            )
            raise RouteDiscoveryError(
                f"Failed to analyze route structure for {route.route_id}: {str(e)}",
                "STRUCTURE_ANALYSIS_FAILED",
                {"route_id": route.route_id}
            )
    
    async def validate_route(
        self,
        route: NavigationRoute
    ) -> bool:
        """Validate route accessibility and confidence"""
        try:
            set_correlation_id(self._correlation_id)
            
            # Get selectors for route validation
            route_selectors = await self.selector_integration.get_selectors_for_route(
                route.destination_url
            )
            
            # Validate selector confidence
            confidence = await self.selector_integration.validate_route_selectors(
                route_selectors
            )
            
            # Update route validation status
            route.update_validation_status(confidence, route.detection_risk)
            
            # Check if route meets production thresholds
            is_valid = route.is_production_ready()
            
            self.logger.debug(
                "Route validation completed",
                route_id=route.route_id,
                confidence=confidence,
                is_valid=is_valid
            )
            
            return is_valid
            
        except Exception as e:
            self.logger.error(
                f"Route validation failed: {str(e)}",
                route_id=route.route_id
            )
            raise RouteDiscoveryError(
                f"Failed to validate route {route.route_id}: {str(e)}",
                "ROUTE_VALIDATION_FAILED",
                {"route_id": route.route_id}
            )
    
    async def _discover_from_url(
        self,
        url: str,
        max_depth: int,
        include_client_routes: bool,
        current_depth: int = 0
    ) -> None:
        """Discover routes from a specific URL"""
        if current_depth >= max_depth or url in self._visited_urls:
            return
        
        self._visited_urls.add(url)
        
        try:
            # Discover navigation elements on the page
            navigation_elements = await self._extract_navigation_elements(url)
            
            # Process each navigation element
            for element in navigation_elements:
                route = await self._create_route_from_element(element, url)
                
                if route and route.route_id not in self._discovered_routes:
                    self._discovered_routes[route.route_id] = route
                    
                    # Recursively discover from destination URL
                    if route.destination_url not in self._visited_urls:
                        await self._discover_from_url(
                            route.destination_url,
                            max_depth,
                            include_client_routes,
                            current_depth + 1
                        )
            
            # Discover client-side routes if requested
            if include_client_routes and current_depth == 0:
                await self._discover_client_side_routes(url)
                
        except Exception as e:
            self.logger.warning(
                f"Failed to discover routes from {url}: {str(e)}",
                url=url,
                current_depth=current_depth
            )
    
    async def _extract_navigation_elements(self, url: str) -> List[Dict[str, Any]]:
        """Extract navigation elements from a page"""
        # This would use Playwright to analyze the actual page
        # For now, return placeholder implementation
        
        navigation_elements = []
        
        # Common navigation element patterns
        element_patterns = [
            {"type": "link", "selector": "a[href]", "attr": "href"},
            {"type": "form", "selector": "form[action]", "attr": "action"},
            {"type": "button", "selector": "button[onclick]", "attr": "onclick"},
            {"type": "nav", "selector": ".nav a", "attr": "href"},
            {"type": "menu", "selector": ".menu a", "attr": "href"}
        ]
        
        for pattern in element_patterns:
            # In real implementation, this would:
            # 1. Load the page with Playwright
            # 2. Find elements matching the selector
            # 3. Extract the specified attribute
            # 4. Return element information
            
            # Placeholder elements for demonstration
            if pattern["type"] == "link":
                navigation_elements.extend([
                    {
                        "type": "link",
                        "url": f"{url}/page1",
                        "text": "Page 1",
                        "selector": "a[href='/page1']"
                    },
                    {
                        "type": "link", 
                        "url": f"{url}/page2",
                        "text": "Page 2",
                        "selector": "a[href='/page2']"
                    }
                ])
            elif pattern["type"] == "form":
                navigation_elements.append({
                    "type": "form",
                    "url": f"{url}/submit",
                    "text": "Submit Form",
                    "selector": "form[action='/submit']"
                })
        
        return navigation_elements
    
    async def _discover_client_side_routes(self, url: str) -> None:
        """Discover client-side routing patterns"""
        try:
            # This would analyze JavaScript for client-side routing
            # Look for patterns like React Router, Vue Router, Angular Router
            
            client_routes = [
                {
                    "type": "client",
                    "url": f"{url}#/dashboard",
                    "text": "Dashboard",
                    "selector": "[href='#/dashboard']"
                },
                {
                    "type": "client",
                    "url": f"{url}#/profile",
                    "text": "Profile", 
                    "selector": "[href='#/profile']"
                }
            ]
            
            for element in client_routes:
                route = await self._create_route_from_element(element, url)
                if route and route.route_id not in self._discovered_routes:
                    self._discovered_routes[route.route_id] = route
                    
        except Exception as e:
            self.logger.warning(
                f"Failed to discover client-side routes: {str(e)}",
                url=url
            )
    
    async def _create_route_from_element(
        self,
        element: Dict[str, Any],
        source_url: str
    ) -> Optional[NavigationRoute]:
        """Create NavigationRoute from navigation element"""
        try:
            route_type = self._determine_route_type(element["type"])
            traversal_method = self._determine_traversal_method(element["type"])
            
            # Assess detection risk
            risk_assessment = await self.stealth_integration.assess_route_risk({
                "element_type": element["type"],
                "selector": element.get("selector", ""),
                "url": element["url"]
            })
            
            route = NavigationRoute(
                route_id=f"{source_url}_{element['url']}_{hash(element['selector']) % 10000}",
                source_url=source_url,
                destination_url=element["url"],
                route_type=route_type,
                traversal_method=traversal_method,
                detection_risk=risk_assessment,
                metadata={
                    "element_text": element.get("text", ""),
                    "selector": element.get("selector", ""),
                    "element_type": element["type"]
                }
            )
            
            # Add interaction requirements if needed
            if traversal_method == TraversalMethod.FORM_SUBMIT:
                route.add_interaction_requirement(
                    "form_submit",
                    element.get("selector", ""),
                    {"form_data": {}}
                )
            elif traversal_method == TraversalMethod.CLICK:
                route.add_interaction_requirement(
                    "click",
                    element.get("selector", ""),
                    None,
                    1.0  # 1 second delay
                )
            
            return route
            
        except Exception as e:
            self.logger.warning(
                f"Failed to create route from element: {str(e)}",
                element=element
            )
            return None
    
    def _determine_route_type(self, element_type: str) -> RouteType:
        """Determine route type from element type"""
        type_mapping = {
            "link": RouteType.LINK,
            "form": RouteType.FORM,
            "button": RouteType.JAVASCRIPT,
            "nav": RouteType.LINK,
            "menu": RouteType.LINK,
            "client": RouteType.CLIENT_SIDE
        }
        return type_mapping.get(element_type, RouteType.LINK)
    
    def _determine_traversal_method(self, element_type: str) -> TraversalMethod:
        """Determine traversal method from element type"""
        method_mapping = {
            "link": TraversalMethod.CLICK,
            "form": TraversalMethod.FORM_SUBMIT,
            "button": TraversalMethod.JAVASCRIPT_EXECUTION,
            "nav": TraversalMethod.CLICK,
            "menu": TraversalMethod.CLICK,
            "client": TraversalMethod.CLIENT_ROUTE
        }
        return method_mapping.get(element_type, TraversalMethod.CLICK)
    
    async def _build_route_connections(self, graph: RouteGraph) -> None:
        """Build connections between discovered routes"""
        for route_id, route in self._discovered_routes.items():
            # Find routes that can be reached from this route
            for other_id, other_route in self._discovered_routes.items():
                if route_id != other_id:
                    # Check if other route is accessible from this route
                    if self._is_route_accessible(route, other_route):
                        # Add connection with weight based on risk
                        weight = 1.0 + other_route.detection_risk
                        graph.add_connection(route_id, other_id, weight)
    
    def _is_route_accessible(
        self,
        source_route: NavigationRoute,
        target_route: NavigationRoute
    ) -> bool:
        """Check if target route is accessible from source route"""
        # Simple heuristic: if source URL is prefix of target URL
        # In real implementation, this would be more sophisticated
        return target_route.destination_url.startswith(source_route.source_url)
    
    def _create_discovery_metadata(self, max_depth: int) -> Any:
        """Create discovery metadata"""
        from .models import GraphMetadata
        
        return GraphMetadata(
            created_by="route_discovery",
            creation_method="dom_analysis",
            max_depth=max_depth,
            total_pages_analyzed=0,
            discovery_duration_seconds=0.0
        )
    
    async def _analyze_route_structure_internal(
        self,
        route: NavigationRoute
    ) -> Dict[str, Any]:
        """Internal route structure analysis"""
        return {
            "route_complexity": "medium" if len(route.interaction_requirements) > 1 else "low",
            "interaction_count": len(route.interaction_requirements),
            "has_timing_constraints": route.timing_constraints is not None,
            "metadata_size": len(route.metadata)
        }
    
    async def _assess_interaction_complexity(
        self,
        route: NavigationRoute
    ) -> Dict[str, Any]:
        """Assess interaction complexity"""
        complexity_score = 0
        
        for req in route.interaction_requirements:
            if req.interaction_type == "form_submit":
                complexity_score += 3
            elif req.interaction_type == "click":
                complexity_score += 1
            elif req.interaction_type == "javascript_execution":
                complexity_score += 2
        
        return {
            "complexity_score": complexity_score,
            "complexity_level": "high" if complexity_score > 5 else "medium" if complexity_score > 2 else "low"
        }
    
    async def _assess_accessibility(self, route: NavigationRoute) -> Dict[str, Any]:
        """Assess route accessibility factors"""
        return {
            "requires_authentication": route.destination_url.startswith("/auth"),
            "has_ssl": route.destination_url.startswith("https://"),
            "is_internal": not route.destination_url.startswith(("http://", "https://")),
            "accessibility_score": 0.8  # Placeholder calculation
        }
    
    async def _assess_stealth_factors(self, route: NavigationRoute) -> Dict[str, Any]:
        """Assess stealth-related factors"""
        return {
            "detection_risk": route.detection_risk,
            "requires_javascript": route.traversal_method in [
                TraversalMethod.JAVASCRIPT_EXECUTION,
                TraversalMethod.CLIENT_ROUTE
            ],
            "interaction_visibility": "high" if route.interaction_requirements else "low",
            "stealth_score": 1.0 - route.detection_risk
        }
