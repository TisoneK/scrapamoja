"""
API routes for the adaptive selector system.
"""

from src.selectors.adaptive.api.routes.failures import router as failures_router

__all__ = ["failures_router"]
