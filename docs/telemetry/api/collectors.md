# Collectors API Reference

This document provides detailed API reference for the telemetry data collectors.

## Performance Collector API

### Class: PerformanceCollector

The PerformanceCollector captures timing and performance metrics from selector operations.

#### Constructor

```python
PerformanceCollector(
    storage_manager: StorageManager,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[TelemetryLogger] = None
)
```

**Parameters:**
- `storage_manager`: Storage manager for persisting metrics
- `config`: Optional configuration dictionary
- `logger`: Optional logger instance

#### Methods

##### collect_timing_metrics

```python
async def collect_timing_metrics(
    self,
    selector_name: str,
    operation_type: str,
    start_time: datetime,
    end_time: datetime,
    strategy_name: Optional[str] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> PerformanceMetrics
```

**Parameters:**
- `selector_name`: Name of the selector
- `operation_type`: Type of operation (click, extract, etc.)
- `start_time`: Start time of the operation
- `end_time`: End time of the operation
- `strategy_name`: Optional strategy name
- `additional_metrics`: Optional additional metrics

**Returns:**
- `PerformanceMetrics`: The collected performance metrics

**Example:**
```python
metrics = await performance_collector.collect_timing_metrics(
    selector_name="product_list_selector",
    operation_type="click",
    start_time=datetime.now() - timedelta(seconds=5),
    end_time=datetime.now()
)
```

##### collect_timing_metrics_batch

```python
async def collect_timing_metrics_batch(
    self,
    events: List[Dict[str, Any]]
) -> List[PerformanceMetrics]
```

**Parameters:**
- `events`: List of timing events

**Returns:**
- `List[PerformanceMetrics]`: List of collected metrics

##### get_statistics

```python
async def get_statistics(
    self,
    time_range: Optional[Tuple[datetime, datetime]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `time_range`: Optional time range for statistics

**Returns:**
- `Dict[str, Any]`: Performance statistics

### Data Classes

#### PerformanceMetrics

```python
@dataclass
class PerformanceMetrics:
    metric_id: str
    selector_name: str
    operation_type: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    strategy_name: Optional[str] = None
    additional_metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
