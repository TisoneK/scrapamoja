"""
Checkpoint Data Model

Defines the Checkpoint entity and related enums for progress saving,
resume capability, and integrity validation with schema versioning.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class CheckpointStatus(Enum):
    """Status of a checkpoint."""
    CREATING = "creating"
    ACTIVE = "active"
    COMPLETED = "completed"
    CORRUPTED = "corrupted"
    EXPIRED = "expired"
    DELETED = "deleted"


class CheckpointType(Enum):
    """Type of checkpoint."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class CheckpointCompression(Enum):
    """Compression types for checkpoint data."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    CUSTOM = "custom"


@dataclass
class CheckpointMetadata:
    """Metadata associated with a checkpoint."""
    job_id: str
    job_name: str
    job_type: str
    created_by: str
    environment: str
    version: str
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "job_type": self.job_type,
            "created_by": self.created_by,
            "environment": self.environment,
            "version": self.version,
            "tags": self.tags,
            "custom_fields": self.custom_fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointMetadata':
        """Create CheckpointMetadata from dictionary."""
        return cls(
            job_id=data.get("job_id", ""),
            job_name=data.get("job_name", ""),
            job_type=data.get("job_type", ""),
            created_by=data.get("created_by", ""),
            environment=data.get("environment", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            custom_fields=data.get("custom_fields", {})
        )


@dataclass
class CheckpointData:
    """Data stored in a checkpoint."""
    progress: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "progress": self.progress,
            "state": self.state,
            "configuration": self.configuration,
            "metrics": self.metrics,
            "artifacts": self.artifacts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointData':
        """Create CheckpointData from dictionary."""
        return cls(
            progress=data.get("progress", {}),
            state=data.get("state", {}),
            configuration=data.get("configuration", {}),
            metrics=data.get("metrics", {}),
            artifacts=data.get("artifacts", [])
        )


@dataclass
class Checkpoint:
    """Checkpoint entity for progress saving and resume capability."""
    
    # Core identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence_number: int = 0
    status: CheckpointStatus = CheckpointStatus.CREATING
    
    # Checkpoint configuration
    checkpoint_type: CheckpointType = CheckpointType.FULL
    compression: CheckpointCompression = CheckpointCompression.GZIP
    encryption_enabled: bool = True
    schema_version: str = "1.0.0"
    
    # Data and metadata
    metadata: Optional[CheckpointMetadata] = None
    data: Optional[CheckpointData] = None
    
    # Integrity and validation
    checksum: str = ""
    size_bytes: int = 0
    compressed_size_bytes: int = 0
    
    # Lifecycle management
    parent_checkpoint_id: Optional[str] = None
    child_checkpoint_ids: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    
    # Additional information
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if not self.job_id:
            raise ValueError("job_id is required")
        
        # Set default metadata if not provided
        if self.metadata is None:
            self.metadata = CheckpointMetadata(
                job_id=self.job_id,
                job_name=self.job_id,
                job_type="unknown",
                created_by="system",
                environment="production",
                version="1.0.0"
            )
        
        # Set default data if not provided
        if self.data is None:
            self.data = CheckpointData()
        
        # Ensure enums are valid
        if isinstance(self.status, str):
            self.status = CheckpointStatus(self.status)
        
        if isinstance(self.checkpoint_type, str):
            self.checkpoint_type = CheckpointType(self.checkpoint_type)
        
        if isinstance(self.compression, str):
            self.compression = CheckpointCompression(self.compression)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "sequence_number": self.sequence_number,
            "status": self.status.value,
            "checkpoint_type": self.checkpoint_type.value,
            "compression": self.compression.value,
            "encryption_enabled": self.encryption_enabled,
            "schema_version": self.schema_version,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "data": self.data.to_dict() if self.data else None,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "child_checkpoint_ids": self.child_checkpoint_ids,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "description": self.description,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create Checkpoint from dictionary."""
        # Handle timestamps
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()
        
        expires_at = data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        # Handle enums
        status = CheckpointStatus(data.get("status", "creating"))
        checkpoint_type = CheckpointType(data.get("checkpoint_type", "full"))
        compression = CheckpointCompression(data.get("compression", "gzip"))
        
        # Handle metadata and data
        metadata_data = data.get("metadata")
        metadata = CheckpointMetadata.from_dict(metadata_data) if metadata_data else None
        
        data_data = data.get("data")
        checkpoint_data = CheckpointData.from_dict(data_data) if data_data else None
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            job_id=data.get("job_id", ""),
            timestamp=timestamp,
            sequence_number=data.get("sequence_number", 0),
            status=status,
            checkpoint_type=checkpoint_type,
            compression=compression,
            encryption_enabled=data.get("encryption_enabled", True),
            schema_version=data.get("schema_version", "1.0.0"),
            metadata=metadata,
            data=checkpoint_data,
            checksum=data.get("checksum", ""),
            size_bytes=data.get("size_bytes", 0),
            compressed_size_bytes=data.get("compressed_size_bytes", 0),
            parent_checkpoint_id=data.get("parent_checkpoint_id"),
            child_checkpoint_ids=data.get("child_checkpoint_ids", []),
            expires_at=expires_at,
            description=data.get("description", ""),
            tags=data.get("tags", [])
        )
    
    def mark_active(self) -> None:
        """Mark checkpoint as active."""
        self.status = CheckpointStatus.ACTIVE
    
    def mark_completed(self) -> None:
        """Mark checkpoint as completed."""
        self.status = CheckpointStatus.COMPLETED
    
    def mark_corrupted(self) -> None:
        """Mark checkpoint as corrupted."""
        self.status = CheckpointStatus.CORRUPTED
    
    def mark_expired(self) -> None:
        """Mark checkpoint as expired."""
        self.status = CheckpointStatus.EXPIRED
    
    def mark_deleted(self) -> None:
        """Mark checkpoint as deleted."""
        self.status = CheckpointStatus.DELETED
    
    def is_active(self) -> bool:
        """Check if checkpoint is active."""
        return self.status == CheckpointStatus.ACTIVE
    
    def is_completed(self) -> bool:
        """Check if checkpoint is completed."""
        return self.status == CheckpointStatus.COMPLETED
    
    def is_corrupted(self) -> bool:
        """Check if checkpoint is corrupted."""
        return self.status == CheckpointStatus.CORRUPTED
    
    def is_expired(self) -> bool:
        """Check if checkpoint is expired."""
        if self.status == CheckpointStatus.EXPIRED:
            return True
        
        if self.expires_at:
            return datetime.utcnow() >= self.expires_at
        
        return False
    
    def is_valid(self) -> bool:
        """Check if checkpoint is valid for use."""
        return (
            self.is_active() or self.is_completed()
        ) and not self.is_corrupted() and not self.is_expired()
    
    def get_age_seconds(self) -> float:
        """Get the age of the checkpoint in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()
    
    def get_age_minutes(self) -> float:
        """Get the age of the checkpoint in minutes."""
        return self.get_age_seconds() / 60.0
    
    def get_age_hours(self) -> float:
        """Get the age of the checkpoint in hours."""
        return self.get_age_minutes() / 60.0
    
    def get_compression_ratio(self) -> float:
        """Get compression ratio."""
        if self.compressed_size_bytes == 0:
            return 1.0
        return self.size_bytes / self.compressed_size_bytes
    
    def add_child_checkpoint(self, child_id: str) -> None:
        """Add a child checkpoint ID."""
        if child_id not in self.child_checkpoint_ids:
            self.child_checkpoint_ids.append(child_id)
    
    def remove_child_checkpoint(self, child_id: str) -> None:
        """Remove a child checkpoint ID."""
        if child_id in self.child_checkpoint_ids:
            self.child_checkpoint_ids.remove(child_id)
    
    def has_children(self) -> bool:
        """Check if checkpoint has child checkpoints."""
        return len(self.child_checkpoint_ids) > 0
    
    def get_progress_value(self, key: str, default: Any = None) -> Any:
        """Get a progress value from checkpoint data."""
        if self.data and self.data.progress:
            return self.data.progress.get(key, default)
        return default
    
    def set_progress_value(self, key: str, value: Any) -> None:
        """Set a progress value in checkpoint data."""
        if self.data:
            if not self.data.progress:
                self.data.progress = {}
            self.data.progress[key] = value
    
    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get a state value from checkpoint data."""
        if self.data and self.data.state:
            return self.data.state.get(key, default)
        return default
    
    def set_state_value(self, key: str, value: Any) -> None:
        """Set a state value in checkpoint data."""
        if self.data:
            if not self.data.state:
                self.data.state = {}
            self.data.state[key] = value
    
    def get_metric_value(self, key: str, default: Any = None) -> Any:
        """Get a metric value from checkpoint data."""
        if self.data and self.data.metrics:
            return self.data.metrics.get(key, default)
        return default
    
    def set_metric_value(self, key: str, value: Any) -> None:
        """Set a metric value in checkpoint data."""
        if self.data:
            if not self.data.metrics:
                self.data.metrics = {}
            self.data.metrics[key] = value
    
    def add_artifact(self, artifact_path: str) -> None:
        """Add an artifact path to checkpoint data."""
        if self.data:
            if artifact_path not in self.data.artifacts:
                self.data.artifacts.append(artifact_path)
    
    def remove_artifact(self, artifact_path: str) -> None:
        """Remove an artifact path from checkpoint data."""
        if self.data and artifact_path in self.data.artifacts:
            self.data.artifacts.remove(artifact_path)
    
    def has_artifacts(self) -> bool:
        """Check if checkpoint has artifacts."""
        return self.data and len(self.data.artifacts) > 0
    
    def update_metadata(self, **kwargs) -> None:
        """Update metadata fields."""
        if self.metadata:
            for key, value in kwargs.items():
                if hasattr(self.metadata, key):
                    setattr(self.metadata, key, value)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the checkpoint."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the checkpoint."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if checkpoint has a specific tag."""
        return tag in self.tags
    
    def clone(self, **kwargs) -> 'Checkpoint':
        """Create a clone of this checkpoint with optional overrides."""
        checkpoint_dict = self.to_dict()
        checkpoint_dict.update(kwargs)
        return Checkpoint.from_dict(checkpoint_dict)
    
    def __str__(self) -> str:
        """String representation of the checkpoint."""
        return (
            f"Checkpoint(id={self.id[:8]}, job_id={self.job_id}, "
            f"status={self.status.value}, type={self.checkpoint_type.value})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation of the checkpoint."""
        return (
            f"Checkpoint(id='{self.id}', job_id='{self.job_id}', "
            f"timestamp='{self.timestamp.isoformat()}', sequence_number={self.sequence_number}, "
            f"status={self.status.value}, type={self.checkpoint_type.value}, "
            f"compression={self.compression.value}, size={self.size_bytes})"
        )


