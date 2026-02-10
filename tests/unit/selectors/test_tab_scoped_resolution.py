"""
Test suite for Tab-Scoped Selector Resolution.

This test suite follows the Test-First Validation principle from the Scorewise Constitution.
All tests are designed to fail initially and will pass once the corresponding implementation is completed.

User Story 3 - Context-Aware Tab Scoping
As a developer working with SPA applications, I want selectors to be automatically scoped to their correct tab context, 
so that tab switching doesn't cause cross-contamination or stale element issues.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.models.selector_models import (
    TabContext, TabState, TabType, TabVisibility,
    SemanticSelector, SelectorResult, ElementInfo, ValidationResult,
    StrategyPattern, StrategyType
)
from src.selectors.context import DOMContext
from src.utils.exceptions import TabContextError, SelectorResolutionError


class TestTabScopedSelectorResolution:
    """Test tab-scoped selector resolution functionality."""
    
    def test_resolve_selector_within_active_tab_context(self):
        """Test resolving a selector within its designated active tab context."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page with active odds tab
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "odds",
            "available_tabs": ["summary", "odds", "h2h"],
            "tab_states": {
                "summary": {"visible": False, "loaded": True},
                "odds": {"visible": True, "loaded": True},
                "h2h": {"visible": False, "loaded": False}
            }
        }
        
        # Create tab-scoped selector for odds tab
        selector = SemanticSelector(
            name="home_team_odds",
            description="Home team odds in odds tab",
            tab_context="odds",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "Manchester United"}
                )
            ]
        )
        
        # Mock element found in odds tab
        mock_element = Mock()
        mock_element.text_content = "2.45"
        mock_element.get_attribute.return_value = "odds-value"
        mock_page.query_selector.return_value = mock_element
        
        # Should resolve selector within active tab context
        result = engine.resolve(mock_page, selector)
        
        assert result is not None
        assert result.success is True
        assert result.tab_context == "odds"
        assert result.element_info.text_content == "2.45"
        assert result.confidence_score > 0.8
    
    def test_resolve_selector_returns_none_when_tab_inactive(self):
        """Test that selector returns None when its tab context is not active."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page with summary tab active (odds tab inactive)
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "summary",
            "available_tabs": ["summary", "odds", "h2h"],
            "tab_states": {
                "summary": {"visible": True, "loaded": True},
                "odds": {"visible": False, "loaded": True},
                "h2h": {"visible": False, "loaded": False}
            }
        }
        
        # Create tab-scoped selector for odds tab
        selector = SemanticSelector(
            name="home_team_odds",
            description="Home team odds in odds tab",
            tab_context="odds",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "Manchester United"}
                )
            ]
        )
        
        # Should return None when tab is inactive
        result = engine.resolve(mock_page, selector)
        
        assert result is not None
        assert result.success is False
        assert result.tab_context == "odds"
        assert result.failure_reason == "tab_context_inactive"
    
    def test_resolve_selector_respects_tab_dom_scope(self):
        """Test that selector resolution is limited to tab's DOM scope."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page with tab DOM structure
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "odds",
            "available_tabs": ["summary", "odds"],
            "tab_states": {
                "summary": {"visible": False, "loaded": True},
                "odds": {"visible": True, "loaded": True}
            }
        }
        
        # Mock elements in different tabs
        summary_element = Mock()
        summary_element.text_content = "Manchester United"
        summary_element.get_attribute.return_value = "summary-team"
        
        odds_element = Mock()
        odds_element.text_content = "2.45"
        odds_element.get_attribute.return_value = "odds-value"
        
        # Mock query_selector to return tab-scoped results
        def mock_query_selector(selector):
            if "div#odds-content" in selector:
                return odds_element
            return None
        
        mock_page.query_selector.side_effect = mock_query_selector
        
        # Create tab-scoped selector
        selector = SemanticSelector(
            name="home_team_odds",
            description="Home team odds in odds tab",
            tab_context="odds",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "2.45"}
                )
            ]
        )
        
        # Should only find elements within tab's DOM scope
        result = engine.resolve(mock_page, selector)
        
        assert result is not None
        assert result.success is True
        assert result.element_info.text_content == "2.45"
        assert "odds-content" in result.element_info.dom_path
    
    def test_resolve_selector_with_tab_context_validation(self):
        """Test selector resolution with tab context validation."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "odds",
            "available_tabs": ["summary", "odds", "h2h"],
            "tab_states": {
                "summary": {"visible": False, "loaded": True},
                "odds": {"visible": True, "loaded": True},
                "h2h": {"visible": False, "loaded": False}
            }
        }
        
        # Create selector with invalid tab context
        selector = SemanticSelector(
            name="invalid_tab_selector",
            description="Selector with invalid tab context",
            tab_context="nonexistent_tab",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "Test"}
                )
            ]
        )
        
        # Should fail with tab context validation error
        with pytest.raises(TabContextError) as exc_info:
            engine.resolve(mock_page, selector)
        
        assert exc_info.value.error_code == "invalid_tab_context"
    
    def test_resolve_selector_with_context_isolation(self):
        """Test that selectors are properly isolated by tab context."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page with multiple tabs
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "odds",
            "available_tabs": ["summary", "odds"],
            "tab_states": {
                "summary": {"visible": False, "loaded": True},
                "odds": {"visible": True, "loaded": True}
            }
        }
        
        # Create selectors for different tabs with same strategy
        summary_selector = SemanticSelector(
            name="summary_team",
            description="Team name in summary tab",
            tab_context="summary",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "Manchester United"}
                )
            ]
        )
        
        odds_selector = SemanticSelector(
            name="odds_value",
            description="Odds value in odds tab",
            tab_context="odds",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "2.45"}
                )
            ]
        )
        
        # Mock elements in respective tabs
        def mock_query_selector(selector):
            if "div#summary-content" in selector:
                element = Mock()
                element.text_content = "Manchester United"
                element.get_attribute.return_value = "summary-team"
                return element
            elif "div#odds-content" in selector:
                element = Mock()
                element.text_content = "2.45"
                element.get_attribute.return_value = "odds-value"
                return element
            return None
        
        mock_page.query_selector.side_effect = mock_query_selector
        
        # Should resolve odds selector (active tab) but not summary selector
        odds_result = engine.resolve(mock_page, odds_selector)
        summary_result = engine.resolve(mock_page, summary_selector)
        
        assert odds_result.success is True
        assert odds_result.element_info.text_content == "2.45"
        
        assert summary_result.success is False
        assert summary_result.failure_reason == "tab_context_inactive"


