"""
Alert Status Enum

This module defines the AlertStatus enumeration for resource monitoring.
"""

from enum import Enum


class AlertStatus(Enum):
    """Resource alert status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
