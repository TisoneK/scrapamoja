# Quickstart Guide: Selector Telemetry System

**Date**: 2025-01-27  
**Purpose**: Quick implementation guide for selector telemetry

## Overview

The Selector Telemetry System provides comprehensive monitoring and analytics for selector operations. This guide covers the essential steps to get telemetry running with minimal configuration.

## Prerequisites

- Python 3.11+ with asyncio
- Existing Selector Engine implementation
- Playwright (async API) for browser automation
- JSON schema support

## Quick Setup

### 1. Basic Configuration

Create a minimal telemetry configuration:

```python
# telemetry_config.py
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration

config = TelemetryConfiguration(
    collection_enabled=True,
    storage_type="json",  # Default JSON storage
    buffer_size=1000,
    flush_interval_seconds=30,
    retention_days=30,
    performance_overhead_threshold=0.02,  # 2% overhead
    correlation_id_enabled=True
)
```

### 2. Initialize Telemetry System

```python
# main.py
from src.telemetry.collector.metrics_collector import MetricsCollector
from src.telemetry.storage.storage_manager import StorageManager
from src.telemetry.processor.metrics_processor import MetricsProcessor
from src.telemetry.alerting.alert_engine import AlertEngine

async def initialize_telemetry():
    # Initialize storage
    storage = StorageManager(config)
    await storage.initialize()
    
    # Initialize processor
    processor = MetricsProcessor(config)
    
    # Initialize alert engine
    alert_engine = AlertEngine(config)
    
    # Initialize collector
    collector = MetricsCollector(
        config=config,
        storage=storage,
        processor=processor,
        alert_engine=alert_engine
    )
    
    await collector.initialize()
    return collector
```

### 3. Integrate with Selector Engine

Add telemetry hooks to your selector operations:

```python
# selector_integration.py
from src.telemetry.integration.selector_integration import SelectorTelemetryIntegration

class SelectorEngine:
    def __init__(self, telemetry_collector):
        self.telemetry = SelectorTelemetryIntegration(telemetry_collector)
    
    async def resolve_selector(self, selector_name: str, context: dict):
        # Generate correlation ID
        correlation_id = await self.telemetry.get_correlation_id()
        
        # Start telemetry tracking
        event_id = await self.telemetry.on_selector_start(
            selector_name=selector_name,
            correlation_id=correlation_id,
            context=context
        )
        
        try:
            # Execute selector resolution
            start_time = time.time()
            result = await self._execute_resolution(selector_name, context)
            end_time = time.time()
            
            # Record success metrics
            metrics = {
                "resolution_time_ms": (end_time - start_time) * 1000,
                "confidence_score": result.get("confidence", 0.0),
                "elements_found": len(result.get("elements", [])),
                "success": True
            }
            
            await self.telemetry.on_selector_complete(
                event_id=event_id,
                metrics=metrics,
                result=result
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            error_data = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "stack_trace": traceback.format_exc()
            }
            
            await self.telemetry.on_selector_error(
                event_id=event_id,
                error=error_data
            )
            
            raise
```

## Core Components Usage

### Metrics Collection

```python
# Collect custom metrics
await collector.record_metrics(
    selector_name="product_title",
    metrics={
        "resolution_time_ms": 45.2,
        "confidence_score": 0.92,
        "elements_found": 1,
        "strategy_used": "text_anchor"
    }
)

# Record events
await collector.record_event({
    "event_type": "selector_resolution",
    "selector_name": "product_title",
    "timestamp": datetime.utcnow().isoformat(),
    "performance_metrics": {...},
    "quality_metrics": {...}
})
```

### Alert Configuration

```python
# Configure performance alerts
alert_thresholds = [
    {
        "threshold_name": "slow_resolution",
        "metric_name": "resolution_time_ms",
        "condition_type": "greater_than",
        "threshold_value": 1000.0,  # 1 second
        "severity": "medium",
        "enabled": True,
        "evaluation_window_minutes": 5
    },
    {
        "threshold_name": "low_confidence",
        "metric_name": "confidence_score",
        "condition_type": "less_than",
        "threshold_value": 0.8,
        "severity": "high",
        "enabled": True,
        "evaluation_window_minutes": 10
    }
]

await alert_engine.update_thresholds(alert_thresholds)
```

### Data Retrieval

