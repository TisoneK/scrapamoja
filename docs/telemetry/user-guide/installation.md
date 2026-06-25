# Installation Guide for Selector Telemetry System

This guide will help you install and configure the Selector Telemetry System in your environment.

## System Requirements

### Minimum Requirements
- Python 3.11 or higher
- 4GB available disk space
- 2GB RAM minimum
- Network connectivity (for remote storage options)

### Recommended Requirements
- Python 3.11+ with asyncio support
- 8GB+ disk space
- 4GB+ RAM
- SSD storage for optimal performance
- Network access for cloud storage (optional)

### Supported Platforms
- Linux (Ubuntu 18.04+, CentOS 7+, Debian 10+)
- macOS 10.15+
- Windows 10+ (with WSL2)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-org/scorewise-scraper.git
cd scorewise-scraper
```

### 2. Create Virtual Environment

```bash
# Using venv (recommended)
python -m venv telemetry-env
telemetry-env\Scripts\activate

# Using conda (alternative)
conda create -n telemetry-env python=3.11
conda activate telemetry-env
```

### 3. Install Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 4. Verify Installation

```python
# Test basic import
python -c "
import src.telemetry
print('Installation successful')
"

# Test core components
python -c "
from src.telemetry.telemetry_system import TelemetrySystem
print('Core system import successful')
"
```

## Configuration

### 1. Basic Configuration

Create a configuration file:

```python
# config/telemetry_config.yaml
enable_data_collection: true
enable_alerting: true
enable_reporting: true
enable_storage: true
```

### 2. Environment Variables

```bash
# Set environment variables
export TELEMETRY_CONFIG_PATH="/path/to/config/telemetry_config.yaml"
export TELEMETRY_LOG_LEVEL="INFO"
export TELEMETRY_STORAGE_PATH="/data/telemetry"
```

### 3. Database Configuration

```python
# config/telemetry_config.py
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration

config = TelemetryConfiguration(
    enable_data_collection=True,
    enable_alerting=True,
    enable_reporting=True,
    enable_storage=True,
    storage_path="/data/telemetry",
    log_level="INFO"
)
```

## Quick Start

### 1. Initialize System

```python
from src.telemetry.telemetry_system import TelemetrySystem

# Create telemetry system
telemetry = TelemetrySystem()

# Configure system
config = TelemetryConfiguration()
await telemetry.configure(config)
```

### 2. Start System Services

```python
# Start all services
await telemetry.start()

# Start individual components
await telemetry.start_data_collection()
await telemetry.start_alerting()
await telemetry.start_reporting()
await telemetry.start_storage_monitoring()
```

### 3. Verify Installation

```python
# Check system status
stats = await telemetry.get_system_statistics()
print(f"Events collected: {stats['total_events']}")
print(f"Active alerts: {stats['active_alerts']}")
print(f"Storage usage: {stats['storage_usage_mb']:.1f}MB")
```

## Configuration Options

### Telemetry Configuration

```python
# config/telemetry_config.py
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration

config = TelemetryConfiguration(
    # Data Collection
    enable_data_collection=True,
    collection_interval_seconds=60,
    batch_size=100,
    
    # Alerting
    enable_alerting=True,
    alert_check_interval_seconds=30,
    alert_cooldown_seconds=300,
    
    # Reporting
    enable_reporting=True,
    report_generation_interval_hours=24,
    auto_export_reports=True,
    
    # Storage
    enable_storage=True,
    storage_path="/data/telemetry",
    max_storage_gb=10000,
    cleanup_interval_hours=24,
    
    # Logging
    log_level="INFO",
    enable_file_logging=True,
    enable_console_logging=True
)
```

### Alert Thresholds

```python
# config/alert_thresholds.yaml
from src.telemetry.configuration.alert_thresholds import AlertThresholdsConfiguration

thresholds = AlertThresholdsConfiguration(
    response_time_warning=1000.0,  # 1 second
    response_time_critical=5000.0,  # 5 seconds
    success_rate_warning=0.95,      # 95%
    success_rate_critical=0.90,      # 90%
    error_rate_warning=0.05,         # 5%
    error_rate_critical=0.10,        # 10%
)
```

### Storage Configuration

```python
# config/storage_config.py
from src.telemetry.configuration.storage_config import StorageConfigManager

config_manager = StorageConfigManager()

# Create retention policy
retention_config_id = await config_manager.create_retention_config(
    name="30-Day Retention",
    description="Delete telemetry data after 30 days",
    policies=[
        {
            "policy_type": "time_based",
            "retention_period_days": 30,
            "action": "delete"
        }
    ]
)

# Create backup configuration
backup_config_id = await config_manager.create_backup_config(
    name="Daily Backup",
    description="Daily full backup of telemetry data",
    backup_policies=[
        {
            "backup_type": "full",
            "schedule": "0 2 * * *",
            "retention_days": 30
        }
    ]
)
```

## Component Configuration

### Performance Collector

```python
from src.telemetry.collectors.performance_collector import PerformanceCollector

collector = PerformanceCollector(
    storage_manager=telemetry.storage_manager,
    config=config.performance
)

