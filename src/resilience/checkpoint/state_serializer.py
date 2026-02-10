"""
State Serializer for Checkpointing

Handles serialization and deserialization of application state with
schema versioning, compression, and encryption support.
"""

import json
import gzip
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from ..utils.serialization import JSONSerializer
from ..utils.integrity import ChecksumValidator, calculate_checksum
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    CUSTOM = "custom"


class CompressionType(Enum):
    """Supported compression types."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    CUSTOM = "custom"


class EncryptionType(Enum):
    """Supported encryption types."""
    NONE = "none"
    FERNET = "fernet"
    AES = "aes"
    CUSTOM = "custom"


@dataclass
class SerializationMetadata:
    """Metadata for serialized state."""
    format: SerializationFormat = SerializationFormat.JSON
    compression: CompressionType = CompressionType.GZIP
    encryption: EncryptionType = EncryptionType.FERNET
    schema_version: str = "1.0.0"
    checksum: str = ""
    size_bytes: int = 0
    compressed_size_bytes: int = 0
    encrypted_size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "format": self.format.value,
            "compression": self.compression.value,
            "encryption": self.encryption.value,
            "schema_version": self.schema_version,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "encrypted_size_bytes": self.encrypted_size_bytes,
            "created_at": self.created_at.isoformat(),
            "custom_fields": self.custom_fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SerializationMetadata':
        """Create SerializationMetadata from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
        
        return cls(
            format=SerializationFormat(data.get("format", "json")),
            compression=CompressionType(data.get("compression", "gzip")),
            encryption=EncryptionType(data.get("encryption", "fernet")),
            schema_version=data.get("schema_version", "1.0.0"),
            checksum=data.get("checksum", ""),
            size_bytes=data.get("size_bytes", 0),
            compressed_size_bytes=data.get("compressed_size_bytes", 0),
            encrypted_size_bytes=data.get("encrypted_size_bytes", 0),
            created_at=created_at,
            custom_fields=data.get("custom_fields", {})
        )


class StateSerializer(ABC):
    """Abstract base class for state serializers."""
    
    @abstractmethod
    def serialize(
        self,
        state: Dict[str, Any],
        metadata: Optional[SerializationMetadata] = None
    ) -> bytes:
        """
        Serialize state to bytes.
        
        Args:
            state: State data to serialize
            metadata: Serialization metadata
            
        Returns:
            Serialized bytes
        """
        pass
    
    @abstractmethod
    def deserialize(
        self,
        data: bytes,
        metadata: Optional[SerializationMetadata] = None
    ) -> Dict[str, Any]:
        """
        Deserialize bytes to state.
        
        Args:
            data: Serialized data
            metadata: Serialization metadata
            
        Returns:
            Deserialized state
        """
        pass


class JSONStateSerializer(StateSerializer):
    """JSON state serializer with compression and encryption support."""
    
    def __init__(self):
        """Initialize JSON state serializer."""
        self.json_serializer = JSONSerializer()
        self.checksum_validator = ChecksumValidator()
        self.logger = get_logger("json_state_serializer")
    
    def serialize(
        self,
        state: Dict[str, Any],
        metadata: Optional[SerializationMetadata] = None
    ) -> bytes:
        """
        Serialize state to JSON with compression and encryption.
        
        Args:
            state: State data to serialize
            metadata: Serialization metadata
            
        Returns:
            Serialized bytes
        """
        if metadata is None:
            metadata = SerializationMetadata()
        
        try:
            # Serialize to JSON
            json_data = json.dumps(state, default=str, separators=(',', ':')).encode('utf-8')
            metadata.size_bytes = len(json_data)
            
            # Calculate checksum
            metadata.checksum = self.checksum_validator.calculate_checksum(json_data)
            
            # Apply compression
            if metadata.compression == CompressionType.GZIP:
                json_data = gzip.compress(json_data)
                metadata.compressed_size_bytes = len(json_data)
            else:
                metadata.compressed_size_bytes = metadata.size_bytes
            
            # Apply encryption
            if metadata.encryption == EncryptionType.FERNET:
                # Note: In production, encryption key should be loaded from secure storage
                from cryptography.fernet import Fernet
                cipher = Fernet(Fernet.generate_key())  # Generate key for demo
                json_data = cipher.encrypt(json_data)
                metadata.encrypted_size_bytes = len(json_data)
            else:
                metadata.encrypted_size_bytes = metadata.compressed_size_bytes
            
            return json_data
            
        except Exception as e:
            self.logger.error(
                f"Failed to serialize state: {str(e)}",
                event_type="state_serialization_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="json_state_serializer"
            )
            raise
    
    def deserialize(
        self,
        data: bytes,
        metadata: Optional[SerializationMetadata] = None
    ) -> Dict[str, Any]:
        """
        Deserialize JSON data with decompression and decryption.
        
        Args:
            data: Serialized data
            metadata: Serialization metadata
            
        Returns:
            Deserialized state
        """
        if metadata is None:
            metadata = SerializationMetadata()
        
        try:
            # Apply decryption
            if metadata.encryption == EncryptionType.FERNET:
                from cryptography.fernet import Fernet
                cipher = Fernet(Fernet.generate_key())  # Generate key for demo
                data = cipher.decrypt(data)
            
            # Apply decompression
            if metadata.compression == CompressionType.GZIP:
                data = gzip.decompress(data)
            
            # Parse JSON
            state = json.loads(data.decode('utf-8'))
            
            # Validate checksum
            if metadata.checksum:
                json_data = json.dumps(state, default=str, separators=(',', ':')).encode('utf-8')
                calculated_checksum = self.checksum_validator.calculate_checksum(json_data)
                if calculated_checksum != metadata.checksum:
                    raise ValueError(f"Checksum mismatch: expected {metadata.checksum}, got {calculated_checksum}")
            
            return state
            
        except Exception as e:
            self.logger.error(
                f"Failed to deserialize state: {str(e)}",
                event_type="state_deserialization_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="json_state_serializer"
            )
            raise


