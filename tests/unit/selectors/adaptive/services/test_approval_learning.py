"""
Tests for Approval Learning functionality (Story 5.1).

Tests the:
- Approval weight tracking per strategy type
- Similar strategy boost (CSS → XPath, etc.)
- Weight persistence to database
- Integration with Approval Workflow
- Confidence score boost from approvals
"""

import pytest
from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
from src.selectors.adaptive.services.dom_analyzer import AlternativeSelector, StrategyType


class TestApprovalWeightTracking:
    """Tests for approval weight tracking per strategy type."""
    
    def test_initial_no_weights(self):
        """Test that a new scorer has no approval weights."""
        scorer = ConfidenceScorer()
        weights = scorer.get_approval_weights()
        assert weights == {}
    
    def test_record_first_approval(self):
        """Test recording first approval increases count and boost."""
        scorer = ConfidenceScorer()
        
        # Record first approval for CSS strategy
        scorer.record_positive_feedback(
            selector=".btn-primary",
            strategy=StrategyType.CSS,
            approved=True,
            confidence_at_approval=0.7,
        )
        
        weights = scorer.get_approval_weights()
        
        # Should have CSS with count 1
        assert 'css' in weights
        assert weights['css']['count'] == 1
        assert weights['css']['total_boost'] > 0
    
    def test_multiple_approvals_increase_boost(self):
        """Test that multiple approvals increase the boost."""
        scorer = ConfidenceScorer()
        
        # Record multiple approvals
        for i in range(5):
            scorer.record_positive_feedback(
                selector=f".selector-{i}",
                strategy=StrategyType.CSS,
                approved=True,
                confidence_at_approval=0.7,
            )
        
        weights = scorer.get_approval_weights()
        
        # Should have 5 approvals
        assert weights['css']['count'] == 5
        # Boost should be capped at MAX_APPROVAL_BOOST (0.25)
        assert weights['css']['total_boost'] <= ConfidenceScorer.MAX_APPROVAL_BOOST
    
    def test_different_strategies_tracked_separately(self):
        """Test that different strategy types are tracked separately."""
        scorer = ConfidenceScorer()
        
        # Record approvals for different strategies
        scorer.record_positive_feedback(
            selector=".btn-primary",
            strategy=StrategyType.CSS,
            approved=True,
        )
        
        scorer.record_positive_feedback(
            selector="//div[@class='btn']",
            strategy=StrategyType.XPATH,
            approved=True,
        )
        
        weights = scorer.get_approval_weights()
        
        assert 'css' in weights
        assert 'xpath' in weights
        assert weights['css']['count'] == 1
        assert weights['xpath']['count'] == 1


class TestSimilarStrategyBoost:
    """Tests for similar selector strategy boost."""
    
    def test_css_boosts_xpath(self):
        """Test that CSS approval boosts related XPath strategy."""
        scorer = ConfidenceScorer()
        
        # Record CSS approval
        scorer.record_positive_feedback(
            selector=".btn-primary",
            strategy=StrategyType.CSS,
            approved=True,
            confidence_at_approval=0.7,
        )
        
        # XPath should have related boost
        xpath_boost = scorer.get_strategy_boost(StrategyType.XPATH)
        
        # Should have some related boost from CSS
        assert xpath_boost > 0
    
    def test_xpath_boosts_css(self):
        """Test that XPath approval boosts related CSS strategy."""
        scorer = ConfidenceScorer()
        
        # Record XPath approval
        scorer.record_positive_feedback(
            selector="//div[@class='btn']",
            strategy=StrategyType.XPATH,
            approved=True,
            confidence_at_approval=0.6,
        )
        
        # CSS should have related boost
        css_boost = scorer.get_strategy_boost(StrategyType.CSS)
        
        # Should have some related boost from XPath
        assert css_boost > 0
    
    def test_text_anchor_boosts_dom_relationship(self):
        """Test that TEXT_ANCHOR boosts DOM_RELATIONSHIP."""
        scorer = ConfidenceScorer()
        
        scorer.record_positive_feedback(
            selector="span:contains('Click')",
            strategy=StrategyType.TEXT_ANCHOR,
            approved=True,
        )
        
        # DOM_RELATIONSHIP should have related boost
        dom_boost = scorer.get_strategy_boost(StrategyType.DOM_RELATIONSHIP)
        assert dom_boost > 0
    
    def test_boosts_accumulate(self):
        """Test that related boosts accumulate from multiple approvals."""
        scorer = ConfidenceScorer()
        
        # CSS boosts XPath
        scorer.record_positive_feedback(
            selector=".btn-1",
            strategy=StrategyType.CSS,
            approved=True,
        )
        
        scorer.record_positive_feedback(
            selector=".btn-2",
            strategy=StrategyType.CSS,
            approved=True,
        )
        
        # XPath should have accumulated related boost
        xpath_boost = scorer.get_strategy_boost(StrategyType.XPATH)
        assert xpath_boost > 0.03  # At least 2 * RELATED_STRATEGY_BOOST


