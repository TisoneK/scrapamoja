"""
Data Integrity Validation Utilities

Provides checksum validation, corruption detection, and data integrity
verification for resilience components including checkpoints and configuration.
"""

import hashlib
import json
from typing import Dict, Any, Optional, Union, Tuple
from pathlib import Path


class IntegrityError(Exception):
    """Raised when data integrity validation fails."""
    pass


class ChecksumValidator:
    """Validates and manages data integrity using cryptographic checksums."""
    
    def __init__(self, algorithm: str = "sha256"):
        """
        Initialize checksum validator.
        
        Args:
            algorithm: Hash algorithm to use (sha256, sha1, md5, etc.)
        """
        self.algorithm = algorithm.lower()
        
        if self.algorithm not in hashlib.algorithms_available:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    def calculate_checksum(
        self,
        data: Union[bytes, str, Dict[str, Any]]
    ) -> str:
        """
        Calculate checksum for data.
        
        Args:
            data: Data to calculate checksum for
            
        Returns:
            Hexadecimal checksum string
        """
        if isinstance(data, dict):
            # Serialize dict to JSON with sorted keys for consistency
            data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            data_bytes = data_str.encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        hash_obj = hashlib.new(self.algorithm)
        hash_obj.update(data_bytes)
        return hash_obj.hexdigest()
    
    def validate_checksum(
        self,
        data: Union[bytes, str, Dict[str, Any]],
        expected_checksum: str
    ) -> bool:
        """
        Validate data against expected checksum.
        
        Args:
            data: Data to validate
            expected_checksum: Expected checksum
            
        Returns:
            True if checksum matches, False otherwise
        """
        actual_checksum = self.calculate_checksum(data)
        return actual_checksum.lower() == expected_checksum.lower()
    
    def validate_checksum_or_raise(
        self,
        data: Union[bytes, str, Dict[str, Any]],
        expected_checksum: str
    ) -> None:
        """
        Validate data against expected checksum, raise exception if invalid.
        
        Args:
            data: Data to validate
            expected_checksum: Expected checksum
            
        Raises:
            IntegrityError: If checksum validation fails
        """
        if not self.validate_checksum(data, expected_checksum):
            actual_checksum = self.calculate_checksum(data)
            raise IntegrityError(
                f"Checksum validation failed. Expected: {expected_checksum}, "
                f"Actual: {actual_checksum}"
            )