class PickleStateSerializer(StateSerializer):
    """Pickle state serializer for complex Python objects."""
    
    def serialize(
        self,
        state: Dict[str, Any],
        metadata: Optional[SerializationMetadata] = None
    ) -> bytes:
        """
        Serialize state using pickle.
        
        Args:
            state: State data to serialize
            metadata: Serialization metadata
            
        Returns:
            Serialized bytes
        """
        import pickle
        
        if metadata is None:
            metadata = SerializationMetadata(format=SerializationFormat.PICKLE)
        
        try:
            # Serialize with pickle
            data = pickle.dumps(state)
            metadata.size_bytes = len(data)
            
            # Calculate checksum
            metadata.checksum = calculate_checksum(data)
            
            # Apply compression
            if metadata.compression == CompressionType.GZIP:
                data = gzip.compress(data)
                metadata.compressed_size_bytes = len(data)
            else:
                metadata.compressed_size_bytes = metadata.size_bytes
            
            return data
            
        except Exception as e:
            raise Exception(f"Failed to serialize state with pickle: {str(e)}")
    
    def deserialize(
        self,
        data: bytes,
        metadata: Optional[SerializationMetadata] = None
    ) -> Dict[str, Any]:
        """
        Deserialize pickle data.
        
        Args:
            data: Serialized data
            metadata: Serialization metadata
            
        Returns:
            Deserialized state
        """
        import pickle
        
        if metadata is None:
            metadata = SerializationMetadata(format=SerializationFormat.PICKLE)
        
        try:
            # Apply decompression
            if metadata.compression == CompressionType.GZIP:
                data = gzip.decompress(data)
            
            # Deserialize with pickle
            state = pickle.loads(data)
            
            # Validate checksum
            if metadata.checksum:
                pickle_data = pickle.dumps(state)
                calculated_checksum = calculate_checksum(pickle_data)
                if calculated_checksum != metadata.checksum:
                    raise ValueError(f"Checksum mismatch: expected {metadata.checksum}, got {calculated_checksum}")
            
            return state
            
        except Exception as e:
            raise Exception(f"Failed to deserialize state with pickle: {str(e)}")


class StateSerializerFactory:
    """Factory for creating state serializers."""
    
    _serializers = {
        SerializationFormat.JSON: JSONStateSerializer,
        SerializationFormat.PICKLE: PickleStateSerializer
    }
    
    @classmethod
    def create_serializer(
        cls,
        format_type: SerializationFormat,
        custom_serializer: Optional[StateSerializer] = None
    ) -> StateSerializer:
        """
        Create a state serializer instance.
        
        Args:
            format_type: Type of serialization format
            custom_serializer: Custom serializer for CUSTOM format
            
        Returns:
            State serializer instance
        """
        if format_type == SerializationFormat.CUSTOM:
            if not custom_serializer:
                raise ValueError("Custom serializer required for CUSTOM format")
            return custom_serializer
        
        serializer_class = cls._serializers.get(format_type)
        if not serializer_class:
            raise ValueError(f"Unknown serialization format: {format_type}")
        
        return serializer_class()
    
    @classmethod
    def register_serializer(
        cls,
        format_type: SerializationFormat,
        serializer_class: type
    ) -> None:
        """
        Register a custom state serializer.
        
        Args:
            format_type: Serialization format to register
            serializer_class: Serializer class to register
        """
        cls._serializers[format_type] = serializer_class


