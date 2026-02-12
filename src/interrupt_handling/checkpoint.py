"""
Data checkpoint creation functionality for interrupt handling.
"""

import os
import json
import pickle
import time
import threading
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager

from .temp_file_manager import TempFileManager
from .atomic_operations import AtomicOperationManager


@dataclass
class CheckpointData:
    """Data structure for checkpoint information."""
    checkpoint_id: str
    timestamp: float
    application_state: Dict[str, Any] = field(default_factory=dict)
    scraping_state: Dict[str, Any] = field(default_factory=dict)
    resource_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    
    @property
    def age(self) -> float:
        """Get age of checkpoint in seconds."""
        return time.time() - self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointData':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class CheckpointInfo:
    """Information about a checkpoint file."""
    checkpoint_id: str
    file_path: Path
    timestamp: float
    size_bytes: int
    version: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age(self) -> float:
        """Get age of checkpoint in seconds."""
        return time.time() - self.timestamp


class CheckpointManager:
    """Manages data checkpoints for resumption."""
    
    def __init__(self, checkpoint_dir: Optional[Union[str, Path]] = None,
                 temp_file_manager: Optional[TempFileManager] = None,
                 atomic_manager: Optional[AtomicOperationManager] = None):
        self.logger = logging.getLogger(__name__)
        
        # Set up checkpoint directory
        if checkpoint_dir:
            self.checkpoint_dir = Path(checkpoint_dir)
        else:
            self.checkpoint_dir = Path.cwd() / '.checkpoints'
        
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Managers
        self.temp_file_manager = temp_file_manager
        self.atomic_manager = atomic_manager or AtomicOperationManager()
        
        # State
        self._checkpoints: Dict[str, CheckpointInfo] = {}
        self._lock = threading.RLock()
        
        # Load existing checkpoints
        self._load_existing_checkpoints()
    
    def _load_existing_checkpoints(self):
        """Load information about existing checkpoints."""
        try:
            checkpoint_files = list(self.checkpoint_dir.glob("checkpoint_*.json"))
            
            for file_path in checkpoint_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    checkpoint_info = CheckpointInfo(
                        checkpoint_id=data.get('checkpoint_id', file_path.stem),
                        file_path=file_path,
                        timestamp=data.get('timestamp', 0),
                        size_bytes=file_path.stat().st_size,
                        version=data.get('version', '1.0'),
                        metadata=data.get('metadata', {})
                    )
                    
                    self._checkpoints[checkpoint_info.checkpoint_id] = checkpoint_info
                    
                except Exception as e:
                    self.logger.error(f"Error loading checkpoint info from {file_path}: {e}")
            
            self.logger.debug(f"Loaded {len(self._checkpoints)} existing checkpoints")
            
        except Exception as e:
            self.logger.error(f"Error loading existing checkpoints: {e}")
    
    def create_checkpoint(self, checkpoint_id: str, application_state: Optional[Dict[str, Any]] = None,
                       scraping_state: Optional[Dict[str, Any]] = None,
                       resource_state: Optional[Dict[str, Any]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a data checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            application_state: Application-level state data
            scraping_state: Scraping-specific state data
            resource_state: Resource state data
            metadata: Additional metadata
            
        Returns:
            True if checkpoint created successfully, False otherwise
        """
        try:
            # Create checkpoint data
            checkpoint_data = CheckpointData(
                checkpoint_id=checkpoint_id,
                timestamp=time.time(),
                application_state=application_state or {},
                scraping_state=scraping_state or {},
                resource_state=resource_state or {},
                metadata=metadata or {}
            )
            
            # Serialize to temporary file
            temp_file_id = f"checkpoint_{checkpoint_id}"
            
            if self.atomic_manager:
                # Use atomic writer
                json_writer = self.atomic_manager.create_json_writer(
                    self.checkpoint_dir / f"checkpoint_{checkpoint_id}.json",
                    create_backup=True
                )
                success = json_writer.write(checkpoint_data.to_dict())
            else:
                # Fallback to temp file manager
                temp_path = self.temp_file_manager.create_temp_file(
                    temp_file_id,
                    suffix=".json",
                    purpose="checkpoint",
                    content=json.dumps(checkpoint_data.to_dict(), indent=2)
                )
                
                # Move to final location
                final_path = self.checkpoint_dir / f"checkpoint_{checkpoint_id}.json"
                success = self.temp_file_manager.move_temp_file(temp_file_id, final_path)
            
            if success:
                # Update checkpoint info
                checkpoint_info = CheckpointInfo(
                    checkpoint_id=checkpoint_id,
                    file_path=self.checkpoint_dir / f"checkpoint_{checkpoint_id}.json",
                    timestamp=checkpoint_data.timestamp,
                    size_bytes=checkpoint_info.file_path.stat().st_size if 'checkpoint_info' in locals() else 0,
                    version=checkpoint_data.version,
                    metadata=checkpoint_data.metadata
                )
                
                with self._lock:
                    self._checkpoints[checkpoint_id] = checkpoint_info
                
                self.logger.info(f"Created checkpoint: {checkpoint_id}")
                return True
            else:
                self.logger.error(f"Failed to create checkpoint: {checkpoint_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating checkpoint {checkpoint_id}: {e}")
            return False
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """
        Load a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to load
            
        Returns:
            CheckpointData if loaded successfully, None otherwise
        """
        with self._lock:
            checkpoint_info = self._checkpoints.get(checkpoint_id)
            if not checkpoint_info:
                self.logger.warning(f"Checkpoint {checkpoint_id} not found")
                return None
        
        try:
            with open(checkpoint_info.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            checkpoint_data = CheckpointData.from_dict(data)
            self.logger.info(f"Loaded checkpoint: {checkpoint_id}")
            return checkpoint_data
            
        except Exception as e:
            self.logger.error(f"Error loading checkpoint {checkpoint_id}: {e}")
            return None
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        with self._lock:
            checkpoint_info = self._checkpoints.get(checkpoint_id)
            if not checkpoint_info:
                self.logger.warning(f"Checkpoint {checkpoint_id} not found")
                return False
        
        try:
            checkpoint_info.file_path.unlink(missing_ok=True)
            
            with self._lock:
                del self._checkpoints[checkpoint_id]
            
            self.logger.info(f"Deleted checkpoint: {checkpoint_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting checkpoint {checkpoint_id}: {e}")
            return False
    
    def list_checkpoints(self) -> List[CheckpointInfo]:
        """List all available checkpoints."""
        with self._lock:
            return sorted(self._checkpoints.values(), key=lambda x: x.timestamp, reverse=True)
    
    def get_latest_checkpoint(self) -> Optional[CheckpointInfo]:
        """Get the most recent checkpoint."""
        checkpoints = self.list_checkpoints()
        return checkpoints[0] if checkpoints else None
    
    def cleanup_old_checkpoints(self, max_age_hours: float = 24.0, keep_count: int = 5) -> int:
        """
        Clean up old checkpoints.
        
        Args:
            max_age_hours: Maximum age in hours
            keep_count: Minimum number of recent checkpoints to keep
            
        Returns:
            Number of checkpoints deleted
        """
        with self._lock:
            checkpoints = list(self._checkpoints.values())
        
        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Determine which to delete
        to_delete = []
        max_age_seconds = max_age_hours * 3600
        
        for i, checkpoint in enumerate(checkpoints):
            # Always keep the most recent 'keep_count' checkpoints
            if i < keep_count:
                continue
            
            # Delete if older than max age
            if checkpoint.age > max_age_seconds:
                to_delete.append(checkpoint.checkpoint_id)
        
        # Delete old checkpoints
        deleted_count = 0
        for checkpoint_id in to_delete:
            if self.delete_checkpoint(checkpoint_id):
                deleted_count += 1
        
        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old checkpoints")
        
        return deleted_count
    
    def get_checkpoint_status(self) -> Dict[str, Any]:
        """Get status of checkpoints."""
        with self._lock:
            checkpoints = list(self._checkpoints.values())
        
        total_size = sum(cp.size_bytes for cp in checkpoints)
        
        return {
            'checkpoint_count': len(checkpoints),
            'total_size_bytes': total_size,
            'checkpoint_directory': str(self.checkpoint_dir),
            'latest_checkpoint': self.get_latest_checkpoint(),
            'oldest_checkpoint_age': max(cp.age for cp in checkpoints) if checkpoints else 0
        }
    
    @contextmanager
    def checkpoint_context(self, checkpoint_id: str, application_state: Optional[Dict[str, Any]] = None,
                        scraping_state: Optional[Dict[str, Any]] = None,
                        resource_state: Optional[Dict[str, Any]] = None,
                        metadata: Optional[Dict[str, Any]] = None):
        """Context manager for checkpoint creation and cleanup."""
        try:
            # Create checkpoint
            success = self.create_checkpoint(
                checkpoint_id, application_state, scraping_state, resource_state, metadata
            )
            
            if not success:
                raise RuntimeError(f"Failed to create checkpoint: {checkpoint_id}")
            
            yield
            
        finally:
            # Cleanup is handled by the regular cleanup process
            pass
    
    def create_auto_checkpoint(self, state_getter: Callable[[], Dict[str, Any]], 
                           checkpoint_id_prefix: str = "auto") -> str:
        """
        Create an automatic checkpoint with current state.
        
        Args:
            state_getter: Function that returns current state dictionary
            checkpoint_id_prefix: Prefix for auto-generated checkpoint ID
            
        Returns:
            ID of the created checkpoint
        """
        try:
            # Get current state
            current_state = state_getter()
            
            # Generate checkpoint ID
            timestamp = int(time.time())
            checkpoint_id = f"{checkpoint_id_prefix}_{timestamp}"
            
            # Extract state components
            application_state = current_state.get('application', {})
            scraping_state = current_state.get('scraping', {})
            resource_state = current_state.get('resources', {})
            metadata = current_state.get('metadata', {})
            metadata['auto_generated'] = True
            metadata['timestamp'] = timestamp
            
            # Create checkpoint
            if self.create_checkpoint(checkpoint_id, application_state, scraping_state, resource_state, metadata):
                return checkpoint_id
            else:
                raise RuntimeError(f"Failed to create auto checkpoint: {checkpoint_id}")
                
        except Exception as e:
            self.logger.error(f"Error creating auto checkpoint: {e}")
            raise
    
    def verify_checkpoint_integrity(self, checkpoint_id: str) -> bool:
        """
        Verify the integrity of a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to verify
            
        Returns:
            True if checkpoint is valid, False otherwise
        """
        with self._lock:
            checkpoint_info = self._checkpoints.get(checkpoint_id)
            if not checkpoint_info:
                return False
        
        try:
            # Check if file exists and is readable
            if not checkpoint_info.file_path.exists():
                return False
            
            # Try to load and validate JSON
            with open(checkpoint_info.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ['checkpoint_id', 'timestamp', 'version']
            if not all(field in data for field in required_fields):
                return False
            
            # Validate checkpoint ID matches
            if data.get('checkpoint_id') != checkpoint_id:
                return False
            
            self.logger.debug(f"Checkpoint {checkpoint_id} integrity verified")
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying checkpoint {checkpoint_id} integrity: {e}")
            return False
    
    def export_checkpoint(self, checkpoint_id: str, export_path: Union[str, Path]) -> bool:
        """
        Export a checkpoint to a different location.
        
        Args:
            checkpoint_id: ID of checkpoint to export
            export_path: Destination path
            
        Returns:
            True if exported successfully, False otherwise
        """
        with self._lock:
            checkpoint_info = self._checkpoints.get(checkpoint_id)
            if not checkpoint_info:
                self.logger.warning(f"Checkpoint {checkpoint_id} not found")
                return False
        
        try:
            import shutil
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(checkpoint_info.file_path, export_path)
            self.logger.info(f"Exported checkpoint {checkpoint_id} to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting checkpoint {checkpoint_id}: {e}")
            return False


# Global checkpoint manager instance
_checkpoint_manager = None


def get_checkpoint_manager(checkpoint_dir: Optional[Union[str, Path]] = None,
                       temp_file_manager: Optional[TempFileManager] = None) -> CheckpointManager:
    """Get the global checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager(checkpoint_dir, temp_file_manager)
    return _checkpoint_manager
