"""
API routes for the adaptive selector system.
"""

from src.selectors.adaptive.api.routes.failures import router as failures_router
from src.selectors.adaptive.api.routes.feature_flags import router as feature_flags_router

__all__ = ["failures_router", "feature_flags_router"]
