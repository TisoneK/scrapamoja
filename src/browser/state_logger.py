"""
State Persistence Logging

This module provides structured logging with correlation IDs for state persistence operations.
"""

import uuid
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import structlog


class StateOperation(Enum):
    """State persistence operation types."""
    SAVE = "save"
    LOAD = "load"
    DELETE = "delete"
    LIST = "list"
    CLEANUP = "cleanup"
    BACKUP = "backup"
    RESTORE = "restore"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    VALIDATE = "validate"
    REPAIR = "repair"


class OperationStatus(Enum):
    """Operation status types."""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StateOperationContext:
    """Context for state persistence operations."""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    state_id: Optional[str] = None
    operation: StateOperation = StateOperation.SAVE
    status: OperationStatus = OperationStatus.STARTED
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
        
        if success:
            self.status = OperationStatus.COMPLETED
        else:
            self.status = OperationStatus.FAILED
            self.error = error
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation_id": self.operation_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "state_id": self.state_id,
            "operation": self.operation.value,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "error": self.error,
            "error_type": self.error_type
        }


class StatePersistenceLogger:
    """Structured logger for state persistence operations."""
    
    def __init__(self, logger_name: str = "browser.state_persistence"):
        self.logger = structlog.get_logger(logger_name)
        self.active_operations: Dict[str, StateOperationContext] = {}
        
    def start_operation(
        self,
        operation: StateOperation,
        session_id: Optional[str] = None,
        state_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata
    ) -> StateOperationContext:
        """Start a new state persistence operation."""
        context = StateOperationContext(
            correlation_id=correlation_id,
            session_id=session_id,
            state_id=state_id,
            operation=operation,
            metadata=metadata
        )
        
        self.active_operations[context.operation_id] = context
        
        self.logger.info(
            "State operation started",
            **context.to_dict()
        )
        
        return context
        
    def update_operation(
        self,
        operation_id: str,
        status: OperationStatus = OperationStatus.IN_PROGRESS,
        **metadata_updates
    ) -> Optional[StateOperationContext]:
        """Update an existing operation."""
        context = self.active_operations.get(operation_id)
        if context is None:
            self.logger.warning(
                "Operation not found for update",
                operation_id=operation_id
            )
            return None
            
        context.status = status
        context.metadata.update(metadata_updates)
        
        self.logger.info(
            "State operation updated",
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
    ) -> Optional[StateOperationContext]:
        """Complete an operation."""
        context = self.active_operations.get(operation_id)
        if context is None:
            self.logger.warning(
                "Operation not found for completion",
                operation_id=operation_id
            )
            return None
            
        context.complete(success, error, error_type)
        context.metadata.update(final_metadata)
        
        log_level = "info" if success else "error"
        getattr(self.logger, log_level)(
            f"State operation {context.status.value}",
            **context.to_dict()
        )
        
        # Remove from active operations
        del self.active_operations[operation_id]
        
        return context
        
    def log_save_operation(
        self,
        session_id: str,
        state_id: str,
        success: bool,
        file_path: Optional[str] = None,
        encrypted: bool = False,
        cookie_count: int = 0,
        storage_items: int = 0,
        file_size_bytes: Optional[int] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log a save operation with specific details."""
        context = self.start_operation(
            StateOperation.SAVE,
            session_id=session_id,
            state_id=state_id,
            correlation_id=correlation_id,
            file_path=file_path,
            encrypted=encrypted,
            cookie_count=cookie_count,
            storage_items=storage_items
        )
        
        final_metadata = {}
        if file_size_bytes is not None:
            final_metadata["file_size_bytes"] = file_size_bytes
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="save_error" if error else None,
            **final_metadata
        )
        
    def log_load_operation(
        self,
        state_id: str,
        success: bool,
        session_id: Optional[str] = None,
        encrypted: bool = False,
        cookie_count: int = 0,
        storage_items: int = 0,
        file_size_bytes: Optional[int] = None,
        validation_issues: Optional[List[str]] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log a load operation with specific details."""
        context = self.start_operation(
            StateOperation.LOAD,
            session_id=session_id,
            state_id=state_id,
            correlation_id=correlation_id,
            encrypted=encrypted,
            cookie_count=cookie_count,
            storage_items=storage_items
        )
        
        final_metadata = {}
        if file_size_bytes is not None:
            final_metadata["file_size_bytes"] = file_size_bytes
        if validation_issues:
            final_metadata["validation_issues"] = validation_issues
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="load_error" if error else None,
            **final_metadata
        )
        
    def log_delete_operation(
        self,
        state_id: str,
        success: bool,
        file_deleted: bool = False,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log a delete operation with specific details."""
        context = self.start_operation(
            StateOperation.DELETE,
            state_id=state_id,
            correlation_id=correlation_id,
            file_deleted=file_deleted
        )
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="delete_error" if error else None
        )
        
    def log_cleanup_operation(
        self,
        success: bool,
        deleted_count: int = 0,
        retention_days: int = 0,
        total_scanned: int = 0,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log a cleanup operation with specific details."""
        context = self.start_operation(
            StateOperation.CLEANUP,
            correlation_id=correlation_id,
            retention_days=retention_days,
            total_scanned=total_scanned
        )
        
        final_metadata = {
            "deleted_count": deleted_count
        }
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="cleanup_error" if error else None,
            **final_metadata
        )
        
    def log_encryption_operation(
        self,
        operation: StateOperation,
        data_type: str,
        success: bool,
        data_size_bytes: Optional[int] = None,
        encryption_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log an encryption/decryption operation."""
        context = self.start_operation(
            operation,
            correlation_id=correlation_id,
            data_type=data_type,
            data_size_bytes=data_size_bytes
        )
        
        final_metadata = {}
        if encryption_time_ms is not None:
            final_metadata["encryption_time_ms"] = encryption_time_ms
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type=f"{operation.value}_error" if error else None,
            **final_metadata
        )
        
    def log_validation_operation(
        self,
        state_id: str,
        success: bool,
        is_valid: bool,
        issues: Optional[List[str]] = None,
        validation_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log a state validation operation."""
        context = self.start_operation(
            StateOperation.VALIDATE,
            state_id=state_id,
            correlation_id=correlation_id,
            is_valid=is_valid
        )
        
        final_metadata = {}
        if validation_time_ms is not None:
            final_metadata["validation_time_ms"] = validation_time_ms
        if issues:
            final_metadata["issues"] = issues
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="validation_error" if error else None,
            **final_metadata
        )
        
    def log_backup_operation(
        self,
        original_state_id: str,
        backup_state_id: str,
        success: bool,
        file_size_bytes: Optional[int] = None,
        backup_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log a backup operation."""
        context = self.start_operation(
            StateOperation.BACKUP,
            state_id=original_state_id,
            correlation_id=correlation_id,
            backup_state_id=backup_state_id,
            file_size_bytes=file_size_bytes
        )
        
        final_metadata = {}
        if backup_time_ms is not None:
            final_metadata["backup_time_ms"] = backup_time_ms
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="backup_error" if error else None,
            **final_metadata
        )
        
    def get_active_operations(self) -> List[StateOperationContext]:
        """Get all currently active operations."""
        return list(self.active_operations.values())
        
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics about operations."""
        return {
            "active_operations": len(self.active_operations),
            "active_operation_ids": list(self.active_operations.keys())
        }


# Global state persistence logger
state_logger = StatePersistenceLogger()


def get_state_logger() -> StatePersistenceLogger:
    """Get the global state persistence logger."""
    return state_logger


def log_state_operation(
    operation: StateOperation,
    success: bool,
    session_id: Optional[str] = None,
    state_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    error: Optional[str] = None,
    **metadata
) -> None:
    """Convenience function to log state operations."""
    if success:
        state_logger.start_operation(
            operation,
            session_id=session_id,
            state_id=state_id,
            correlation_id=correlation_id,
            **metadata
        )
        state_logger.complete_operation(
            list(state_logger.active_operations.keys())[-1],
            success=True
        )
    else:
        context = state_logger.start_operation(
            operation,
            session_id=session_id,
            state_id=state_id,
            correlation_id=correlation_id,
            **metadata
        )
        state_logger.complete_operation(
            context.operation_id,
            success=False,
            error=error
        )
