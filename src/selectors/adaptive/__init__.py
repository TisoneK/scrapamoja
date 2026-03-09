"""
Adaptive module for selector API integration.

This module provides the AdaptiveAPIClient for calling the adaptive REST API
to get alternative selector suggestions when primary selectors fail.
"""

from src.selectors.adaptive.api_client import AdaptiveAPIClient
from src.selectors.adaptive.sync_adapter import SyncAdaptiveAPIClient
from src.selectors.adaptive.services.confidence_query_service import (
    ConfidenceQueryService,
    ConfidenceScoreResult,
    BatchConfidenceResult,
    PaginatedConfidenceResult,
    ConfidenceQueryConfig,
    get_confidence_query_service,
)
from src.selectors.adaptive.services.health_status_service import (
    HealthStatusService,
    HealthStatus,
    HealthStatusConfig,
    SelectorHealthInfo,
    HealthDashboardData,
    get_health_status_service,
)

__all__ = [
    "AdaptiveAPIClient",
    "SyncAdaptiveAPIClient",
    "ConfidenceQueryService",
    "ConfidenceScoreResult",
    "BatchConfidenceResult",
    "PaginatedConfidenceResult",
    "ConfidenceQueryConfig",
    "get_confidence_query_service",
    "HealthStatusService",
    "HealthStatus",
    "HealthStatusConfig",
    "SelectorHealthInfo",
    "HealthDashboardData",
    "get_health_status_service",
]
