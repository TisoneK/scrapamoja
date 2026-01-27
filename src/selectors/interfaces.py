"""
Base interfaces for Selector Engine components.

Defines abstract interfaces for all major components as specified in the
API contracts, ensuring consistent implementation patterns.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.models.selector_models import (
    SemanticSelector, SelectorResult, StrategyPattern, ValidationResult,
    DOMSnapshot, ConfidenceMetrics, DriftAnalysis, PerformanceTrend,
    StrategyRecommendation, SnapshotType, TrendDirection
)
from src.selectors.context import DOMContext


# Core interfaces

class ISelectorEngine(ABC):
    """Main selector engine interface."""
    
    @abstractmethod
    async def resolve(self, selector_name: str, context: DOMContext) -> SelectorResult:
        """Resolve a semantic selector to DOM element."""
        pass
    
    @abstractmethod
    async def resolve_batch(self, selector_names: List[str], context: DOMContext) -> List[SelectorResult]:
        """Resolve multiple selectors in parallel."""
        pass
    
    @abstractmethod
    def get_selector(self, name: str) -> Optional[SemanticSelector]:
        """Get selector definition by name."""
        pass
    
    @abstractmethod
    def list_selectors(self, context: Optional[str] = None) -> List[str]:
        """List available selectors, optionally filtered by context."""
        pass
    
    @abstractmethod
    async def validate_selector(self, selector: SemanticSelector) -> List[str]:
        """Validate selector definition, return list of issues."""
        pass
    
    @abstractmethod
    def get_confidence_metrics(self, selector_name: str) -> ConfidenceMetrics:
        """Get performance metrics for selector."""
        pass


class IStrategyPattern(ABC):
    """Interface for selector resolution strategies."""
    
    @property
    @abstractmethod
    def type(self) -> str:
        """Strategy type identifier."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Strategy priority (lower = higher priority)."""
        pass
    
    @abstractmethod
    async def attempt_resolution(self, selector: SemanticSelector, context: DOMContext) -> SelectorResult:
        """Attempt to resolve selector using this strategy."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate strategy-specific configuration."""
        pass
    
    @abstractmethod
    def update_metrics(self, success: bool, resolution_time: float) -> None:
        """Update strategy performance metrics."""
        pass


class IConfidenceScorer(ABC):
    """Interface for confidence scoring algorithms."""
    
    @abstractmethod
    def calculate_confidence(self, result: SelectorResult, validations: List[ValidationResult]) -> float:
        """Calculate confidence score for selector result."""
        pass
    
    @abstractmethod
    def validate_content(self, element_info, rules: List[Any]) -> List[ValidationResult]:
        """Validate element content against rules."""
        pass
    
    @abstractmethod
    def get_threshold(self, context: str) -> float:
        """Get confidence threshold for context."""
        pass


class IDOMSnapshotManager(ABC):
    """Interface for DOM snapshot management."""
    
    @abstractmethod
    async def capture_snapshot(self, context: DOMContext, selector_name: str,
                              snapshot_type: SnapshotType, failure_reason: str) -> str:
        """Capture DOM snapshot and return snapshot ID."""
        pass
    
    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional[DOMSnapshot]:
        """Retrieve snapshot by ID."""
        pass
    
    @abstractmethod
    async def analyze_drift(self, selector_name: str, time_range: Tuple[datetime, datetime]) -> DriftAnalysis:
        """Analyze selector drift over time."""
        pass
    
    @abstractmethod
    async def cleanup_snapshots(self, older_than: datetime) -> int:
        """Clean up old snapshots, return count deleted."""
        pass


class IDriftDetector(ABC):
    """Interface for drift detection and analysis."""
    
    @abstractmethod
    async def analyze_drift(self, selector_name: str,
                           time_range: Tuple[datetime, datetime]) -> DriftAnalysis:
        """Analyze drift for selector over time range."""
        pass
    
    @abstractmethod
    def get_drift_score(self, metrics: ConfidenceMetrics) -> float:
        """Calculate drift score from performance metrics."""
        pass
    
    @abstractmethod
    def detect_anomalies(self, results: List[SelectorResult]) -> List[str]:
        """Detect anomalous patterns in selector results."""
        pass
    
    @abstractmethod
    def should_trigger_alert(self, drift_analysis: DriftAnalysis) -> bool:
        """Determine if drift analysis should trigger alert."""
        pass


