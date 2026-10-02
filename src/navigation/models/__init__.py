"""
Navigation data models

Core entities for Navigation & Routing Intelligence system following
Constitution Principle III - Deep Modularity.
"""

from .route import NavigationRoute, RouteType, TraversalMethod
from .graph import RouteGraph, GraphMetadata
from .context import NavigationContext, NavigationOutcome, AuthenticationState, PageState
from .plan import PathPlan, RouteStep
from .event import NavigationEvent
from .optimizer import RouteOptimizer, OptimizationRule

__all__ = [
    'NavigationRoute',
    'RouteType', 
    'TraversalMethod',
    'RouteGraph',
    'GraphMetadata',
    'NavigationContext',
    'NavigationOutcome',
    'AuthenticationState',
    'PageState',
    'PathPlan',
    'RouteStep',
    'NavigationEvent',
    'RouteOptimizer',
    'OptimizationRule'
]
