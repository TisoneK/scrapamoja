# Context-Aware Snapshot System: API Documentation

## Overview

The context-aware snapshot system provides a comprehensive API for capturing, managing, and monitoring web page snapshots with hierarchical organization and event-driven capabilities.

## Core API

### SnapshotManager

The main class for managing snapshot operations.

```python
from src.core.snapshot import SnapshotManager, SnapshotContext, SnapshotConfig

manager = SnapshotManager("data/snapshots")
```

#### Methods

##### capture_snapshot()

Captures a snapshot bundle with the given context and configuration.

```python
async def capture_snapshot(
    self,
    page,
    context: SnapshotContext,
    config: Optional[SnapshotConfig] = None,
    timestamp: Optional[datetime] = None
) -> SnapshotBundle
```

**Parameters:**
- `page`: The browser page object to capture from
- `context`: Snapshot context with site, module, component information
- `config`: Optional snapshot configuration (defaults to SnapshotConfig())
- `timestamp`: Optional timestamp (defaults to current time)

**Returns:**
- `SnapshotBundle`: The created snapshot bundle

**Example:**
```python
context = SnapshotContext(
    site="example.com",
    module="scraping",
    component="extractor",
    session_id="session_123",
    function="data_extraction"
)

bundle = await manager.capture_snapshot(page, context)
```

##### get_snapshots_by_context()

Retrieves snapshots matching the given context criteria.

```python
def get_snapshots_by_context(self, context: SnapshotContext) -> List[SnapshotBundle]
```

**Parameters:**
- `context`: Context criteria for filtering (use "*" for wildcard)

**Returns:**
- `List[SnapshotBundle]`: List of matching snapshot bundles

##### get_performance_metrics()

Gets comprehensive performance metrics.

```python
def get_performance_metrics(self) -> Dict[str, Any]
```

**Returns:**
- `Dict[str, Any]`: Performance metrics including capture times, success rates, etc.

### SnapshotContext

Dataclass containing context information for snapshots.

```python
@dataclass
class SnapshotContext:
    site: str
    module: str
    component: str
    session_id: str
    function: str
    additional_metadata: Dict[str, Any] = field(default_factory=dict)
```

**Fields:**
- `site`: Website or domain name
- `module`: Functional module (e.g., "scraping", "parsing")
- `component`: Specific component (e.g., "extractor", "validator")
- `session_id`: Unique session identifier
- `function`: Function being executed
- `additional_metadata`: Extra context information

### SnapshotConfig

Configuration for snapshot capture behavior.

```python
@dataclass
class SnapshotConfig:
    mode: SnapshotMode = SnapshotMode.FULL_PAGE
    capture_html: bool = True
    capture_screenshot: bool = True
    capture_console: bool = True
    capture_network: bool = True
    deduplication_enabled: bool = True
    async_save: bool = True
    selector: Optional[str] = None
```

**Fields:**
- `mode`: Capture mode (FULL_PAGE, SELECTOR, MINIMAL, BOTH)
- `capture_html`: Whether to capture HTML content
- `capture_screenshot`: Whether to capture screenshots
- `capture_console`: Whether to capture console logs
- `capture_network`: Whether to capture network logs
- `deduplication_enabled`: Whether to enable content deduplication
- `async_save`: Whether to use async parallel saving
- `selector`: CSS selector for element-specific capture

### SnapshotBundle

Represents a complete snapshot bundle with all artifacts.

```python
@dataclass
class SnapshotBundle:
    context: SnapshotContext
    timestamp: datetime
    config: SnapshotConfig
    bundle_path: str
    artifacts: List[str]
    metadata: Dict[str, Any]
```

## Integration APIs

### SiteSnapshotManager

Simplified interface for site-specific snapshot management.

```python
from src.sites.site_snapshot_integration import SiteSnapshotManager

site_manager = SiteSnapshotManager("flashscore")
```

#### Methods

##### capture_scraping_snapshot()

Capture a snapshot during normal scraping operations.

