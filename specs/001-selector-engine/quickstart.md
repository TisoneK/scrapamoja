# Selector Engine Quickstart Guide

**Date**: 2025-01-27  
**Purpose**: Quick start guide for implementing and using the Selector Engine  
**Status**: Complete

## Overview

The Selector Engine is the core component of the Scorewise Scraper system that provides semantic abstraction for DOM element selection. It enables reliable data extraction from dynamic web applications through multi-strategy resolution, confidence scoring, and adaptive evolution.

## Key Concepts

### Semantic Selectors
- **Business Meaning**: Selectors represent what you want, not where it is
- **Multi-Strategy**: Each selector has primary, secondary, and tertiary resolution strategies
- **Context-Aware**: Selectors are scoped to specific tab contexts (summary, odds, h2h, etc.)

### Confidence Scoring
- **Quality Control**: Every resolution gets a confidence score (0.0-1.0)
- **Thresholds**: Production requires >0.8 confidence for reliable results
- **Validation**: Content validation contributes to confidence calculation

### Adaptive Evolution
- **Learning**: System learns which strategies work best over time
- **Promotion**: Successful fallback strategies can become primary
- **Drift Detection**: Automatically detects when selectors start failing

## Quick Start

### 1. Basic Selector Definition

```python
from src.selectors.engine import SemanticSelector, StrategyPattern, StrategyType
from src.selectors.validation import ValidationRule, ValidationType

# Create a semantic selector for home team name
home_team_selector = SemanticSelector(
    name="home_team_name",
    description="Home team name in match header",
    context="summary",
    confidence_threshold=0.8,
    strategies=[
        # Primary strategy: Text anchor near "Home"
        StrategyPattern(
            id="home_text_anchor",
            type=StrategyType.TEXT_ANCHOR,
            priority=1,
            config={
                "anchor_text": "Home",
                "proximity_selector": ".team-name",
                "case_sensitive": False
            }
        ),
        # Secondary strategy: Attribute match
        StrategyPattern(
            id="home_attribute_match",
            type=StrategyType.ATTRIBUTE_MATCH,
            priority=2,
            config={
                "attribute": "data-team",
                "value_pattern": "home",
                "element_tag": "div"
            }
        ),
        # Tertiary strategy: DOM relationship
        StrategyPattern(
            id="home_dom_relationship",
            type=StrategyType.DOM_RELATIONSHIP,
            priority=3,
            config={
                "parent_selector": ".match-header",
                "child_index": 0,
                "relationship_type": "child"
            }
        )
    ],
    validation_rules=[
        ValidationRule(
            type=ValidationType.REGEX,
            pattern=r"^[A-Za-z\s]+$",
            required=True,
            weight=0.4
        ),
        ValidationRule(
            type=ValidationType.SEMANTIC,
            pattern="team_name",
            required=True,
            weight=0.3
        )
    ]
)
```

### 2. Basic Usage

```python
from src.selectors.engine import SelectorEngine, DOMContext
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.flashscore.com/match/123456")
        
        # Create DOM context
        context = DOMContext(
            page=page,
            tab_context="summary",
            url=page.url,
            timestamp=datetime.now(),
            metadata={}
        )
        
        # Initialize selector engine
        engine = SelectorEngine()
        
        # Register selector
        engine.register_selector(home_team_selector)
        
        # Resolve selector
        result = await engine.resolve("home_team_name", context)
        
        if result.success and result.confidence_score > 0.8:
            print(f"Home team: {result.element_info.text_content}")
            print(f"Confidence: {result.confidence_score}")
            print(f"Strategy used: {result.strategy_used}")
        else:
            print(f"Failed to resolve home team name")
            print(f"Reason: {result.failure_reason}")
        
        await browser.close()
```

### 3. Batch Resolution

```python
# Resolve multiple selectors in parallel
selector_names = ["home_team_name", "away_team_name", "match_score", "match_time"]
results = await engine.resolve_batch(selector_names, context)

for result in results:
    if result.success:
        print(f"{result.selector_name}: {result.element_info.text_content}")
    else:
        print(f"{result.selector_name}: FAILED")
```

### 4. Context-Aware Selection

