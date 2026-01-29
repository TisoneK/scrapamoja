"""
Navigation system interfaces

Core interfaces for Navigation & Routing Intelligence system following
Constitution Principle III - Deep Modularity.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Callable
from .models import (
    NavigationRoute, RouteGraph, NavigationContext, PathPlan, 
    NavigationEvent, OptimizationRule
)


class IRouteDiscovery(ABC):
    """Interface for route discovery and analysis"""
    
    @abstractmethod
    async def discover_routes(
        self, 
        page_url: str,
        max_depth: int = 3,
        include_client_routes: bool = True
    ) -> RouteGraph:
        """Discover all navigable routes from starting page"""
        pass
    
    @abstractmethod
    async def analyze_route_structure(
        self,
        route: NavigationRoute
    ) -> Dict[str, Any]:
        """Analyze route structure and properties"""
        pass
    
    @abstractmethod
    async def validate_route(
        self,
        route: NavigationRoute
    ) -> bool:
        """Validate route accessibility and confidence"""
        pass


class IPathPlanning(ABC):
    """Interface for intelligent path planning"""
    
    @abstractmethod
    async def plan_optimal_path(
        self,
        source_context: str,
        target_destination: str,
        risk_tolerance: float = 0.3
    ) -> PathPlan:
        """Calculate optimal navigation path"""
        pass
    
    @abstractmethod
    async def evaluate_path_risk(
        self,
        path_plan: PathPlan
    ) -> float:
        """Evaluate detection risk for navigation path"""
        pass
    
    @abstractmethod
    async def generate_alternatives(
        self,
        primary_plan: PathPlan,
        max_alternatives: int = 3
    ) -> List[PathPlan]:
        """Generate alternative navigation paths"""
        pass


class IRouteAdaptation(ABC):
    """Interface for dynamic route adaptation"""
    
    @abstractmethod
    async def monitor_navigation(
        self,
        path_plan: PathPlan
    ) -> NavigationEvent:
        """Monitor navigation execution"""
        pass
    
    @abstractmethod
    async def adapt_to_obstacles(
        self,
        current_plan: PathPlan,
        obstacle_type: str
    ) -> Optional[PathPlan]:
        """Adapt route when encountering obstacles"""
        pass
    
    @abstractmethod
    async def handle_detection_triggers(
        self,
        detection_event: NavigationEvent
    ) -> Optional[PathPlan]:
        """Handle anti-bot detection triggers"""
        pass


class IContextManager(ABC):
    """Interface for navigation context management"""
    
    @abstractmethod
    async def create_context(
        self,
        session_id: str,
        initial_page: str
    ) -> NavigationContext:
        """Create new navigation context"""
        pass
    
    @abstractmethod
    async def update_context(
        self,
        context_id: str,
        navigation_event: NavigationEvent
    ) -> NavigationContext:
        """Update context with navigation event"""
        pass
    
    @abstractmethod
    async def get_context_history(
        self,
        context_id: str,
        limit: int = 100
    ) -> List[NavigationEvent]:
        """Get navigation history for context"""
        pass
    
    @abstractmethod
    async def cleanup_context(
        self,
        context_id: str
    ) -> bool:
        """Clean up context resources"""
        pass


class IRouteOptimizer(ABC):
    """Interface for route learning and optimization"""
    
    @abstractmethod
    async def analyze_outcomes(
        self,
        events: List[NavigationEvent]
    ) -> Dict[str, float]:
        """Analyze navigation outcomes for patterns"""
        pass
    
    @abstractmethod
    async def generate_optimization_rules(
        self,
        analysis_data: Dict[str, float]
    ) -> List[OptimizationRule]:
        """Generate optimization rules from analysis"""
        pass
    
    @abstractmethod
    async def apply_optimizations(
        self,
        routes: List[NavigationRoute],
        rules: List[OptimizationRule]
    ) -> List[NavigationRoute]:
        """Apply optimization rules to routes"""
        pass
    
    @abstractmethod
    async def update_performance_metrics(
        self,
        new_events: List[NavigationEvent]
    ) -> bool:
        """Update performance metrics with new data"""
        pass


class INavigationService(ABC):
    """Main navigation service interface"""
    
    @abstractmethod
    async def initialize_navigation(
        self,
        session_id: str,
        start_url: str
    ) -> NavigationContext:
        """Initialize navigation system"""
        pass
    
    @abstractmethod
    async def discover_and_plan(
        self,
        context_id: str,
        target_destination: str
    ) -> PathPlan:
        """Discover routes and plan optimal path"""
        pass
    
    @abstractmethod
    async def execute_navigation(
        self,
        path_plan: PathPlan
    ) -> NavigationContext:
        """Execute navigation plan with adaptation"""
        pass
    
    @abstractmethod
    async def get_navigation_status(
        self,
        context_id: str
    ) -> Dict[str, Any]:
        """Get current navigation status"""
        pass


class INavigationEventPublisher(ABC):
    """Interface for publishing navigation events"""
    
    @abstractmethod
    async def publish_event(
        self,
        event: NavigationEvent
    ) -> bool:
        """Publish navigation event to subscribers"""
        pass
    
    @abstractmethod
    async def subscribe_to_events(
        self,
        event_type: str,
        callback: Callable
    ) -> str:
        """Subscribe to specific navigation events"""
        pass


class INavigationConfig(ABC):
    """Interface for navigation configuration"""
    
    @abstractmethod
    def get_discovery_config(self) -> Dict[str, Any]:
        """Get route discovery configuration"""
        pass
    
    @abstractmethod
    def get_planning_config(self) -> Dict[str, Any]:
        """Get path planning configuration"""
        pass
    
    @abstractmethod
    def get_stealth_config(self) -> Dict[str, Any]:
        """Get stealth-related configuration"""
        pass


class ISelectorEngineIntegration(ABC):
    """Interface for selector engine integration"""
    
    @abstractmethod
    async def get_selectors_for_route(
        self,
        route_url: str
    ) -> List[str]:
        """Get semantic selectors for route"""
        pass
    
    @abstractmethod
    async def validate_route_selectors(
        self,
        route_selectors: List[str]
    ) -> float:
        """Validate selector confidence for route"""
        pass


class IStealthSystemIntegration(ABC):
    """Interface for stealth system integration"""
    
    @abstractmethod
    async def assess_route_risk(
        self,
        route_metadata: Dict[str, Any]
    ) -> float:
        """Assess detection risk for route"""
        pass
    
    @abstractmethod
    async def get_timing_patterns(
        self,
        interaction_type: str
    ) -> Dict[str, float]:
        """Get human-like timing patterns"""
        pass
