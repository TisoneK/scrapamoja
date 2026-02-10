# Quickstart Guide: Navigation & Routing Intelligence

**Created**: 2025-01-27  
**Updated**: 2025-01-27  
**Purpose**: Getting started with Navigation & Routing Intelligence implementation

## Overview

Navigation & Routing Intelligence provides automatic route discovery, intelligent path planning, and dynamic adaptation for web application navigation. This guide walks through the basic setup and usage patterns, including advanced production features.

## Prerequisites

- Python 3.11+ with asyncio
- Playwright (async API) installed and configured
- Existing selector engine and stealth systems
- JSON schema validation library
- NetworkX for graph operations
- psutil for system monitoring

## Basic Setup

### 1. Module Structure

```python
# src/navigation/__init__.py
from .navigation_service import NavigationService
from .route_discovery import RouteDiscovery
from .path_planning import PathPlanning
from .route_adaptation import RouteAdaptation
from .context_manager import ContextManager
from .route_optimizer import RouteOptimizationEngine

# Advanced features
from .memory_optimization import MemoryOptimizedRouteGraph
from .event_publisher import NavigationEventPublisher
from .error_context import ErrorContextCollector
from .route_visualization import RouteAnalyzer, RouteVisualizer
from .checkpoint_manager import NavigationCheckpointManager
from .proxy_manager import ProxyManager
from .health_checker import NavigationHealthChecker

__all__ = [
    'NavigationService',
    'RouteDiscovery',
    'PathPlanning', 
    'RouteAdaptation',
    'ContextManager',
    'RouteOptimizationEngine',
    'MemoryOptimizedRouteGraph',
    'NavigationEventPublisher',
    'ErrorContextCollector',
    'RouteAnalyzer',
    'RouteVisualizer',
    'NavigationCheckpointManager',
    'ProxyManager',
    'NavigationHealthChecker'
]
```

### 2. Core Service Initialization

```python
# src/navigation/navigation_service.py
from typing import Optional
from .interfaces import INavigationService
from .models import NavigationContext, PathPlan

class NavigationService(INavigationService):
    def __init__(
        self,
        selector_engine,  # Existing selector engine
        stealth_system,   # Existing stealth system
        config: dict
    ):
        self.route_discovery = RouteDiscovery(selector_engine, stealth_system)
        self.path_planning = PathPlanning(stealth_system, config)
        self.route_adaptation = RouteAdaptation(stealth_system)
        self.context_manager = ContextManager()
        self.route_optimizer = RouteOptimizer()
        
    async def initialize_navigation(
        self,
        session_id: str,
        start_url: str
    ) -> NavigationContext:
        """Initialize navigation system for session"""
        context = await self.context_manager.create_context(
            session_id=session_id,
            initial_page=start_url
        )
        return context
```

## Usage Examples

### Example 1: Basic Route Discovery

```python
import asyncio
from navigation import NavigationService
from selectors import SelectorEngine  # Existing
from stealth import StealthSystem     # Existing

async def discover_routes_example():
    # Initialize systems
    selector_engine = SelectorEngine()
    stealth_system = StealthSystem()
    nav_service = NavigationService(selector_engine, stealth_system, {})
    
    # Discover routes from starting page
    route_graph = await nav_service.route_discovery.discover_routes(
        page_url="https://example.com",
        max_depth=3,
        include_client_routes=True
    )
    
    print(f"Discovered {len(route_graph.routes)} routes")
    return route_graph

# Run the example
asyncio.run(discover_routes_example())
```

### Example 2: Intelligent Path Planning

```python
async def plan_navigation_example():
    nav_service = NavigationService(selector_engine, stealth_system, {})
    
    # Initialize navigation context
    context = await nav_service.initialize_navigation(
        session_id="session_123",
        start_url="https://example.com"
    )
    
    # Plan optimal path to target
    path_plan = await nav_service.discover_and_plan(
        context_id=context.context_id,
        target_destination="https://example.com/target-page"
    )
    
    print(f"Planned path with {len(path_plan.route_sequence)} steps")
    print(f"Total risk score: {path_plan.total_risk_score}")
    return path_plan
```

### Example 3: Navigation with Adaptation

