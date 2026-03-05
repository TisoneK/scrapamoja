"""
Database models package.
"""

from .recipe import Recipe, FailureSeverity, Base
from .failure_event import FailureEvent, ErrorType
from .weights import ApprovalWeight, SelectorApprovalHistory, RejectionWeight, SelectorRejectionHistory
from .audit_event import AuditEvent

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
]
