"""
Navigation & Routing Intelligence Module

Provides automatic route discovery, intelligent path planning, and dynamic adaptation
for web application navigation with stealth-aware design and human behavior emulation.
"""

# Core service
from .navigation_service import NavigationService

# Individual components
from .route_discovery import RouteDiscovery
from .path_planning import PathPlanning
from .route_adaptation import RouteAdaptation
from .context_manager import ContextManager
from .route_optimizer import RouteOptimizationEngine

# Data models
from .models import (
    NavigationRoute,
    RouteGraph,
    NavigationContext,
    PathPlan,
    NavigationEvent,
    RouteOptimizer
)

# Interfaces
from .interfaces import (
    IRouteDiscovery,
    IPathPlanning,
    IRouteAdaptation,
    IContextManager,
    IRouteOptimizer,
    INavigationService
)

# Exceptions
from .exceptions import (
    NavigationError,
    RouteDiscoveryError,
    PathPlanningError,
    RouteAdaptationError,
    ContextManagementError,
    OptimizationError,
    NavigationServiceError
)

# Utilities
from .logging_config import get_navigation_logger, set_correlation_id, generate_correlation_id
from .schema_validation import navigation_validator
from .config import NavigationConfig
from .performance_monitor import PerformanceMonitor

# Advanced features
from .memory_optimization import MemoryOptimizedRouteGraph, create_memory_optimized_graph
from .graph_serialization import RouteGraphSerializer, RouteGraphCache, create_route_graph_serializer
from .event_publisher import NavigationEventPublisher, EventType, EventFilter, get_event_publisher
from .error_context import ErrorContextCollector, get_error_collector
from .route_visualization import RouteAnalyzer, RouteVisualizer, create_route_analyzer, create_route_visualizer
from .checkpoint_manager import NavigationCheckpointManager, create_checkpoint_manager
from .proxy_manager import ProxyManager, ProxyConfig, create_proxy_manager
from .health_checker import NavigationHealthChecker, create_health_checker

__version__ = "1.0.0"

__all__ = [
    # Main service
    'NavigationService',
    
    # Individual components
    'RouteDiscovery',
    'PathPlanning',
    'RouteAdaptation',
    'ContextManager',
    'RouteOptimizationEngine',
    
    # Data models
    'NavigationRoute',
    'RouteGraph',
    'NavigationContext',
    'PathPlan',
    'NavigationEvent',
    'RouteOptimizer',
    
    # Interfaces
    'IRouteDiscovery',
    'IPathPlanning',
    'IRouteAdaptation',
    'IContextManager',
    'IRouteOptimizer',
    'INavigationService',
    
    # Exceptions
    'NavigationError',
    'RouteDiscoveryError',
    'PathPlanningError',
    'RouteAdaptationError',
    'ContextManagementError',
    'OptimizationError',
    'NavigationServiceError',
    
    # Utilities
    'get_navigation_logger',
    'set_correlation_id',
    'generate_correlation_id',
    'navigation_validator',
    'NavigationConfig',
    'PerformanceMonitor',
    
    # Advanced features
    'MemoryOptimizedRouteGraph',
    'create_memory_optimized_graph',
    'RouteGraphSerializer',
    'RouteGraphCache',
    'create_route_graph_serializer',
    'NavigationEventPublisher',
    'EventType',
    'EventFilter',
    'get_event_publisher',
    'ErrorContextCollector',
    'get_error_collector',
    'RouteAnalyzer',
    'RouteVisualizer',
    'create_route_analyzer',
    'create_route_visualizer',
    'NavigationCheckpointManager',
    'create_checkpoint_manager',
    'ProxyManager',
    'ProxyConfig',
    'create_proxy_manager',
    'NavigationHealthChecker',
    'create_health_checker'
]