```python
# Define selectors for different tab contexts
odds_selector = SemanticSelector(
    name="home_win_odds",
    description="Home team win odds",
    context="odds",  # Only valid in odds tab
    strategies=[...]
)

# Tab switching with context validation
async def extract_odds_data(engine, page):
    # Switch to odds tab
    await page.click('[data-tab="odds"]')
    await page.wait_for_selector('.odds-container')
    
    # Create odds context
    odds_context = DOMContext(
        page=page,
        tab_context="odds",
        url=page.url,
        timestamp=datetime.now(),
        metadata={}
    )
    
    # Resolve odds-specific selectors
    result = await engine.resolve("home_win_odds", odds_context)
    return result
```

## Advanced Usage

### 1. Custom Strategy Implementation

```python
from src.selectors.strategies.base import IStrategyPattern
from src.selectors.engine import SelectorResult, ElementInfo

class CustomMLStrategy(IStrategyPattern):
    def __init__(self):
        self._type = StrategyType.CUSTOM
        self._priority = 4
        self._model = load_ml_model()  # Your ML model
    
    @property
    def type(self) -> StrategyType:
        return self._type
    
    @property
    def priority(self) -> int:
        return self._priority
    
    async def attempt_resolution(self, selector, context):
        # Use ML model to predict element location
        prediction = self._model.predict(context.page.content())
        
        if prediction.confidence > 0.7:
            element = await context.page.query_selector(prediction.selector)
            if element:
                element_info = await self._extract_element_info(element)
                return SelectorResult(
                    selector_name=selector.name,
                    strategy_used=self.id,
                    element_info=element_info,
                    confidence_score=prediction.confidence,
                    resolution_time=prediction.time,
                    validation_results=[],
                    success=True,
                    timestamp=datetime.now()
                )
        
        return SelectorResult.failure(selector.name, "ML prediction too uncertain")
```

### 2. Performance Monitoring

```python
from src.selectors.monitoring import PerformanceMonitor

# Monitor selector performance
monitor = PerformanceMonitor()

# Get performance metrics
metrics = monitor.get_metrics("home_team_name")
print(f"Success rate: {metrics.success_rate}")
print(f"Average confidence: {metrics.avg_confidence}")
print(f"Average resolution time: {metrics.avg_resolution_time}ms")

# Get top performers
top_performers = monitor.get_top_performers(limit=5)
for name, success_rate in top_performers:
    print(f"{name}: {success_rate:.2%} success rate")
```

### 3. Drift Detection

```python
from src.selectors.drift import DriftDetector

# Analyze drift over last 24 hours
drift_detector = DriftDetector()
time_range = (
    datetime.now() - timedelta(hours=24),
    datetime.now()
)

drift_analysis = await drift_detector.analyze_drift("home_team_name", time_range)

if drift_analysis.drift_score > 0.7:
    print(f"High drift detected for home_team_name")
    print(f"Drift score: {drift_analysis.drift_score}")
    print(f"Trend: {drift_analysis.trend_direction}")
    print(f"Recommendations: {drift_analysis.recommendations}")
```

### 4. DOM Snapshot Analysis

```python
from src.selectors.snapshots import DOMSnapshotManager

# Analyze failure snapshots
snapshot_manager = DOMSnapshotManager()

# Get recent failure snapshots
snapshots = snapshot_manager.get_snapshots(
    selector_name="home_team_name",
    snapshot_type=SnapshotType.FAILURE,
    time_range=time_range
)

for snapshot in snapshots:
    print(f"Snapshot {snapshot.id}: {snapshot.failure_reason}")
    # Analyze DOM structure changes
    analysis = await snapshot_manager.analyze_snapshot(snapshot)
    print(f"DOM changes: {analysis.changes}")
```

## Configuration

### 1. Basic Configuration

```python
from src.selectors.config import SelectorEngineConfig, SnapshotConfig

# Configure selector engine
engine_config = SelectorEngineConfig(
    default_confidence_threshold=0.8,
    max_resolution_time=1000.0,  # milliseconds
    snapshot_on_failure=True,
    drift_detection_enabled=True,
    evolution_enabled=True,
    cache_enabled=True,
    cache_ttl=30,  # seconds
    parallel_resolution=True,
    max_concurrent_resolutions=10
)

# Configure snapshots
snapshot_config = SnapshotConfig(
    compression_enabled=True,
    max_file_size=10 * 1024 * 1024,  # 10MB
    retention_days=30,
    storage_path="data/snapshots"
)
```

### 2. Environment-Specific Configuration

