"""
Checkpoint Event Logging

Specialized logging for checkpoint operations with detailed context,
correlation tracking, and structured output for debugging and analysis.
"""

import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..correlation import get_correlation_id
from ..models.checkpoint import Checkpoint, CheckpointStatus, CheckpointType
from .resilience_logger import ResilienceLogger


class CheckpointLogger:
    """Specialized logger for checkpoint operations with enhanced context tracking."""
    
    def __init__(self, name: str = "checkpoint_logger"):
        """
        Initialize checkpoint logger.
        
        Args:
            name: Logger name
        """
        self.logger = ResilienceLogger(name)
    
    def log_checkpoint_created(
        self,
        checkpoint: Checkpoint,
        file_path: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint creation with comprehensive context.
        
        Args:
            checkpoint: The checkpoint that was created
            file_path: Path where checkpoint was saved
            additional_context: Additional context information
        """
        context = {
            "checkpoint_id": checkpoint.id,
            "job_id": checkpoint.job_id,
            "sequence_number": checkpoint.sequence_number,
            "checkpoint_type": checkpoint.checkpoint_type.value,
            "status": checkpoint.status.value,
            "file_path": file_path,
            "size_bytes": checkpoint.size_bytes,
            "compressed_size_bytes": checkpoint.compressed_size_bytes,
            "compression_ratio": checkpoint.get_compression_ratio(),
            "checksum": checkpoint.checksum,
            "encryption_enabled": checkpoint.encryption_enabled,
            "schema_version": checkpoint.schema_version,
            "description": checkpoint.description,
            "tags": checkpoint.tags,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint created: {checkpoint.id} for job {checkpoint.job_id}",
            event_type="checkpoint_created",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_loaded(
        self,
        checkpoint: Checkpoint,
        file_path: str,
        load_time: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint loading with performance metrics.
        
        Args:
            checkpoint: The checkpoint that was loaded
            file_path: Path where checkpoint was loaded from
            load_time: Time taken to load the checkpoint
            additional_context: Additional context information
        """
        context = {
            "checkpoint_id": checkpoint.id,
            "job_id": checkpoint.job_id,
            "sequence_number": checkpoint.sequence_number,
            "checkpoint_type": checkpoint.checkpoint_type.value,
            "status": checkpoint.status.value,
            "file_path": file_path,
            "load_time": load_time,
            "size_bytes": checkpoint.size_bytes,
            "compressed_size_bytes": checkpoint.compressed_size_bytes,
            "age_seconds": checkpoint.get_age_seconds(),
            "age_minutes": checkpoint.get_age_minutes(),
            "age_hours": checkpoint.get_age_hours(),
            "checksum": checkpoint.checksum,
            "schema_version": checkpoint.schema_version,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint loaded: {checkpoint.id} for job {checkpoint.job_id} "
            f"(age: {checkpoint.get_age_minutes():.1f}m, load_time: {load_time:.3f}s)",
            event_type="checkpoint_loaded",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_deleted(
        self,
        checkpoint_id: str,
        job_id: str,
        reason: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint deletion with reason and context.
        
        Args:
            checkpoint_id: ID of deleted checkpoint
            job_id: Job ID
            reason: Reason for deletion
            additional_context: Additional context information
        """
        context = {
            "checkpoint_id": checkpoint_id,
            "job_id": job_id,
            "reason": reason,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint deleted: {checkpoint_id} for job {job_id} ({reason})",
            event_type="checkpoint_deleted",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_corruption_detected(
        self,
        checkpoint_id: str,
        job_id: str,
        corruption_type: str,
        severity: str,
        details: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint corruption detection with detailed analysis.
        
        Args:
            checkpoint_id: ID of corrupted checkpoint
            job_id: Job ID
            corruption_type: Type of corruption detected
            severity: Severity level
            details: Corruption details
            additional_context: Additional context information
        """
        context = {
            "checkpoint_id": checkpoint_id,
            "job_id": job_id,
            "corruption_type": corruption_type,
            "severity": severity,
            "details": details,
            **(additional_context or {})
        }
        
        log_level = "critical" if severity == "critical" else "error"
        
        getattr(self.logger, log_level)(
            f"Checkpoint corruption detected: {checkpoint_id} ({corruption_type}, {severity})",
            event_type="checkpoint_corruption_detected",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_recovery(
        self,
        checkpoint_id: str,
        job_id: str,
        recovery_action: str,
        recovery_details: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint recovery actions.
        
        Args:
            checkpoint_id: ID of recovered checkpoint
            job_id: Job ID
            recovery_action: Recovery action taken
            recovery_details: Recovery details
            additional_context: Additional context information
        """
        context = {
            "checkpoint_id": checkpoint_id,
            "job_id": job_id,
            "recovery_action": recovery_action,
            "recovery_details": recovery_details,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint recovery: {checkpoint_id} ({recovery_action})",
            event_type="checkpoint_recovery",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_migration(
        self,
        checkpoint_id: str,
        job_id: str,
        from_version: str,
        to_version: str,
        migration_time: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint schema migration.
        
        Args:
            checkpoint_id: ID of migrated checkpoint
            job_id: Job ID
            from_version: Source schema version
            to_version: Target schema version
            migration_time: Time taken for migration
            additional_context: Additional context information
        """
        context = {
            "checkpoint_id": checkpoint_id,
            "job_id": job_id,
            "from_version": from_version,
            "to_version": to_version,
            "migration_time": migration_time,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint migrated: {checkpoint_id} ({from_version} -> {to_version}) "
            f"in {migration_time:.3f}s",
            event_type="checkpoint_migrated",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_cleanup(
        self,
        job_id: str,
        cleaned_count: int,
        cleanup_reason: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint cleanup operations.
        
        Args:
            job_id: Job ID
            cleaned_count: Number of checkpoints cleaned up
            cleanup_reason: Reason for cleanup
            additional_context: Additional context information
        """
        context = {
            "job_id": job_id,
            "cleaned_count": cleaned_count,
            "cleanup_reason": cleanup_reason,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint cleanup: {cleaned_count} checkpoints for job {job_id} ({cleanup_reason})",
            event_type="checkpoint_cleanup",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_batch_operation(
        self,
        operation: str,
        job_id: str,
        total_count: int,
        success_count: int,
        failure_count: int,
        duration: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log batch checkpoint operations.
        
        Args:
            operation: Type of batch operation
            job_id: Job ID
            total_count: Total number of checkpoints processed
            success_count: Number of successful operations
            failure_count: Number of failed operations
            duration: Total duration of batch operation
            additional_context: Additional context information
        """
        context = {
            "operation": operation,
            "job_id": job_id,
            "total_count": total_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": (success_count / total_count) * 100 if total_count > 0 else 0,
            "duration": duration,
            "throughput": total_count / duration if duration > 0 else 0,
            **(additional_context or {})
        }
        
        log_level = "error" if failure_count > 0 else "info"
        
        getattr(self.logger, log_level)(
            f"Batch checkpoint {operation}: {success_count}/{total_count} successful "
            f"for job {job_id} ({duration:.2f}s, {context['throughput']:.1f}/s)",
            event_type="checkpoint_batch_operation",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_storage_stats(
        self,
        stats: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint storage statistics.
        
        Args:
            stats: Storage statistics
            additional_context: Additional context information
        """
        context = {
            "storage_stats": stats,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint storage stats: {stats.get('total_checkpoints', 0)} checkpoints, "
            f"{stats.get('total_size_bytes', 0)} bytes, "
            f"compression_ratio: {stats.get('compression_ratio', 1.0):.2f}",
            event_type="checkpoint_storage_stats",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def log_checkpoint_progress(
        self,
        job_id: str,
        current_progress: float,
        target_progress: float,
        milestone: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log checkpoint progress updates.
        
        Args:
            job_id: Job ID
            current_progress: Current progress percentage
            target_progress: Target progress percentage
            milestone: Optional milestone name
            additional_context: Additional context information
        """
        context = {
            "job_id": job_id,
            "current_progress": current_progress,
            "target_progress": target_progress,
            "progress_percentage": (current_progress / target_progress) * 100 if target_progress > 0 else 0,
            "milestone": milestone,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Checkpoint progress: {current_progress:.1f}/{target_progress:.1f} "
            f"({context['progress_percentage']:.1f}%) for job {job_id}"
            + (f" - {milestone}" if milestone else ""),
            event_type="checkpoint_progress",
            correlation_id=get_correlation_id(),
            context=context,
            component="checkpoint_manager"
        )
    
    def create_checkpoint_report(
        self,
        checkpoints: List[Dict[str, Any]],
        report_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a comprehensive checkpoint report.
        
        Args:
            checkpoints: List of checkpoint data
            report_context: Additional context for the report
            
        Returns:
            Comprehensive checkpoint report
        """
        if not checkpoints:
            return {
                "report_timestamp": datetime.utcnow().isoformat(),
                "total_checkpoints": 0,
                "total_size_bytes": 0,
                "average_size_bytes": 0.0,
                "compression_ratio": 1.0,
                "context": report_context or {}
            }
        
        # Calculate statistics
        total_checkpoints = len(checkpoints)
        total_size_bytes = sum(cp.get("size_bytes", 0) for cp in checkpoints)
        total_compressed_size_bytes = sum(cp.get("compressed_size_bytes", 0) for cp in checkpoints)
        
        # Count by status
        status_counts = {}
        type_counts = {}
        
        for checkpoint in checkpoints:
            status = checkpoint.get("status", "unknown")
            checkpoint_type = checkpoint.get("checkpoint_type", "unknown")
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[checkpoint_type] = type_counts.get(checkpoint_type, 0) + 1
        
        # Calculate age statistics
        ages = [cp.get("age_seconds", 0) for cp in checkpoints]
        average_age = sum(ages) / len(ages) if ages else 0
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "total_checkpoints": total_checkpoints,
            "total_size_bytes": total_size_bytes,
            "total_compressed_size_bytes": total_compressed_size_bytes,
            "average_size_bytes": total_size_bytes / total_checkpoints if total_checkpoints > 0 else 0,
            "compression_ratio": (total_size_bytes / total_compressed_size_bytes) if total_compressed_size_bytes > 0 else 1.0,
            "average_age_seconds": average_age,
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "context": report_context or {},
            "checkpoint_details": checkpoints
        }
        
        # Log the report
        self.log_checkpoint_storage_stats(
            {
                "total_checkpoints": total_checkpoints,
                "total_size_bytes": total_size_bytes,
                "compression_ratio": report["compression_ratio"],
                "status_distribution": status_counts,
                "type_distribution": type_counts
            },
            "checkpoint_report"
        )
        
        return report


# Global checkpoint logger instance
_checkpoint_logger = CheckpointLogger()


def get_checkpoint_logger() -> CheckpointLogger:
    """Get the global checkpoint logger instance."""
    return _checkpoint_logger


def log_checkpoint_created(
    checkpoint: Checkpoint,
    file_path: str,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log checkpoint creation using the global logger."""
    _checkpoint_logger.log_checkpoint_created(checkpoint, file_path, additional_context)


def log_checkpoint_loaded(
    checkpoint: Checkpoint,
    file_path: str,
    load_time: float,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log checkpoint loading using the global logger."""
    _checkpoint_logger.log_checkpoint_loaded(checkpoint, file_path, load_time, additional_context)


def log_checkpoint_corruption_detected(
    checkpoint_id: str,
    job_id: str,
    corruption_type: str,
    severity: str,
    details: Dict[str, Any],
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log checkpoint corruption detection using the global logger."""
    _checkpoint_logger.log_checkpoint_corruption_detected(
        checkpoint_id, job_id, corruption_type, severity, details, additional_context
    )
