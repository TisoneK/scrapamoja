"""
Selector Engine Integration - Hooks snapshot system into selector operations.

This module integrates the snapshot system with the selector engine
to automatically capture snapshots when selectors fail or perform poorly.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from ..manager import SnapshotManager
from ..models import SnapshotContext, SnapshotConfig, SnapshotMode
from ..config import get_settings


@dataclass
class SelectorEvent:
    """Selector event data for snapshot triggering."""
    event_type: str
    selector: str
    matched_count: int
    expected_count: Optional[int] = None
    session_id: str = "unknown"
    site: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelectorSnapshot:
    """Integrates snapshot system with selector engine."""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        """Initialize selector engine integration."""
        self.snapshot_manager = snapshot_manager
        self.settings = get_settings()
        self._selector_engine = None
        self._initialized = False
        
        # Event callbacks
        self.on_selector_failure: List[Callable] = []
        self.on_selector_timeout: List[Callable] = []
        self.on_performance_degradation: List[Callable] = []
        self.on_selector_success: List[Callable] = []
        
        # Statistics
        self.integration_stats = {
            "selectors_executed": 0,
            "selector_failures": 0,
            "selector_timeouts": 0,
            "snapshots_captured": 0,
            "performance_issues": 0
        }
        
        # Performance tracking
        self.selector_performance: Dict[str, List[float]] = {}
        self.performance_threshold_ms = 5000  # 5 seconds
    
    async def initialize(self):
        """Initialize selector snapshot handler."""
        try:
            # Import selector engine to avoid circular imports
            from src.resilience.integration.selector_engine import SelectorEngineIntegration
            
            # Get selector engine integration
            self._selector_engine = SelectorEngineIntegration()
            
            # Hook into selector engine events
            await self._hook_selector_events()
            
            self._initialized = True
            print("✅ Selector engine integration initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize selector engine integration: {e}")
            raise
    
    async def _hook_selector_events(self):
        """Hook into selector engine events."""
        if not self._selector_engine:
            return
        
        # Hook into selector execution
        if hasattr(self._selector_engine, 'on_selector_executed'):
            self._selector_engine.on_selector_executed.append(self._on_selector_executed)
        
        # Hook into selector failures
        if hasattr(self._selector_engine, 'on_selector_failed'):
            self._selector_engine.on_selector_failed.append(self._on_selector_failed)
        
        # Hook into selector timeouts
        if hasattr(self._selector_engine, 'on_selector_timeout'):
            self._selector_engine.on_selector_timeout.append(self._on_selector_timeout)
        
        # Hook into performance monitoring
        if hasattr(self._selector_engine, 'on_performance_issue'):
            self._selector_engine.on_performance_issue.append(self._on_performance_issue)
    
    async def _on_selector_executed(self, selector: str, result: Dict[str, Any]):
        """Handle selector execution event."""
        try:
            self.integration_stats["selectors_executed"] += 1
            
            # Track performance
            execution_time = result.get("execution_time_ms", 0)
            if selector not in self.selector_performance:
                self.selector_performance[selector] = []
            self.selector_performance[selector].append(execution_time)
            
            # Check for performance degradation
            if execution_time > self.performance_threshold_ms:
                await self._handle_performance_degradation(selector, result)
            
            # Check for selector failure
            matched_count = result.get("matched_count", 0)
            if matched_count == 0:
                await self._handle_selector_failure(selector, result)
            else:
                await self._handle_selector_success(selector, result)
            
        except Exception as e:
            print(f"❌ Error handling selector execution: {e}")
    
    async def _on_selector_failed(self, selector: str, error: Dict[str, Any]):
        """Handle selector failure event."""
        try:
            self.integration_stats["selector_failures"] += 1
            await self._handle_selector_failure(selector, error)
            
        except Exception as e:
            print(f"❌ Error handling selector failure: {e}")
    
    async def _on_selector_timeout(self, selector: str, timeout_info: Dict[str, Any]):
        """Handle selector timeout event."""
        try:
            self.integration_stats["selector_timeouts"] += 1
            
            # Capture snapshot on selector timeout
            if self.settings.enable_metrics:
                context_data = {
                    "site": timeout_info.get("site", "unknown"),
                    "module": "selector_engine",
                    "component": "timeout_handler",
                    "session_id": timeout_info.get("session_id", "unknown"),
                    "function": "selector_timeout",
                    "selector": selector,
                    "timeout_duration": timeout_info.get("duration_ms"),
                    "timeout_reason": timeout_info.get("reason")
                }
                
                snapshot_id = await self._capture_selector_snapshot(
                    trigger_source="selector_timeout",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_selector_timeout:
                await callback(selector, timeout_info)
                
        except Exception as e:
            print(f"❌ Error handling selector timeout: {e}")
    
    async def _on_performance_issue(self, selector: str, performance_data: Dict[str, Any]):
        """Handle performance issue event."""
        try:
            await self._handle_performance_degradation(selector, performance_data)
            
        except Exception as e:
            print(f"❌ Error handling performance issue: {e}")
    
    async def _handle_selector_failure(self, selector: str, error_data: Dict[str, Any]):
        """Handle selector failure with snapshot capture."""
        try:
            # Capture snapshot on selector failure
            if self.settings.enable_metrics:
                context_data = {
                    "site": error_data.get("site", "unknown"),
                    "module": "selector_engine",
                    "component": "failure_handler",
                    "session_id": error_data.get("session_id", "unknown"),
                    "function": "selector_failed",
                    "selector": selector,
                    "matched_count": 0,
                    "error_type": error_data.get("error_type"),
                    "error_message": error_data.get("error_message"),
                    "page_url": error_data.get("page_url")
                }
                
                snapshot_id = await self._capture_selector_snapshot(
                    trigger_source="selector_failure",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_selector_failure:
                await callback(selector, error_data)
                
        except Exception as e:
            print(f"❌ Error handling selector failure: {e}")
    
    async def _handle_selector_success(self, selector: str, result: Dict[str, Any]):
        """Handle successful selector execution."""
        try:
            # Notify callbacks
            for callback in self.on_selector_success:
                await callback(selector, result)
                
        except Exception as e:
            print(f"❌ Error handling selector success: {e}")
    
    async def _handle_performance_degradation(self, selector: str, performance_data: Dict[str, Any]):
        """Handle performance degradation with snapshot capture."""
        try:
            self.integration_stats["performance_issues"] += 1
            
            # Capture snapshot on performance degradation
            if self.settings.enable_metrics:
                context_data = {
                    "site": performance_data.get("site", "unknown"),
                    "module": "selector_engine",
                    "component": "performance_monitor",
                    "session_id": performance_data.get("session_id", "unknown"),
                    "function": "performance_degradation",
                    "selector": selector,
                    "execution_time_ms": performance_data.get("execution_time_ms"),
                    "performance_threshold_ms": self.performance_threshold_ms,
                    "degradation_factor": performance_data.get("execution_time_ms", 0) / self.performance_threshold_ms
                }
                
                snapshot_id = await self._capture_selector_snapshot(
                    trigger_source="selector_performance_degradation",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_performance_degradation:
                await callback(selector, performance_data)
                
        except Exception as e:
            print(f"❌ Error handling performance degradation: {e}")
    
    async def _capture_selector_snapshot(self, 
                                   trigger_source: str,
                                   context_data: Dict[str, Any]) -> Optional[str]:
        """Capture selector-specific snapshot."""
        try:
            # Get active page
            page = await self._get_active_page()
            if not page:
                return None
            
            # Build snapshot context
            context = SnapshotContext(
                site=context_data.get("site", "unknown"),
                module=context_data.get("module", "selector"),
                component=context_data.get("component", "engine"),
                session_id=context_data.get("session_id", "unknown"),
                function=context_data.get("function"),
                additional_metadata={
                    "trigger_source": trigger_source,
                    "selector_integration": True,
                    "timestamp": datetime.now().isoformat(),
                    **context_data
                }
            )
            
            # Build snapshot config
            # FIX: Check if selector is available, otherwise use FULL_PAGE mode
            selector = context_data.get("selector")
            if selector:
                mode = SnapshotMode.SELECTOR
            else:
                mode = SnapshotMode.FULL_PAGE
                print(f"⚠️ No selector provided, using FULL_PAGE mode for {trigger_source}")
            
            config = SnapshotConfig(
                mode=mode,
                capture_html=True,
                capture_screenshot=True,
                capture_console=True,
                capture_network=False,
                selector=selector,
                async_save=self.settings.enable_async_save,
                deduplication_enabled=self.settings.enable_deduplication
            )
            
            # Capture snapshot
            bundle = await self.snapshot_manager.capture_snapshot(page, context, config)
            
            if bundle:
                # Handle both SnapshotBundle and PartialSnapshotBundle
                # Try to get a useful snapshot ID
                try:
                    # SnapshotBundle has content_hash
                    snapshot_id = getattr(bundle, 'content_hash', None)
                    if snapshot_id:
                        snapshot_id = snapshot_id[:8]
                    else:
                        # PartialSnapshotBundle has timestamp as string
                        ts = getattr(bundle, 'timestamp', None)
                        if ts and isinstance(ts, str):
                            snapshot_id = ts.replace('-', '').replace(':', '').replace('T', '').replace('.', '')[:8]
                        else:
                            snapshot_id = "unknown"
                except Exception:
                    snapshot_id = "unknown"
                    
                print(f"📸 Selector snapshot captured: {snapshot_id} from {trigger_source}")
                return snapshot_id
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to capture selector snapshot: {e}")
            return None
    
    async def _get_active_page(self) -> Optional[Any]:
        """Get the currently active page."""
        try:
            # Try to get page from selector engine
            if self._selector_engine and hasattr(self._selector_engine, 'get_active_page'):
                return await self._selector_engine.get_active_page()
            
            # Try to get page from browser manager
            from src.browser.manager import BrowserManager
            browser_manager = BrowserManager()
            if hasattr(browser_manager, 'get_active_page'):
                return await browser_manager.get_active_page()
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting active page: {e}")
            return None
    
    def get_selector_performance_stats(self) -> Dict[str, Any]:
        """Get selector performance statistics."""
        stats = {}
        for selector, times in self.selector_performance.items():
            if times:
                stats[selector] = {
                    "executions": len(times),
                    "average_time_ms": sum(times) / len(times),
                    "min_time_ms": min(times),
                    "max_time_ms": max(times),
                    "latest_time_ms": times[-1] if times else 0,
                    "performance_issues": sum(1 for t in times if t > self.performance_threshold_ms)
                }
        
        return stats
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of selector integration."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "selector_engine_available": self._selector_engine is not None,
            "statistics": self.integration_stats,
            "performance_threshold_ms": self.performance_threshold_ms,
            "tracked_selectors": len(self.selector_performance),
            "event_callbacks": {
                "selector_failure": len(self.on_selector_failure) > 0,
                "selector_timeout": len(self.on_selector_timeout) > 0,
                "performance_degradation": len(self.on_performance_degradation) > 0,
                "selector_success": len(self.on_selector_success) > 0
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "integration_type": "selector_engine",
            "initialized": self._initialized,
            "statistics": self.integration_stats,
            "performance_stats": self.get_selector_performance_stats(),
            "event_callbacks": {
                "selector_failure": len(self.on_selector_failure),
                "selector_timeout": len(self.on_selector_timeout),
                "performance_degradation": len(self.on_performance_degradation),
                "selector_success": len(self.on_selector_success)
            }
        }
