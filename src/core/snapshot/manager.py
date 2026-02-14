"""
SnapshotManager - Central orchestrator for the snapshot system.

This module provides the main interface for the snapshot system, coordinating
capture, storage, triggers, monitoring, and integration components.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import uuid

from .models import (
    SnapshotContext, SnapshotConfig, SnapshotBundle, SnapshotMode,
    SnapshotMetrics, ContentDeduplicator, SnapshotError
)
from .storage import SnapshotStorage
from .capture import SnapshotCapture
from .triggers import TriggerManager
from .config import get_settings
from .metrics import MetricsCollector, HealthMonitor, MonitoringDashboard
from .exceptions import (
    SnapshotError, SnapshotCaptureError, SnapshotStorageError,
    SnapshotValidationError, SnapshotCompleteFailure,
    DiskFullError, PermissionError, PartialSnapshotBundle,
    SnapshotCircuitOpen
)
from .circuit_breaker import get_circuit_breaker, check_circuit_breaker


class SnapshotManager:
    """Central orchestrator for the snapshot system."""
    
    def __init__(self, 
                 storage_path: str = "data/snapshots",
                 config_path: Optional[str] = None):
        """Initialize snapshot manager."""
        # Initialize configuration
        self.settings = get_settings()
        
        # Initialize core components
        self.storage = SnapshotStorage(storage_path)  # Use provided storage_path directly, not settings.base_path
        self.deduplicator = ContentDeduplicator(
            max_cache_size=self.settings.dedup_cache_size
        )
        self.capture = SnapshotCapture(self.storage, self.deduplicator)
        self.trigger_manager = TriggerManager()
        self.metrics_collector = MetricsCollector(
            max_history_size=self.settings.metrics_max_history_size
        )
        self.health_monitor = HealthMonitor(self.metrics_collector)
        self.dashboard = MonitoringDashboard(self.metrics_collector, self.health_monitor)
        
        # Note: Integration is now handled by SnapshotCoordinator
        # This manager focuses on core snapshot functionality
        
        # Manager state
        self.initialized = True
        self.session_id = str(uuid.uuid4())
    
    async def capture_snapshot(self,
                             page: Any,
                             context: SnapshotContext,
                             config: Optional[SnapshotConfig] = None) -> Optional[Union[SnapshotBundle, PartialSnapshotBundle]]:
        """Main snapshot capture method with comprehensive error handling."""
        try:
            # Check circuit breaker first
            check_circuit_breaker()
            
            # Use default config if not provided
            if config is None:
                config = SnapshotConfig(
                    capture_html=self.settings.default_capture_html,
                    capture_screenshot=self.settings.default_capture_screenshot,
                    capture_console=self.settings.default_capture_console,
                    capture_network=self.settings.default_capture_network,
                    async_save=self.settings.enable_async_save,
                    deduplication_enabled=self.settings.enable_deduplication
                )
            
            # Validate configuration
            try:
                config.validate()
            except SnapshotValidationError as e:
                self.metrics_collector.record_failure("validation", str(e))
                raise
            
            # Start performance timer
            timer = self.metrics_collector.start_operation_timer("snapshot_capture")
            
            # Capture with graceful degradation
            artifacts = []
            errors = []
            
            # Try each artifact independently
            # DIAGNOSTIC: Log the start of artifact capture
            print(f"🔍 DIAGNOSTIC: Starting artifact capture with config: {config}")
            
            # FIX: Compute html_dir properly before using it
            from datetime import datetime
            start_time = datetime.now()
            bundle_path = self.storage.get_bundle_path(context, start_time)
            html_dir = bundle_path / "html"
            screenshots_dir = bundle_path / "screenshots"
            logs_dir = bundle_path / "logs"
            
            # FIX: Create bundle directory BEFORE capturing artifacts
            print(f"🔍 DIAGNOSTIC: Creating bundle directory: {bundle_path}")
            await self.storage.create_bundle_directory(bundle_path)
            print(f"🔍 DIAGNOSTIC: Bundle directory created successfully")
            
            print(f"🔍 DIAGNOSTIC: bundle_path={bundle_path}, html_dir={html_dir}")
            
            if config.capture_html:
                try:
                    html_artifact = await self.capture._capture_full_html(page, html_dir)
                    artifacts.append(html_artifact)
                    print(f"🔍 DIAGNOSTIC: HTML capture result: {html_artifact}")
                except Exception as e:
                    errors.append(("html", e))
                    print(f"⚠️ Failed to capture HTML: {e}")
                    import traceback
                    print(f"🔍 DIAGNOSTIC: HTML capture traceback: {traceback.format_exc()}")
            
            if config.capture_screenshot:
                try:
                    screenshot_artifact = await self.capture._capture_screenshot(page, screenshots_dir)
                    artifacts.append(screenshot_artifact)
                except Exception as e:
                    errors.append(("screenshot", e))
                    print(f"⚠️ Failed to capture screenshot: {e}")
            
            if config.capture_console:
                try:
                    console_artifact = await self.capture._capture_console_logs(page, logs_dir)
                    artifacts.append(console_artifact)
                except Exception as e:
                    errors.append(("console", e))
                    print(f"⚠️ Failed to capture console: {e}")
            
            if config.capture_network:
                try:
                    network_artifact = await self.capture._capture_network_logs(page, logs_dir)
                    artifacts.append(network_artifact)
                except Exception as e:
                    errors.append(("network", e))
                    print(f"⚠️ Failed to capture network: {e}")
            
            # Check if we got any artifacts
            if not artifacts:
                circuit_breaker = get_circuit_breaker()
                circuit_breaker.record_failure("complete_failure", "No artifacts captured")
                self.metrics_collector.record_failure("complete_failure", "No artifacts captured")
                raise SnapshotCompleteFailure("No artifacts could be captured")
            
            # Save whatever we got
            try:
                if errors:
                    # Partial snapshot
                    bundle = await self._save_partial_snapshot(artifacts, context, config, errors)
                    circuit_breaker = get_circuit_breaker()
                    circuit_breaker.record_failure("partial_failure", f"{len(errors)} artifacts failed")
                    
                    # Record partial success metric
                    timer(success=True, metadata={
                        "site": context.site,
                        "module": context.module,
                        "component": context.component,
                        "mode": config.mode.value,
                        "partial": True,
                        "success_rate": bundle.success_rate
                    })
                    
                    return bundle
                else:
                    # Full success - create SnapshotBundle and save using storage
                    bundle = SnapshotBundle(
                        context=context,
                        timestamp=start_time,
                        config=config,
                        bundle_path=str(bundle_path),
                        artifacts=artifacts,
                        metadata={"capture_method": "manager_graceful_degradation"}
                    )
                    # Save the bundle using storage
                    await self.storage.save_bundle(bundle)
                    circuit_breaker = get_circuit_breaker()
                    circuit_breaker.record_success()
                    
                    # Record success metric
                    timer(success=True, metadata={
                        "site": context.site,
                        "module": context.module,
                        "component": context.component,
                        "mode": config.mode.value,
                        "partial": False
                    })
                    
                    print(f"📸 Full snapshot saved: {len(artifacts)} artifacts at {bundle_path}")
                    return bundle
                    
            except Exception as e:
                # Storage failure
                error_type = "storage"
                if "disk full" in str(e).lower():
                    error_type = "disk_full"
                elif "permission" in str(e).lower():
                    error_type = "permission"
                
                circuit_breaker = get_circuit_breaker()
                circuit_breaker.record_failure(error_type, str(e))
                self.metrics_collector.record_failure(error_type, str(e))
                
                if error_type == "disk_full":
                    raise DiskFullError(f"Disk full: {e}", e)
                elif error_type == "permission":
                    raise PermissionError(f"Permission denied: {e}", e)
                else:
                    raise SnapshotStorageError(f"Storage failed: {e}", e)
                
        except SnapshotCircuitOpen:
            # Circuit breaker is open - don't try to capture
            print("🚨 Snapshot circuit breaker is OPEN - skipping capture")
            self.metrics_collector.record_failure("circuit_breaker", "Circuit breaker open")
            return None
            
        except SnapshotError:
            # Re-raise snapshot errors (they're already handled)
            raise
            
        except Exception as e:
            # Unexpected error
            print(f"❌ Unexpected error in snapshot capture: {e}")
            circuit_breaker = get_circuit_breaker()
            circuit_breaker.record_failure("unexpected", str(e))
            self.metrics_collector.record_failure("unexpected", str(e))
            return None
    
    async def _save_partial_snapshot(self, 
                                  artifacts: List[Any], 
                                  context: SnapshotContext, 
                                  config: SnapshotConfig,
                                  errors: List[tuple]) -> PartialSnapshotBundle:
        """Save partial snapshot when some artifacts failed."""
        try:
            # Get bundle_path from storage
            timestamp = datetime.now()
            bundle_path = self.storage.get_bundle_path(context, timestamp)
            
            # Create partial bundle - errors need to be converted to List[Tuple[str, Exception]]
            error_tuples: List[tuple] = [(str(err_type), err) for err_type, err in errors]
            
            partial_bundle = PartialSnapshotBundle(
                artifacts=artifacts,
                errors=error_tuples,
                context=context,
                timestamp=datetime.now().isoformat()
            )
            
            # Try to save what we got - storage.save_partial_bundle takes only the bundle
            await self.storage.save_partial_bundle(partial_bundle)
            partial_bundle.bundle_path = str(bundle_path)
            
            print(f"📸 Partial snapshot saved: {len(artifacts)} artifacts, {len(errors)} failed at {bundle_path}")
            return partial_bundle
            
        except Exception as e:
            print(f"❌ Failed to save partial snapshot: {e}")
            # Still return the partial bundle even if save failed
            error_tuples: List[tuple] = [(str(err_type), err) for err_type, err in errors]
            return PartialSnapshotBundle(
                artifacts=artifacts,
                errors=error_tuples,
                context=context,
                timestamp=datetime.now().isoformat()
            )
    
    async def handle_selector_failure(self,
                                     page: Any,
                                     site: str,
                                     module: str,
                                     component: str,
                                     session_id: str,
                                     selector: str,
                                     matched_count: int = 0) -> bool:
        """Event-driven failure handling for selector failures."""
        # This is now handled by SnapshotCoordinator
        # Keeping method for backward compatibility
        print(f"⚠️ Selector failure detected: {selector} (matched: {matched_count})")
        return False
    
    async def handle_retry_exhaustion(self,
                                     page: Any,
                                     site: str,
                                     module: str,
                                     component: str,
                                     session_id: str,
                                     operation: str,
                                     retry_count: int,
                                     max_retries: int,
                                     last_error: Optional[str] = None) -> bool:
        """Event-driven failure handling for retry exhaustion."""
        # This is now handled by SnapshotCoordinator
        # Keeping method for backward compatibility
        print(f"⚠️ Retry exhaustion detected: {operation} (retries: {retry_count}/{max_retries})")
        return False
    
    async def handle_timeout(self,
                           page: Any,
                           site: str,
                           module: str,
                           component: str,
                           session_id: str,
                           operation: str,
                           timeout_duration: float,
                           partial_results: Optional[Dict[str, Any]] = None) -> bool:
        """Event-driven failure handling for timeouts."""
        # This is now handled by SnapshotCoordinator
        # Keeping method for backward compatibility
        print(f"⚠️ Timeout detected: {operation} (duration: {timeout_duration}s)")
        return False
    
    async def load_bundle(self, bundle_path: str) -> Optional[SnapshotBundle]:
        """Load bundle with validation."""
        try:
            timer = self.metrics_collector.start_operation_timer("bundle_load")
            
            try:
                bundle = await self.storage.load_bundle(bundle_path)
                timer(success=True)
                return bundle
                
            except Exception as e:
                timer(success=False, error_type=type(e).__name__)
                raise
                
        except Exception as e:
            print(f"Error loading bundle: {e}")
            return None
    
    async def list_bundles(self,
                          site: Optional[str] = None,
                          module: Optional[str] = None,
                          component: Optional[str] = None,
                          limit: int = 100) -> List[SnapshotBundle]:
        """List bundles with optional filtering."""
        try:
            return await self.storage.list_bundles(site, module, component, limit)
        except Exception as e:
            print(f"Error listing bundles: {e}")
            return []
    
    async def delete_bundle(self, bundle_path: str) -> bool:
        """Delete bundle atomically."""
        try:
            timer = self.metrics_collector.start_operation_timer("bundle_delete")
            
            try:
                result = await self.storage.delete_bundle(bundle_path)
                timer(success=True)
                return result
                
            except Exception as e:
                timer(success=False, error_type=type(e).__name__)
                raise
                
        except Exception as e:
            print(f"Error deleting bundle: {e}")
            return False
    
    async def cleanup_old_bundles(self, 
                                 days_to_keep: int = 30,
                                 dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old bundles and return statistics."""
        try:
            timer = self.metrics_collector.start_operation_timer("cleanup_bundles")
            
            try:
                result = await self.storage.cleanup_old_bundles(days_to_keep, dry_run)
                timer(success=True, metadata={
                    "deleted_count": result["deleted_count"],
                    "dry_run": dry_run
                })
                return result
                
            except Exception as e:
                timer(success=False, error_type=type(e).__name__)
                raise
                
        except Exception as e:
            print(f"Error cleaning up bundles: {e}")
            return {"deleted_count": 0, "errors": [str(e)]}
    
    def get_metrics(self) -> SnapshotMetrics:
        """Get comprehensive snapshot metrics."""
        return self.metrics_collector.get_snapshot_metrics()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        health_checks = self.health_monitor.run_health_checks()
        overall_health = self.health_monitor.get_system_health()
        
        return {
            "overall_health": overall_health.__dict__ if overall_health else None,
            "health_checks": [check.__dict__ for check in health_checks],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get monitoring dashboard data."""
        return self.dashboard.get_dashboard_data()
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return asyncio.run(self.storage.get_storage_statistics())
    
    def get_deduplication_statistics(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        return self.capture.get_deduplication_stats()
    
    def get_trigger_statistics(self) -> Dict[str, Any]:
        """Get trigger statistics."""
        return self.trigger_manager.get_trigger_statistics()
    
    def get_configuration_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        return {
            "settings": self.settings.to_dict(),
            "storage_path": self.storage.base_path,
            "deduplicator_cache_size": self.deduplicator.cache_size,
            "metrics_enabled": self.settings.enable_metrics
        }
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        # This is now handled by SnapshotCoordinator
        return {
            "note": "Integration statistics now available through SnapshotCoordinator"
        }
    
    # Configuration methods
    def update_setting(self, key: str, value: Any) -> bool:
        """Update a configuration setting."""
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            return True
        return False
    
    def get_setting(self, key: str) -> Any:
        """Get a configuration setting."""
        return getattr(self.settings, key, None)
    
    # Trigger management methods
    def enable_trigger(self, trigger_type: str) -> bool:
        """Enable a specific trigger."""
        return self.trigger_manager.enable_trigger(trigger_type)
    
    def disable_trigger(self, trigger_type: str) -> bool:
        """Disable a specific trigger."""
        return self.trigger_manager.disable_trigger(trigger_type)
    
    def set_trigger_rate_limit(self, trigger_type: str, rate_limit: int) -> bool:
        """Set rate limit for a specific trigger."""
        return self.trigger_manager.set_rate_limit(trigger_type, rate_limit)
    
    # Utility methods
    async def export_metrics(self, filepath: str, hours: int = 24) -> bool:
        """Export metrics to file."""
        try:
            self.dashboard.export_metrics(filepath, hours)
            return True
        except Exception as e:
            print(f"Error exporting metrics: {e}")
            return False
    
    async def validate_system(self) -> Dict[str, Any]:
        """Validate system components and return status."""
        validation_results = {}
        
        # Validate storage
        try:
            storage_stats = await self.storage.get_storage_statistics()
            validation_results["storage"] = {
                "status": "healthy",
                "details": storage_stats
            }
        except Exception as e:
            validation_results["storage"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Validate deduplicator
        try:
            dedup_stats = self.get_deduplication_statistics()
            validation_results["deduplicator"] = {
                "status": "healthy",
                "details": dedup_stats
            }
        except Exception as e:
            validation_results["deduplicator"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Validate configuration
        try:
            config_stats = self.get_configuration_statistics()
            validation_results["configuration"] = {
                "status": "healthy",
                "details": config_stats
            }
        except Exception as e:
            validation_results["configuration"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Validate triggers
        try:
            trigger_stats = self.get_trigger_statistics()
            validation_results["triggers"] = {
                "status": "healthy",
                "details": trigger_stats
            }
        except Exception as e:
            validation_results["triggers"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Overall system status
        unhealthy_components = [
            name for name, result in validation_results.items()
            if result["status"] == "unhealthy"
        ]
        
        validation_results["overall"] = {
            "status": "healthy" if not unhealthy_components else "unhealthy",
            "unhealthy_components": unhealthy_components,
            "validation_timestamp": datetime.now().isoformat()
        }
        
        return validation_results
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Cleanup resources if needed
        pass


# Global snapshot manager instance
_snapshot_manager: Optional[SnapshotManager] = None


def get_snapshot_manager(storage_path: str = "data/snapshots", 
                        config_path: Optional[str] = None) -> SnapshotManager:
    """Get the global snapshot manager instance."""
    global _snapshot_manager
    if _snapshot_manager is None:
        _snapshot_manager = SnapshotManager(storage_path, config_path)
    return _snapshot_manager
