"""
Database models package.
"""

from .recipe import Recipe, FailureSeverity, Base
from .failure_event import FailureEvent, ErrorType
from .weights import ApprovalWeight, SelectorApprovalHistory, RejectionWeight, SelectorRejectionHistory
from .audit_event import AuditEvent
from .user_preferences import UserPreference, ViewUsageAnalytics, UserRole, ViewMode
from .triage_metrics import TriageMetrics, BulkOperation, PerformanceCache
from .feature_flag import FeatureFlag

# NOTE: snapshot.py was removed - if needed, restore from version control
# from .snapshot import Snapshot, compress_html, decompress_html

__all__ = [
    "Recipe",
    "FailureSeverity",
    "Base",
    "FailureEvent",
    "ErrorType",
    "ApprovalWeight",
    "SelectorApprovalHistory",
    "RejectionWeight",
    "SelectorRejectionHistory",
    "AuditEvent",
    "UserPreference",
    "ViewUsageAnalytics",
    "UserRole",
    "ViewMode",
    "TriageMetrics",
    "BulkOperation",
    "PerformanceCache",
    "FeatureFlag",
]