```

## Quality Collector API

### Class: QualityCollector

The QualityCollector monitors data quality and confidence scores.

#### Constructor

```python
QualityCollector(
    storage_manager: StorageManager,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[TelemetryLogger] = None
)
```

#### Methods

##### collect_quality_metrics

```python
async def collect_quality_metrics(
    self,
    selector_name: str,
    operation_type: str,
    success: bool,
    confidence_score: Optional[float] = None,
    error_type: Optional[str] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> QualityMetrics
```

**Parameters:**
- `selector_name`: Name of the selector
- `operation_type`: Type of operation
- `success`: Whether the operation was successful
- `confidence_score`: Optional confidence score
- `error_type`: Optional error type
- `additional_metrics`: Optional additional metrics

**Returns:**
- `QualityMetrics`: The collected quality metrics

##### get_statistics

```python
async def get_statistics(
    self,
    time_range: Optional[Tuple[datetime, datetime]] = None
) -> Dict[str, Any]
```

### Data Classes

#### QualityMetrics

```python
@dataclass
class QualityMetrics:
    metric_id: str
    selector_name: str
    operation_type: str
    success: bool
    confidence_score: Optional[float] = None
    error_type: Optional[str] = None
    additional_metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
```

## Strategy Collector API

### Class: StrategyCollector

The StrategyCollector tracks strategy usage and effectiveness.

#### Constructor

```python
StrategyCollector(
    storage_manager: StorageManager,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[TelemetryLogger] = None
)
```

#### Methods

##### collect_strategy_metrics

```python
async def collect_strategy_metrics(
    self,
    selector_name: str,
    operation_type: str,
    primary_strategy: str,
    alternative_strategies: Optional[List[str]] = None,
    strategy_performance: Optional[Dict[str, float]] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> StrategyMetrics
```

**Parameters:**
- `selector_name`: Name of the selector
- `operation_type`: Type of operation
- `primary_strategy`: Primary strategy used
- `alternative_strategies`: Optional alternative strategies
- `strategy_performance`: Optional strategy performance data
- `additional_metrics`: Optional additional metrics

**Returns:**
- `StrategyMetrics`: The collected strategy metrics

##### get_statistics

```python
async def get_statistics(
    self,
    time_range: Optional[Tuple[datetime, datetime]] = None
) -> Dict[str, Any]
```

### Data Classes

#### StrategyMetrics

```python
@dataclass
class StrategyMetrics:
    metric_id: str
    selector_name: str
    operation_type: str
    primary_strategy: str
    alternative_strategies: Optional[List[str]] = None
    strategy_performance: Optional[Dict[str, float]] = None
    additional_metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
```

## Error Collector API

### Class: ErrorCollector

The ErrorCollector captures error data and patterns.

#### Constructor

```python
ErrorCollector(
    storage_manager: StorageManager,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[TelemetryLogger] = None
)
```

#### Methods

##### collect_error_data

```python
async def collect_error_data(
    self,
    selector_name: str,
    operation_type: str,
    error_type: str,
    error_message: str,
    stack_trace: Optional[str] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> ErrorData
```

**Parameters:**
- `selector_name`: Name of the selector
- `operation_type`: Type of operation
- `error_type`: Type of error
- `error_message`: Error message
- `stack_trace`: Optional stack trace
- `additional_metrics`: Optional additional metrics

**Returns:**
- `ErrorData`: The collected error data

##### get_statistics

```python
async def get_statistics(
    self,
    time_range: Optional[Tuple[datetime, datetime]] = None
) -> Dict[str, Any]
```

### Data Classes

#### ErrorData

```python
@dataclass
class ErrorData:
    error_id: str
    selector_name: str
    operation_type: str
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    additional_metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
```

## Context Collector API

### Class: ContextCollector

The ContextCollector records browser session and page context information.

#### Constructor

```python
ContextCollector(
    storage_manager: StorageManager,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[TelemetryLogger] = None
)
```

#### Methods

##### collect_context_data

```python
async def collect_context_data(
    self,
    selector_name: str,
    operation_type: str,
    browser_session_id: str,
    tab_context_id: str,
    page_url: str,
    additional_context: Optional[Dict[str, Any]] = None
) -> ContextData
```

**Parameters:**
- `selector_name`: Name of the selector
- `operation_type`: Type of operation
- `browser_session_id`: Browser session ID
- `tab_context_id`: Tab context ID
- `page_url`: Page URL
- `additional_context`: Optional additional context

**Returns:**
- `ContextData`: The collected context data

##### get_statistics

```python
async def get_statistics(
    self,
    time_range: Optional[Tuple[datetime, datetime]] = None
) -> Dict[str, Any]
```

### Data Classes

#### ContextData

```python
@dataclass
class ContextData:
    context_id: str
    selector_name: str
    operation_type: str
    browser_session_id: str
    tab_context_id: str
    page_url: str
    additional_context: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
```

## Configuration Options

### Performance Collector Configuration

```python
performance_config = {
    "collection_interval_seconds": 60,
    "batch_size": 100,
    "enable_anomaly_detection": True,
    "enable_real_time_processing": True,
    "max_events_per_minute": 1000
}
```

### Quality Collector Configuration

```python
quality_config = {
    "confidence_threshold": 0.8,
    "enable_anomaly_detection": True,
    "enable_trend_analysis": True,
    "collection_interval_seconds": 60
}
```

### Strategy Collector Configuration

```python
strategy_config = {
    "enable_effectiveness_analysis": True,
    "enable_usage_tracking": True,
    "enable_pattern_detection": True,
    "collection_interval_seconds": 60
}
```

### Error Collector Configuration

```python
error_config = {
    "enable_pattern_analysis": True,
    "enable_trend_detection": True,
    "enable_recovery_analysis": True,
    "collection_interval_seconds": 60
}
```

### Context Collector Configuration

```python
context_config = {
    "enable_session_tracking": True,
    "enable_page_context_analysis": True,
    "enable_navigation_tracking": True,
    "collection_interval_seconds": 60
}
```

## Error Handling

### Common Exceptions

#### ValueError

```python
# Invalid parameters
try:
    await performance_collector.collect_timing_metrics(
        selector_name="",
        operation_type="click",
        start_time=datetime.now(),
        end_time=datetime.now()
    )
except ValueError as e:
    print(f"Invalid parameters: {e}")
```

#### StorageError

```python
# Storage issues
try:
    await performance_collector.collect_timing_metrics(...)
except StorageError as e:
    print(f"Storage error: {e}")
```

#### ConfigurationError

```python
# Configuration issues
try:
    collector = PerformanceCollector(storage_manager, invalid_config)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Examples

### Basic Usage

```python
# Create collectors
performance_collector = PerformanceCollector(storage_manager)
quality_collector = QualityCollector(storage_manager)

# Collect metrics
await performance_collector.collect_timing_metrics(
    selector_name="product_list_selector",
    operation_type="click",
    start_time=datetime.now() - timedelta(seconds=5),
    end_time=datetime.now()
)

await quality_collector.collect_quality_metrics(
    selector_name="product_list_selector",
    operation_type="click",
    success=True,
    confidence_score=0.95
)
```

### Batch Collection

```python
# Collect multiple metrics in batch
events = [
    {
        "selector_name": "selector_1",
        "operation_type": "click",
        "start_time": datetime.now() - timedelta(seconds=5),
        "end_time": datetime.now()
    },
    {
        "selector_name": "selector_2",
        "operation_type": "click",
        "start_time": datetime.now() - timedelta(seconds=3),
        "end_time": datetime.now()
    }
]

metrics = await performance_collector.collect_timing_metrics_batch(events)
```

### Statistics Retrieval

```python
# Get performance statistics
stats = await performance_collector.get_statistics()
print(f"Average response time: {stats['average_response_time']:.2f}ms")
print(f"Success rate: {stats['success_rate']:.2%}")

# Get quality statistics
quality_stats = await quality_collector.get_statistics()
print(f"Average confidence score: {quality_stats['average_confidence']:.2f}")
```

## Best Practices

1. **Use Appropriate Collection Intervals**: Balance freshness with performance
2. **Batch Processing**: Use batch processing for high-volume operations
3. **Error Handling**: Implement proper error handling and retry logic
4. **Resource Management**: Monitor memory and CPU usage
5. **Data Validation**: Validate input parameters before collection
6. **Logging**: Use structured logging for debugging
7. **Testing**: Unit test collector functionality
8. **Monitoring**: Monitor collector performance and health

## Support

For additional help:
- Check the [User Guide](../user-guide/)
- Review [Architecture Overview](../architecture.md)
- Create an issue in the repository
- Check the [Troubleshooting](../troubleshooting.md) guide
