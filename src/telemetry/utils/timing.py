"""
Timing Measurement Utilities

Utilities for measuring and tracking timing performance for
telemetry data collection and analysis.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
import threading

from ..exceptions import TelemetryCollectionError


@dataclass
class TimingMeasurement:
    """
    Represents a timing measurement with metadata.
    """
    
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    operation_type: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def finish(self, end_time: Optional[datetime] = None) -> None:
        """
        Finish the timing measurement.
        
        Args:
            end_time: Optional end time (defaults to current time)
        """
        self.end_time = end_time or datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def is_finished(self) -> bool:
        """Check if timing measurement is finished."""
        return self.end_time is not None
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        return self.duration_ms / 1000 if self.duration_ms is not None else None
    
    def get_duration_ms(self) -> Optional[float]:
        """Get duration in milliseconds."""
        return self.duration_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "operation_type": self.operation_type,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata or {}
        }


class TimingCollector:
    """
    Collects and manages timing measurements.
    
    Provides thread-safe timing collection with various
    measurement strategies and aggregation capabilities.
    """
    
    def __init__(self):
        """Initialize timing collector."""
        self._measurements: Dict[str, TimingMeasurement] = {}
        self._completed_measurements: list[TimingMeasurement] = []
        self._lock = threading.Lock()
    
    def start_timing(
        self,
        measurement_id: str,
        operation_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TimingMeasurement:
        """
        Start a timing measurement.
        
        Args:
            measurement_id: Unique measurement identifier
            operation_type: Type of operation being measured
            correlation_id: Optional correlation ID
            metadata: Optional metadata
            
        Returns:
            TimingMeasurement instance
        """
        with self._lock:
            if measurement_id in self._measurements:
                raise TelemetryCollectionError(
                    f"Measurement {measurement_id} already exists",
                    error_code="TEL-301"
                )
            
            measurement = TimingMeasurement(
                start_time=datetime.utcnow(),
                operation_type=operation_type,
                correlation_id=correlation_id,
                metadata=metadata
            )
            
            self._measurements[measurement_id] = measurement
            return measurement
    
    def finish_timing(
        self,
        measurement_id: str,
        end_time: Optional[datetime] = None
    ) -> TimingMeasurement:
        """
        Finish a timing measurement.
        
        Args:
            measurement_id: Measurement identifier
            end_time: Optional end time
            
        Returns:
            Completed TimingMeasurement
        """
        with self._lock:
            if measurement_id not in self._measurements:
                raise TelemetryCollectionError(
                    f"Measurement {measurement_id} not found",
                    error_code="TEL-302"
                )
            
            measurement = self._measurements.pop(measurement_id)
            measurement.finish(end_time)
            self._completed_measurements.append(measurement)
            
            return measurement
    
    def get_timing(self, measurement_id: str) -> Optional[TimingMeasurement]:
        """
        Get a timing measurement.
        
        Args:
            measurement_id: Measurement identifier
            
        Returns:
            TimingMeasurement or None if not found
        """
        with self._lock:
            # Check active measurements first
            if measurement_id in self._measurements:
                return self._measurements[measurement_id]
            
            # Check completed measurements
            for measurement in self._completed_measurements:
                if measurement_id == getattr(measurement, 'measurement_id', None):
                    return measurement
            
            return None
    
    def get_active_measurements(self) -> Dict[str, TimingMeasurement]:
        """
        Get all active timing measurements.
        
        Returns:
            Dictionary of active measurements
        """
        with self._lock:
            return self._measurements.copy()
    
    def get_completed_measurements(
        self,
        limit: Optional[int] = None,
        operation_type: Optional[str] = None
    ) -> list[TimingMeasurement]:
        """
        Get completed timing measurements.
        
        Args:
            limit: Optional limit on number of measurements
            operation_type: Optional operation type filter
            
        Returns:
            List of completed measurements
        """
        with self._lock:
            measurements = self._completed_measurements.copy()
            
            if operation_type:
                measurements = [
                    m for m in measurements
                    if m.operation_type == operation_type
                ]
            
            if limit:
                measurements = measurements[-limit:]
            
            return measurements
    
    def calculate_statistics(
        self,
        operation_type: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Calculate timing statistics.
        
        Args:
            operation_type: Optional operation type filter
            time_window: Optional time window for calculations
            
        Returns:
            Timing statistics
        """
        with self._lock:
            measurements = self._completed_measurements.copy()
            
            # Apply filters
            if operation_type:
                measurements = [
                    m for m in measurements
                    if m.operation_type == operation_type
                ]
            
            if time_window:
                cutoff_time = datetime.utcnow() - time_window
                measurements = [
                    m for m in measurements
                    if m.end_time and m.end_time >= cutoff_time
                ]
            
            if not measurements:
                return {
                    "count": 0,
                    "avg_ms": 0,
                    "min_ms": 0,
                    "max_ms": 0,
                    "total_ms": 0
                }
            
            durations = [m.duration_ms for m in measurements if m.duration_ms is not None]
            
            return {
                "count": len(durations),
                "avg_ms": sum(durations) / len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
                "total_ms": sum(durations),
                "operation_type": operation_type,
                "time_window_hours": time_window.total_seconds() / 3600 if time_window else None
            }
    
    def cleanup_old_measurements(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed measurements.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of measurements cleaned up
        """
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            original_count = len(self._completed_measurements)
            
            self._completed_measurements = [
                m for m in self._completed_measurements
                if not m.end_time or m.end_time >= cutoff_time
            ]
            
            return original_count - len(self._completed_measurements)
    
    def clear_all_measurements(self) -> None:
        """Clear all measurements."""
        with self._lock:
            self._measurements.clear()
            self._completed_measurements.clear()


# Global timing collector instance
_default_collector = TimingCollector()


@contextmanager
def measure_timing(
    measurement_id: Optional[str] = None,
    operation_type: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    collector: Optional[TimingCollector] = None
):
    """
    Context manager for measuring timing.
    
    Args:
        measurement_id: Optional measurement ID
        operation_type: Type of operation
        correlation_id: Optional correlation ID
        metadata: Optional metadata
        collector: Optional timing collector
        
    Yields:
        TimingMeasurement instance
    """
    if collector is None:
        collector = _default_collector
    
    if measurement_id is None:
        measurement_id = f"timing_{int(time.time() * 1000)}"
    
    measurement = collector.start_timing(
        measurement_id=measurement_id,
        operation_type=operation_type,
        correlation_id=correlation_id,
        metadata=metadata
    )
    
    try:
        yield measurement
    finally:
        collector.finish_timing(measurement_id)


@asynccontextmanager
async def measure_timing_async(
    measurement_id: Optional[str] = None,
    operation_type: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    collector: Optional[TimingCollector] = None
):
    """
    Async context manager for measuring timing.
    
    Args:
        measurement_id: Optional measurement ID
        operation_type: Type of operation
        correlation_id: Optional correlation ID
        metadata: Optional metadata
        collector: Optional timing collector
        
    Yields:
        TimingMeasurement instance
    """
    if collector is None:
        collector = _default_collector
    
    if measurement_id is None:
        measurement_id = f"timing_{int(time.time() * 1000)}"
    
    measurement = collector.start_timing(
        measurement_id=measurement_id,
        operation_type=operation_type,
        correlation_id=correlation_id,
        metadata=metadata
    )
    
    try:
        yield measurement
    finally:
        collector.finish_timing(measurement_id)


def measure_function_timing(
    func: Callable,
    measurement_id: Optional[str] = None,
    operation_type: Optional[str] = None,
    collector: Optional[TimingCollector] = None
):
    """
    Decorator for measuring function timing.
    
    Args:
        func: Function to measure
        measurement_id: Optional measurement ID
        operation_type: Optional operation type
        collector: Optional timing collector
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        nonlocal measurement_id
        if measurement_id is None:
            measurement_id = f"{func.__name__}_{int(time.time() * 1000)}"
        
        with measure_timing(
            measurement_id=measurement_id,
            operation_type=operation_type or func.__name__,
            collector=collector
        ):
            return func(*args, **kwargs)
    
    return wrapper


def measure_async_function_timing(
    func: Callable,
    measurement_id: Optional[str] = None,
    operation_type: Optional[str] = None,
    collector: Optional[TimingCollector] = None
):
    """
    Decorator for measuring async function timing.
    
    Args:
        func: Async function to measure
        measurement_id: Optional measurement ID
        operation_type: Optional operation type
        collector: Optional timing collector
        
    Returns:
        Decorated async function
    """
    async def wrapper(*args, **kwargs):
        nonlocal measurement_id
        if measurement_id is None:
            measurement_id = f"{func.__name__}_{int(time.time() * 1000)}"
        
        async with measure_timing_async(
            measurement_id=measurement_id,
            operation_type=operation_type or func.__name__,
            collector=collector
        ):
            return await func(*args, **kwargs)
    
    return wrapper


def get_timing_statistics(
    operation_type: Optional[str] = None,
    time_window: Optional[timedelta] = None
) -> Dict[str, Any]:
    """
    Get timing statistics using default collector.
    
    Args:
        operation_type: Optional operation type filter
        time_window: Optional time window
        
    Returns:
        Timing statistics
    """
    return _default_collector.calculate_statistics(operation_type, time_window)


def start_timing(
    measurement_id: str,
    operation_type: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TimingMeasurement:
    """
    Start timing measurement using default collector.
    
    Args:
        measurement_id: Unique measurement identifier
        operation_type: Type of operation
        correlation_id: Optional correlation ID
        metadata: Optional metadata
        
    Returns:
        TimingMeasurement instance
    """
    return _default_collector.start_timing(
        measurement_id, operation_type, correlation_id, metadata
    )


def finish_timing(measurement_id: str) -> TimingMeasurement:
    """
    Finish timing measurement using default collector.
    
    Args:
        measurement_id: Measurement identifier
        
    Returns:
        Completed TimingMeasurement
    """
    return _default_collector.finish_timing(measurement_id)
