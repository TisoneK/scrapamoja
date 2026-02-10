"""
Checkpoint Corruption Detector

Detects and handles corruption in checkpoint files using checksum validation,
schema versioning, and data integrity checks with automatic recovery mechanisms.
"""

import json
import gzip
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from ..models.checkpoint import Checkpoint, CheckpointStatus
from ..utils.integrity import ChecksumValidator, validate_checksum
from ..utils.serialization import JSONSerializer
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_checkpoint_event


class CorruptionType(Enum):
    """Types of corruption that can be detected."""
    CHECKSUM_MISMATCH = "checksum_mismatch"
    SCHEMA_VERSION_MISMATCH = "schema_version_mismatch"
    INVALID_JSON = "invalid_json"
    INVALID_COMPRESSION = "invalid_compression"
    INVALID_ENCRYPTION = "invalid_encryption"
    MISSING_FIELDS = "missing_fields"
    INVALID_DATA_TYPES = "invalid_data_types"
    SIZE_MISMATCH = "size_mismatch"
    UNKNOWN = "unknown"


class CorruptionSeverity(Enum):
    """Severity levels for corruption."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CorruptionReport:
    """Report of corruption detection and analysis."""
    checkpoint_id: str
    corruption_type: CorruptionType
    severity: CorruptionSeverity
    detected_at: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)
    recovery_possible: bool = False
    recovery_actions: List[str] = field(default_factory=list)
    original_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "corruption_type": self.corruption_type.value,
            "severity": self.severity.value,
            "detected_at": self.detected_at.isoformat(),
            "details": self.details,
            "recovery_possible": self.recovery_possible,
            "recovery_actions": self.recovery_actions,
            "original_error": self.original_error
        }


class CheckpointCorruptionDetector:
    """Detects and analyzes corruption in checkpoint files."""
    
    def __init__(self):
        """Initialize corruption detector."""
        self.logger = get_logger("checkpoint_corruption_detector")
        self.checksum_validator = ChecksumValidator()
        self.json_serializer = JSONSerializer()
        
        # Required fields for checkpoint validation
        self.required_fields = {
            "id",
            "job_id",
            "timestamp",
            "sequence_number",
            "status",
            "checkpoint_type",
            "compression",
            "encryption_enabled",
            "schema_version"
        }
        
        # Field type validation
        self.field_types = {
            "id": str,
            "job_id": str,
            "timestamp": str,
            "sequence_number": int,
            "status": str,
            "checkpoint_type": str,
            "compression": str,
            "encryption_enabled": bool,
            "schema_version": str,
            "checksum": str,
            "size_bytes": int,
            "compressed_size_bytes": int,
            "parent_checkpoint_id": (str, type(None)),
            "child_checkpoint_ids": list,
            "expires_at": (str, type(None)),
            "description": str,
            "tags": list
        }
    
    def detect_corruption(
        self,
        checkpoint: Checkpoint,
        file_data: Optional[bytes] = None
    ) -> Optional[CorruptionReport]:
        """
        Detect corruption in a checkpoint.
        
        Args:
            checkpoint: Checkpoint to validate
            file_data: Raw file data (optional)
            
        Returns:
            CorruptionReport if corruption detected, None otherwise
        """
        try:
            # Check checksum integrity
            corruption_report = self._validate_checksum(checkpoint)
            if corruption_report:
                return corruption_report
            
            # Check schema version compatibility
            corruption_report = self._validate_schema_version(checkpoint)
            if corruption_report:
                return corruption_report
            
            # Check data structure integrity
            corruption_report = self._validate_data_structure(checkpoint)
            if corruption_report:
                return corruption_report
            
            # Check field types
            corruption_report = self._validate_field_types(checkpoint)
            if corruption_report:
                return corruption_report
            
            # Check size consistency if file data provided
            if file_data:
                corruption_report = self._validate_size_consistency(checkpoint, file_data)
                if corruption_report:
                    return corruption_report
            
            # No corruption detected
            return None
            
        except Exception as e:
            return CorruptionReport(
                checkpoint_id=checkpoint.id,
                corruption_type=CorruptionType.UNKNOWN,
                severity=CorruptionSeverity.HIGH,
                details={"error": str(e), "stack_trace": str(e.__traceback__) if hasattr(e, '__traceback__') else None},
                recovery_possible=False,
                original_error=str(e)
            )
    
    def _validate_checksum(self, checkpoint: Checkpoint) -> Optional[CorruptionReport]:
        """Validate checksum integrity."""
        try:
            if not checkpoint.data or not checkpoint.checksum:
                return CorruptionReport(
                    checkpoint_id=checkpoint.id,
                    corruption_type=CorruptionType.CHECKSUM_MISMATCH,
                    severity=CorruptionSeverity.HIGH,
                    details={
                        "reason": "Missing checksum or data",
                        "has_data": checkpoint.data is not None,
                        "has_checksum": bool(checkpoint.checksum)
                    },
                    recovery_possible=False
                )
            
            # Calculate checksum of current data
            calculated_checksum = self.checksum_validator.calculate_checksum(checkpoint.data.to_dict())
            
            if calculated_checksum != checkpoint.checksum:
                return CorruptionReport(
                    checkpoint_id=checkpoint.id,
                    corruption_type=CorruptionType.CHECKSUM_MISMATCH,
                    severity=CorruptionSeverity.HIGH,
                    details={
                        "expected_checksum": checkpoint.checksum,
                        "calculated_checksum": calculated_checksum,
                        "mismatch": True
                    },
                    recovery_possible=False
                )
            
            return None
            
        except Exception as e:
            return CorruptionReport(
                checkpoint_id=checkpoint.id,
                corruption_type=CorruptionType.CHECKSUM_MISMATCH,
                severity=CorruptionSeverity.MEDIUM,
                details={"error": str(e)},
                recovery_possible=False,
                original_error=str(e)
            )
    
    def _validate_schema_version(self, checkpoint: Checkpoint) -> Optional[CorruptionReport]:
        """Validate schema version compatibility."""
        try:
            current_version = checkpoint.schema_version
            
            # Check if version is valid format
            if not self._is_valid_version_format(current_version):
                return CorruptionReport(
                    checkpoint_id=checkpoint.id,
                    corruption_type=CorruptionType.SCHEMA_VERSION_MISMATCH,
                    severity=CorruptionSeverity.MEDIUM,
                    details={
                        "reason": "Invalid version format",
                        "version": current_version
                    },
                    recovery_possible=False
                )
            
            # Check if version is supported
            if not self._is_version_supported(current_version):
                return CorruptionReport(
                    checkpoint_id=checkpoint.id,
                    corruption_type=CorruptionType.SCHEMA_VERSION_MISMATCH,
                    severity=CorruptionSeverity.MEDIUM,
                    details={
                        "reason": "Unsupported schema version",
                        "version": current_version,
                        "supported_versions": ["1.0.0", "1.1.0", "1.2.0"]
                    },
                    recovery_possible=True,
                    recovery_actions=["migrate_to_supported_version"]
                )
            
            return None
            
        except Exception as e:
            return CorruptionReport(
                checkpoint_id=checkpoint.id,
                corruption_type=CorruptionType.SCHEMA_VERSION_MISMATCH,
                severity=CorruptionSeverity.LOW,
                details={"error": str(e)},
                recovery_possible=False,
                original_error=str(e)
            )
    
    def _validate_data_structure(self, checkpoint: Checkpoint) -> Optional[CorruptionReport]:
        """Validate checkpoint data structure."""
        try:
            # Convert to dictionary for validation
            checkpoint_dict = checkpoint.to_dict()
            
            # Check required fields
            missing_fields = []
            for field in self.required_fields:
                if field not in checkpoint_dict:
                    missing_fields.append(field)
            
            if missing_fields:
                return CorruptionReport(
                    checkpoint_id=checkpoint.id,
                    corruption_type=CorruptionType.MISSING_FIELDS,
                    severity=CorruptionSeverity.HIGH,
                    details={
                        "reason": "Missing required fields",
                        "missing_fields": missing_fields
                    },
                    recovery_possible=False
                )
            
            # Validate nested structures
            if checkpoint.metadata:
                metadata_dict = checkpoint.metadata.to_dict()
                required_metadata_fields = ["job_id", "job_name", "job_type", "created_by", "environment", "version"]
                missing_metadata_fields = [f"metadata.{field}" for field in required_metadata_fields if field not in metadata_dict]
                
                if missing_metadata_fields:
                    return CorruptionReport(
                        checkpoint_id=checkpoint.id,
                        corruption_type=CorruptionType.MISSING_FIELDS,
                        severity=CorruptionSeverity.MEDIUM,
                        details={
                            "reason": "Missing required metadata fields",
                            "missing_fields": missing_metadata_fields
                        },
                        recovery_possible=False
                    )
            
            if checkpoint.data:
                data_dict = checkpoint.data.to_dict()
                required_data_sections = ["progress", "state", "configuration", "metrics", "artifacts"]
                missing_data_sections = [f"data.{section}" for section in required_data_sections if section not in data_dict]
                
                if missing_data_sections:
                    return CorruptionReport(
                        checkpoint_id=checkpoint.id,
                        corruption_type=CorruptionType.MISSING_FIELDS,
                        severity=CorruptionSeverity.LOW,
                        details={
                            "reason": "Missing required data sections",
                            "missing_fields": missing_data_sections
                        },
                        recovery_possible=False
                    )
            
            return None
            
        except Exception as e:
            return CorruptionReport(
                checkpoint_id=checkpoint.id,
                corruption_type=CorruptionType.MISSING_FIELDS,
                severity=CorruptionSeverity.MEDIUM,
                details={"error": str(e)},
                recovery_possible=False,
                original_error=str(e)
            )
    
    def _validate_field_types(self, checkpoint: Checkpoint) -> Optional[CorruptionReport]:
        """Validate field types in checkpoint."""
        try:
            checkpoint_dict = checkpoint.to_dict()
            invalid_fields = []
            
            for field_name, expected_type in self.field_types.items():
                if field_name in checkpoint_dict:
                    value = checkpoint_dict[field_name]
                    
                    # Handle union types
                    if isinstance(expected_type, tuple):
                        if not isinstance(value, expected_type):
                            invalid_fields.append({
                                "field": field_name,
                                "expected_type": [t.__name__ for t in expected_type],
                                "actual_type": type(value).__name__
                            })
                    else:
                        if not isinstance(value, expected_type):
                            invalid_fields.append({
                                "field": field_name,
                                "expected_type": expected_type.__name__,
                                "actual_type": type(value).__name__
                            })
            
            if invalid_fields:
                return CorruptionReport(
                    checkpoint_id=checkpoint.id,
                    corruption_type=CorruptionType.INVALID_DATA_TYPES,
                    severity=CorruptionSeverity.MEDIUM,
                    details={
                        "reason": "Invalid field types",
                        "invalid_fields": invalid_fields
                    },
                    recovery_possible=False
                )
            
            return None
            
        except Exception as e:
            return CorruptionReport(
                checkpoint_id=checkpoint.id,
                corruption_type=CorruptionType.INVALID_DATA_TYPES,
                severity=CorruptionSeverity.LOW,
                details={"error": str(e)},
                recovery_possible=False,
                original_error=str(e)
            )
    
    def _validate_size_consistency(
        self,
        checkpoint: Checkpoint,
        file_data: bytes
    ) -> Optional[CorruptionReport]:
        """Validate size consistency between checkpoint and file data."""
        try:
            # Calculate expected sizes
            if checkpoint.data:
                json_data = json.dumps(checkpoint.data.to_dict(), default=str, separators=(',', ':')).encode('utf-8')
                expected_size = len(json_data)
                
                # Apply compression
                if checkpoint.compression.value == "gzip":
                    expected_compressed_size = len(gzip.compress(json_data))
                else:
                    expected_compressed_size = expected_size
                
                # Apply encryption
                if checkpoint.encryption_enabled:
                    # Encryption adds overhead, so we can't validate exact size
                    expected_encrypted_size = len(file_data)
                else:
                    expected_encrypted_size = expected_compressed_size
                
                # Validate sizes
                if checkpoint.size_bytes != expected_size:
                    return CorruptionReport(
                        checkpoint_id=checkpoint.id,
                        corruption_type=CorruptionType.SIZE_MISMATCH,
                        severity=CorruptionSeverity.LOW,
                        details={
                            "reason": "Size mismatch in checkpoint data",
                            "expected_size": expected_size,
                            "actual_size": checkpoint.size_bytes
                        },
                        recovery_possible=False
                    )
                
                if checkpoint.compressed_size_bytes != expected_compressed_size:
                    return CorruptionReport(
                        checkpoint_id=checkpoint.id,
                        corruption_type=CorruptionType.SIZE_MISMATCH,
                        severity=CorruptionSeverity.LOW,
                        details={
                            "reason": "Size mismatch in compressed data",
                            "expected_compressed_size": expected_compressed_size,
                            "actual_compressed_size": checkpoint.compressed_size_bytes
                        },
                        recovery_possible=False
                    )
                
                if not checkpoint.encryption_enabled and checkpoint.encrypted_size_bytes != expected_encrypted_size:
                    return CorruptionReport(
                        checkpoint_id=checkpoint.id,
                        corruption_type=CorruptionType.SIZE_MISMATCH,
                        severity=CorruptionSeverity.LOW,
                        details={
                            "reason": "Size mismatch in file data",
                            "expected_encrypted_size": expected_encrypted_size,
                            "actual_encrypted_size": checkpoint.encrypted_size_bytes
                        },
                        recovery_possible=False
                    )
            
            return None
            
        except Exception as e:
            return CorruptionReport(
                checkpoint_id=checkpoint.id,
                corruption_type=CorruptionType.SIZE_MISMATCH,
                severity=CorruptionSeverity.LOW,
                details={"error": str(e)},
                recovery_possible=False,
                original_error=str(e)
            )
    
    def _is_valid_version_format(self, version: str) -> bool:
        """Check if version string is valid format."""
        try:
            # Simple semantic version validation
            parts = version.split('.')
            return len(parts) >= 2 and all(part.isdigit() for part in parts)
        except Exception:
            return False
    
    def _is_version_supported(self, version: str) -> bool:
        """Check if version is supported."""
        supported_versions = ["1.0.0", "1.1.0", "1.2.0"]
        return version in supported_versions
    
    def analyze_corruption_patterns(
        self,
        corruption_reports: List[CorruptionReport]
    ) -> Dict[str, Any]:
        """
        Analyze corruption patterns across multiple reports.
        
        Args:
            corruption_reports: List of corruption reports
            
        Returns:
            Analysis results
        """
        if not corruption_reports:
            return {"total_reports": 0}
        
        # Count by corruption type
        type_counts = {}
        severity_counts = {}
        
        for report in corruption_reports:
            corruption_type = report.corruption_type.value
            severity = report.severity.value
            
            type_counts[corruption_type] = type_counts.get(corruption_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Find most common issues
        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else ("none", 0)
        most_common_severity = max(severity_counts.items(), key=lambda x: x[1])[0] if severity_counts else ("none", 0))
        
        # Calculate recovery statistics
        recoverable_count = sum(1 for report in corruption_reports if report.recovery_possible)
        
        return {
            "total_reports": len(corruption_reports),
            "type_distribution": type_counts,
            "severity_distribution": severity_counts,
            "most_common_type": most_common_type,
            "most_common_severity": most_common_severity,
            "recoverable_count": recoverable_count,
            "recoverable_percentage": (recoverable_count / len(corruption_reports)) * 100 if corruption_reports else 0
        }
    
    def suggest_recovery_actions(
        self,
        corruption_report: CorruptionReport
    ) -> List[str]:
        """
        Suggest recovery actions for corruption.
        
        Args:
            corruption_report: Corruption report
            
        Returns:
            List of suggested recovery actions
        """
        actions = []
        
        if corruption_report.corruption_type == CorruptionType.CHECKSUM_MISMATCH:
            actions.extend([
                "Restore from backup checkpoint",
                "Regenerate checkpoint from application state",
                "Check for storage system corruption"
            ])
        
        elif corruption_report.corruption_type == CorruptionType.SCHEMA_VERSION_MISMATCH:
            actions.extend([
                "Migrate checkpoint to supported schema version",
                "Update application to support new schema version",
                "Use compatibility layer for version translation"
            ])
        
        elif corruption_report.corruption_type == CorruptionType.INVALID_JSON:
            actions.extend([
                "Attempt manual JSON repair",
                "Restore from backup",
                "Regenerate checkpoint from application state"
            ])
        
        elif corruption_report.corruption_type == CorruptionType.INVALID_COMPRESSION:
            actions.extend([
                "Attempt decompression with different algorithm",
                "Check for file system corruption",
                "Restore from uncompressed backup"
            ])
        
        elif corruption_report.corruption_type == CorruptionType.INVALID_ENCRYPTION:
            actions.extend([
                "Check encryption key configuration",
                "Attempt decryption with correct key",
                "Restore from unencrypted backup"
            ])
        
        elif corruption_report.corruption_type == CorruptionType.MISSING_FIELDS:
            actions.extend([
                "Attempt data reconstruction",
                "Restore from backup",
                "Regenerate checkpoint from application state"
            ])
        
        elif corruption_report.corruption_type == CorruptionType.INVALID_DATA_TYPES:
            actions.extend([
                "Attempt data type conversion",
                "Restore from backup",
                "Regenerate checkpoint from application state"
            ])
        
        elif corruption_report.corruption_type == CorruptionType.SIZE_MISMATCH:
            actions.extend([
                "Check for file truncation",
                "Verify storage system integrity",
                "Restore from backup"
            ])
        
        # Add general recovery actions
        actions.extend([
            "Check storage system health",
            "Verify backup availability",
            "Contact system administrator if issue persists"
        ])
        
        return actions


# Global corruption detector instance
_checkpoint_corruption_detector = CheckpointCorruptionDetector()


def detect_checkpoint_corruption(
    checkpoint: Checkpoint,
    file_data: Optional[bytes] = None
) -> Optional[CorruptionReport]:
    """Detect corruption in checkpoint using the global detector."""
    return _checkpoint_corruption_detector.detect_corruption(checkpoint, file_data)


def analyze_corruption_patterns(
    corruption_reports: List[CorruptionReport]
) -> Dict[str, Any]:
    """Analyze corruption patterns using the global detector."""
    return _checkpoint_corruption_detector.analyze_corruption_patterns(corruption_reports)


def suggest_recovery_actions(
    corruption_report: CorruptionReport
) -> List[str]:
    """Suggest recovery actions using the global detector."""
    return _checkpoint_corruption_detector.suggest_recovery_actions(corruption_report)
