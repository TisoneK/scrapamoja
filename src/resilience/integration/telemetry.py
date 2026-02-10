"""
Telemetry Integration

Integrates resilience components with telemetry collection providing comprehensive
monitoring, metrics aggregation, and health reporting for all resilience operations.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..retry.retry_manager import RetryManager
from ..checkpoint.checkpoint_manager import CheckpointManager
from ..resource.resource_manager import ResourceManager
from ..abort.abort_manager import AbortManager
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_telemetry_event


class TelemetryIntegration:
    """Integrates telemetry collection with resilience components."""
    
    def __init__(self):
        """Initialize telemetry integration."""
        self.logger = get_logger("telemetry_integration")
        
        # Component managers
        self.retry_manager: Optional[RetryManager] = None
        self.checkpoint_manager: Optional[CheckpointManager] = None
        self.resource_manager: Optional[ResourceManager] = None
        self.abort_manager: Optional[AbortManager] = None
        
        # Telemetry data
        self.metrics_history: deque = deque(maxlen=10000)
        self.health_checks: deque = deque(maxlen=1000)
        self.performance_snapshots: deque = deque(maxlen=1000)
        
        # Aggregated metrics
        self.aggregated_metrics: Dict[str, Any] = {}
        self.last_aggregation_time: Optional[datetime] = None
        
        # Configuration
        self.collection_interval_seconds = 60
        self.aggregation_interval_seconds = 300  # 5 minutes
        self.health_check_interval_seconds = 120  # 2 minutes
        self.retention_hours = 24
        
        # Callbacks
        self.telemetry_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Integration state
        self._initialized = False
        self._collection_task: Optional[asyncio.Task] = None
        self._aggregation_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(
        self,
        retry_manager: RetryManager,
        checkpoint_manager: CheckpointManager,
        resource_manager: ResourceManager,
        abort_manager: AbortManager
    ) -> None:
        """Initialize the telemetry integration."""
        if self._initialized:
            return
        
        self.retry_manager = retry_manager
        self.checkpoint_manager = checkpoint_manager
        self.resource_manager = resource_manager
        self.abort_manager = abort_manager
        
        # Start collection tasks
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        self._initialized = True
        
        self.logger.info(
            "Telemetry integration initialized",
            event_type="telemetry_integration_initialized",
            correlation_id=get_correlation_id(),
            context={
                "collection_interval": self.collection_interval_seconds,
                "aggregation_interval": self.aggregation_interval_seconds,
                "health_check_interval": self.health_check_interval_seconds
            },
            component="telemetry_integration"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the telemetry integration gracefully."""
        if not self._initialized:
            return
        
        self._running = False
        
        # Cancel all tasks
        tasks = [self._collection_task, self._aggregation_task, self._health_check_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._initialized = False
        
        self.logger.info(
            "Telemetry integration shutdown",
            event_type="telemetry_integration_shutdown",
            correlation_id=get_correlation_id(),
            component="telemetry_integration"
        )
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics from all components."""
        if not self._initialized:
            return {}
        
        try:
            timestamp = datetime.utcnow()
            
            # Collect retry metrics
            retry_metrics = await self._collect_retry_metrics()
            
            # Collect checkpoint metrics
            checkpoint_metrics = await self._collect_checkpoint_metrics()
            
            # Collect resource metrics
            resource_metrics = await self._collect_resource_metrics()
            
            # Collect abort metrics
            abort_metrics = await self._collect_abort_metrics()
            
            # System metrics
            system_metrics = await self._collect_system_metrics()
            
            # Combine all metrics
            metrics = {
                "timestamp": timestamp.isoformat(),
                "retry": retry_metrics,
                "checkpoint": checkpoint_metrics,
                "resource": resource_metrics,
                "abort": abort_metrics,
                "system": system_metrics
            }
            
            # Store in history
            self.metrics_history.append(metrics)
            
            # Publish event
            await publish_telemetry_event(
                action="metrics_collected",
                context={
                    "timestamp": timestamp.isoformat(),
                    "component_count": 4
                },
                component="telemetry_integration"
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(
                f"Failed to collect metrics: {str(e)}",
                event_type="metrics_collection_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="telemetry_integration"
            )
            return {}
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        if not self._initialized:
            return {"status": "uninitialized", "components": {}}
        
        try:
            timestamp = datetime.utcnow()
            
            # Health check for each component
            component_health = {
                "retry": await self.retry_manager.health_check(),
                "checkpoint": await self.checkpoint_manager.health_check(),
                "resource": await self.resource_manager.health_check(),
                "abort": await self.abort_manager.health_check()
            }
            
            # Overall health assessment
            healthy_components = len([
                c for c in component_health.values()
                if c.get("status") == "healthy"
            ])
            
            overall_status = "healthy" if healthy_components == len(component_health) else "degraded"
            
            health_check = {
                "timestamp": timestamp.isoformat(),
                "overall_status": overall_status,
                "healthy_components": healthy_components,
                "total_components": len(component_health),
                "components": component_health
            }
            
            # Store in history
            self.health_checks.append(health_check)
            
            # Publish event
            await publish_telemetry_event(
                action="health_check_completed",
                context={
                    "overall_status": overall_status,
                    "healthy_components": healthy_components
                },
                component="telemetry_integration"
            )
            
            return health_check
            
        except Exception as e:
            self.logger.error(
                f"Failed to perform health check: {str(e)}",
                event_type="health_check_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="telemetry_integration"
            )
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "error",
                "error": str(e)
            }
    
    async def get_performance_snapshot(self) -> Dict[str, Any]:
        """Get current performance snapshot."""
        if not self._initialized:
            return {}
        
        try:
            timestamp = datetime.utcnow()
            
            # Get recent metrics
            recent_metrics = list(self.metrics_history)[-10:] if self.metrics_history else []
            
            if not recent_metrics:
                return {
                    "timestamp": timestamp.isoformat(),
                    "status": "no_data"
                }
            
            # Calculate performance indicators
            performance = {
                "timestamp": timestamp.isoformat(),
                "metrics_count": len(recent_metrics),
                "collection_rate": len(recent_metrics) / max(1, len(set(m["timestamp"] for m in recent_metrics))),
                "data_points": sum(
                    1 + len(m.get("retry", {})) + len(m.get("checkpoint", {})) + 
                    len(m.get("resource", {})) + len(m.get("abort", {}))
                    for m in recent_metrics
                )
            }
            
            # Store snapshot
            self.performance_snapshots.append(performance)
            
            return performance
            
        except Exception as e:
            self.logger.error(
                f"Failed to get performance snapshot: {str(e)}",
                event_type="performance_snapshot_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="telemetry_integration"
            )
            return {}
    
    async def get_aggregated_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Get aggregated metrics for specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter metrics by time
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) >= cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "period_hours": hours,
                "metrics_count": 0,
                "aggregated": {}
            }
        
        # Aggregate metrics
        aggregated = {
            "retry": self._aggregate_retry_metrics(recent_metrics),
            "checkpoint": self._aggregate_checkpoint_metrics(recent_metrics),
            "resource": self._aggregate_resource_metrics(recent_metrics),
            "abort": self._aggregate_abort_metrics(recent_metrics)
        }
        
        return {
            "period_hours": hours,
            "metrics_count": len(recent_metrics),
            "start_time": min(m["timestamp"] for m in recent_metrics),
            "end_time": max(m["timestamp"] for m in recent_metrics),
            "aggregated": aggregated
        }
    
    async def get_telemetry_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive telemetry report."""
        try:
            # Get aggregated metrics
            aggregated_metrics = await self.get_aggregated_metrics(hours)
            
            # Get health check summary
            recent_health_checks = [
                hc for hc in self.health_checks
                if datetime.fromisoformat(hc["timestamp"]) >= datetime.utcnow() - timedelta(hours=hours)
            ]
            
            health_summary = {
                "total_checks": len(recent_health_checks),
                "healthy_checks": len([hc for hc in recent_health_checks if hc["overall_status"] == "healthy"]),
                "degraded_checks": len([hc for hc in recent_health_checks if hc["overall_status"] == "degraded"]),
                "health_trend": self._calculate_health_trend(recent_health_checks)
            }
            
            # Get performance summary
            recent_snapshots = [
                ps for ps in self.performance_snapshots
                if datetime.fromisoformat(ps["timestamp"]) >= datetime.utcnow() - timedelta(hours=hours)
            ]
            
            performance_summary = {
                "total_snapshots": len(recent_snapshots),
                "average_collection_rate": sum(ps.get("collection_rate", 0) for ps in recent_snapshots) / len(recent_snapshots) if recent_snapshots else 0,
                "total_data_points": sum(ps.get("data_points", 0) for ps in recent_snapshots)
            }
            
            report = {
                "report_timestamp": datetime.utcnow().isoformat(),
                "period_hours": hours,
                "aggregated_metrics": aggregated_metrics,
                "health_summary": health_summary,
                "performance_summary": performance_summary,
                "system_status": "healthy" if health_summary["healthy_checks"] > health_summary["degraded_checks"] else "degraded"
            }
            
            return report
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate telemetry report: {str(e)}",
                event_type="telemetry_report_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="telemetry_integration"
            )
            return {
                "report_timestamp": datetime.utcnow().isoformat(),
                "period_hours": hours,
                "error": str(e)
            }
    
    def add_telemetry_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a telemetry callback."""
        self.telemetry_callbacks.append(callback)
    
    def remove_telemetry_callback(self, callback: Callable) -> bool:
        """Remove a telemetry callback."""
        if callback in self.telemetry_callbacks:
            self.telemetry_callbacks.remove(callback)
            return True
        return False
    
    async def _collect_retry_metrics(self) -> Dict[str, Any]:
        """Collect retry manager metrics."""
        try:
            # This would get actual metrics from retry manager
            # For now, return placeholder metrics
            return {
                "active_sessions": 0,
                "total_retries": 0,
                "success_rate": 0.0,
                "average_attempts": 0.0
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _collect_checkpoint_metrics(self) -> Dict[str, Any]:
        """Collect checkpoint manager metrics."""
        try:
            # This would get actual metrics from checkpoint manager
            return {
                "total_checkpoints": 0,
                "active_checkpoints": 0,
                "storage_usage_mb": 0.0,
                "compression_ratio": 1.0
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _collect_resource_metrics(self) -> Dict[str, Any]:
        """Collect resource manager metrics."""
        try:
            # This would get actual metrics from resource manager
            return {
                "total_resources": 0,
                "healthy_resources": 0,
                "critical_resources": 0,
                "resource_utilization": 0.0
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _collect_abort_metrics(self) -> Dict[str, Any]:
        """Collect abort manager metrics."""
        try:
            # This would get actual metrics from abort manager
            return {
                "active_policies": 0,
                "triggered_aborts": 0,
                "abort_rate": 0.0,
                "average_decision_time": 0.0
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics."""
        try:
            import psutil
            
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "process_count": len(psutil.pids())
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _aggregate_retry_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate retry metrics."""
        retry_metrics = [m.get("retry", {}) for m in metrics if "retry" in m]
        
        if not retry_metrics:
            return {}
        
        # Simple aggregation
        total_retries = sum(r.get("total_retries", 0) for r in retry_metrics)
        success_rates = [r.get("success_rate", 0) for r in retry_metrics if r.get("success_rate") is not None]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        
        return {
            "total_retries": total_retries,
            "average_success_rate": avg_success_rate,
            "samples": len(retry_metrics)
        }
    
    def _aggregate_checkpoint_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate checkpoint metrics."""
        checkpoint_metrics = [m.get("checkpoint", {}) for m in metrics if "checkpoint" in m]
        
        if not checkpoint_metrics:
            return {}
        
        total_checkpoints = sum(c.get("total_checkpoints", 0) for c in checkpoint_metrics)
        storage_usage = sum(c.get("storage_usage_mb", 0) for c in checkpoint_metrics)
        
        return {
            "total_checkpoints": total_checkpoints,
            "total_storage_usage_mb": storage_usage,
            "samples": len(checkpoint_metrics)
        }
    
    def _aggregate_resource_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate resource metrics."""
        resource_metrics = [m.get("resource", {}) for m in metrics if "resource" in m]
        
        if not resource_metrics:
            return {}
        
        total_resources = sum(r.get("total_resources", 0) for r in resource_metrics)
        healthy_resources = sum(r.get("healthy_resources", 0) for r in resource_metrics)
        
        return {
            "total_resources": total_resources,
            "healthy_resources": healthy_resources,
            "health_rate": healthy_resources / total_resources if total_resources > 0 else 0.0,
            "samples": len(resource_metrics)
        }
    
    def _aggregate_abort_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate abort metrics."""
        abort_metrics = [m.get("abort", {}) for m in metrics if "abort" in m]
        
        if not abort_metrics:
            return {}
        
        triggered_aborts = sum(a.get("triggered_aborts", 0) for a in abort_metrics)
        
        return {
            "total_triggered_aborts": triggered_aborts,
            "samples": len(abort_metrics)
        }
    
    def _calculate_health_trend(self, health_checks: List[Dict[str, Any]]) -> str:
        """Calculate health trend from health checks."""
        if len(health_checks) < 2:
            return "stable"
        
        # Compare recent vs older checks
        mid_point = len(health_checks) // 2
        recent_checks = health_checks[mid_point:]
        older_checks = health_checks[:mid_point]
        
        recent_healthy = len([hc for hc in recent_checks if hc["overall_status"] == "healthy"])
        older_healthy = len([hc for hc in older_checks if hc["overall_status"] == "healthy"])
        
        recent_rate = recent_healthy / len(recent_checks) if recent_checks else 0
        older_rate = older_healthy / len(older_checks) if older_checks else 0
        
        if recent_rate > older_rate + 0.1:
            return "improving"
        elif recent_rate < older_rate - 0.1:
            return "degrading"
        else:
            return "stable"
    
    async def _collection_loop(self) -> None:
        """Main metrics collection loop."""
        while self._running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.collection_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in telemetry collection loop: {str(e)}",
                    event_type="telemetry_collection_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="telemetry_integration"
                )
                await asyncio.sleep(self.collection_interval_seconds)
    
    async def _aggregation_loop(self) -> None:
        """Main aggregation loop."""
        while self._running:
            try:
                # Update aggregated metrics
                self.aggregated_metrics = await self.get_aggregated_metrics(1)
                self.last_aggregation_time = datetime.utcnow()
                
                await asyncio.sleep(self.aggregation_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in telemetry aggregation loop: {str(e)}",
                    event_type="telemetry_aggregation_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="telemetry_integration"
                )
                await asyncio.sleep(self.aggregation_interval_seconds)
    
    async def _health_check_loop(self) -> None:
        """Main health check loop."""
        while self._running:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.health_check_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in telemetry health check loop: {str(e)}",
                    event_type="telemetry_health_check_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="telemetry_integration"
                )
                await asyncio.sleep(self.health_check_interval_seconds)


# Global telemetry integration instance
_telemetry_integration = TelemetryIntegration()


def get_telemetry_integration() -> TelemetryIntegration:
    """Get the global telemetry integration instance."""
    return _telemetry_integration