class StateMigrationManager:
    """Manages state migration between schema versions."""
    
    def __init__(self):
        """Initialize state migration manager."""
        self.logger = get_logger("state_migration_manager")
        self.migrations = {}
        self._register_default_migrations()
    
    def _register_default_migrations(self) -> None:
        """Register default state migrations."""
        # Migration from 1.0.0 to 1.1.0
        self.migrations["1.0.0"] = {
            "1.1.0": self._migrate_1_0_0_to_1_1_0
        }
        
        # Migration from 1.1.0 to 1.2.0
        self.migrations["1.1.0"] = {
            "1.2.0": self._migrate_1_1_0_to_1_2_0
        }
    
    def migrate_state(
        self,
        state: Dict[str, Any],
        from_version: str,
        to_version: str
    ) -> Dict[str, Any]:
        """
        Migrate state from one version to another.
        
        Args:
            state: State data to migrate
            from_version: Source version
            to_version: Target version
            
        Returns:
            Migrated state
        """
        if from_version == to_version:
            return state
        
        try:
            current_state = state.copy()
            current_version = from_version
            
            # Apply migrations in sequence
            while current_version != to_version:
                if current_version not in self.migrations:
                    raise ValueError(f"No migration path from {current_version}")
                
                next_migrations = self.migrations[current_version]
                
                # Find the next version to migrate to
                for version, migration_func in next_migrations.items():
                    if self._is_version_newer(version, current_version):
                        current_state = migration_func(current_state)
                        current_version = version
                        break
                else:
                    raise ValueError(f"No migration path from {current_version}")
            
            return current_state
            
        except Exception as e:
            self.logger.error(
                f"Failed to migrate state from {from_version} to {to_version}: {str(e)}",
                event_type="state_migration_error",
                correlation_id=get_correlation_id(),
                context={
                    "from_version": from_version,
                    "to_version": to_version,
                    "error": str(e)
                },
                component="state_migration_manager"
            )
            raise
    
    def _is_version_newer(self, version1: str, version2: str) -> bool:
        """Check if version1 is newer than version2."""
        try:
            from semantic_version import Version
            return Version(version1) > Version(version2)
        except Exception:
            return False
    
    def _migrate_1_0_0_to_1_1_0(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate state from version 1.0.0 to 1.1.0."""
        # Example migration: Add new metadata field
        if "metadata" not in state:
            state["metadata"] = {}
        
        # Add version to metadata
        state["metadata"]["schema_version"] = "1.1.0"
        
        return state
    
    def _migrate_1_1_0_to_1_2_0(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate state from version 1.1.0 to 1.2.0."""
        # Example migration: Rename field
        if "old_field_name" in state:
            state["new_field_name"] = state.pop("old_field_name")
        
        # Update version in metadata
        if "metadata" in state:
            state["metadata"]["schema_version"] = "1.2.0"
        
        return state


# Global instances
_state_serializer_factory = StateSerializerFactory()
_state_migration_manager = StateMigrationManager()


def serialize_state(
    state: Dict[str, Any],
    format_type: SerializationFormat = SerializationFormat.JSON,
    compression: CompressionType = CompressionType.GZIP,
    encryption: EncryptionType = EncryptionType.FERNET,
    custom_serializer: Optional[StateSerializer] = None
) -> bytes:
    """
    Serialize state with specified options.
    
    Args:
        state: State data to serialize
        format_type: Serialization format
        compression: Compression type
        encryption: Encryption type
        custom_serializer: Custom serializer
        
    Returns:
        Serialized bytes
    """
    metadata = SerializationMetadata(
        format=format_type,
        compression=compression,
        encryption=encryption
    )
    
    serializer = _state_serializer_factory.create_serializer(format_type, custom_serializer)
    return serializer.serialize(state, metadata)


def deserialize_state(
    data: bytes,
    format_type: SerializationFormat = SerializationFormat.JSON,
    compression: CompressionType = CompressionType.GZIP,
    encryption: EncryptionType = EncryptionType.FERNET,
    custom_serializer: Optional[StateSerializer] = None
) -> Dict[str, Any]:
    """
    Deserialize state with specified options.
    
    Args:
        data: Serialized data
        format_type: Serialization format
        compression: Compression type
        encryption: Encryption type
        custom_serializer: Custom serializer
        
    Returns:
        Deserialized state
    """
    metadata = SerializationMetadata(
        format=format_type,
        compression=compression,
        encryption=encryption
    )
    
    serializer = _state_serializer_factory.create_serializer(format_type, custom_serializer)
    return serializer.deserialize(data, metadata)


def migrate_state(
    state: Dict[str, Any],
    from_version: str,
    to_version: str
) -> Dict[str, Any]:
    """Migrate state using the global migration manager."""
    return _state_migration_manager.migrate_state(state, from_version, to_version)


def create_state_serializer(
    format_type: SerializationFormat,
    custom_serializer: Optional[StateSerializer] = None
) -> StateSerializer:
    """Create a state serializer using the global factory."""
    return _state_serializer_factory.create_serializer(format_type, custom_serializer)
