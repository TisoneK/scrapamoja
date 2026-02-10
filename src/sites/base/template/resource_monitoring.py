"""
Resource monitoring integration for template framework.

This module provides automatic integration with resource monitoring,
including memory, CPU, disk, and network monitoring for template operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .integration_bridge import BaseIntegrationBridge


logger = logging.getLogger(__name__)


class ResourceMonitoringIntegration:
    """
    Resource monitoring integration for template framework.
    
    This class provides automatic integration with resource monitoring
    features, enabling templates to track resource usage during operations.
    """
    
    def __init__(self, integration_bridge: BaseIntegrationBridge):
        """
        Initialize resource monitoring integration.
        
        Args:
            integration_bridge: The integration bridge instance
        """
        self.integration_bridge = integration_bridge
        self.template_name = integration_bridge.template_name
        
        # Resource monitoring state
        self.monitoring_active = False
        self.monitoring_session_id = None
        self.resource_monitor = None
        self.monitoring_events = []
        
        # Feature availability
        self.features_available = {
            "memory_monitoring": False,
            "cpu_monitoring": False,
            "disk_monitoring": False,
            "network_monitoring": False,
            "process_monitoring": False
        }
        
        # Configuration
        self.config = {
            "auto_monitoring": False,
            "monitoring_interval": 5.0,  # seconds
            "memory_threshold": 80.0,  # percentage
            "cpu_threshold": 80.0,  # percentage
            "disk_threshold": 90.0,  # percentage
            "network_threshold": 1000000,  # bytes per second
            "alert_on_threshold": True,
            "cleanup_on_threshold": True,
            "max_monitoring_time": 3600  # seconds
        }
        
        # Resource history
        self.resource_history = []
        self.threshold_alerts = []
        
        logger.info(f"ResourceMonitoringIntegration initialized for {template_name}")
    
    async def initialize_resource_monitoring(self) -> bool:
        """
        Initialize resource monitoring integration.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info(f"Initializing resource monitoring for {self.template_name}")
            
            # Detect resource monitoring capabilities
            await self._detect_monitoring_capabilities()
            
            # Initialize resource monitor
            if not await self._initialize_resource_monitor():
                logger.warning("Resource monitor initialization failed")
                return False
            
            # Setup monitoring configuration
            await self._setup_monitoring_config()
            
            # Register monitoring handlers
            await self._register_monitoring_handlers()
            
            logger.info(f"Resource monitoring initialized successfully for {self.template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize resource monitoring: {e}")
            return False
    
    async def _detect_monitoring_capabilities(self) -> None:
        """Detect resource monitoring capabilities."""
        try:
            # Get monitoring capabilities from integration bridge
            available_components = self.integration_bridge.get_available_components()
            
            # Detect resource monitoring capabilities
            resource_monitoring = available_components.get("resource_monitoring", {})
            
            self.features_available["memory_monitoring"] = resource_monitoring.get("supports_memory_monitoring", False)
            self.features_available["cpu_monitoring"] = resource_monitoring.get("supports_cpu_monitoring", False)
            self.features_available["disk_monitoring"] = resource_monitoring.get("supports_disk_monitoring", False)
            self.features_available["network_monitoring"] = resource_monitoring.get("supports_network_monitoring", False)
            
            # Try to import psutil for process monitoring
            try:
                import psutil
                self.features_available["process_monitoring"] = True
                logger.debug("psutil available for process monitoring")
            except ImportError:
                self.features_available["process_monitoring"] = False
                logger.debug("psutil not available for process monitoring")
            
            logger.debug(f"Resource monitoring capabilities detected: {list(self.features_available.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to detect resource monitoring capabilities: {e}")
    
    async def _initialize_resource_monitor(self) -> bool:
        """Initialize the resource monitor."""
        try:
            # Try to use existing resource monitoring system
            try:
                from src.monitoring import ResourceMonitor
                self.resource_monitor = ResourceMonitor()
                logger.info("Using existing ResourceMonitor")
                return True
            except ImportError:
                logger.debug("Existing ResourceMonitor not found, creating fallback")
            
            # Create fallback resource monitor
            self.resource_monitor = FallbackResourceMonitor(self.features_available)
            logger.info("Using fallback resource monitor")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize resource monitor: {e}")
            return False
    
    async def _setup_monitoring_config(self) -> None:
        """Setup monitoring configuration."""
        try:
            # Configure monitoring thresholds
            if self.resource_monitor and hasattr(self.resource_monitor, 'set_thresholds'):
                await self.resource_monitor.set_thresholds({
                    "memory": self.config["memory_threshold"],
                    "cpu": self.config["cpu_threshold"],
                    "disk": self.config["disk_threshold"],
                    "network": self.config["network_threshold"]
                })
            
            # Configure alert settings
            if self.resource_monitor and hasattr(self.resource_monitor, 'set_alert_config'):
                await self.resource_monitor.set_alert_config({
                    "alert_on_threshold": self.config["alert_on_threshold"],
                    "cleanup_on_threshold": self.config["cleanup_on_threshold"]
                })
            
            logger.debug("Resource monitoring configuration completed")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring config: {e}")
    
    async def _register_monitoring_handlers(self) -> None:
        """Register monitoring event handlers."""
        try:
            # Register threshold alert handler
            if self.resource_monitor and hasattr(self.resource_monitor, 'on_threshold_alert'):
                self.resource_monitor.on_threshold_alert(self._on_threshold_alert)
            
            # Register resource update handler
            if self.resource_monitor and hasattr(self.resource_monitor, 'on_resource_update'):
                self.resource_monitor.on_resource_update(self._on_resource_update)
            
            logger.debug("Resource monitoring handlers registered")
            
        except Exception as e:
            logger.error(f"Failed to register monitoring handlers: {e}")
    
    async def _on_threshold_alert(self, alert_data: Dict[str, Any]) -> None:
        """Handle threshold alert events."""
        try:
            alert_info = {
                "type": "threshold_alert",
                "template_name": self.template_name,
                "session_id": self.monitoring_session_id,
                "alert_data": alert_data,
                "timestamp": datetime.now().isoformat()
            }
            
            self.monitoring_events.append(alert_info)
            self.threshold_alerts.append(alert_info)
            
            # Log alert
            logger.warning(f"Resource threshold alert in {self.template_name}: {alert_data}")
            
            # Trigger cleanup if configured
            if self.config.get("cleanup_on_threshold", False):
                await self._trigger_cleanup(alert_data)
            
        except Exception as e:
            logger.error(f"Failed to handle threshold alert: {e}")
    
    async def _on_resource_update(self, resource_data: Dict[str, Any]) -> None:
        """Handle resource update events."""
        try:
            # Add to resource history
            resource_info = {
                "template_name": self.template_name,
                "session_id": self.monitoring_session_id,
                "resource_data": resource_data,
                "timestamp": datetime.now().isoformat()
            }
            
            self.resource_history.append(resource_info)
            
            # Keep only recent history (last 1000 entries)
            if len(self.resource_history) > 1000:
                self.resource_history = self.resource_history[-1000:]
            
        except Exception as e:
            logger.debug(f"Failed to handle resource update: {e}")
    
    async def start_monitoring(self) -> bool:
        """
        Start resource monitoring.
        
        Returns:
            bool: True if monitoring started successfully
        """
        try:
            if self.monitoring_active:
                logger.warning("Resource monitoring already active")
                return True
            
            if not self.resource_monitor:
                logger.error("Resource monitor not initialized")
                return False
            
            # Generate monitoring session ID
            import uuid
            self.monitoring_session_id = str(uuid.uuid4())
            
            # Start monitoring
            if hasattr(self.resource_monitor, 'start_monitoring'):
                success = await self.resource_monitor.start_monitoring(
                    session_id=self.monitoring_session_id,
                    interval=self.config["monitoring_interval"]
                )
            else:
                # Fallback monitoring
                success = await self._start_fallback_monitoring()
            
            if success:
                self.monitoring_active = True
                logger.info(f"Resource monitoring started: {self.monitoring_session_id}")
            else:
                logger.error("Failed to start resource monitoring")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return False
    
    async def stop_monitoring(self) -> bool:
        """
        Stop resource monitoring.
        
        Returns:
            bool: True if monitoring stopped successfully
        """
        try:
            if not self.monitoring_active:
                logger.warning("Resource monitoring not active")
                return True
            
            if self.resource_monitor and hasattr(self.resource_monitor, 'stop_monitoring'):
                success = await self.resource_monitor.stop_monitoring(
                    session_id=self.monitoring_session_id
                )
            else:
                # Fallback monitoring
                success = await self._stop_fallback_monitoring()
            
            if success:
                self.monitoring_active = False
                logger.info(f"Resource monitoring stopped: {self.monitoring_session_id}")
            else:
                logger.error("Failed to stop resource monitoring")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            return False
    
    async def _start_fallback_monitoring(self) -> bool:
        """Start fallback resource monitoring."""
        try:
            # Simple fallback monitoring implementation
            self._monitoring_task = asyncio.create_task(self._fallback_monitoring_loop())
            return True
            
        except Exception as e:
            logger.error(f"Failed to start fallback monitoring: {e}")
            return False
    
    async def _stop_fallback_monitoring(self) -> bool:
        """Stop fallback resource monitoring."""
        try:
            if hasattr(self, '_monitoring_task'):
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop fallback monitoring: {e}")
            return False
    
    async def _fallback_monitoring_loop(self) -> None:
        """Fallback monitoring loop."""
        try:
            while self.monitoring_active:
                # Collect resource metrics
                metrics = await self._collect_resource_metrics()
                
                # Handle resource update
                await self._on_resource_update(metrics)
                
                # Check thresholds
                await self._check_thresholds(metrics)
                
                # Wait for next interval
                await asyncio.sleep(self.config["monitoring_interval"])
                
        except asyncio.CancelledError:
            logger.debug("Fallback monitoring cancelled")
        except Exception as e:
            logger.error(f"Fallback monitoring loop error: {e}")
    
    async def _collect_resource_metrics(self) -> Dict[str, Any]:
        """Collect resource metrics."""
        try:
            metrics = {}
            
            # Memory metrics
            if self.features_available["memory_monitoring"]:
                try:
                    import psutil
                    memory = psutil.virtual_memory()
                    metrics["memory"] = {
                        "total": memory.total,
                        "available": memory.available,
                        "used": memory.used,
                        "percentage": memory.percent
                    }
                except Exception as e:
                    logger.debug(f"Failed to collect memory metrics: {e}")
            
            # CPU metrics
            if self.features_available["cpu_monitoring"]:
                try:
                    import psutil
                    cpu_percent = psutil.cpu_percent(interval=1)
                    metrics["cpu"] = {
                        "percentage": cpu_percent
                    }
                except Exception as e:
                    logger.debug(f"Failed to collect CPU metrics: {e}")
            
            # Disk metrics
            if self.features_available["disk_monitoring"]:
                try:
                    import psutil
                    disk = psutil.disk_usage('/')
                    metrics["disk"] = {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percentage": (disk.used / disk.total) * 100
                    }
                except Exception as e:
                    logger.debug(f"Failed to collect disk metrics: {e}")
            
            # Network metrics
            if self.features_available["network_monitoring"]:
                try:
                    import psutil
                    network = psutil.net_io_counters()
                    metrics["network"] = {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv
                    }
                except Exception as e:
                    logger.debug(f"Failed to collect network metrics: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect resource metrics: {e}")
            return {}
    
    async def _check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """Check resource thresholds."""
        try:
            alerts = []
            
            # Check memory threshold
            if "memory" in metrics:
                memory_percent = metrics["memory"].get("percentage", 0)
                if memory_percent > self.config["memory_threshold"]:
                    alerts.append({
                        "type": "memory",
                        "current": memory_percent,
                        "threshold": self.config["memory_threshold"],
                        "severity": "high" if memory_percent > 90 else "medium"
                    })
            
            # Check CPU threshold
            if "cpu" in metrics:
                cpu_percent = metrics["cpu"].get("percentage", 0)
                if cpu_percent > self.config["cpu_threshold"]:
                    alerts.append({
                        "type": "cpu",
                        "current": cpu_percent,
                        "threshold": self.config["cpu_threshold"],
                        "severity": "high" if cpu_percent > 90 else "medium"
                    })
            
            # Check disk threshold
            if "disk" in metrics:
                disk_percent = metrics["disk"].get("percentage", 0)
                if disk_percent > self.config["disk_threshold"]:
                    alerts.append({
                        "type": "disk",
                        "current": disk_percent,
                        "threshold": self.config["disk_threshold"],
                        "severity": "high" if disk_percent > 95 else "medium"
                    })
            
            # Trigger alerts
            for alert in alerts:
                await self._on_threshold_alert(alert)
            
        except Exception as e:
            logger.error(f"Failed to check thresholds: {e}")
    
    async def _trigger_cleanup(self, alert_data: Dict[str, Any]) -> None:
        """Trigger cleanup based on alert data."""
        try:
            alert_type = alert_data.get("type", "unknown")
            severity = alert_data.get("severity", "medium")
            
            logger.info(f"Triggering cleanup for {alert_type} alert (severity: {severity})")
            
            # Template-specific cleanup logic would go here
            # For now, just log the cleanup action
            cleanup_info = {
                "type": "cleanup_triggered",
                "template_name": self.template_name,
                "alert_data": alert_data,
                "timestamp": datetime.now().isoformat()
            }
            
            self.monitoring_events.append(cleanup_info)
            
        except Exception as e:
            logger.error(f"Failed to trigger cleanup: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status.
        
        Returns:
            Dict[str, Any]: Monitoring status
        """
        return {
            "template_name": self.template_name,
            "monitoring_active": self.monitoring_active,
            "session_id": self.monitoring_session_id,
            "features_available": self.features_available,
            "config": self.config,
            "monitoring_events_count": len(self.monitoring_events),
            "resource_history_count": len(self.resource_history),
            "threshold_alerts_count": len(self.threshold_alerts)
        }
    
    def get_resource_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get resource usage history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: Resource history
        """
        return self.resource_history[-limit:] if self.resource_history else []
    
    def get_threshold_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get threshold alerts.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List[Dict[str, Any]]: Threshold alerts
        """
        return self.threshold_alerts[-limit:] if self.threshold_alerts else []
    
    def get_monitoring_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get monitoring events.
        
        Args:
            event_type: Optional event type filter
            limit: Maximum number of events to return
            
        Returns:
            List[Dict[str, Any]]: Monitoring events
        """
        events = self.monitoring_events
        
        # Filter by event type if specified
        if event_type:
            events = [event for event in events if event.get("type") == event_type]
        
        # Return most recent events
        return events[-limit:] if events else []
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update monitoring configuration.
        
        Args:
            new_config: New configuration values
        """
        self.config.update(new_config)
        logger.info(f"Resource monitoring configuration updated: {list(new_config.keys())}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current monitoring configuration.
        
        Returns:
            Dict[str, Any]: Current configuration
        """
        return self.config.copy()


class FallbackResourceMonitor:
    """
    Fallback resource monitor for when the main monitoring system is not available.
    """
    
    def __init__(self, features_available: Dict[str, bool]):
        """
        Initialize fallback resource monitor.
        
        Args:
            features_available: Available monitoring features
        """
        self.features_available = features_available
        self.thresholds = {}
        self.alert_config = {}
    
    async def set_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Set resource thresholds."""
        self.thresholds = thresholds
    
    async def set_alert_config(self, alert_config: Dict[str, bool]) -> None:
        """Set alert configuration."""
        self.alert_config = alert_config
    
    def on_threshold_alert(self, handler: callable) -> None:
        """Register threshold alert handler."""
        self.threshold_alert_handler = handler
    
    def on_resource_update(self, handler: callable) -> None:
        """Register resource update handler."""
        self.resource_update_handler = handler
