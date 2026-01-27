# Selector Engine API Contracts

**Date**: 2025-01-27  
**Purpose**: Define interfaces and contracts for Selector Engine components  
**Status**: Complete

## Core API Contracts

### 1. SelectorEngine Interface

Main entry point for selector resolution and management.

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DOMContext:
    """Context information for DOM resolution"""
    page: Any  # Playwright Page object
    tab_context: str
    url: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class SelectorResult:
    """Result of selector resolution attempt"""
    selector_name: str
    strategy_used: str
    element_info: Optional['ElementInfo']
    confidence_score: float
    resolution_time: float
    validation_results: List['ValidationResult']
    success: bool
    timestamp: datetime
    failure_reason: Optional[str] = None

class ISelectorEngine(ABC):
    """Main selector engine interface"""
    
    @abstractmethod
    async def resolve(self, selector_name: str, context: DOMContext) -> SelectorResult:
        """Resolve a semantic selector to DOM element"""
        pass
    
    @abstractmethod
    async def resolve_batch(self, selector_names: List[str], context: DOMContext) -> List[SelectorResult]:
        """Resolve multiple selectors in parallel"""
        pass
    
    @abstractmethod
    def get_selector(self, name: str) -> Optional['SemanticSelector']:
        """Get selector definition by name"""
        pass
    
    @abstractmethod
    def list_selectors(self, context: Optional[str] = None) -> List[str]:
        """List available selectors, optionally filtered by context"""
        pass
    
    @abstractmethod
    async def validate_selector(self, selector: 'SemanticSelector') -> List[str]:
        """Validate selector definition, return list of issues"""
        pass
    
    @abstractmethod
    def get_confidence_metrics(self, selector_name: str) -> 'ConfidenceMetrics':
        """Get performance metrics for selector"""
        pass
```

### 2. Strategy Pattern Interface

Base interface for all selector resolution strategies.

```python
from abc import ABC, abstractmethod
from enum import Enum

class StrategyType(Enum):
    TEXT_ANCHOR = "text_anchor"
    ATTRIBUTE_MATCH = "attribute_match"
    DOM_RELATIONSHIP = "dom_relationship"
    ROLE_BASED = "role_based"

@dataclass
class StrategyConfig:
    """Configuration for strategy execution"""
    timeout: float = 5000.0  # milliseconds
    retry_attempts: int = 3
    retry_delay: float = 100.0  # milliseconds

class IStrategyPattern(ABC):
    """Interface for selector resolution strategies"""
    
    @property
    @abstractmethod
    def type(self) -> StrategyType:
        """Strategy type identifier"""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Strategy priority (lower = higher priority)"""
        pass
    
    @abstractmethod
    async def attempt_resolution(self, selector: 'SemanticSelector', context: DOMContext) -> SelectorResult:
        """Attempt to resolve selector using this strategy"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate strategy-specific configuration"""
        pass
    
    @abstractmethod
    def update_metrics(self, success: bool, resolution_time: float) -> None:
        """Update strategy performance metrics"""
        pass
```

### 3. Confidence Scoring Interface

Interface for confidence calculation and validation.

```python
from abc import ABC, abstractmethod
from typing import List

@dataclass
class ValidationResult:
    """Result of content validation"""
    rule_type: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any]

class IConfidenceScorer(ABC):
    """Interface for confidence scoring algorithms"""
    
    @abstractmethod
    def calculate_confidence(self, result: SelectorResult, validations: List[ValidationResult]) -> float:
        """Calculate confidence score for selector result"""
        pass
    
    @abstractmethod
    def validate_content(self, element_info: 'ElementInfo', rules: List['ValidationRule']) -> List[ValidationResult]:
        """Validate element content against rules"""
        pass
    
    @abstractmethod
    def get_threshold(self, context: str) -> float:
        """Get confidence threshold for context"""
        pass
```

### 4. DOM Snapshot Interface

Interface for DOM snapshot capture and management.

```python
from abc import ABC, abstractmethod
from enum import Enum

