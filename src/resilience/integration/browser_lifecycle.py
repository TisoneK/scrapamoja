"""
Browser Lifecycle Integration

Integrates resilience components with browser lifecycle management including
automatic resource monitoring, checkpointing, and abort policies during browser operations.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta

from ..browser.browser_manager import BrowserManager, BrowserMetrics, BrowserConfiguration
from ..resource.resource_manager import ResourceManager, Resource, ResourceType
from ..checkpoint.checkpoint_manager import CheckpointManager, Checkpoint, CheckpointType
from ..abort.abort_manager import AbortManager, AbortPolicy
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_integration_event


class BrowserLifecycleIntegration:
    """Integrates resilience components with browser lifecycle."""
    
    def __init__(self):
        """Initialize browser lifecycle integration."""
        self.logger = get_logger("browser_lifecycle_integration")
        
        # Component managers
        self.browser_manager: Optional[BrowserManager] = None
        self.resource_manager: Optional[ResourceManager] = None
        self.checkpoint_manager: Optional[CheckpointManager] = None
        self.abort_manager: Optional[AbortManager] = None
        
        # Integration state
        self.browser_resources: Dict[str, str] = {}  # browser_id -> resource_id
        self.browser_checkpoints: Dict[str, List[str]] = {}  # browser_id -> checkpoint_ids
        self.browser_abort_policies: Dict[str, List[str]] = {}  # browser_id -> policy_ids
        
        # Monitoring configuration
        self.auto_monitoring_enabled = True
        self.auto_checkpointing_enabled = True
        self.auto_abort_policies_enabled = True
        
        # Callbacks
        self.lifecycle_callbacks: List[Callable[[str, str, Dict[str, Any]], None]] = []
        
        # Integration state
        self._initialized = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(
        self,
        browser_manager: BrowserManager,
        resource_manager: ResourceManager,
        checkpoint_manager: CheckpointManager,
        abort_manager: AbortManager
    ) -> None:
        """Initialize the integration with component managers."""
        if self._initialized:
            return
        
        self.browser_manager = browser_manager
        self.resource_manager = resource_manager
        self.checkpoint_manager = checkpoint_manager
        self.abort_manager = abort_manager
        
        # Register callbacks with browser manager
        self.browser_manager.add_browser_callback(self._on_browser_metrics_updated)
        
        # Start monitoring task
        self._running = True
        self._monitoring_task = asyncio.create_task(self._integration_monitoring_loop())
        
        self._initialized = True
        
        self.logger.info(
            "Browser lifecycle integration initialized",
            event_type="browser_lifecycle_integration_initialized",
            correlation_id=get_correlation_id(),
            context={
                "auto_monitoring": self.auto_monitoring_enabled,
                "auto_checkpointing": self.auto_checkpointing_enabled,
                "auto_abort_policies": self.auto_abort_policies_enabled
            },
            component="browser_lifecycle_integration"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the integration gracefully."""
        if not self._initialized:
            return
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Unregister callbacks
        if self.browser_manager:
            self.browser_manager.remove_browser_callback(self._on_browser_metrics_updated)
        
        self._initialized = False
        
        self.logger.info(
            "Browser lifecycle integration shutdown",
            event_type="browser_lifecycle_integration_shutdown",
            correlation_id=get_correlation_id(),
            component="browser_lifecycle_integration"
        )
    
    async def on_browser_created(self, browser_id: str) -> None:
        """Handle browser creation event."""
        if not self._initialized:
            return
        
        try:
            # Create resource for browser
            if self.auto_monitoring_enabled:
                resource_id = await self._create_browser_resource(browser_id)
                self.browser_resources[browser_id] = resource_id
            
            # Create abort policies for browser
            if self.auto_abort_policies_enabled:
                policy_ids = await self._create_browser_abort_policies(browser_id)
                self.browser_abort_policies[browser_id] = policy_ids
            
            # Publish event
            await publish_integration_event(
                action="browser_integrated",
                browser_id=browser_id,
                context={
                    "resource_created": browser_id in self.browser_resources,
                    "abort_policies_created": browser_id in self.browser_abort_policies
                },
                component="browser_lifecycle_integration"
            )
            
            self.logger.info(
                f"Browser integrated: {browser_id}",
                event_type="browser_integrated",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "resource_id": self.browser_resources.get(browser_id),
                    "policy_count": len(self.browser_abort_policies.get(browser_id, []))
                },
                component="browser_lifecycle_integration"
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to integrate browser {browser_id}: {str(e)}",
                event_type="browser_integration_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_lifecycle_integration"
            )
    
    async def on_browser_shutdown(self, browser_id: str) -> None:
        """Handle browser shutdown event."""
        if not self._initialized:
            return
        
        try:
            # Create final checkpoint
            if self.auto_checkpointing_enabled:
                await self._create_final_checkpoint(browser_id)
            
            # Clean up resource
            if browser_id in self.browser_resources:
                resource_id = self.browser_resources[browser_id]
                await self.resource_manager.delete_resource(resource_id)
                del self.browser_resources[browser_id]
            
            # Clean up abort policies
            if browser_id in self.browser_abort_policies:
                for policy_id in self.browser_abort_policies[browser_id]:
                    await self.abort_manager.delete_policy(policy_id)
                del self.browser_abort_policies[browser_id]
            
            # Clean up checkpoints
            if browser_id in self.browser_checkpoints:
                del self.browser_checkpoints[browser_id]
            
            # Publish event
            await publish_integration_event(
                action="browser_deintegrated",
                browser_id=browser_id,
                context={},
                component="browser_lifecycle_integration"
            )
            
            self.logger.info(
                f"Browser deintegrated: {browser_id}",
                event_type="browser_deintegrated",
                correlation_id=get_correlation_id(),
                context={"browser_id": browser_id},
                component="browser_lifecycle_integration"
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to deintegrate browser {browser_id}: {str(e)}",
                event_type="browser_deintegration_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_lifecycle_integration"
            )
    
    async def create_browser_checkpoint(
        self,
        browser_id: str,
        reason: str = "manual"
    ) -> Optional[str]:
        """
        Create a checkpoint for a browser.
        
        Args:
            browser_id: Browser identifier
            reason: Reason for checkpoint
            
        Returns:
            Checkpoint ID or None if failed
        """
        if not self._initialized or not self.browser_manager:
            return None
        
        try:
            # Get browser metrics
            metrics = await self.browser_manager.get_browser_metrics(browser_id)
            if not metrics:
                return None
            
            # Create checkpoint data
            checkpoint_data = {
                "browser_id": browser_id,
                "metrics": metrics.to_dict(),
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason
            }
            
            # Create checkpoint
            checkpoint = Checkpoint(
                job_id=f"browser_{browser_id}",
                sequence_number=len(self.browser_checkpoints.get(browser_id, [])) + 1,
                checkpoint_type=CheckpointType.MANUAL,
                description=f"Browser checkpoint: {reason}"
            )
            
            checkpoint_id = await self.checkpoint_manager.create_checkpoint(checkpoint, checkpoint_data)
            
            # Track checkpoint
            if browser_id not in self.browser_checkpoints:
                self.browser_checkpoints[browser_id] = []
            self.browser_checkpoints[browser_id].append(checkpoint_id)
            
            self.logger.info(
                f"Browser checkpoint created: {browser_id} - {reason}",
                event_type="browser_checkpoint_created",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "checkpoint_id": checkpoint_id,
                    "reason": reason
                },
                component="browser_lifecycle_integration"
            )
            
            return checkpoint_id
            
        except Exception as e:
            self.logger.error(
                f"Failed to create browser checkpoint {browser_id}: {str(e)}",
                event_type="browser_checkpoint_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "reason": reason,
                    "error": str(e)
                },
                component="browser_lifecycle_integration"
            )
            return None
    
    async def restore_browser_checkpoint(
        self,
        browser_id: str,
        checkpoint_id: str
    ) -> bool:
        """
        Restore a browser from checkpoint.
        
        Args:
            browser_id: Browser identifier
            checkpoint_id: Checkpoint identifier
            
        Returns:
            True if restored successfully, False otherwise
        """
        if not self._initialized or not self.browser_manager:
            return False
        
        try:
            # Load checkpoint
            checkpoint = await self.checkpoint_manager.load_checkpoint(checkpoint_id)
            if not checkpoint:
                return False
            
            # Restore browser state (placeholder - would implement actual restoration)
            await self._restore_browser_state(browser_id, checkpoint.data)
            
            self.logger.info(
                f"Browser restored from checkpoint: {browser_id}",
                event_type="browser_restored",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "checkpoint_id": checkpoint_id
                },
                component="browser_lifecycle_integration"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to restore browser {browser_id} from checkpoint: {str(e)}",
                event_type="browser_restore_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "checkpoint_id": checkpoint_id,
                    "error": str(e)
                },
                component="browser_lifecycle_integration"
            )
            return False
    
    async def get_browser_integration_status(self, browser_id: str) -> Dict[str, Any]:
        """Get integration status for a browser."""
        return {
            "browser_id": browser_id,
            "resource_id": self.browser_resources.get(browser_id),
            "checkpoint_count": len(self.browser_checkpoints.get(browser_id, [])),
            "policy_count": len(self.browser_abort_policies.get(browser_id, [])),
            "auto_monitoring": self.auto_monitoring_enabled,
            "auto_checkpointing": self.auto_checkpointing_enabled,
            "auto_abort_policies": self.auto_abort_policies_enabled
        }
    
    def add_lifecycle_callback(self, callback: Callable[[str, str, Dict[str, Any]], None]) -> None:
        """Add a lifecycle event callback."""
        self.lifecycle_callbacks.append(callback)
    
    def remove_lifecycle_callback(self, callback: Callable) -> bool:
        """Remove a lifecycle event callback."""
        if callback in self.lifecycle_callbacks:
            self.lifecycle_callbacks.remove(callback)
            return True
        return False
    
    async def _create_browser_resource(self, browser_id: str) -> str:
        """Create a resource for browser monitoring."""
        resource_id = await self.resource_manager.create_resource(
            name=f"browser_{browser_id}",
            resource_type=ResourceType.BROWSER,
            description=f"Browser resource for {browser_id}"
        )
        return resource_id
    
    async def _create_browser_abort_policies(self, browser_id: str) -> List[str]:
        """Create abort policies for a browser."""
        from ..models.abort import (
            AbortCondition, AbortTrigger, AbortAction, AbortSeverity
        )
        
        policy_ids = []
        
        # High failure rate policy
        failure_rate_policy_id = await self.abort_manager.create_policy(
            name=f"browser_{browser_id}_high_failure_rate",
            conditions=[
                AbortCondition(
                    trigger_type=AbortTrigger.FAILURE_RATE,
                    threshold=0.5,
                    time_window_seconds=600,
                    severity=AbortSeverity.HIGH,
                    description="Browser failure rate > 50% over 10 minutes"
                )
            ],
            action=AbortAction.SAVE_STATE_AND_STOP,
            description=f"High failure rate policy for browser {browser_id}",
            priority=100
        )
        policy_ids.append(failure_rate_policy_id)
        
        # Error threshold policy
        error_threshold_policy_id = await self.abort_manager.create_policy(
            name=f"browser_{browser_id}_error_threshold",
            conditions=[
                AbortCondition(
                    trigger_type=AbortTrigger.ERROR_THRESHOLD,
                    threshold=10,
                    time_window_seconds=300,
                    severity=AbortSeverity.MEDIUM,
                    description="Browser error count > 10 in 5 minutes"
                )
            ],
            action=AbortAction.GRACEFUL_SHUTDOWN,
            description=f"Error threshold policy for browser {browser_id}",
            priority=90
        )
        policy_ids.append(error_threshold_policy_id)
        
        return policy_ids
    
    async def _create_final_checkpoint(self, browser_id: str) -> Optional[str]:
        """Create a final checkpoint before browser shutdown."""
        return await self.create_browser_checkpoint(browser_id, "browser_shutdown")
    
    async def _restore_browser_state(self, browser_id: str, checkpoint_data: Dict[str, Any]) -> None:
        """Restore browser state from checkpoint data."""
        # This would implement actual browser state restoration
        # For now, just log the restoration
        pass
    
    def _on_browser_metrics_updated(self, browser_id: str, metrics: BrowserMetrics) -> None:
        """Handle browser metrics update."""
        if not self._initialized:
            return
        
        try:
            # Update resource metrics
            if browser_id in self.browser_resources:
                resource_id = self.browser_resources[browser_id]
                # This would update the resource with browser metrics
                # For now, just log the update
                pass
            
            # Record operation for abort evaluation
            if self.abort_manager:
                asyncio.create_task(
                    self.abort_manager.record_operation(
                        operation_id=f"browser_{browser_id}_{int(time.time())}",
                        success=metrics.state.value == "running",
                        error_type="browser_error" if metrics.error_count > 0 else None,
                        response_time=metrics.page_load_time_avg
                    )
                )
            
        except Exception as e:
            self.logger.error(
                f"Error handling browser metrics update for {browser_id}: {str(e)}",
                event_type="browser_metrics_update_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_lifecycle_integration"
            )
    
    async def _integration_monitoring_loop(self) -> None:
        """Main integration monitoring loop."""
        while self._running:
            try:
                # Monitor all integrated browsers
                if self.browser_manager:
                    browsers = await self.browser_manager.list_browsers()
                    
                    for browser in browsers:
                        browser_id = browser.id
                        
                        # Auto-checkpointing
                        if self.auto_checkpointing_enabled:
                            await self._auto_checkpoint_browser(browser_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in integration monitoring loop: {str(e)}",
                    event_type="integration_monitoring_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="browser_lifecycle_integration"
                )
                await asyncio.sleep(60)
    
    async def _auto_checkpoint_browser(self, browser_id: str) -> None:
        """Create automatic checkpoint for browser."""
        # Check if browser needs checkpointing
        last_checkpoint_time = None
        if browser_id in self.browser_checkpoints and self.browser_checkpoints[browser_id]:
            # Get the most recent checkpoint time
            # This would need to be implemented to get checkpoint timestamps
            pass
        
        # Create checkpoint if needed (e.g., every 30 minutes)
        # For now, just skip auto-checkpointing
        pass


# Global browser lifecycle integration instance
_browser_lifecycle_integration = BrowserLifecycleIntegration()


def get_browser_lifecycle_integration() -> BrowserLifecycleIntegration:
    """Get the global browser lifecycle integration instance."""
    return _browser_lifecycle_integration
