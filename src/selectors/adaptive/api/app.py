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

from src.selectors.adaptive.api.routes.failures import router as failures_router


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
        allow_headers=["Content-Type", "Authorization"],
    )
    
    # Include routers
    app.include_router(failures_router)
    
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
