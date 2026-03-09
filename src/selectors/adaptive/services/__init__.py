"""
Services package for adaptive selector logic.
"""

from .stability_scoring import StabilityScoringService, FailureSeverity
from .failure_context import FailureContextService
from .dom_analyzer import DOMAnalyzer, AlternativeSelector, StrategyType
from .confidence_scorer import ConfidenceScorer, ConfidenceTier, ScoringBreakdown
from .confidence_query_service import (
    ConfidenceQueryService,
    ConfidenceScoreResult,
    BatchConfidenceResult,
    PaginatedConfidenceResult,
    ConfidenceQueryConfig,
    get_confidence_query_service,
)
from .health_status_service import (
    HealthStatusService,
    HealthStatus,
    HealthStatusConfig,
    SelectorHealthInfo,
    HealthDashboardData,
    get_health_status_service,
)
from .blast_radius import (
    BlastRadiusCalculator,
    BlastRadiusResult,
    BlastRadiusUI,
    SeverityLevel,
    AffectedSelector,
    RecipeSelector,
    get_blast_radius_calculator,
)
from .blast_radius_service import (
    BlastRadiusService,
    BlastRadiusSeverity,
    FieldType,
    DependencyType,
    AffectedFieldData,
    CascadingSelectorData,
    BlastRadiusConfig,
    BlastRadiusResult,
    get_blast_radius_service,
)
from .audit_service import AuditLogger, get_audit_logger, record_human_decision
from .view_service import ViewService, get_view_service
from .fast_triage_service import FastTriageService, get_fast_triage_service
from .feature_flag_service import FeatureFlagService, get_feature_flag_service, is_adaptive_enabled

__all__ = [
    "StabilityScoringService", 
    "FailureSeverity",
    "FailureContextService",
    "DOMAnalyzer",
    "AlternativeSelector",
    "StrategyType",
    "ConfidenceScorer",
    "ConfidenceTier",
    "ScoringBreakdown",
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
    "BlastRadiusCalculator",
    "BlastRadiusResult",
    "BlastRadiusUI",
    "SeverityLevel",
    "AffectedSelector",
    "RecipeSelector",
    "get_blast_radius_calculator",
    # Blast Radius Service (Story 6-3)
    "BlastRadiusService",
    "BlastRadiusSeverity",
    "FieldType",
    "DependencyType",
    "AffectedFieldData",
    "CascadingSelectorData",
    "BlastRadiusConfig",
    "BlastRadiusResult",
    "get_blast_radius_service",
    "AuditLogger",
    "get_audit_logger",
    "record_human_decision",
    "ViewService",
    "get_view_service",
    "FastTriageService",
    "get_fast_triage_service",
    "FeatureFlagService",
    "get_feature_flag_service",
    "is_adaptive_enabled",
]
