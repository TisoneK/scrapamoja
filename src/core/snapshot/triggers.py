"""
Event-driven triggers system for automatic snapshot capture.

This module implements various trigger types that automatically capture snapshots
based on specific events like selector failures, retry exhaustion, and timeouts.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field

from src.observability.logger import get_logger

from .models import (
    SnapshotContext, SnapshotConfig, SnapshotMode, RateLimiter,
    SnapshotError
)

logger = get_logger(__name__)


class SnapshotTrigger(ABC):
    """Abstract base class for snapshot triggers."""
    
    def __init__(self, enabled: bool = True, rate_limit_per_minute: int = 5):
        """Initialize trigger."""
        self.enabled = enabled
        self.rate_limiter = RateLimiter(max_requests_per_minute=rate_limit_per_minute)
    
    @abstractmethod
    async def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Determine if snapshot should be triggered."""
        pass
    
    @abstractmethod
    async def get_snapshot_context(self, context: Dict[str, Any]) -> SnapshotContext:
        """Extract snapshot context from trigger context."""
        pass
    
    @abstractmethod
    async def get_snapshot_config(self, context: Dict[str, Any]) -> SnapshotConfig:
        """Get snapshot configuration for this trigger."""
        pass
    
    def get_trigger_type(self) -> str:
        """Get trigger type identifier."""
        return self.__class__.__name__.lower().replace("trigger", "")


class SelectorFailureTrigger(SnapshotTrigger):
    """Trigger for selector failure events."""
    
    def __init__(self, enabled: bool = True, rate_limit_per_minute: int = 5):
        """Initialize selector failure trigger."""
        super().__init__(enabled, rate_limit_per_minute)
        self.default_selector = None
    
    async def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if selector failure should trigger snapshot."""
        return (
            context.get("matched_count", 0) == 0 and
            context.get("selector") and
            self.enabled and
            self.rate_limiter.should_allow(self.get_trigger_type())
        )
    
    async def get_snapshot_context(self, context: Dict[str, Any]) -> SnapshotContext:
        """Create snapshot context from selector failure."""
        return SnapshotContext(
            site=context.get("site", "unknown"),
            module=context.get("module", "selector_execution"),
            component=context.get("component", "element_selection"),
            session_id=context.get("session_id", "unknown"),
            function=context.get("function", "selector_execution"),
            additional_metadata={
                "trigger_type": "selector_failure",
                "selector": context.get("selector"),
                "matched_count": context.get("matched_count", 0),
                "page_url": context.get("page_url"),
                "error_message": context.get("error_message")
            }
        )
    
    async def get_snapshot_config(self, context: Dict[str, Any]) -> SnapshotConfig:
        """Get snapshot config for selector failure."""
        selector = context.get("selector")
        # Use FULL_PAGE mode if no selector is provided
        mode = SnapshotMode.FULL_PAGE if not selector else SnapshotMode.SELECTOR
        
        return SnapshotConfig(
            mode=mode,
            capture_html=True,
            capture_screenshot=True,
            capture_console=True,
            capture_network=False,
            selector=selector,
            deduplication_enabled=True,
            async_save=True
        )


class RetryExhaustionTrigger(SnapshotTrigger):
    """Trigger for retry exhaustion events."""
    
    def __init__(self, enabled: bool = True, rate_limit_per_minute: int = 3):
        """Initialize retry exhaustion trigger."""
        super().__init__(enabled, rate_limit_per_minute)
    
    async def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if retry exhaustion should trigger snapshot."""
        return (
            context.get("retry_count", 0) >= context.get("max_retries", 3) and
            self.enabled and
            self.rate_limiter.should_allow(self.get_trigger_type())
        )
    
    async def get_snapshot_context(self, context: Dict[str, Any]) -> SnapshotContext:
        """Create snapshot context from retry exhaustion."""
        return SnapshotContext(
            site=context.get("site", "unknown"),
            module=context.get("module", "retry_logic"),
            component=context.get("component", "operation_retry"),
            session_id=context.get("session_id", "unknown"),
            function=context.get("function", "retry_operation"),
            additional_metadata={
                "trigger_type": "retry_exhaustion",
                "retry_count": context.get("retry_count", 0),
                "max_retries": context.get("max_retries", 3),
                "operation": context.get("operation"),
                "last_error": context.get("last_error"),
                "page_url": context.get("page_url")
            }
        )
    
    async def get_snapshot_config(self, context: Dict[str, Any]) -> SnapshotConfig:
        """Get snapshot config for retry exhaustion."""
        return SnapshotConfig(
            mode=SnapshotMode.FULL_PAGE,
            capture_html=True,
            capture_screenshot=True,
            capture_console=True,
            capture_network=True,
            deduplication_enabled=True,
            async_save=True
        )


