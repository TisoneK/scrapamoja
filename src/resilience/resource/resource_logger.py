"""
Resource Event Logging

Specialized logging for resource operations with detailed context,
correlation tracking, and structured output for debugging and analysis.
"""

import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..correlation import get_correlation_id
from ..models.resource import Resource, ResourceStatus, ResourceType, ResourceAction
from .resilience_logger import ResilienceLogger


class ResourceLogger:
    """Specialized logger for resource operations with enhanced context tracking."""
    
    def __init__(self, name: str = "resource_logger"):
        """Initialize resource logger."""
        self.logger = ResilienceLogger(name)
    
    def log_resource_created(
        self,
        resource: Resource,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log resource creation with comprehensive context."""
        context = {
            "resource_id": resource.id,
            "name": resource.name,
            "resource_type": resource.resource_type.value,
            "status": resource.status.value,
            "configuration": resource.configuration.to_dict() if resource.configuration else None,
            "description": resource.description,
            "tags": resource.tags,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Resource created: {resource.name} ({resource.resource_type.value})",
            event_type="resource_created",
            correlation_id=get_correlation_id(),
            context=context,
            component="resource_manager"
        )
    
    def log_resource_updated(
        self,
        resource: Resource,
        changes: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log resource updates with change details."""
        context = {
            "resource_id": resource.id,
            "name": resource.name,
            "resource_type": resource.resource_type.value,
            "status": resource.status.value,
            "changes": changes,
            "metrics": resource.metrics.to_dict(),
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Resource updated: {resource.name}",
            event_type="resource_updated",
            correlation_id=get_correlation_id(),
            context=context,
            component="resource_manager"
        )
    
    def log_resource_restarted(
        self,
        resource: Resource,
        reason: str,
        restart_time: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log resource restart with performance metrics."""
        context = {
            "resource_id": resource.id,
            "name": resource.name,
            "resource_type": resource.resource_type.value,
            "reason": reason,
            "restart_time": restart_time,
            "restart_count": resource.restart_count,
            "last_restart": resource.last_restart.isoformat() if resource.last_restart else None,
            "metrics": resource.metrics.to_dict(),
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Resource restarted: {resource.name} ({reason})",
            event_type="resource_restarted",
            correlation_id=get_correlation_id(),
            context=context,
            component="resource_manager"
        )
    
    def log_resource_throttled(
        self,
        resource_id: str,
        reason: str,
        current_metrics: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log resource throttling events."""
        context = {
            "resource_id": resource_id,
            "reason": reason,
            "current_metrics": current_metrics,
            **(additional_context or {})
        }
        
        self.logger.warning(
            f"Resource throttled: {resource_id} ({reason})",
            event_type="resource_throttled",
            correlation_id=get_correlation_id(),
            context=context,
            component="resource_manager"
        )
    
    def log_resource_cleanup(
        self,
        resource_id: str,
        cleanup_type: str,
        items_cleaned: int,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log resource cleanup operations."""
        context = {
            "resource_id": resource_id,
            "cleanup_type": cleanup_type,
            "items_cleaned": items_cleaned,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Resource cleanup: {resource_id} - {items_cleaned} items ({cleanup_type})",
            event_type="resource_cleanup",
            correlation_id=get_correlation_id(),
            context=context,
            component="resource_manager"
        )
    
    def log_memory_gc_completed(
        self,
        collected_objects: int,
        memory_freed_mb: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log garbage collection completion."""
        context = {
            "collected_objects": collected_objects,
            "memory_freed_mb": memory_freed_mb,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Garbage collection completed: {collected_objects} objects, {memory_freed_mb:.1f}MB freed",
            event_type="memory_gc_completed",
            correlation_id=get_correlation_id(),
            context=context,
            component="memory_monitor"
        )
    
    def log_memory_leak_detected(
        self,
        leak_rate: float,
        confidence: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log memory leak detection."""
        context = {
            "leak_rate_mb_per_hour": leak_rate,
            "confidence": confidence,
            **(additional_context or {})
        }
        
        self.logger.warning(
            f"Memory leak detected: {leak_rate:.1f}MB/hour (confidence: {confidence:.2f})",
            event_type="memory_leak_detected",
            correlation_id=get_correlation_id(),
            context=context,
            component="memory_monitor"
        )
    
    def log_browser_error(
        self,
        browser_id: str,
        error_message: str,
        error_count: int,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log browser errors."""
        context = {
            "browser_id": browser_id,
            "error_message": error_message,
            "error_count": error_count,
            **(additional_context or {})
        }
        
        self.logger.warning(
            f"Browser error: {browser_id} - {error_message} (count: {error_count})",
            event_type="browser_error",
            correlation_id=get_correlation_id(),
            context=context,
            component="browser_manager"
        )
    
    def log_browser_tabs_cleaned(
        self,
        browser_id: str,
        cleaned_count: int,
        remaining_tabs: int,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log browser tab cleanup."""
        context = {
            "browser_id": browser_id,
            "cleaned_count": cleaned_count,
            "remaining_tabs": remaining_tabs,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Browser tabs cleaned: {browser_id} - {cleaned_count} tabs removed, {remaining_tabs} remaining",
            event_type="browser_tabs_cleaned",
            correlation_id=get_correlation_id(),
            context=context,
            component="browser_manager"
        )
    
    def create_resource_report(
        self,
        resources: List[Dict[str, Any]],
        report_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a comprehensive resource report."""
        if not resources:
            return {
                "report_timestamp": datetime.utcnow().isoformat(),
                "total_resources": 0,
                "context": report_context or {}
            }
        
        # Calculate statistics
        total_resources = len(resources)
        status_counts = {}
        type_counts = {}
        
        for resource in resources:
            status = resource.get("status", "unknown")
            resource_type = resource.get("resource_type", "unknown")
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[resource_type] = type_counts.get(resource_type, 0) + 1
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "total_resources": total_resources,
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "context": report_context or {},
            "resource_details": resources
        }
        
        return report


# Global resource logger instance
_resource_logger = ResourceLogger()


def get_resource_logger() -> ResourceLogger:
    """Get the global resource logger instance."""
    return _resource_logger


def log_resource_created(
    resource: Resource,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log resource creation using the global logger."""
    _resource_logger.log_resource_created(resource, additional_context)


def log_resource_restarted(
    resource: Resource,
    reason: str,
    restart_time: float,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log resource restart using the global logger."""
    _resource_logger.log_resource_restarted(resource, reason, restart_time, additional_context)