class IStrategyEvolution(ABC):
    """Interface for strategy evolution logic."""
    
    @abstractmethod
    async def evaluate_strategies(self, selector_name: str) -> List[StrategyRecommendation]:
        """Evaluate strategies and return recommendations."""
        pass
    
    @abstractmethod
    async def apply_recommendations(self, selector_name: str,
                                   recommendations: List[StrategyRecommendation]) -> bool:
        """Apply evolution recommendations to selector."""
        pass
    
    @abstractmethod
    def should_promote(self, metrics: ConfidenceMetrics) -> bool:
        """Determine if strategy should be promoted."""
        pass
    
    @abstractmethod
    def should_demote(self, metrics: ConfidenceMetrics) -> bool:
        """Determine if strategy should be demoted."""
        pass
    
    @abstractmethod
    def should_blacklist(self, metrics: ConfidenceMetrics) -> bool:
        """Determine if strategy should be blacklisted."""
        pass


# Registry interfaces

class ISelectorRegistry(ABC):
    """Interface for selector registry management."""
    
    @abstractmethod
    def register_selector(self, selector: SemanticSelector) -> bool:
        """Register a new selector definition."""
        pass
    
    @abstractmethod
    def unregister_selector(self, name: str) -> bool:
        """Unregister selector definition."""
        pass
    
    @abstractmethod
    def get_selector(self, name: str) -> Optional[SemanticSelector]:
        """Get selector definition by name."""
        pass
    
    @abstractmethod
    def list_selectors(self, context: Optional[str] = None) -> List[SemanticSelector]:
        """List all selectors, optionally filtered by context."""
        pass
    
    @abstractmethod
    def update_selector(self, selector: SemanticSelector) -> bool:
        """Update existing selector definition."""
        pass
    
    @abstractmethod
    def validate_selector(self, selector: SemanticSelector) -> List[str]:
        """Validate selector definition."""
        pass


class IStrategyRegistry(ABC):
    """Interface for strategy pattern registry."""
    
    @abstractmethod
    def register_strategy(self, strategy: IStrategyPattern) -> bool:
        """Register a strategy pattern."""
        pass
    
    @abstractmethod
    def get_strategy(self, strategy_id: str) -> Optional[IStrategyPattern]:
        """Get strategy by ID."""
        pass
    
    @abstractmethod
    def list_strategies(self, strategy_type: Optional[str] = None) -> List[IStrategyPattern]:
        """List all strategies, optionally filtered by type."""
        pass
    
    @abstractmethod
    def get_strategies_by_type(self, strategy_type: str) -> List[IStrategyPattern]:
        """Get strategies of specific type."""
        pass


# Monitoring interfaces