class FileIntegrityManager:
    """Manages file integrity with checksum storage and validation."""
    
    def __init__(self, checksum_dir: Optional[str] = None):
        """
        Initialize file integrity manager.
        
        Args:
            checksum_dir: Directory to store checksum files
        """
        self.checksum_dir = Path(checksum_dir or "./data/checksums")
        self.checksum_dir.mkdir(parents=True, exist_ok=True)
        self.validator = ChecksumValidator()
    
    def calculate_file_checksum(self, file_path: Union[str, Path]) -> str:
        """
        Calculate checksum for file contents.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hexadecimal checksum string
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file in binary mode
        with open(file_path, 'rb') as f:
            return self.validator.calculate_checksum(f.read())
    
    def save_file_checksum(self, file_path: Union[str, Path]) -> str:
        """
        Calculate and save checksum for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Calculated checksum
        """
        file_path = Path(file_path)
        checksum = self.calculate_file_checksum(file_path)
        
        # Save checksum to file
        checksum_file = self.checksum_dir / f"{file_path.stem}.checksum"
        with open(checksum_file, 'w') as f:
            f.write(f"{checksum}  {file_path.name}")
        
        return checksum
    
    def load_file_checksum(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Load saved checksum for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Saved checksum or None if not found
        """
        file_path = Path(file_path)
        checksum_file = self.checksum_dir / f"{file_path.stem}.checksum"
        
        if not checksum_file.exists():
            return None
        
        try:
            with open(checksum_file, 'r') as f:
                content = f.read().strip()
                # Extract checksum (format: "checksum filename")
                return content.split()[0]
        except Exception:
            return None
    
    def validate_file_integrity(
        self,
        file_path: Union[str, Path],
        expected_checksum: Optional[str] = None
    ) -> bool:
        """
        Validate file integrity.
        
        Args:
            file_path: Path to file
            expected_checksum: Expected checksum (loads from file if not provided)
            
        Returns:
            True if file is valid, False otherwise
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False
        
        # Get expected checksum
        if expected_checksum is None:
            expected_checksum = self.load_file_checksum(file_path)
            if expected_checksum is None:
                # No checksum available, cannot validate
                return True
        
        try:
            actual_checksum = self.calculate_file_checksum(file_path)
            return actual_checksum.lower() == expected_checksum.lower()
        except Exception:
            return False
    
    def validate_file_integrity_or_raise(
        self,
        file_path: Union[str, Path],
        expected_checksum: Optional[str] = None
    ) -> None:
        """
        Validate file integrity, raise exception if invalid.
        
        Args:
            file_path: Path to file
            expected_checksum: Expected checksum
            
        Raises:
            IntegrityError: If file integrity validation fails
        """
        if not self.validate_file_integrity(file_path, expected_checksum):
            file_path = Path(file_path)
            actual_checksum = self.calculate_file_checksum(file_path)
            raise IntegrityError(
                f"File integrity validation failed for {file_path}. "
                f"Expected: {expected_checksum}, Actual: {actual_checksum}"
            )
    
    def delete_file_checksum(self, file_path: Union[str, Path]) -> bool:
        """
        Delete saved checksum for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if checksum was deleted, False if not found
        """
        file_path = Path(file_path)
        checksum_file = self.checksum_dir / f"{file_path.stem}.checksum"
        
        if checksum_file.exists():
            checksum_file.unlink()
            return True
        return False


class DataIntegrityWrapper:
    """Wrapper for data with automatic integrity validation."""
    
    def __init__(
        self,
        data: Dict[str, Any],
        checksum: Optional[str] = None,
        algorithm: str = "sha256"
    ):
        """
        Initialize data integrity wrapper.
        
        Args:
            data: Data to wrap
            checksum: Pre-calculated checksum (calculated if not provided)
            algorithm: Hash algorithm to use
        """
        self.data = data
        self.algorithm = algorithm
        self.validator = ChecksumValidator(algorithm)
        
        if checksum is None:
            self.checksum = self.validator.calculate_checksum(data)
        else:
            self.checksum = checksum
    
    def validate(self) -> bool:
        """Validate data integrity."""
        return self.validator.validate_checksum(self.data, self.checksum)
    
    def validate_or_raise(self) -> None:
        """Validate data integrity, raise exception if invalid."""
        self.validator.validate_checksum_or_raise(self.data, self.checksum)
    
    def update_data(self, new_data: Dict[str, Any]) -> None:
        """Update data and recalculate checksum."""
        self.data = new_data
        self.checksum = self.validator.calculate_checksum(new_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with checksum."""
        return {
            "data": self.data,
            "checksum": self.checksum,
            "algorithm": self.algorithm
        }
    
    @classmethod
    def from_dict(cls, data_dict: Dict[str, Any]) -> 'DataIntegrityWrapper':
        """Create wrapper from dictionary."""
        return cls(
            data=data_dict["data"],
            checksum=data_dict["checksum"],
            algorithm=data_dict.get("algorithm", "sha256")
        )


# Global instances
_default_validator = ChecksumValidator()
_file_manager = FileIntegrityManager()


def calculate_checksum(data: Union[bytes, str, Dict[str, Any]]) -> str:
    """Calculate checksum for data using default validator."""
    return _default_validator.calculate_checksum(data)


def validate_checksum(
    data: Union[bytes, str, Dict[str, Any]],
    expected_checksum: str
) -> bool:
    """Validate data against expected checksum."""
    return _default_validator.validate_checksum(data, expected_checksum)


def validate_checksum_or_raise(
    data: Union[bytes, str, Dict[str, Any]],
    expected_checksum: str
) -> None:
    """Validate data against expected checksum, raise exception if invalid."""
    _default_validator.validate_checksum_or_raise(data, expected_checksum)


def calculate_file_checksum(file_path: Union[str, Path]) -> str:
    """Calculate checksum for file contents."""
    return _file_manager.calculate_file_checksum(file_path)


def validate_file_integrity(
    file_path: Union[str, Path],
    expected_checksum: Optional[str] = None
) -> bool:
    """Validate file integrity."""
    return _file_manager.validate_file_integrity(file_path, expected_checksum)


def validate_file_integrity_or_raise(
    file_path: Union[str, Path],
    expected_checksum: Optional[str] = None
) -> None:
    """Validate file integrity, raise exception if invalid."""
    _file_manager.validate_file_integrity_or_raise(file_path, expected_checksum)
