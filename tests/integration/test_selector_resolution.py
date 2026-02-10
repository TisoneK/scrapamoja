"""
Failing integration tests for multi-strategy selector resolution.

These tests are written first (Test-First Validation) and must fail
before implementation. They will pass once the multi-strategy resolution system
is properly implemented according to the specification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.models.selector_models import (
    SemanticSelector, StrategyPattern, StrategyType, SelectorResult,
    ElementInfo, ValidationRule, ValidationResult
)
from src.selectors.context import DOMContext
from src.selectors.interfaces import ISelectorEngine
from src.utils.exceptions import (
    SelectorNotFoundError, ResolutionTimeoutError,
    ConfidenceThresholdError
)


class TestMultiStrategyResolution:
    """Integration tests for multi-strategy selector resolution."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_primary_success(self, page, sample_html_content):
        """Test successful resolution using primary strategy."""
        # Setup page with sample content
        await page.set_content(sample_html_content)
        
        # Create DOM context
        context = DOMContext(
            page=page,
            tab_context="summary",
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
        # Create selector with multiple strategies
        selector = SemanticSelector(
            name="home_team_name",
            description="Home team name in match header",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="text_anchor_primary",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={
                        "anchor_text": "Manchester United",
                        "proximity_selector": ".team.home .team-name",
                        "case_sensitive": False
                    }
                ),
                StrategyPattern(
                    id="attribute_secondary",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=2,
                    config={
                        "attribute": "class",
                        "value_pattern": "team-name",
                        "element_tag": "span"
                    }
                ),
                StrategyPattern(
                    id="dom_tertiary",
                    type=StrategyType.DOM_RELATIONSHIP,
                    priority=3,
                    config={
                        "parent_selector": ".match-header",
                        "child_index": 0,
                        "relationship_type": "child"
                    }
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
        
        # Initialize selector engine
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        # Resolve selector
        result = await engine.resolve("home_team_name", context)
        
        # Should succeed with primary strategy
        assert result.success is True
        assert result.strategy_used == "text_anchor_primary"
        assert result.confidence_score > 0.8
        assert result.element_info.text_content == "Manchester United"
        assert result.element_info.tag_name == "span"
        assert "team-name" in result.element_info.css_classes
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_primary_fallback_secondary(self, page, sample_html_content):
        """Test fallback to secondary strategy when primary fails."""
        # Modify content to make primary strategy fail
        modified_content = sample_html_content.replace("Manchester United", "Home Team")
        
        await page.set_content(modified_content)
        
        context = DOMContext(
            page=page,
            tab_context="summary",
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
        selector = SemanticSelector(
            name="home_team_name",
            description="Home team name in match header",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="text_anchor_failing",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={
                        "anchor_text": "Manchester United",  # This won't match
                        "proximity_selector": ".team.home .team-name",
                        "case_sensitive": False
                    }
                ),
                StrategyPattern(
                    id="attribute_working",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=2,
                    config={
                        "attribute": "class",
                        "value_pattern": "team-name",
                        "element_tag": "span"
                    }
                ),
                StrategyPattern(
                    id="dom_backup",
                    type=StrategyType.DOM_RELATIONSHIP,
                    priority=3,
                    config={
                        "parent_selector": ".match-header",
                        "child_index": 0,
                        "relationship_type": "child"
                    }
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
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        result = await engine.resolve("home_team_name", context)
        
        # Should succeed with secondary strategy
        assert result.success is True
        assert result.strategy_used == "attribute_working"
        assert result.confidence_score > 0.8
        assert result.element_info.text_content == "Home Team"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_all_strategies_fail(self, page):
        """Test complete failure when all strategies fail."""
        # Create content that won't match any strategy
        await page.set_content("""
        <html>
        <body>
            <div class="match-header">
                <div class="unknown-content">No team info here</div>
            </div>
        </body>
        </html>
        """)
        
        context = DOMContext(
            page=page,
            tab_context="summary",
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
        selector = SemanticSelector(
            name="home_team_name",
            description="Home team name in match header",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="text_anchor_failing",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "Manchester United"}
                ),
                StrategyPattern(
                    id="attribute_failing",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=2,
                    config={"attribute": "class", "value_pattern": "nonexistent"}
                ),
                StrategyPattern(
                    id="dom_failing",
                    type=StrategyType.DOM_RELATIONSHIP,
                    priority=3,
                    config={"parent_selector": ".nonexistent", "child_index": 0}
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
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        result = await engine.resolve("home_team_name", context)
        
        # Should fail gracefully
        assert result.success is False
        assert result.confidence_score == 0.0
        assert result.element_info is None
        assert result.failure_reason is not None
        assert "All strategies failed" in result.failure_reason
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_confidence_threshold(self, page):
        """Test confidence threshold enforcement."""
        # Create content with ambiguous match
        await page.set_content("""
        <html>
        <body>
            <div class="match-header">
                <span class="team-name">???</span>
            </div>
        </body>
        </html>
        """)
        
        context = DOMContext(
            page=page,
            tab_context="summary",
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
        selector = SemanticSelector(
            name="home_team_name",
            description="Home team name in match header",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="text_anchor_low_confidence",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "???"}
                ),
                StrategyPattern(
                    id="attribute_low_confidence",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=2,
                    config={"attribute": "class", "value_pattern": "team-name"}
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
            confidence_threshold=0.8  # High threshold
        )
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        # Should raise confidence threshold error
        with pytest.raises(ConfidenceThresholdError) as exc_info:
            await engine.resolve("home_team_name", context)
        
        assert "home_team_name" in str(exc_info.value)
        assert "0.8" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_batch_processing(self, page, sample_html_content):
        """Test batch resolution of multiple selectors."""
        await page.set_content(sample_html_content)
        
        context = DOMContext(
            page=page,
            tab_context="summary",
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
        # Create multiple selectors
        selectors = [
            SemanticSelector(
                name="home_team_name",
                description="Home team name",
                context="summary",
                strategies=[
                    StrategyPattern(
                        id="home_text",
                        type=StrategyType.TEXT_ANCHOR,
                        priority=1,
                        config={"anchor_text": "Manchester United"}
                    ),
                    StrategyPattern(
                        id="home_attr",
                        type=StrategyType.ATTRIBUTE_MATCH,
                        priority=2,
                        config={"attribute": "class", "value_pattern": "team-name"}
                    )
                ],
                validation_rules=[],
                confidence_threshold=0.8
            ),
            SemanticSelector(
                name="away_team_name",
                description="Away team name",
                context="summary",
                strategies=[
                    StrategyPattern(
                        id="away_text",
                        type=StrategyType.TEXT_ANCHOR,
                        priority=1,
                        config={"anchor_text": "Liverpool"}
                    ),
                    StrategyPattern(
                        id="away_attr",
                        type=StrategyType.ATTRIBUTE_MATCH,
                        priority=2,
                        config={"attribute": "class", "value_pattern": "team-name"}
                    )
                ],
                validation_rules=[],
                confidence_threshold=0.8
            ),
            SemanticSelector(
                name="match_score",
                description="Match score",
                context="summary",
                strategies=[
                    StrategyPattern(
                        id="score_text",
                        type=StrategyType.TEXT_ANCHOR,
                        priority=1,
                        config={"anchor_text": "2"}  # Home score
                    ),
                    StrategyPattern(
                        id="score_attr",
                        type=StrategyType.ATTRIBUTE_MATCH,
                        priority=2,
                        config={"attribute": "class", "value_pattern": "score"}
                    )
                ],
                validation_rules=[],
                confidence_threshold=0.8
            )
        ]
        
        engine = ISelectorEngine()
        # for selector in selectors:
        #     engine.register_selector(selector)  # Not implemented yet
        
        selector_names = ["home_team_name", "away_team_name", "match_score"]
        results = await engine.resolve_batch(selector_names, context)
        
        # Should resolve all selectors
        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(result.confidence_score > 0.8 for result in results)
        
        # Check specific results
        home_result = next(r for r in results if r.selector_name == "home_team_name")
        assert home_result.element_info.text_content == "Manchester United"
        
        away_result = next(r for r in results if r.selector_name == "away_team_name")
        assert away_result.element_info.text_content == "Liverpool"
        
        score_result = next(r for r in results if r.selector_name == "match_score")
        assert score_result.element_info.text_content == "2"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_strategy_performance_tracking(self, page, sample_html_content):
        """Test that strategy performance metrics are tracked."""
        await page.set_content(sample_html_content)
        
        context = DOMContext(
            page=page,
            tab_context="summary",
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
        selector = SemanticSelector(
            name="home_team_name",
            description="Home team name",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="primary_strategy",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "Manchester United"}
                ),
                StrategyPattern(
                    id="secondary_strategy",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=2,
                    config={"attribute": "class", "value_pattern": "team-name"}
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        # Resolve selector multiple times to build performance data
        for i in range(5):
            result = await engine.resolve("home_team_name", context)
            assert result.success is True
            assert result.strategy_used == "primary_strategy"
        
        # Check that metrics are tracked
        metrics = engine.get_confidence_metrics("home_team_name")
        assert metrics.total_attempts >= 5
        assert metrics.successful_attempts >= 5
        assert metrics.success_rate > 0.8
        assert metrics.avg_resolution_time > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_context_scoping(self, page, sample_html_content):
        """Test that selectors are properly scoped to tab context."""
        await page.set_content(sample_html_content)
        
        # Create context for different tab
        odds_context = DOMContext(
            page=page,
            tab_context="odds",  # Different tab context
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
        # Create selector for odds context
        odds_selector = SemanticSelector(
            name="home_win_odds",
            description="Home team win odds",
            context="odds",  # Only valid in odds tab
            strategies=[
                StrategyPattern(
                    id="odds_text",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={"anchor_text": "2.10"}
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        engine = ISelectorEngine()
        # engine.register_selector(odds_selector)  # Not implemented yet
        
        # Should fail because we're in summary context, not odds context
        with pytest.raises(SelectorNotFoundError) as exc_info:
            await engine.resolve("home_win_odds", odds_context)
        
        # Or alternatively, could return None result depending on implementation
        # result = await engine.resolve("home_win_odds", odds_context)
        # assert result.success is False
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_timeout_handling(self, page):
        """Test timeout handling for slow strategies."""
        # Mock page to simulate timeout
        page.query_selector = AsyncMock(side_effect=Exception("Timeout"))
        
        context = DOMContext(
            page=page,
            tab_context="summary",
            url="https://test.example.com/match/123",
            timestamp=datetime.utcnow()
        )
        
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
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        # Should handle timeout gracefully
        with pytest.raises(ResolutionTimeoutError) as exc_info:
            await engine.resolve("timeout_selector", context)
        
        assert "timeout_selector" in str(exc_info.value)


class TestMultiStrategyResolutionEdgeCases:
    """Edge case tests for multi-strategy resolution."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_empty_strategies(self):
        """Test selector with no strategies."""
        context = MagicMock()
        
        selector = SemanticSelector(
            name="no_strategies",
            description="Selector with no strategies",
            context="summary",
            strategies=[],  # No strategies
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        # Should fail validation or raise appropriate error
        issues = await engine.validate_selector(selector)
        assert len(issues) > 0
        assert any("strategies" in issue.lower() for issue in issues)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_duplicate_priorities(self):
        """Test selector with duplicate strategy priorities."""
        selector = SemanticSelector(
            name="duplicate_priorities",
            description="Selector with duplicate priorities",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="strategy1",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,  # Duplicate priority
                    config={"anchor_text": "test1"}
                ),
                StrategyPattern(
                    id="strategy2",
                    type=StrategyType.ATTRIBUTE_MATCH,
                    priority=1,  # Duplicate priority
                    config={"attribute": "class", "value_pattern": "test"}
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        # Should fail validation
        issues = await engine.validate_selector(selector)
        assert len(issues) > 0
        assert any("priority" in issue.lower() for issue in issues)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.selector_engine
    async def test_multi_strategy_resolution_invalid_strategy_config(self):
        """Test selector with invalid strategy configuration."""
        selector = SemanticSelector(
            name="invalid_config",
            description="Selector with invalid strategy config",
            context="summary",
            strategies=[
                StrategyPattern(
                    id="invalid_strategy",
                    type=StrategyType.TEXT_ANCHOR,
                    priority=1,
                    config={}  # Empty config
                )
            ],
            validation_rules=[],
            confidence_threshold=0.8
        )
        
        engine = ISelectorEngine()
        # engine.register_selector(selector)  # Not implemented yet
        
        # Should fail validation
        issues = await engine.validate_selector(selector)
        assert len(issues) > 0