@dataclass
class CheckpointSummary:
    """Summary information about checkpoints for a job."""
    job_id: str
    total_checkpoints: int = 0
    active_checkpoints: int = 0
    completed_checkpoints: int = 0
    corrupted_checkpoints: int = 0
    expired_checkpoints: int = 0
    latest_checkpoint: Optional[str] = None
    oldest_checkpoint: Optional[str] = None
    total_size_bytes: int = 0
    average_size_bytes: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "job_id": self.job_id,
            "total_checkpoints": self.total_checkpoints,
            "active_checkpoints": self.active_checkpoints,
            "completed_checkpoints": self.completed_checkpoints,
            "corrupted_checkpoints": self.corrupted_checkpoints,
            "expired_checkpoints": self.expired_checkpoints,
            "latest_checkpoint": self.latest_checkpoint,
            "oldest_checkpoint": self.oldest_checkpoint,
            "total_size_bytes": self.total_size_bytes,
            "average_size_bytes": self.average_size_bytes
        }


# Default checkpoint configurations
DEFAULT_CHECKPOINT_CONFIG = {
    "compression": CheckpointCompression.GZIP,
    "encryption_enabled": True,
    "schema_version": "1.0.0",
    "retention_count": 10,
    "auto_cleanup": True,
    "validation_enabled": True
}

LIGHTWEIGHT_CHECKPOINT_CONFIG = {
    "compression": CheckpointCompression.NONE,
    "encryption_enabled": False,
    "schema_version": "1.0.0",
    "retention_count": 20,
    "auto_cleanup": True,
    "validation_enabled": False
}

HIGH_SECURITY_CHECKPOINT_CONFIG = {
    "compression": CheckpointCompression.GZIP,
    "encryption_enabled": True,
    "schema_version": "1.0.0",
    "retention_count": 5,
    "auto_cleanup": True,
    "validation_enabled": True
}
