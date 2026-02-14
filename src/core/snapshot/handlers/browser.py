"""
Browser Manager Integration - Hooks snapshot system into browser lifecycle.

This module integrates the snapshot system with the browser manager
to automatically capture snapshots during browser operations.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from ..manager import SnapshotManager
from ..models import SnapshotContext, SnapshotConfig, SnapshotMode
from ..config import get_settings
from ..exceptions import (
    SnapshotError, SnapshotCircuitOpen, SnapshotCompleteFailure,
    DiskFullError, PermissionError
)


@dataclass
class BrowserEvent:
    """Browser event data for snapshot triggering."""
    event_type: str
    session_id: str
    page_url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BrowserSnapshot:
    """Integrates snapshot system with browser manager."""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        """Initialize browser manager integration."""
        self.snapshot_manager = snapshot_manager
        self.settings = get_settings()
        self._browser_manager = None
        self._initialized = False
        
        # Event callbacks
        self.on_session_created: List[Callable] = []
        self.on_session_terminated: List[Callable] = []
        self.on_navigation_error: List[Callable] = []
        self.on_resource_error: List[Callable] = []
        self.on_browser_crash: List[Callable] = []
        
        # Statistics
        self.integration_stats = {
            "sessions_monitored": 0,
            "snapshots_captured": 0,
            "navigation_errors": 0,
            "browser_crashes": 0
        }
    
    async def initialize(self):
        """Initialize browser snapshot handler."""
        try:
            # Import browser manager to avoid circular imports
            from src.browser.manager import BrowserManager
            
            # Get global browser manager instance
            self._browser_manager = BrowserManager()
            
            # Hook into browser manager events
            await self._hook_browser_events()
            
            self._initialized = True
            print("✅ Browser manager integration initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize browser manager integration: {e}")
            raise
    
    async def _hook_browser_events(self):
        """Hook into browser manager events."""
        if not self._browser_manager:
            return
        
        # Hook into session lifecycle
        if hasattr(self._browser_manager, 'on_session_created'):
            self._browser_manager.on_session_created.append(self._on_session_created)
        
        if hasattr(self._browser_manager, 'on_session_terminated'):
            self._browser_manager.on_session_terminated.append(self._on_session_terminated)
        
        # Hook into navigation events
        if hasattr(self._browser_manager, 'on_navigation_error'):
            self._browser_manager.on_navigation_error.append(self._on_navigation_error)
        
        # Hook into resource errors
        if hasattr(self._browser_manager, 'on_resource_error'):
            self._browser_manager.on_resource_error.append(self._on_resource_error)
        
        # Hook into browser crashes
        if hasattr(self._browser_manager, 'on_browser_crash'):
            self._browser_manager.on_browser_crash.append(self._on_browser_crash)
    
    async def _on_session_created(self, session_id: str, session_data: Dict[str, Any]):
        """Handle session creation event."""
        try:
            self.integration_stats["sessions_monitored"] += 1
            
            # Capture snapshot on session creation for debugging
            if self.settings.enable_metrics:
                context_data = {
                    "site": session_data.get("site", "unknown"),
                    "module": "browser_lifecycle",
                    "component": "session_creation",
                    "session_id": session_id,
                    "function": "session_created"
                }
                
                snapshot_id = await self._capture_browser_snapshot(
                    trigger_source="browser_session_created",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_session_created:
                await callback(session_id, session_data)
                
        except Exception as e:
            print(f"❌ Error handling session creation: {e}")
    
    async def _on_session_terminated(self, session_id: str, reason: str):
        """Handle session termination event."""
        try:
            # Capture snapshot before session termination
            if self.settings.enable_metrics:
                context_data = {
                    "site": "session_termination",
                    "module": "browser_lifecycle",
                    "component": "session_cleanup",
                    "session_id": session_id,
                    "function": "session_terminated",
                    "termination_reason": reason
                }
                
                snapshot_id = await self._capture_browser_snapshot(
                    trigger_source="browser_session_terminated",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_session_terminated:
                await callback(session_id, reason)
                
        except Exception as e:
            print(f"❌ Error handling session termination: {e}")
    
    async def _on_navigation_error(self, session_id: str, error: Dict[str, Any]):
        """Handle navigation error event."""
        try:
            self.integration_stats["navigation_errors"] += 1
            
            # Capture snapshot on navigation error
            if self.settings.enable_metrics:
                context_data = {
                    "site": error.get("site", "unknown"),
                    "module": "browser_navigation",
                    "component": "page_load",
                    "session_id": session_id,
                    "function": "navigation_failed",
                    "error_url": error.get("url"),
                    "error_type": error.get("error_type"),
                    "error_message": error.get("message")
                }
                
                snapshot_id = await self._capture_browser_snapshot(
                    trigger_source="browser_navigation_error",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_navigation_error:
                await callback(session_id, error)
                
        except Exception as e:
            print(f"❌ Error handling navigation error: {e}")
    
    async def _on_resource_error(self, session_id: str, error: Dict[str, Any]):
        """Handle resource error event."""
        try:
            # Capture snapshot on resource error
            if self.settings.enable_metrics:
                context_data = {
                    "site": error.get("site", "unknown"),
                    "module": "browser_resources",
                    "component": "resource_loading",
                    "session_id": session_id,
                    "function": "resource_failed",
                    "resource_url": error.get("url"),
                    "resource_type": error.get("resource_type"),
                    "error_status": error.get("status")
                }
                
                snapshot_id = await self._capture_browser_snapshot(
                    trigger_source="browser_resource_error",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_resource_error:
                await callback(session_id, error)
                
        except Exception as e:
            print(f"❌ Error handling resource error: {e}")
    
    async def _on_browser_crash(self, session_id: str, crash_info: Dict[str, Any]):
        """Handle browser crash event."""
        try:
            self.integration_stats["browser_crashes"] += 1
            
            # Capture snapshot on browser crash
            if self.settings.enable_metrics:
                context_data = {
                    "site": "browser_crash",
                    "module": "browser_stability",
                    "component": "crash_handler",
                    "session_id": session_id,
                    "function": "browser_crashed",
                    "crash_reason": crash_info.get("reason"),
                    "crash_stack": crash_info.get("stack_trace")
                }
                
                snapshot_id = await self._capture_browser_snapshot(
                    trigger_source="browser_crash",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_browser_crash:
                await callback(session_id, crash_info)
                
        except Exception as e:
            print(f"❌ Error handling browser crash: {e}")
    
    async def _capture_browser_snapshot(self, 
                                   trigger_source: str,
                                   context_data: Dict[str, Any]) -> Optional[str]:
        """Capture browser-specific snapshot with robust error handling."""
        try:
            # Get active page from browser manager
            page = await self.get_active_page()
            if not page:
                print("⚠️ No active page available for browser snapshot")
                return None
            
            # Build snapshot context
            context = SnapshotContext(
                site=context_data.get("site", "unknown"),
                module=context_data.get("module", "browser"),
                component=context_data.get("component", "integration"),
                session_id=context_data.get("session_id", "unknown"),
                function=context_data.get("function"),
                additional_metadata={
                    "trigger_source": trigger_source,
                    "browser_integration": True,
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
            
            # Capture with exception handling
            try:
                bundle = await self.snapshot_manager.capture_snapshot(page, context, config)
                if bundle:
                    snapshot_id = bundle.content_hash[:8] if hasattr(bundle, 'content_hash') else str(hash(bundle))[:8]
                    print(f"📸 Browser snapshot captured: {snapshot_id} from {trigger_source}")
                    return snapshot_id
                return None
                
            except SnapshotCircuitOpen:
                print("🚨 Browser snapshot skipped - circuit breaker open")
                return None
            except SnapshotCompleteFailure:
                print("⚠️ Browser snapshot failed completely")
                return None
            except (DiskFullError, PermissionError) as e:
                print(f"🚨 Browser snapshot storage failed: {e.message}")
                return None
            except SnapshotError as e:
                print(f"⚠️ Browser snapshot failed: {e.message}")
                return None
            
        except Exception as e:
            print(f"❌ Unexpected error in browser snapshot: {e}")
            return None
    
    async def get_active_page(self) -> Optional[Any]:
        """Get the currently active page from browser manager."""
        try:
            if not self._browser_manager:
                return None
            
            # Try different methods to get active page
            if hasattr(self._browser_manager, 'get_active_page'):
                return await self._browser_manager.get_active_page()
            elif hasattr(self._browser_manager, 'active_page'):
                return self._browser_manager.active_page
            elif hasattr(self._browser_manager, 'sessions'):
                # Get page from most recent session
                sessions = self._browser_manager.sessions
                if sessions:
                    latest_session = max(sessions.values(), key=lambda s: s.created_at)
                    return latest_session.page
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting active page: {e}")
            return None
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of browser integration."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "browser_manager_available": self._browser_manager is not None,
            "statistics": self.integration_stats,
            "event_hooks": {
                "session_created": len(self.on_session_created) > 0,
                "session_terminated": len(self.on_session_terminated) > 0,
                "navigation_error": len(self.on_navigation_error) > 0,
                "resource_error": len(self.on_resource_error) > 0,
                "browser_crash": len(self.on_browser_crash) > 0
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "integration_type": "browser_manager",
            "initialized": self._initialized,
            "statistics": self.integration_stats,
            "event_callbacks": {
                "session_created": len(self.on_session_created),
                "session_terminated": len(self.on_session_terminated),
                "navigation_error": len(self.on_navigation_error),
                "resource_error": len(self.on_resource_error),
                "browser_crash": len(self.on_browser_crash)
            }
        }
