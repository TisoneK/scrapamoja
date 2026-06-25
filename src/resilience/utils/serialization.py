"""
JSON Serialization Utilities with Schema Versioning

Provides JSON serialization and deserialization with schema versioning,
compression support, and backward compatibility for resilience data.
"""

import json
import gzip
import hashlib
from typing import Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import semantic_version


class SerializationError(Exception):
    """Raised when serialization operations fail."""
    pass


class VersionMismatchError(SerializationError):
    """Raised when schema version is incompatible."""
    pass


class JSONSerializer:
    """JSON serializer with schema versioning and compression support."""
    
    def __init__(self, current_version: str = "1.0.0"):
        self.current_version = current_version
        self.version_parser = semantic_version.Version
    
    def serialize(
        self,
        data: Dict[str, Any],
        version: Optional[str] = None,
        compress: bool = False
    ) -> bytes:
        """
        Serialize data to JSON with versioning.
        
        Args:
            data: Data to serialize
            version: Schema version (uses current if not provided)
            compress: Whether to compress the output
            
        Returns:
            Serialized bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            # Add version metadata
            serialized_data = {
                "version": version or self.current_version,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            
            # Convert to JSON string
            json_str = json.dumps(serialized_data, default=str, separators=(',', ':'))
            
            # Convert to bytes
            json_bytes = json_str.encode('utf-8')
            
            # Compress if requested
            if compress:
                json_bytes = gzip.compress(json_bytes)
            
            return json_bytes
            
        except Exception as e:
            raise SerializationError(f"Failed to serialize data: {e}")
    
    def deserialize(
        self,
        data: Union[bytes, str],
        expected_version: Optional[str] = None,
        compressed: bool = False
    ) -> Dict[str, Any]:
        """
        Deserialize JSON data with version checking.
        
        Args:
            data: Data to deserialize
            expected_version: Expected schema version (optional)
            compressed: Whether data is compressed
            
        Returns:
            Deserialized data
            
        Raises:
            SerializationError: If deserialization fails
            VersionMismatchError: If version is incompatible
        """
        try:
            # Handle input types
            if isinstance(data, str):
                json_bytes = data.encode('utf-8')
            else:
                json_bytes = data
            
            # Decompress if needed
            if compressed:
                json_bytes = gzip.decompress(json_bytes)
            
            # Parse JSON
            json_str = json_bytes.decode('utf-8')
            serialized_data = json.loads(json_str)
            
            # Validate structure
            if not isinstance(serialized_data, dict):
                raise SerializationError("Invalid serialized data structure")
            
            if "version" not in serialized_data:
                raise SerializationError("Missing version information")
            
            if "data" not in serialized_data:
                raise SerializationError("Missing data payload")
            
            version = serialized_data["version"]
            payload_data = serialized_data["data"]
            
            # Check version compatibility
            if expected_version:
                if not self._is_version_compatible(version, expected_version):
                    raise VersionMismatchError(
                        f"Version {version} is not compatible with expected {expected_version}"
                    )
            
            # Apply version migrations if needed
            migrated_data = self._migrate_data(payload_data, version)
            
            return migrated_data
            
        except gzip.BadGzipFile as e:
            raise SerializationError(f"Failed to decompress data: {e}")
        except json.JSONDecodeError as e:
            raise SerializationError(f"Failed to parse JSON: {e}")
        except Exception as e:
            if isinstance(e, (SerializationError, VersionMismatchError)):
                raise
            raise SerializationError(f"Failed to deserialize data: {e}")
    
    def _is_version_compatible(
        self,
        actual_version: str,
        expected_version: str
    ) -> bool:
        """
        Check if actual version is compatible with expected version.
        
        Args:
            actual_version: Actual schema version
            expected_version: Expected schema version
            
        Returns:
            True if compatible, False otherwise
        """
        try:
            actual = self.version_parser(actual_version)
            expected = self.version_parser(expected_version)
            
            # Major version must match
            if actual.major != expected.major:
                return False
            
            # Actual version should be >= expected version
            return actual >= expected
            
        except Exception:
            return False
    
    def _migrate_data(
        self,
        data: Dict[str, Any],
        from_version: str
    ) -> Dict[str, Any]:
        """
        Migrate data from older version to current version.
        
        Args:
            data: Data to migrate
            from_version: Source version
            
        Returns:
            Migrated data
        """
        try:
            from_ver = self.version_parser(from_version)
            current_ver = self.version_parser(self.current_version)
            
            # No migration needed if versions are the same
            if from_ver == current_ver:
                return data
            
            # Apply migrations based on version differences
            migrated_data = data.copy()
            
            # Example migration logic (customize based on actual schema changes)
            if from_ver < self.version_parser("1.1.0"):
                migrated_data = self._migrate_to_1_1_0(migrated_data)
            
            if from_ver < self.version_parser("1.2.0"):
                migrated_data = self._migrate_to_1_2_0(migrated_data)
            
            return migrated_data
            
        except Exception:
            # If migration fails, return original data
            return data
    
    def _migrate_to_1_1_0(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate data to version 1.1.0."""
        # Example: Add new field with default value
        if "metadata" not in data:
            data["metadata"] = {}
        return data
    
    def _migrate_to_1_2_0(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate data to version 1.2.0."""
        # Example: Rename field
        if "old_field_name" in data:
            data["new_field_name"] = data.pop("old_field_name")
        return data


class FileSerializer:
    """File-based serializer with automatic compression and versioning."""
    
    def __init__(self, serializer: Optional[JSONSerializer] = None):
        self.serializer = serializer or JSONSerializer()
    
    def save_to_file(
        self,
        file_path: Union[str, Path],
        data: Dict[str, Any],
        version: Optional[str] = None,
        compress: bool = True
    ) -> None:
        """
        Save data to file with versioning and compression.
        
        Args:
            file_path: Path to save file
            data: Data to save
            version: Schema version
            compress: Whether to compress the file
        """
        file_path = Path(file_path)
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize data
        serialized_data = self.serializer.serialize(data, version, compress)
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(serialized_data)
    
    def load_from_file(
        self,
        file_path: Union[str, Path],
        expected_version: Optional[str] = None,
        compressed: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Load data from file with version checking.
        
        Args:
            file_path: Path to load file
            expected_version: Expected schema version
            compressed: Whether file is compressed (auto-detect if None)
            
        Returns:
            Loaded data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise SerializationError(f"File not found: {file_path}")
        
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Auto-detect compression if not specified
        if compressed is None:
            compressed = self._is_compressed(file_data)
        
        # Deserialize data
        return self.serializer.deserialize(file_data, expected_version, compressed)
    
    def _is_compressed(self, data: bytes) -> bool:
        """Check if data is gzip compressed."""
        return data.startswith(b'\x1f\x8b')


# Global serializer instance
_default_serializer = JSONSerializer()
_file_serializer = FileSerializer(_default_serializer)


def serialize_json(
    data: Dict[str, Any],
    version: Optional[str] = None,
    compress: bool = False
) -> bytes:
    """Serialize data to JSON with versioning."""
    return _default_serializer.serialize(data, version, compress)


def deserialize_json(
    data: Union[bytes, str],
    expected_version: Optional[str] = None,
    compressed: bool = False
) -> Dict[str, Any]:
    """Deserialize JSON data with version checking."""
    return _default_serializer.deserialize(data, expected_version, compressed)


def save_json_file(
    file_path: Union[str, Path],
    data: Dict[str, Any],
    version: Optional[str] = None,
    compress: bool = True
) -> None:
    """Save data to JSON file with versioning."""
    _file_serializer.save_to_file(file_path, data, version, compress)


def load_json_file(
    file_path: Union[str, Path],
    expected_version: Optional[str] = None,
    compressed: Optional[bool] = None
) -> Dict[str, Any]:
    """Load data from JSON file with version checking."""
    return _file_serializer.load_from_file(file_path, expected_version, compressed)