class IPerformanceMonitor(ABC):
    """Interface for performance monitoring."""
    
    @abstractmethod
    async def record_resolution(self, result: SelectorResult) -> None:
        """Record selector resolution result."""
        pass
    
    @abstractmethod
    def get_metrics(self, selector_name: str,
                   time_range: Optional[Tuple[datetime, datetime]] = None) -> ConfidenceMetrics:
        """Get performance metrics for selector."""
        pass
    
    @abstractmethod
    def get_top_performers(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get top performing selectors by success rate."""
        pass
    
    @abstractmethod
    def get_underperformers(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get underperforming selectors by success rate."""
        pass
    
    @abstractmethod
    async def generate_report(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Generate performance report for time range."""
        pass


# Event interfaces

class IEventBus(ABC):
    """Interface for event bus."""
    
    @abstractmethod
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event to subscribers."""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler) -> str:
        """Subscribe to event type, return subscription ID."""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        pass


# Configuration interfaces

class IConfigManager(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def get_engine_config(self):
        """Get selector engine configuration."""
        pass
    
    @abstractmethod
    def get_snapshot_config(self):
        """Get snapshot configuration."""
        pass
    
    @abstractmethod
    def get_drift_config(self):
        """Get drift detection configuration."""
        pass
    
    @abstractmethod
    def update_config(self, section: str, config: Any) -> bool:
        """Update configuration section."""
        pass


# Storage interfaces

class IStorageAdapter(ABC):
    """Interface for storage operations."""
    
    @abstractmethod
    async def store_snapshot(self, snapshot: DOMSnapshot) -> str:
        """Store DOM snapshot."""
        pass
    
    @abstractmethod
    async def retrieve_snapshot(self, snapshot_id: str) -> Optional[DOMSnapshot]:
        """Retrieve DOM snapshot."""
        pass
    
    @abstractmethod
    async def store_metrics(self, metrics: ConfidenceMetrics) -> bool:
        """Store performance metrics."""
        pass
    
    @abstractmethod
    async def retrieve_metrics(self, selector_name: str,
                              time_range: Tuple[datetime, datetime]) -> List[ConfidenceMetrics]:
        """Retrieve performance metrics."""
        pass


# Validation interfaces

class IValidator(ABC):
    """Interface for content validation."""
    
    @abstractmethod
    def validate(self, content: str, rule: Any) -> ValidationResult:
        """Validate content against rule."""
        pass
    
    @abstractmethod
    def validate_batch(self, content: str, rules: List[Any]) -> List[ValidationResult]:
        """Validate content against multiple rules."""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Get supported validation types."""
        pass


# Testing interfaces

class ISelectorTestHarness(ABC):
    """Interface for selector testing."""
    
    @abstractmethod
    async def test_selector(self, selector_name: str, test_cases: List[Any]) -> Any:
        """Test selector against multiple test cases."""
        pass
    
    @abstractmethod
    async def test_strategy(self, strategy_id: str, test_cases: List[Any]) -> Any:
        """Test strategy against multiple test cases."""
        pass
    
    @abstractmethod
    def generate_test_cases(self, selector: SemanticSelector) -> List[Any]:
        """Generate test cases for selector."""
        pass


# External system interfaces

class IPlaywrightAdapter(ABC):
    """Interface for Playwright integration."""
    
    @abstractmethod
    async def query_selector(self, selector: str, context: DOMContext) -> Optional[Any]:
        """Query DOM element using CSS selector."""
        pass
    
    @abstractmethod
    async def get_page_content(self, context: DOMContext) -> str:
        """Get full page HTML content."""
        pass
    
    @abstractmethod
    async def wait_for_element(self, selector: str, timeout: float, context: DOMContext) -> bool:
        """Wait for element to appear."""
        pass


# Utility interfaces

class ICache(ABC):
    """Interface for caching."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """Get cache size."""
        pass


class IRetryPolicy(ABC):
    """Interface for retry policies."""
    
    @abstractmethod
    async def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if operation should be retried."""
        pass
    
    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Get delay before next retry attempt."""
        pass
    
    @abstractmethod
    def get_max_attempts(self) -> int:
        """Get maximum retry attempts."""
        pass


# Event type constants
class EventTypes:
    """Event type constants for the event bus."""
    SELECTOR_RESOLVED = "selector.resolved"
    SELECTOR_FAILED = "selector.failed"
    STRATEGY_PROMOTED = "strategy.promoted"
    STRATEGY_DEMOTED = "strategy.demoted"
    DRIFT_DETECTED = "drift.detected"
    SNAPSHOT_CAPTURED = "snapshot.captured"
    PERFORMANCE_ALERT = "performance.alert"
    CONFIGURATION_CHANGED = "config.changed"
    ERROR_OCCURRED = "error.occurred"


# Abstract base classes for convenience

class BaseStrategyPattern(IStrategyPattern):
    """Base implementation for strategy patterns."""
    
    def __init__(self, strategy_id: str, strategy_type: str, priority: int = 1):
        self._strategy_id = strategy_id
        self._strategy_type = strategy_type
        self._priority = priority
        self._success_count = 0
        self._total_attempts = 0
        self._total_time = 0.0
    
    @property
    def id(self) -> str:
        return self._strategy_id
    
    @property
    def type(self) -> str:
        return self._strategy_type
    
    @property
    def priority(self) -> int:
        return self._priority
    
    def update_metrics(self, success: bool, resolution_time: float) -> None:
        """Update performance metrics."""
        self._total_attempts += 1
        self._total_time += resolution_time
        if success:
            self._success_count += 1
    
    def get_success_rate(self) -> float:
        """Get success rate."""
        if self._total_attempts == 0:
            return 0.0
        return self._success_count / self._total_attempts
    
    def get_avg_resolution_time(self) -> float:
        """Get average resolution time."""
        if self._total_attempts == 0:
            return 0.0
        return self._total_time / self._total_attempts


class BaseValidator(IValidator):
    """Base implementation for validators."""
    
    def __init__(self, validator_type: str):
        self._validator_type = validator_type
    
    def get_supported_types(self) -> List[str]:
        """Get supported validation types."""
        return [self._validator_type]
    
    def validate_batch(self, content: str, rules: List[Any]) -> List[ValidationResult]:
        """Validate content against multiple rules."""
        results = []
        for rule in rules:
            result = self.validate(content, rule)
            results.append(result)
        return results


class BaseRetryPolicy(IRetryPolicy):
    """Base implementation for retry policies."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        self._max_attempts = max_attempts
        self._base_delay = base_delay
    
    def get_max_attempts(self) -> int:
        """Get maximum retry attempts."""
        return self._max_attempts
    
    def get_delay(self, attempt: int) -> float:
        """Get delay before next retry attempt."""
        return self._base_delay * (2 ** (attempt - 1))  # Exponential backoff
