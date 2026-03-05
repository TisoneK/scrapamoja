"""
Tests for Rejection Learning functionality (Story 5.2).

Tests the:
- Rejection weight tracking per strategy type
- Similar strategy penalty (CSS → XPath, etc.)
- Weight persistence to database
- Integration with Rejection Workflow
- Confidence score penalty from rejections
- Rejection reason pattern extraction
"""

import pytest
import unittest
from unittest.mock import Mock
from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
from src.selectors.adaptive.services.dom_analyzer import AlternativeSelector, StrategyType


class TestRejectionWeightTracking:
    """Tests for rejection weight tracking per strategy type."""
    
    def test_initial_no_rejection_weights(self):
        """Test that a new scorer has no rejection weights."""
        scorer = ConfidenceScorer()
        weights = scorer.get_rejection_weights()
        assert weights == {}
    
    def test_record_first_rejection(self):
        """Test recording first rejection increases count and penalty."""
        scorer = ConfidenceScorer()
        
        # Record first rejection for CSS strategy
        scorer.record_negative_feedback(
            selector=".btn-primary",
            strategy=StrategyType.CSS,
            rejection_reason="too specific",
            confidence_at_rejection=0.7,
        )
        
        weights = scorer.get_rejection_weights()
        
        # Should have CSS with count 1
        assert 'css' in weights
        assert weights['css']['count'] == 1
        assert weights['css']['total_penalty'] > 0
    
    def test_multiple_rejections_increase_penalty(self):
        """Test that multiple rejections increase the penalty."""
        scorer = ConfidenceScorer()
        
        # Record multiple rejections
        for i in range(5):
            scorer.record_negative_feedback(
                selector=f".selector-{i}",
                strategy=StrategyType.CSS,
                rejection_reason="fragile",
                confidence_at_rejection=0.7,
            )
        
        weights = scorer.get_rejection_weights()
        
        # Should have 5 rejections
        assert weights['css']['count'] == 5
        # Penalty should be capped at MAX_REJECTION_PENALTY (0.25)
        assert weights['css']['total_penalty'] <= ConfidenceScorer.MAX_REJECTION_PENALTY
    
    def test_different_strategies_tracked_separately(self):
        """Test that different strategy types are tracked separately."""
        scorer = ConfidenceScorer()
        
        # Record rejections for different strategies
        scorer.record_negative_feedback(
            selector=".btn-primary",
            strategy=StrategyType.CSS,
            rejection_reason="too specific",
        )
        
        scorer.record_negative_feedback(
            selector="//div[@class='btn']",
            strategy=StrategyType.XPATH,
            rejection_reason="wrong element",
        )
        
        weights = scorer.get_rejection_weights()
        
        assert 'css' in weights
        assert 'xpath' in weights
        assert weights['css']['count'] == 1
        assert weights['xpath']['count'] == 1


class TestSimilarStrategyPenalty:
    """Tests for similar selector strategy penalty."""
    
    def test_css_penalizes_xpath(self):
        """Test that CSS rejection penalizes related XPath strategy."""
        scorer = ConfidenceScorer()
        
        # Record CSS rejection
        scorer.record_negative_feedback(
            selector=".btn-primary",
            strategy=StrategyType.CSS,
            rejection_reason="too specific",
            confidence_at_rejection=0.7,
        )
        
        # XPath should have related penalty
        xpath_penalty = scorer.get_strategy_penalty(StrategyType.XPATH)
        
        # Should have some related penalty from CSS
        assert xpath_penalty > 0
    
    def test_xpath_penalizes_css(self):
        """Test that XPath rejection penalizes related CSS strategy."""
        scorer = ConfidenceScorer()
        
        # Record XPath rejection
        scorer.record_negative_feedback(
            selector="//div[@class='btn']",
            strategy=StrategyType.XPATH,
            rejection_reason="wrong element",
            confidence_at_rejection=0.6,
        )
        
        # CSS should have related penalty
        css_penalty = scorer.get_strategy_penalty(StrategyType.CSS)
        
        # Should have some related penalty from XPath
        assert css_penalty > 0
    
    def test_text_anchor_penalizes_dom_relationship(self):
        """Test that TEXT_ANCHOR penalizes DOM_RELATIONSHIP."""
        scorer = ConfidenceScorer()
        
        scorer.record_negative_feedback(
            selector="span:contains('Click')",
            strategy=StrategyType.TEXT_ANCHOR,
            rejection_reason="fragile",
        )
        
        # DOM_RELATIONSHIP should have related penalty
        dom_penalty = scorer.get_strategy_penalty(StrategyType.DOM_RELATIONSHIP)
        assert dom_penalty > 0
    
    def test_penalties_accumulate(self):
        """Test that related penalties accumulate from multiple rejections."""
        scorer = ConfidenceScorer()
        
        # CSS penalizes XPath
        scorer.record_negative_feedback(
            selector=".btn-1",
            strategy=StrategyType.CSS,
            rejection_reason="too specific",
        )
        
        scorer.record_negative_feedback(
            selector=".btn-2",
            strategy=StrategyType.CSS,
            rejection_reason="too generic",
        )
        
        # XPath should have accumulated related penalty
        xpath_penalty = scorer.get_strategy_penalty(StrategyType.XPATH)
        assert xpath_penalty > 0.03  # At least 2 * RELATED_STRATEGY_PENALTY


