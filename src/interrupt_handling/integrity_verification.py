"""
Data integrity verification for interrupt handling.
"""

import hashlib
import json
import time
import logging
import threading
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from .checkpoint import CheckpointManager
from .state_serialization import StateSerializationManager


class VerificationMethod(Enum):
    """Methods for data integrity verification."""
    HASH = "hash"
    CHECKSUM = "checksum"
    SIZE = "size"
    TIMESTAMP = "timestamp"
    CUSTOM = "custom"


class VerificationResult(Enum):
    """Results of integrity verification."""
    VALID = "valid"
    INVALID = "invalid"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    ERROR = "error"


@dataclass
class IntegrityCheck:
    """Result of an integrity check."""
    check_id: str
    method: VerificationMethod
    result: VerificationResult
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_valid(self) -> bool:
        """Check if the integrity check passed."""
        return self.result == VerificationResult.VALID
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'check_id': self.check_id,
            'method': self.method.value,
            'result': self.result.value,
            'expected_value': self.expected_value,
            'actual_value': self.actual_value,
            'error_message': self.error_message,
            'timestamp': self.timestamp
        }


class IntegrityVerifier:
    """Verifies data integrity using various methods."""
    
    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None,
                 state_manager: Optional[StateSerializationManager] = None):
        self.logger = logging.getLogger(__name__)
        self.checkpoint_manager = checkpoint_manager
        self.state_manager = state_manager
        
        # Verification history
        self._verification_history: Dict[str, List[IntegrityCheck]] = {}
        self._lock = threading.RLock()
        
        # Custom verifiers
        self._custom_verifiers: Dict[str, Callable[[Any], IntegrityCheck]] = {}
    
    def register_custom_verifier(self, name: str, verifier: Callable[[Any], IntegrityCheck]):
        """Register a custom verification function."""
        self._custom_verifiers[name] = verifier
        self.logger.debug(f"Registered custom verifier: {name}")
    
    def calculate_file_hash(self, file_path: Union[str, Path], 
                         algorithm: str = 'sha256') -> Optional[str]:
        """
        Calculate hash of a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            
        Returns:
            Hexadecimal hash string, or None if failed
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return None
            
            hash_func = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def calculate_data_hash(self, data: Union[str, bytes], 
                        algorithm: str = 'sha256') -> str:
        """
        Calculate hash of data.
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm to use
            
        Returns:
            Hexadecimal hash string
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_func = hashlib.new(algorithm)
        hash_func.update(data)
        return hash_func.hexdigest()
    
    def verify_file_integrity(self, file_path: Union[str, Path], 
                           expected_hash: Optional[str] = None,
                           expected_size: Optional[int] = None,
                           algorithm: str = 'sha256') -> IntegrityCheck:
        """
        Verify integrity of a file.
        
        Args:
            file_path: Path to the file
            expected_hash: Expected hash value
            expected_size: Expected file size
            algorithm: Hash algorithm to use
            
        Returns:
            IntegrityCheck with verification result
        """
        check_id = f"file_{Path(file_path).name}_{int(time.time())}"
        
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                return IntegrityCheck(
                    check_id=check_id,
                    method=VerificationMethod.HASH,
                    result=VerificationResult.MISSING,
                    error_message=f"File not found: {file_path}"
                )
            
            # Verify size if expected
            if expected_size is not None:
                actual_size = file_path.stat().st_size
                if actual_size != expected_size:
                    return IntegrityCheck(
                        check_id=check_id,
                        method=VerificationMethod.SIZE,
                        result=VerificationResult.INVALID,
                        expected_value=str(expected_size),
                        actual_value=str(actual_size),
                        error_message=f"Size mismatch: expected {expected_size}, got {actual_size}"
                    )
            
            # Verify hash if expected
            if expected_hash is not None:
                actual_hash = self.calculate_file_hash(file_path, algorithm)
                if actual_hash is None:
                    return IntegrityCheck(
                        check_id=check_id,
                        method=VerificationMethod.HASH,
                        result=VerificationResult.ERROR,
                        error_message="Failed to calculate file hash"
                    )
                
                if actual_hash != expected_hash:
                    return IntegrityCheck(
                        check_id=check_id,
                        method=VerificationMethod.HASH,
                        result=VerificationResult.INVALID,
                        expected_value=expected_hash,
                        actual_value=actual_hash,
                        error_message=f"Hash mismatch: expected {expected_hash}, got {actual_hash}"
                    )
            
            # All checks passed
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.HASH,
                result=VerificationResult.VALID,
                expected_value=expected_hash,
                actual_value=self.calculate_file_hash(file_path, algorithm)
            )
            
        except Exception as e:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.HASH,
                result=VerificationResult.ERROR,
                error_message=f"Verification error: {e}"
            )
    
    def verify_data_integrity(self, data: Any, expected_hash: Optional[str] = None,
                           algorithm: str = 'sha256') -> IntegrityCheck:
        """
        Verify integrity of data.
        
        Args:
            data: Data to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm to use
            
        Returns:
            IntegrityCheck with verification result
        """
        check_id = f"data_{int(time.time())}"
        
        try:
            # Calculate actual hash
            if isinstance(data, (dict, list)):
                # For structured data, use JSON serialization
                json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
                actual_hash = self.calculate_data_hash(json_str, algorithm)
            else:
                actual_hash = self.calculate_data_hash(data, algorithm)
            
            # Verify if expected hash provided
            if expected_hash is not None:
                if actual_hash != expected_hash:
                    return IntegrityCheck(
                        check_id=check_id,
                        method=VerificationMethod.HASH,
                        result=VerificationResult.INVALID,
                        expected_value=expected_hash,
                        actual_value=actual_hash,
                        error_message=f"Data hash mismatch: expected {expected_hash}, got {actual_hash}"
                    )
            
            # Valid
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.HASH,
                result=VerificationResult.VALID,
                expected_value=expected_hash,
                actual_value=actual_hash
            )
            
        except Exception as e:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.HASH,
                result=VerificationResult.ERROR,
                error_message=f"Data verification error: {e}"
            )
    
    def verify_checkpoint_integrity(self, checkpoint_id: str) -> IntegrityCheck:
        """
        Verify integrity of a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to verify
            
        Returns:
            IntegrityCheck with verification result
        """
        check_id = f"checkpoint_{checkpoint_id}_{int(time.time())}"
        
        if not self.checkpoint_manager:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.CUSTOM,
                result=VerificationResult.ERROR,
                error_message="No checkpoint manager available"
            )
        
        try:
            # Use checkpoint manager's built-in verification
            is_valid = self.checkpoint_manager.verify_checkpoint_integrity(checkpoint_id)
            
            if is_valid:
                return IntegrityCheck(
                    check_id=check_id,
                    method=VerificationMethod.CUSTOM,
                    result=VerificationResult.VALID,
                    expected_value="valid",
                    actual_value="valid"
                )
            else:
                return IntegrityCheck(
                    check_id=check_id,
                    method=VerificationMethod.CUSTOM,
                    result=VerificationResult.INVALID,
                    expected_value="valid",
                    actual_value="invalid",
                    error_message="Checkpoint integrity verification failed"
                )
                
        except Exception as e:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.CUSTOM,
                result=VerificationResult.ERROR,
                error_message=f"Checkpoint verification error: {e}"
            )
    
    def verify_state_snapshot_integrity(self, snapshot_id: str) -> IntegrityCheck:
        """
        Verify integrity of a state snapshot.
        
        Args:
            snapshot_id: ID of state snapshot to verify
            
        Returns:
            IntegrityCheck with verification result
        """
        check_id = f"snapshot_{snapshot_id}_{int(time.time())}"
        
        if not self.state_manager:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.CUSTOM,
                result=VerificationResult.ERROR,
                error_message="No state manager available"
            )
        
        try:
            # Get snapshot info
            snapshot_info = self.state_manager.get_snapshot_info(snapshot_id)
            
            if not snapshot_info:
                return IntegrityCheck(
                    check_id=check_id,
                    method=VerificationMethod.CUSTOM,
                    result=VerificationResult.MISSING,
                    error_message=f"State snapshot {snapshot_id} not found"
                )
            
            # Verify timestamp is reasonable (not too old or in future)
            current_time = time.time()
            snapshot_time = snapshot_info['timestamp']
            
            if snapshot_time > current_time:
                return IntegrityCheck(
                    check_id=check_id,
                    method=VerificationMethod.TIMESTAMP,
                    result=VerificationResult.INVALID,
                    expected_value=str(current_time),
                    actual_value=str(snapshot_time),
                    error_message="Snapshot timestamp is in the future"
                )
            
            # Check age (optional - very old snapshots might be suspicious)
            age_hours = (current_time - snapshot_time) / 3600
            if age_hours > 168:  # 7 days
                self.logger.warning(f"State snapshot {snapshot_id} is very old: {age_hours:.1f} hours")
            
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.CUSTOM,
                result=VerificationResult.VALID,
                expected_value="valid",
                actual_value="valid"
            )
            
        except Exception as e:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.CUSTOM,
                result=VerificationResult.ERROR,
                error_message=f"State snapshot verification error: {e}"
            )
    
    def run_custom_verification(self, verifier_name: str, data: Any) -> IntegrityCheck:
        """
        Run a custom verification function.
        
        Args:
            verifier_name: Name of the custom verifier
            data: Data to verify
            
        Returns:
            IntegrityCheck with verification result
        """
        check_id = f"custom_{verifier_name}_{int(time.time())}"
        
        if verifier_name not in self._custom_verifiers:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.CUSTOM,
                result=VerificationResult.ERROR,
                error_message=f"Custom verifier '{verifier_name}' not found"
            )
        
        try:
            verifier = self._custom_verifiers[verifier_name]
            return verifier(data)
            
        except Exception as e:
            return IntegrityCheck(
                check_id=check_id,
                method=VerificationMethod.CUSTOM,
                result=VerificationResult.ERROR,
                error_message=f"Custom verification error: {e}"
            )
    
    def verify_multiple_files(self, file_specs: List[Dict[str, Any]]) -> List[IntegrityCheck]:
        """
        Verify integrity of multiple files.
        
        Args:
            file_specs: List of file specifications with keys:
                      - path: file path
                      - expected_hash: optional expected hash
                      - expected_size: optional expected size
                      - algorithm: optional hash algorithm (default: sha256)
                      
        Returns:
            List of IntegrityCheck results
        """
        results = []
        
        for spec in file_specs:
            file_path = spec.get('path')
            expected_hash = spec.get('expected_hash')
            expected_size = spec.get('expected_size')
            algorithm = spec.get('algorithm', 'sha256')
            
            if file_path:
                check = self.verify_file_integrity(file_path, expected_hash, expected_size, algorithm)
                results.append(check)
        
        return results
    
    def record_verification(self, check: IntegrityCheck):
        """Record a verification result in history."""
        with self._lock:
            if check.check_id not in self._verification_history:
                self._verification_history[check.check_id] = []
            
            self._verification_history[check.check_id].append(check)
        
        # Log result
        if check.is_valid:
            self.logger.debug(f"Verification passed: {check.check_id}")
        else:
            self.logger.warning(f"Verification failed: {check.check_id} - {check.error_message}")
    
    def get_verification_history(self, check_id: Optional[str] = None) -> Union[List[IntegrityCheck], Dict[str, List[IntegrityCheck]]]:
        """Get verification history."""
        with self._lock:
            if check_id:
                return self._verification_history.get(check_id, [])
            else:
                return self._verification_history.copy()
    
    def cleanup_verification_history(self, max_age_hours: float = 24.0) -> int:
        """Clean up old verification history."""
        with self._lock:
            current_time = time.time()
            to_remove = []
            
            for check_id, checks in self._verification_history.items():
                # Keep only recent checks
                recent_checks = [
                    check for check in checks
                    if (current_time - check.timestamp) < (max_age_hours * 3600)
                ]
                
                if recent_checks:
                    self._verification_history[check_id] = recent_checks
                else:
                    to_remove.append(check_id)
            
            # Remove empty entries
            for check_id in to_remove:
                del self._verification_history[check_id]
        
        if to_remove:
            self.logger.info(f"Cleaned up verification history for {len(to_remove)} checks")
        
        return len(to_remove)
    
    def create_integrity_report(self, checks: List[IntegrityCheck]) -> Dict[str, Any]:
        """Create a comprehensive integrity report."""
        if not checks:
            return {'error': 'No checks provided'}
        
        # Count results
        result_counts = {result.value: 0 for result in VerificationResult}
        method_counts = {method.value: 0 for method in VerificationMethod}
        
        for check in checks:
            result_counts[check.result.value] += 1
            method_counts[check.method.value] += 1
        
        # Calculate success rate
        total_checks = len(checks)
        valid_checks = result_counts[VerificationResult.VALID.value]
        success_rate = (valid_checks / total_checks) * 100 if total_checks > 0 else 0
        
        return {
            'summary': {
                'total_checks': total_checks,
                'valid_checks': valid_checks,
                'success_rate_percent': success_rate,
                'timestamp': time.time()
            },
            'results_by_type': result_counts,
            'methods_by_type': method_counts,
            'failed_checks': [
                check.to_dict() for check in checks 
                if not check.is_valid
            ],
            'all_checks': [
                check.to_dict() for check in checks
            ]
        }
    
    def get_verification_status(self) -> Dict[str, Any]:
        """Get current verification status."""
        with self._lock:
            total_checks = sum(len(checks) for checks in self._verification_history.values())
            custom_verifiers = list(self._custom_verifiers.keys())
        
        return {
            'total_checks_recorded': total_checks,
            'custom_verifiers_count': len(custom_verifiers),
            'custom_verifiers': custom_verifiers,
            'has_checkpoint_manager': self.checkpoint_manager is not None,
            'has_state_manager': self.state_manager is not None
        }


# Global integrity verifier instance
_integrity_verifier = None


def get_integrity_verifier(checkpoint_manager: Optional[CheckpointManager] = None,
                        state_manager: Optional[StateSerializationManager] = None) -> IntegrityVerifier:
    """Get the global integrity verifier instance."""
    global _integrity_verifier
    if _integrity_verifier is None:
        _integrity_verifier = IntegrityVerifier(checkpoint_manager, state_manager)
    return _integrity_verifier
