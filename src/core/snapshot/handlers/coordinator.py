"""
Snapshot Coordinator - Central orchestration for all snapshot integrations.

This module provides the main coordinator that manages all snapshot
integrations and ensures they work together seamlessly.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from ..manager import SnapshotManager, get_snapshot_manager
from ..exceptions import (
    SnapshotError, SnapshotCircuitOpen, SnapshotCompleteFailure,
    DiskFullError, PermissionError, PartialSnapshotBundle
)
from ..circuit_breaker import get_circuit_breaker, check_circuit_breaker
from ..models import SnapshotContext, SnapshotConfig, SnapshotMode
from ..config import get_settings
from .browser import BrowserSnapshot
from .session import SessionSnapshot
from .scraper import ScraperSnapshot
from .selector import SelectorSnapshot
from .error import ErrorSnapshot
from .retry import RetrySnapshot
from .monitoring import MonitoringSnapshot


@dataclass
class IntegrationState:
    """State tracking for snapshot integrations."""
    initialized_integrations: Set[str] = field(default_factory=set)
    active_snapshots: Dict[str, str] = field(default_factory=dict)  # session_id -> snapshot_id
    integration_errors: List[Dict[str, Any]] = field(default_factory=list)
    last_health_check: Optional[datetime] = None


class SnapshotCoordinator:
    """Central coordinator for all snapshot integrations."""
    
    def __init__(self, snapshot_manager: Optional[SnapshotManager] = None):
        """Initialize snapshot coordinator."""
        self.snapshot_manager = snapshot_manager or get_snapshot_manager()
        self.settings = get_settings()
        
        # Initialize integration components
        self.browser = BrowserSnapshot(self.snapshot_manager)
        self.session = SessionSnapshot(self.snapshot_manager)
        self.scraper = ScraperSnapshot(self.snapshot_manager)
        self.selector = SelectorSnapshot(self.snapshot_manager)
        self.error = ErrorSnapshot(self.snapshot_manager)
        self.retry = RetrySnapshot(self.snapshot_manager)
        self.monitoring = MonitoringSnapshot(self.snapshot_manager)
        
        # Coordinator state
        self.state = IntegrationState()
        self._lock = asyncio.Lock()
        self.is_shutting_down = False
        self.shutdown_start_time = None
        
        # Event callbacks
        self.on_snapshot_captured: List[callable] = []
        self.on_integration_error: List[callable] = []
    
    async def initialize_all_integrations(self) -> bool:
        """Initialize all snapshot integrations."""
        try:
            async with self._lock:
                integrations = [
                    ("browser", self.browser),
                    ("session", self.session),
                    ("scraper", self.scraper),
                    ("selector", self.selector),
                    ("error", self.error),
                    ("retry", self.retry),
                    ("monitoring", self.monitoring)
                ]
                
                for name, integration in integrations:
                    try:
                        await integration.initialize()
                        self.state.initialized_integrations.add(name)
                        print(f"✅ Initialized {name} integration")
                    except Exception as e:
                        error_info = {
                            "integration": name,
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                        self.state.integration_errors.append(error_info)
                        print(f"❌ Failed to initialize {name} integration: {e}")
                
                # Set up cross-integration event routing
                await self._setup_event_routing()
                
                self.state.last_health_check = datetime.now()
                success_rate = len(self.state.initialized_integrations) / len(integrations) * 100
                print(f"🎯 Snapshot coordinator initialized: {success_rate:.1f}% success rate")
                
                return len(self.state.initialized_integrations) > 0
                
        except Exception as e:
            print(f"❌ Critical error initializing snapshot coordinator: {e}")
            return False
    
    async def _setup_event_routing(self):
        """Set up event routing between integrations."""
        # Route browser events to session integration
        self.browser.on_session_created.append(
            self.session.handle_session_created
        )
        
        # Route selector failures to scraper integration
        self.selector.on_selector_failure.append(
            self.scraper.handle_selector_failure
        )
        
        # Route scraper errors to error integration
        self.scraper.on_scraping_error.append(
            self.error.handle_scraping_error
        )
        
        # Route retry exhaustion to error integration
        self.retry.on_retry_exhausted.append(
            self.error.handle_retry_exhaustion
        )
        
        # Route all errors to monitoring integration
        self.error.on_error_occurred.append(
            self.monitoring.record_error
        )
        
        # Route all snapshots to monitoring integration
        for integration in [self.browser, self.session, 
                          self.scraper, self.selector]:
            integration.on_snapshot_captured.append(
                self.monitoring.record_snapshot
            )
    
    async def capture_system_snapshot(self, 
                                 trigger_source: str,
                                 context_data: Dict[str, Any],
                                 page: Any = None) -> Optional[str]:
        """Capture system-wide snapshot with full context."""
        try:
            # Build comprehensive context
            context = SnapshotContext(
                site=context_data.get("site", "unknown"),
                module=context_data.get("module", "system"),
                component=context_data.get("component", trigger_source),
                session_id=context_data.get("session_id", "system"),
                function=context_data.get("function", "system_snapshot"),
                additional_metadata={
                    "trigger_source": trigger_source,
                    "coordinator_timestamp": datetime.now().isoformat(),
                    "integration_context": context_data
                }
            )
            
            # Build comprehensive config
            config = SnapshotConfig(
                mode=SnapshotMode.BOTH,  # Capture everything for system snapshots
                capture_html=True,
                capture_screenshot=True,
                capture_console=True,
                capture_network=True,
                selector=context_data.get("selector"),
                async_save=self.settings.enable_async_save,
                deduplication_enabled=self.settings.enable_deduplication
            )
            
            # Get page if not provided
            if page is None:
                page = await self.browser_integration.get_active_page()
                if page is None:
                    print("⚠️  No active page available for system snapshot")
                    return None
            
            # Capture snapshot
            bundle = await self.snapshot_manager.capture_snapshot(page, context, config)
            
            if bundle:
                snapshot_id = bundle.content_hash[:8]
                session_id = context.session_id
                self.state.active_snapshots[session_id] = snapshot_id
                
                # Notify callbacks
                for callback in self.on_snapshot_captured:
                    await callback(trigger_source, bundle)
                
                print(f"📸 System snapshot captured: {snapshot_id} from {trigger_source}")
                return snapshot_id
            
            return None
            
        except Exception as e:
            error_info = {
                "trigger_source": trigger_source,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "context_data": context_data
            }
            self.state.integration_errors.append(error_info)
            
            # Notify error callbacks
            for callback in self.on_integration_error:
                await callback("system_snapshot", error_info)
            
            print(f"❌ Failed to capture system snapshot: {e}")
            return None
    
    async def get_integration_health(self) -> Dict[str, Any]:
        """Get health status of all integrations."""
        health_report = {
            "coordinator": {
                "overall_status": "healthy",
                "status": "healthy",
                "initialized_integrations": list(self.state.initialized_integrations),
                "total_integrations": 7,
                "initialization_rate": len(self.state.initialized_integrations) / 7 * 100,
                "active_snapshots": len(self.state.active_snapshots),
                "integration_errors": len(self.state.integration_errors),
                "last_health_check": self.state.last_health_check.isoformat() if self.state.last_health_check else None
            },
            "integrations": {}
        }
        
        # Get health from each integration
        integration_methods = [
            ("browser", self.browser),
            ("session", self.session),
            ("scraper", self.scraper),
            ("selector", self.selector),
            ("error", self.error),
            ("retry", self.retry),
            ("monitoring", self.monitoring)
        ]
        
        for name, integration in integration_methods:
            try:
                if hasattr(integration, 'get_health'):
                    health_report["integrations"][name] = await integration.get_health()
                else:
                    health_report["integrations"][name] = {
                        "status": "unknown",
                        "message": "Health check not implemented"
                    }
            except Exception as e:
                health_report["integrations"][name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return health_report
    
    async def cleanup_session_snapshots(self, session_id: str) -> int:
        """Clean up snapshots for a specific session."""
        try:
            if session_id in self.state.active_snapshots:
                del self.state.active_snapshots[session_id]
                print(f"🧹 Cleaned up snapshots for session: {session_id}")
                return 1
            return 0
        except Exception as e:
            print(f"❌ Error cleaning up session snapshots: {e}")
            return 0
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            # Get stats from all integrations
            integration_stats = {}
            integration_methods = [
                ("browser", self.browser_integration),
                ("session", self.session_integration),
                ("scraper", self.scraper_integration),
                ("selector", self.selector_integration),
                ("error", self.error_integration),
                ("retry", self.retry_integration),
                ("monitoring", self.monitoring_integration)
            ]
            
            for name, integration in integration_methods:
                try:
                    if hasattr(integration, 'get_statistics'):
                        integration_stats[name] = await integration.get_statistics()
                    else:
                        integration_stats[name] = {"status": "statistics not available"}
                except Exception as e:
                    integration_stats[name] = {"error": str(e)}
            
            # Get snapshot manager stats
            snapshot_stats = self.snapshot_manager.get_metrics()
            
            return {
                "coordinator": {
                    "initialized_integrations": list(self.state.initialized_integrations),
                    "active_snapshots": self.state.active_snapshots,
                    "integration_errors": self.state.integration_errors,
                    "last_health_check": self.state.last_health_check.isoformat() if self.state.last_health_check else None
                },
                "integrations": integration_stats,
                "snapshot_manager": {
                    "total_snapshots": snapshot_stats.total_snapshots,
                    "successful_snapshots": snapshot_stats.successful_snapshots,
                    "failed_snapshots": snapshot_stats.failed_snapshots,
                    "success_rate": snapshot_stats.success_rate,
                    "average_capture_time": snapshot_stats.average_capture_time
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def register_snapshot_callback(self, callback: callable):
        """Register callback for snapshot events."""
        self.on_snapshot_captured.append(callback)
    
    def register_error_callback(self, callback: callable):
        """Register callback for integration errors."""
        self.on_integration_error.append(callback)
    
    async def shutdown(self, timeout: int = 30) -> bool:
        """Shutdown snapshot coordinator - called by application shutdown system."""
        if self.is_shutting_down:
            return True
        
        print(f"🔄 Shutting down snapshot coordinator (timeout: {timeout}s)...")
        self.is_shutting_down = True
        self.shutdown_start_time = datetime.now()
        
        try:
            # 1. Stop accepting new snapshot requests
            print("   🛑 Stopping new snapshot requests...")
            await self._stop_accepting_requests()
            
            # 2. Wait for in-progress snapshots
            print("   ⏳ Waiting for in-progress snapshots...")
            await self._wait_for_snapshots(timeout)
            
            # 3. Shutdown all handlers
            print("   🔧 Shutting down handlers...")
            await self._shutdown_handlers()
            
            # 4. Flush final metrics
            print("   📊 Flushing final metrics...")
            await self._flush_final_metrics()
            
            # 5. Cleanup resources
            print("   🧹 Cleaning up resources...")
            await self._cleanup_coordinator_resources()
            
            shutdown_duration = (datetime.now() - self.shutdown_start_time).total_seconds()
            print(f"   ✅ Snapshot coordinator shutdown complete ({shutdown_duration:.2f}s)")
            return True
            
        except Exception as e:
            print(f"   ❌ Error during shutdown: {e}")
            return False
    
    async def _stop_accepting_requests(self):
        """Stop accepting new snapshot requests."""
        # Mark all handlers as shutting down
        for handler_name, handler in [
            ("browser", self.browser),
            ("session", self.session),
            ("scraper", self.scraper),
            ("selector", self.selector),
            ("error", self.error),
            ("retry", self.retry),
            ("monitoring", self.monitoring)
        ]:
            try:
                if hasattr(handler, 'stop_accepting_requests'):
                    await handler.stop_accepting_requests()
                    print(f"      ✅ {handler_name} handler stopped accepting requests")
            except Exception as e:
                print(f"      ⚠️ Error stopping {handler_name} handler: {e}")
    
    async def _wait_for_snapshots(self, timeout: int):
        """Wait for in-progress snapshots to complete."""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            # Check if any snapshots are in progress
            in_progress = len(self.state.active_snapshots)
            if in_progress == 0:
                print(f"      ✅ All snapshots completed")
                break
            
            print(f"      ⏳ Waiting for {in_progress} in-progress snapshots...")
            await asyncio.sleep(0.5)
        else:
            print(f"      ⚠️ Timeout waiting for snapshots - {len(self.state.active_snapshots)} remaining")
    
    async def _flush_final_metrics(self):
        """Flush final metrics before shutdown."""
        try:
            stats = await self.get_system_statistics()
            snapshot_stats = stats.get('snapshot_manager', {})
            
            print("      📊 Final Snapshot Metrics:")
            print(f"         Total Snapshots: {snapshot_stats.get('total_snapshots', 0)}")
            print(f"         Success Rate: {snapshot_stats.get('success_rate', 0):.1f}%")
            print(f"         Average Capture Time: {snapshot_stats.get('average_capture_time', 0):.0f}ms")
            
        except Exception as e:
            print(f"      ⚠️ Error flushing metrics: {e}")
    
    async def _shutdown_handlers(self):
        """Shutdown all snapshot handlers."""
        for handler_name, handler in [
            ("browser", self.browser),
            ("session", self.session),
            ("scraper", self.scraper),
            ("selector", self.selector),
            ("error", self.error),
            ("retry", self.retry),
            ("monitoring", self.monitoring)
        ]:
            try:
                if hasattr(handler, 'shutdown'):
                    await handler.shutdown()
                    print(f"      ✅ {handler_name} handler shutdown")
                else:
                    print(f"      ⚠️ {handler_name} handler has no shutdown method")
            except Exception as e:
                print(f"      ❌ Failed to shutdown {handler_name} handler: {e}")
    
    async def _cleanup_coordinator_resources(self):
        """Clean up coordinator-specific resources."""
        try:
            # Clear event callbacks
            self.on_snapshot_captured.clear()
            self.on_integration_error.clear()
            
            # Clear state
            self.state = IntegrationState()
            
            print("🧹 Coordinator resources cleaned up")
            
        except Exception as e:
            print(f"❌ Error during coordinator cleanup: {e}")


# Global coordinator instance
_snapshot_coordinator: Optional[SnapshotCoordinator] = None


def get_snapshot_coordinator() -> SnapshotCoordinator:
    """Get the global snapshot coordinator instance."""
    global _snapshot_coordinator
    if _snapshot_coordinator is None:
        _snapshot_coordinator = SnapshotCoordinator()
    return _snapshot_coordinator
