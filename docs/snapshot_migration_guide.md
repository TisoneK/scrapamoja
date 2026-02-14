# Context-Aware Snapshot System: Migration Guide

## Overview

This guide provides comprehensive documentation for migrating from the legacy flat snapshot system to the new context-aware hierarchical bundle architecture.

## Table of Contents

1. [System Overview](#system-overview)
2. [Migration Prerequisites](#migration-prerequisites)
3. [Migration Process](#migration-process)
4. [Configuration](#configuration)
5. [Feature Flags](#feature-flags)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

## System Overview

### What's New

The context-aware snapshot system introduces:

- **Hierarchical Organization**: `data/snapshots/<site>/<module>/<YYYYMMDD>/<HHMMSS_session>/`
- **Dual HTML Capture**: Full page and element-specific captures with hash-based naming
- **Event-Driven Triggers**: Automatic snapshots on failures, timeouts, and extraction mismatches
- **Performance Optimizations**: Async parallel saving and content deduplication
- **Comprehensive Monitoring**: Real-time health checks and alerting
- **Gradual Rollout**: Feature flags for controlled deployment

### Architecture Benefits

- **Scalability**: Hierarchical structure prevents directory overload
- **Debuggability**: Context-aware organization simplifies issue investigation
- **Performance**: Async operations and deduplication reduce resource usage
- **Maintainability**: Event-driven architecture reduces manual snapshot management
- **Observability**: Built-in monitoring and alerting capabilities

## Migration Prerequisites

### System Requirements

- Python 3.8+
- AsyncIO-compatible environment
- Sufficient disk space for migration (temporary + new structure)
- Backup system for existing snapshots

### Dependencies

```bash
# Core dependencies
pip install asyncio pathlib dataclasses typing

# Optional monitoring dependencies
pip install psutil  # For system monitoring
```

### Pre-Migration Checklist

- [ ] Create a complete backup of existing snapshots
- [ ] Verify system meets requirements
- [ ] Schedule maintenance window for migration
- [ ] Test migration in staging environment
- [ ] Prepare rollback plan

## Migration Process

### Step 1: Automated Migration

Use the provided migration script:

```bash
# Preview migration (dry run)
python scripts/migrate_snapshots.py --dry-run

# Execute migration
python scripts/migrate_snapshots.py

# Validate migration
python scripts/migrate_snapshots.py --validate
```

### Step 2: Configuration

Configure the new system:

```python
from src.core.snapshot import SnapshotManager, SnapshotContext
from src.core.snapshot.config_presets import CaptureEnvironment

# Create snapshot manager
manager = SnapshotManager("data/snapshots")

# Create context for snapshots
context = SnapshotContext(
    site="example_site",
    module="scraping",
    component="extractor",
    session_id="session_123",
    function="data_extraction"
)
```

### Step 3: Feature Flag Rollout

Configure gradual rollout:

```python
from src.core.snapshot.feature_flags import get_feature_flag_manager, RolloutStage

# Get feature flag manager
feature_manager = get_feature_flag_manager()

# Set rollout stage
feature_manager.set_rollout_stage(RolloutStage.GRADUAL_ROLLOUT)

# Enable specific features
feature_manager.enable_feature("context_aware_bundles", rollout_percentage=10.0)
```

### Step 4: Monitoring Setup

Enable monitoring:

```python
from src.core.snapshot.monitoring_system import get_system_monitor
import asyncio

# Get monitor
monitor = get_system_monitor(manager)

# Start monitoring
asyncio.run(monitor.start_monitoring())
```

## Configuration

### Environment Configuration

```python
# Production environment
from src.core.snapshot.config_presets import SnapshotConfigPresets, CaptureEnvironment

config = SnapshotConfigPresets.get_config_for_environment(CaptureEnvironment.PRODUCTION)

# Debug environment
debug_config = SnapshotConfigPresets.get_config_for_environment(CaptureEnvironment.DEBUG)
```

### Custom Configuration

```python
from src.core.snapshot.models import SnapshotConfig, SnapshotMode

custom_config = SnapshotConfig(
    mode=SnapshotMode.BOTH,
    capture_html=True,
    capture_screenshot=True,
    capture_console=True,
    capture_network=True,
    deduplication_enabled=True,
    async_save=True
)
```

### Site-Specific Configuration

```python
from src.sites.site_snapshot_integration import SiteSnapshotManager

# Create site-specific manager
site_manager = SiteSnapshotManager("flashscore")
site_manager.set_environment(CaptureEnvironment.PRODUCTION)
```

## Feature Flags

### Rollout Stages

1. **DISABLED**: All new features disabled
2. **INTERNAL_TESTING**: Internal testing only
3. **BETA_TESTING**: Beta testing with limited rollout
4. **GRADUAL_ROLLOUT**: Gradual percentage-based rollout
5. **FULL_ROLLOUT**: All features enabled

### Feature Flag Management

```python
from src.core.snapshot.feature_flags import get_feature_flag_manager

manager = get_feature_flag_manager()

# Check if feature is enabled
if manager.is_feature_enabled("context_aware_bundles", site="flashscore"):
    # Use new system
    pass

# Enable feature with rollout percentage
manager.enable_feature("dual_html_capture", rollout_percentage=25.0)

# Set site-specific rollout
manager.set_site_rollout("flashscore", 50.0)
```

### Available Features

- `context_aware_bundles`: Core hierarchical bundle system
- `dual_html_capture`: Full page + element capture
- `async_performance`: Async parallel operations
- `event_driven_snapshots`: Automatic failure triggers
- `performance_monitoring`: Metrics and alerting
- `legacy_compatibility`: Backward compatibility layer
- `migration_tools`: Migration utilities

## Monitoring and Alerting

### Setting Up Monitoring

```python
from src.core.snapshot.monitoring_system import SnapshotSystemMonitor
import asyncio

# Create monitor
monitor = SnapshotSystemMonitor(snapshot_manager)

# Start monitoring
asyncio.run(monitor.start_monitoring())
```

### Alert Types

- **PERFORMANCE_DEGRADATION**: Performance threshold breaches
- **ERROR_RATE_HIGH**: High failure rates
- **STORAGE_SPACE_LOW**: Disk space issues
- **CAPTURE_FAILURE**: Snapshot capture failures
- **FEATURE_FLAG_ANOMALY**: Inconsistent feature flag states
- **SYSTEM_HEALTH**: General system health issues

### Custom Alert Handlers

```python
def custom_alert_handler(alert):
    """Custom alert handler for external systems."""
    if alert.severity.value == "critical":
        # Send to external monitoring system
        send_to_monitoring_system(alert)

monitor.alert_manager.add_alert_handler(custom_alert_handler)
```

### Performance Metrics

Key metrics to monitor:

- **Average Capture Time**: Should be < 5 seconds
- **Success Rate**: Should be > 95%
- **Deduplication Rate**: Should be > 50%
- **Parallel Execution Rate**: Should be > 80%
- **Cache Utilization**: Should be < 80%

## Rollback Procedures

### Creating Backups

```python
from src.core.snapshot.rollback import RollbackManager

# Create backup
rollback_manager = RollbackManager()
backup_id = rollback_manager.create_backup("Pre-migration backup")
```

### Emergency Rollback

```python
from src.core.snapshot.rollback import EmergencyRollback

# Emergency disable all new features
EmergencyRollback.emergency_disable_all_features()

# Emergency restore to legacy system
EmergencyRollback.emergency_restore_legacy_system()
```

### Rollback to Backup

```python
# List available backups
backups = rollback_manager.list_backups()

# Rollback to specific backup
success = rollback_manager.rollback_to_backup(backup_id)
```

### Feature Flag Rollback

```python
from src.core.snapshot.rollback import RollbackManager
from src.core.snapshot.feature_flags import RolloutStage

# Rollback to previous stage
manager = RollbackManager()
manager.rollback_feature_flags(RolloutStage.BETA_TESTING)
```

## Troubleshooting

### Common Issues

#### Migration Fails

**Symptoms**: Migration script fails with errors

**Solutions**:
1. Check source directory permissions
2. Verify sufficient disk space
3. Run with `--dry-run` first to identify issues
4. Check migration log for specific errors

```bash
python scripts/migrate_snapshots.py --dry-run --log-file migration.log
```

#### Performance Degradation

**Symptoms**: Slower snapshot capture after migration

**Solutions**:
1. Check if async performance is enabled
2. Verify deduplication is working
3. Monitor cache utilization
4. Check for storage I/O issues

```python
# Check performance metrics
metrics = snapshot_manager.get_performance_metrics()
print(metrics)
```

#### Feature Flags Not Working

**Symptoms**: New features not enabled despite configuration

**Solutions**:
1. Verify feature flag configuration file
2. Check environment variable settings
3. Validate feature dependencies
4. Check rollout stage settings

```python
# Check feature flag status
manager = get_feature_flag_manager()
status = manager.get_rollout_status()
print(status)
```

#### Monitoring Alerts

**Symptoms**: Continuous alerting for performance issues

**Solutions**:
1. Adjust threshold values in monitoring config
2. Check system resources (CPU, memory, disk)
3. Verify snapshot capture patterns
4. Consider scaling resources

### Debug Mode

Enable debug mode for detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug configuration
from src.core.snapshot.config_presets import SnapshotConfigPresets, CaptureEnvironment
config = SnapshotConfigPresets.get_config_for_environment(CaptureEnvironment.DEBUG)
```

### Validation Tools

```python
# Validate migrated snapshots
from src.core.snapshot.migration import MigrationValidator

validator = MigrationValidator("data/snapshots")
results = await validator.validate_migration()
print(results)
```

## API Reference

### Core Classes

#### SnapshotManager

```python
class SnapshotManager:
    def __init__(self, base_path: str = "data/snapshots")
    
    async def capture_snapshot(
        self,
        page,
        context: SnapshotContext,
        config: Optional[SnapshotConfig] = None,
        timestamp: Optional[datetime] = None
    ) -> SnapshotBundle
```

#### SnapshotContext

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

#### SnapshotConfig

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

### Integration Classes

#### SiteSnapshotManager

```python
class SiteSnapshotManager:
    def __init__(self, site_name: str, base_path: str = "data/snapshots")
    
    async def capture_scraping_snapshot(
        self,
        page,
        module: str = None,
        component: str = None,
        function_name: str = None,
        selector: Optional[str] = None
    )
```

#### ScraperSnapshotMixin

```python
class ScraperSnapshotMixin:
    def initialize_snapshots(self, site_name: str, environment: CaptureEnvironment)
    
    async def capture_page_snapshot(self, page, function_name: str = "page_load")
    
    async def handle_failure(self, page, error_type: str, error_message: str)
```

### Migration Classes

#### SnapshotMigrator

```python
class SnapshotMigrator:
    def __init__(self, old_snapshot_path: str, new_snapshot_path: str)
    
    def scan_existing_snapshots(self) -> List[Dict[str, Any]]
    
    async def migrate_snapshots(self, dry_run: bool = False) -> Dict[str, Any]
```

### Monitoring Classes

#### SnapshotSystemMonitor

```python
class SnapshotSystemMonitor:
    def __init__(self, snapshot_manager: SnapshotManager)
    
    async def start_monitoring(self)
    
    async def stop_monitoring(self)
    
    def get_monitoring_status(self) -> Dict[str, Any]
```

## Best Practices

### Performance Optimization

1. **Enable async operations** for better performance
2. **Use deduplication** to reduce storage usage
3. **Configure appropriate capture modes** for different environments
4. **Monitor performance metrics** regularly
5. **Clean up old snapshots** periodically

### Error Handling

1. **Use event-driven triggers** for automatic failure capture
2. **Implement retry logic** for transient failures
3. **Monitor error rates** and set up alerts
4. **Use graceful degradation** when features fail
5. **Maintain backward compatibility** during transitions

### Storage Management

1. **Use hierarchical organization** to prevent directory overload
2. **Implement cleanup policies** for old snapshots
3. **Monitor storage usage** and set up alerts
4. **Consider compression** for long-term storage
5. **Plan storage capacity** based on usage patterns

### Security Considerations

1. **Secure snapshot storage** with appropriate permissions
2. **Sanitize sensitive data** before capture
3. **Implement access controls** for snapshot viewing
4. **Audit snapshot access** regularly
5. **Encrypt sensitive snapshots** if required

## Support and Resources

### Getting Help

- Check the troubleshooting section for common issues
- Review the API reference for correct usage
- Enable debug mode for detailed logging
- Contact the development team for complex issues

### Additional Resources

- [API Documentation](api_reference.md)
- [Performance Tuning Guide](performance_tuning.md)
- [Security Guidelines](security_guidelines.md)
- [Migration Scripts](../scripts/)
- [Configuration Examples](config_examples/)

---

**Last Updated**: 2026-02-13  
**Version**: 1.0.0  
**Maintainer**: Snapshot System Team
