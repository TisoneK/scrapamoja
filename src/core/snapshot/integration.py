"""
Browser integration layer for the snapshot system.

This module provides seamless integration with existing browser automation,
including session management, page extraction, and error handling hooks.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import traceback

from src.observability.logger import get_logger
from .models import (
    SnapshotContext, SnapshotConfig, SnapshotBundle, SnapshotMode,
    SnapshotError
)
from .capture import SnapshotCapture
from .triggers import TriggerManager
from .config import get_settings
from .metrics import MetricsCollector

# Module logger
logger = get_logger(__name__)


class BrowserSnapshotIntegration:
    """Integrates snapshot system with browser automation."""
    
    def __init__(self, 
                 snapshot_capture: SnapshotCapture,
                 trigger_manager: TriggerManager,
                 metrics_collector: MetricsCollector):
        """Initialize browser integration."""
        self.snapshot_capture = snapshot_capture
        self.trigger_manager = trigger_manager
        self.metrics_collector = metrics_collector
        self.settings = get_settings()
    
    async def capture_snapshot_on_selector_failure(
        self,
        browser_manager: Any,
        site: str,
        module: str,
        component: str,
        session_id: str,
        selector: str,
        matched_count: int = 0,
        page: Optional[Any] = None
    ) -> bool:
        """Capture snapshot on selector failure."""
        try:
            # Check if snapshots are enabled
            if not self.settings.enable_metrics:
                return False
            
            # Get page from browser manager if not provided
            if page is None:
                page = await self._extract_page_from_browser_manager(browser_manager)
                if page is None:
                    return False
            
            # Create trigger context
            trigger_context = {
                "site": site,
                "module": module,
                "component": component,
                "session_id": session_id,
                "selector": selector,
                "matched_count": matched_count,
                "page_url": await page.url() if page else None,
                "function": "selector_execution"
            }
            
            # Evaluate triggers
            activated_triggers = await self.trigger_manager.evaluate_triggers(trigger_context)
            
            # Capture snapshots for activated triggers
            success_count = 0
            for trigger_data in activated_triggers:
                if trigger_data["trigger_type"] == "selector_failure":
                    try:
                        bundle = await self.snapshot_capture.capture_snapshot(
                            page=page,
                            context=trigger_data["snapshot_context"],
                            config=trigger_data["snapshot_config"]
                        )
                        success_count += 1
                        
                        # Record metric
                        self.metrics_collector.record_metric(
                            operation="selector_failure_snapshot",
                            duration_ms=0,  # Will be set by timer
                            success=True
                        )
                        
                    except Exception as e:
                        # Record error metric
                        self.metrics_collector.record_metric(
                            operation="selector_failure_snapshot",
                            duration_ms=0,
                            success=False,
                            error_type=type(e).__name__
                        )
                        logger.warning("Failed to capture selector failure snapshot", error=str(e))
            
            return success_count > 0
            
        except Exception as e:
            logger.error("Error in selector failure snapshot integration", error=str(e))
            return False
    
    async def capture_snapshot_on_retry_exhaustion(
        self,
        browser_manager: Any,
        site: str,
        module: str,
        component: str,
        session_id: str,
        operation: str,
        retry_count: int,
        max_retries: int,
        last_error: Optional[str] = None,
        page: Optional[Any] = None
    ) -> bool:
        """Capture snapshot on retry exhaustion."""
        try:
            # Check if snapshots are enabled
            if not self.settings.enable_metrics:
                return False
            
            # Get page from browser manager if not provided
            if page is None:
                page = await self._extract_page_from_browser_manager(browser_manager)
                if page is None:
                    return False
            
            # Create trigger context
            trigger_context = {
                "site": site,
                "module": module,
                "component": component,
                "session_id": session_id,
                "operation": operation,
                "retry_count": retry_count,
                "max_retries": max_retries,
                "last_error": last_error,
                "page_url": await page.url() if page else None,
                "function": "retry_operation"
            }
            
            # Evaluate triggers
            activated_triggers = await self.trigger_manager.evaluate_triggers(trigger_context)
            
            # Capture snapshots for activated triggers
            success_count = 0
            for trigger_data in activated_triggers:
                if trigger_data["trigger_type"] == "retry_exhaustion":
                    try:
                        bundle = await self.snapshot_capture.capture_snapshot(
                            page=page,
                            context=trigger_data["snapshot_context"],
                            config=trigger_data["snapshot_config"]
                        )
                        success_count += 1
                        
                        # Record metric
                        self.metrics_collector.record_metric(
                            operation="retry_exhaustion_snapshot",
                            duration_ms=0,
                            success=True
                        )
                        
                    except Exception as e:
                        # Record error metric
                        self.metrics_collector.record_metric(
                            operation="retry_exhaustion_snapshot",
                            duration_ms=0,
                            success=False,
                            error_type=type(e).__name__
                        )
                        logger.warning("Failed to capture retry exhaustion snapshot", error=str(e))
            
            return success_count > 0
            
        except Exception as e:
            logger.error("Error in retry exhaustion snapshot integration", error=str(e))
            return False
    
    async def capture_snapshot_on_timeout(
        self,
        browser_manager: Any,
        site: str,
        module: str,
        component: str,
        session_id: str,
        operation: str,
        timeout_duration: float,
        partial_results: Optional[Dict[str, Any]] = None,
        page: Optional[Any] = None
    ) -> bool:
        """Capture snapshot on timeout."""
        try:
            # Check if snapshots are enabled
            if not self.settings.enable_metrics:
                return False
            
            # Get page from browser manager if not provided
            if page is None:
                page = await self._extract_page_from_browser_manager(browser_manager)
                if page is None:
                    return False
            
            # Create trigger context
            trigger_context = {
                "site": site,
                "module": module,
                "component": component,
                "session_id": session_id,
                "operation": operation,
                "timeout_duration": timeout_duration,
                "partial_results": partial_results,
                "page_url": await page.url() if page else None,
                "function": "timeout_operation",
                "timed_out": True
            }
            
            # Evaluate triggers
            activated_triggers = await self.trigger_manager.evaluate_triggers(trigger_context)
            
            # Capture snapshots for activated triggers
            success_count = 0
            for trigger_data in activated_triggers:
                if trigger_data["trigger_type"] == "timeout":
                    try:
                        bundle = await self.snapshot_capture.capture_snapshot(
                            page=page,
                            context=trigger_data["snapshot_context"],
                            config=trigger_data["snapshot_config"]
                        )
                        success_count += 1
                        
                        # Record metric
                        self.metrics_collector.record_metric(
                            operation="timeout_snapshot",
                            duration_ms=0,
                            success=True
                        )
                        
                    except Exception as e:
                        # Record error metric
                        self.metrics_collector.record_metric(
                            operation="timeout_snapshot",
                            duration_ms=0,
                            success=False,
                            error_type=type(e).__name__
                        )
                        logger.warning("Failed to capture timeout snapshot", error=str(e))
            
            return success_count > 0
            
        except Exception as e:
            logger.error("Error in timeout snapshot integration", error=str(e))
            return False
    
    async def capture_snapshot_on_extraction_mismatch(
        self,
        browser_manager: Any,
        site: str,
        module: str,
        component: str,
        session_id: str,
        selector: str,
        extracted_data: Dict[str, Any],
        expected_schema: Dict[str, Any],
        validation_errors: List[str],
        page: Optional[Any] = None
    ) -> bool:
        """Capture snapshot on extraction validation failure."""
        try:
            # Check if snapshots are enabled
            if not self.settings.enable_metrics:
                return False
            
            # Get page from browser manager if not provided
            if page is None:
                page = await self._extract_page_from_browser_manager(browser_manager)
                if page is None:
                    return False
            
            # Create trigger context
            trigger_context = {
                "site": site,
                "module": module,
                "component": component,
                "session_id": session_id,
                "selector": selector,
                "extracted_data": extracted_data,
                "expected_schema": expected_schema,
                "validation_errors": validation_errors,
                "page_url": await page.url() if page else None,
                "function": "extract_and_validate",
                "validation_passed": False
            }
            
            # Evaluate triggers
            activated_triggers = await self.trigger_manager.evaluate_triggers(trigger_context)
            
            # Capture snapshots for activated triggers
            success_count = 0
            for trigger_data in activated_triggers:
                if trigger_data["trigger_type"] == "extraction_mismatch":
                    try:
                        bundle = await self.snapshot_capture.capture_snapshot(
                            page=page,
                            context=trigger_data["snapshot_context"],
                            config=trigger_data["snapshot_config"]
                        )
                        success_count += 1
                        
                        # Record metric
                        self.metrics_collector.record_metric(
                            operation="extraction_mismatch_snapshot",
                            duration_ms=0,
                            success=True
                        )
                        
                    except Exception as e:
                        # Record error metric
                        self.metrics_collector.record_metric(
                            operation="extraction_mismatch_snapshot",
                            duration_ms=0,
                            success=False,
                            error_type=type(e).__name__
                        )
                        logger.warning("Failed to capture extraction mismatch snapshot", error=str(e))
            
            return success_count > 0
            
        except Exception as e:
            logger.error("Error in extraction mismatch snapshot integration", error=str(e))
            return False
    
    async def capture_manual_snapshot(
        self,
        browser_manager: Any,
        site: str,
        module: str,
        component: str,
        session_id: str,
        mode: Union[SnapshotMode, str] = SnapshotMode.FULL_PAGE,
        reason: str = "User initiated",
        selector: Optional[str] = None,
        page: Optional[Any] = None
    ) -> Optional[SnapshotBundle]:
        """Capture manual snapshot."""
        try:
            # Check if snapshots are enabled
            if not self.settings.enable_metrics:
                return None
            
            # Get page from browser manager if not provided
            if page is None:
                page = await self._extract_page_from_browser_manager(browser_manager)
                if page is None:
                    return None
            
            # Create manual trigger context
            trigger_context = {
                "site": site,
                "module": module,
                "component": component,
                "session_id": session_id,
                "mode": mode,
                "reason": reason,
                "selector": selector,
                "page_url": await page.url() if page else None,
                "manual_trigger": True
            }
            
            # Get manual trigger
            manual_trigger = self.trigger_manager.get_trigger("manual")
            if not manual_trigger:
                # Add manual trigger if not present
                from .triggers import ManualTrigger
                manual_trigger = ManualTrigger()
                self.trigger_manager.add_trigger(manual_trigger)
            
            # Check if manual trigger should activate
            if await manual_trigger.should_trigger(trigger_context):
                context = await manual_trigger.get_snapshot_context(trigger_context)
                config = await manual_trigger.get_snapshot_config(trigger_context)
                
                # Start timer
                timer = self.metrics_collector.start_operation_timer("manual_snapshot")
                
                try:
                    # Capture snapshot
                    bundle = await self.snapshot_capture.capture_snapshot(
                        page=page,
                        context=context,
                        config=config
                    )
                    
                    # Record success metric
                    timer(success=True)
                    
                    return bundle
                    
                except Exception as e:
                    # Record error metric
                    timer(success=False, error_type=type(e).__name__)
                    raise
            
            return None
            
        except Exception as e:
            logger.error("Error in manual snapshot capture", error=str(e))
            return None
    
    async def _extract_page_from_browser_manager(self, browser_manager: Any) -> Optional[Any]:
        """Extract page object from browser manager."""
        try:
            # Try different methods to get the page
            if hasattr(browser_manager, 'page'):
                return browser_manager.page
            elif hasattr(browser_manager, 'get_current_page'):
                return await browser_manager.get_current_page()
            elif hasattr(browser_manager, 'current_page'):
                return browser_manager.current_page
            elif hasattr(browser_manager, 'pages') and browser_manager.pages:
                return browser_manager.pages[-1]  # Get last page
            else:
                logger.warning("Could not extract page from browser manager")
                return None
                
        except Exception as e:
            logger.error("Error extracting page from browser manager", error=str(e))
            return None
    
    async def validate_session_status(self, browser_manager: Any, session_id: str) -> bool:
        """Validate browser session status."""
        try:
            # Check if session is still active
            if hasattr(browser_manager, 'is_session_active'):
                return await browser_manager.is_session_active(session_id)
            elif hasattr(browser_manager, 'session_status'):
                status = await browser_manager.session_status(session_id)
                return status in ['active', 'connected']
            else:
                # Default to True if we can't check
                return True
                
        except Exception as e:
            logger.error("Error validating session status", error=str(e))
            return False
    
    async def handle_session_termination(self, browser_manager: Any, session_id: str) -> bool:
        """Handle graceful session termination."""
        try:
            # Try to capture final snapshot before session termination
            page = await self._extract_page_from_browser_manager(browser_manager)
            if page:
                # Create context for session termination
                context = SnapshotContext(
                    site="session_termination",
                    module="session_management",
                    component="cleanup",
                    session_id=session_id,
                    function="session_termination",
                    additional_metadata={
                        "trigger_type": "session_termination",
                        "termination_reason": "graceful_shutdown"
                    }
                )
                
                # Capture minimal snapshot
                bundle = await self.snapshot_capture.capture_minimal_snapshot(page, context)
                return bundle is not None
            
            return True
            
        except Exception as e:
            logger.error("Error handling session termination", error=str(e))
            return False
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "trigger_statistics": self.trigger_manager.get_trigger_statistics(),
            "settings": self.settings.to_dict(),
            "snapshot_metrics": self.metrics_collector.get_snapshot_metrics()
        }
