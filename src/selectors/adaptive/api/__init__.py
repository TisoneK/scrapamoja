"""
API module for the adaptive selector system.

This module provides REST API endpoints for the escalation UI
as specified in Epic 4: Human Verification Workflow.
"""

from src.selectors.adaptive.api.routes import failures

__all__ = ["failures"]