class SnapshotType(Enum):
    FAILURE = "failure"
    DRIFT_ANALYSIS = "drift_analysis"
    MANUAL = "manual"

@dataclass
class SnapshotMetadata:
    """Metadata for DOM snapshots"""
    page_url: str
    tab_context: str
    viewport_size: tuple[int, int]
    user_agent: str
    resolution_attempt: int
    failure_reason: str
    performance_metrics: Dict[str, float]

class IDOMSnapshotManager(ABC):
    """Interface for DOM snapshot management"""
    
    @abstractmethod
    async def capture_snapshot(self, context: DOMContext, selector_name: str, 
                              snapshot_type: SnapshotType, failure_reason: str) -> str:
        """Capture DOM snapshot and return snapshot ID"""
        pass
    
    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional['DOMSnapshot']:
        """Retrieve snapshot by ID"""
        pass
    
    @abstractmethod
    async def analyze_drift(self, selector_name: str, time_range: tuple[datetime, datetime]) -> 'DriftAnalysis':
        """Analyze selector drift over time"""
        pass
    
    @abstractmethod
    async def cleanup_snapshots(self, older_than: datetime) -> int:
        """Clean up old snapshots, return count deleted"""
        pass
```

### 5. Drift Detection Interface

Interface for detecting and analyzing selector performance drift.

```python
from abc import ABC, abstractmethod
from enum import Enum

