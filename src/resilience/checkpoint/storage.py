"""
Checkpoint Storage Management

Handles checkpoint storage operations including compression, encryption,
file management, and cleanup with support for multiple storage backends.
"""

import os
import json
import gzip
import shutil
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet

from ..models.checkpoint import Checkpoint, CheckpointStatus, CheckpointCompression
from ..utils.serialization import JSONSerializer, FileSerializer
from ..utils.integrity import ChecksumValidator, calculate_checksum
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_checkpoint_event


class StorageBackend(Enum):
    """Available storage backends."""
    LOCAL_FILESYSTEM = "local_filesystem"
    S3 = "s3"
    DATABASE = "database"
    CUSTOM = "custom"


@dataclass
class StorageConfig:
    """Configuration for checkpoint storage."""
    backend: StorageBackend = StorageBackend.LOCAL_FILESYSTEM
    base_path: str = "./data/checkpoints"
    compression: CheckpointCompression = CheckpointCompression.GZIP
    encryption_enabled: bool = True
    encryption_key: Optional[str] = None
    retention_days: int = 30
    max_file_size_mb: int = 100
    backup_enabled: bool = True
    backup_path: Optional[str] = None
    custom_config: Dict[str, Any] = field(default_factory=dict)


class CheckpointStorage:
    """Manages checkpoint storage operations."""
    
    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize checkpoint storage.
        
        Args:
            config: Storage configuration
        """
        self.config = config or StorageConfig()
        self.logger = get_logger("checkpoint_storage")
        self.serializer = JSONSerializer()
        self.file_serializer = FileSerializer(self.serializer)
        self.checksum_validator = ChecksumValidator()
        
        # Initialize encryption if enabled
        self.cipher = None
        if self.config.encryption_enabled:
            if self.config.encryption_key:
                self.cipher = Fernet(self.config.encryption_key.encode())
            else:
                # Generate key for demo purposes (in production, load from secure storage)
                self.cipher = Fernet.generate_key()
        
        # Ensure storage directory exists
        self.base_path = Path(self.config.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize backup directory if enabled
        if self.config.backup_enabled and self.config.backup_path:
            self.backup_path = Path(self.config.backup_path)
            self.backup_path.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
    
    async def save_checkpoint(
        self,
        checkpoint: Checkpoint
    ) -> str:
        """
        Save a checkpoint to storage.
        
        Args:
            checkpoint: Checkpoint to save
            
        Returns:
            File path where checkpoint was saved
            
        Raises:
            Exception: If save operation fails
        """
        try:
            # Prepare checkpoint data
            checkpoint_data = checkpoint.to_dict()
            
            # Serialize to JSON
            json_data = json.dumps(checkpoint_data, default=str, separators=(',', ':')).encode('utf-8')
            
            # Apply compression
            if self.config.compression == CheckpointCompression.GZIP:
                json_data = gzip.compress(json_data)
                checkpoint.compressed_size_bytes = len(json_data)
            else:
                checkpoint.compressed_size_bytes = len(json_data)
            
            # Apply encryption
            if self.config.encryption_enabled and self.cipher:
                json_data = self.cipher.encrypt(json_data)
                checkpoint.encrypted_size_bytes = len(json_data)
            else:
                checkpoint.encrypted_size_bytes = checkpoint.compressed_size_bytes
            
            # Calculate checksum before encryption
            if checkpoint.data:
                checkpoint.checksum = calculate_checksum(checkpoint.data.to_dict())
            
            # Save to file
            file_path = self.base_path / f"{checkpoint.id}.json"
            
            if self.config.compression == CheckpointCompression.GZIP:
                # Save compressed data directly
                with open(file_path, 'wb') as f:
                    f.write(json_data)
            else:
                # Save using file serializer
                self.file_serializer.save_to_file(
                    file_path,
                    checkpoint_data,
                    checkpoint.schema_version,
                    self.config.compression == CheckpointCompression.GZIP
                )
            
            # Create backup if enabled
            if self.config.backup_enabled:
                await self._create_backup(file_path)
            
            # Publish event
            await publish_checkpoint_event(
                action="saved",
                checkpoint_id=checkpoint.id,
                job_id=checkpoint.job_id,
                context={
                    "file_path": str(file_path),
                    "size_bytes": checkpoint.size_bytes,
                    "compression": checkpoint.compression.value,
                    "encryption": checkpoint.encryption_enabled
                },
                component="checkpoint_storage"
            )
            
            self.logger.info(
                f"Checkpoint saved: {checkpoint.id} to {file_path}",
                event_type="checkpoint_saved",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint.id,
                    "job_id": checkpoint.job_id,
                    "file_path": str(file_path),
                    "size_bytes": checkpoint.size_bytes,
                    "compression_ratio": checkpoint.get_compression_ratio()
                },
                component="checkpoint_storage"
            )
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(
                f"Failed to save checkpoint {checkpoint.id}: {str(e)}",
                event_type="checkpoint_save_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint.id,
                    "error": str(e)
                },
                component="checkpoint_storage"
            )
            raise
    
    async def load_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Checkpoint]:
        """
        Load a checkpoint from storage.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Loaded checkpoint or None if not found
            
        Raises:
            Exception: If load operation fails
        """
        try:
            # Construct file path
            file_path = self.base_path / f"{checkpoint_id}.json"
            
            if not file_path.exists():
                return None
            
            # Load file data
            if self.config.compression == CheckpointCompression.GZIP:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
            else:
                checkpoint_data = self.file_serializer.load_from_file(
                    file_path,
                    "1.0.0",
                    self.config.compression == CheckpointCompression.GZIP
                )
                file_data = json.loads(file_data.decode('utf-8'))
            
            # Apply decryption if needed
            if self.config.encryption_enabled and self.cipher:
                if self.config.compression == CheckpointCompression.GZIP:
                    file_data = gzip.decompress(file_data)
                file_data = self.cipher.decrypt(file_data)
            
            # Parse checkpoint
            checkpoint = Checkpoint.from_dict(file_data)
            
            # Validate integrity
            if not await self._validate_checkpoint_integrity(checkpoint):
                raise Exception(f"Checkpoint integrity validation failed: {checkpoint_id}")
            
            # Publish event
            await publish_checkpoint_event(
                action="loaded",
                checkpoint_id=checkpoint.id,
                job_id=checkpoint.job_id,
                context={
                    "file_path": str(file_path),
                    "age_seconds": checkpoint.get_age_seconds()
                },
                component="checkpoint_storage"
            )
            
            self.logger.info(
                f"Checkpoint loaded: {checkpoint_id} from {file_path}",
                event_type="checkpoint_loaded",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint.id,
                    "job_id": checkpoint.job_id,
                    "file_path": str(file_path),
                    "age_seconds": checkpoint.get_age_seconds()
                },
                component="checkpoint_storage"
            )
            
            return checkpoint
            
        except Exception as e:
            self.logger.error(
                f"Failed to load checkpoint {checkpoint_id}: {str(e)}",
                event_type="checkpoint_load_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint_id,
                    "error": str(e)
                },
                component="checkpoint_storage"
            )
            raise
    
    async def delete_checkpoint(
        self,
        checkpoint_id: str
    ) -> bool:
        """
        Delete a checkpoint from storage.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            file_path = self.base_path / f"{checkpoint_id}.json"
            
            if not file_path.exists():
                return False
            
            # Create backup before deletion if enabled
            if self.config.backup_enabled:
                await self._create_backup(file_path)
            
            # Delete file
            file_path.unlink()
            
            # Delete backup if it exists
            if self.config.backup_enabled and self.backup_path:
                backup_path = self.backup_path / f"{checkpoint_id}.json"
                if backup_path.exists():
                    backup_path.unlink()
            
            # Publish event
            await publish_checkpoint_event(
                action="deleted",
                checkpoint_id=checkpoint_id,
                job_id=checkpoint_id,
                context={
                    "file_path": str(file_path)
                },
                component="checkpoint_storage"
            )
            
            self.logger.info(
                f"Checkpoint deleted: {checkpoint_id}",
                event_type="checkpoint_deleted",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint_id
                },
                component="checkpoint_storage"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to delete checkpoint {checkpoint_id}: {str(e)}",
                event_type="checkpoint_delete_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint_id,
                    "error": str(e)
                },
                component="checkpoint_storage"
            )
            return False
    
    async def list_checkpoints(
        self,
        job_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints in storage.
        
        Args:
            job_id: Filter by job ID (optional)
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint metadata
        """
        try:
            checkpoints = []
            
            # List all JSON files in storage directory
            for file_path in self.base_path.glob("*.json"):
                try:
                    # Extract checkpoint ID from filename
                    checkpoint_id = file_path.stem
                    
                    # Load checkpoint metadata
                    checkpoint = await self.load_checkpoint(checkpoint_id)
                    if checkpoint:
                        # Apply filters
                        if job_id and checkpoint.job_id != job_id:
                            continue
                        
                        checkpoint_info = {
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
                            "age_seconds": checkpoint.get_age_seconds(),
                            "file_path": str(file_path)
                        }
                        
                        checkpoints.append(checkpoint_info)
                        
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load checkpoint metadata from {file_path}: {str(e)}",
                        event_type="checkpoint_list_error",
                        correlation_id=get_correlation_id(),
                        context={
                            "file_path": str(file_path),
                            "error": str(e)
                        },
                        component="checkpoint_storage"
                    )
                    continue
            
            # Sort by sequence number (descending)
            checkpoints.sort(key=lambda x: x["sequence_number"], reverse=True)
            
            # Apply limit
            if limit:
                checkpoints = checkpoints[:limit]
            
            return checkpoints
            
        except Exception as e:
            self.logger.error(
                f"Failed to list checkpoints: {str(e)}",
                event_type="checkpoint_list_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="checkpoint_storage"
            )
            return []
    
    async def cleanup_expired_checkpoints(self) -> int:
        """
        Clean up expired checkpoints.
        
        Returns:
            Number of checkpoints cleaned up
        """
        try:
            cleaned_count = 0
            cutoff_time = datetime.utcnow() - timedelta(days=self.config.retention_days)
            
            # List all checkpoint files
            for file_path in self.base_path.glob("*.json"):
                try:
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if mod_time < cutoff_time:
                        # Load checkpoint to check expiration
                        checkpoint_id = file_path.stem
                        checkpoint = await self.load_checkpoint(checkpoint_id)
                        
                        if checkpoint and checkpoint.is_expired():
                            # Delete expired checkpoint
                            if await self.delete_checkpoint(checkpoint_id):
                                cleaned_count += 1
                                self.logger.info(
                                    f"Cleaned up expired checkpoint: {checkpoint_id}",
                                    event_type="checkpoint_cleanup",
                                    correlation_id=get_correlation_id(),
                                    context={
                                        "checkpoint_id": checkpoint_id,
                                        "expired_at": checkpoint.expires_at.isoformat() if checkpoint.expires_at else None
                                    },
                                    component="checkpoint_storage"
                                )
                
                except Exception as e:
                    self.logger.warning(
                        f"Error checking checkpoint expiration for {file_path}: {str(e)}",
                        event_type="checkpoint_cleanup_error",
                        correlation_id=get_correlation_id(),
                        context={
                            "file_path": str(file_path),
                            "error": str(e)
                        },
                        component="checkpoint_storage"
                    )
                    continue
            
            if cleaned_count > 0:
                self.logger.info(
                    f"Cleaned up {cleaned_count} expired checkpoints",
                    event_type="checkpoint_cleanup_completed",
                    correlation_id=get_correlation_id(),
                    context={"cleaned_count": cleaned_count},
                    component="checkpoint_storage"
                )
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup expired checkpoints: {str(e)}",
                event_type="checkpoint_cleanup_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="checkpoint_storage"
            )
            return 0
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Storage statistics
        """
        try:
            # Count total checkpoints
            total_checkpoints = len(list(self.base_path.glob("*.json")))
            
            # Calculate total size
            total_size_bytes = sum(
                file_path.stat().st_size
                for file_path in self.base_path.glob("*.json")
            )
            
            # Count by status
            status_counts = {}
            for file_path in self.backup_path.glob("*.json") if self.config.backup_enabled else []:
                try:
                    checkpoint_id = file_path.stem
                    checkpoint = await self.load_checkpoint(checkpoint_id)
                    if checkpoint:
                        status = checkpoint.status.value
                        status_counts[status] = status_counts.get(status, 0) + 1
                except Exception:
                    continue
            
            # Calculate compression ratio
            compressed_size = sum(
                checkpoint.compressed_size_bytes for checkpoint in self._get_all_checkpoints()
            )
            original_size = sum(
                checkpoint.size_bytes for checkpoint in self._get_all_checkpoints()
            )
            compression_ratio = (original_size / compressed_size) if compressed_size > 0 else 1.0
            
            return {
                "backend": self.config.backend.value,
                "base_path": str(self.base_path),
                "total_checkpoints": total_checkpoints,
                "total_size_bytes": total_size,
                "compression_enabled": self.config.compression == CheckpointCompression.GZIP,
                "encryption_enabled": self.config.encryption_enabled,
                "retention_days": self.config.retention_days,
                "max_file_size_mb": self.config.max_file_size_mb,
                "backup_enabled": self.config.backup_enabled,
                "status_distribution": status_counts,
                "compression_ratio": compression_ratio,
                "backup_path": str(self.backup_path) if self.config.backup_path else None
            }
            
        except Exception as e:
            self.logger.error(
                f"Failed to get storage stats: {str(e)}",
                event_type="storage_stats_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="checkpoint_storage"
            )
            return {}
    
    async def _create_backup(self, file_path: Path) -> None:
        """Create a backup of a checkpoint file."""
        if not self.config.backup_enabled or not self.backup_path:
            return
        
        try:
            backup_path = self.backup_path / file_path.name
            shutil.copy2(file_path, backup_path)
            
            self.logger.debug(
                f"Created backup: {backup_path}",
                event_type="backup_created",
                correlation_id=get_correlation_id(),
                context={
                    "original_path": str(file_path),
                    "backup_path": str(backup_path)
                },
                component="checkpoint_storage"
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to create backup for {file_path}: {str(e)}",
                event_type="backup_error",
                correlation_id=get_correlation_id(),
                context={
                    "file_path": str(file_path),
                    "error": str(e)
                },
                component="checkpoint_storage"
            )
    
    async def _validate_checkpoint_integrity(self, checkpoint: Checkpoint) -> bool:
        """Validate checkpoint integrity."""
        try:
            if not checkpoint.data or not checkpoint.checksum:
                return False
            
            # Calculate checksum of current data
            calculated_checksum = self.checksum_validator.calculate_checksum(checkpoint.data.to_dict())
            
            return calculated_checksum == checkpoint.checksum
            
        except Exception as e:
            self.logger.error(
                f"Failed to validate checkpoint integrity: {str(e)}",
                event_type="integrity_validation_error",
                correlation_id=get_correlation_id(),
                context={
                    "checkpoint_id": checkpoint.id,
                    "error": str(e)
                },
                component="checkpoint_storage"
            )
            return False
    
    def _get_all_checkpoints(self) -> List[Checkpoint]:
        """Get all checkpoints from storage."""
        checkpoints = []
        
        for file_path in self.base_path.glob("*.json"):
            try:
                checkpoint_id = file_path.stem
                checkpoint = self.load_checkpoint(checkpoint_id)
                if checkpoint:
                    checkpoints.append(checkpoint)
            except Exception:
                continue
        
        return checkpoints


# Global storage instance
_checkpoint_storage = CheckpointStorage()


def get_checkpoint_storage() -> CheckpointStorage:
    """Get the global checkpoint storage instance."""
    return _checkpoint_storage


async def save_checkpoint(checkpoint: Checkpoint) -> str:
    """Save a checkpoint using the global storage."""
    return await _checkpoint_storage.save_checkpoint(checkpoint)


async def load_checkpoint(checkpoint_id: str) -> Optional[Checkpoint]:
    """Load a checkpoint using the global storage."""
    return await _checkpoint_storage.load_checkpoint(checkpoint)


async def delete_checkpoint(checkpoint_id: str) -> bool:
    """Delete a checkpoint using the global storage."""
    return await _checkpoint_storage.delete_checkpoint(checkpoint_id)


async def list_checkpoints(
    job_id: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """List checkpoints using the global storage."""
    return await _checkpoint_storage.list_checkpoints(job_id, limit)
