"""
Telemetry Utility Functions

Utility functions for correlation ID generation, timing measurement,
data validation, and other common operations.
"""

from .correlation import (
    generate_correlation_id,
    generate_time_based_correlation_id,
    generate_context_based_correlation_id,
    set_thread_correlation_id,
    get_thread_correlation_id,
    clear_thread_correlation_id,
    validate_correlation_id,
    CorrelationIdGenerator
)
from .timing import (
    TimingMeasurement,
    TimingCollector,
    measure_timing,
    measure_timing_async,
    measure_function_timing,
    measure_async_function_timing,
    get_timing_statistics,
    start_timing,
    finish_timing
)
from .validation import (
    TelemetryDataValidator,
    validate_telemetry_data,
    is_valid_telemetry_data
)

__all__ = [
    # Correlation utilities
    "generate_correlation_id",
    "generate_time_based_correlation_id",
    "generate_context_based_correlation_id",
    "set_thread_correlation_id",
    "get_thread_correlation_id",
    "clear_thread_correlation_id",
    "validate_correlation_id",
    "CorrelationIdGenerator",
    
    # Timing utilities
    "TimingMeasurement",
    "TimingCollector",
    "measure_timing",
    "measure_timing_async",
    "measure_function_timing",
    "measure_async_function_timing",
    "get_timing_statistics",
    "start_timing",
    "finish_timing",
    
    # Validation utilities
    "TelemetryDataValidator",
    "validate_telemetry_data",
    "is_valid_telemetry_data",
]
