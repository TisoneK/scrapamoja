"""
Checkpoint Manager

Manages checkpoint creation, loading, validation, and lifecycle management
with JSON serialization, compression, encryption, and integrity validation.
"""

import asyncio
import os
import json
import gzip
import hashlib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet

from ..interfaces import ICheckpointManager, IResilienceManager
from ..models.checkpoint import (
    Checkpoint, CheckpointStatus, CheckpointType, CheckpointCompression,
    CheckpointMetadata, CheckpointData, CheckpointSummary
)
from ..utils.serialization import JSONSerializer, FileSerializer
from ..utils.integrity import ChecksumValidator, calculate_checksum
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_checkpoint_event
from ..config import get_configuration
from ..exceptions import (
    CheckpointCreationError, CheckpointCorruptionError,
    CheckpointNotFoundError, CheckpointValidationError
)


class CheckpointManager(ICheckpointManager, IResilienceManager):
    """Manages checkpoint operations with serialization, compression, and encryption."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize checkpoint manager.
        
        Args:
            storage_path: Directory path for checkpoint storage
        """
        self.storage_path = Path(storage_path or "./data/checkpoints")
        self.serializer = JSONSerializer()
        self.file_serializer = FileSerializer(self.serializer)
        self.checksum_validator = ChecksumValidator()
        self.logger = get_logger("checkpoint_manager")
        
        # Encryption key (in production, this should be loaded from secure storage)
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        
        self._initialized = False
        self._active_checkpoints: Dict[str, Checkpoint] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the checkpoint manager."""
        if self._initialized:
            return
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self._initialized = True
        
        self.logger.info(
            "Checkpoint manager initialized",
            event_type="checkpoint_manager_initialized",
            correlation_id=get_correlation_id(),
            context={
                "storage_path": str(self.storage_path),
                "encryption_enabled": True
            },
            component="checkpoint_manager"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the checkpoint manager gracefully."""
        if not self._initialized:
            return
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save active checkpoints
        for checkpoint_id, checkpoint in self._active_checkpoints.items():
            if checkpoint.status == CheckpointStatus.ACTIVE:
                await self._save_checkpoint_to_file(checkpoint)
        
        self._active_checkpoints.clear()
        self._initialized = False
        
        self.logger.info(
            "Checkpoint manager shutdown",
            event_type="checkpoint_manager_shutdown",
            correlation_id=get_correlation_id(),
            component="checkpoint_manager"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "storage_path": str(self.storage_path),
            "active_checkpoints": len(self._active_checkpoints),
            "storage_exists": self.storage_path.exists(),
            "storage_writable": os.access(self.storage_path, os.W_OK)
        }
    
    async def create_checkpoint(
        self,
        job_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new checkpoint for the specified job.
        
        Args:
            job_id: Unique identifier for the scraping job
            data: Job state data to checkpoint
            metadata: Optional metadata about the checkpoint
            
        Returns:
            Checkpoint ID if successful
            
        Raises:
            CheckpointCreationError: If checkpoint creation fails
            ValidationError: If data is invalid
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Validate input data
            if not job_id:
                raise CheckpointValidationError("job_id is required")
            
            if not data:
                raise CheckpointValidationError("data is required")
            
            # Get configuration
            config = get_configuration()
            
            # Create checkpoint
            checkpoint = Checkpoint(
                job_id=job_id,
                sequence_number=await self._get_next_sequence_number(job_id),
                checkpoint_type=CheckpointType.FULL,
                compression=CheckpointCompression.GZIP,
                encryption_enabled=config.checkpoint.encryption_enabled,
                schema_version="1.0.0"
            )
            
            # Set metadata
            if metadata:
                checkpoint.update_metadata(**metadata)
            
            # Set data
            checkpoint.data = CheckpointData(
                progress=data.get("progress", {}),
                state=data.get("state", {}),
                configuration=data.get("configuration", {}),
                metrics=data.get("metrics", {}),
                artifacts=data.get("artifacts", [])
            )
            
            # Calculate checksum
            checkpoint_data = checkpoint.data.to_dict()
            checkpoint.checksum = calculate_checksum(checkpoint_data)
            
            # Serialize and compress data
            serialized_data = self.serializer.serialize(
                checkpoint_data,
                checkpoint.schema_version,
                checkpoint.compression == CheckpointCompression.GZIP
            )
            
            # Encrypt if enabled
            if checkpoint.encryption_enabled:
                serialized_data = self.cipher.encrypt(serialized_data)
            
            # Calculate sizes
            checkpoint.size_bytes = len(json.dumps(checkpoint_data).encode('utf-8'))
            checkpoint.compressed_size_bytes = len(serialized_data)
            
            # Save to file
            await self._save_checkpoint_to_file(checkpoint)
            
            # Add to active checkpoints
            self._active_checkpoints[checkpoint.id] = checkpoint
            
            # Mark as active
            checkpoint.mark_active()
            
            # Publish event
            await publish_checkpoint_event(
                action="created",
                checkpoint_id=checkpoint.id,
                job_id=job_id,
                context={
                    "sequence_number": checkpoint.sequence_number,
                    "size_bytes": checkpoint.size_bytes,
                    "compression": checkpoint.compression.value,
                    "encryption": checkpoint.encryption_enabled
                },
                component="checkpoint_manager"
            )
            
            self.logger.info(
                f"Checkpoint created: {checkpoint.id} for job {job_id}",
                event_type="checkpoint_created",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint.id,
                    "job_id": job_id,
                    "sequence_number": checkpoint.sequence_number,
                    "size_bytes": checkpoint.size_bytes,
                    "compression_ratio": checkpoint.get_compression_ratio()
                },
                component="checkpoint_manager"
            )
            
            return checkpoint.id
            
        except Exception as e:
            raise CheckpointCreationError(f"Failed to create checkpoint: {str(e)}")
    
    async def load_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data by ID.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            Checkpoint data if found, None otherwise
            
        Raises:
            CheckpointCorruptionError: If checkpoint is corrupted
            ValidationError: If checkpoint format is invalid
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Check active checkpoints first
            if checkpoint_id in self._active_checkpoints:
                checkpoint = self._active_checkpoints[checkpoint_id]
                if checkpoint.data:
                    return checkpoint.data.to_dict()
                else:
                    return None
            
            # Load from file
            checkpoint = await self._load_checkpoint_from_file(checkpoint_id)
            if not checkpoint:
                return None
            
            # Validate integrity
            if not await self._validate_checkpoint_integrity(checkpoint):
                raise CheckpointCorruptionError(f"Checkpoint integrity validation failed: {checkpoint_id}")
            
            # Add to active checkpoints
            self._active_checkpoints[checkpoint_id] = checkpoint
            
            # Publish event
            await publish_checkpoint_event(
                action="loaded",
                checkpoint_id=checkpoint_id,
                job_id=checkpoint.job_id,
                context={
                    "sequence_number": checkpoint.sequence_number,
                    "status": checkpoint.status.value
                },
                component="checkpoint_manager"
            )
            
            self.logger.info(
                f"Checkpoint loaded: {checkpoint_id} for job {checkpoint.job_id}",
                event_type="checkpoint_loaded",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint_id,
                    "job_id": checkpoint.job_id,
                    "sequence_number": checkpoint.sequence_number,
                    "age_seconds": checkpoint.get_age_seconds()
                },
                component="checkpoint_manager"
            )
            
            return checkpoint.data.to_dict() if checkpoint.data else None
            
        except CheckpointCorruptionError:
            raise
        except Exception as e:
            raise CheckpointCorruptionError(f"Failed to load checkpoint: {str(e)}")
    
    async def list_checkpoints(
        self,
        job_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint metadata
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get all checkpoint files for the job
            job_checkpoints = []
            
            # Check active checkpoints
            for checkpoint in self._active_checkpoints.values():
                if checkpoint.job_id == job_id:
                    job_checkpoints.append(checkpoint)
            
            # Load from file system
            checkpoint_files = list(self.storage_path.glob(f"{job_id}_*.json"))
            for file_path in checkpoint_files:
                checkpoint_id = file_path.stem
                if checkpoint_id not in [cp.id for cp in job_checkpoints]:
                    checkpoint = await self._load_checkpoint_from_file(checkpoint_id)
                    if checkpoint:
                        job_checkpoints.append(checkpoint)
            
            # Sort by sequence number (descending)
            job_checkpoints.sort(key=lambda cp: cp.sequence_number, reverse=True)
            
            # Apply limit
            if limit:
                job_checkpoints = job_checkpoints[:limit]
            
            # Convert to metadata
            return [
                {
                    "id": checkpoint.id,
                    "job_id": checkpoint.job_id,
                    "sequence_number": checkpoint.sequence_number,
                    "timestamp": checkpoint.timestamp.isoformat(),
                    "status": checkpoint.status.value,
                    "checkpoint_type": checkpoint.checkpoint_type.value,
                    "size_bytes": checkpoint.size_bytes,
                    "compressed_size_bytes": checkpoint.compressed_size_bytes,
                    "checksum": checkpoint.checksum,
                    "description": checkpoint.description,
                    "tags": checkpoint.tags,
                    "expires_at": checkpoint.expires_at.isoformat() if checkpoint.expires_at else None,
                    "age_seconds": checkpoint.get_age_seconds()
                }
                for checkpoint in job_checkpoints
            ]
            
        except Exception as e:
            self.logger.error(
                f"Failed to list checkpoints for job {job_id}: {str(e)}",
                event_type="checkpoint_list_error",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "error": str(e)
                },
                component="checkpoint_manager"
            )
            return []
    
    async def delete_checkpoint(
        self,
        checkpoint_id: str
    ) -> bool:
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Remove from active checkpoints
            if checkpoint_id in self._active_checkpoints:
                checkpoint = self._active_checkpoints[checkpoint_id]
                del self._active_checkpoints[checkpoint_id]
            
            # Delete file
            file_path = self.storage_path / f"{checkpoint_id}.json"
            if file_path.exists():
                file_path.unlink()
                
                # Publish event
                await publish_checkpoint_event(
                    action="deleted",
                    checkpoint_id=checkpoint_id,
                    job_id=checkpoint.job_id if 'checkpoint' in locals() else "unknown",
                    context={},
                    component="checkpoint_manager"
                )
                
                self.logger.info(
                    f"Checkpoint deleted: {checkpoint_id}",
                    event_type="checkpoint_deleted",
                    correlation_id=get_correlation_id(),
                    context={"checkpoint_id": checkpoint_id},
                    component="checkpoint_manager"
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                f"Failed to delete checkpoint {checkpoint_id}: {str(e)}",
                event_type="checkpoint_delete_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint_id,
                    "error": str(e)
                },
                component="checkpoint_manager"
            )
            return False
    
    async def validate_checkpoint(
        self,
        checkpoint_id: str
    ) -> bool:
        """
        Validate checkpoint integrity.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check active checkpoints first
            if checkpoint_id in self._active_checkpoints:
                checkpoint = self._active_checkpoints[checkpoint_id]
                return await self._validate_checkpoint_integrity(checkpoint)
            
            # Load from file
            checkpoint = await self._load_checkpoint_from_file(checkpoint_id)
            if not checkpoint:
                return False
            
            return await self._validate_checkpoint_integrity(checkpoint)
            
        except Exception as e:
            self.logger.error(
                f"Failed to validate checkpoint {checkpoint_id}: {str(e)}",
                event_type="checkpoint_validation_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint_id,
                    "error": str(e)
                },
                component="checkpoint_manager"
            )
            return False
    
    async def get_checkpoint_summary(
        self,
        job_id: str
    ) -> CheckpointSummary:
        """
        Get summary of checkpoints for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            CheckpointSummary with statistics
        """
        try:
            checkpoints = await self.list_checkpoints(job_id)
            
            summary = CheckpointSummary(job_id=job_id)
            summary.total_checkpoints = len(checkpoints)
            
            # Count by status
            for cp in checkpoints:
                status = cp.get("status", "unknown")
                if status == "active":
                    summary.active_checkpoints += 1
                elif status == "completed":
                    summary.completed_checkpoints += 1
                elif status == "corrupted":
                    summary.corrupted_checkpoints += 1
                elif status == "expired":
                    summary.expired_checkpoints += 1
                
                # Track latest and oldest
                if summary.latest_checkpoint is None:
                    summary.latest_checkpoint = cp["id"]
                if summary.oldest_checkpoint is None:
                    summary.oldest_checkpoint = cp["id"]
                
                # Calculate total size
                summary.total_size_bytes += cp.get("size_bytes", 0)
            
            # Calculate average size
            if summary.total_checkpoints > 0:
                summary.average_size_bytes = summary.total_size_bytes / summary.total_checkpoints
            
            return summary
            
        except Exception as e:
            self.logger.error(
                f"Failed to get checkpoint summary for job {job_id}: {str(e)}",
                event_type="checkpoint_summary_error",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "error": str(e)
                },
                component="checkpoint_manager"
            )
            return CheckpointSummary(job_id=job_id)
    
    async def cleanup_expired_checkpoints(self) -> int:
        """
        Clean up expired checkpoints.
        
        Returns:
            Number of checkpoints cleaned up
        """
        try:
            cleaned_count = 0
            
            # Check active checkpoints
            expired_ids = []
            for checkpoint_id, checkpoint in self._active_checkpoints.items():
                if checkpoint.is_expired():
                    expired_ids.append(checkpoint_id)
            
            # Delete expired checkpoints
            for checkpoint_id in expired_ids:
                if await self.delete_checkpoint(checkpoint_id):
                    cleaned_count += 1
            
            # Check file system for expired checkpoints
            for file_path in self.storage_path.glob("*.json"):
                try:
                    checkpoint_id = file_path.stem
                    if checkpoint_id not in self._active_checkpoints:
                        checkpoint = await self._load_checkpoint_from_file(checkpoint_id)
                        if checkpoint and checkpoint.is_expired():
                            if await self.delete_checkpoint(checkpoint_id):
                                cleaned_count += 1
                except Exception:
                    continue
            
            if cleaned_count > 0:
                self.logger.info(
                    f"Cleaned up {cleaned_count} expired checkpoints",
                    event_type="checkpoint_cleanup_completed",
                    correlation_id=get_correlation_id(),
                    context={"cleaned_count": cleaned_count},
                    component="checkpoint_manager"
                )
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup expired checkpoints: {str(e)}",
                event_type="checkpoint_cleanup_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="checkpoint_manager"
            )
            return 0
    
    async def _save_checkpoint_to_file(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to file."""
        file_path = self.storage_path / f"{checkpoint.id}.json"
        
        # Prepare checkpoint data for saving
        checkpoint_data = checkpoint.to_dict()
        
        # Save to file
        self.file_serializer.save_to_file(
            file_path,
            checkpoint_data,
            checkpoint.schema_version,
            checkpoint.compression == CheckpointCompression.GZIP
        )
    
    async def _load_checkpoint_from_file(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from file."""
        file_path = self.storage_path / f"{checkpoint_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            # Load from file
            checkpoint_data = self.file_serializer.load_from_file(
                file_path,
                "1.0.0",
                True  # Auto-detect compression
            )
            
            # Decrypt if needed
            if checkpoint_data.get("encryption_enabled", False):
                checkpoint_data["data"] = json.loads(
                    self.cipher.decrypt(
                        checkpoint_data["data"].encode('utf-8')
                    ).decode('utf-8')
                )
            
            return Checkpoint.from_dict(checkpoint_data)
            
        except Exception as e:
            self.logger.error(
                f"Failed to load checkpoint from file {checkpoint_id}: {str(e)}",
                event_type="checkpoint_file_load_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint_id,
                    "file_path": str(file_path),
                    "error": str(e)
                },
                component="checkpoint_manager"
            )
            return None
    
    async def _validate_checkpoint_integrity(self, checkpoint: Checkpoint) -> bool:
        """Validate checkpoint integrity."""
        try:
            if not checkpoint.data or not checkpoint.checksum:
                return False
            
            # Calculate checksum of current data
            calculated_checksum = calculate_checksum(checkpoint.data.to_dict())
            
            # Compare with stored checksum
            return calculated_checksum == checkpoint.checksum
            
        except Exception as e:
            self.logger.error(
                f"Failed to validate checkpoint integrity: {str(e)}",
                event_type="checkpoint_integrity_validation_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint.id,
                    "error": str(e)
                },
                component="checkpoint_manager"
            )
            return False
    
    async def _get_next_sequence_number(self, job_id: str) -> int:
        """Get next sequence number for a job."""
        try:
            # List existing checkpoints for the job
            checkpoints = await self.list_checkpoints(job_id)
            
            if not checkpoints:
                return 1
            
            # Find highest sequence number
            max_sequence = max(cp.get("sequence_number", 0) for cp in checkpoints)
            return max_sequence + 1
            
        except Exception:
            return 1
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired checkpoints."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.cleanup_expired_checkpoints()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in cleanup loop: {str(e)}",
                    event_type="cleanup_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="checkpoint_manager"
                )
                await asyncio.sleep(300)  # Wait 5 minutes before retry


# Global checkpoint manager instance
_checkpoint_manager = CheckpointManager()


def get_checkpoint_manager() -> CheckpointManager:
    """Get the global checkpoint manager instance."""
    return _checkpoint_manager


async def create_checkpoint(
    job_id: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a checkpoint using the global manager."""
    return await _checkpoint_manager.create_checkpoint(job_id, data, metadata)


async def load_checkpoint(checkpoint_id: str) -> Optional[Dict[str, Any]]:
    """Load a checkpoint using the global manager."""
    return await _checkpoint_manager.load_checkpoint(checkpoint_id)