class TimeoutTrigger(SnapshotTrigger):
    """Trigger for timeout events."""
    
    def __init__(self, enabled: bool = True, rate_limit_per_minute: int = 3):
        """Initialize timeout trigger."""
        super().__init__(enabled, rate_limit_per_minute)
    
    async def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if timeout should trigger snapshot."""
        return (
            context.get("timed_out", False) and
            self.enabled and
            self.rate_limiter.should_allow(self.get_trigger_type())
        )
    
    async def get_snapshot_context(self, context: Dict[str, Any]) -> SnapshotContext:
        """Create snapshot context from timeout."""
        return SnapshotContext(
            site=context.get("site", "unknown"),
            module=context.get("module", "timeout_handling"),
            component=context.get("component", "operation_timeout"),
            session_id=context.get("session_id", "unknown"),
            function=context.get("function", "timeout_operation"),
            additional_metadata={
                "trigger_type": "timeout",
                "timeout_duration": context.get("timeout_duration"),
                "operation": context.get("operation"),
                "page_url": context.get("page_url"),
                "partial_results": context.get("partial_results")
            }
        )
    
    async def get_snapshot_config(self, context: Dict[str, Any]) -> SnapshotConfig:
        """Get snapshot config for timeout."""
        return SnapshotConfig(
            mode=SnapshotMode.BOTH,
            capture_html=True,
            capture_screenshot=True,
            capture_console=True,
            capture_network=True,
            selector=context.get("selector"),
            deduplication_enabled=True,
            async_save=True
        )


class ExtractionMismatchTrigger(SnapshotTrigger):
    """Trigger for extraction validation failures."""
    
    def __init__(self, enabled: bool = True, rate_limit_per_minute: int = 5):
        """Initialize extraction mismatch trigger."""
        super().__init__(enabled, rate_limit_per_minute)
    
    async def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if extraction mismatch should trigger snapshot."""
        return (
            not context.get("validation_passed", True) and
            context.get("extracted_data") and
            self.enabled and
            self.rate_limiter.should_allow(self.get_trigger_type())
        )
    
    async def get_snapshot_context(self, context: Dict[str, Any]) -> SnapshotContext:
        """Create snapshot context from extraction mismatch."""
        return SnapshotContext(
            site=context.get("site", "unknown"),
            module=context.get("module", "data_extraction"),
            component=context.get("component", "validation"),
            session_id=context.get("session_id", "unknown"),
            function=context.get("function", "extract_and_validate"),
            additional_metadata={
                "trigger_type": "extraction_mismatch",
                "validation_errors": context.get("validation_errors", []),
                "extracted_data": context.get("extracted_data"),
                "expected_schema": context.get("expected_schema"),
                "selector": context.get("selector"),
                "page_url": context.get("page_url")
            }
        )
    
    async def get_snapshot_config(self, context: Dict[str, Any]) -> SnapshotConfig:
        """Get snapshot config for extraction mismatch."""
        return SnapshotConfig(
            mode=SnapshotMode.SELECTOR,
            capture_html=True,
            capture_screenshot=True,
            capture_console=False,
            capture_network=False,
            selector=context.get("selector"),
            deduplication_enabled=True,
            async_save=True
        )


