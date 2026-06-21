# Quick Start Guide for Selector Telemetry System

This guide will help you get the Selector Telemetry System up and running quickly.

## Prerequisites

- Python 3.11 or higher
- asyncio support
- Required Python packages (see requirements.txt)
- Sufficient disk space for telemetry data

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/scorewise-scraper.git
cd scorewise-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Verify installation:
```bash
python -c "import src.telemetry; print('Installation successful')"
```

## Basic Configuration

### 1. Initialize Telemetry System

```python
from src.telemetry import TelemetrySystem

# Create telemetry system instance
telemetry = TelemetrySystem()

# Start the system
await telemetry.start()
```

### 2. Configure Basic Settings

```python
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration

# Create configuration
config = TelemetryConfiguration(
    enable_data_collection=True,
    enable_alerting=True,
    enable_reporting=True,
    enable_storage=True
)

# Apply configuration
await telemetry.configure(config)
```

## Quick Usage Examples

### 1. Start Data Collection

```python
from src.telemetry.collectors.performance_collector import PerformanceCollector

# Create performance collector
performance_collector = PerformanceCollector(telemetry.storage_manager)

# Start collecting metrics
await performance_collector.start_collection()
```

### 2. Generate Reports

```python
from src.telemetry.reporting.report_generator import ReportGenerator, ReportType
from datetime import datetime, timedelta

# Create report generator
report_generator = ReportGenerator(
    metrics_processor=telemetry.metrics_processor,
    aggregator=telemetry.aggregator
)

# Generate performance report
time_range = (datetime.now() - timedelta(days=7), datetime.now())
report = await report_generator.generate_performance_report(
    time_range=time_range
)

# Export report
await report_generator.export_report(report, "performance_report.html", ReportFormat.HTML)
```

### 3. Set Up Alerting

```python
from src.telemetry.alerting.alert_engine import AlertEngine
from src.telemetry.configuration.alert_thresholds import AlertThresholdsConfiguration

# Create alert engine
alert_engine = AlertEngine(
    metrics_processor=telemetry.metrics_processor,
    threshold_monitor=telemetry.threshold_monitor
)

# Configure alert thresholds
thresholds_config = AlertThresholdsConfiguration()
await alert_engine.configure_thresholds(thresholds_config)

# Start alerting
await alert_engine.start_monitoring()
```

### 4. Monitor Storage

```python
from src.telemetry.storage.monitoring import StorageMonitoring

# Create storage monitor
storage_monitor = StorageMonitoring(telemetry.storage_manager)

# Start monitoring
await storage_monitor.start_monitoring(interval_seconds=300)  # 5 minutes

# Get storage statistics
stats = await storage_monitor.get_monitoring_statistics()
print(f"Storage usage: {stats['total_usage_gb']}GB / {stats['total_capacity_gb']}GB")
```

## Data Collection Examples

### Performance Metrics

```python
from src.telemetry.collectors.performance_collector import PerformanceCollector

# Create performance collector
performance_collector = PerformanceCollector(telemetry.storage_manager)

# Collect timing metrics
await performance_collector.collect_timing_metrics(
    selector_name="example_selector",
    operation_type="click",
    start_time=datetime.now() - timedelta(seconds=5),
    end_time=datetime.now()
)

# Get statistics
stats = await performance_collector.get_statistics()
print(f"Average response time: {stats['average_response_time']}ms")
```

### Quality Metrics

```python
from src.telemetry.collectors.quality_collector import QualityCollector

# Create quality collector
quality_collector = QualityCollector(telemetry.storage_manager)

# Collect quality metrics
await quality_collector.collect_quality_metrics(
    selector_name="example_selector",
    operation_type="click",
    success=True,
    confidence_score=0.95
)

# Get statistics
stats = await quality_collector.get_statistics()
print(f"Average confidence score: {stats['average_confidence']}")
```

### Strategy Metrics

