# Navigation & Routing Intelligence - Implementation Guide

## Overview

The Navigation & Routing Intelligence system provides automatic route discovery, intelligent path planning, and dynamic adaptation for web application navigation with stealth-aware design and human behavior emulation.

## Quick Start

### Basic Usage

```python
from navigation import NavigationService

# Initialize the navigation service
nav_service = NavigationService()

# Discover routes from a starting URL
routes = await nav_service.discover_routes("https://example.com")

# Plan optimal path to target
path_plan = await nav_service.plan_path(
    source="https://example.com/home",
    target="https://example.com/dashboard",
    optimization_criteria="confidence"
)

# Execute navigation with adaptation
result = await nav_service.execute_navigation(path_plan)
```

### Advanced Configuration

```python
from navigation import NavigationService, NavigationConfig

# Configure with custom settings
config = NavigationConfig(
    discovery_timeout=60,
    max_concurrent_discoveries=10,
    enable_memory_optimization=True,
    enable_event_publishing=True
)

nav_service = NavigationService(config=config)
```

## Core Components

### 1. Route Discovery

Automatic discovery of navigation routes using semantic selector integration.

```python
from navigation import RouteDiscovery

discovery = RouteDiscovery()

# Basic discovery
routes = await discovery.discover_routes(
    page_url="https://example.com",
    max_depth=3,
    include_client_routes=True
)

# Discovery with timeout
routes = await discovery.discover_routes_with_timeout(
    page_url="https://example.com",
    timeout=30
)

# Cancel discovery
discovery_id = "discovery_123"
await discovery.cancel_discovery(discovery_id)
```

### 2. Path Planning

Intelligent path planning with multiple algorithms and risk assessment.

```python
from navigation import PathPlanning

planner = PathPlanning()

# Find shortest path
path = await planner.find_shortest_path(
    graph=route_graph,
    source="home",
    target="dashboard"
)

# Find all paths with constraints
paths = await planner.find_all_paths(
    graph=route_graph,
    source="home",
    target="dashboard",
    max_risk=0.5,
    max_duration=10.0
)

# Optimize path for specific criteria
optimized_path = await planner.optimize_path(
    path=path,
    optimization_criteria="confidence"
)
```

### 3. Route Adaptation

Dynamic route adaptation with intelligent obstacle handling.

```python
from navigation import RouteAdaptation

adapter = RouteAdaptation()

# Adapt to obstacle
adapted_route = await adapter.adapt_to_obstacle(
    original_route=route,
    obstacle_type="element_not_found",
    context=nav_context
)

# Get adaptation strategies
strategies = await adapter.get_adaptation_strategies(
    route=route,
    obstacle_type="timeout"
)
```

### 4. Context Management

Comprehensive navigation context tracking and persistence.

```python
from navigation import ContextManager

context_manager = ContextManager()

# Create new context
context = await context_manager.create_context(
    session_id="session_123",
    start_url="https://example.com"
)

# Update context
await context_manager.update_context(
    context_id=context.context_id,
    current_page="https://example.com/dashboard",
    navigation_data={"action": "login"}
)

# Get context
context = await context_manager.get_context(context.context_id)
```

### 5. Route Optimization

Machine learning-based route optimization and performance improvement.

```python
from navigation import RouteOptimizationEngine

optimizer = RouteOptimizationEngine()

# Optimize route graph
optimized_graph = await optimizer.optimize_graph(
    graph=route_graph,
    optimization_type="performance"
)

# Learn from navigation results
await optimizer.learn_from_result(
    route=route,
    outcome="success",
    duration=5.2,
    confidence=0.95
)

# Get optimization suggestions
suggestions = await optimizer.get_optimization_suggestions(
    graph=route_graph
)
```

## Advanced Features

### Memory Optimization

Efficient handling of large route graphs with memory optimization.

```python
from navigation import create_memory_optimized_graph

# Create memory-optimized graph
graph = create_memory_optimized_graph(max_memory_mb=512)

# Add routes efficiently
graph.add_route(route)

# Optimize memory usage
graph.optimize_memory()

# Get memory statistics
stats = graph.get_memory_stats()
print(f"Memory usage: {stats.memory_usage_mb:.2f} MB")
```

### Event Publishing

Real-time event publishing and subscription system.

