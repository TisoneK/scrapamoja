"""
Retry Logic Integration - Hooks snapshot system into retry mechanisms.

This module integrates the snapshot system with retry logic
to automatically capture snapshots when retries are exhausted.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from ..manager import SnapshotManager
from ..models import SnapshotContext, SnapshotConfig, SnapshotMode
from ..config import get_settings


@dataclass
class RetryEvent:
    """Retry event data for snapshot triggering."""
    operation: str
    retry_count: int
    max_retries: int
    last_error: str
    session_id: str = "unknown"
    site: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RetrySnapshot:
    """Integrates snapshot system with retry logic."""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        """Initialize retry logic integration."""
        self.snapshot_manager = snapshot_manager
        self.settings = get_settings()
        self._retry_manager = None
        self._initialized = False
        
        # Event callbacks
        self.on_retry_started: List[Callable] = []
        self.on_retry_attempt: List[Callable] = []
        self.on_retry_exhausted: List[Callable] = []
        self.on_retry_succeeded: List[Callable] = []
        
        # Statistics
        self.integration_stats = {
            "retry_operations": 0,
            "retry_attempts": 0,
            "retry_exhaustions": 0,
            "snapshots_captured": 0,
            "retry_successes": 0
        }
        
        # Retry tracking
        self.active_retries: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize retry snapshot handler."""
        try:
            # Import retry manager to avoid circular imports
            from src.resilience.retry.retry_manager import RetryManager
            
            # Get global retry manager instance
            self._retry_manager = RetryManager()
            
            # Hook into retry manager events
            await self._hook_retry_events()
            
            self._initialized = True
            print("✅ Retry logic integration initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize retry logic integration: {e}")
            raise
    
    async def _hook_retry_events(self):
        """Hook into retry manager events."""
        if not self._retry_manager:
            return
        
        # Hook into retry lifecycle
        if hasattr(self._retry_manager, 'on_retry_started'):
            self._retry_manager.on_retry_started.append(self._on_retry_started)
        
        if hasattr(self._retry_manager, 'on_retry_attempt'):
            self._retry_manager.on_retry_attempt.append(self._on_retry_attempt)
        
        if hasattr(self._retry_manager, 'on_retry_exhausted'):
            self._retry_manager.on_retry_exhausted.append(self._on_retry_exhausted)
        
        if hasattr(self._retry_manager, 'on_retry_succeeded'):
            self._retry_manager.on_retry_succeeded.append(self._on_retry_succeeded)
    
    async def _on_retry_started(self, operation_id: str, retry_info: Dict[str, Any]):
        """Handle retry started event."""
        try:
            self.integration_stats["retry_operations"] += 1
            
            # Track active retry
            self.active_retries[operation_id] = {
                "started_at": datetime.now(),
                "operation": retry_info.get("operation"),
                "max_retries": retry_info.get("max_retries", 3),
                "attempts": 0
            }
            
            # Notify callbacks
            for callback in self.on_retry_started:
                await callback(operation_id, retry_info)
                
        except Exception as e:
            print(f"❌ Error handling retry started: {e}")
    
    async def _on_retry_attempt(self, operation_id: str, attempt_info: Dict[str, Any]):
        """Handle retry attempt event."""
        try:
            self.integration_stats["retry_attempts"] += 1
            
            # Update active retry
            if operation_id in self.active_retries:
                self.active_retries[operation_id]["attempts"] += 1
                self.active_retries[operation_id]["last_attempt"] = attempt_info
            
            # Notify callbacks
            for callback in self.on_retry_attempt:
                await callback(operation_id, attempt_info)
                
        except Exception as e:
            print(f"❌ Error handling retry attempt: {e}")
    
    async def _on_retry_exhausted(self, operation_id: str, exhaustion_info: Dict[str, Any]):
        """Handle retry exhausted event with snapshot capture."""
        try:
            self.integration_stats["retry_exhaustions"] += 1
            
            # Clean up active retry
            if operation_id in self.active_retries:
                del self.active_retries[operation_id]
            
            # Capture snapshot on retry exhaustion
            if self.settings.enable_metrics:
                retry_data = self.active_retries.get(operation_id, {})
                context_data = {
                    "site": exhaustion_info.get("site", "unknown"),
                    "module": "retry_logic",
                    "component": "exhaustion_handler",
                    "session_id": exhaustion_info.get("session_id", "unknown"),
                    "function": exhaustion_info.get("operation", "retry_exhausted"),
                    "operation": exhaustion_info.get("operation"),
                    "retry_count": retry_data.get("attempts", 0),
                    "max_retries": exhaustion_info.get("max_retries", 3),
                    "last_error": exhaustion_info.get("last_error"),
                    "total_duration_ms": exhaustion_info.get("total_duration_ms"),
                    "exhaustion_reason": "max_retries_reached"
                }
                
                snapshot_id = await self._capture_retry_snapshot(
                    trigger_source="retry_exhausted",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_retry_exhausted:
                await callback(operation_id, exhaustion_info)
                
        except Exception as e:
            print(f"❌ Error handling retry exhausted: {e}")
    
    async def _on_retry_succeeded(self, operation_id: str, success_info: Dict[str, Any]):
        """Handle retry succeeded event."""
        try:
            self.integration_stats["retry_successes"] += 1
            
            # Clean up active retry
            if operation_id in self.active_retries:
                del self.active_retries[operation_id]
            
            # Notify callbacks
            for callback in self.on_retry_succeeded:
                await callback(operation_id, success_info)
                
        except Exception as e:
            print(f"❌ Error handling retry succeeded: {e}")
    
    async def _capture_retry_snapshot(self, 
                                 trigger_source: str,
                                 context_data: Dict[str, Any]) -> Optional[str]:
        """Capture retry-specific snapshot."""
        try:
            # Get active page
            page = await self._get_active_page()
            if not page:
                return None
            
            # Build snapshot context
            context = SnapshotContext(
                site=context_data.get("site", "unknown"),
                module=context_data.get("module", "retry"),
                component=context_data.get("component", "logic"),
                session_id=context_data.get("session_id", "unknown"),
                function=context_data.get("function"),
                additional_metadata={
                    "trigger_source": trigger_source,
                    "retry_integration": True,
                    "timestamp": datetime.now().isoformat(),
                    **context_data
                }
            )
            
            # Build snapshot config
            config = SnapshotConfig(
                mode=SnapshotMode.FULL_PAGE,
                capture_html=True,
                capture_screenshot=True,
                capture_console=True,
                capture_network=True,
                async_save=self.settings.enable_async_save,
                deduplication_enabled=self.settings.enable_deduplication
            )
            
            # Capture snapshot
            bundle = await self.snapshot_manager.capture_snapshot(page, context, config)
            
            if bundle:
                snapshot_id = bundle.content_hash[:8]
                print(f"📸 Retry snapshot captured: {snapshot_id} from {trigger_source}")
                return snapshot_id
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to capture retry snapshot: {e}")
            return None
    
    async def _get_active_page(self) -> Optional[Any]:
        """Get the currently active page."""
        try:
            # Try to get page from retry manager
            if self._retry_manager and hasattr(self._retry_manager, 'get_active_page'):
                return await self._retry_manager.get_active_page()
            
            # Try to get page from browser manager
            from src.browser.manager import BrowserManager
            browser_manager = BrowserManager()
            if hasattr(browser_manager, 'get_active_page'):
                return await browser_manager.get_active_page()
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting active page: {e}")
            return None
    
    def get_active_retries(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active retries."""
        return self.active_retries.copy()
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry performance statistics."""
        stats = {
            "total_operations": self.integration_stats["retry_operations"],
            "total_attempts": self.integration_stats["retry_attempts"],
            "exhaustions": self.integration_stats["retry_exhaustions"],
            "successes": self.integration_stats["retry_successes"],
            "active_retries": len(self.active_retries)
        }
        
        if self.integration_stats["retry_operations"] > 0:
            stats["average_attempts_per_operation"] = (
                self.integration_stats["retry_attempts"] / self.integration_stats["retry_operations"]
            )
            stats["exhaustion_rate"] = (
                self.integration_stats["retry_exhaustions"] / self.integration_stats["retry_operations"] * 100
            )
            stats["success_rate"] = (
                self.integration_stats["retry_successes"] / self.integration_stats["retry_operations"] * 100
            )
        
        return stats
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of retry integration."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "retry_manager_available": self._retry_manager is not None,
            "statistics": self.integration_stats,
            "active_retries": len(self.active_retries),
            "retry_stats": self.get_retry_statistics(),
            "event_callbacks": {
                "retry_started": len(self.on_retry_started) > 0,
                "retry_attempt": len(self.on_retry_attempt) > 0,
                "retry_exhausted": len(self.on_retry_exhausted) > 0,
                "retry_succeeded": len(self.on_retry_succeeded) > 0
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "integration_type": "retry_logic",
            "initialized": self._initialized,
            "statistics": self.integration_stats,
            "retry_performance": self.get_retry_statistics(),
            "active_retries": self.active_retries,
            "event_callbacks": {
                "retry_started": len(self.on_retry_started),
                "retry_attempt": len(self.on_retry_attempt),
                "retry_exhausted": len(self.on_retry_exhausted),
                "retry_succeeded": len(self.on_retry_succeeded)
            }
        }