```python
# Development configuration
dev_config = SelectorEngineConfig(
    default_confidence_threshold=0.5,  # More lenient
    snapshot_on_failure=True,
    drift_detection_enabled=False,  # Disabled in dev
    evolution_enabled=False
)

# Production configuration
prod_config = SelectorEngineConfig(
    default_confidence_threshold=0.8,  # Strict
    snapshot_on_failure=False,  # Minimal overhead
    drift_detection_enabled=True,
    evolution_enabled=True,
    cache_enabled=True
)
```

## Testing

### 1. Unit Testing Selectors

```python
import pytest
from src.selectors.testing import SelectorTestHarness, TestCase

@pytest.mark.asyncio
async def test_home_team_selector():
    harness = SelectorTestHarness()
    
    test_cases = [
        TestCase(
            name="basic_match_page",
            dom_content='<div class="team-name">Manchester United</div>',
            expected_element=".team-name",
            expected_confidence=0.9,
            context="summary"
        ),
        TestCase(
            name="no_home_team",
            dom_content='<div class="team-name">--</div>',
            expected_element=None,
            expected_confidence=0.0,
            context="summary"
        )
    ]
    
    result = await harness.test_selector("home_team_name", test_cases)
    
    assert result.passed_tests == 1
    assert result.failed_tests == 1
    assert result.average_confidence > 0.4
```

### 2. Integration Testing

```python
@pytest.mark.asyncio
async def test_selector_engine_integration():
    engine = SelectorEngine()
    
    # Register test selectors
    engine.register_selector(home_team_selector)
    engine.register_selector(away_team_selector)
    
    # Create test context
    context = create_test_context()
    
    # Test batch resolution
    results = await engine.resolve_batch(
        ["home_team_name", "away_team_name"], 
        context
    )
    
    assert len(results) == 2
    assert all(r.success for r in results)
    assert all(r.confidence_score > 0.8 for r in results)
```

## Best Practices

### 1. Selector Design
- **Semantic Names**: Use descriptive names that reflect business meaning
- **Multiple Strategies**: Always provide at least 3 strategies
- **Context Scoping**: Define appropriate tab contexts for each selector
- **Validation Rules**: Include comprehensive validation for content quality

### 2. Performance Optimization
- **Caching**: Enable caching for frequently used selectors
- **Parallel Resolution**: Use batch resolution for independent selectors
- **Strategy Ordering**: Put most reliable strategies first
- **Timeout Management**: Set appropriate timeouts for each strategy

### 3. Monitoring and Maintenance
- **Performance Tracking**: Monitor success rates and confidence scores
- **Drift Detection**: Enable drift detection for production environments
- **Regular Reviews**: Periodically review selector performance and strategies
- **Snapshot Analysis**: Use failure snapshots to identify DOM changes

### 4. Error Handling
- **Graceful Degradation**: Always have fallback strategies
- **Confidence Thresholds**: Set appropriate thresholds for different environments
- **Failure Logging**: Log detailed failure information for debugging
- **Recovery Strategies**: Implement automatic recovery for common failures

## Troubleshooting

### Common Issues

1. **Low Confidence Scores**
   - Check validation rules
   - Verify strategy configurations
   - Review DOM structure changes

2. **Timeout Errors**
   - Increase timeout values
   - Optimize selector strategies
   - Check page load performance

3. **Context Validation Failures**
   - Verify tab context is correct
   - Check tab activation logic
   - Ensure DOM is ready

4. **High Memory Usage**
   - Enable snapshot compression
   - Reduce retention period
   - Implement cleanup policies

### Debug Mode

```python
# Enable debug mode for detailed logging
engine = SelectorEngine(debug=True)

# Get detailed resolution information
result = await engine.resolve("home_team_name", context, debug=True)

# Access debug information
print(f"Debug info: {result.debug_info}")
print(f"Strategy attempts: {result.strategy_attempts}")
print(f"Validation details: {result.validation_results}")
```

## Next Steps

1. **Define Selectors**: Create semantic selectors for your specific use case
2. **Implement Strategies**: Add custom strategies if needed
3. **Configure System**: Set appropriate configuration for your environment
4. **Test Thoroughly**: Write comprehensive tests for all selectors
5. **Monitor Performance**: Set up monitoring and drift detection
6. **Iterate**: Continuously improve selectors based on performance data

For more detailed information, refer to the [API contracts](contracts/selector-engine-api.md) and [data model](data-model.md) documentation.