```python
from navigation import get_event_publisher, EventType

# Get global event publisher
publisher = get_event_publisher()

# Subscribe to events
def handle_route_discovery(event):
    print(f"Route discovered: {event.data}")

publisher.subscribe(
    subscriber_id="my_app",
    callback=handle_route_discovery,
    filter=EventFilter(event_types={EventType.ROUTE_DISCOVERY_COMPLETED})
)

# Publish events
await publisher.publish_event(
    event_type=EventType.NAVIGATION_COMPLETED,
    source_component="path_planning",
    data={"route_id": "route_123", "success": True}
)
```

### Error Context Collection

Comprehensive error context collection for debugging.

```python
from navigation import get_error_collector

# Get global error collector
collector = get_error_collector()

# Collect error context
try:
    # Navigation operation that might fail
    await some_navigation_operation()
except Exception as e:
    error_context = collector.collect_error_context(
        error=e,
        component_name="route_discovery",
        correlation_id="corr_123",
        navigation_context=current_context
    )
    
    # Export error context for analysis
    collector.export_error_context(error_context, "error_debug.json")

# Get error statistics
stats = collector.get_error_statistics()
print(f"Total errors: {stats['total_errors']}")
```

### Route Visualization

Interactive visualization and analysis of navigation routes.

```python
from navigation import create_route_visualizer

# Create visualizer
visualizer = create_route_visualizer()

# Create visualization data
viz_data = visualizer.create_visualization_data(
    graph=route_graph,
    layout="spring"
)

# Export to different formats
visualizer.export_to_d3_json(route_graph, "routes_d3.json")
visualizer.export_to_cytoscape(route_graph, "routes_cytoscape.json")

# Create interactive HTML dashboard
visualizer.create_html_dashboard(route_graph, "routes_dashboard.html")

# Analyze routes
analyzer = create_route_analyzer()
metrics = analyzer.analyze_routes(route_graph)
print(f"Average confidence: {metrics.average_confidence:.2f}")
```

### Checkpointing and Resume

Checkpoint and resume functionality for long-running operations.

```python
from navigation import create_checkpoint_manager

# Create checkpoint manager
checkpoint_manager = create_checkpoint_manager()

# Create checkpoint during operation
checkpoint_id = checkpoint_manager.create_checkpoint(
    operation_type="route_discovery",
    correlation_id="corr_123",
    session_id="session_456",
    current_step=5,
    total_steps=20,
    completed_routes=["route_1", "route_2"],
    failed_routes=[],
    pending_routes=["route_3", "route_4"]
)

# Resume from checkpoint
checkpoint = checkpoint_manager.load_checkpoint(checkpoint_id)
if checkpoint:
    print(f"Resuming from step {checkpoint.current_step}")
    # Resume operation from checkpoint
```

### Proxy Management

Production-ready proxy management and rotation.

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
    password="pass",
    country="US"
)
proxy_manager.add_proxy(proxy_config)

# Get proxy for navigation
proxy = proxy_manager.get_proxy()
if proxy:
    # Use proxy for navigation
    await navigate_with_proxy(proxy)

# Mark proxy success/failure
proxy_manager.mark_proxy_success(proxy.proxy_id)
proxy_manager.mark_proxy_failure(proxy.proxy_id)
```

### Health Monitoring

Comprehensive system health monitoring and diagnostics.

```python
from navigation import create_health_checker

# Create health checker
health_checker = create_health_checker()

# Check system health
health_status = await health_checker.check_system_health()

print(f"Overall status: {health_status.overall_status}")
for result in health_status.component_results:
    print(f"{result.component_name}: {result.status} - {result.message}")

# Check system metrics
print(f"Process count: {health_status.system_metrics['process_count']}")
print(f"Network connections: {health_status.system_metrics['network_connections']}")
```

## Configuration

### Environment Variables

```bash
# Navigation configuration
NAVIGATION_LOG_LEVEL=INFO
NAVIGATION_TIMEOUT=30
NAVIGATION_MAX_MEMORY_MB=512

# Event publishing
NAVIGATION_ENABLE_EVENTS=true
NAVIGATION_EVENT_BUFFER_SIZE=1000

# Performance monitoring
NAVIGATION_ENABLE_MONITORING=true
NAVIGATION_METRICS_INTERVAL=60