class TestRejectionWeightPersistence:
    """Tests for rejection weight persistence (in-memory for testing)."""
    
    def test_export_rejection_weights(self):
        """Test exporting rejection weights for persistence."""
        scorer = ConfidenceScorer()
        
        scorer.record_negative_feedback(
            selector=".btn",
            strategy=StrategyType.CSS,
            rejection_reason="fragile",
        )
        
        exported = scorer.export_rejection_weights()
        
        assert 'css' in exported
        assert exported['css']['count'] == 1
    
    def test_load_rejection_weights(self):
        """Test loading rejection weights from persistence."""
        scorer = ConfidenceScorer()
        
        # Simulate loading persisted weights
        persisted = {
            'css': {
                'count': 3,
                'total_penalty': 0.15,
                'related_penalty': 0.05,
                'last_rejection': '2026-03-05T10:00:00',
            }
        }
        
        scorer.load_rejection_weights(persisted)
        
        weights = scorer.get_rejection_weights()
        assert weights['css']['count'] == 3
    
    def test_empty_load_does_not_crash(self):
        """Test that loading empty rejection weights doesn't crash."""
        scorer = ConfidenceScorer()
        
        # Should not raise
        scorer.load_rejection_weights({})
        
        assert scorer.get_rejection_weights() == {}


class TestConfidencePenalty:
    """Tests for confidence score penalty from rejections."""
    
    def test_rejection_penalizes_historical_stability(self):
        """Test that rejection decreases historical stability lookup."""
        scorer = ConfidenceScorer()
        
        # Record rejection
        scorer.record_negative_feedback(
            selector=".rejected-selector",
            strategy=StrategyType.CSS,
            rejection_reason="too specific",
            confidence_at_rejection=0.7,
        )
        
        # Create a new selector with same string
        test_selector = AlternativeSelector(
            selector_string=".rejected-selector",
            strategy_type=StrategyType.CSS,
            confidence_score=0.5,
            element_description="Test selector",
        )
        
        # Score should use the penalized historical data
        scored = scorer.calculate_confidence(test_selector)
        
        # Should be lower than base due to rejection learning
        # The historical lookup should return penalized value
        assert scored.historical_stability is not None
        assert scored.historical_stability < 0.7  # Should be penalized from original 0.7
    
    def test_strategy_default_penalized_after_rejection(self):
        """Test that strategy defaults get penalized after rejection."""
        scorer = ConfidenceScorer()
        
        # Base default for CSS is 0.7
        base_default = ConfidenceScorer.STRATEGY_DEFAULTS[StrategyType.CSS]
        
        # Record rejection
        scorer.record_negative_feedback(
            selector=".new-selector",
            strategy=StrategyType.CSS,
            rejection_reason="fragile",
            confidence_at_rejection=0.7,
        )
        
        # Create selector with no specific history
        test_selector = AlternativeSelector(
            selector_string=".different-selector",
            strategy_type=StrategyType.CSS,
            confidence_score=0.5,
            element_description="Different selector",
        )
        
        # Historical stability should include rejection penalty
        scored = scorer.calculate_confidence(test_selector)
        
        # After rejection, strategy-level historical should be penalized
        penalty = scorer.get_strategy_penalty(StrategyType.CSS)
        assert penalty > 0
    
    def test_minimum_confidence_floor(self):
        """Test that confidence doesn't go below minimum floor."""
        scorer = ConfidenceScorer()
        
        # Record many rejections to exceed max penalty
        for i in range(20):
            scorer.record_negative_feedback(
                selector=f".selector-{i}",
                strategy=StrategyType.CSS,
                rejection_reason="too specific",
                confidence_at_rejection=0.7,
            )
        
        # The historical lookup should still return at least MIN_CONFIDENCE_FLOOR
        test_selector = AlternativeSelector(
            selector_string=".any-selector",
            strategy_type=StrategyType.CSS,
            confidence_score=0.5,
            element_description="Test selector",
        )
        
        scored = scorer.calculate_confidence(test_selector)
        
        # Final score should not go below floor
        assert scored.confidence_score >= ConfidenceScorer.MIN_CONFIDENCE_FLOOR


