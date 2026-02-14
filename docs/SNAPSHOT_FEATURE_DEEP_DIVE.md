# Snapshot Feature Specification

> **🎯 Build Instructions**  
> This specification describes a **single-system architecture**.  
> When implementing, build ONLY what is described here.  
> Do NOT add migration tools, compatibility layers, or fallback mechanisms.  
> The bundle system is the complete and only snapshot implementation.

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Data Models](#data-models)
5. [Capture Modes](#capture-modes)
6. [Event-Driven System](#event-driven-system)
7. [Performance Optimizations](#performance-optimizations)
8. [Feature Flags & Rollout](#feature-flags--rollout)
9. [Monitoring & Metrics](#monitoring--metrics)
10. [Integration Points](#integration-points)
11. [Storage Organization](#storage-organization)
12. [Error Handling & Recovery](#error-handling--recovery)
13. [Usage Examples](#usage-examples)
14. [Best Practices](#best-practices)

## Overview

The Snapshot feature is a sophisticated context-aware system designed to capture, organize, and manage browser state snapshots for web scraping operations. It provides hierarchical organization, dual HTML capture, async performance optimizations, and event-driven failure tracking.

### Key Benefits
- **Context-Aware Organization**: Snapshots are organized hierarchically by site, module, component, and timestamp
- **Dual HTML Capture**: Captures both full page HTML and element-specific HTML for comprehensive debugging
- **Event-Driven Triggers**: Automatically captures snapshots on failures, timeouts, and extraction mismatches
- **Performance Optimized**: Async parallel artifact saving with deduplication and caching
- **Gradual Rollout**: Feature flags enable controlled deployment and A/B testing
- **Comprehensive Monitoring**: Built-in metrics collection and performance tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Snapshot System                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Manager       │  │   Triggers      │  │   Monitor    │ │
│  │                 │  │                 │  │              │ │
│  │ • Capture       │  │ • Selector      │  │ • Metrics    │ │
│  │ • Storage       │  │ • Retry         │  │ • Performance│ │
│  │ • Retrieval     │  │ • Timeout       │  │ • Health     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Integration    │  │   Feature Flags │  │   Utilities  │ │
│  │                 │  │                 │  │              │ │
│  │ • Browser       │  │ • Rollout       │  │ • Validation │ │
│  │ • Session       │  │ • Environment   │  │ • Cleanup    │ │
│  │ • Error         │  │ • Percentage    │  │ • Tools      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │     Models     │  │   Config        │  │   Storage    │ │
│  │                 │  │                 │  │              │ │
│  │ • Bundle        │  │ • Presets       │  │ • Hierarchical│ │
│  │ • Context       │  │ • Environment   │  │ • Partitioned│ │
│  │ • Config        │  │ • Features      │  │ • Atomic     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### SnapshotManager
The central orchestrator responsible for:
- Capturing snapshots with atomic operations
- Managing hierarchical storage organization
- Coordinating async artifact capture
- Handling content deduplication
- Providing retrieval and querying capabilities

**Key Methods:**
- `capture_snapshot()`: Main capture method with comprehensive error handling
- `handle_selector_failure()`: Event-driven failure handling
- `handle_retry_exhaustion()`: Retry exhaustion snapshot capture
- `handle_timeout()`: Timeout event snapshot capture
- `load_bundle()`: Bundle loading with validation

### Event-Driven System
Automatically captures snapshots based on predefined triggers:

**Trigger Types:**
- **Selector Failure**: When CSS selectors fail to match elements
- **Retry Exhaustion**: When maximum retry attempts are exceeded
- **Timeout**: When operations exceed time limits
- **Extraction Mismatch**: When extracted data doesn't match expectations
- **Manual**: User-initiated snapshot capture

**Rate Limiting:**
- Prevents cascade failures with configurable rate limits
- Default: 5 triggers per minute per trigger type
- Automatic cleanup of old trigger timestamps

## Data Models

### SnapshotContext
Provides hierarchical organization and traceability:
```python
@dataclass
class SnapshotContext:
    site: str              # Website domain (e.g., "flashscore")
    module: str            # Functional module (e.g., "navigation")
    component: str         # Specific component (e.g., "menu")
    session_id: str        # Unique session identifier
    function: Optional[str]  # Function name where snapshot occurred
    additional_metadata: Dict[str, Any]  # Extra context data
```

**Hierarchical Path Generation:**
```
data/snapshots/{site}/{module}/{component}/{YYYYMMDD}/{HHMMSS}_{session_id}
```

### SnapshotConfig
Configures capture behavior:
```python
@dataclass
class SnapshotConfig:
    mode: SnapshotMode = SnapshotMode.SELECTOR
    capture_html: bool = True
    capture_screenshot: bool = False
    capture_network: bool = False
    capture_console: bool = False
    selector: Optional[str] = None
    capture_full_page: bool = False
    deduplication_enabled: bool = True
    async_save: bool = True
```

### SnapshotBundle
Represents a complete snapshot with all artifacts:
```python
@dataclass
class SnapshotBundle:
    context: SnapshotContext
    timestamp: datetime
    config: SnapshotConfig
    bundle_path: str
    artifacts: List[str]
    metadata: Dict[str, Any]
    content_hash: Optional[str]
```

## Capture Modes

### FULL_PAGE
Captures the entire page HTML:
- Use case: Complete page state analysis
- Performance impact: Higher
- Storage: Larger files

### SELECTOR
Captures element-specific HTML:
- Use case: Targeted component debugging
- Performance impact: Lower
- Storage: Smaller files

### MINIMAL
Captures only essential metadata:
- Use case: High-frequency monitoring
- Performance impact: Minimal
- Storage: Minimal

### BOTH
Captures both full page and element HTML:
- Use case: Comprehensive debugging
- Performance impact: Highest
- Storage: Largest files

## Event-Driven System

### Trigger Implementation
Each trigger implements the `SnapshotTrigger` interface:

```python
class SnapshotTrigger(ABC):
    @abstractmethod
    async def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Determine if snapshot should be triggered."""
        pass
    
    @abstractmethod
    async def get_snapshot_context(self, context: Dict[str, Any]) -> SnapshotContext:
        """Extract snapshot context from trigger context."""
        pass
    
    @abstractmethod
    async def get_snapshot_config(self, context: Dict[str, Any]) -> SnapshotConfig:
        """Get snapshot configuration for this trigger."""
        pass
```

### Selector Failure Trigger
```python
async def should_trigger(self, context: Dict[str, Any]) -> bool:
    return (
        context.get("matched_count", 0) == 0 and
        context.get("selector") and
        self.enabled and
        self.rate_limiter.should_allow()
    )
```

### Rate Limiting
Prevents cascade failures during widespread issues:
- Configurable limits per trigger type
- Time-based window (default: 1 minute)
- Automatic cleanup of expired entries

## Performance Optimizations

### Async Parallel Capture
Artifacts are captured in parallel when `async_save=True`:

```python
# Prepare capture tasks
capture_tasks = [
    self._capture_full_html(page, html_dir),
    self._capture_element_html(page, config.selector, html_dir),
    self._capture_screenshot(page, screenshots_dir),
    self._capture_console_logs(page, logs_dir),
    self._capture_network_logs(page, logs_dir)
]

# Execute in parallel
artifact_paths = await asyncio.gather(*capture_tasks, return_exceptions=True)
```

### Content Deduplication
Prevents storage of duplicate content:
- MD5 hash-based comparison
- In-memory cache with 1000 entry limit
- FIFO eviction strategy
- Configurable enable/disable

### Atomic Operations
Ensures data consistency:
- Bundle directories created atomically
- Metadata saved with temp file + rename pattern
- Automatic cleanup on failure
- Validation before completion

## Feature Flags & Rollout

### Rollout Stages
```python
class RolloutStage(Enum):
    DISABLED = "disabled"
    INTERNAL_TESTING = "internal_testing"
    BETA_TESTING = "beta_testing"
    GRADUAL_ROLLOUT = "gradual_rollout"
    FULL_ROLLOUT = "full_rollout"
```

### Feature Flags
Current enabled features (from config):
- **context_aware_bundles**: Hierarchical organization (100% rollout)
- **dual_html_capture**: Full page + element capture (100% rollout)
- **async_performance**: Parallel artifact saving (100% rollout)
- **event_driven_snapshots**: Automatic failure capture (100% rollout)
- **performance_monitoring**: Metrics collection (100% rollout)

### Site-Specific Rollout
```json
"site_rollout": {
    "flashscore": 100.0,
    "betting": 100.0,
    "sports": 100.0
}
```

### Environment-Based Control
Features can be enabled per environment:
- Development: All features enabled
- Staging: Controlled testing
- Production: Gradual rollout

## Monitoring & Metrics

### Performance Metrics
```python
@dataclass
class SnapshotMetrics:
    total_snapshots: int = 0
    successful_snapshots: int = 0
    failed_snapshots: int = 0
    average_capture_time: float = 0.0
    deduplication_hits: int = 0
    deduplication_misses: int = 0
    parallel_executions: int = 0
    sequential_executions: int = 0
    cache_size: int = 0
    cache_utilization: float = 0.0
```

### Key Performance Indicators
- **Success Rate**: Percentage of successful snapshot captures
- **Average Capture Time**: Mean time to complete snapshot capture
- **Deduplication Rate**: Percentage of content deduplicated
- **Parallel Execution Rate**: Percentage of captures using parallel processing
- **Error Breakdown**: Categorization of failure types

### Real-time Monitoring
- Uptime tracking
- Operation timing histograms
- Error rate monitoring
- Cache utilization metrics

## Integration Points

### Browser Integration
The `BrowserSnapshotIntegration` class provides seamless integration with existing browser automation:

```python
class BrowserSnapshotIntegration:
    async def capture_snapshot_on_selector_failure(
        self,
        browser_manager,
        site: str,
        module: str,
        component: str,
        session_id: str,
        selector: str,
        matched_count: int = 0
    ) -> bool:
```

### Session Management
Integrates with browser session lifecycle:
- Automatic page extraction from active sessions
- Session status validation
- Graceful handling of session termination

### Error Handling Integration
Hooks into existing error handling patterns:
- Selector failure detection
- Retry exhaustion handling
- Timeout event capture
- Extraction validation failures

## Storage Organization

### Hierarchical Structure
```
data/snapshots/
├── {site}/
│   ├── {module}/
│   │   ├── {component}/
│   │   │   ├── {YYYYMMDD}/
│   │   │   │   ├── {HHMMSS}_{session_id}/
│   │   │   │   │   ├── html/
│   │   │   │   │   │   ├── fullpage.html
│   │   │   │   │   │   └── element_{hash}.html
│   │   │   │   │   ├── screenshots/
│   │   │   │   │   │   └── viewport.png
│   │   │   │   │   ├── logs/
│   │   │   │   │   │   ├── console.json
│   │   │   │   │   │   └── network.json
│   │   │   │   │   └── metadata.json
```

### Partitioning
Automatic partitioning when directory limits are exceeded:
- Monitors directory size and file count
- Creates sub-partitions when thresholds are reached
- Maintains atomic operations during partitioning

### Metadata Structure
```json
{
    "context": {
        "site": "flashscore",
        "module": "navigation",
        "component": "menu",
        "session_id": "session_123",
        "function": "selector_execution",
        "additional_metadata": {
            "trigger_type": "selector_failure",
            "selector": ".menu-item",
            "matched_count": 0
        }
    },
    "timestamp": "2026-02-13T14:30:00",
    "config": {
        "mode": "selector",
        "capture_html": true,
        "capture_screenshot": false,
        "capture_network": false,
        "capture_console": false,
        "selector": ".menu-item",
        "deduplication_enabled": true,
        "async_save": true
    },
    "artifacts": [
        "html/element_a1b2c3d4.html"
    ],
    "bundle_version": "1.0"
}
```

## Error Handling & Recovery

### Atomic Operations
- Bundle directories created with atomic patterns
- Metadata saved using temp file + rename
- Automatic cleanup on partial failures
- Validation before completion

### Corruption Detection
- Bundle structure validation on load
- Metadata integrity checks
- Required field validation
- Artifact existence verification

### Graceful Degradation
- Fallback to sequential execution on parallel failures
- Individual artifact failure isolation
- Rate limiting during cascade failures

### Exception Hierarchy
```python
SnapshotError
├── BundleCorruptionError
├── ArtifactCaptureError
└── ConfigurationError
```

## Usage Examples

### Basic Snapshot Capture
```python
from src.core.snapshot import SnapshotManager, SnapshotContext, SnapshotConfig

# Initialize manager
manager = SnapshotManager()

# Create context
context = SnapshotContext(
    site="flashscore",
    module="navigation",
    component="menu",
    session_id="session_123",
    function="extract_menu_items"
)

# Create config
config = SnapshotConfig(
    mode=SnapshotMode.SELECTOR,
    capture_html=True,
    capture_screenshot=True,
    selector=".menu-item"
)

# Capture snapshot
bundle = await manager.capture_snapshot(page, context, config)
```

### Event-Driven Capture
```python
# Automatic capture on selector failure
await manager.handle_selector_failure(
    page=page,
    site="flashscore",
    module="navigation",
    component="menu",
    session_id="session_123",
    selector=".menu-item",
    matched_count=0
)
```

### Browser Integration
```python
from src.core.snapshot.integration import BrowserSnapshotIntegration

integration = BrowserSnapshotIntegration(manager)

# Capture on selector failure
success = await integration.capture_snapshot_on_selector_failure(
    browser_manager=browser_manager,
    site="flashscore",
    module="navigation",
    component="menu",
    session_id="session_123",
    selector=".menu-item",
    matched_count=0
)
```

### Feature Flag Control
```python
from src.core.snapshot.feature_flags import get_feature_flag_manager

# Get manager
flag_manager = get_feature_flag_manager()

# Check if feature is enabled
if flag_manager.is_feature_enabled("context_aware_bundles", site="flashscore"):
    # Use snapshot system
    pass

# Enable feature for specific site
flag_manager.set_site_rollout("flashscore", 50.0)  # 50% rollout
```

## Best Practices

### Performance Optimization
1. **Enable Async Save**: Use parallel artifact capture for better performance
2. **Deduplication**: Keep deduplication enabled to reduce storage costs
3. **Selective Capture**: Choose appropriate capture mode based on needs
4. **Rate Limiting**: Configure appropriate rate limits to prevent cascade failures

### Storage Management
1. **Regular Cleanup**: Implement periodic cleanup of old snapshots
2. **Partitioning**: Monitor directory sizes and enable automatic partitioning
3. **Compression**: Consider compressing old snapshots for long-term storage
4. **Backup Strategy**: Implement backup and recovery procedures

### Monitoring
1. **Metrics Collection**: Enable performance monitoring for all environments
2. **Alert Thresholds**: Set up alerts for high error rates or performance degradation
3. **Regular Audits**: Periodically review snapshot quality and storage usage
4. **Capacity Planning**: Monitor storage growth and plan capacity accordingly

### Development
1. **Feature Flags**: Use feature flags for gradual rollout and testing
2. **Environment Isolation**: Test new features in isolated environments first
3. **Single System Principle**: Build and maintain one implementation path - avoid conditional logic for alternative systems
4. **Documentation**: Keep documentation updated with new features and changes

### Error Handling
1. **Graceful Degradation**: Implement fallback mechanisms for failures
2. **Comprehensive Logging**: Log detailed error information for debugging
3. **Recovery Procedures**: Document and test recovery procedures
4. **Monitoring Integration**: Integrate with existing monitoring and alerting systems

## Configuration Reference

### SnapshotConfig Options
- `mode`: Capture mode (full, selector, minimal, both)
- `capture_html`: Enable HTML capture
- `capture_screenshot`: Enable screenshot capture
- `capture_network`: Enable network log capture
- `capture_console`: Enable console log capture
- `selector`: CSS selector for element capture
- `capture_full_page`: Enable full page HTML capture
- `deduplication_enabled`: Enable content deduplication
- `async_save`: Enable parallel artifact saving

### Feature Flag Configuration
- `current_stage`: Rollout stage (disabled to full_rollout)
- `enabled_features`: Feature-specific configurations
- `site_rollout`: Site-specific rollout percentages
- `global_settings`: Global system settings

### Performance Settings
- `max_rollout_percentage_per_day`: Maximum daily rollout increase
- `rollback_threshold`: Error rate threshold for auto-rollback
- `feature_flag_cache_ttl`: Cache TTL for feature flags
- `rate_limit_triggers_per_minute`: Rate limit per trigger type

This comprehensive snapshot system provides robust, performant, and scalable browser state capture capabilities with extensive monitoring, control, and integration options.
