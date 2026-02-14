"""
Session Manager Integration - Hooks snapshot system into session lifecycle.

This module integrates the snapshot system with session management
to automatically capture snapshots during session operations.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from ..manager import SnapshotManager
from ..models import SnapshotContext, SnapshotConfig, SnapshotMode
from ..config import get_settings


@dataclass
class SessionEvent:
    """Session event data for snapshot triggering."""
    event_type: str
    session_id: str
    site: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionSnapshot:
    """Integrates snapshot system with session manager."""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        """Initialize session manager integration."""
        self.snapshot_manager = snapshot_manager
        self.settings = get_settings()
        self._session_manager = None
        self._initialized = False
        
        # Event callbacks
        self.on_session_created: List[Callable] = []
        self.on_session_started: List[Callable] = []
        self.on_session_paused: List[Callable] = []
        self.on_session_resumed: List[Callable] = []
        self.on_session_terminated: List[Callable] = []
        self.on_session_error: List[Callable] = []
        
        # Statistics
        self.integration_stats = {
            "sessions_monitored": 0,
            "snapshots_captured": 0,
            "session_errors": 0,
            "session_lifecycles": {
                "created": 0,
                "started": 0,
                "paused": 0,
                "resumed": 0,
                "terminated": 0
            }
        }
    
    async def initialize(self):
        """Initialize session snapshot handler."""
        try:
            # Import session manager to avoid circular imports
            from src.browser.session_manager import BrowserSessionManager
            
            # Get global session manager instance
            self._session_manager = BrowserSessionManager
            
            # Hook into session manager events
            await self._hook_session_events()
            
            self._initialized = True
            print("✅ Session manager integration initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize session manager integration: {e}")
            raise
    
    async def _hook_session_events(self):
        """Hook into session manager events."""
        if not self._session_manager:
            return
        
        # Hook into session lifecycle events
        if hasattr(self._session_manager, 'on_session_created'):
            self._session_manager.on_session_created.append(self._on_session_created)
        
        if hasattr(self._session_manager, 'on_session_started'):
            self._session_manager.on_session_started.append(self._on_session_started)
        
        if hasattr(self._session_manager, 'on_session_paused'):
            self._session_manager.on_session_paused.append(self._on_session_paused)
        
        if hasattr(self._session_manager, 'on_session_resumed'):
            self._session_manager.on_session_resumed.append(self._on_session_resumed)
        
        if hasattr(self._session_manager, 'on_session_terminated'):
            self._session_manager.on_session_terminated.append(self._on_session_terminated)
        
        if hasattr(self._session_manager, 'on_session_error'):
            self._session_manager.on_session_error.append(self._on_session_error)
    
    async def _on_session_created(self, session_id: str, session_data: Dict[str, Any]):
        """Handle session creation event."""
        try:
            self.integration_stats["sessions_monitored"] += 1
            self.integration_stats["session_lifecycles"]["created"] += 1
            
            # Capture snapshot on session creation
            if self.settings.enable_metrics:
                context_data = {
                    "site": session_data.get("site", "unknown"),
                    "module": "session_lifecycle",
                    "component": "creation",
                    "session_id": session_id,
                    "function": "session_created",
                    "session_config": session_data.get("config"),
                    "creation_reason": session_data.get("reason")
                }
                
                snapshot_id = await self._capture_session_snapshot(
                    trigger_source="session_created",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_session_created:
                await callback(session_id, session_data)
                
        except Exception as e:
            print(f"❌ Error handling session creation: {e}")
    
    async def _on_session_started(self, session_id: str, start_data: Dict[str, Any]):
        """Handle session started event."""
        try:
            self.integration_stats["session_lifecycles"]["started"] += 1
            
            # Notify callbacks
            for callback in self.on_session_started:
                await callback(session_id, start_data)
                
        except Exception as e:
            print(f"❌ Error handling session started: {e}")
    
    async def _on_session_paused(self, session_id: str, pause_data: Dict[str, Any]):
        """Handle session paused event."""
        try:
            self.integration_stats["session_lifecycles"]["paused"] += 1
            
            # Capture snapshot on session pause
            if self.settings.enable_metrics:
                context_data = {
                    "site": pause_data.get("site", "unknown"),
                    "module": "session_lifecycle",
                    "component": "pause",
                    "session_id": session_id,
                    "function": "session_paused",
                    "pause_reason": pause_data.get("reason"),
                    "pause_duration": pause_data.get("duration")
                }
                
                snapshot_id = await self._capture_session_snapshot(
                    trigger_source="session_paused",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_session_paused:
                await callback(session_id, pause_data)
                
        except Exception as e:
            print(f"❌ Error handling session paused: {e}")
    
    async def _on_session_resumed(self, session_id: str, resume_data: Dict[str, Any]):
        """Handle session resumed event."""
        try:
            self.integration_stats["session_lifecycles"]["resumed"] += 1
            
            # Notify callbacks
            for callback in self.on_session_resumed:
                await callback(session_id, resume_data)
                
        except Exception as e:
            print(f"❌ Error handling session resumed: {e}")
    
    async def _on_session_terminated(self, session_id: str, termination_data: Dict[str, Any]):
        """Handle session termination event."""
        try:
            self.integration_stats["session_lifecycles"]["terminated"] += 1
            
            # Capture snapshot before session termination
            if self.settings.enable_metrics:
                context_data = {
                    "site": termination_data.get("site", "unknown"),
                    "module": "session_lifecycle",
                    "component": "termination",
                    "session_id": session_id,
                    "function": "session_terminated",
                    "termination_reason": termination_data.get("reason"),
                    "session_duration": termination_data.get("duration"),
                    "final_state": termination_data.get("final_state")
                }
                
                snapshot_id = await self._capture_session_snapshot(
                    trigger_source="session_terminated",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_session_terminated:
                await callback(session_id, termination_data)
                
        except Exception as e:
            print(f"❌ Error handling session termination: {e}")
    
    async def _on_session_error(self, session_id: str, error_data: Dict[str, Any]):
        """Handle session error event."""
        try:
            self.integration_stats["session_errors"] += 1
            
            # Capture snapshot on session error
            if self.settings.enable_metrics:
                context_data = {
                    "site": error_data.get("site", "unknown"),
                    "module": "session_lifecycle",
                    "component": "error_handler",
                    "session_id": session_id,
                    "function": "session_error",
                    "error_type": error_data.get("error_type"),
                    "error_message": error_data.get("error_message"),
                    "error_context": error_data.get("context")
                }
                
                snapshot_id = await self._capture_session_snapshot(
                    trigger_source="session_error",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_session_error:
                await callback(session_id, error_data)
                
        except Exception as e:
            print(f"❌ Error handling session error: {e}")
    
    async def _capture_session_snapshot(self, 
                                  trigger_source: str,
                                  context_data: Dict[str, Any]) -> Optional[str]:
        """Capture session-specific snapshot."""
        try:
            # Get active page
            page = await self._get_active_page()
            if not page:
                return None
            
            # Build snapshot context
            context = SnapshotContext(
                site=context_data.get("site", "unknown"),
                module=context_data.get("module", "session"),
                component=context_data.get("component", "lifecycle"),
                session_id=context_data.get("session_id", "unknown"),
                function=context_data.get("function"),
                additional_metadata={
                    "trigger_source": trigger_source,
                    "session_integration": True,
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
                capture_network=False,
                async_save=self.settings.enable_async_save,
                deduplication_enabled=self.settings.enable_deduplication
            )
            
            # Capture snapshot
            bundle = await self.snapshot_manager.capture_snapshot(page, context, config)
            
            if bundle:
                snapshot_id = bundle.content_hash[:8]
                print(f"📸 Session snapshot captured: {snapshot_id} from {trigger_source}")
                return snapshot_id
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to capture session snapshot: {e}")
            return None
    
    async def _get_active_page(self) -> Optional[Any]:
        """Get the currently active page."""
        try:
            # Try to get page from session manager
            if self._session_manager and hasattr(self._session_manager, 'get_active_page'):
                return await self._session_manager.get_active_page()
            
            # Try to get page from browser manager
            from src.browser.manager import BrowserManager
            browser_manager = BrowserManager()
            if hasattr(browser_manager, 'get_active_page'):
                return await browser_manager.get_active_page()
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting active page: {e}")
            return None
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of session integration."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "session_manager_available": self._session_manager is not None,
            "statistics": self.integration_stats,
            "lifecycle_events": self.integration_stats["session_lifecycles"],
            "event_callbacks": {
                "session_created": len(self.on_session_created) > 0,
                "session_started": len(self.on_session_started) > 0,
                "session_paused": len(self.on_session_paused) > 0,
                "session_resumed": len(self.on_session_resumed) > 0,
                "session_terminated": len(self.on_session_terminated) > 0,
                "session_error": len(self.on_session_error) > 0
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "integration_type": "session_manager",
            "initialized": self._initialized,
            "statistics": self.integration_stats,
            "lifecycle_breakdown": self.integration_stats["session_lifecycles"],
            "event_callbacks": {
                "session_created": len(self.on_session_created),
                "session_started": len(self.on_session_started),
                "session_paused": len(self.on_session_paused),
                "session_resumed": len(self.on_session_resumed),
                "session_terminated": len(self.on_session_terminated),
                "session_error": len(self.on_session_error)
            }
        }
