"""
Failing unit tests for selector resolution engine.

These tests are written first (Test-First Validation) and must fail
before implementation. They will pass once the SelectorEngine is properly
implemented according to the specification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.models.selector_models import (
    SemanticSelector, StrategyPattern, StrategyType, SelectorResult,
    ElementInfo, ValidationRule
)
from src.selectors.context import DOMContext
from src.selectors import SelectorEngine
from src.utils.exceptions import (
    SelectorNotFoundError, ResolutionTimeoutError, 
    ConfidenceThresholdError
)


class TestSelectorEngine:
    """Test cases for the main selector engine."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_resolve_selector_success(self, mock_dom_context, sample_selector_definition):
        """Test successful selector resolution with confidence > 0.8."""
        # This test will fail until SelectorEngine is implemented
        engine = SelectorEngine()
        
        # Register the selector
        # engine.register_selector(sample_selector_definition)  # Not implemented yet
        
        # Resolve the selector
        result = await engine.resolve("home_team_name", mock_dom_context)
        
        # Assertions that should pass after implementation
        assert result.success is True
        assert result.confidence_score > 0.8
        assert result.element_info is not None
        assert result.selector_name == "home_team_name"
        assert result.strategy_used in ["home_text_anchor", "home_attribute_match"]
        assert result.resolution_time > 0
        assert len(result.validation_results) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_resolve_selector_fallback_to_secondary_strategy(self, mock_dom_context):
        """Test selector resolution falls back to secondary strategy when primary fails."""
        engine = SelectorEngine()
        
        # Create selector where primary strategy will fail
        selector = SemanticSelector(
            name="test_selector",
            description="Test selector for fallback",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="primary_failing",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "nonexistent_text"}
                ),
                StrategyPattern(
                    id="secondary_working",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=2,
                    config={"attribute": "class", "value_pattern": "team-name"}
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        # engine.register_selector(selector)  # Not implemented yet
        
        result = await engine.resolve("test_selector", mock_dom_context)
        
        # Should succeed with secondary strategy
        assert result.success is True
        assert result.strategy_used == "secondary_working"
        assert result.confidence_score > 0.8
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_resolve_selector_all_strategies_fail(self, mock_dom_context):
        """Test selector resolution when all strategies fail."""
        engine = SelectorEngine()
        
        # Create selector where all strategies will fail
        selector = SemanticSelector(
            name="failing_selector",
            description="Selector that will fail",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="strategy1",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "nonexistent"}
                ),
                StrategyPattern(
                    id="strategy2",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=2,
                    config={"attribute": "nonexistent", "value_pattern": "none"}
                ),
                StrategyPattern(
                    id="strategy3",
                    type=StrategyType.DOM_RELATIONSHIP,
                    priority=3,
                    config={"parent_selector": ".nonexistent", "child_index": 0}
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        # engine.register_selector(selector)  # Not implemented yet
        
        result = await engine.resolve("failing_selector", mock_dom_context)
        
        # Should fail gracefully
        assert result.success is False
        assert result.confidence_score == 0.0
        assert result.element_info is None
        assert result.failure_reason is not None
        assert "All strategies failed" in result.failure_reason
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_resolve_selector_not_found(self, mock_dom_context):
        """Test resolution when selector is not found."""
        engine = SelectorEngine()
        
        with pytest.raises(SelectorNotFoundError) as exc_info:
            await engine.resolve("nonexistent_selector", mock_dom_context)
        
        assert "nonexistent_selector" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_resolve_selector_timeout(self, mock_dom_context):
        """Test selector resolution timeout."""
        engine = SelectorEngine()
        
        # Create selector with very short timeout
        selector = SemanticSelector(
            name="timeout_selector",
            description="Selector that will timeout",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="slow_strategy",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "test"}
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        # Mock the page to simulate timeout
        mock_dom_context.page.query_selector.side_effect = AsyncMock(
            side_effect=Exception("Timeout")
        )
        
        # engine.register_selector(selector)  # Not implemented yet
        
        with pytest.raises(ResolutionTimeoutError) as exc_info:
            await engine.resolve("timeout_selector", mock_dom_context)
        
        assert "timeout_selector" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_resolve_selector_low_confidence(self, mock_dom_context):
        """Test selector resolution with confidence below threshold."""
        engine = SelectorEngine()
        
        # Create selector with low confidence threshold
        selector = SemanticSelector(
            name="low_confidence_selector",
            description="Selector with low confidence",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="low_conf_strategy",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "ambiguous"}
                )
            ],
            validation_rules=[
                ValidationRule(
                    type="regex",
                    pattern=r"^[A-Za-z\s]+$",
                    required=True,
                    weight=0.5
                )
            ],
            confidence_threshold=0.8
        )
        
        # Mock element with ambiguous content
        mock_element = AsyncMock()
        mock_element.text_content.return_value = "???"
        mock_element.get_attribute.return_value = "class ambiguous"
        mock_dom_context.page.query_selector.return_value = mock_element
        
        # engine.register_selector(selector)  # Not implemented yet
        
        with pytest.raises(ConfidenceThresholdError) as exc_info:
            await engine.resolve("low_confidence_selector", mock_dom_context)
        
        assert "low_confidence_selector" in str(exc_info.value)
        assert "0.8" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_resolve_batch_selectors(self, mock_dom_context):
        """Test batch resolution of multiple selectors."""
        engine = SelectorEngine()
        
        # Register multiple selectors
        selectors = ["home_team_name", "away_team_name", "match_score"]
        
        # for selector_name in selectors:
        #     engine.register_selector(create_test_selector(selector_name))  # Not implemented yet
        
        results = await engine.resolve_batch(selectors, mock_dom_context)
        
        # Should return results for all selectors
        assert len(results) == len(selectors)
        
        # Each result should have the correct selector name
        for i, result in enumerate(results):
            assert result.selector_name == selectors[i]
            assert result.resolution_time > 0
    
    def test_get_selector_exists(self, sample_selector_definition):
        """Test getting an existing selector."""
        engine = SelectorEngine()
        
        # engine.register_selector(sample_selector_definition)  # Not implemented yet
        
        selector = engine.get_selector("home_team_name")
        
        assert selector is not None
        assert selector.name == "home_team_name"
        assert selector.context == "summary"
        assert len(selector.strategies) >= 3
    
    def test_get_selector_not_exists(self):
        """Test getting a non-existent selector."""
        engine = SelectorEngine()
        
        selector = engine.get_selector("nonexistent_selector")
        
        assert selector is None
    
    def test_list_selectors_all(self, sample_selector_definition):
        """Test listing all selectors."""
        engine = SelectorEngine()
        
        # engine.register_selector(sample_selector_definition)  # Not implemented yet
        
        selectors = engine.list_selectors()
        
        assert isinstance(selectors, list)
        assert "home_team_name" in selectors
    
    def test_list_selectors_by_context(self, sample_selector_definition):
        """Test listing selectors filtered by context."""
        engine = SelectorEngine()
        
        # engine.register_selector(sample_selector_definition)  # Not implemented yet
        
        selectors = engine.list_selectors(context="summary")
        
        assert isinstance(selectors, list)
        assert all(context == "summary" for context in selectors)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_validate_selector_valid(self, sample_selector_definition):
        """Test validating a valid selector."""
        engine = SelectorEngine()
        
        issues = await engine.validate_selector(sample_selector_definition)
        
        # Should return empty list for valid selector
        assert isinstance(issues, list)
        assert len(issues) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.selector_engine
    async def test_validate_selector_invalid(self):
        """Test validating an invalid selector."""
        engine = SelectorEngine()
        
        # Create invalid selector (less than 3 strategies)
        invalid_selector = SemanticSelector(
            name="invalid_selector",
            description="Invalid selector",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="only_strategy",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "test"}
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        issues = await engine.validate_selector(invalid_selector)
        
        # Should return list of validation issues
        assert isinstance(issues, list)
        assert len(issues) > 0
        assert any("strategies" in issue.lower() for issue in issues)
    
    def test_get_confidence_metrics(self, sample_selector_definition):
        """Test getting confidence metrics for selector."""
        engine = SelectorEngine()
        
        # engine.register_selector(sample_selector_definition)  # Not implemented yet
        
        metrics = engine.get_confidence_metrics("home_team_name")
        
        assert metrics.selector_name == "home_team_name"
        assert metrics.total_attempts >= 0
        assert metrics.successful_attempts >= 0
        assert metrics.failed_attempts >= 0
        assert 0.0 <= metrics.success_rate <= 1.0
        assert 0.0 <= metrics.avg_confidence <= 1.0


# Helper functions for testing (these will be needed for the tests to work)

def create_test_selector(selector_name: str) -> SemanticSelector:
    """Create a test selector for the given name."""
    return SemanticSelector(
        name=selector_name,
        description=f"Test selector for {selector_name}",
        context="summary",
        strategies=[
            StrategyPattern(
                id=f"{selector_name}_primary",
                type=StrategyType.TEXT_ANCHOR,
                priority=1,
                config={"anchor_text": selector_name.replace("_", " ").title()}
            ),
            StrategyPattern(
                id=f"{selector_name}_secondary",
                type=StrategyType.ATTRIBUTE_MATCH,
                priority=2,
                config={"attribute": "class", "value_pattern": selector_name}
            ),
            StrategyPattern(
                id=f"{selector_name}_tertiary",
                type=StrategyType.DOM_RELATIONSHIP,
                priority=3,
                config={"parent_selector": ".match-header", "child_index": 0}
            )
        ],
        validation_rules=[
            ValidationRule(
                type="regex",
                pattern=r"^[A-Za-z\s]+$",
                required=True,
                weight=0.4
            )
        ],
        confidence_threshold=0.8
    )
