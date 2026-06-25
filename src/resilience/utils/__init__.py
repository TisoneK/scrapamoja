"""
Resilience Utility Modules

Utility functions and helpers for resilience components including
serialization, integrity validation, and time calculations.
"""

from .serialization import (
    JSONSerializer,
    FileSerializer,
    serialize_json,
    deserialize_json,
    save_json_file,
    load_json_file
)

from .integrity import (
    ChecksumValidator,
    FileIntegrityManager,
    DataIntegrityWrapper,
    calculate_checksum,
    validate_checksum,
    validate_checksum_or_raise,
    calculate_file_checksum,
    validate_file_integrity,
    validate_file_integrity_or_raise
)

from .time import (
    BackoffCalculator,
    TimeWindow,
    RateLimiter,
    TimeoutManager,
    CircuitBreakerTimer,
    calculate_exponential_backoff,
    calculate_linear_backoff,
    add_jitter,
    sleep_with_jitter
)

__all__ = [
    # Serialization
    "JSONSerializer",
    "FileSerializer",
    "serialize_json",
    "deserialize_json",
    "save_json_file",
    "load_json_file",
    
    # Integrity
    "ChecksumValidator",
    "FileIntegrityManager",
    "DataIntegrityWrapper",
    "calculate_checksum",
    "validate_checksum",
    "validate_checksum_or_raise",
    "calculate_file_checksum",
    "validate_file_integrity",
    "validate_file_integrity_or_raise",
    
    # Time utilities
    "BackoffCalculator",
    "TimeWindow",
    "RateLimiter",
    "TimeoutManager",
    "CircuitBreakerTimer",
    "calculate_exponential_backoff",
    "calculate_linear_backoff",
    "add_jitter",
    "sleep_with_jitter"
]
