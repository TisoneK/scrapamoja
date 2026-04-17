"""
API routes for custom selector strategy management.

This implements Story 7.2 (Technical and Non-Technical Views):
- Custom selector strategy creation interface
- Real-time validation and testing interface
- Save custom strategies for future use

Routes:
- POST /custom-strategies - Create new custom strategy
- GET /custom-strategies - List strategies
- GET /custom-strategies/{id} - Get specific strategy
- PUT /custom-strategies/{id} - Update strategy
- DELETE /custom-strategies/{id} - Delete strategy
- POST /custom-strategies/validate - Validate selector
- POST /custom-strategies/{id}/test - Test strategy
"""

from typing import Final, List, Optional, Type
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..schemas.custom_strategies import (
    CustomStrategyCreateSchema,
    CustomStrategyUpdateSchema,
    CustomStrategyResponseSchema,
    CustomStrategyListSchema,
    ValidationResultSchema,
    TestResultSchema,
    StrategyCreateResponseSchema,
)
from ..services.custom_strategy_service import (
    CustomStrategyService,
    get_custom_strategy_service,
    CustomStrategy,
    ValidationResult,
)

# Create router
router = APIRouter(prefix="/custom-strategies", tags=["custom-strategies"])


def _get_default_user_id() -> str:
    """
    Get default user ID for development.
    
    In production, this would come from authentication.
    """
    return "default_user"


@router.post(
    "",
    response_model=StrategyCreateResponseSchema,
    summary="Create custom strategy",
    description="Create a new custom selector strategy with validation",
    responses={
        400: {"description": "Invalid strategy or validation failed"},
    },
)
async def create_custom_strategy(
    request: CustomStrategyCreateSchema,
    user_id: Optional[str] = Query(None, description="User ID (optional, uses default if not provided)"),
    service: CustomStrategyService = Query(None, description="Custom strategy service dependency"),
) -> StrategyCreateResponseSchema:
    """
    Create a new custom selector strategy.
    
    Args:
        request: Strategy creation request
        user_id: Optional user ID override
        
    Returns:
        Created strategy with validation results
    """
    if service is None:
        service = get_custom_strategy_service()
    
    # Use provided user_id or default
    uid = user_id or _get_default_user_id()
    
    # Create strategy
    strategy, validation = service.create_strategy(
        name=request.name,
        description=request.description,
        selector=request.selector,
        strategy_type=request.strategy_type,
        confidence_weight=request.confidence_weight,
        blast_radius_protection=request.blast_radius_protection,
        validation_rules=request.validation_rules,
        created_by=uid
    )
    
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.error_message or "Strategy creation failed",
        )
    
    return StrategyCreateResponseSchema(
        strategy=CustomStrategyResponseSchema(**strategy.to_dict()),
        validation=ValidationResultSchema(
            is_valid=validation.is_valid,
            confidence_score=validation.confidence_score,
            error_message=validation.error_message,
            suggestions=validation.suggestions,
            test_results=validation.test_results,
        )
    )


@router.get(
    "",
    response_model=CustomStrategyListSchema,
    summary="List custom strategies",
    description="List all custom strategies with optional filtering",
)
async def list_custom_strategies(
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    active_only: bool = Query(True, description="Only return active strategies"),
    user_id: Optional[str] = Query(None, description="User ID (optional)"),
    service: CustomStrategyService = Query(None, description="Custom strategy service dependency"),
) -> CustomStrategyListSchema:
    """
    List custom strategies.
    
    Args:
        strategy_type: Optional strategy type filter
        created_by: Optional creator filter
        active_only: Only return active strategies
        user_id: Optional user ID override
        
    Returns:
        List of custom strategies
    """
    if service is None:
        service = get_custom_strategy_service()
    
    strategies = service.list_strategies(
        strategy_type=strategy_type,
        created_by=created_by,
        active_only=active_only
    )
    
    return CustomStrategyListSchema(
        strategies=[CustomStrategyResponseSchema(**s.to_dict()) for s in strategies],
        total=len(strategies)
    )


@router.get(
    "/{strategy_id}",
    response_model=CustomStrategyResponseSchema,
    summary="Get custom strategy",
    description="Get details of a specific custom strategy",
    responses={
        404: {"description": "Strategy not found"},
    },
)
async def get_custom_strategy(
    strategy_id: str,
    service: CustomStrategyService = Query(None, description="Custom strategy service dependency"),
) -> CustomStrategyResponseSchema:
    """
    Get a specific custom strategy.
    
    Args:
        strategy_id: The strategy ID
        
    Returns:
        Strategy details
    """
    if service is None:
        service = get_custom_strategy_service()
    
    strategy = service.get_strategy(strategy_id)
    
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    
    return CustomStrategyResponseSchema(**strategy.to_dict())