```python
async def execute_navigation_with_adaptation():
    nav_service = NavigationService(selector_engine, stealth_system, {})
    
    # Get path plan (from previous example)
    path_plan = await plan_navigation_example()
    
    # Execute navigation with automatic adaptation
    try:
        final_context = await nav_service.execute_navigation(path_plan)
        print("Navigation completed successfully")
    except Exception as e:
        print(f"Navigation failed: {e}")
        
    return final_context
```

## Configuration

### Basic Configuration

```python
navigation_config = {
    "discovery": {
        "max_depth": 3,
        "include_client_routes": True,
        "risk_threshold": 0.3,
        "timeout_seconds": 30
    },
    "planning": {
        "risk_tolerance": 0.3,
        "max_alternatives": 3,
        "timing_constraints": {
            "min_delay": 1.0,
            "max_delay": 5.0
        }
    },
    "adaptation": {
        "enable_adaptation": True,
        "fallback_on_failure": True,
        "detection_response": "conservative"
    },
    "optimization": {
        "enable_learning": True,
        "min_samples": 100,
        "update_frequency": "daily"
    }
}
```

### Stealth Integration

```python
stealth_config = {
    "human_timing": {
        "click_delay": {"min": 0.5, "max": 2.0},
        "scroll_delay": {"min": 0.3, "max": 1.5},
        "page_load_wait": {"min": 1.0, "max": 3.0}
    },
    "risk_assessment": {
        "interaction_weight": 0.4,
        "timing_weight": 0.3,
        "pattern_weight": 0.3
    }
}
```

## Error Handling

### Basic Error Handling

```python
from navigation.exceptions import (
    NavigationException,
    RouteDiscoveryError,
    PathPlanningError,
    NavigationExecutionError
)

async def robust_navigation_example():
    try:
        nav_service = NavigationService(selector_engine, stealth_system, config)
        context = await nav_service.initialize_navigation("session_123", "https://example.com")
        path_plan = await nav_service.discover_and_plan(context.context_id, "target")
        result = await nav_service.execute_navigation(path_plan)
        
    except RouteDiscoveryError as e:
        print(f"Route discovery failed: {e.error_code} - {e.message}")
        
    except PathPlanningError as e:
        print(f"Path planning failed: {e.error_code} - {e.message}")
        
    except NavigationExecutionError as e:
        print(f"Navigation execution failed: {e.error_code} - {e.message}")
        
    except NavigationException as e:
        print(f"General navigation error: {e.error_code} - {e.message}")
```

## Performance Monitoring

### Basic Metrics Collection

```python
async def monitor_navigation_performance():
    nav_service = NavigationService(selector_engine, stealth_system, config)
    
    # Execute navigation
    start_time = time.time()
    result = await execute_navigation_with_adaptation()
    end_time = time.time()
    
    # Get performance metrics
    status = await nav_service.get_navigation_status(result.context_id)
    
    print(f"Navigation completed in {end_time - start_time:.2f} seconds")
    print(f"Routes discovered: {status['routes_discovered']}")
    print(f"Path adaptations: {status['adaptations_count']}")
    print(f"Success rate: {status['success_rate']:.2%}")
```

## Testing and Validation

### Manual Validation Steps

1. **Route Discovery Validation**
   - Verify all expected routes are discovered
   - Check selector confidence scores >0.8
   - Validate detection risk scores <0.3

2. **Path Planning Validation**
   - Test path calculation under 100ms
   - Verify risk assessment accuracy
   - Check fallback plan generation

3. **Navigation Execution Validation**
   - Test adaptation to blocked routes
   - Verify stealth compliance
   - Check context management accuracy

### Integration Testing

```python
async def integration_test():
    # Test complete navigation flow
    nav_service = NavigationService(selector_engine, stealth_system, config)
    
    # Initialize
    context = await nav_service.initialize_navigation("test_session", "https://test-site.com")
    
    # Discover and plan
    path_plan = await nav_service.discover_and_plan(
        context.context_id, 
        "https://test-site.com/target"
    )
    
    # Execute with monitoring
    result = await nav_service.execute_navigation(path_plan)
    
    # Validate results
    assert result.context_id == context.context_id
    assert len(result.navigation_history) > 0
    
    print("Integration test passed")
```

## Best Practices

### 1. Resource Management
- Clean up navigation contexts when done
- Monitor memory usage for large route graphs
- Use timeouts for long-running operations

### 2. Stealth Compliance
- Always use stealth system integration
- Respect rate limiting and timing constraints
- Monitor detection risk scores

### 3. Error Recovery
- Implement fallback plans for critical paths
- Log all navigation events for analysis
- Use graceful degradation when routes fail