```python
# Get recent events for a selector
events = await storage.get_events(
    selector_name="product_title",
    start_time=datetime.utcnow() - timedelta(hours=24),
    limit=100
)

# Get aggregated metrics
metrics = await storage.get_aggregated_metrics(
    selector_name="product_title",
    time_period="hour",
    start_time=datetime.utcnow() - timedelta(days=7),
    end_time=datetime.utcnow()
)

print(f"Average resolution time: {metrics['average_resolution_time_ms']:.2f}ms")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Error rate: {metrics['error_rate']:.2%}")
```

## Monitoring and Alerting

### Real-time Monitoring

```python
# Set up real-time monitoring
async def monitor_performance():
    while True:
        # Check for performance issues
        recent_events = await storage.get_events(
            start_time=datetime.utcnow() - timedelta(minutes=5)
        )
        
        # Analyze performance
        if recent_events:
            avg_time = sum(e["performance_metrics"]["resolution_time_ms"] 
                          for e in recent_events) / len(recent_events)
            
            if avg_time > 500:  # 500ms threshold
                print(f"⚠️  Performance alert: Average resolution time {avg_time:.2f}ms")
        
        await asyncio.sleep(60)  # Check every minute

# Start monitoring
asyncio.create_task(monitor_performance())
```

### Alert Handling

```python
# Handle alerts
async def handle_alerts():
    alerts = await alert_engine.get_active_alerts()
    
    for alert in alerts:
        if alert["severity"] == "critical":
            # Immediate notification
            await send_critical_notification(alert)
        elif alert["severity"] == "high":
            # Email notification
            await send_email_alert(alert)
        
        # Acknowledge alert
        await alert_engine.acknowledge_alert(alert["alert_id"])
```

## Reporting

### Generate Performance Report

```python
# Generate daily performance report
async def generate_daily_report():
    report = await report_generator.generate_performance_report(
        start_time=datetime.utcnow() - timedelta(days=1),
        end_time=datetime.utcnow()
    )
    
    # Save report
    report_path = f"reports/performance_{datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Report generated: {report_path}")
    
    # Print summary
    print(f"Total operations: {report['overall_metrics']['total_operations']}")
    print(f"Average confidence: {report['overall_metrics']['average_confidence']:.3f}")
    print(f"Error rate: {report['overall_metrics']['error_rate']:.2%}")

# Schedule daily reports
asyncio.create_task(schedule_daily_report(generate_daily_report))
```

## Performance Optimization

### Buffer Management

```python
# Optimize buffer settings for high-volume scenarios
config.buffer_size = 5000  # Increase buffer size
config.flush_interval_seconds = 10  # More frequent flushes
config.performance_overhead_threshold = 0.01  # Stricter overhead limit
```

### Storage Optimization

```python
# Use InfluxDB for high-performance scenarios
config.storage_type = "influxdb"
config.influxdb_config = {
    "url": "http://localhost:8086",
    "token": "your-token",
    "org": "your-org",
    "bucket": "telemetry"
}
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```python
   # Reduce buffer size
   config.buffer_size = 500
   config.flush_interval_seconds = 15
   ```

2. **Storage Performance**
   ```python
   # Enable batch writes
   config.batch_writes = True
   config.batch_size = 100
   ```

3. **Missing Events**
   ```python
   # Check if telemetry is enabled
   if not collector.is_enabled():
       print("Telemetry collection is disabled")
   ```

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('src.telemetry').setLevel(logging.DEBUG)

# Check buffer status
buffer_status = await collector.get_buffer_status()
print(f"Buffer size: {buffer_status['current_size']}")
print(f"Buffer utilization: {buffer_status['utilization']:.2%}")
```

## Best Practices

### Performance
- Keep buffer sizes reasonable (1000-5000 events)
- Use appropriate flush intervals (10-60 seconds)
- Monitor overhead to stay under 2% threshold

### Data Management
- Set appropriate retention policies (30-90 days)
- Regular cleanup of old data
- Monitor storage usage

### Alerting
- Configure meaningful thresholds
- Avoid alert fatigue with proper severity levels
- Regularly review and adjust thresholds

### Integration
- Use correlation IDs for end-to-end tracking
- Handle telemetry failures gracefully
- Keep telemetry impact minimal

## Next Steps

1. **Configure Production Settings**: Set up appropriate thresholds and retention policies
2. **Integrate All Selectors**: Add telemetry hooks to all selector operations
3. **Set Up Monitoring**: Configure real-time monitoring and alerting
4. **Create Dashboards**: Build visualization for telemetry data
5. **Optimize Performance**: Fine-tune buffer settings and storage configuration

## Support

For issues and questions:
- Check the logs in `logs/telemetry.log`
- Review the configuration in `telemetry_config.py`
- Monitor system performance metrics
- Consult the full documentation in `docs/telemetry/`