@router.put(
    "/{strategy_id}",
    response_model=CustomStrategyResponseSchema,
    summary="Update custom strategy",
    description="Update an existing custom strategy",
    responses={
        404: {"description": "Strategy not found"},
        400: {"description": "Invalid update data"},
    },
)
async def update_custom_strategy(
    strategy_id: str,
    request: CustomStrategyUpdateSchema,
    service: CustomStrategyService = Query(None, description="Custom strategy service dependency"),
) -> CustomStrategyResponseSchema:
    """
    Update a custom strategy.
    
    Args:
        strategy_id: The strategy ID
        request: Update request
        
    Returns:
        Updated strategy
    """
    if service is None:
        service = get_custom_strategy_service()
    
    # Convert request to dict, excluding None values
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    strategy = service.update_strategy(strategy_id, updates)
    
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    
    return CustomStrategyResponseSchema(**strategy.to_dict())


@router.delete(
    "/{strategy_id}",
    summary="Delete custom strategy",
    description="Delete a custom strategy",
    responses={
        404: {"description": "Strategy not found"},
    },
)
async def delete_custom_strategy(
    strategy_id: str,
    service: CustomStrategyService = Query(None, description="Custom strategy service dependency"),
) -> dict:
    """
    Delete a custom strategy.
    
    Args:
        strategy_id: The strategy ID
        
    Returns:
        Deletion result
    """
    if service is None:
        service = get_custom_strategy_service()
    
    success = service.delete_strategy(strategy_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )
    
    return {"message": f"Strategy {strategy_id} deleted successfully"}


@router.post(
    "/validate",
    response_model=ValidationResultSchema,
    summary="Validate selector",
    description="Validate a selector string without creating a strategy",
)
async def validate_selector(
    selector: str = Query(..., description="Selector string to validate"),
    strategy_type: str = Query(..., description="Strategy type (css, xpath, text_anchor, custom)"),
    service: CustomStrategyService = Query(None, description="Custom strategy service dependency"),
) -> ValidationResultSchema:
    """
    Validate a selector string.
    
    Args:
        selector: The selector to validate
        strategy_type: Type of selector
        service: Custom strategy service dependency
        
    Returns:
        Validation result
    """
    if service is None:
        service = get_custom_strategy_service()
    
    validation = service.validate_selector(selector, strategy_type)
    
    return ValidationResultSchema(
        is_valid=validation.is_valid,
        confidence_score=validation.confidence_score,
        error_message=validation.error_message,
        suggestions=validation.suggestions,
        test_results=validation.test_results,
    )


@router.post(
    "/{strategy_id}/test",
    response_model=TestResultSchema,
    summary="Test custom strategy",
    description="Test a custom strategy against sample content",
    responses={
        404: {"description": "Strategy not found"},
    },
)
async def test_custom_strategy(
    strategy_id: str,
    test_content: Optional[str] = Query(None, description="Sample content to test against"),
    service: CustomStrategyService = Query(None, description="Custom strategy service dependency"),
) -> TestResultSchema:
    """
    Test a custom strategy.
    
    Args:
        strategy_id: The strategy ID
        test_content: Optional sample content
        
    Returns:
        Test results
    """
    if service is None:
        service = get_custom_strategy_service()
    
    result = service.test_strategy(strategy_id, test_content)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )
    
    return TestResultSchema(**result)


@router.get(
    "/types",
    summary="Get strategy types",
    description="Get list of available strategy types",
)
async def get_strategy_types() -> dict:
    """
    Get available strategy types.
    
    Returns:
        Dictionary of available strategy types
    """
    return {
        "strategy_types": [
            {
                "id": "css",
                "name": "CSS Selector",
                "description": "Standard CSS selectors (classes, IDs, attributes)",
                "examples": [".team-name", "#score", "[data-testid]"],
                "confidence_range": [0.5, 0.9],
            },
            {
                "id": "xpath",
                "name": "XPath",
                "description": "XPath expressions for complex selections",
                "examples": ["//div[@class='team']", "//span[contains(text(), 'Score')]"],
                "confidence_range": [0.6, 0.8],
            },
            {
                "id": "text_anchor",
                "name": "Text Anchor",
                "description": "Text-based selectors using content matching",
                "examples": ["Team Name", "Final Score"],
                "confidence_range": [0.4, 0.7],
            },
            {
                "id": "custom",
                "name": "Custom",
                "description": "Custom selector logic with advanced rules",
                "examples": ["custom_function()", "regex_pattern"],
                "confidence_range": [0.3, 0.8],
            },
        ]
    }