@dataclass
class TriggerManager:
    """Manages multiple snapshot triggers."""
    triggers: List[SnapshotTrigger] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize default triggers."""
        if not self.triggers:
            self.triggers = [
                SelectorFailureTrigger(),
                RetryExhaustionTrigger(),
                TimeoutTrigger(),
                ExtractionMismatchTrigger()
            ]
    
    def add_trigger(self, trigger: SnapshotTrigger) -> None:
        """Add a trigger to the manager."""
        self.triggers.append(trigger)
    
    def remove_trigger(self, trigger_type: str) -> bool:
        """Remove trigger by type."""
        for i, trigger in enumerate(self.triggers):
            if trigger.get_trigger_type() == trigger_type:
                del self.triggers[i]
                return True
        return False
    
    def get_trigger(self, trigger_type: str) -> Optional[SnapshotTrigger]:
        """Get trigger by type."""
        for trigger in self.triggers:
            if trigger.get_trigger_type() == trigger_type:
                return trigger
        return None
    
    async def evaluate_triggers(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all triggers and return activated ones."""
        activated_triggers = []
        
        for trigger in self.triggers:
            try:
                if await trigger.should_trigger(context):
                    snapshot_context = await trigger.get_snapshot_context(context)
                    snapshot_config = await trigger.get_snapshot_config(context)
                    
                    activated_triggers.append({
                        "trigger": trigger,
                        "trigger_type": trigger.get_trigger_type(),
                        "snapshot_context": snapshot_context,
                        "snapshot_config": snapshot_config
                    })
            except Exception as e:
                # Log error but continue with other triggers
                logger.error("Error evaluating trigger", trigger_type=trigger.get_trigger_type(), error=str(e))
                continue
        
        return activated_triggers
    
    def get_trigger_statistics(self) -> Dict[str, Any]:
        """Get statistics for all triggers."""
        stats = {}
        
        for trigger in self.triggers:
            trigger_type = trigger.get_trigger_type()
            stats[trigger_type] = {
                "enabled": trigger.enabled,
                "rate_limit_per_minute": trigger.rate_limiter.max_requests_per_minute,
                "current_requests": len(trigger.rate_limiter.request_timestamps.get(trigger_type, []))
            }
        
        return stats
    
    def enable_trigger(self, trigger_type: str) -> bool:
        """Enable a specific trigger."""
        trigger = self.get_trigger(trigger_type)
        if trigger:
            trigger.enabled = True
            return True
        return False
    
    def disable_trigger(self, trigger_type: str) -> bool:
        """Disable a specific trigger."""
        trigger = self.get_trigger(trigger_type)
        if trigger:
            trigger.enabled = False
            return True
        return False
    
    def set_rate_limit(self, trigger_type: str, rate_limit: int) -> bool:
        """Set rate limit for a specific trigger."""
        trigger = self.get_trigger(trigger_type)
        if trigger:
            trigger.rate_limiter.max_requests_per_minute = rate_limit
            return True
        return False


class ManualTrigger(SnapshotTrigger):
    """Manual trigger for user-initiated snapshots."""
    
    def __init__(self, enabled: bool = True):
        """Initialize manual trigger."""
        super().__init__(enabled, rate_limit_per_minute=100)  # High limit for manual
    
    async def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Manual trigger always activates if enabled."""
        return (
            context.get("manual_trigger", False) and
            self.enabled and
            self.rate_limiter.should_allow(self.get_trigger_type())
        )
    
    async def get_snapshot_context(self, context: Dict[str, Any]) -> SnapshotContext:
        """Create snapshot context from manual trigger."""
        return SnapshotContext(
            site=context.get("site", "manual"),
            module=context.get("module", "manual_capture"),
            component=context.get("component", "user_initiated"),
            session_id=context.get("session_id", "manual"),
            function=context.get("function", "manual_snapshot"),
            additional_metadata={
                "trigger_type": "manual",
                "user_reason": context.get("reason", "User initiated"),
                "page_url": context.get("page_url"),
                "manual_timestamp": datetime.now().isoformat()
            }
        )
    
    async def get_snapshot_config(self, context: Dict[str, Any]) -> SnapshotConfig:
        """Get snapshot config for manual trigger."""
        mode = context.get("mode", SnapshotMode.FULL_PAGE)
        if isinstance(mode, str):
            mode = SnapshotMode(mode)
        
        return SnapshotConfig(
            mode=mode,
            capture_html=context.get("capture_html", True),
            capture_screenshot=context.get("capture_screenshot", True),
            capture_console=context.get("capture_console", True),
            capture_network=context.get("capture_network", False),
            selector=context.get("selector"),
            deduplication_enabled=context.get("deduplication_enabled", True),
            async_save=context.get("async_save", True)
        )
