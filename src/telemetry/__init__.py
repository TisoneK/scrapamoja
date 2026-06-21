"""
Selector Telemetry System

Comprehensive telemetry system for selector performance monitoring, usage pattern analysis, 
and health metrics tracking. System collects data from every selector operation, provides 
real-time alerting, generates analytical reports, and manages telemetry data lifecycle.
"""

from .models.telemetry_event import TelemetryEvent
from .models.performance_metrics import PerformanceMetrics
from .models.quality_metrics import QualityMetrics
from .models.strategy_metrics import StrategyMetrics
from .models.error_data import ErrorData
from .models.context_data import ContextData

from .interfaces.collector import ITelemetryCollector
from .interfaces.storage import ITelemetryStorage
from .interfaces.processor import ITelemetryProcessor
from .interfaces.alert_engine import IAlertEngine
from .interfaces.report_generator import IReportGenerator
from .interfaces.configuration import ITelemetryConfiguration
from .interfaces.integration import ISelectorTelemetryIntegration

from .configuration.telemetry_config import TelemetryConfiguration

__version__ = "1.0.0"
__all__ = [
    # Models
    "TelemetryEvent",
    "PerformanceMetrics", 
    "QualityMetrics",
    "StrategyMetrics",
    "ErrorData",
    "ContextData",
    
    # Interfaces
    "ITelemetryCollector",
    "ITelemetryStorage",
    "ITelemetryProcessor", 
    "IAlertEngine",
    "IReportGenerator",
    "ITelemetryConfiguration",
    "ISelectorTelemetryIntegration",
    
    # Configuration
    "TelemetryConfiguration",
]