class TrendDirection(Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"

@dataclass
class PerformanceTrend:
    """Performance trend information"""
    strategy_id: str
    success_rate_trend: float
    confidence_trend: float
    performance_trend: float
    volatility: float

class IDriftDetector(ABC):
    """Interface for drift detection and analysis"""
    
    @abstractmethod
    async def analyze_drift(self, selector_name: str, 
                           time_range: tuple[datetime, datetime]) -> 'DriftAnalysis':
        """Analyze drift for selector over time range"""
        pass
    
    @abstractmethod
    def get_drift_score(self, metrics: 'ConfidenceMetrics') -> float:
        """Calculate drift score from performance metrics"""
        pass
    
    @abstractmethod
    def detect_anomalies(self, results: List[SelectorResult]) -> List[str]:
        """Detect anomalous patterns in selector results"""
        pass
    
    @abstractmethod
    def should_trigger_alert(self, drift_analysis: 'DriftAnalysis') -> bool:
        """Determine if drift analysis should trigger alert"""
        pass
```

### 6. Strategy Evolution Interface

Interface for automatic strategy promotion and demotion.

```python
from abc import ABC, abstractmethod

class IStrategyEvolution(ABC):
    """Interface for strategy evolution logic"""
    
    @abstractmethod
    async def evaluate_strategies(self, selector_name: str) -> List['StrategyRecommendation']:
        """Evaluate strategies and return recommendations"""
        pass
    
    @abstractmethod
    async def apply_recommendations(self, selector_name: str, 
                                   recommendations: List['StrategyRecommendation']) -> bool:
        """Apply evolution recommendations to selector"""
        pass
    
    @abstractmethod
    def should_promote(self, metrics: 'ConfidenceMetrics') -> bool:
        """Determine if strategy should be promoted"""
        pass
    
    @abstractmethod
    def should_demote(self, metrics: 'ConfidenceMetrics') -> bool:
        """Determine if strategy should be demoted"""
        pass
    
    @abstractmethod
    def should_blacklist(self, metrics: 'ConfidenceMetrics') -> bool:
        """Determine if strategy should be blacklisted"""
        pass

@dataclass
class StrategyRecommendation:
    """Recommendation for strategy changes"""
    strategy_id: str
    action: str  # "promote", "demote", "blacklist", "keep"
    reason: str
    confidence: float
    metrics: 'ConfidenceMetrics'
```

## Implementation Contracts

### 1. Registry Interface

Interface for selector definition management.

```python
class ISelectorRegistry(ABC):
    """Interface for selector registry management"""
    
    @abstractmethod
    def register_selector(self, selector: 'SemanticSelector') -> bool:
        """Register a new selector definition"""
        pass
    
    @abstractmethod
    def unregister_selector(self, name: str) -> bool:
        """Unregister selector definition"""
        pass
    
    @abstractmethod
    def get_selector(self, name: str) -> Optional['SemanticSelector']:
        """Get selector definition by name"""
        pass
    
    @abstractmethod
    def list_selectors(self, context: Optional[str] = None) -> List['SemanticSelector']:
        """List all selectors, optionally filtered by context"""
        pass
    
    @abstractmethod
    def update_selector(self, selector: 'SemanticSelector') -> bool:
        """Update existing selector definition"""
        pass
    
    @abstractmethod
    def validate_selector(self, selector: 'SemanticSelector') -> List[str]:
        """Validate selector definition"""
        pass
```

### 2. Performance Monitoring Interface

Interface for performance monitoring and metrics collection.

```python
class IPerformanceMonitor(ABC):
    """Interface for performance monitoring"""
    
    @abstractmethod
    async def record_resolution(self, result: SelectorResult) -> None:
        """Record selector resolution result"""
        pass
    
    @abstractmethod
    def get_metrics(self, selector_name: str, 
                   time_range: Optional[tuple[datetime, datetime]] = None) -> 'ConfidenceMetrics':
        """Get performance metrics for selector"""
        pass
    
    @abstractmethod
    def get_top_performers(self, limit: int = 10) -> List[tuple[str, float]]:
        """Get top performing selectors by success rate"""
        pass
    
    @abstractmethod
    def get_underperformers(self, limit: int = 10) -> List[tuple[str, float]]:
        """Get underperforming selectors by success rate"""
        pass
    
    @abstractmethod
    async def generate_report(self, time_range: tuple[datetime, datetime]) -> Dict[str, Any]:
        """Generate performance report for time range"""
        pass
```

## Event Contracts

### 1. Event System Interface

Interface for event-driven architecture components.

```python
from abc import ABC, abstractmethod
from typing import Callable, Any

class IEventBus(ABC):
    """Interface for event bus"""
    
    @abstractmethod
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event to subscribers"""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]) -> str:
        """Subscribe to event type, return subscription ID"""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        pass

# Event Types
class EventTypes:
    SELECTOR_RESOLVED = "selector.resolved"
    SELECTOR_FAILED = "selector.failed"
    STRATEGY_PROMOTED = "strategy.promoted"
    STRATEGY_DEMOTED = "strategy.demoted"
    DRIFT_DETECTED = "drift.detected"
    SNAPSHOT_CAPTURED = "snapshot.captured"
    PERFORMANCE_ALERT = "performance.alert"
```

## Configuration Contracts

### 1. Configuration Interface

Interface for configuration management.

```python
@dataclass
class SelectorEngineConfig:
    """Configuration for selector engine"""
    default_confidence_threshold: float = 0.8
    max_resolution_time: float = 1000.0  # milliseconds
    snapshot_on_failure: bool = True
    drift_detection_enabled: bool = True
    evolution_enabled: bool = True
    cache_enabled: bool = True
    cache_ttl: int = 30  # seconds
    parallel_resolution: bool = True
    max_concurrent_resolutions: int = 10

@dataclass
class SnapshotConfig:
    """Configuration for DOM snapshots"""
    compression_enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    retention_days: int = 30
    storage_path: str = "data/snapshots"

@dataclass
class DriftDetectionConfig:
    """Configuration for drift detection"""
    analysis_window_hours: int = 24
    drift_threshold: float = 0.7
    trend_sensitivity: float = 0.1
    min_sample_size: int = 30

class IConfigManager(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    def get_engine_config(self) -> SelectorEngineConfig:
        """Get selector engine configuration"""
        pass
    
    @abstractmethod
    def get_snapshot_config(self) -> SnapshotConfig:
        """Get snapshot configuration"""
        pass
    
    @abstractmethod
    def get_drift_config(self) -> DriftDetectionConfig:
        """Get drift detection configuration"""
        pass
    
    @abstractmethod
    def update_config(self, section: str, config: Any) -> bool:
        """Update configuration section"""
        pass
```

## Error Handling Contracts

### 1. Exception Hierarchy

```python
class SelectorEngineError(Exception):
    """Base exception for selector engine"""
    pass

class SelectorNotFoundError(SelectorEngineError):
    """Raised when selector is not found"""
    def __init__(self, selector_name: str):
        self.selector_name = selector_name
        super().__init__(f"Selector not found: {selector_name}")

class ResolutionTimeoutError(SelectorEngineError):
    """Raised when resolution times out"""
    def __init__(self, selector_name: str, timeout: float):
        self.selector_name = selector_name
        self.timeout = timeout
        super().__init__(f"Resolution timeout for {selector_name}: {timeout}ms")

class ConfidenceThresholdError(SelectorEngineError):
    """Raised when confidence threshold is not met"""
    def __init__(self, selector_name: str, confidence: float, threshold: float):
        self.selector_name = selector_name
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(f"Confidence {confidence} below threshold {threshold} for {selector_name}")

class ContextValidationError(SelectorEngineError):
    """Raised when tab context validation fails"""
    def __init__(self, context: str, reason: str):
        self.context = context
        self.reason = reason
        super().__init__(f"Context validation failed for {context}: {reason}")

class SnapshotError(SelectorEngineError):
    """Raised when snapshot operations fail"""
    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        super().__init__(f"Snapshot {operation} failed: {reason}")
```

## Testing Contracts

### 1. Test Interfaces

```python
class ISelectorTestHarness(ABC):
    """Interface for selector testing"""
    
    @abstractmethod
    async def test_selector(self, selector_name: str, test_cases: List['TestCase']) -> 'TestResult':
        """Test selector against multiple test cases"""
        pass
    
    @abstractmethod
    async def test_strategy(self, strategy_id: str, test_cases: List['TestCase']) -> 'TestResult':
        """Test strategy against multiple test cases"""
        pass
    
    @abstractmethod
    def generate_test_cases(self, selector: 'SemanticSelector') -> List['TestCase']:
        """Generate test cases for selector"""
        pass

@dataclass
class TestCase:
    """Test case for selector validation"""
    name: str
    dom_content: str
    expected_element: Optional[str]
    expected_confidence: float
    context: str

@dataclass
class TestResult:
    """Result of selector testing"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_confidence: float
    average_resolution_time: float
    failures: List[str]
```

## Integration Contracts

### 1. External System Integration

```python
class IPlaywrightAdapter(ABC):
    """Interface for Playwright integration"""
    
    @abstractmethod
    async def query_selector(self, selector: str, context: DOMContext) -> Optional['ElementInfo']:
        """Query DOM element using CSS selector"""
        pass
    
    @abstractmethod
    async def get_page_content(self, context: DOMContext) -> str:
        """Get full page HTML content"""
        pass
    
    @abstractmethod
    async def wait_for_element(self, selector: str, timeout: float, context: DOMContext) -> bool:
        """Wait for element to appear"""
        pass

class IStorageAdapter(ABC):
    """Interface for storage operations"""
    
    @abstractmethod
    async def store_snapshot(self, snapshot: 'DOMSnapshot') -> str:
        """Store DOM snapshot"""
        pass
    
    @abstractmethod
    async def retrieve_snapshot(self, snapshot_id: str) -> Optional['DOMSnapshot']:
        """Retrieve DOM snapshot"""
        pass
    
    @abstractmethod
    async def store_metrics(self, metrics: 'ConfidenceMetrics') -> bool:
        """Store performance metrics"""
        pass
    
    @abstractmethod
    async def retrieve_metrics(self, selector_name: str, 
                              time_range: tuple[datetime, datetime]) -> List['ConfidenceMetrics']:
        """Retrieve performance metrics"""
        pass
```

These contracts provide a comprehensive interface definition for the Selector Engine system, ensuring clear boundaries between components and enabling independent testing and development of each module.
