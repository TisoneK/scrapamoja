"""
Monitoring Snapshot - Hooks snapshot system into monitoring system.

This module integrates the snapshot system with the monitoring system
to report snapshot metrics and health status.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from ..manager import SnapshotManager
from ..models import SnapshotMetrics
from ..config import get_settings


@dataclass
class MonitoringEvent:
    """Monitoring event data for snapshot reporting."""
    event_type: str
    snapshot_id: str
    integration_source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MonitoringSnapshot:
    """Integrates snapshot system with monitoring system."""
    
    def __init__(self, snapshot_manager: SnapshotManager):
        """Initialize monitoring snapshot handler."""
        self.snapshot_manager = snapshot_manager
        self.settings = get_settings()
        self._monitoring_system = None
        self._initialized = False
        
        # Event callbacks
        self.on_snapshot_recorded: List[Callable] = []
        self.on_metrics_updated: List[Callable] = []
        self.on_health_check: List[Callable] = []
        
        # Statistics
        self.integration_stats = {
            "snapshots_recorded": 0,
            "metrics_reports": 0,
            "health_checks": 0,
            "alerts_triggered": 0
        }
        
        # Snapshot tracking
        self.recorded_snapshots: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize monitoring snapshot handler."""
        try:
            # Import monitoring system to avoid circular imports
            # Note: This would need to be implemented based on your monitoring architecture
            # For now, we'll create a placeholder that can be hooked into
            
            self._initialized = True
            print("✅ Monitoring snapshot handler initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize monitoring snapshot handler: {e}")
            raise
    
    async def record_error(self, error_data: Dict[str, Any]):
        """Record error from other integrations."""
        try:
            self.integration_stats["alerts_triggered"] += 1
            
            # Log error to monitoring system
            error_info = {
                "timestamp": datetime.now().isoformat(),
                "error_type": error_data.get("error_type"),
                "error_message": error_data.get("error_message"),
                "integration_source": error_data.get("integration_source"),
                "session_id": error_data.get("session_id"),
                "site": error_data.get("site"),
                "severity": error_data.get("severity", "medium")
            }
            
            # This would integrate with your monitoring system
            print(f"🚨 Error recorded: {error_info}")
            
            # Notify callbacks
            for callback in self.on_snapshot_recorded:
                await callback("error", error_info)
                
        except Exception as e:
            print(f"❌ Error recording to monitoring: {e}")
    
    async def record_snapshot(self, integration_source: str, bundle: Any):
        """Record snapshot from other integrations."""
        try:
            self.integration_stats["snapshots_recorded"] += 1
            
            # Record snapshot information
            snapshot_info = {
                "snapshot_id": bundle.content_hash[:8] if hasattr(bundle, 'content_hash') else 'unknown',
                "timestamp": bundle.timestamp.isoformat() if hasattr(bundle, 'timestamp') else datetime.now().isoformat(),
                "integration_source": integration_source,
                "site": bundle.context.site if hasattr(bundle, 'context') else 'unknown',
                "module": bundle.context.module if hasattr(bundle, 'context') else 'unknown',
                "component": bundle.context.component if hasattr(bundle, 'context') else 'unknown',
                "session_id": bundle.context.session_id if hasattr(bundle, 'context') else 'unknown',
                "bundle_path": bundle.bundle_path if hasattr(bundle, 'bundle_path') else 'unknown',
                "artifacts_count": len(bundle.artifacts) if hasattr(bundle, 'artifacts') else 0,
                "config_mode": bundle.config.mode.value if hasattr(bundle, 'config') else 'unknown'
            }
            
            # Store in tracking
            snapshot_id = snapshot_info["snapshot_id"]
            self.recorded_snapshots[snapshot_id] = snapshot_info
            
            # This would integrate with your monitoring system
            print(f"📊 Snapshot recorded: {snapshot_id} from {integration_source}")
            
            # Notify callbacks
            for callback in self.on_snapshot_recorded:
                await callback("snapshot", snapshot_info)
                
        except Exception as e:
            print(f"❌ Error recording snapshot: {e}")
    
    async def generate_metrics_report(self) -> Dict[str, Any]:
        """Generate comprehensive metrics report."""
        try:
            self.integration_stats["metrics_reports"] += 1
            
            # Get snapshot manager metrics
            snapshot_metrics = self.snapshot_manager.get_metrics()
            
            # Generate report
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "report_period": "last_24_hours",
                "snapshot_metrics": {
                    "total_snapshots": snapshot_metrics.total_snapshots,
                    "successful_snapshots": snapshot_metrics.successful_snapshots,
                    "failed_snapshots": snapshot_metrics.failed_snapshots,
                    "success_rate": snapshot_metrics.success_rate,
                    "average_capture_time": snapshot_metrics.average_capture_time
                },
                "integration_stats": self.integration_stats,
                "recorded_snapshots": len(self.recorded_snapshots),
                "snapshot_breakdown": self._get_snapshot_breakdown()
            }
            
            # This would integrate with your monitoring system
            print(f"📈 Metrics report generated")
            
            # Notify callbacks
            for callback in self.on_metrics_updated:
                await callback(report)
            
            return report
            
        except Exception as e:
            print(f"❌ Error generating metrics report: {e}")
            return {"error": str(e)}
    
    def _get_snapshot_breakdown(self) -> Dict[str, Any]:
        """Get breakdown of recorded snapshots by integration source."""
        breakdown = {}
        for snapshot_info in self.recorded_snapshots.values():
            source = snapshot_info.get("integration_source", "unknown")
            if source not in breakdown:
                breakdown[source] = {
                    "count": 0,
                    "sites": set(),
                    "modules": set(),
                    "components": set()
                }
            
            breakdown[source]["count"] += 1
            breakdown[source]["sites"].add(snapshot_info.get("site", "unknown"))
            breakdown[source]["modules"].add(snapshot_info.get("module", "unknown"))
            breakdown[source]["components"].add(snapshot_info.get("component", "unknown"))
        
        # Convert sets to lists for JSON serialization
        for source in breakdown:
            breakdown[source]["sites"] = list(breakdown[source]["sites"])
            breakdown[source]["modules"] = list(breakdown[source]["modules"])
            breakdown[source]["components"] = list(breakdown[source]["components"])
        
        return breakdown
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            self.integration_stats["health_checks"] += 1
            
            # Get snapshot manager metrics
            snapshot_metrics = self.snapshot_manager.get_metrics()
            
            # Health check criteria
            health_status = {
                "overall_status": "healthy",
                "checks": {
                    "snapshot_success_rate": {
                        "status": "healthy" if snapshot_metrics.success_rate >= 95.0 else "degraded",
                        "value": snapshot_metrics.success_rate,
                        "threshold": 95.0
                    },
                    "average_capture_time": {
                        "status": "healthy" if snapshot_metrics.average_capture_time <= 3000 else "degraded",  # 3 seconds
                        "value": snapshot_metrics.average_capture_time,
                        "threshold": 3000
                    },
                    "integration_activity": {
                        "status": "healthy" if self.integration_stats["snapshots_recorded"] > 0 else "warning",
                        "value": self.integration_stats["snapshots_recorded"],
                        "threshold": 1
                    }
                }
            }
            
            # Determine overall status
            check_statuses = [check["status"] for check in health_status["checks"].values()]
            if "unhealthy" in check_statuses:
                health_status["overall_status"] = "unhealthy"
            elif "degraded" in check_statuses or "warning" in check_statuses:
                health_status["overall_status"] = "degraded"
            
            health_status["check_timestamp"] = datetime.now().isoformat()
            
            # This would integrate with your monitoring system
            print(f"🏥 Health check completed: {health_status['overall_status']}")
            
            # Notify callbacks
            for callback in self.on_health_check:
                await callback(health_status)
            
            return health_status
            
        except Exception as e:
            print(f"❌ Error performing health check: {e}")
            return {"error": str(e)}
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status of monitoring integration."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "monitoring_system_available": self._monitoring_system is not None,
            "statistics": self.integration_stats,
            "recorded_snapshots": len(self.recorded_snapshots),
            "event_callbacks": {
                "snapshot_recorded": len(self.on_snapshot_recorded) > 0,
                "metrics_updated": len(self.on_metrics_updated) > 0,
                "health_check": len(self.on_health_check) > 0
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "integration_type": "monitoring_system",
            "initialized": self._initialized,
            "statistics": self.integration_stats,
            "recorded_snapshots": len(self.recorded_snapshots),
            "snapshot_breakdown": self._get_snapshot_breakdown(),
            "event_callbacks": {
                "snapshot_recorded": len(self.on_snapshot_recorded),
                "metrics_updated": len(self.on_metrics_updated),
                "health_check": len(self.on_health_check)
            }
        }
