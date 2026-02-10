# Data Model: Selector Engine Integration

**Date**: 2025-01-29  
**Feature**: 012-selector-engine-integration  
**Purpose**: Entity definitions for selector engine integration

## Core Entities

### SelectorOperation

Represents a single selector engine operation with strategy, confidence score, and result.

**Attributes**:
- `operation_id`: String - Unique identifier for the operation
- `element_purpose`: String - Human-readable description of what element is being located
- `strategies_used`: Array[StrategyResult] - List of strategies attempted in order
- `successful_strategy`: StrategyResult - The strategy that succeeded
- `total_duration_ms`: Integer - Total time taken for all strategies
- `confidence_threshold`: Float - Minimum confidence required for success
- `timestamp`: DateTime - When the operation was performed

### StrategyResult

Represents the result of a single selector strategy attempt.

**Attributes**:
- `strategy_type`: String - Type of strategy (CSS, XPath, Text, etc.)
- `selector_expression`: String - The actual selector used
- `confidence_score`: Float - Confidence score (0.0-1.0)
- `duration_ms`: Integer - Time taken for this strategy
- `success`: Boolean - Whether this strategy found an element
- `element_found`: Boolean - Whether an element was located
- `error_message`: String - Error details if strategy failed

### TelemetryEvent

Captures selector performance data including timing, success rate, and fallback usage.

**Attributes**:
- `event_id`: String - Unique identifier for the telemetry event
- `session_id`: String - Browser session identifier
- `operation_count`: Integer - Number of selector operations in session
- `total_operations_duration_ms`: Integer - Cumulative time for all operations
- `average_confidence_score`: Float - Average confidence across successful operations
- `fallback_usage_rate`: Float - Percentage of operations requiring fallback strategies
- `success_rate`: Float - Percentage of operations that succeeded
- `strategies_usage_distribution`: Object - Usage count by strategy type

### ElementInteraction

Records the interaction type (click, type, scroll) and associated selector information.

**Attributes**:
- `interaction_id`: String - Unique identifier for the interaction
- `operation_id`: String - Reference to the SelectorOperation
- `interaction_type`: String - Type of interaction (click, type, scroll, hover)
- `element_description`: String - Human-readable description of target element
- `interaction_success`: Boolean - Whether the interaction completed successfully
- `interaction_duration_ms`: Integer - Time taken for the interaction
- `error_details`: String - Error information if interaction failed

## Data Relationships

```
SelectorOperation (1) -> (*) StrategyResult
SelectorOperation (1) -> (*) ElementInteraction
TelemetryEvent (1) -> (*) SelectorOperation
BrowserSession (1) -> (*) TelemetryEvent
```

## Validation Rules

### SelectorOperation Validation
- `operation_id` must be unique within session
- `confidence_threshold` must be between 0.0 and 1.0
- `total_duration_ms` must be non-negative
- At least one strategy must be attempted

### StrategyResult Validation
- `confidence_score` must be between 0.0 and 1.0
- `duration_ms` must be non-negative
- `selector_expression` must be non-empty when provided
- `error_message` required when `success` is false

### TelemetryEvent Validation
- `session_id` must reference valid browser session
- `operation_count` must match actual operations in session
- All rate fields must be between 0.0 and 1.0
- Duration fields must be non-negative

### ElementInteraction Validation
- `interaction_id` must be unique within session
- `operation_id` must reference valid SelectorOperation
- `interaction_type` must be one of: click, type, scroll, hover
- `interaction_duration_ms` must be non-negative

## State Transitions

### SelectorOperation Lifecycle
1. **Created**: Operation initialized with strategies
2. **Executing**: Strategies being attempted sequentially
3. **Completed**: Either successful strategy found or all failed
4. **Logged**: Telemetry data captured and stored

### StrategyResult Lifecycle
1. **Attempted**: Strategy execution started
2. **Evaluated**: Result assessed for confidence and success
3. **Selected**: Chosen as successful strategy or marked as failed

## JSON Schema Extensions

The existing snapshot schema will be extended to include selector operation data:

```json
{
  "snapshot_version": "1.3",
  "selector_operations": [
    {
      "operation_id": "search_input_location",
      "element_purpose": "Wikipedia search input field",
      "strategies_used": [...],
      "successful_strategy": {...},
      "total_duration_ms": 45,
      "confidence_threshold": 0.7,
      "timestamp": "2025-01-29T14:30:00Z"
    }
  ],
  "element_interactions": [...],
  "telemetry_summary": {...}
}
```

## Data Storage

### File Locations
- **Selector operations**: Stored within snapshot JSON files
- **Telemetry events**: Separate JSON files in `data/telemetry/`
- **Session logs**: Structured logs in `data/logs/`

### Retention Policy
- Selector operation data: Retained with snapshots (configurable)
- Telemetry events: 30 days default retention
- Session logs: 7 days default retention

## Performance Considerations

### Data Volume Estimates
- SelectorOperation: ~500 bytes per operation
- StrategyResult: ~200 bytes per strategy
- TelemetryEvent: ~1KB per session
- ElementInteraction: ~300 bytes per interaction

### Indexing Strategy
- Primary index: `operation_id`, `session_id`
- Secondary index: `timestamp`, `strategy_type`
- Telemetry queries: Grouped by session and time windows
