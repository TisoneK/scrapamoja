"""
Error Handler Integration - Hooks snapshot system into error handling.

This module integrates the snapshot system with the error handler
to automatically capture snapshots when unhandled exceptions occur.
"""

import asyncio
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from src.observability.logger import get_logger

from ..manager import SnapshotManager
from ..models import SnapshotContext, SnapshotConfig, SnapshotMode
from ..config import get_settings

logger = get_logger(__name__)


@dataclass
class ErrorEvent:
    """Error event data for snapshot triggering."""
    error_type: str
    error_message: str
    stack_trace: str
    session_id: str = "unknown"
    site: str = "unknown"
    module: str = "unknown"
    component: str = "error_handler"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ErrorSnapshot:
    """Integrates snapshot system with error handler."""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        """Initialize error handler integration."""
        self.snapshot_manager = snapshot_manager
        self.settings = get_settings()
        self._error_handler = None
        self._initialized = False
        
        # Event callbacks
        self.on_error_occurred: List[Callable] = []
        self.on_critical_error: List[Callable] = []
        self.on_unhandled_exception: List[Callable] = []
        
        # Statistics
        self.integration_stats = {
            "errors_handled": 0,
            "snapshots_captured": 0,
            "critical_errors": 0,
            "unhandled_exceptions": 0,
            "error_types": {}
        }
        
        # Error categorization
        self.critical_error_types = {
            "BrowserCrashError",
            "SessionCreationError", 
            "NavigationError",
            "MemoryError",
            "TimeoutError"
        }
        
        self.snapshot_trigger_errors = {
            "SelectorNotFoundError",
            "ElementNotFoundError",
            "TimeoutError",
            "ConnectionError",
            "ValidationError"
        }
    
    async def initialize(self):
        """Initialize error snapshot handler."""
        try:
            # Import error handler to avoid circular imports
            from src.error_handler import GlobalErrorHandler
            
            # Get global error handler instance
            self._error_handler = GlobalErrorHandler()
            
            # Hook into error handler events
            await self._hook_error_events()
            
            self._initialized = True
            logger.info("Error handler integration initialized")
            
        except Exception as e:
            logger.error("Failed to initialize error handler integration", error=str(e))
            raise
    
    async def _hook_error_events(self):
        """Hook into error handler events."""
        if not self._error_handler:
            return
        
        # Hook into error handling
        if hasattr(self._error_handler, 'on_error_occurred'):
            self._error_handler.on_error_occurred.append(self._on_error_occurred)
        
        # Hook into critical errors
        if hasattr(self._error_handler, 'on_critical_error'):
            self._error_handler.on_critical_error.append(self._on_critical_error)
        
        # Hook into unhandled exceptions
        if hasattr(self._error_handler, 'on_unhandled_exception'):
            self._error_handler.on_unhandled_exception.append(self._on_unhandled_exception)
        
        # Set up global exception hook if not already present
        self._setup_global_exception_hook()
    
    def _setup_global_exception_hook(self):
        """Set up global exception hook for unhandled exceptions."""
        try:
            import sys
            
            # Store original exception hook
            original_hook = sys.excepthook
            
            def exception_hook(exc_type, exc_value, exc_traceback):
                """Global exception hook that captures snapshots."""
                # Handle the exception with snapshot capture
                asyncio.create_task(self._handle_global_exception(
                    exc_type, exc_value, exc_traceback
                ))
                
                # Call original hook
                if original_hook:
                    original_hook(exc_type, exc_value, exc_traceback)
            
            # Set our hook
            sys.excepthook = exception_hook
            
        except Exception as e:
            logger.error("Failed to set up global exception hook", error=str(e))
    
    async def _on_error_occurred(self, error: Dict[str, Any]):
        """Handle error occurrence event."""
        try:
            self.integration_stats["errors_handled"] += 1
            
            # Categorize error
            error_type = error.get("error_type", "UnknownError")
            error_class_name = error.get("error_class", "UnknownError")
            
            # Track error types
            if error_class_name not in self.integration_stats["error_types"]:
                self.integration_stats["error_types"][error_class_name] = 0
            self.integration_stats["error_types"][error_class_name] += 1
            
            # Check if this is a critical error
            if error_class_name in self.critical_error_types:
                await self._handle_critical_error(error)
            elif error_class_name in self.snapshot_trigger_errors:
                await self._handle_snapshot_trigger_error(error)
            
            # Notify callbacks
            for callback in self.on_error_occurred:
                await callback(error)
                
        except Exception as e:
            logger.error("Error handling error occurrence", error=str(e))
    
    async def _on_critical_error(self, error: Dict[str, Any]):
        """Handle critical error event."""
        try:
            self.integration_stats["critical_errors"] += 1
            
            # Capture snapshot on critical error
            if self.settings.enable_metrics:
                context_data = {
                    "site": error.get("site", "unknown"),
                    "module": error.get("module", "error_handler"),
                    "component": "critical_error",
                    "session_id": error.get("session_id", "unknown"),
                    "function": error.get("function", "critical_error"),
                    "error_type": error.get("error_type"),
                    "error_class": error.get("error_class"),
                    "error_message": error.get("error_message"),
                    "stack_trace": error.get("stack_trace"),
                    "criticality": "critical"
                }
                
                snapshot_id = await self._capture_error_snapshot(
                    trigger_source="critical_error",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_critical_error:
                await callback(error)
                
        except Exception as e:
            logger.error("Error handling critical error", error=str(e))
    
    async def _on_unhandled_exception(self, exc_type: type, exc_value: Exception, exc_traceback):
        """Handle unhandled exception event."""
        try:
            self.integration_stats["unhandled_exceptions"] += 1
            
            # Capture snapshot on unhandled exception
            if self.settings.enable_metrics:
                context_data = {
                    "site": "unhandled_exception",
                    "module": "error_handler",
                    "component": "exception_handler",
                    "session_id": "unknown",
                    "function": "unhandled_exception",
                    "error_type": exc_type.__name__,
                    "error_class": exc_type.__name__,
                    "error_message": str(exc_value),
                    "stack_trace": ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
                    "unhandled": True
                }
                
                snapshot_id = await self._capture_error_snapshot(
                    trigger_source="unhandled_exception",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            error_data = {
                "error_type": exc_type.__name__,
                "error_class": exc_type.__name__,
                "error_message": str(exc_value),
                "stack_trace": ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
                "unhandled": True
            }
            
            for callback in self.on_unhandled_exception:
                await callback(error_data)
                
        except Exception as e:
            logger.error("Error handling unhandled exception", error=str(e))
    
    async def _handle_snapshot_trigger_error(self, error: Dict[str, Any]):
        """Handle error that should trigger snapshot."""
        try:
            # Capture snapshot on trigger error
            if self.settings.enable_metrics:
                context_data = {
                    "site": error.get("site", "unknown"),
                    "module": error.get("module", "error_handler"),
                    "component": "snapshot_trigger",
                    "session_id": error.get("session_id", "unknown"),
                    "function": error.get("function", "snapshot_trigger_error"),
                    "error_type": error.get("error_type"),
                    "error_class": error.get("error_class"),
                    "error_message": error.get("error_message"),
                    "stack_trace": error.get("stack_trace"),
                    "trigger_reason": "error_occurred"
                }
                
                snapshot_id = await self._capture_error_snapshot(
                    trigger_source="error_triggered",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
        except Exception as e:
            logger.error("Error handling snapshot trigger error", error=str(e))
    
    async def _handle_global_exception(self, exc_type: type, exc_value: Exception, exc_traceback):
        """Handle global exception from exception hook."""
        await self._on_unhandled_exception(exc_type, exc_value, exc_traceback)
    
    async def _capture_error_snapshot(self, 
                                 trigger_source: str,
                                 context_data: Dict[str, Any]) -> Optional[str]:
        """Capture error-specific snapshot."""
        try:
            # Get active page
            page = await self._get_active_page()
            if not page:
                return None
            
            # Build snapshot context
            context = SnapshotContext(
                site=context_data.get("site", "unknown"),
                module=context_data.get("module", "error"),
                component=context_data.get("component", "handler"),
                session_id=context_data.get("session_id", "unknown"),
                function=context_data.get("function"),
                additional_metadata={
                    "trigger_source": trigger_source,
                    "error_integration": True,
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
                logger.info("Error snapshot captured", snapshot_id=snapshot_id, trigger_source=trigger_source)
                return snapshot_id
            
            return None
            
        except Exception as e:
            logger.error("Failed to capture error snapshot", error=str(e))
            return None
    
    async def _get_active_page(self) -> Optional[Any]:
        """Get the currently active page."""
        try:
            # Try to get page from error handler
            if self._error_handler and hasattr(self._error_handler, 'get_active_page'):
                return await self._error_handler.get_active_page()
            
            # Try to get page from browser manager
            from src.browser.manager import BrowserManager
            browser_manager = BrowserManager()
            if hasattr(browser_manager, 'get_active_page'):
                return await browser_manager.get_active_page()
            
            return None
            
        except Exception as e:
            logger.error("Error getting active page", error=str(e))
            return None
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of error integration."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "error_handler_available": self._error_handler is not None,
            "statistics": self.integration_stats,
            "critical_error_types": list(self.critical_error_types),
            "snapshot_trigger_errors": list(self.snapshot_trigger_errors),
            "global_exception_hook": True,
            "event_callbacks": {
                "error_occurred": len(self.on_error_occurred) > 0,
                "critical_error": len(self.on_critical_error) > 0,
                "unhandled_exception": len(self.on_unhandled_exception) > 0
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "integration_type": "error_handler",
            "initialized": self._initialized,
            "statistics": self.integration_stats,
            "error_breakdown": self.integration_stats["error_types"],
            "event_callbacks": {
                "error_occurred": len(self.on_error_occurred),
                "critical_error": len(self.on_critical_error),
                "unhandled_exception": len(self.on_unhandled_exception)
            }
        }