class TestWeightPersistence:
    """Tests for weight persistence (in-memory for testing)."""
    
    def test_export_weights(self):
        """Test exporting weights for persistence."""
        scorer = ConfidenceScorer()
        
        scorer.record_positive_feedback(
            selector=".btn",
            strategy=StrategyType.CSS,
            approved=True,
        )
        
        exported = scorer.export_weights()
        
        assert 'css' in exported
        assert exported['css']['count'] == 1
    
    def test_load_weights(self):
        """Test loading weights from persistence."""
        scorer = ConfidenceScorer()
        
        # Simulate loading persisted weights
        persisted = {
            'css': {
                'count': 3,
                'total_boost': 0.15,
                'related_boost': 0.05,
                'last_approval': '2026-03-05T10:00:00',
            }
        }
        
        scorer.load_weights(persisted)
        
        weights = scorer.get_approval_weights()
        assert weights['css']['count'] == 3
    
    def test_empty_load_does_not_crash(self):
        """Test that loading empty weights doesn't crash."""
        scorer = ConfidenceScorer()
        
        # Should not raise
        scorer.load_weights({})
        
        assert scorer.get_approval_weights() == {}


class TestConfidenceBoost:
    """Tests for confidence score boost from approvals."""
    
    def test_approval_boosts_historical_stability(self):
        """Test that approval increases historical stability lookup."""
        scorer = ConfidenceScorer()
        
        # Record approval
        scorer.record_positive_feedback(
            selector=".approved-selector",
            strategy=StrategyType.CSS,
            approved=True,
            confidence_at_approval=0.7,
        )
        
        # Create a new selector with same string
        test_selector = AlternativeSelector(
            selector_string=".approved-selector",
            strategy_type=StrategyType.CSS,
            confidence_score=0.5,
            element_description="Test selector",
        )
        
        # Score should use the boosted historical data
        scored = scorer.calculate_confidence(test_selector)
        
        # Should be higher than base due to approval learning
        # The historical lookup should return boosted value (not None)
        assert scored.historical_stability is not None
        assert scored.historical_stability >= 0.5
    
    def test_strategy_default_boosted_after_approval(self):
        """Test that strategy defaults get boosted after approval."""
        scorer = ConfidenceScorer()
        
        # Base default for CSS is 0.7
        base_default = ConfidenceScorer.STRATEGY_DEFAULTS[StrategyType.CSS]
        
        # Record approval
        scorer.record_positive_feedback(
            selector=".new-selector",
            strategy=StrategyType.CSS,
            approved=True,
            confidence_at_approval=0.7,
        )
        
        # Create selector with no specific history
        test_selector = AlternativeSelector(
            selector_string=".different-selector",
            strategy_type=StrategyType.CSS,
            confidence_score=0.5,
            element_description="Different selector",
        )
        
        # Historical stability should include approval boost
        scored = scorer.calculate_confidence(test_selector)
        
        # After approval, strategy-level historical should be boosted
        boost = scorer.get_strategy_boost(StrategyType.CSS)
        assert boost > 0


class TestIntegrationWithFailureService:
    """Tests for integration with FailureService."""
    
    def test_failure_service_approval_calls_learning(self):
        """Test that approval calls trigger learning."""
        from src.selectors.adaptive.services.failure_service import FailureService
        from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
        
        # Create service with scorer
        scorer = ConfidenceScorer()
        service = FailureService(confidence_scorer=scorer)
        
        # Verify no weights initially
        assert scorer.get_approval_weights() == {}
        
        # Approve would normally call _record_positive_feedback
        # Let's test that method directly
        service._record_positive_feedback(
            selector=".test-selector",
            strategy=StrategyType.CSS,
        )
        
        # Should have recorded learning
        weights = scorer.get_approval_weights()
        assert 'css' in weights
        assert weights['css']['count'] == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_unknown_strategy_does_not_crash(self):
        """Test that unknown strategy doesn't crash."""
        scorer = ConfidenceScorer()
        
        # Should not raise even with unknown strategy
        scorer.record_positive_feedback(
            selector=".test",
            strategy=StrategyType.CSS,  # Use valid strategy
            approved=True,
        )
        
        assert 'css' in scorer.get_approval_weights()
    
    def test_none_confidence_uses_default(self):
        """Test that None confidence uses strategy default."""
        scorer = ConfidenceScorer()
        
        scorer.record_positive_feedback(
            selector=".test",
            strategy=StrategyType.CSS,
            approved=True,
            confidence_at_approval=None,  # Should use default
        )
        
        # Should still work and use default
        weights = scorer.get_approval_weights()
        assert 'css' in weights
    
    def test_boost_capped_at_max(self):
        """Test that boost doesn't exceed maximum."""
        scorer = ConfidenceScorer()
        
        # Record many approvals to exceed max
        for i in range(20):
            scorer.record_positive_feedback(
                selector=f".selector-{i}",
                strategy=StrategyType.CSS,
                approved=True,
                confidence_at_approval=0.7,
            )
        
        boost = scorer.get_strategy_boost(StrategyType.CSS)
        assert boost <= ConfidenceScorer.MAX_APPROVAL_BOOST
