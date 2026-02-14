"""
Snapshot system exceptions with comprehensive error handling.

This module defines all exception classes used throughout the snapshot system
with robust error handling to prevent cascading failures.
"""

from typing import Optional, List, Tuple, Any
from dataclasses import dataclass


class SnapshotError(Exception):
    """Base exception for snapshot system."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error
        self.message = message


class SnapshotCaptureError(SnapshotError):
    """Failed to capture snapshot artifacts."""
    pass


class SnapshotStorageError(SnapshotError):
    """Failed to store snapshot to disk."""
    pass


class SnapshotValidationError(SnapshotError):
    """Failed to validate snapshot data."""
    pass


class SnapshotCompleteFailure(SnapshotError):
    """No artifacts could be captured at all."""
    pass


class SnapshotCircuitOpen(SnapshotError):
    """Circuit breaker is open - snapshots temporarily disabled."""
    pass


class DiskFullError(SnapshotStorageError):
    """Disk is full - cannot store snapshots."""
    pass


class PermissionError(SnapshotStorageError):
    """Permission denied - cannot write to snapshot directory."""
    pass




class ArtifactCaptureError(SnapshotCaptureError):
    """Raised when artifact capture fails."""
    pass


class ConfigurationError(SnapshotError):
    """Raised when configuration is invalid."""
    pass


class StorageError(SnapshotStorageError):
    """Raised when storage operations fail."""
    pass


class ValidationError(SnapshotValidationError):
    """Raised when validation fails."""
    pass


class TriggerError(SnapshotError):
    """Raised when trigger operations fail."""
    pass


class IntegrationError(SnapshotError):
    """Raised when browser integration fails."""
    pass


class MetricsError(SnapshotError):
    """Raised when metrics operations fail."""
    pass


@dataclass
class PartialSnapshotBundle:
    """Bundle with partial artifacts when some captures failed."""
    artifacts: List[Any]
    errors: List[Tuple[str, Exception]]
    context: Any
    timestamp: str
    bundle_path: Optional[str] = None
    
    @property
    def is_partial(self) -> bool:
        """Check if this is a partial snapshot."""
        return len(self.errors) > 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of artifact capture."""
        total_attempts = len(self.artifacts) + len(self.errors)
        if total_attempts == 0:
            return 0.0
        return len(self.artifacts) / total_attempts


@dataclass
class SnapshotFailureMetrics:
    """Track snapshot failure patterns."""
    total_failures: int = 0
    disk_full_failures: int = 0
    permission_failures: int = 0
    capture_failures: int = 0
    storage_failures: int = 0
    validation_failures: int = 0
    circuit_breaker_trips: int = 0
    
    def record_failure(self, error_type: str):
        """Record a failure by type."""
        self.total_failures += 1
        
        if error_type == "disk_full":
            self.disk_full_failures += 1
        elif error_type == "permission":
            self.permission_failures += 1
        elif error_type == "capture":
            self.capture_failures += 1
        elif error_type == "storage":
            self.storage_failures += 1
        elif error_type == "validation":
            self.validation_failures += 1
        elif error_type == "circuit_breaker":
            self.circuit_breaker_trips += 1
    
    def get_failure_rate(self, total_snapshots: int) -> float:
        """Calculate failure rate percentage."""
        if total_snapshots == 0:
            return 0.0
        return (self.total_failures / total_snapshots) * 100
