"""
Resource Manager

Manages resource lifecycle control including monitoring, threshold checking,
automatic restarts, and cleanup with support for multiple resource types.
"""

import asyncio
import psutil
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict

from ..interfaces import IResilienceManager
from ..models.resource import (
    Resource, ResourceType, ResourceStatus, ResourceAction,
    ResourceConfiguration, ResourceMetrics, ResourceSummary,
    DEFAULT_MEMORY_CONFIG, DEFAULT_BROWSER_CONFIG, DEFAULT_CPU_CONFIG
)
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_resource_event
from ..config import get_configuration


class ResourceManager(IResilienceManager):
    """Manages resource lifecycle control and monitoring."""
    
    def __init__(self):
        """Initialize resource manager."""
        self.logger = get_logger("resource_manager")
        self.resources: Dict[str, Resource] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.resource_callbacks: List[Callable] = []
        
        # Monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.history_retention_hours = 24
        self.max_history_points = 1000
        
        # Resource history
        self.resource_history: Dict[str, List[ResourceMetrics]] = defaultdict(list)
        
        # Restart tracking
        self.restart_history: Dict[str, List[datetime]] = defaultdict(list)
        
        self._initialized = False
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the resource manager."""
        if self._initialized:
            return
        
        # Create default resources
        await self._create_default_resources()
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self._initialized = True
        
        self.logger.info(
            "Resource manager initialized",
            event_type="resource_manager_initialized",
            correlation_id=get_correlation_id(),
            context={
                "monitoring_interval": self.monitoring_interval,
                "default_resources": len(self.resources)
            },
            component="resource_manager"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the resource manager gracefully."""
        if not self._initialized:
            return
        
        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Cancel individual monitoring tasks
        for resource_id, task in self.monitoring_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.monitoring_tasks.clear()
        self.resources.clear()
        self.resource_history.clear()
        self.restart_history.clear()
        
        self._initialized = False
        
        self.logger.info(
            "Resource manager shutdown",
            event_type="resource_manager_shutdown",
            correlation_id=get_correlation_id(),
            component="resource_manager"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "total_resources": len(self.resources),
            "monitoring_tasks": len(self.monitoring_tasks),
            "healthy_resources": sum(1 for r in self.resources.values() if r.is_healthy()),
            "critical_resources": sum(1 for r in self.resources.values() if r.status == ResourceStatus.CRITICAL),
            "monitoring_interval": self.monitoring_interval
        }
    
    async def create_resource(
        self,
        name: str,
        resource_type: ResourceType,
        configuration: Optional[ResourceConfiguration] = None,
        description: str = ""
    ) -> str:
        """
        Create a new resource.
        
        Args:
            name: Resource name
            resource_type: Type of resource
            configuration: Resource configuration
            description: Resource description
            
        Returns:
            Resource ID
        """
        try:
            # Create resource
            resource = Resource(
                name=name,
                resource_type=resource_type,
                description=description
            )
            
            # Set configuration
            if configuration:
                resource.configuration = configuration
            else:
                resource.configuration = self._get_default_configuration(resource_type)
            
            # Add to resources
            self.resources[resource.id] = resource
            
            # Start monitoring if enabled
            if resource.configuration.monitoring_enabled:
                await self._start_resource_monitoring(resource)
            
            # Publish event
            await publish_resource_event(
                action="created",
                resource_id=resource.id,
                resource_type=resource_type.value,
                context={
                    "name": name,
                    "description": description
                },
                component="resource_manager"
            )
            
            self.logger.info(
                f"Resource created: {name} ({resource_type.value})",
                event_type="resource_created",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource.id,
                    "name": name,
                    "resource_type": resource_type.value
                },
                component="resource_manager"
            )
            
            return resource.id
            
        except Exception as e:
            self.logger.error(
                f"Failed to create resource {name}: {str(e)}",
                event_type="resource_creation_error",
                correlation_id=get_correlation_id(),
                context={
                    "name": name,
                    "resource_type": resource_type.value,
                    "error": str(e)
                },
                component="resource_manager"
            )
            raise
    
    async def get_resource(self, resource_id: str) -> Optional[Resource]:
        """
        Get a resource by ID.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            Resource or None if not found
        """
        return self.resources.get(resource_id)
    
    async def list_resources(
        self,
        resource_type: Optional[ResourceType] = None,
        status: Optional[ResourceStatus] = None
    ) -> List[Resource]:
        """
        List resources with optional filtering.
        
        Args:
            resource_type: Filter by resource type
            status: Filter by status
            
        Returns:
            List of resources
        """
        resources = list(self.resources.values())
        
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        
        if status:
            resources = [r for r in resources if r.status == status]
        
        return resources
    
    async def update_resource_metrics(
        self,
        resource_id: str,
        metrics: ResourceMetrics
    ) -> bool:
        """
        Update resource metrics.
        
        Args:
            resource_id: Resource identifier
            metrics: New metrics
            
        Returns:
            True if updated successfully, False if not found
        """
        resource = self.resources.get(resource_id)
        if not resource:
            return False
        
        # Update metrics
        resource.update_metrics(metrics)
        
        # Store in history
        self._store_metrics_history(resource_id, metrics)
        
        # Check thresholds and take action if needed
        await self._check_thresholds_and_take_action(resource)
        
        # Notify callbacks
        self._notify_callbacks(resource)
        
        return True
    
    async def restart_resource(
        self,
        resource_id: str,
        reason: str = "manual"
    ) -> bool:
        """
        Restart a resource.
        
        Args:
            resource_id: Resource identifier
            reason: Reason for restart
            
        Returns:
            True if restarted successfully, False if not found or not allowed
        """
        resource = self.resources.get(resource_id)
        if not resource:
            return False
        
        # Check if restart is allowed
        if not resource.can_restart():
            self.logger.warning(
                f"Resource restart not allowed: {resource.name}",
                event_type="resource_restart_blocked",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource_id,
                    "reason": reason,
                    "restart_count": resource.restart_count,
                    "last_restart": resource.last_restart.isoformat() if resource.last_restart else None
                },
                component="resource_manager"
            )
            return False
        
        try:
            # Update status
            resource.update_status(ResourceStatus.RESTARTING)
            resource.record_action(ResourceAction.RESTART)
            
            # Perform restart based on resource type
            await self._perform_resource_restart(resource)
            
            # Update status
            resource.update_status(ResourceStatus.HEALTHY)
            
            # Record restart in history
            self.restart_history[resource_id].append(datetime.utcnow())
            
            # Publish event
            await publish_resource_event(
                action="restarted",
                resource_id=resource_id,
                resource_type=resource.resource_type.value,
                context={
                    "reason": reason,
                    "restart_count": resource.restart_count
                },
                component="resource_manager"
            )
            
            self.logger.info(
                f"Resource restarted: {resource.name} ({reason})",
                event_type="resource_restarted",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource_id,
                    "name": resource.name,
                    "reason": reason,
                    "restart_count": resource.restart_count
                },
                component="resource_manager"
            )
            
            return True
            
        except Exception as e:
            resource.update_status(ResourceStatus.FAILED)
            
            self.logger.error(
                f"Failed to restart resource {resource.name}: {str(e)}",
                event_type="resource_restart_error",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource_id,
                    "name": resource.name,
                    "reason": reason,
                    "error": str(e)
                },
                component="resource_manager"
            )
            
            return False
    
    async def cleanup_resource(
        self,
        resource_id: str
    ) -> bool:
        """
        Clean up a resource.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            True if cleaned up successfully, False if not found
        """
        resource = self.resources.get(resource_id)
        if not resource:
            return False
        
        try:
            # Perform cleanup based on resource type
            await self._perform_resource_cleanup(resource)
            
            # Record action
            resource.record_action(ResourceAction.CLEANUP)
            
            # Publish event
            await publish_resource_event(
                action="cleaned",
                resource_id=resource_id,
                resource_type=resource.resource_type.value,
                context={},
                component="resource_manager"
            )
            
            self.logger.info(
                f"Resource cleaned: {resource.name}",
                event_type="resource_cleaned",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource_id,
                    "name": resource.name
                },
                component="resource_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup resource {resource.name}: {str(e)}",
                event_type="resource_cleanup_error",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource_id,
                    "name": resource.name,
                    "error": str(e)
                },
                component="resource_manager"
            )
            
            return False
    
    async def delete_resource(self, resource_id: str) -> bool:
        """
        Delete a resource.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        resource = self.resources.get(resource_id)
        if not resource:
            return False
        
        try:
            # Stop monitoring
            if resource_id in self.monitoring_tasks:
                self.monitoring_tasks[resource_id].cancel()
                try:
                    await self.monitoring_tasks[resource_id]
                except asyncio.CancelledError:
                    pass
                del self.monitoring_tasks[resource_id]
            
            # Cleanup resource
            await self.cleanup_resource(resource_id)
            
            # Remove from resources
            del self.resources[resource_id]
            
            # Clean up history
            if resource_id in self.resource_history:
                del self.resource_history[resource_id]
            
            if resource_id in self.restart_history:
                del self.restart_history[resource_id]
            
            # Publish event
            await publish_resource_event(
                action="deleted",
                resource_id=resource_id,
                resource_type=resource.resource_type.value,
                context={},
                component="resource_manager"
            )
            
            self.logger.info(
                f"Resource deleted: {resource.name}",
                event_type="resource_deleted",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource_id,
                    "name": resource.name
                },
                component="resource_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to delete resource {resource.name}: {str(e)}",
                event_type="resource_deletion_error",
                correlation_id=get_correlation_id(),
                context={
                    "resource_id": resource_id,
                    "name": resource.name,
                    "error": str(e)
                },
                component="resource_manager"
            )
            
            return False
    
    async def get_resource_summary(self) -> ResourceSummary:
        """
        Get summary of all resources.
        
        Returns:
            Resource summary
        """
        summary = ResourceSummary()
        summary.total_resources = len(self.resources)
        
        for resource in self.resources.values():
            if resource.status == ResourceStatus.HEALTHY:
                summary.healthy_resources += 1
            elif resource.status == ResourceStatus.WARNING:
                summary.warning_resources += 1
            elif resource.status == ResourceStatus.CRITICAL:
                summary.critical_resources += 1
            elif resource.status == ResourceStatus.EXHAUSTED:
                summary.exhausted_resources += 1
            elif resource.status == ResourceStatus.RESTARTING:
                summary.restarting_resources += 1
            elif resource.status == ResourceStatus.RECOVERING:
                summary.recovering_resources += 1
            elif resource.status == ResourceStatus.FAILED:
                summary.failed_resources += 1
        
        return summary
    
    async def get_resource_history(
        self,
        resource_id: str,
        limit: Optional[int] = None
    ) -> List[ResourceMetrics]:
        """
        Get resource metrics history.
        
        Args:
            resource_id: Resource identifier
            limit: Maximum number of history points to return
            
        Returns:
            List of metrics history
        """
        history = self.resource_history.get(resource_id, [])
        
        if limit:
            history = history[-limit:]
        
        return history.copy()
    
    def add_resource_callback(self, callback: Callable[[Resource], None]) -> None:
        """
        Add a resource change callback.
        
        Args:
            callback: Function that receives Resource object
        """
        self.resource_callbacks.append(callback)
    
    def remove_resource_callback(self, callback: Callable) -> bool:
        """
        Remove a resource change callback.
        
        Args:
            callback: Callback function to remove
            
        Returns:
            True if removed, False if not found
        """
        if callback in self.resource_callbacks:
            self.resource_callbacks.remove(callback)
            return True
        return False
    
    async def _create_default_resources(self) -> None:
        """Create default resources."""
        # Memory resource
        await self.create_resource(
            name="system_memory",
            resource_type=ResourceType.MEMORY,
            configuration=DEFAULT_MEMORY_CONFIG,
            description="System memory monitoring"
        )
        
        # CPU resource
        await self.create_resource(
            name="system_cpu",
            resource_type=ResourceType.CPU,
            configuration=DEFAULT_CPU_CONFIG,
            description="System CPU monitoring"
        )
        
        # Browser resource (will be created when browser is initialized)
        # This is a placeholder - actual browser resources will be created dynamically
    
    async def _start_resource_monitoring(self, resource: Resource) -> None:
        """Start monitoring for a specific resource."""
        if resource.id in self.monitoring_tasks:
            return
        
        task = asyncio.create_task(self._monitor_resource(resource))
        self.monitoring_tasks[resource.id] = task
    
    async def _monitor_resource(self, resource: Resource) -> None:
        """Monitor a specific resource."""
        while True:
            try:
                # Get current metrics based on resource type
                metrics = await self._get_resource_metrics(resource)
                
                # Update resource metrics
                await self.update_resource_metrics(resource.id, metrics)
                
                # Wait for next monitoring interval
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error monitoring resource {resource.name}: {str(e)}",
                    event_type="resource_monitoring_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "resource_id": resource.id,
                        "name": resource.name,
                        "error": str(e)
                    },
                    component="resource_manager"
                )
                
                # Wait before retrying
                await asyncio.sleep(self.monitoring_interval)
    
    async def _get_resource_metrics(self, resource: Resource) -> ResourceMetrics:
        """Get current metrics for a resource."""
        if resource.resource_type == ResourceType.MEMORY:
            memory = psutil.virtual_memory()
            return ResourceMetrics(
                current_value=memory.percent,
                peak_value=memory.percent,  # Would need to track over time
                average_value=memory.percent,  # Would need to calculate from history
                minimum_value=0.0,
                maximum_value=100.0,
                unit="percent",
                samples_count=1,
                trend="stable"
            )
        
        elif resource.resource_type == ResourceType.CPU:
            cpu_percent = psutil.cpu_percent(interval=1)
            return ResourceMetrics(
                current_value=cpu_percent,
                peak_value=cpu_percent,
                average_value=cpu_percent,
                minimum_value=0.0,
                maximum_value=100.0,
                unit="percent",
                samples_count=1,
                trend="stable"
            )
        
        elif resource.resource_type == ResourceType.BROWSER:
            # Browser-specific metrics would be implemented here
            # For now, return placeholder metrics
            return ResourceMetrics(
                current_value=50.0,
                peak_value=50.0,
                average_value=50.0,
                minimum_value=0.0,
                maximum_value=100.0,
                unit="percent",
                samples_count=1,
                trend="stable"
            )
        
        else:
            # Default metrics for unknown resource types
            return ResourceMetrics()
    
    async def _check_thresholds_and_take_action(self, resource: Resource) -> None:
        """Check thresholds and take appropriate action."""
        if not resource.configuration or not resource.configuration.thresholds.enabled:
            return
        
        # Check if restart is needed
        if resource.needs_restart() and resource.can_restart():
            if resource.configuration.restart_policy.value in ["on_threshold", "adaptive"]:
                await self.restart_resource(resource.id, "threshold_exceeded")
        
        # Check if cleanup is needed
        if resource.status == ResourceStatus.CRITICAL and resource.configuration.cleanup_enabled:
            await self.cleanup_resource(resource.id)
    
    async def _perform_resource_restart(self, resource: Resource) -> None:
        """Perform restart based on resource type."""
        if resource.resource_type == ResourceType.BROWSER:
            # Browser restart logic would be implemented here
            # This would involve closing and reopening browser instances
            pass
        elif resource.resource_type == ResourceType.MEMORY:
            # Memory cleanup (garbage collection, etc.)
            import gc
            gc.collect()
        elif resource.resource_type == ResourceType.CPU:
            # CPU throttling or process management
            pass
        else:
            # Generic restart logic
            pass
    
    async def _perform_resource_cleanup(self, resource: Resource) -> None:
        """Perform cleanup based on resource type."""
        if resource.resource_type == ResourceType.MEMORY:
            # Memory cleanup
            import gc
            gc.collect()
        elif resource.resource_type == ResourceType.BROWSER:
            # Browser cleanup (close tabs, clear cache, etc.)
            pass
        elif resource.resource_type == ResourceType.DISK:
            # Disk cleanup (temp files, cache, etc.)
            pass
        else:
            # Generic cleanup
            pass
    
    def _store_metrics_history(self, resource_id: str, metrics: ResourceMetrics) -> None:
        """Store metrics in history."""
        history = self.resource_history[resource_id]
        history.append(metrics)
        
        # Cleanup old history
        cutoff_time = datetime.utcnow() - timedelta(hours=self.history_retention_hours)
        history[:] = [m for m in history if m.timestamp >= cutoff_time]
        
        # Limit history size
        if len(history) > self.max_history_points:
            history[:] = history[-self.max_history_points:]
    
    def _notify_callbacks(self, resource: Resource) -> None:
        """Notify all resource callbacks."""
        for callback in self.resource_callbacks:
            try:
                callback(resource)
            except Exception as e:
                self.logger.error(
                    f"Error in resource callback: {str(e)}",
                    event_type="resource_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "resource_id": resource.id,
                        "error": str(e)
                    },
                    component="resource_manager"
                )
    
    def _get_default_configuration(self, resource_type: ResourceType) -> ResourceConfiguration:
        """Get default configuration for a resource type."""
        if resource_type == ResourceType.MEMORY:
            return DEFAULT_MEMORY_CONFIG
        elif resource_type == ResourceType.BROWSER:
            return DEFAULT_BROWSER_CONFIG
        elif resource_type == ResourceType.CPU:
            return DEFAULT_CPU_CONFIG
        else:
            return ResourceConfiguration(
                resource_type=resource_type,
                name=f"default_{resource_type.value}"
            )
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                # Update all resources that are being monitored
                for resource in self.resources.values():
                    if resource.configuration and resource.configuration.monitoring_enabled:
                        if resource.id not in self.monitoring_tasks:
                            await self._start_resource_monitoring(resource)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in monitoring loop: {str(e)}",
                    event_type="monitoring_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="resource_manager"
                )
                await asyncio.sleep(self.monitoring_interval)


# Global resource manager instance
_resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    return _resource_manager


async def create_resource(
    name: str,
    resource_type: ResourceType,
    configuration: Optional[ResourceConfiguration] = None,
    description: str = ""
) -> str:
    """Create a resource using the global manager."""
    return await _resource_manager.create_resource(name, resource_type, configuration, description)


async def get_resource(resource_id: str) -> Optional[Resource]:
    """Get a resource using the global manager."""
    return await _resource_manager.get_resource(resource_id)