### 4. Performance Optimization
- Cache frequently used route graphs
- Use lazy loading for large navigation networks
- Optimize path calculation algorithms

## Troubleshooting

### Common Issues

1. **Route Discovery Timeout**
   - Check max_depth configuration
   - Verify page load performance
   - Reduce discovery scope

2. **High Detection Risk**
   - Review stealth configuration
   - Check timing patterns
   - Consider alternative routes

3. **Context Management Errors**
   - Verify session ID validity
   - Check context cleanup procedures
   - Monitor memory usage

### Debug Information

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Key log messages to monitor:
- Route discovery progress
- Path planning calculations
- Adaptation triggers
- Performance metrics

## Next Steps

1. Implement core navigation modules
2. Set up integration with existing systems
3. Configure stealth and performance settings
4. Test with target web applications
5. Monitor and optimize performance

## Advanced Features

### Memory Optimization

```python
from navigation import create_memory_optimized_graph

# Create memory-optimized graph for large navigation scenarios
graph = create_memory_optimized_graph(max_memory_mb=512)

# Add routes efficiently
graph.add_route(route)

# Monitor memory usage
stats = graph.get_memory_stats()
print(f"Memory usage: {stats.memory_usage_mb:.2f} MB")
```

### Event Publishing

```python
from navigation import get_event_publisher, EventType

# Get global event publisher
publisher = get_event_publisher()

# Subscribe to navigation events
def handle_navigation_event(event):
    print(f"Navigation event: {event.event_type.value}")

publisher.subscribe(
    subscriber_id="monitor",
    callback=handle_navigation_event
)

# Publish events
await publisher.publish_event(
    event_type=EventType.NAVIGATION_COMPLETED,
    source_component="path_planning",
    data={"success": True}
)
```

### Error Context Collection

```python
from navigation import get_error_collector

# Collect comprehensive error context
try:
    await some_navigation_operation()
except Exception as e:
    collector = get_error_collector()
    error_context = collector.collect_error_context(
        error=e,
        component_name="route_discovery",
        correlation_id="corr_123"
    )
    
    # Export for debugging
    collector.export_error_context(error_context, "error_debug.json")
```

### Route Visualization

```python
from navigation import create_route_visualizer

# Create interactive visualizations
visualizer = create_route_visualizer()

# Generate HTML dashboard
visualizer.create_html_dashboard(route_graph, "navigation_dashboard.html")

# Export for external tools
visualizer.export_to_d3_json(route_graph, "routes_d3.json")
visualizer.export_to_cytoscape(route_graph, "routes_cytoscape.json")

# Analyze routes
analyzer = create_route_analyzer()
metrics = analyzer.analyze_routes(route_graph)
print(f"Average confidence: {metrics.average_confidence:.2f}")
```

### Checkpointing and Resume

```python
from navigation import create_checkpoint_manager

# Create checkpoint manager
checkpoint_manager = create_checkpoint_manager()

# Create checkpoint during long operations
checkpoint_id = checkpoint_manager.create_checkpoint(
    operation_type="route_discovery",
    correlation_id="corr_123",
    current_step=5,
    total_steps=20,
    completed_routes=["route_1", "route_2"],
    pending_routes=["route_3", "route_4"]
)

# Resume from checkpoint
checkpoint = checkpoint_manager.load_checkpoint(checkpoint_id)
if checkpoint:
    print(f"Resuming from step {checkpoint.current_step}")
```

### Proxy Management

```python
from navigation import create_proxy_manager, ProxyConfig

# Create proxy manager
proxy_manager = create_proxy_manager()

# Add proxy configurations
proxy_config = ProxyConfig(
    proxy_id="proxy_1",
    proxy_type="http",
    host="proxy.example.com",
    port=8080,
    username="user",
    password="pass"
)
proxy_manager.add_proxy(proxy_config)

# Get proxy for navigation
proxy = proxy_manager.get_proxy()
if proxy:
    await navigate_with_proxy(proxy)
```

### Health Monitoring

```python
from navigation import create_health_checker

# Monitor system health
health_checker = create_health_checker()
health_status = await health_checker.check_system_health()

print(f"Overall status: {health_status.overall_status}")
for result in health_status.component_results:
    print(f"{result.component_name}: {result.status}")
```

For detailed implementation guidance, refer to the data model and API contracts in this specification.
