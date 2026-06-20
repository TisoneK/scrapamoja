"""
Telemetry Configuration Components

Configuration management for telemetry system including
settings, thresholds, and validation rules.
"""

from .telemetry_config import TelemetryConfiguration
from .alert_thresholds import AlertThresholdsConfiguration as AlertThresholds

__all__ = [
    "TelemetryConfiguration",
    "AlertThresholds",
]
