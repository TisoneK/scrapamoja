"""
Telemetry System Interfaces

Abstract base classes and interfaces defining contracts for
telemetry system components.
"""

from .collector import ITelemetryCollector
from .storage import ITelemetryStorage
from .processor import ITelemetryProcessor
from .alert_engine import IAlertEngine, Alert, AlertSeverity, AlertType
from .report_generator import IReportGenerator, Report, ReportType, ReportFormat
from .configuration import ITelemetryConfiguration
from .integration import ISelectorTelemetryIntegration

__all__ = [
    "ITelemetryCollector",
    "ITelemetryStorage",
    "ITelemetryProcessor",
    "IAlertEngine", 
    "IReportGenerator",
    "ITelemetryConfiguration",
    "ISelectorTelemetryIntegration",
    # Alert classes
    "Alert",
    "AlertSeverity",
    "AlertType",
    # Report classes
    "Report",
    "ReportType",
    "ReportFormat",
]