```python
async def capture_scraping_snapshot(
    self,
    page,
    module: str = None,
    component: str = None,
    function_name: str = None,
    selector: Optional[str] = None,
    **kwargs
)
```

##### capture_failure_snapshot()

Capture a snapshot when a failure occurs.

```python
async def capture_failure_snapshot(
    self,
    page,
    error_type: str,
    error_message: str,
    module: str = None,
    component: str = None,
    function_name: str = None,
    **kwargs
)
```

##### handle_selector_failure()

Handle selector failure using the event-driven system.

```python
async def handle_selector_failure(
    self,
    page,
    selector: str,
    module: str = None,
    component: str = None,
    function_name: str = None
)
```

### ScraperSnapshotMixin

Mixin class for easy integration with existing scrapers.

```python
from src.sites.site_snapshot_integration import ScraperSnapshotMixin

class MyScraper(ScraperSnapshotMixin, BaseScraper):
    def __init__(self):
        super().__init__()
        self.initialize_snapshots("mysite", CaptureEnvironment.PRODUCTION)
```

#### Methods

##### initialize_snapshots()

Initialize snapshot functionality for the scraper.

```python
def initialize_snapshots(self, site_name: str, environment: CaptureEnvironment)
```

##### capture_page_snapshot()

Capture a snapshot of the current page state.

```python
async def capture_page_snapshot(self, page, function_name: str = "page_load", **kwargs)
```

##### handle_failure()

Handle a failure with automatic snapshot capture.

```python
async def handle_failure(self, page, error_type: str, error_message: str, **kwargs)
```

## Configuration APIs

### Configuration Presets

Predefined configurations for different environments.

```python
from src.core.snapshot.config_presets import SnapshotConfigPresets, CaptureEnvironment

# Production configuration
prod_config = SnapshotConfigPresets.get_production_config()

# Debug configuration
debug_config = SnapshotConfigPresets.get_debug_config()

# Testing configuration
test_config = SnapshotConfigPresets.get_testing_config()

# Get config for environment
config = SnapshotConfigPresets.get_config_for_environment(CaptureEnvironment.PRODUCTION)
```

### Available Environments

- `CaptureEnvironment.PRODUCTION`: Minimal capture, only on failures
- `CaptureEnvironment.DEBUG`: Full capture for comprehensive debugging
- `CaptureEnvironment.TESTING`: Balanced capture for test validation

## Event-Driven APIs

### EventDrivenSnapshotManager

Manages event-driven snapshot creation with multiple triggers.

```python
from src.core.snapshot.triggers import EventDrivenSnapshotManager

event_manager = EventDrivenSnapshotManager(snapshot_manager)
```

#### Methods

##### handle_event()

Handle an event and potentially trigger snapshot creation.

```python
async def handle_event(self, trigger_type: SnapshotTriggerType, context: Dict[str, Any]) -> bool
```

##### register_trigger()

Register a custom snapshot trigger.

```python
def register_trigger(self, trigger: SnapshotTrigger)
```

### Available Trigger Types

```python
from src.core.snapshot.triggers import SnapshotTriggerType

# Trigger types
SnapshotTriggerType.SELECTOR_FAILURE
SnapshotTriggerType.RETRY_EXHAUSTION
SnapshotTriggerType.TIMEOUT
SnapshotTriggerType.EXTRACTION_MISMATCH
```

### SnapshotManager Event Handlers

The SnapshotManager includes built-in event handlers:

```python
# Handle selector failure
await manager.handle_selector_failure(page, site, module, component, session_id, selector)

# Handle retry exhaustion
await manager.handle_retry_exhaustion(page, site, module, component, session_id, retry_count, max_retries, last_error)

# Handle timeout
await manager.handle_timeout(page, site, module, component, session_id, timeout_duration, operation)

# Handle extraction mismatch
await manager.handle_extraction_mismatch(page, site, module, component, session_id, expected_data, actual_data, validation_errors)
```

## Migration APIs

