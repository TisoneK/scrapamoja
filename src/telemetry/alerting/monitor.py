"""
Real-time Monitoring Loop

Background monitoring loop for continuous alerting system
health checks, performance monitoring, and automated responses.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import psutil

from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class MonitoringStatus(Enum):
    """Monitoring status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Health check result."""
    component: str
    status: MonitoringStatus
    message: str
    response_time_ms: float
    last_check: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringMetrics:
    """Monitoring metrics for the alerting system."""
    total_checks: int = 0
    healthy_checks: int = 0
    warning_checks: int = 0
    degraded_checks: int = 0
    error_checks: int = 0
    critical_checks: int = 0
    average_response_time_ms: float = 0.0
    uptime_percentage: float = 0.0
    last_check: Optional[datetime] = None
    component_status: Dict[str, MonitoringStatus] = field(default_factory=dict)


class RealTimeMonitor:
    """
    Real-time monitoring loop for alerting system.
    
    Provides continuous health monitoring, performance tracking,
    and automated response capabilities.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize real-time monitor.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("real_time_monitor")
        
        # Monitoring configuration
        self.enabled = config.get("real_time_monitoring_enabled", True)
        self.health_check_interval_seconds = config.get("health_check_interval_seconds", 60)
        self.performance_check_interval_seconds = config.get("performance_check_interval_seconds", 300)
        self.automated_response_enabled = config.get("automated_response_enabled", True)
        self.max_response_attempts = config.get("max_response_attempts", 3)
        
        # Monitoring state
        self._monitoring_active = False
        self._shutdown_event = asyncio.Event()
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Health checks
        self._health_checks: List[Callable] = []
        self._health_check_results: Dict[str, HealthCheck] = {}
        
        # Performance metrics
        self._metrics = MonitoringMetrics()
        self._metrics_lock = asyncio.Lock()
        
        # Automated response
        self._response_rules: List[Dict[str, Any]] = []
        
        # Initialize default health checks
        self._initialize_health_checks()
        
        # Initialize default response rules
        self._initialize_response_rules()
        
        # Start monitoring if enabled
        if self.enabled:
            self._start_monitoring()
    
    async def start_monitoring(self) -> None:
        """Start real-time monitoring."""
        if self.enabled and not self._monitoring_active:
            self._monitoring_active = True
            self._shutdown_event.clear()
            self._start_monitoring_loop()
            
            self.logger.info("Real-time monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop real-time monitoring."""
        self._monitoring_active = False
        self._shutdown_event.set()
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        self.logger.info("Real-time monitoring stopped")
    
    async def add_health_check(self, check_func: Callable, component_name: str) -> bool:
        """
        Add a health check function.
        
        Args:
            check_func: Health check function
            component_name: Name of the component
            
        Returns:
            True if successfully added
        """
        try:
            self._health_checks.append(check_func)
            
            self.logger.info(
                "Health check added",
                component_name=component_name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add health check",
                component_name=component_name,
                error=str(e)
            )
            return False
    
    async def remove_health_check(self, component_name: str) -> bool:
        """
        Remove a health check function.
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if successfully removed
        """
        try:
            # Find and remove check by component name
            for i, check in enumerate(self._health_checks):
                if hasattr(check, '__name__') and check.__name__ == component_name:
                    self._health_checks.pop(i)
                    break
            else:
                # Try to find by checking if it's a wrapper
                for i, check in enumerate(self._health_checks):
                    if hasattr(check, '__self__') and hasattr(check.__self__, '__name__') and check.__self__.__name__ == component_name:
                        self._health_checks.pop(i)
                        break
            
            self.logger.info(
                "Health check removed",
                component_name=component_name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to remove health check",
                component_name=component_name,
                error=str(e)
            )
            return False
    
    async def add_response_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Add an automated response rule.
        
        Args:
            rule: Response rule configuration
            
        Returns:
            True if successfully added
        """
        try:
            self._response_rules.append(rule)
            
            self.logger.info(
                "Response rule added",
                rule_name=rule.get("name", "unknown")
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add response rule",
                rule=rule.get("name", "unknown"),
                error=str(e)
            )
            return False
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status.
        
        Returns:
            Monitoring status information
        """
        try:
            async with self._metrics_lock:
                return {
                    "monitoring_active": self._monitoring_active,
                    "enabled": self.enabled,
                    "health_check_interval_seconds": self.health_check_interval_seconds,
                    "performance_check_interval_seconds": self.performance_check_interval_seconds,
                    "automated_response_enabled": self.automated_response_enabled,
                    "total_checks": self._metrics.total_checks,
                    "healthy_checks": self._metrics.healthy_checks,
                    "warning_checks": self._metrics.warning_checks,
                    "degraded_checks": self._metrics.degraded_checks,
                    "error_checks": self._metrics.error_checks,
                    "critical_checks": self._metrics.critical_checks,
                    "average_response_time_ms": self._metrics.average_response_time_ms,
                    "uptime_percentage": self._metrics.uptime_percentage,
                    "last_check": self._metrics.last_check,
                    "component_status": dict(self._metrics.component_status),
                    "health_checks_count": len(self._health_checks),
                    "response_rules_count": len(self._response_rules)
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get monitoring status",
                error=str(e)
            )
            return {}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of all components.
        
        Returns:
            Health status information
        """
        try:
            async with self._metrics_lock:
                status_counts = {
                    MonitoringStatus.HEALTHY: self._metrics.healthy_checks,
                    MonitoringStatus.WARNING: self._metrics.warning_checks,
                    MonitoringStatus.DEGRADED: self._metrics.degraded_checks,
                    MonitoringStatus.ERROR: self._metrics.error_checks,
                    MonitoringStatus.CRITICAL: self._metrics.critical_checks
                }
                
                component_status = dict(self._metrics.component_status)
                
                return {
                    "overall_status": self._determine_overall_status(status_counts),
                    "status_counts": {status.value: count for status, count in status_counts.items()},
                    "component_status": component_status,
                    "last_check": self._metrics.last_check,
                    "total_checks": self._metrics.total_checks,
                    "uptime_percentage": self._metrics.uptime_percentage
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get health status",
                error=str(e)
            )
            return {}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Performance metrics information
        """
        try:
            async with self._metrics_lock:
                return {
                    "total_checks": self._metrics.total_checks,
                    "healthy_checks": self._metrics.healthy_checks,
                    "warning_checks": self._metrics.warning_checks,
                    "degraded_checks": self._metrics.degraded_checks,
                    "error_checks": self._metrics.error_checks,
                    "critical_checks": self._metrics.critical_checks,
                    "average_response_time_ms": self._metrics.average_response_time_ms,
                    "uptime_percentage": self._metrics.uptime_percentage,
                    "last_check": self._metrics.last_check,
                    "component_status": dict(self._metrics.component_status),
                    "health_checks_count": len(self._health_checks),
                    "response_rules_count": len(self._response_rules)
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get performance metrics",
                error=str(e)
            )
            return {}
    
    async def get_health_check_results(self) -> Dict[str, HealthCheck]:
        """
        Get results of all health checks.
        
        Returns:
            Health check results by component
        """
        try:
            return dict(self._health_check_results)
            
        except Exception as e:
            self.logger.error(
                "Failed to get health check results",
                error=str(e)
            )
            return {}
    
    async def get_response_rules(self) -> List[Dict[str, Any]]:
        """
        Get all automated response rules.
        
        Returns:
            List of response rules
        """
        try:
            return self._response_rules.copy()
            
        except Exception as e:
            self.logger.error(
                "Failed to get response rules",
                error=str(e)
            )
            return []
    
    async def trigger_health_check(self, component_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger health check for specific component or all components.
        
        Args:
            component_name: Optional component name to check
            
        Returns:
            Health check results
        """
        try:
            start_time = datetime.utcnow()
            results = {}
            
            if component_name:
                # Check specific component
                for check in self._health_checks:
                    if hasattr(check, '__name__') and check.__name__ == component_name:
                        result = await self._execute_health_check(check, component_name)
                        results[component_name] = result
                        break
                    elif hasattr(check, '__self__') and hasattr(check.__self__, '__name__') and check.__self__.__name__ == component_name:
                        result = await self._execute_health_check(check, component_name)
                        results[component_name] = result
                        break
            else:
                # Check all components
                for i, check in enumerate(self._health_checks):
                    component_name = f"component_{i}"
                    result = await self._execute_health_check(check, component_name)
                    results[component_name] = result
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to trigger health check",
                component_name=component_name,
                error=str(e)
            )
            return {}
    
    # Private methods
    
    def _start_monitoring_loop(self) -> None:
        """Start the monitoring loop."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for health check interval or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.health_check_interval_seconds
                )
                
                if self._shutdown_event.is_set():
                    break
                
                # Perform health checks
                await self._perform_health_checks()
                
                # Perform performance checks
                if self._metrics.total_checks % (self.performance_check_interval_seconds // self.health_check_interval_seconds) == 0:
                    await self._perform_performance_checks()
                
                # Check for automated responses
                if self.automated_response_enabled:
                    await self._check_automated_responses()
                
            except asyncio.TimeoutError:
                # Timeout - continue with next iteration
                continue
            except Exception as e:
                self.logger.error(
                    "Monitoring loop error",
                    error=str(e)
                )
                await asyncio.sleep(10.0)  # Brief pause before retrying
    
    async def _perform_health_checks(self) -> None:
        """Perform all health checks."""
        try:
            start_time = datetime.utcnow()
            
            for i, check in enumerate(self._health_checks):
                component_name = f"component_{i}"
                
                try:
                    result = await self._execute_health_check(check, component_name)
                    self._health_check_results[component_name] = result
                    
                    # Update metrics
                    await self._update_health_metrics(result)
                    
                except Exception as e:
                    # Create error result for failed check
                    error_result = HealthCheck(
                        component=component_name,
                        status=MonitoringStatus.ERROR,
                        message=f"Health check failed: {str(e)}",
                        response_time_ms=0,
                        last_check=datetime.utcnow(),
                        error_details={"error": str(e)}
                    )
                    
                    self._health_check_results[component_name] = error_result
                    await self._update_health_metrics(error_result)
            
            self._metrics.last_check = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(
                "Failed to perform health checks",
                error=str(e)
            )
    
    async def _execute_health_check(self, check: Callable, component_name: str) -> HealthCheck:
        """Execute a single health check."""
        start_time = datetime.utcnow()
        
        try:
            # Execute health check
            result = await check()
            
            # Handle different result types
            if isinstance(result, dict):
                # Result is already a dictionary
                health_result = HealthCheck(
                    component=component_name,
                    status=MonitoringStatus(result.get("status", MonitoringStatus.ERROR),
                    message=result.get("message", "Health check completed"),
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    last_check=datetime.utcnow(),
                    details=result.get("details", {})
                )
            elif isinstance(result, tuple):
                # Result is a tuple (status, message)
                status, message = result
                health_result = HealthCheck(
                    component=component_name,
                    status=status,
                    message=message,
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    last_check=datetime.utcnow()
                )
            elif isinstance(result, bool):
                # Result is a boolean
                health_result = HealthCheck(
                    component=component_name,
                    status=MonitoringStatus.HEALTHY if result else MonitoringStatus.ERROR,
                    message="Health check passed" if result else "Health check failed",
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    last_check=datetime.utcnow()
                )
            else:
                # Unknown result type
                health_result = HealthCheck(
                    component=component_name,
                    status=MonitoringStatus.WARNING,
                    message="Unknown health check result type",
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    last_check=datetime.utcnow(),
                    details={"result_type": str(type(result))}
                )
                
            return health_result
            
        except Exception as e:
            return HealthCheck(
                component=component_name,
                status=MonitoringStatus.ERROR,
                message=f"Health check exception: {str(e)}",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                last_check=datetime.utcnow(),
                error_details={"error": str(e), "type": type(e).__name__}
            )
    
    async def _update_health_metrics(self, result: HealthCheck) -> None:
        """Update health check metrics."""
        try:
            async with self._metrics_lock:
                self._metrics.total_checks += 1
                
                # Update status counts
                if result.status == MonitoringStatus.HEALTHY:
                    self._metrics.healthy_checks += 1
                elif result.status == MonitoringStatus.WARNING:
                    self._metrics.warning_checks += 1
                elif result.status == MonitoringStatus.DEGRADED:
                    self._metrics.degraded_checks += 1
                elif result.status == MonitoringStatus.ERROR:
                    self._metrics.error_checks += 1
                elif result.status == MonitoringStatus.CRITICAL:
                    self._metrics.critical_checks += 1
                
                # Update component status
                self._metrics.component_status[result.component] = result.status
                
                # Update average response time
                if result.response_time_ms is not None:
                    total_checks = self._metrics.total_checks
                    current_avg = self._metrics.average_response_time_ms
                    new_avg = ((current_avg * (total_checks - 1)) + result.response_time_ms) / total_checks
                    self._metrics.average_response_time_ms = new_avg
                
                # Update uptime percentage
                if self._metrics.total_checks > 0:
                    self._metrics.uptime_percentage = (
                        self._metrics.healthy_checks / self._metrics.total_checks
                    ) * 100
                
                self._metrics.last_check = result.last_check
                
        except Exception as e:
            self.logger.error(
                "Failed to update health metrics",
                error=str(e)
            )
    
    async def _perform_performance_checks(self) -> None:
        """Perform performance checks."""
        try:
            # Check memory usage
            memory_info = psutil.virtual_memory()
            
            memory_usage_percent = (memory_info.used / memory_info.total) * 100
            
            # Check CPU usage
            cpu_usage_percent = psutil.cpu_percent()
            
            # Check disk usage
            disk_usage = psutil.disk_usage('/')
            disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Log performance metrics
            self.logger.debug(
                "Performance metrics",
                memory_usage_percent=memory_usage_percent,
                cpu_usage_percent=cpu_usage_percent,
                disk_usage_percent=disk_usage_percent
            )
            
            # Check if any metric exceeds threshold
            performance_threshold = 80.0
            if memory_usage_percent > performance_threshold:
                self.logger.warning(
                    "High memory usage detected",
                    usage_percent=memory_usage_percent
                )
            
            if cpu_usage_percent > performance_threshold:
                self.logger.warning(
                    "High CPU usage detected",
                    usage_percent=cpu_usage_percent
                )
            
            if disk_usage_percent > performance_threshold:
                self.logger.warning(
                    "High disk usage detected",
                    usage_percent=disk_usage_percent
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to perform performance checks",
                error=str(e)
            )
    
    async def _check_automated_responses(self) -> None:
        """Check for automated responses."""
        try:
            # Check for critical alerts that need automated response
            critical_components = [
                name for name, status in self._metrics.component_status.items()
                if status in [MonitoringStatus.CRITICAL, MonitoringStatus.ERROR]
            ]
            
            for component_name in critical_components:
                # Find response rules for this component
                for rule in self._response_rules:
                    if rule.get("component") == component_name:
                        await self._execute_response_rule(rule)
                        
            # Check for degraded components
            degraded_components = [
                name for name, status in self._metrics.component_status.items()
                if status == MonitoringStatus.DEGRADED
            ]
            
            for component_name in degraded_components:
                # Find response rules for this component
                for rule in self._response_rules:
                    if rule.get("component") == component_name:
                        await self._execute_response_rule(rule)
                        
        except Exception as e:
            self.logger.error(
                "Failed to check automated responses",
                error=str(e)
            )
    
    async def _execute_response_rule(self, rule: Dict[str, Any]) -> None:
        """Execute an automated response rule."""
        try:
            rule_name = rule.get("name", "unknown")
            component = rule.get("component")
            condition = rule.get("condition")
            action = rule.get("action")
            
            # Check if condition is met
            if self._evaluate_rule_condition(condition, component):
                self.logger.warning(
                    "Executing automated response",
                    rule_name=rule_name,
                    component=component,
                    action=action
                )
                
                # Execute action
                await self._execute_action(action, rule)
                
        except Exception as e:
            self.logger.error(
                "Failed to execute response rule",
                rule_name=rule_name,
                error=str(e)
            )
    
    def _evaluate_rule_condition(self, condition: Any, component: str) -> bool:
        """Evaluate rule condition."""
        try:
            # Get component status
            component_status = self._metrics.component_status.get(component, MonitoringStatus.ERROR)
            
            # Simple condition evaluation
            if isinstance(condition, str):
                if condition == "critical":
                    return component_status == MonitoringStatus.CRITICAL
                elif condition == "error":
                    return component_status == MonitoringStatus.ERROR
                elif condition == "degraded":
                    return component_status == MonitoringStatus.DEGRADED
                elif condition == "unhealthy":
                    return component_status in [MonitoringStatus.ERROR, MonitoringStatus.CRITICAL, MonitoringStatus.DEGRADED]
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate rule condition",
                condition=condition,
                error=str(e)
            )
            return False
    
    async def _execute_action(self, action: str, rule: Dict[str, Any]) -> None:
        """Execute an automated action."""
        try:
            action_name = action.lower()
            
            if action_name == "restart_component":
                await self._restart_component(rule)
            elif action_name == "escalate_alert":
                await self._escalate_alert(rule)
            elif action_name == "send_notification":
                await self._send_notification(rule)
            elif action_name == "disable_feature":
                await self._disable_feature(rule)
            else:
                self.logger.warning(
                    "Unknown action in response rule",
                    action=action,
                    rule_name=rule.get("name")
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to execute action",
                action=action,
                error=str(e)
            )
    
    async def _restart_component(self, rule: Dict[str, Any]) -> None:
        """Restart a component."""
        self.logger.info(f"Restarting component: {rule.get('component')}")
        # Implementation would depend on the specific component
        # This is a placeholder for component restart logic
    
    async def _escalate_alert(self, rule: Dict[str, Any]) -> None:
        """Escalate an alert."""
        self.logger.warning(f"Escalating alert: {rule.get('alert_id')}")
        # Implementation would depend on the alert manager
        # This is a placeholder for alert escalation logic
    
    async def _send_notification(self, rule: Dict[str, Any]) -> None:
        """Send a notification."""
        self.logger.info(f"Sending notification: {rule.get('message')}")
        # Implementation would depend on the notifier
        # This is a placeholder for notification sending logic
    
    async def _disable_feature(self, rule: Dict[str, Any]) -> None:
        """Disable a feature."""
        self.logger.info(f"Disabling feature: {rule.get('feature')}")
        # Implementation would depend on the specific feature
        # This is a placeholder for feature disabling logic
    
    def _determine_overall_status(self, status_counts: Dict[str, int]) -> str:
        """Determine overall system status from status counts."""
        if status_counts.get(MonitoringStatus.CRITICAL.value, 0) > 0:
            return MonitoringStatus.CRITICAL.value
        elif status_counts.get(MonitoringStatus.ERROR.value, 0) > 0:
            return MonitoringStatus.ERROR.value
        elif status_counts.get(MonitoringStatus.DEGRADED.value, 0) > 0:
            return MonitoringStatus.DEGRADED.value
        elif status_counts.get(MonitoringStatus.WARNING.value, 0) > 0:
            return MonitoringStatus.WARNING.value
        elif status_counts.get(MonitoringStatus.HEALTHY.value, 0) > 0:
            return MonitoringStatus.HEALTHY.value
        else:
            return MonitoringStatus.ERROR.value
    
    def _initialize_default_health_checks(self) -> None:
        """Initialize default health checks."""
        # This would be populated with actual health check functions
        # For now, we'll add placeholder checks
        
        # Placeholder health check for alert engine
        async def check_alert_engine():
            return {
                "status": "healthy",
                "message": "Alert engine is operational",
                "details": {
                    "enabled": True,
                    "active_alerts": 0
                }
            }
        
        # Placeholder health check for threshold monitor
        async def check_threshold_monitor():
            return {
                "status": "healthy",
                "message": "Threshold monitor is operational",
                "details": {
                    "enabled": True,
                    "active_thresholds": 0
                }
            }
        
        # Placeholder health check for performance evaluator
        async def check_performance_evaluator():
            return {
                "status": "healthy",
                "message": "Performance evaluator is operational",
                "details": {
                    "enabled": True,
                    "evaluations_performed": 0
                }
            }
        
        # Add placeholder checks
        self._health_checks.extend([
            check_alert_engine,
            check_threshold_monitor,
            check_performance_evaluator
        ])
    
    def _initialize_default_response_rules(self) -> None:
        """Initialize default automated response rules."""
        # This would be populated with actual response rules
        # For now, we'll add placeholder rules
        
        # Placeholder rule for critical component restart
        self._response_rules.append({
            "name": "critical_component_restart",
            "component": "component_0",  # Would be actual component name
            "condition": "critical",
            "action": "restart_component",
            "max_attempts": 3,
            "cooldown_minutes": 5
        })
        
        # Placeholder rule for error notification
        self._response_rules.append({
            "name": "error_notification",
            "component": "component_0",
            "condition": "error",
            "action": "send_notification",
            "message": "Component {component} is in error state"
        })
        
        # Placeholder rule for degraded component escalation
        self._response_rules.append({
            "name": "degraded_escalation",
            "component": "component_0",
            "condition": "degraded",
            "action": "escalate_alert",
            "escalation_level": "level_1",
            "message": "Component {component} performance is degraded"
        })