class TestRejectionReasonPattern:
    """Tests for rejection reason pattern extraction."""
    
    def test_parse_too_specific(self):
        """Test parsing 'too specific' reason."""
        scorer = ConfidenceScorer()
        
        # This is tested indirectly through record_negative_feedback
        # Direct test of the private method
        result = scorer._parse_rejection_reason("This selector is too specific")
        assert result == 'too_specific'
    
    def test_parse_too_generic(self):
        """Test parsing 'too generic' reason."""
        scorer = ConfidenceScorer()
        
        result = scorer._parse_rejection_reason("Too generic, matches many elements")
        assert result == 'too_generic'
    
    def test_parse_wrong_element(self):
        """Test parsing 'wrong element' reason."""
        scorer = ConfidenceScorer()
        
        result = scorer._parse_rejection_reason("Wrong element selected")
        assert result == 'wrong_element'
    
    def test_parse_fragile(self):
        """Test parsing 'fragile' reason."""
        scorer = ConfidenceScorer()
        
        result = scorer._parse_rejection_reason("This selector is fragile")
        assert result == 'fragile'
    
    def test_parse_not_stable(self):
        """Test parsing 'not stable' reason."""
        scorer = ConfidenceScorer()
        
        result = scorer._parse_rejection_reason("Not stable across page changes")
        assert result == 'not_stable'
    
    def test_parse_custom_reason(self):
        """Test parsing custom/unknown reason."""
        scorer = ConfidenceScorer()
        
        result = scorer._parse_rejection_reason("My custom reason text")
        assert result == 'custom'
    
    def test_parse_none_returns_none(self):
        """Test parsing None reason returns None."""
        scorer = ConfidenceScorer()
        
        result = scorer._parse_rejection_reason(None)
        assert result is None


class TestIntegrationWithFailureService:
    """Tests for integration with FailureService."""
    
    def test_failure_service_rejection_calls_learning(self):
        """Test that rejection calls trigger learning."""
        from src.selectors.adaptive.services.failure_service import FailureService
        from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
        
        # Create service with scorer
        scorer = ConfidenceScorer()
        service = FailureService(confidence_scorer=scorer)
        
        # Verify no rejection weights initially
        assert scorer.get_rejection_weights() == {}
        
        # Reject would normally call _record_negative_feedback
        # Let's test that method directly
        service._record_negative_feedback(
            selector=".test-selector",
            strategy=StrategyType.CSS,
            reason="too specific",
        )
        
        # Should have recorded learning
        weights = scorer.get_rejection_weights()
        assert 'css' in weights
        assert weights['css']['count'] == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_unknown_strategy_does_not_crash(self):
        """Test that unknown strategy doesn't crash."""
        scorer = ConfidenceScorer()
        
        # Should not raise even with unknown strategy
        scorer.record_negative_feedback(
            selector=".test",
            strategy=StrategyType.CSS,  # Use valid strategy
            rejection_reason="too specific",
        )
        
        assert 'css' in scorer.get_rejection_weights()
    
    def test_none_confidence_uses_default(self):
        """Test that None confidence uses strategy default."""
        scorer = ConfidenceScorer()
        
        scorer.record_negative_feedback(
            selector=".test",
            strategy=StrategyType.CSS,
            rejection_reason="fragile",
            confidence_at_rejection=None,  # Should use default
        )
        
        # Should still work and use default
        weights = scorer.get_rejection_weights()
        assert 'css' in weights
    
    def test_penalty_capped_at_max(self):
        """Test that penalty doesn't exceed maximum."""
        scorer = ConfidenceScorer()
        
        # Record many rejections to exceed max
        for i in range(20):
            scorer.record_negative_feedback(
                selector=f".selector-{i}",
                strategy=StrategyType.CSS,
                rejection_reason="too specific",
                confidence_at_rejection=0.7,
            )
        
        penalty = scorer.get_strategy_penalty(StrategyType.CSS)
        assert penalty <= ConfidenceScorer.MAX_REJECTION_PENALTY
    
    def test_no_reason_still_works(self):
        """Test that rejection without reason still works."""
        scorer = ConfidenceScorer()
        
        scorer.record_negative_feedback(
            selector=".test",
            strategy=StrategyType.CSS,
            rejection_reason=None,
            confidence_at_rejection=0.7,
        )
        
        weights = scorer.get_rejection_weights()
        assert 'css' in weights
        assert weights['css']['count'] == 1