### SnapshotMigrator

Handles migration of existing flat snapshots to hierarchical bundles.

```python
from src.core.snapshot.migration import SnapshotMigrator

migrator = SnapshotMigrator("old_snapshots", "new_snapshots")
```

#### Methods

##### scan_existing_snapshots()

Scan existing flat snapshots and return migration candidates.

```python
def scan_existing_snapshots(self) -> List[Dict[str, Any]]
```

##### migrate_snapshots()

Migrate all existing snapshots to new hierarchical structure.

```python
async def migrate_snapshots(self, dry_run: bool = False) -> Dict[str, Any]
```

### MigrationValidator

Validates migrated snapshots for completeness and correctness.

```python
from src.core.snapshot.migration import MigrationValidator

validator = MigrationValidator("new_snapshots")
```

#### Methods

##### validate_migration()

Validate all migrated snapshots.

```python
async def validate_migration(self) -> Dict[str, Any]
```

## Feature Flag APIs

### FeatureFlagManager

Manages feature flags for gradual rollout.

```python
from src.core.snapshot.feature_flags import get_feature_flag_manager

feature_manager = get_feature_flag_manager()
```

#### Methods

##### is_feature_enabled()

Check if a feature is enabled for the given context.

```python
def is_feature_enabled(self, feature_name: str, site: Optional[str] = None, environment: Optional[str] = None) -> bool
```

##### enable_feature()

Enable a feature with specified rollout percentage.

```python
def enable_feature(self, feature_name: str, rollout_percentage: float = 100.0)
```

##### set_rollout_stage()

Set the current rollout stage.

```python
def set_rollout_stage(self, stage: RolloutStage)
```

##### set_site_rollout()

Set rollout percentage for a specific site.

```python
def set_site_rollout(self, site: str, percentage: float)
```

### Convenience Functions

```python
from src.core.snapshot.feature_flags import (
    is_context_aware_snapshots_enabled,
    is_dual_capture_enabled,
    is_async_performance_enabled,
    is_event_driven_enabled,
    is_legacy_compatibility_enabled
)

# Check if features are enabled
if is_context_aware_snapshots_enabled():
    # Use new system
    pass
```

## Monitoring APIs

### SnapshotSystemMonitor

Main monitoring system for the snapshot system.

```python
from src.core.snapshot.monitoring_system import get_system_monitor

monitor = get_system_monitor(snapshot_manager)
```

#### Methods

##### start_monitoring()

Start the monitoring system.

```python
async def start_monitoring(self)
```

##### stop_monitoring()

Stop the monitoring system.

```python
async def stop_monitoring(self)
```

##### get_monitoring_status()

Get current monitoring status.

```python
def get_monitoring_status(self) -> Dict[str, Any]
```

### AlertManager

Manages alert creation, routing, and resolution.

```python
monitor.alert_manager.create_alert(
    AlertType.PERFORMANCE_DEGRADATION,
    AlertSeverity.WARNING,
    "Performance threshold exceeded"
)
```

#### Methods

##### create_alert()

Create and process a new alert.

```python
def create_alert(self, alert_type: AlertType, severity: AlertSeverity, message: str, metadata: Optional[Dict[str, Any]] = None) -> Alert
```

##### get_active_alerts()

Get all unresolved alerts.

```python
def get_active_alerts(self) -> List[Alert]
```

## Rollback APIs

### RollbackManager

Manages rollback procedures for the snapshot system.

```python
from src.core.snapshot.rollback import RollbackManager

rollback_manager = RollbackManager()
```

#### Methods

##### create_backup()

Create a complete backup of the current snapshot system.

```python
def create_backup(self, description: str = "") -> str
```

##### rollback_to_backup()

Rollback to a specific backup.

```python
def rollback_to_backup(self, backup_id: str, force: bool = False) -> bool
```

##### rollback_feature_flags()

Rollback feature flags to a specific stage.

```python
def rollback_feature_flags(self, stage: RolloutStage, force: bool = False) -> bool
```