# Configure collector
collector.set_collection_interval(60)  # 1 minute intervals
collector.set_batch_size(100)
```

### Quality Collector

```python
from src.telemetry.collectors.quality_collector import QualityCollector

collector = QualityCollector(
    storage_manager=storage_manager,
    config=config.quality
)

# Configure collector
collector.set_confidence_threshold(0.8)  # Minimum confidence score
collector.set_anomaly_detection(True)
```

### Strategy Collector

```python
from src.telemetry.collectors.strategy_collector import StrategyCollector

collector = StrategyCollector(
    storage_manager=storage_manager,
    config=config.strategy
)

# Configure collector
collector.set_tracking_enabled(True)
collector.set_effectiveness_analysis(True)
```

### Error Collector

```python
from src.telemetry.collectors.error_collector import ErrorCollector

collector = ErrorCollector(
    storage_manager=storage_manager,
    config=config.error
)

# Configure collector
collector.set_error_tracking(True)
collector.set_pattern_analysis(True)
```

## Integration Examples

### Web Scraping Integration

```python
from src.telemetry.telemetry_system import TelemetrySystem
from your_scraping_framework import WebScraper

# Initialize telemetry system
telemetry = TelemetrySystem()

# Create custom collector
class CustomCollector:
    async def collect_event(self, event_data):
        await telemetry.collect_event(event_data)

# Integrate with web scraper
scraper = WebScraper()
scraper.add_event_listener(CustomCollector())
```

### Monitoring Integration

```python
from src.telemetry.telemetry_system import TelemetrySystem
from your_monitoring_system import MonitoringSystem

# Initialize both systems
telemetry = TelemetrySystem()
monitoring = MonitoringSystem()

# Forward telemetry data to monitoring system
await telemetry.add_data_consumer(monitoring.process_telemetry_data)
```

### Alerting Integration

```python
from src.telemetry.telemetry_system import TelemetrySystem
from your_alerting_system import AlertSystem

# Initialize systems
telemetry = TelemetrySystem()
alerting = AlertSystem()

# Forward alerts to alerting system
await telemetry.add_alert_consumer(alerting.process_alert)
```

## Testing

### Unit Tests

```python
# Run all tests
pytest tests/

# Run specific test category
pytest tests/test_collectors/
pytest tests/test_reporting/
pytest tests/test_storage/
```

### Integration Tests

```python
# Run integration tests
pytest tests/integration/

# Run performance tests
pytest tests/performance/
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
EXPOSE 8080

CMD ["python", "-m", "src.telemetry.telemetry_system", "start"]]
```

### Systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/telemetry.service > /dev/null << EOF
[Unit]
Description=Selector Telemetry System
After=network.target
[Service]
Type=simple
User=telemetry
ExecStart=/usr/bin/python -m src.telemetry.telemetry_system start
Restart=always
RestartSec=10
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable telemetry
sudo systemctl start telemetry
```

## Troubleshooting

### Common Issues

#### Installation Issues

**Problem**: Python version incompatibility
```bash
python --version
# Should show Python 3.11+
```

**Problem**: Missing dependencies
```bash
pip install -r requirements.txt
# Check for missing packages
pip list
```

**Problem**: Permission errors
```bash
# Check directory permissions
ls -la /data/
sudo chown -R $USER:$USER /data/telemetry
```

#### Configuration Issues

**Problem**: Configuration file not found
```bash
# Check config path
echo $TELEMETRY_CONFIG_PATH
ls -la $TELEMETRY_CONFIG_PATH
```

**Problem**: Invalid configuration
```bash
# Validate configuration
python -c "
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration
TelemetryConfiguration.validate()
"
```

#### Performance Issues

**Problem**: High memory usage
```bash
# Monitor memory usage
python -c "
import psutil
print(f"Memory usage: {psutil.virtual_memory().percent}%")
"

# Reduce collection frequency
collector.set_collection_interval(300)  # 5 minutes
```

#### Storage Issues

**Problem**: Storage path not accessible
```bash
# Check storage path
ls -la /data/telemetry
sudo chown -R $USER:$USER /data/telemetry
```

#### Alerting Issues

**Problem Alerts not firing
```python
# Check alert configuration
alert_engine = telemetry.alert_engine
print(f"Alert rules: {len(alert_engine.alert_rules)}")
print(f"Active alerts: {len(alert_engine.active_alerts)}")
```

### Getting Help

#### Documentation
- [Quick Start Guide](quickstart.md)
- [User Guide](user-guide/)
- [API Reference](api/)
- [Troubleshooting](troubleshooting.md)

#### Community Support
- GitHub Issues: Create an issue in the repository
- Discussions: Start a discussion for questions
- Wiki: Check community documentation

#### Technical Support
- Architecture: Review [Architecture Overview](architecture.md)
- API Reference: Check [API Reference](api/)
- Configuration: Check [Configuration Guide](configuration/)

## Next Steps

1. **Explore the User Guide** for detailed usage instructions
2. **Review the API Reference** for technical details
3. **Check Development Guide** for customization options
4. **Review Deployment Guide** for production deployment
5. **Configure Monitoring** for production monitoring

## Support

For additional help:
- Create an issue in the repository
- Start a discussion in the project
- Check the documentation for more information
