"""
Confidence Score Query API endpoints.

This module provides REST API endpoints for:
- Single selector confidence query (GET /api/v1/confidence/{selector_id})
- Batch selector confidence query (POST /api/v1/confidence/batch)
- Paginated all-selectors query (GET /api/v1/confidence)

Story: 6.1 - Confidence Score Query API
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from src.selectors.adaptive.services.confidence_query_service import (
    get_confidence_query_service,
    ConfidenceScoreResult,
    BatchConfidenceResult,
    PaginatedConfidenceResult,
)
from src.selectors.adaptive.api.schemas.confidence import (
    ConfidenceScoreResponse,
    BatchConfidenceQuery,
    BatchConfidenceResponse,
    PaginatedConfidenceResponse,
)

router = APIRouter(prefix="/api/v1/confidence", tags=["confidence"])


def _to_response(result: ConfidenceScoreResult) -> ConfidenceScoreResponse:
    """Convert service result to API response."""
    return ConfidenceScoreResponse(
        selector_id=result.selector_id,
        confidence_score=result.confidence_score,
        last_updated=result.last_updated,
        is_estimated=result.is_estimated,
    )


@router.get(
    "/{selector_id}",
    response_model=ConfidenceScoreResponse,
    summary="Get single selector confidence score",
    description="Query the confidence score for a single selector by ID",
)
async def get_confidence(
    selector_id: str,
) -> ConfidenceScoreResponse:
    """
    Get confidence score for a single selector.

    Args:
        selector_id: The selector ID to query

    Returns:
        ConfidenceScoreResponse with score, timestamp, and estimated flag

    Raises:
        HTTPException: If the selector is not found
    """
    service = get_confidence_query_service()

    try:
        result = service.query_single(selector_id)
        return _to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query confidence: {str(e)}")


@router.post(
    "/batch",
    response_model=BatchConfidenceResponse,
    summary="Batch query confidence scores",
    description="Query confidence scores for multiple selectors in one request",
)
async def batch_query_confidence(
    query: BatchConfidenceQuery,
) -> BatchConfidenceResponse:
    """
    Batch query confidence scores for multiple selectors.

    Args:
        query: BatchConfidenceQuery with list of selector IDs

    Returns:
        BatchConfidenceResponse with results and missing selectors
    """
    service = get_confidence_query_service()

    try:
        result = service.query_batch(query.selector_ids)

        # Convert results to response format
        results_dict = {}
        for selector_id, res in result.results.items():
            if res is not None:
                results_dict[selector_id] = _to_response(res)
            else:
                results_dict[selector_id] = None

        return BatchConfidenceResponse(
            results=results_dict,
            missing_selectors=result.missing_selectors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to batch query confidence: {str(e)}")


@router.get(
    "",
    response_model=PaginatedConfidenceResponse,
    summary="Query all selectors with pagination",
    description="Query all selector confidence scores with pagination support",
)
async def get_all_confidence(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=50, ge=1, le=100, description="Results per page"),
) -> PaginatedConfidenceResponse:
    """
    Query all selector confidence scores with pagination.

    Args:
        page: Page number (1-indexed)
        page_size: Number of results per page

    Returns:
        PaginatedConfidenceResponse with paginated results
    """
    service = get_confidence_query_service()

    try:
        result = service.query_all_paginated(page=page, page_size=page_size)

        return PaginatedConfidenceResponse(
            results=[_to_response(r) for r in result.results],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query all confidence: {str(e)}")