```python
from src.telemetry.collectors.strategy_collector import StrategyCollector

# Create strategy collector
strategy_collector = StrategyCollector(telemetry.storage_manager)

# Collect strategy metrics
await strategy_collector.collect_strategy_metrics(
    selector_name="example_selector",
    operation_type="click",
    primary_strategy="css_selector",
    alternative_strategies=["xpath_selector", "text_selector"],
    strategy_performance={"css_selector": 0.95, "xpath_selector": 0.85}
)

# Get statistics
stats = await strategy_collector.get_statistics()
print(f"Most used strategy: {stats['most_used_strategy']}")
```

## Reporting Examples

### Performance Report

```python
from src.telemetry.reporting.performance_reports import PerformanceReports

# Create performance reports
performance_reports = PerformanceReports(
    report_generator=report_generator,
    performance_collector=performance_collector
)

# Generate performance overview
time_range = (datetime.now() - timedelta(days=7), datetime.now())
report = await performance_reports.generate_performance_overview(
    time_range=time_range,
    include_recommendations=True
)

# Export to HTML
await report_generator.export_report(report, "performance_report.html", ReportFormat.HTML)
```

### Usage Analysis Report

```python
from src.telemetry.reporting.usage_reports import UsageReports

# Create usage reports
usage_reports = UsageReports(
    report_generator=report_generator,
    strategy_collector=strategy_collector
)

# Generate usage analysis
report = await usage_reports.generate_usage_overview(
    time_range=(datetime.now() - timedelta(days=30), datetime.now()),
    group_by="selector",
    include_patterns=True
)
```

### Health Report

```python
from src.telemetry.reporting.health_reports import HealthReports

# Create health reports
health_reports = HealthReports(
    report_generator=report_generator,
    quality_collector=quality_collector,
    error_collector=telemetry.error_collector
)

# Generate health overview
report = await health_reports.generate_health_overview(
    time_range=(datetime.now() - timedelta(days=7), datetime.now()),
    include_recommendations=True
)
```

## Alerting Examples

### Create Alert Rules

```python
from src.telemetry.alerting.alert_engine import AlertEngine
from src.telemetry.models.selector_models import MetricType

# Create alert for high response times
await alert_engine.create_alert_rule(
    metric_name="response_time",
    threshold_value=1000.0,  # 1 second
    comparison="greater_than",
    severity="warning"
)

# Create alert for low success rates
await alert_engine.create_alert_rule(
    metric_name="success_rate",
    threshold_value=0.95,  # 95%
    comparison="less_than",
    severity="error"
)
```

### Manual Alert Creation

```python
from src.telemetry.models.selector_models import TelemetryEvent

# Create manual alert
alert = await alert_engine.create_manual_alert(
    title="Performance Degradation Detected",
    message="Response time has increased significantly",
    severity="warning",
    metadata={"current_response_time": 1200.0, "threshold": 1000.0}
)
```

## Storage Management Examples

### Data Retention

```python
from src.telemetry.storage.retention_manager import RetentionManager, RetentionPolicy, RetentionAction

# Create retention manager
retention_manager = RetentionManager(telemetry.storage_manager)

# Create retention policy
policy_id = await retention_manager.create_policy(
    name="30-Day Data Retention",
    description="Delete telemetry data after 30 days",
    policy_type=RetentionPolicyType.TIME_BASED,
    target_data_type="events",
    retention_period=timedelta(days=30),
    action=RetentionAction.DELETE
)

# Apply retention policy
result = await retention_manager.apply_policy(policy_id)
print(f"Deleted {result.records_deleted} records, freed {result.space_freed_mb:.1f}MB")
```

### Data Archival

```python
from src.telemetry.storage.archival import DataArchival, ArchiveFormat

# Create archival system
archival = DataArchival(telemetry.storage_manager)

# Create archival policy
policy_id = await archival.create_archive_policy(
    name="Monthly Archive",
    description="Archive old telemetry data monthly",
    source_data_type="events",
    archive_format=ArchiveFormat.JSON_GZ,
    archive_location="/data/telemetry/archive",
    retention_period=timedelta(days=365)
)

# Archive data
task_id = await archival.archive_data(policy_id, [
    "/data/telemetry/events/2024/01",
    "/data/telemetry/events/2023/12"
])
```

