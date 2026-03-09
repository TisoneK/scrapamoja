"""
FastAPI application for the adaptive selector API.

This app provides REST API endpoints for:
- Listing selector failures with filtering
- Getting failure details with proposed alternatives
- Approving/rejecting proposed selectors

Story: 4.1 - View Proposed Selectors with Visual Preview

Run with: uvicorn src.selectors.adaptive.api.app:app --reload
"""

import os
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.selectors.adaptive.api.middleware.performance import PerformanceMonitoringMiddleware
from src.selectors.adaptive.api.middleware.rate_limiting import RateLimitMiddleware, BulkOperationSizeMiddleware
from src.selectors.adaptive.api.middleware.audit_logging import AuditLoggingMiddleware
from src.selectors.adaptive.api.websocket.failure_updates import websocket_endpoint
from src.selectors.adaptive.api.routes.failures import router as failures_router
from src.selectors.adaptive.api.routes.audit import router as audit_router
from src.selectors.adaptive.api.routes.audit_query import router as audit_query_router
from src.selectors.adaptive.api.routes.users import router as users_router
from src.selectors.adaptive.api.routes.views import router as views_router
from src.selectors.adaptive.api.routes.triage import router as triage_router
from src.selectors.adaptive.api.routes.custom_strategies import router as custom_strategies_router
from src.selectors.adaptive.api.routes.feature_flags import router as feature_flags_router
from src.selectors.adaptive.api.routes.confidence import router as confidence_router
from src.selectors.adaptive.api.routes.health import router as health_router
from src.selectors.adaptive.api.routes.blast_radius import router as blast_radius_router


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Get allowed origins from environment (comma-separated)
    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
    
    app = FastAPI(
        title="Scrapamoja Adaptive Selector API",
        description="API for managing selector failures and proposed alternatives",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware with configurable origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-User-ID"],
    )
    
    # Add audit logging middleware for compliance and debugging
    # Logs all triage actions with sanitized request/response data
    app.add_middleware(AuditLoggingMiddleware, log_level="INFO")
    
    # Add rate limiting middleware to prevent abuse
    # Limits: 100 req/min default, 20 bulk/min, 10 strict/min
    app.add_middleware(RateLimitMiddleware)
    
    # Add bulk operation size validation
    # Prevents excessively large bulk operations (>100 items)
    app.add_middleware(BulkOperationSizeMiddleware, max_bulk_size=100)
    
    # Add performance monitoring middleware for AC #3 compliance
    # Tracks response times to ensure < 2s page load and < 500ms actions
    app.add_middleware(PerformanceMonitoringMiddleware)
    
    # Include routers
    app.include_router(failures_router)
    app.include_router(audit_router)
    app.include_router(audit_query_router)
    app.include_router(users_router)
    app.include_router(views_router)
    app.include_router(triage_router)
    app.include_router(custom_strategies_router)
    app.include_router(feature_flags_router)
    app.include_router(confidence_router)
    app.include_router(health_router)
    app.include_router(blast_radius_router)
    
    # WebSocket endpoint for real-time failure updates (Task 3.2)
    app.websocket("/ws/failures")(websocket_endpoint)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "adaptive-selector-api"}
    
    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "service": "Scrapamoja Adaptive Selector API",
            "version": "1.0.0",
            "docs": "/docs",
            "endpoints": {
                "failures": "/failures",
                "failure_detail": "/failures/{failure_id}",
                "approve": "/failures/{failure_id}/approve",
                "reject": "/failures/{failure_id}/reject",
                "audit_trail": "/audit/trail",
                "selector_audit_trail": "/audit/trail/{selector_id}",
                "user_decision_history": "/audit/trail/user/{user_id}",
                "audit_summary": "/audit/summary",
                "export_json": "/audit/export/json",
                "export_csv": "/audit/export/csv",
                "audit_query": "/audit/log",
                "selector_audit_query": "/audit/log/selector/{selector_id}",
                "user_audit_query": "/audit/log/user/{user_id}",
                "date_range_audit_query": "/audit/log/date-range",
                "user_info": "/users/me",
                "view_mode_switch": "/users/me/view-mode",
                "view_adaptive_failure": "/views/failures/{failure_id}",
                "view_modes": "/views/modes",
                # Fast triage endpoints
                "triage_failures": "/triage/failures",
                "quick_approve": "/triage/failures/{failure_id}/quick-approve",
                "bulk_approve": "/triage/bulk-approve",
                "bulk_reject": "/triage/bulk-reject",
                "quick_escalate": "/triage/escalate",
                "performance": "/triage/performance",
                # Feature flag endpoints
                "feature_flags": "/feature-flags",
                "feature_flag_check": "/feature-flags/check",
                "enabled_sports": "/feature-flags/enabled-sports",
                "feature_flag_stats": "/feature-flags/stats",
                "toggle_sport_flag": "/feature-flags/{sport}",
                "update_site_flag": "/feature-flags/{sport}/sites/{site}",
                # Confidence score query endpoints (Story 6-1)
                "confidence_query": "/api/v1/confidence/{selector_id}",
                "confidence_batch": "/api/v1/confidence/batch",
                "confidence_all": "/api/v1/confidence",
                # Health status display endpoints (Story 6-2)
                "health_dashboard": "/api/v1/health",
                "health_selector": "/api/v1/health/{selector_id}",
                "health_config": "/api/v1/health/config/thresholds",
                # Blast radius calculation endpoints (Story 6-3)
                "blast_radius_selector": "/api/v1/blast-radius/{selector_id}",
                "blast_radius_batch": "/api/v1/blast-radius?selector_ids=...",
                "blast_radius_config": "/api/v1/blast-radius/config",
                "blast_radius_summary": "/api/v1/blast-radius/summary",
            },
        }
    
    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.selectors.adaptive.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
