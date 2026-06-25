"""
State serialization for resumption after interrupts.
"""

import json
import pickle
import time
import threading
import logging
from typing import Any, Dict, List, Optional, Union, Callable, Type
from pathlib import Path
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from enum import Enum

from .checkpoint import CheckpointManager
from .atomic_operations import AtomicOperationManager


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    CUSTOM = "custom"


@dataclass
class StateSnapshot:
    """A snapshot of application state."""
    snapshot_id: str
    timestamp: float
    format: SerializationFormat
    data: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age(self) -> float:
        """Get age of snapshot in seconds."""
        return time.time() - self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'snapshot_id': self.snapshot_id,
            'timestamp': self.timestamp,
            'format': self.format.value,
            'data': self.data,
            'version': self.version,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateSnapshot':
        """Create from dictionary."""
        format_value = data.get('format', 'json')
        format_enum = SerializationFormat(format_value) if format_value in [f.value for f in SerializationFormat] else SerializationFormat.JSON
        
        return cls(
            snapshot_id=data.get('snapshot_id', ''),
            timestamp=data.get('timestamp', 0),
            format=format_enum,
            data=data.get('data', {}),
            version=data.get('version', '1.0'),
            metadata=data.get('metadata', {})
        )


class StateSerializer(ABC):
    """Abstract base class for state serializers."""
    
    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data from bytes."""
        pass
    
    @abstractmethod
    def get_format(self) -> SerializationFormat:
        """Get the serialization format."""
        pass


class JsonSerializer(StateSerializer):
    """JSON state serializer."""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes."""
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            return json_str.encode('utf-8')
        except Exception as e:
            raise ValueError(f"JSON serialization failed: {e}")
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data from JSON bytes."""
        try:
            json_str = data.decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"JSON deserialization failed: {e}")
    
    def get_format(self) -> SerializationFormat:
        """Get the serialization format."""
        return SerializationFormat.JSON


class PickleSerializer(StateSerializer):
    """Pickle state serializer."""
    
    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self.protocol = protocol
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to pickle bytes."""
        try:
            return pickle.dumps(data, protocol=self.protocol)
        except Exception as e:
            raise ValueError(f"Pickle serialization failed: {e}")
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data from pickle bytes."""
        try:
            return pickle.loads(data)
        except Exception as e:
            raise ValueError(f"Pickle deserialization failed: {e}")
    
    def get_format(self) -> SerializationFormat:
        """Get the serialization format."""
        return SerializationFormat.PICKLE


class StateSerializationManager:
    """Manages state serialization and deserialization."""
    
    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None,
                 atomic_manager: Optional[AtomicOperationManager] = None):
        self.logger = logging.getLogger(__name__)
        self.checkpoint_manager = checkpoint_manager
        self.atomic_manager = atomic_manager or AtomicOperationManager()
        
        # Initialize serializers
        self._serializers: Dict[SerializationFormat, StateSerializer] = {
            SerializationFormat.JSON: JsonSerializer(),
            SerializationFormat.PICKLE: PickleSerializer()
        }
        
        # State tracking
        self._state_snapshots: Dict[str, StateSnapshot] = {}
        self._lock = threading.RLock()
        
        # Custom serializers
        self._custom_serializers: Dict[str, StateSerializer] = {}
    
    def register_serializer(self, format_name: str, serializer: StateSerializer):
        """Register a custom serializer."""
        self._custom_serializers[format_name] = serializer
        self.logger.debug(f"Registered custom serializer: {format_name}")
    
    def get_serializer(self, format: SerializationFormat) -> StateSerializer:
        """Get a serializer for the given format."""
        return self._serializers.get(format, JsonSerializer())  # Fallback to JSON
    
    def serialize_state(self, state_data: Dict[str, Any], snapshot_id: str,
                      format: SerializationFormat = SerializationFormat.JSON,
                      metadata: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
        """
        Serialize state data.
        
        Args:
            state_data: State data to serialize
            snapshot_id: Unique identifier for the snapshot
            format: Serialization format to use
            metadata: Additional metadata
            
        Returns:
            Serialized data as bytes, or None if failed
        """
        try:
            # Create state snapshot
            snapshot = StateSnapshot(
                snapshot_id=snapshot_id,
                timestamp=time.time(),
                format=format,
                data=state_data,
                metadata=metadata or {}
            )
            
            # Get serializer
            serializer = self.get_serializer(format)
            
            # Serialize data
            serialized_data = serializer.serialize(snapshot.to_dict())
            
            # Store snapshot info
            with self._lock:
                self._state_snapshots[snapshot_id] = snapshot
            
            self.logger.info(f"Serialized state {snapshot_id} using {format.value}")
            return serialized_data
            
        except Exception as e:
            self.logger.error(f"Error serializing state {snapshot_id}: {e}")
            return None
    
    def deserialize_state(self, data: bytes, snapshot_id: str,
                        expected_format: Optional[SerializationFormat] = None) -> Optional[StateSnapshot]:
        """
        Deserialize state data.
        
        Args:
            data: Serialized data bytes
            snapshot_id: Expected snapshot ID
            expected_format: Expected serialization format
            
        Returns:
            StateSnapshot if deserialized successfully, None otherwise
        """
        try:
            # Try to detect format if not provided
            if expected_format is None:
                # Try JSON first
                try:
                    serializer = self._serializers[SerializationFormat.JSON]
                    snapshot_dict = serializer.deserialize(data)
                    format = SerializationFormat.JSON
                except:
                    # Try pickle
                    try:
                        serializer = self._serializers[SerializationFormat.PICKLE]
                        snapshot_dict = serializer.deserialize(data)
                        format = SerializationFormat.PICKLE
                    except:
                        self.logger.error("Could not detect serialization format")
                        return None
            else:
                serializer = self.get_serializer(expected_format)
                snapshot_dict = serializer.deserialize(data)
                format = expected_format
            
            # Create state snapshot
            snapshot = StateSnapshot.from_dict(snapshot_dict)
            
            # Verify snapshot ID matches
            if snapshot.snapshot_id != snapshot_id:
                self.logger.warning(f"Snapshot ID mismatch: expected {snapshot_id}, got {snapshot.snapshot_id}")
            
            # Store snapshot info
            with self._lock:
                self._state_snapshots[snapshot_id] = snapshot
            
            self.logger.info(f"Deserialized state {snapshot_id} using {format.value}")
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error deserializing state {snapshot_id}: {e}")
            return None
    
    def save_state_snapshot(self, snapshot_id: str, state_data: Dict[str, Any],
                         file_path: Optional[Union[str, Path]] = None,
                         format: SerializationFormat = SerializationFormat.JSON,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a state snapshot to file.
        
        Args:
            snapshot_id: Unique identifier for the snapshot
            state_data: State data to save
            file_path: Destination file path (auto-generated if None)
            format: Serialization format to use
            metadata: Additional metadata
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Generate file path if not provided
            if file_path is None:
                timestamp = int(time.time())
                suffix = ".json" if format == SerializationFormat.JSON else ".pkl"
                file_path = Path(f"state_snapshot_{timestamp}_{snapshot_id}{suffix}")
            
            file_path = Path(file_path)
            
            # Serialize state
            serialized_data = self.serialize_state(state_data, snapshot_id, format, metadata)
            if serialized_data is None:
                return False
            
            # Write to file
            if format == SerializationFormat.JSON:
                # Use atomic JSON writer
                json_writer = self.atomic_manager.create_json_writer(file_path)
                snapshot_dict = json.loads(serialized_data.decode('utf-8'))
                success = json_writer.write(snapshot_dict)
            else:
                # Use atomic pickle writer
                pickle_writer = self.atomic_manager.create_pickle_writer(file_path)
                snapshot_data = pickle.loads(serialized_data)
                success = pickle_writer.write(snapshot_data)
            
            if success:
                self.logger.info(f"Saved state snapshot {snapshot_id} to {file_path}")
                return True
            else:
                self.logger.error(f"Failed to save state snapshot {snapshot_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving state snapshot {snapshot_id}: {e}")
            return False
    
    def load_state_snapshot(self, file_path: Union[str, Path], 
                         snapshot_id: Optional[str] = None) -> Optional[StateSnapshot]:
        """
        Load a state snapshot from file.
        
        Args:
            file_path: Path to the snapshot file
            snapshot_id: Expected snapshot ID (for verification)
            
        Returns:
            StateSnapshot if loaded successfully, None otherwise
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.logger.error(f"State snapshot file not found: {file_path}")
                return None
            
            # Determine format from file extension
            if file_path.suffix.lower() == '.json':
                format = SerializationFormat.JSON
            elif file_path.suffix.lower() == '.pkl':
                format = SerializationFormat.PICKLE
            else:
                self.logger.warning(f"Unknown file format: {file_path.suffix}")
                format = SerializationFormat.JSON  # Default to JSON
            
            # Read file
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Deserialize
            snapshot = self.deserialize_state(data, snapshot_id or file_path.stem, format)
            
            if snapshot:
                self.logger.info(f"Loaded state snapshot from {file_path}")
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error loading state snapshot from {file_path}: {e}")
            return None
    
    def create_state_checkpoint(self, checkpoint_id: str, state_data: Dict[str, Any],
                            format: SerializationFormat = SerializationFormat.JSON,
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a checkpoint with state data.
        
        Args:
            checkpoint_id: Checkpoint ID
            state_data: State data to checkpoint
            format: Serialization format
            metadata: Additional metadata
            
        Returns:
            True if checkpoint created successfully, False otherwise
        """
        if not self.checkpoint_manager:
            self.logger.error("No checkpoint manager available")
            return False
        
        try:
            # Prepare checkpoint data
            checkpoint_data = {
                'application': state_data.get('application', {}),
                'scraping': state_data.get('scraping', {}),
                'resources': state_data.get('resources', {}),
                'serialization': {
                    'format': format.value,
                    'version': '1.0'
                }
            }
            
            # Add metadata
            if metadata:
                checkpoint_data['metadata'] = metadata
            
            # Create checkpoint
            success = self.checkpoint_manager.create_checkpoint(
                checkpoint_id=checkpoint_id,
                application_state=checkpoint_data.get('application'),
                scraping_state=checkpoint_data.get('scraping'),
                resource_state=checkpoint_data.get('resources'),
                metadata=checkpoint_data.get('metadata')
            )
            
            if success:
                self.logger.info(f"Created state checkpoint: {checkpoint_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error creating state checkpoint {checkpoint_id}: {e}")
            return False
    
    def load_state_from_checkpoint(self, checkpoint_id: str) -> Optional[StateSnapshot]:
        """
        Load state from a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID
            
        Returns:
            StateSnapshot if loaded successfully, None otherwise
        """
        if not self.checkpoint_manager:
            self.logger.error("No checkpoint manager available")
            return None
        
        try:
            # Load checkpoint
            checkpoint_data = self.checkpoint_manager.load_checkpoint(checkpoint_id)
            if not checkpoint_data:
                return None
            
            # Extract state data
            state_data = {
                'application': checkpoint_data.application_state,
                'scraping': checkpoint_data.scraping_state,
                'resources': checkpoint_data.resource_state
            }
            
            # Create state snapshot
            snapshot = StateSnapshot(
                snapshot_id=checkpoint_id,
                timestamp=checkpoint_data.timestamp,
                format=SerializationFormat.JSON,  # Checkpoints are JSON
                data=state_data,
                metadata=checkpoint_data.metadata
            )
            
            self.logger.info(f"Loaded state from checkpoint: {checkpoint_id}")
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error loading state from checkpoint {checkpoint_id}: {e}")
            return None
    
    def get_snapshot_info(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a state snapshot."""
        with self._lock:
            snapshot = self._state_snapshots.get(snapshot_id)
        
        if not snapshot:
            return None
        
        return {
            'snapshot_id': snapshot.snapshot_id,
            'timestamp': snapshot.timestamp,
            'age': snapshot.age,
            'format': snapshot.format.value,
            'version': snapshot.version,
            'data_keys': list(snapshot.data.keys()),
            'metadata': snapshot.metadata
        }
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all state snapshots."""
        with self._lock:
            snapshots = list(self._state_snapshots.values())
        
        return [
            {
                'snapshot_id': snapshot.snapshot_id,
                'timestamp': snapshot.timestamp,
                'age': snapshot.age,
                'format': snapshot.format.value,
                'version': snapshot.version
            }
            for snapshot in sorted(snapshots, key=lambda x: x.timestamp, reverse=True)
        ]
    
    def cleanup_old_snapshots(self, max_age_hours: float = 24.0) -> int:
        """Clean up old state snapshots."""
        with self._lock:
            old_snapshots = [
                snapshot_id for snapshot_id, snapshot in self._state_snapshots.items()
                if snapshot.age > (max_age_hours * 3600)
            ]
        
        for snapshot_id in old_snapshots:
            del self._state_snapshots[snapshot_id]
        
        if old_snapshots:
            self.logger.info(f"Cleaned up {len(old_snapshots)} old state snapshots")
        
        return len(old_snapshots)
    
    def get_serialization_status(self) -> Dict[str, Any]:
        """Get serialization manager status."""
        with self._lock:
            snapshot_count = len(self._state_snapshots)
        
        return {
            'snapshot_count': snapshot_count,
            'available_formats': [f.value for f in SerializationFormat],
            'custom_serializers': list(self._custom_serializers.keys()),
            'has_checkpoint_manager': self.checkpoint_manager is not None
        }


# Global state serialization manager instance
_state_serialization_manager = None


def get_state_serialization_manager(checkpoint_manager: Optional[CheckpointManager] = None) -> StateSerializationManager:
    """Get the global state serialization manager instance."""
    global _state_serialization_manager
    if _state_serialization_manager is None:
        _state_serialization_manager = StateSerializationManager(checkpoint_manager)
    return _state_serialization_manager
