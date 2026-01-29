# Configuration Guide for Selector Telemetry System

This guide covers configuration options for the Selector Telemetry System, including basic setup, advanced configuration, and best practices.

## Configuration Overview

The Selector Telemetry System uses a hierarchical configuration approach:

1. **Environment Variables**: System-wide settings
2. **Configuration Files**: YAML/JSON configuration files
3. **Code Configuration**: Runtime configuration objects
4. **Default Values**: Built-in fallback values

## Configuration Files

### Primary Configuration

#### `config/telemetry_config.yaml`

```yaml
# Main telemetry configuration
enable_data_collection: true
enable_alerting: true
enable_reporting: true
enable_storage: true

# Data Collection Settings
data_collection:
  collection_interval_seconds: 60
  batch_size: 100
  max_events_per_minute: 1000
  enable_real_time_processing: true

# Alerting Settings
alerting:
  check_interval_seconds: 30
  cooldown_seconds: 300
  max_alerts_per_hour: 10
  default_severity: "warning"

# Reporting Settings
reporting:
  generation_interval_hours: 24
  auto_export: true
  default_format: "json"
  include_recommendations: true

# Storage Settings
storage:
  base_path: "/data/telemetry"
  max_storage_gb: 10000
  cleanup_interval_hours: 24
  compression_enabled: true
  encryption_enabled: true
  monitoring_enabled: true
```

### Alert Thresholds

#### `config/alert_thresholds.yaml`

```yaml
# Performance thresholds
performance:
  response_time:
    warning: 1000.0    # 1 second
    critical: 5000.0    # 5 seconds
  throughput:
    warning: 50.0       # operations per minute
    critical: 20.0       # operations per minute

# Quality thresholds
quality:
  confidence_score:
    warning: 0.8       # 80%
    critical: 0.7       # 70%
  success_rate:
    warning: 0.95       # 95%
    critical: 0.90       # 90%
  error_rate:
    warning: 0.05       # 5%
    critical: 0.10       # 10%
```

### Storage Configuration

#### `config/storage_config.yaml`

```yaml
# Storage settings
storage:
  paths:
    data: "/data/telemetry"
    temp: "/tmp/telemetry"
    logs: "/data/telemetry/logs"
    backups: "/data/telemetry/backups"
    archive: "/data/telemetry/archive"

# Retention policies
retention:
  default_retention_days: 30
  cleanup_interval_hours: 24
  auto_cleanup_enabled: true
  archive_after_retention: true

# Backup settings
backup:
  default_type: "full"
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention_days: 30
  compression_enabled: true
  encryption_enabled: true
  verification_enabled: true

# Tiered storage
tiered_storage:
  hot_tier:
    storage_type: "ssd"
    location: "/data/storage/hot"
    max_capacity_gb: 100
    performance_tier: 1
    cost_per_gb: 0.25
    
  warm_tier:
    storage_type: "ssd"
    location: "/data/storage/warm"
    max_capacity_gb: 500
    performance_tier: 2
    cost_per_gb: 0.15
    
  cold_tier:
    storage_type: "hdd"
    location: "/data/storage/cold"
    max_capacity_gb: 2000
    performance_tier: 3
    cost_per_gb: 0.05
    
  archive_tier:
    storage_type: "cloud"
    location: "s3://telemetry-archive"
    max_capacity_gb: 10000
    performance_tier: 4
    cost_per_gb: 0.01
```

## Environment Variables

### Required Variables

```bash
# Core telemetry configuration
export TELEMETRY_CONFIG_PATH="/path/to/config/telemetry_config.yaml"
export TELEMETRY_LOG_LEVEL="INFO"
export TELEMETRY_STORAGE_PATH="/data/telemetry"

# Optional: Database configuration
export TELEMETRY_DB_HOST="localhost"
export TELEMETRY_DB_PORT="5432"
export TELEMETRY_DB_NAME="telemetry"
export TELEMETRY_DB_USER="telemetry"
export TELEMETRY_DB_PASSWORD="password"
```

### Optional Variables

```bash
# Performance tuning
export TELEMETRY_COLLECTION_INTERVAL=60
export TELEMETRY_BATCH_SIZE=100
export TELEMETRY_MAX_EVENTS_PER_MINUTE=1000

# Storage optimization
export TELEMETRY_COMPRESSION=true
export TELEMETRY_ENCRYPTION=true
export TELEMETRY_CLEANUP_INTERVAL=24

# Alerting
export TELEMETRY_ALERT_COOLDOWN=300
export TELEMETRY_MAX_ALERTS_PER_HOUR=10
export TELEMETRY_DEFAULT_SEVERITY="warning"
```

## Runtime Configuration

### Python Configuration

```python
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration

# Create configuration
config = TelemetryConfiguration(
    enable_data_collection=True,
    collection_interval_seconds=60,
    batch_size=100,
    max_events_per_minute=1000,
    enable_real_time_processing=True
)

# Apply configuration
await telemetry.configure(config)
```

### YAML Configuration Loading

```python
import yaml

# Load from file
with open(config_path, 'r') as f:
    config_data = yaml.safe_load(f)
    config = TelemetryConfiguration(**config_data)
```

### Environment-Specific Configuration