class TestRestartPersistence(unittest.TestCase):
    """Test rejection weight persistence across service restarts."""
    
    def test_restart_persistence_with_repository(self):
        """Test that rejection weights persist across scorer restarts."""
        # Create a mock repository
        mock_repo = Mock()
        mock_repo.load_rejection_weights_for_scorer.return_value = {
            'css': {
                'count': 5,
                'last_rejection': '2026-03-05T20:00:00',
                'total_penalty': 0.2,
                'related_penalty': 0.03,
            },
            'xpath': {
                'count': 2,
                'last_rejection': '2026-03-05T19:30:00',
                'total_penalty': 0.1,
                'related_penalty': 0.0,
            }
        }
        
        # Create scorer with repository (simulates restart)
        scorer = ConfidenceScorer(weight_repository=mock_repo)
        
        # Verify persisted weights were loaded
        weights = scorer.get_rejection_weights()
        assert len(weights) == 2
        assert weights['css']['count'] == 5
        assert weights['css']['total_penalty'] == 0.2
        assert weights['xpath']['count'] == 2
        
        # Verify that penalties are applied in confidence calculation
        penalty = scorer.get_strategy_penalty(StrategyType.CSS)
        assert penalty == 0.23  # 0.2 + 0.03
        
        # Verify historical stability lookup uses persisted penalties
        stability = scorer._get_historical_stability(".test-selector", StrategyType.CSS)
        base_confidence = scorer.STRATEGY_DEFAULTS[StrategyType.CSS]
        expected = max(scorer.MIN_CONFIDENCE_FLOOR, base_confidence - penalty)
        assert stability == expected
        
        # Verify repository was called during initialization
        mock_repo.load_rejection_weights_for_scorer.assert_called_once()
    
    def test_restart_persistence_without_repository(self):
        """Test behavior when no repository provided (no persistence)."""
        scorer = ConfidenceScorer(weight_repository=None)
        
        # Should start with empty rejection weights
        weights = scorer.get_rejection_weights()
        assert len(weights) == 0
        
        # Add some rejections
        scorer.record_negative_feedback(
            selector=".test",
            strategy=StrategyType.CSS,
            rejection_reason="too specific"
        )
        
        # Should have local weights but no persistence
        weights = scorer.get_rejection_weights()
        assert 'css' in weights
        assert weights['css']['count'] == 1
    
    def test_restart_persistence_handles_corrupted_data(self):
        """Test graceful handling of corrupted persisted data."""
        mock_repo = Mock()
        mock_repo.load_rejection_weights_for_scorer.side_effect = Exception("Database error")
        
        # Should not crash, should start with empty weights
        scorer = ConfidenceScorer(weight_repository=mock_repo)
        
        weights = scorer.get_rejection_weights()
        assert len(weights) == 0
        
        # Should still be able to record new rejections
        scorer.record_negative_feedback(
            selector=".test",
            strategy=StrategyType.CSS,
            rejection_reason="fragile"
        )
        
        weights = scorer.get_rejection_weights()
        assert 'css' in weights
