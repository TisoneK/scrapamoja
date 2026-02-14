"""
Scraper Snapshot - Hooks snapshot system into scraper engine.

This module integrates the snapshot system with the scraper engine
to automatically capture snapshots during scraping operations.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from ..manager import SnapshotManager
from ..models import SnapshotContext, SnapshotConfig, SnapshotMode
from ..config import get_settings


@dataclass
class ScraperEvent:
    """Scraper event data for snapshot triggering."""
    event_type: str
    site: str
    operation: str
    session_id: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScraperSnapshot:
    """Integrates snapshot system with scraper engine."""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        """Initialize scraper snapshot handler."""
        self.snapshot_manager = snapshot_manager
        self.settings = get_settings()
        self._scraper_engine = None
        self._initialized = False
        
        # Event callbacks
        self.on_scraping_started: List[Callable] = []
        self.on_scraping_completed: List[Callable] = []
        self.on_scraping_error: List[Callable] = []
        self.on_data_extraction_failed: List[Callable] = []
        self.on_site_navigation_failed: List[Callable] = []
        
        # Statistics
        self.integration_stats = {
            "scraping_operations": 0,
            "snapshots_captured": 0,
            "scraping_errors": 0,
            "extraction_failures": 0,
            "navigation_failures": 0
        }
    
    async def initialize(self):
        """Initialize scraper snapshot handler."""
        try:
            # Import scraper engine to avoid circular imports
            # Note: This would need to be implemented based on your scraper architecture
            # For now, we'll create a placeholder that can be hooked into
            
            self._initialized = True
            print("✅ Scraper snapshot handler initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize scraper snapshot handler: {e}")
            raise
    
    async def handle_selector_failure(self, selector: str, failure_data: Dict[str, Any]):
        """Handle selector failure from scraper."""
        try:
            self.integration_stats["scraping_errors"] += 1
            
            # Capture snapshot on selector failure in scraper context
            if self.settings.enable_metrics:
                context_data = {
                    "site": failure_data.get("site", "unknown"),
                    "module": "scraper_engine",
                    "component": "selector_handler",
                    "session_id": failure_data.get("session_id", "unknown"),
                    "function": "scraper_selector_failed",
                    "selector": selector,
                    "error_type": failure_data.get("error_type"),
                    "error_message": failure_data.get("error_message"),
                    "page_url": failure_data.get("page_url"),
                    "scraping_context": failure_data.get("context")
                }
                
                snapshot_id = await self._capture_scraper_snapshot(
                    trigger_source="scraper_selector_failure",
                    context_data=context_data
                )
                
                if snapshot_id:
                    self.integration_stats["snapshots_captured"] += 1
            
            # Notify callbacks
            for callback in self.on_scraping_error:
                await callback(selector, failure_data)
                
        except Exception as e:
            print(f"❌ Error handling scraper selector failure: {e}")
    
    async def _capture_scraper_snapshot(self, 
                                   trigger_source: str,
                                   context_data: Dict[str, Any]) -> Optional[str]:
        """Capture scraper-specific snapshot."""
        try:
            # Get active page
            page = await self._get_active_page()
            if not page:
                return None
            
            # Build snapshot context
            context = SnapshotContext(
                site=context_data.get("site", "unknown"),
                module=context_data.get("module", "scraper"),
                component=context_data.get("component", "engine"),
                session_id=context_data.get("session_id", "unknown"),
                function=context_data.get("function"),
                additional_metadata={
                    "trigger_source": trigger_source,
                    "scraper_integration": True,
                    "timestamp": datetime.now().isoformat(),
                    **context_data
                }
            )
            
            # Build snapshot config
            selector = context_data.get("selector")
            # Use FULL_PAGE mode if no selector is provided
            mode = SnapshotMode.FULL_PAGE if not selector else SnapshotMode.SELECTOR
            
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
                snapshot_id = bundle.content_hash[:8]
                print(f"📸 Scraper snapshot captured: {snapshot_id} from {trigger_source}")
                return snapshot_id
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to capture scraper snapshot: {e}")
            return None
    
    async def _get_active_page(self) -> Optional[Any]:
        """Get the currently active page."""
        try:
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
        """Get health status of scraper integration."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "scraper_engine_available": self._scraper_engine is not None,
            "statistics": self.integration_stats,
            "event_callbacks": {
                "scraping_started": len(self.on_scraping_started) > 0,
                "scraping_completed": len(self.on_scraping_completed) > 0,
                "scraping_error": len(self.on_scraping_error) > 0,
                "data_extraction_failed": len(self.on_data_extraction_failed) > 0,
                "site_navigation_failed": len(self.on_site_navigation_failed) > 0
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "integration_type": "scraper_engine",
            "initialized": self._initialized,
            "statistics": self.integration_stats,
            "event_callbacks": {
                "scraping_started": len(self.on_scraping_started),
                "scraping_completed": len(self.on_scraping_completed),
                "scraping_error": len(self.on_scraping_error),
                "data_extraction_failed": len(self.on_data_extraction_failed),
                "site_navigation_failed": len(self.on_site_navigation_failed)
            }
        }