class TestTabScopedResolutionStrategies:
    """Test tab-scoped resolution strategies and fallbacks."""
    
    def test_tab_aware_strategy_execution(self):
        """Test that strategies are executed with tab awareness."""
        # This test will fail until TabAwareStrategyPattern is implemented
        from src.selectors.strategies.tab_aware import TabAwareTextAnchorStrategy
        
        strategy = TabAwareTextAnchorStrategy({"anchor_text": "Test"})
        
        # Mock DOM context with tab information
        dom_context = DOMContext(
            page=Mock(),
            tab_context=TabContext(
                tab_id="odds",
                tab_type=TabType.CONTENT,
                state=TabState.LOADED,
                visibility=TabVisibility.VISIBLE,
                is_active=True,
                dom_scope="div#odds-content"
            )
        )
        
        # Mock selector
        selector = SemanticSelector(
            name="test_selector",
            description="Test selector",
            tab_context="odds",
            strategies=[strategy]
        )
        
        # Mock element within tab scope
        mock_element = Mock()
        mock_element.text_content = "Test content"
        mock_element.get_attribute.return_value = "test-element"
        dom_context.page.query_selector.return_value = mock_element
        
        # Should execute strategy with tab awareness
        result = strategy.attempt_resolution(dom_context, selector)
        
        assert result is not None
        assert result.success is True
        assert result.tab_context == "odds"
        assert "odds-content" in result.element_info.dom_path
    
    def test_tab_scoped_fallback_mechanism(self):
        """Test fallback mechanism within tab context."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "odds",
            "available_tabs": ["odds"],
            "tab_states": {
                "odds": {"visible": True, "loaded": True}
            }
        }
        
        # Create selector with multiple strategies
        selector = SemanticSelector(
            name="multi_strategy_selector",
            description="Selector with fallback strategies",
            tab_context="odds",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "NonExistent"}
                ),
                StrategyPattern(
                    strategy_type=StrategyType.ATTRIBUTE_MATCH,
                    config={"attribute": "class", "value_pattern": "odds-value"}
                )
            ]
        )
        
        # Mock element found by second strategy
        mock_element = Mock()
        mock_element.text_content = "2.45"
        mock_element.get_attribute.return_value = "odds-value"
        mock_page.query_selector.return_value = mock_element
        
        # Should fallback to second strategy within tab context
        result = engine.resolve(mock_page, selector)
        
        assert result is not None
        assert result.success is True
        assert result.strategy_used == "attribute_match"
        assert result.tab_context == "odds"
    
    def test_tab_context_confidence_adjustment(self):
        """Test confidence scoring adjustment based on tab context."""
        # This test will fail until TabAwareConfidenceScorer is implemented
        from src.selectors.confidence.tab_aware import TabAwareConfidenceScorer
        
        scorer = TabAwareConfidenceScorer()
        
        # Create result within active tab
        result = SelectorResult(
            selector_name="test_selector",
            strategy_used="text_anchor",
            element_info=ElementInfo(
                tag_name="span",
                text_content="Test",
                attributes={"class": "test-element"},
                css_classes=["test-element"],
                dom_path="div#odds-content span.test",
                visibility=True,
                interactable=True
            ),
            confidence_score=0.8,
            resolution_time=50.0,
            tab_context="odds",
            validation_results=[
                ValidationResult(rule_type="regex", passed=True, score=0.9, weight=1.0)
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        # Should adjust confidence based on tab context
        adjusted_score = scorer.calculate_confidence(result, result.validation_results)
        
        assert adjusted_score > 0.8  # Should be higher for correct tab context
        assert adjusted_score <= 1.0


class TestTabScopedResolutionEdgeCases:
    """Test edge cases for tab-scoped selector resolution."""
    
    def test_selector_without_tab_context(self):
        """Test selector without specified tab context."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "odds",
            "available_tabs": ["summary", "odds"],
            "tab_states": {
                "summary": {"visible": False, "loaded": True},
                "odds": {"visible": True, "loaded": True}
            }
        }
        
        # Create selector without tab context
        selector = SemanticSelector(
            name="global_selector",
            description="Global selector without tab context",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "Global"}
                )
            ]
        )
        
        # Should resolve without tab restriction
        mock_element = Mock()
        mock_element.text_content = "Global content"
        mock_page.query_selector.return_value = mock_element
        
        result = engine.resolve(mock_page, selector)
        
        assert result is not None
        assert result.success is True
        assert result.tab_context is None  # No tab context specified
    
    def test_tab_context_not_loaded(self):
        """Test selector resolution when tab context is not loaded."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page with unloaded tab
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "active_tab": "odds",
            "available_tabs": ["summary", "odds"],
            "tab_states": {
                "summary": {"visible": False, "loaded": False},  # Not loaded
                "odds": {"visible": True, "loaded": True}
            }
        }
        
        # Create selector for unloaded tab
        selector = SemanticSelector(
            name="unloaded_tab_selector",
            description="Selector for unloaded tab",
            tab_context="summary",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "Test"}
                )
            ]
        )
        
        # Should fail because tab is not loaded
        result = engine.resolve(mock_page, selector)
        
        assert result is not None
        assert result.success is False
        assert result.failure_reason == "tab_context_not_loaded"
    
    def test_dynamic_tab_context_switching(self):
        """Test selector resolution during dynamic tab switching."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        
        engine = TabScopedSelectorEngine()
        
        # Mock page with tab switching
        mock_page = Mock()
        
        # Initial state - summary active
        mock_page.evaluate.side_effect = [
            {"active_tab": "summary", "available_tabs": ["summary", "odds"]},  # Tab detection
            {"active_tab": "odds", "available_tabs": ["summary", "odds"]}     # After switch
        ]
        
        # Create selector for odds tab
        selector = SemanticSelector(
            name="odds_selector",
            description="Selector for odds tab",
            tab_context="odds",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "2.45"}
                )
            ]
        )
        
        # Mock element in odds tab
        mock_element = Mock()
        mock_element.text_content = "2.45"
        mock_page.query_selector.return_value = mock_element
        
        # Should handle tab switching during resolution
        result = engine.resolve(mock_page, selector)
        
        assert result is not None
        assert result.success is True
        assert result.tab_context == "odds"
    
    def test_tab_context_resolution_timeout(self):
        """Test timeout handling for tab context resolution."""
        # This test will fail until TabScopedSelectorEngine is implemented
        from src.selectors.engine.tab_scoped import TabScopedSelectorEngine
        from src.utils.exceptions import SelectorResolutionError
        
        engine = TabScopedSelectorEngine()
        
        # Mock page that times out
        mock_page = Mock()
        mock_page.evaluate.side_effect = TimeoutError("Tab context detection timeout")
        
        # Create selector
        selector = SemanticSelector(
            name="timeout_selector",
            description="Selector that times out",
            tab_context="odds",
            strategies=[
                StrategyPattern(
                    strategy_type=StrategyType.TEXT_ANCHOR,
                    config={"anchor_text": "Test"}
                )
            ]
        )
        
        # Should handle timeout gracefully
        with pytest.raises(SelectorResolutionError) as exc_info:
            engine.resolve(mock_page, selector)
        
        assert "timeout" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "tab_context_timeout"