```python
import os

# Load environment-specific config
config_path = os.getenv('TELEMETRY_CONFIG_PATH')
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
        config = TelemetryConfiguration(**config_data)
```

## Advanced Configuration

### Custom Collectors

```python
from src.telemetry.collectors.performance_collector import PerformanceCollector

# Custom collector with configuration
collector = PerformanceCollector(
    storage_manager=storage_manager,
    config=config.performance,
    collection_interval=30,  # 30 seconds
    batch_size=50,      # Smaller batches
    enable_anomaly_detection=True
)
```

### Custom Alert Rules

```python
from src.telemetry.alerting.alert_engine import AlertEngine

# Custom alert engine with custom thresholds
alert_engine = AlertEngine(
    metrics_processor=metrics_processor,
    threshold_monitor=threshold_monitor,
    custom_thresholds={
        "response_time_p99": 2000.0,
        "error_rate_p99": 0.02,
        "success_rate_p99": 0.98
    }
)
```

### Custom Storage Configuration

```python
from src.telemetry.storage.tiered_storage import TieredStorage

# Custom tiered storage configuration
tiered_storage = TieredStorage(
    storage_manager=storage_manager,
    custom_tiers=[
        {
            "tier": "ultra_fast",
            "storage_type": "nvme",
            "location": "/data/storage/ultra_fast",
            "max_capacity_gb": 50,
            "performance_tier": 0,
            "cost_per_gb": 0.50
        }
    ]
)
```

## Validation

### Configuration Validation

```python
from src.telemetry.configuration.validation import ConfigValidator

# Validate configuration
validator = ConfigValidator()

# Validate telemetry configuration
is_valid, errors = validator.validate_telemetry_config(config)
if not is_valid:
    print(f"Configuration errors: {errors}")
    for error in errors:
        print(f"Error: {error}")
```

### Schema Validation

```python
from src.telemetry.configuration.validation import ConfigValidator

# Validate configuration schema
is_valid, errors = validator.validate_storage_config(storage_config)
if not is_valid:
    print(f"Storage config errors: {errors}")
```

## Best Practices

### Performance Optimization

1. **Collection Frequency**
   - High-frequency operations: 30-60 seconds
   - Normal operations: 60-300 seconds
   - Background operations: 5-15 minutes

2. **Batch Size**
   - Small datasets: 50-100 records per batch
   - Medium datasets: 100-500 records per batch
   - Large datasets: 500-1000 records per batch

3. **Storage Optimization**
   - Enable compression for historical data
   - Use appropriate storage tiers
   - Implement regular cleanup

### Security Best Practices

1. **Data Encryption**
   - Enable encryption for sensitive data
   - Use secure key management
   - Rotate encryption keys regularly

2. **Access Control**
   - Implement role-based access control
   - Use principle of least privilege
   - Audit access attempts

3. **Data Privacy**
   - Implement data minimization
   - Set appropriate retention periods
   - Comply with privacy regulations

### Monitoring Best Practices

1. **Comprehensive Monitoring**
   - Monitor all system components
   - Set appropriate alert thresholds
   - Implement health checks

2. **Alert Management**
   - Configure alert cooldowns
   - Implement alert escalation
   - Track alert lifecycle

3. **Log Management**
   - Use structured logging
   - Implement log rotation
   - Archive old logs

### Configuration Management

1. **Version Control**
   - Version configuration files
   - Track configuration changes
   - Maintain backward compatibility

2. **Environment Separation**
   - Use environment-specific configs
   - Secure sensitive configurations
   - Document configuration differences

3. **Validation**
   - Validate on startup
   - Validate on configuration changes
   - Implement schema validation

## Troubleshooting

### Common Installation Issues

#### Permission Errors

```bash
# Fix permission issues
sudo chown -R $USER:$USER /data/telemetry
chmod 755 /data/telemetry
```

#### Configuration Errors

```bash
# Check configuration syntax
python -m "
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration
TelemetryConfiguration.validate()
"

# Check file permissions
ls -la $TELEMETRY_CONFIG_PATH
```

#### Performance Issues

```python
# Monitor resource usage
import psutil
print(f"CPU: {psutil.cpu_percent()}%")
print(f"Memory: {psutil.virtual_memory().percent()}%")
print(f"Disk: {psutil.disk_usage('/data/telemetry').percent}%")
```

### Configuration Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Show configuration
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration
config = TelemetryConfiguration()
print(f"Config path: {config.config_path}")
print(f"Storage path: {config.storage_path}")
print(f"Enabled: {config.enabled}")
```

### Getting Help

For additional help:
- Check the [Troubleshooting](troubleshooting.md) guide
- Review [Architecture Overview](architecture.md) for system design
- Check [API Reference](api/) for technical details
- Create an issue in the repository for specific issues

## Next Steps

1. **Complete User Guide**: Continue with the user guide sections
2. **API Reference**: Review the API documentation
3. **Development Guide**: Check development guidelines
4. **Deployment Guide**: Prepare for production deployment

## Support Resources

- **Documentation**: [Documentation Index](README.md)
- **Community**: GitHub Issues and Discussions
- **Wiki**: Project Wiki pages
- **Discordance**: Community channels

The Selector Telemetry System is now ready for comprehensive monitoring and analytics of your web scraping operations! 🚀