### Backup Operations

```python
from src.telemetry.storage.backup import BackupAndRecovery, BackupType

# Create backup system
backup_system = BackupAndRecovery(telemetry.storage_manager)

# Create backup policy
policy_id = await backup_system.create_backup_policy(
    name="Daily Backup",
    description="Daily full backup of telemetry data",
    backup_type=BackupType.FULL,
    source_paths=["/data/telemetry/events"],
    backup_location="/data/telemetry/backups",
    schedule="0 2 * * *",  # Daily at 2 AM
    retention_days=30
)

# Execute backup
task_id = await backup_system.execute_backup(policy_id)
print(f"Backup completed: {task_id}")
```

## Advanced Features

### Trend Analysis

```python
from src.telemetry.reporting.trend_analysis import TrendAnalysis

# Create trend analysis
trend_analysis = TrendAnalysis(
    report_generator=report_generator
)

# Analyze trends
time_range = (datetime.now() - timedelta(days=30), datetime.now())
trends = await trend_analysis.analyze_trends(
    metric_names=["response_time", "success_rate"],
    time_range=time_range,
    include_forecast=True,
    forecast_periods=7
)
```

### Optimization Recommendations

```python
from src.telemetry.reporting.recommendations import OptimizationRecommendations

# Create recommendations engine
recommendations = OptimizationRecommendations(
    performance_collector=performance_collector,
    quality_collector=quality_collector
)

# Generate recommendations
recommendations = await recommendations.generate_recommendations(
    time_range=(datetime.now() - timedelta(days=7), datetime.now()),
    categories=["performance", "quality", "strategy"]
)

# Apply recommendations
for rec in recommendations:
    print(f"Recommendation: {rec.title}")
    print(f"Impact: {rec.impact}")
    print(f"Confidence: {rec.confidence}")
```

### Data Quality Assessment

```python
from src.telemetry.reporting.data_quality import DataQualityMetrics

# Create quality metrics
quality_metrics = DataQualityMetrics(report_generator)

# Assess data quality
quality_score = await quality_metrics.assess_data_quality(
    time_range=(datetime.now() - timedelta(days=7), datetime.now())
)

print(f"Overall quality score: {quality_score.overall_score:.2f}")
print(f"Quality status: {quality_score.status.value}")
```

## Monitoring and Observability

### System Health Check

```python
# Get system statistics
stats = await telemetry.get_system_statistics()
print(f"Total events collected: {stats['total_events']}")
print(f"Active alerts: {stats['active_alerts']}")
print(f"Storage usage: {stats['storage_usage_mb']:.1f}MB")
```

### Performance Monitoring

```python
# Get performance statistics
perf_stats = await telemetry.get_performance_statistics()
print(f"Average response time: {perf_stats['average_response_time']:.2f}ms")
print(f"Success rate: {perf_stats['success_rate']:.2%}")
print(f"Error rate: {perf_stats['error_rate']:.2%}")
```

## Troubleshooting

### Common Issues

1. **Installation Issues**
   - Ensure Python 3.11+ is installed
   - Check all dependencies are installed
   - Verify virtual environment is activated

2. **Configuration Issues**
   - Check configuration file permissions
   - Validate JSON syntax
   - Ensure all required fields are present

3. **Performance Issues**
   - Monitor system resources
   - Check storage capacity
   - Review alert thresholds

4. **Data Issues**
   - Verify data integrity
   - Check backup status
   - Review retention policies

### Getting Help

- Check the [Troubleshooting](troubleshooting.md) guide
- Review the [User Guide](user-guide/) for detailed instructions
- Check the [API Reference](api/) for technical details
- Create an issue in the project repository

## Next Steps

1. Explore the [User Guide](user_guide/) for detailed usage instructions
2. Review the [API Reference](api/) for technical documentation
3. Check the [Development Guide](development/) for contribution guidelines
4. Consider the [Deployment Guide](deployment/) for production deployment

## Support

For questions, issues, or contributions, please create an issue in the project repository or refer to the documentation.