# Checkpointing
NAVIGATION_CHECKPOINT_DIR=data/navigation/checkpoints
NAVIGATION_CHECKPOINT_RETENTION_DAYS=7
```

### Configuration File

```json
{
  "navigation": {
    "discovery_timeout": 30,
    "max_concurrent_discoveries": 5,
    "enable_memory_optimization": true,
    "max_memory_mb": 512,
    "enable_event_publishing": true,
    "enable_performance_monitoring": true
  },
  "logging": {
    "level": "INFO",
    "correlation_id_header": "X-Correlation-ID"
  },
  "performance": {
    "metrics_interval": 60,
    "enable_health_checks": true
  },
  "checkpointing": {
    "checkpoint_dir": "data/navigation/checkpoints",
    "retention_days": 7
  }
}
```

## Integration Examples

### Integration with Browser Automation

```python
from navigation import NavigationService
from playwright import async_api

class BrowserNavigationIntegration:
    def __init__(self, browser: async_api.Browser):
        self.browser = browser
        self.nav_service = NavigationService()
    
    async def navigate_to_target(self, start_url: str, target_url: str):
        # Create browser context
        context = await self.browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to start page
            await page.goto(start_url)
            
            # Discover routes
            routes = await self.nav_service.discover_routes(start_url)
            
            # Plan path to target
            path_plan = await self.nav_service.plan_path(
                source=start_url,
                target=target_url
            )
            
            # Execute navigation
            for step in path_plan.steps:
                # Execute step using Playwright
                await self._execute_navigation_step(page, step)
            
            return True
            
        except Exception as e:
            # Collect error context
            from navigation import get_error_collector
            collector = get_error_collector()
            error_context = collector.collect_error_context(
                error=e,
                component_name="browser_navigation",
                correlation_id=path_plan.correlation_id
            )
            
            return False
        finally:
            await context.close()
    
    async def _execute_navigation_step(self, page, step):
        # Execute navigation step using selector
        element = await page.wait_for_selector(step.selector)
        await element.click()
        
        # Wait for navigation
        await page.wait_for_load_state("networkidle")
```

### Integration with Testing Framework

```python
import pytest
from navigation import NavigationService

@pytest.fixture
async def nav_service():
    service = NavigationService()
    yield service
    await service.cleanup()

@pytest.mark.asyncio
async def test_route_discovery(nav_service):
    routes = await nav_service.discover_routes("https://example.com")
    
    assert len(routes) > 0
    assert all(route.confidence_score > 0.5 for route in routes)

@pytest.mark.asyncio
async def test_path_planning(nav_service):
    path_plan = await nav_service.plan_path(
        source="https://example.com/home",
        target="https://example.com/dashboard"
    )
    
    assert path_plan is not None
    assert len(path_plan.steps) > 0
    assert path_plan.confidence_score > 0.7

@pytest.mark.asyncio
async def test_navigation_with_adaptation(nav_service):
    path_plan = await nav_service.plan_path(
        source="https://example.com/home",
        target="https://example.com/dashboard"
    )
    
    result = await nav_service.execute_navigation(path_plan)
    
    assert result.success
    assert result.outcome == "success"
```

## Performance Optimization

### Memory Usage

- Use memory-optimized graphs for large navigation scenarios
- Enable automatic memory optimization
- Monitor memory usage with performance monitoring

### Caching

- Enable route graph caching for frequently accessed routes
- Use checkpointing for long-running operations
- Configure appropriate cache sizes and retention

### Concurrency

- Configure appropriate concurrent discovery limits
- Use event publishing for asynchronous processing
- Implement proper error handling for concurrent operations

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Enable memory optimization
   - Reduce concurrent operations
   - Use checkpointing for long operations

2. **Slow Discovery**
   - Increase timeout values
   - Optimize selector performance
   - Use caching for repeated operations

3. **Navigation Failures**
   - Check error context for detailed information
   - Verify stealth configuration
   - Use proxy rotation for blocked requests

### Debugging

1. Enable debug logging
2. Use error context collection
3. Monitor performance metrics
4. Check system health status

## Best Practices

1. **Configuration Management**
   - Use environment-specific configurations
   - Enable monitoring in production
   - Configure appropriate timeouts

2. **Error Handling**
   - Collect comprehensive error context
   - Implement proper recovery mechanisms
   - Use checkpointing for reliability

3. **Performance**
   - Monitor memory usage
   - Optimize for your specific use case
   - Use caching appropriately

4. **Security**
   - Use proxy rotation for production
   - Enable stealth features
   - Monitor for detection triggers

## Support

For issues and questions:
1. Check error context and logs
2. Review system health status
3. Consult performance metrics
4. Enable debug logging for detailed information