### EmergencyRollback

Emergency rollback procedures for critical issues.

```python
from src.core.snapshot.rollback import EmergencyRollback

# Emergency disable all new features
EmergencyRollback.emergency_disable_all_features()

# Emergency restore to legacy system
EmergencyRollback.emergency_restore_legacy_system()
```

## Browser Integration APIs

### BrowserSnapshotIntegration

Integration layer between browser automation and snapshot system.

```python
from src.core.snapshot.integration import BrowserSnapshotIntegration

integration = BrowserSnapshotIntegration(snapshot_manager)
```

#### Methods

##### capture_snapshot_on_selector_failure()

Integrate snapshot capture with browser manager on selector failure.

```python
async def capture_snapshot_on_selector_failure(
    self,
    browser_manager,
    site: str,
    module: str,
    component: str,
    session_id: str,
    selector: str,
    matched_count: int = 0
) -> bool
```

## Compatibility APIs

### LegacySnapshotManager

Backward compatibility wrapper for the new SnapshotManager.

```python
from src.core.snapshot.compatibility import LegacySnapshotManager

legacy_manager = LegacySnapshotManager()
```

#### Methods

##### capture_snapshot()

Legacy snapshot capture method (deprecated).

```python
async def capture_snapshot(
    self,
    page,
    site: str = "unknown",
    module: str = "unknown",
    component: str = "unknown",
    session_id: Optional[str] = None,
    capture_mode: str = "full",
    **kwargs
)
```

### CompatibilityLayer

Provides compatibility utilities for the transition period.

```python
from src.core.snapshot.compatibility import CompatibilityLayer

# Create context from legacy parameters
context = CompatibilityLayer.create_context_from_legacy_params(
    site="example.com",
    module="scraping",
    component="extractor"
)
```

## Error Handling

### Exceptions

```python
from src.core.snapshot.exceptions import SnapshotError, BundleCorruptionError, ArtifactCaptureError

try:
    bundle = await manager.capture_snapshot(page, context)
except SnapshotError as e:
    print(f"Snapshot error: {e}")
except BundleCorruptionError as e:
    print(f"Bundle corruption: {e}")
except ArtifactCaptureError as e:
    print(f"Artifact capture error: {e}")
```

## Utility APIs

### DirectoryManager

Manages hierarchical directory creation and validation.

```python
from src.core.snapshot.utils import DirectoryManager

dir_manager = DirectoryManager("data/snapshots")
```

#### Methods

##### create_bundle_directory()

Create the full directory structure for a snapshot bundle.

```python
async def create_bundle_directory(self, context: SnapshotContext, timestamp: datetime) -> pathlib.Path
```

##### get_bundle_path()

Get the expected bundle path without creating directories.

```python
def get_bundle_path(self, context: SnapshotContext, timestamp: datetime) -> pathlib.Path
```

### PerformanceMonitor

Collects and manages performance metrics.

```python
from src.core.snapshot.monitoring import PerformanceMonitor

perf_monitor = PerformanceMonitor()
```

#### Methods

##### get_performance_summary()

Get comprehensive performance summary.

```python
def get_performance_summary(self) -> Dict[str, Any]
```

## Enums and Constants

### SnapshotMode

```python
from src.core.snapshot.models import SnapshotMode

SnapshotMode.FULL_PAGE
SnapshotMode.SELECTOR
SnapshotMode.MINIMAL
SnapshotMode.BOTH
```

### AlertSeverity and AlertType

```python
from src.core.snapshot.monitoring_system import AlertSeverity, AlertType

AlertSeverity.INFO
AlertSeverity.WARNING
AlertSeverity.ERROR
AlertSeverity.CRITICAL

AlertType.PERFORMANCE_DEGRADATION
AlertType.ERROR_RATE_HIGH
AlertType.STORAGE_SPACE_LOW
AlertType.CAPTURE_FAILURE
```

---

**API Version**: 1.0.0  
**Last Updated**: 2026-02-13
