"""
Telemetry selector models - re-exports for backward compatibility.

This module provides backward-compatible imports for models previously
located in selector_models.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class TelemetryEventType(str, Enum):
    """Types of telemetry events."""
    SELECTOR_RESOLVED = "selector_resolved"
    SELECTOR_FAILED = "selector_failed"
    SELECTOR_CACHED = "selector_cached"
    SELECTOR_EVOLVED = "selector_evolved"
    NAVIGATION_COMPLETED = "navigation_completed"
    EXTRACTION_COMPLETED = "extraction_completed"
    ERROR_OCCURRED = "error_occurred"
    PERFORMANCE_ALERT = "performance_alert"
    QUALITY_ALERT = "quality_alert"
    HEALTH_CHECK = "health_check"
    USAGE_TRACKED = "usage_tracked"


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"


class SeverityLevel(str, Enum):
    """Severity levels for telemetry events and alerts."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Re-export TelemetryEvent from the actual module
from .telemetry_event import TelemetryEvent

__all__ = [
    "TelemetryEvent",
    "TelemetryEventType", 
    "MetricType",
    "SeverityLevel",
]
