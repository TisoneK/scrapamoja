"""
Navigation system health checks and diagnostics

Provides comprehensive health monitoring and diagnostic capabilities for the navigation
system with component status checks, performance metrics, and system validation.
"""

import asyncio
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .logging_config import get_navigation_logger


@dataclass
class HealthCheckResult:
    """Health check result"""
    component_name: str
    status: str  # "healthy", "warning", "critical"
    message: str
    timestamp: datetime
    metrics: Dict[str, Any]


@dataclass
class SystemHealthStatus:
    """Overall system health status"""
    overall_status: str
    timestamp: datetime
    component_results: List[HealthCheckResult]
    system_metrics: Dict[str, Any]


class NavigationHealthChecker:
    """Navigation system health checker"""
    
    def __init__(self):
        """Initialize health checker"""
        self.logger = get_navigation_logger("health_checker")
    
    async def check_system_health(self) -> SystemHealthStatus:
        """Perform comprehensive system health check"""
        try:
            self.logger.info("Starting system health check")
            
            component_results = []
            
            # Check system resources
            system_result = await self._check_system_resources()
            component_results.append(system_result)
            
            # Check memory usage
            memory_result = await self._check_memory_usage()
            component_results.append(memory_result)
            
            # Check disk space
            disk_result = await self._check_disk_space()
            component_results.append(disk_result)
            
            # Calculate overall status
            statuses = [r.status for r in component_results]
            if "critical" in statuses:
                overall_status = "critical"
            elif "warning" in statuses:
                overall_status = "warning"
            else:
                overall_status = "healthy"
            
            system_metrics = self._collect_system_metrics()
            
            health_status = SystemHealthStatus(
                overall_status=overall_status,
                timestamp=datetime.utcnow(),
                component_results=component_results,
                system_metrics=system_metrics
            )
            
            self.logger.info(
                "System health check completed",
                overall_status=overall_status,
                components_checked=len(component_results)
            )
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            raise
    
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resources"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 90:
                status = "critical"
                message = f"High CPU usage: {cpu_percent}%"
            elif cpu_percent > 70:
                status = "warning"
                message = f"Elevated CPU usage: {cpu_percent}%"
            else:
                status = "healthy"
                message = f"CPU usage normal: {cpu_percent}%"
            
            return HealthCheckResult(
                component_name="system_resources",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                metrics={"cpu_percent": cpu_percent}
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name="system_resources",
                status="critical",
                message=f"Failed to check system resources: {str(e)}",
                timestamp=datetime.utcnow(),
                metrics={}
            )
    
    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent > 90:
                status = "critical"
                message = f"High memory usage: {memory_percent}%"
            elif memory_percent > 80:
                status = "warning"
                message = f"Elevated memory usage: {memory_percent}%"
            else:
                status = "healthy"
                message = f"Memory usage normal: {memory_percent}%"
            
            return HealthCheckResult(
                component_name="memory_usage",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                metrics={
                    "memory_percent": memory_percent,
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name="memory_usage",
                status="critical",
                message=f"Failed to check memory usage: {str(e)}",
                timestamp=datetime.utcnow(),
                metrics={}
            )
    
    async def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space"""
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            if disk_percent > 95:
                status = "critical"
                message = f"Low disk space: {disk_percent:.1f}% used"
            elif disk_percent > 85:
                status = "warning"
                message = f"Low disk space: {disk_percent:.1f}% used"
            else:
                status = "healthy"
                message = f"Disk space normal: {disk_percent:.1f}% used"
            
            return HealthCheckResult(
                component_name="disk_space",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                metrics={
                    "disk_percent": disk_percent,
                    "free_gb": disk.free / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "total_gb": disk.total / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component_name="disk_space",
                status="critical",
                message=f"Failed to check disk space: {str(e)}",
                timestamp=datetime.utcnow(),
                metrics={}
            )
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics"""
        try:
            return {
                "process_count": len(psutil.pids()),
                "boot_time": psutil.boot_time(),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "network_connections": len(psutil.net_connections()),
                "python_version": psutil.sys.version
            }
        except Exception:
            return {}


def create_health_checker() -> NavigationHealthChecker:
    """Create navigation health checker"""
    return NavigationHealthChecker()
