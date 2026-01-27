"""
Configuration Logging

This module provides structured logging with correlation IDs for configuration operations.
"""

import uuid
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import structlog

from .resource_logger import ResourceOperation, get_resource_logger


class ConfigurationOperation(Enum):
    """Configuration operation types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VALIDATE = "validate"
    CLONE = "clone"
    EXPORT = "export"
    IMPORT = "import"
    LIST = "list"
    GET_DEFAULT = "get_default"


@dataclass
class ConfigurationOperationContext:
    """Context for configuration operations."""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4().hex[:8])
    correlation_id: Optional[str] = None
    config_id: Optional[str] = None
    operation: ConfigurationOperation = ConfigurationOperation.CREATE
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark operation as completed."""
        self.completed_at = time.time()
        self.duration_ms = (self.completed_at - self.started_at) * 1000
        
        if not success:
            self.error = error
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation_id": self.operation_id,
            "correlation_id": self.correlation_id,
            "config_id": self.config_id,
            "operation": self.operation.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "error": self.error,
            "error_type": self.error_type
        }


class ConfigurationLogger:
    """Structured logger for configuration operations."""
    
    def __init__(self, logger_name: str = "browser.configuration"):
        self.logger = structlog.get_logger(logger_name)
        self.active_operations: Dict[str, ConfigurationOperationContext] = {}
        
    def start_operation(
        self,
        operation: ConfigurationOperation,
        config_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata
    ) -> ConfigurationOperationContext:
        """Start a new configuration operation."""
        context = ConfigurationOperationContext(
            correlation_id=correlation_id,
            config_id=config_id,
            operation=operation,
            metadata=metadata
        )
        
        self.active_operations[context.operation_id] = context
        
        self.logger.info(
            "Configuration operation started",
            **context.to_dict()
        )
        
        return context
        
    def complete_operation(
        self,
        operation_id: str,
        success: bool = True,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        **final_metadata
    ) -> Optional[ConfigurationOperationContext]:
        """Complete an operation."""
        context = self.active_operations.get(operation_id)
        if context is None:
            self.logger.warning(
                "Operation not found for completion",
                operation_id=operation_id
            )
            return None
            
        context.complete(success, error)
        context.error_type = error_type
        context.metadata.update(final_metadata)
        
        log_level = "info" if success else "error"
        getattr(self.logger, log_level)(
            f"Configuration operation {context.operation.value}",
            **context.to_dict()
        )
        
        # Remove from active operations
        del self.active_operations[operation_id]
        
        return context
        
    def log_configuration_creation(
        self,
        config_id: str,
        browser_type: str,
        headless: bool,
        viewport_width: int,
        viewport_height: int,
        success: bool,
        validation_issues: Optional[List[str]] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration creation operation."""
        context = self.start_operation(
            ConfigurationOperation.CREATE,
            config_id=config_id,
            correlation_id=correlation_id,
            browser_type=browser_type,
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height
        )
        
        final_metadata = {}
        if validation_issues:
            final_metadata["validation_issues"] = validation_issues
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="validation_error" if error else None,
            **final_metadata
        )
        
        return context.operation_id
        
    def log_configuration_update(
        self,
        config_id: str,
        updates: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration update operation."""
        context = self.start_operation(
            ConfigurationOperation.UPDATE,
            config_id=config_id,
            correlation_id=correlation_id,
            updates=updates
        )
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="update_error" if error else None
        )
        
        return context.operation_id
        
    def log_configuration_delete(
        self,
        config_id: str,
        success: bool,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration deletion operation."""
        context = self.start_operation(
            ConfigurationOperation.DELETE,
            config_id=config_id,
            correlation_id=correlation_id
        )
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="delete_error" if error else None
        )
        
        return context.operation_id
        
    def log_configuration_validation(
        self,
        config_id: str,
        validation_result,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration validation operation."""
        context = self.start_operation(
            ConfigurationOperation.VALIDATE,
            config_id=config_id,
            correlation_id=correlation_id,
            validation_result=validation_result.to_dict()
        )
        
        success = validation_result.is_valid
        self.complete_operation(
            context.operation_id,
            success=success,
            error=None if success else "; ". ".join(validation_result.errors),
            error_type="validation_error" if not success else None
        )
        
        return context.operation_id
        
    def log_configuration_clone(
        self,
        source_config_id: str,
        new_config_id: str,
        success: bool,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration clone operation."""
        context = self.start_operation(
            ConfigurationOperation.CLONE,
            correlation_id=correlation_id,
            source_config_id=source_config_id,
            new_config_id=new_config_id
        )
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="clone_error" if error else None
        )
        
        return context.operation_id
        
    def log_configuration_export(
        self,
        config_id: str,
        file_path: str,
        success: bool,
        file_size_bytes: Optional[int] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration export operation."""
        context = self.start_operation(
            ConfigurationOperation.EXPORT,
            config_id=config_id,
            correlation_id=correlation_id,
            file_path=file_path
        )
        
        final_metadata = {}
        if file_size_bytes is not None:
            final_metadata["file_size_bytes"] = file_size_bytes
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="export_error" if error else None,
            **final_metadata
        )
        
        return context.operation_id
        
    def log_configuration_import(
        self,
        file_path: str,
        config_id: Optional[str] = None,
        success: bool,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration import operation."""
        context = self.start_operation(
            ConfigurationOperation.IMPORT,
            correlation_id=correlation_id,
            file_path=file_path,
            config_id=config_id
        )
        
        final_metadata = {}
        if config_id:
            final_metadata["config_id"] = config_id
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="import_error" if error else None,
            **final_metadata
        )
        
        return context.operation_id
        
    def log_configuration_list(
        self,
        config_count: int,
        success: bool,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log configuration list operation."""
        context = self.start_operation(
            ConfigurationOperation.LIST,
            correlation_id=correlation_id,
            config_count=config_count
        )
        
        final_metadata = {}
        if error:
            final_metadata["error"] = error
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="list_error" if error else None,
            **final_metadata
        )
        
        return context.operation_id
        
    def log_get_default(self, success: bool, default_config_id: Optional[str] = None, error: Optional[str] = None, correlation_id: Optional[str] = None) -> str:
        """Log get default configuration operation."""
        context = self.start_operation(
            ConfigurationOperation.GET_DEFAULT,
            correlation_id=correlation_id,
            default_config_id=default_config_id
        )
        
        final_metadata = {}
        if default_config_id:
            final_metadata["default_config_id"] = default_config_id
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="get_default_error" if error else None,
            **final_metadata
        )
        
        return context.operation_id
        
    def get_active_operations(self) -> List[ConfigurationOperationContext]:
        """Get all currently active configuration operations."""
        return list(self.active_operations.values())
        
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics about configuration operations."""
        return {
            "active_operations": len(self.active_operations),
            "active_operation_ids": list(self.active_operations.keys())
        }


# Global configuration logger instance
configuration_logger = ConfigurationLogger()


def get_configuration_logger() -> ConfigurationLogger:
    """Get the global configuration logger instance."""
    return configuration_logger


def log_configuration_operation(
    operation: ConfigurationOperation,
    success: bool = True,
    config_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    error: Optional[str] = None,
    **metadata
) -> str:
    """Convenience function to log configuration operations."""
    if success:
        context = configuration_logger.start_operation(
            operation,
            config_id=config_id,
            correlation_id=correlation_id,
            **metadata
        )
        configuration_logger.complete_operation(context.operation_id, success=True)
    else:
        context = configuration_logger.start_operation(
            operation,
            config_id=config_id,
            correlation_id=correlation_id,
            **metadata
        )
        configuration_logger.complete_operation(
            context.operation_id, success=False, error=error
        )
        
        return context.operation_id
