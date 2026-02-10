# API Contracts: Selector Engine Integration

**Date**: 2025-01-29  
**Feature**: 012-selector-engine-integration  
**Purpose**: API specifications for selector engine integration

## Selector Engine Integration API

### Main Integration Interface

```python
class SelectorEngineIntegration:
    """Integration layer for selector engine in browser lifecycle example"""
    
    async def locate_element(
        self,
        page: Page,
        element_purpose: str,
        selector_config: SelectorConfiguration,
        timeout_ms: int = 5000
    ) -> Optional[ElementHandle]:
        """
        Locate an element using multi-strategy selector engine
        
        Args:
            page: Playwright page instance
            element_purpose: Human-readable description of target element
            selector_config: Multi-strategy selector configuration
            timeout_ms: Maximum time to spend on all strategies
            
        Returns:
            Element handle if found, None if all strategies fail
        """
        
    async def interact_with_element(
        self,
        page: Page,
        element: ElementHandle,
        interaction_type: str,
        interaction_data: Optional[Dict] = None
    ) -> InteractionResult:
        """
        Perform interaction with located element
        
        Args:
            page: Playwright page instance
            element: Located element handle
            interaction_type: Type of interaction (click, type, scroll, hover)
            interaction_data: Additional data for interaction (text to type, etc.)
            
        Returns:
            Result of the interaction with success status and timing
        """
        
    def get_telemetry_summary(self) -> TelemetrySummary:
        """Get summary of selector operations and performance metrics"""
```

### Selector Configuration Schema

```json
{
  "element_purpose": "Wikipedia search input field",
  "strategies": [
    {
      "type": "css",
      "selector": "input#searchInput",
      "priority": 1,
      "expected_attributes": {
        "type": "search",
        "name": "search",
        "placeholder": "Search Wikipedia"
      }
    },
    {
      "type": "xpath",
      "selector": "//input[@name='search']",
      "priority": 2,
      "expected_attributes": {
        "type": "search"
      }
    },
    {
      "type": "text",
      "selector": "Search",
      "priority": 3,
      "search_context": "input",
      "expected_attributes": {
        "type": "search"
      }
    }
  ],
  "confidence_threshold": 0.7,
  "timeout_per_strategy_ms": 1500,
  "enable_fallback": true
}
```

### Element Interaction Schema

```json
{
  "interaction_id": "search_input_type",
  "operation_id": "search_input_location",
  "interaction_type": "type",
  "element_description": "Wikipedia search input field",
  "interaction_data": {
    "text": "Python programming",
    "delay_ms": 100
  },
  "stealth_settings": {
    "human_typing": true,
    "random_delay": true,
    "mouse_movement": true
  }
}
```

### Telemetry Data Schema

```json
{
  "telemetry_version": "1.0",
  "session_id": "browser_session_123",
  "generated_at": "2025-01-29T14:30:00Z",
  "summary": {
    "total_operations": 5,
    "successful_operations": 4,
    "success_rate": 0.8,
    "total_duration_ms": 1250,
    "average_confidence_score": 0.85,
    "fallback_usage_rate": 0.4
  },
  "operations": [
    {
      "operation_id": "search_input_location",
      "element_purpose": "Wikipedia search input field",
      "strategies_attempted": 2,
      "successful_strategy": "css",
      "confidence_score": 0.92,
      "duration_ms": 45,
      "timestamp": "2025-01-29T14:30:00Z"
    }
  ],
  "strategy_performance": {
    "css": {
      "attempts": 3,
      "successes": 2,
      "average_confidence": 0.88,
      "average_duration_ms": 35
    },
    "xpath": {
      "attempts": 2,
      "successes": 1,
      "average_confidence": 0.75,
      "average_duration_ms": 65
    },
    "text": {
      "attempts": 1,
      "successes": 1,
      "average_confidence": 0.68,
      "average_duration_ms": 120
    }
  }
}
```

## Error Handling Contracts

### Error Types

```python
class SelectorEngineError(Exception):
    """Base exception for selector engine operations"""
    
class StrategyTimeoutError(SelectorEngineError):
    """Raised when all strategies timeout"""
    
class ElementNotFoundError(SelectorEngineError):
    """Raised when no strategies locate an element"""
    
class InteractionError(SelectorEngineError):
    """Raised when element interaction fails"""
```

### Error Response Schema

```json
{
  "error_type": "ElementNotFoundError",
  "error_message": "All selector strategies failed to locate element",
  "operation_id": "search_input_location",
  "element_purpose": "Wikipedia search input field",
  "strategies_attempted": [
    {
      "type": "css",
      "selector": "input#searchInput",
      "error": "Element not found",
      "duration_ms": 1500
    },
    {
      "type": "xpath", 
      "selector": "//input[@name='search']",
      "error": "Element not found",
      "duration_ms": 1500
    }
  ],
  "total_duration_ms": 3000,
  "timestamp": "2025-01-29T14:30:00Z"
}
```

## Logging Contracts

### Log Message Schema

```json
{
  "timestamp": "2025-01-29T14:30:00Z",
  "level": "INFO",
  "session_id": "browser_session_123",
  "operation_id": "search_input_location",
  "message": "Selector operation completed successfully",
  "context": {
    "element_purpose": "Wikipedia search input field",
    "strategy_used": "css",
    "confidence_score": 0.92,
    "duration_ms": 45
  }
}
```

### Log Levels and Messages

- **INFO**: Successful selector operations and interactions
- **WARN**: Fallback strategy usage, low confidence scores
- **ERROR**: Failed selector operations, interaction failures
- **DEBUG**: Detailed strategy attempts, timing information

## Integration Points

### Browser Lifecycle Example Integration

```python
# Enhanced browser_lifecycle_example.py structure
class BrowserLifecycleExample:
    def __init__(self):
        self.selector_integration = SelectorEngineIntegration()
        
    async def perform_wikipedia_search(self, page: Page, search_term: str):
        # Locate search input using selector engine
        search_input = await self.selector_integration.locate_element(
            page=page,
            element_purpose="Wikipedia search input field",
            selector_config=self.get_search_input_config()
        )
        
        if search_input:
            # Type search term with stealth behavior
            await self.selector_integration.interact_with_element(
                page=page,
                element=search_input,
                interaction_type="type",
                interaction_data={"text": search_term}
            )
```

### Snapshot Integration

```json
{
  "snapshot_version": "1.3",
  "selector_operations": [...],
  "element_interactions": [...],
  "telemetry_summary": {...},
  "existing_snapshot_fields": {...}
}
```

## Performance Contracts

### Timing Requirements

- **Single strategy timeout**: 1500ms maximum
- **Total operation timeout**: 5000ms maximum
- **Interaction timeout**: 2000ms maximum
- **Telemetry capture overhead**: <10ms per operation

### Quality Requirements

- **Minimum confidence threshold**: 0.7 for production use
- **Success rate requirement**: >80% for stable elements
- **Fallback usage target**: <30% for optimal performance

## Versioning and Compatibility

### Schema Versioning

- Current version: 1.0
- Backward compatibility: Maintained for 1.x versions
- Breaking changes: Increment major version

### API Stability

- Core interfaces: Stable within major version
- Configuration schema: Backward compatible
- Telemetry format: Extensible but backward compatible
