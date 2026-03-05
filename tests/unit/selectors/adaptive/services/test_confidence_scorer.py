"""
Unit tests for ConfidenceScorer service.

Story: 3.2 - Generate Confidence Scores
Story: 5.1 - Learn from Approvals
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.selectors.adaptive.services.confidence_scorer import (
    ConfidenceScorer,
    ConfidenceTier,
    ScoringBreakdown,
)
from src.selectors.adaptive.services.dom_analyzer import (
    AlternativeSelector,
    StrategyType,
)


class TestConfidenceTier:
    """Tests for ConfidenceTier enum."""
    
    def test_from_score_high(self):
        """Test tier conversion for high scores (0.7-1.0)."""
        assert ConfidenceTier.from_score(0.7) == ConfidenceTier.HIGH
        assert ConfidenceTier.from_score(0.85) == ConfidenceTier.HIGH
        assert ConfidenceTier.from_score(1.0) == ConfidenceTier.HIGH
    
    def test_from_score_medium(self):
        """Test tier conversion for medium scores (0.4-0.69)."""
        assert ConfidenceTier.from_score(0.4) == ConfidenceTier.MEDIUM
        assert ConfidenceTier.from_score(0.55) == ConfidenceTier.MEDIUM
        assert ConfidenceTier.from_score(0.69) == ConfidenceTier.MEDIUM
    
    def test_from_score_low(self):
        """Test tier conversion for low scores (0.0-0.39)."""
        assert ConfidenceTier.from_score(0.0) == ConfidenceTier.LOW
        assert ConfidenceTier.from_score(0.2) == ConfidenceTier.LOW
        assert ConfidenceTier.from_score(0.39) == ConfidenceTier.LOW


class TestScoringBreakdown:
    """Tests for ScoringBreakdown dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        breakdown = ScoringBreakdown(
            historical_stability=0.8,
            specificity_score=0.7,
            dom_similarity=0.6,
            final_score=0.7,
        )
        result = breakdown.to_dict()
        
        assert result["historical_stability"] == 0.8
        assert result["specificity_score"] == 0.7
        assert result["dom_similarity"] == 0.6
        assert result["final_score"] == 0.7


class TestConfidenceScorer:
    """Tests for ConfidenceScorer service."""
    
    @pytest.fixture
    def scorer(self):
        """Create a ConfidenceScorer instance."""
        return ConfidenceScorer()
    
    @pytest.fixture
    def sample_selector(self):
        """Create a sample AlternativeSelector."""
        return AlternativeSelector(
            selector_string=".btn-primary",
            strategy_type=StrategyType.CSS,
            confidence_score=0.7,
            element_description="Primary button class",
        )
    
    def test_init_default_weights(self, scorer):
        """Test initialization with default weights."""
        assert scorer.WEIGHTS['historical_stability'] == 0.4
        assert scorer.WEIGHTS['specificity'] == 0.35
        assert scorer.WEIGHTS['dom_similarity'] == 0.25
    
    def test_init_custom_weights(self):
        """Test initialization with custom weights."""
        scorer = ConfidenceScorer(
            weight=0.5,
            specificity_weight=0.3,
            dom_similarity_weight=0.2,
        )
        
        assert scorer.WEIGHTS['historical_stability'] == 0.5
        assert scorer.WEIGHTS['specificity'] == 0.3
        assert scorer.WEIGHTS['dom_similarity'] == 0.2
    
    def test_calculate_specificity_id_selector(self, scorer):
        """Test specificity calculation for ID selectors."""
        # Single ID - highest specificity
        assert scorer._calculate_specificity("#main-content") == 0.9
        
        # Multiple IDs - very specific
        assert scorer._calculate_specificity("#nav #logo") == 0.95
    
    def test_calculate_specificity_class_selector(self, scorer):
        """Test specificity calculation for class selectors."""
        # Single class
        assert scorer._calculate_specificity(".btn") == 0.65  # 0.6 + 0.05 for 1 class
        
        # Multiple classes
        assert scorer._calculate_specificity(".btn.primary.large") == 0.75
        
        # Should not exceed 0.8
        assert scorer._calculate_specificity(".a.b.c.d.e") == 0.8
    
    def test_calculate_specificity_attribute_selector(self, scorer):
        """Test specificity calculation for attribute selectors."""
        assert scorer._calculate_specificity("[data-testid='test']") == 0.6
        assert scorer._calculate_specificity("[name='email']") == 0.6
    
    def test_calculate_specificity_tag_class_combo(self, scorer):
        """Test specificity for tag + class combinations (with space)."""
        # Note: "div.container" (no space) is treated as class-based
        # Only selectors with spaces are considered tag+class combos
        assert scorer._calculate_specificity("div .container") == 0.5
        assert scorer._calculate_specificity("span .highlight") == 0.5
    
    def test_calculate_specificity_tag_only(self, scorer):
        """Test specificity for tag-only selectors."""
        assert scorer._calculate_specificity("div") == 0.3
        assert scorer._calculate_specificity("span") == 0.3
        assert scorer._calculate_specificity("a") == 0.3
    
    def test_calculate_specificity_empty(self, scorer):
        """Test specificity for empty selectors."""
        assert scorer._calculate_specificity("") == 0.3
        assert scorer._calculate_specificity("   ") == 0.3
    
    def test_get_historical_stability_default(self, scorer):
        """Test historical stability with default strategy."""
        # Should return strategy default
        stability = scorer._get_historical_stability(
            ".btn",
            StrategyType.CSS,
            None,
        )
        
        assert stability == 0.7  # CSS default
    
    def test_get_historical_stability_cached(self, scorer):
        """Test historical stability with cached data."""
        # Add historical data
        scorer.add_historical_data(".btn", 0.9, "football")
        
        # Should return cached value
        stability = scorer._get_historical_stability(
            ".btn",
            StrategyType.CSS,
            "football",
        )
        
        assert stability == 0.9
    
    def test_get_historical_stability_different_sports(self, scorer):
        """Test historical stability is sport-specific."""
        # Add historical data for one sport
        scorer.add_historical_data(".btn", 0.9, "football")
        
        # Different sport should use default
        stability = scorer._get_historical_stability(
            ".btn",
            StrategyType.CSS,
            "basketball",
        )
        
        assert stability == 0.7  # Default, not cached
    
    def test_calculate_confidence_with_selector(self, scorer, sample_selector):
        """Test confidence calculation with a sample selector."""
        result = scorer.calculate_confidence(sample_selector)
        
        # Should return an AlternativeSelector
        assert isinstance(result, AlternativeSelector)
        
        # Should have confidence score in valid range
        assert 0.0 <= result.confidence_score <= 1.0

    def test_calculate_confidence_score_range(self, scorer):
        """Test that confidence scores are always in valid range."""
        test_cases = [
            AlternativeSelector("#id", StrategyType.CSS, 0.5, "test"),
            AlternativeSelector(".class", StrategyType.CSS, 0.5, "test"),
            AlternativeSelector("div", StrategyType.CSS, 0.5, "test"),
            AlternativeSelector("[data-test]", StrategyType.ATTRIBUTE_MATCH, 0.5, "test"),
        ]
        
        for selector in test_cases:
            result = scorer.calculate_confidence(selector)
            assert 0.0 <= result.confidence_score <= 1.0


class TestApprovalLearning:
    """Tests for approval learning functionality (Story 5.1)."""
    
    @pytest.fixture
    def scorer(self):
        """Create a ConfidenceScorer instance for testing."""
        return ConfidenceScorer()
    
    def test_record_positive_feedback_basic(self, scorer):
        """Test basic positive feedback recording."""
        selector = "#test-button"
        strategy = StrategyType.CSS
        
        # Record approval
        scorer.record_positive_feedback(selector, strategy, approved=True)
        
        # Check approval weights were updated
        weights = scorer.get_approval_weights()
        assert strategy.value in weights
        assert weights[strategy.value]['count'] == 1
        assert weights[strategy.value]['total_boost'] > 0
    
    def test_record_positive_feedback_applies_boost(self, scorer):
        """Test that approval feedback actually boosts confidence scores."""
        selector = ".boosted-class"
        strategy = StrategyType.CSS
        
        # Get baseline confidence (should be strategy default)
        baseline = scorer._get_historical_stability(selector, strategy)
        assert baseline == scorer.STRATEGY_DEFAULTS[strategy]  # 0.7 for CSS
        
        # Record approval
        scorer.record_positive_feedback(selector, strategy, approved=True)
        
        # Check confidence is now boosted
        boosted = scorer._get_historical_stability(selector, strategy)
        assert boosted > baseline
        assert boosted <= 1.0
    
    def test_related_strategy_boost(self, scorer):
        """Test that related strategies get boosted when one is approved."""
        # Approve a CSS selector
        css_selector = "#main-content"
        scorer.record_positive_feedback(css_selector, StrategyType.CSS, approved=True)
        
        # Check that related XPath strategy got a boost
        xpath_boost = scorer.get_strategy_boost(StrategyType.XPATH)
        assert xpath_boost > 0
        
        # Check that related Attribute Match strategy got a boost
        attr_boost = scorer.get_strategy_boost(StrategyType.ATTRIBUTE_MATCH)
        assert attr_boost > 0
    
    def test_multiple_approvals_accumulate(self, scorer):
        """Test that multiple approvals accumulate boosts up to the cap."""
        selector = ".repeatedly-approved"
        strategy = StrategyType.CSS
        
        # Record multiple approvals
        for i in range(10):  # More than enough to hit the cap
            scorer.record_positive_feedback(f"{selector}-{i}", strategy, approved=True)
        
        # Check boost is capped at MAX_APPROVAL_BOOST
        boost = scorer.get_strategy_boost(strategy)
        assert boost <= scorer.MAX_APPROVAL_BOOST
        assert boost > 0
    
    def test_approval_persists_to_historical_data(self, scorer):
        """Test that approval affects historical data cache."""
        selector = "#persistent-boost"
        strategy = StrategyType.CSS
        
        # Record approval
        scorer.record_positive_feedback(selector, strategy, approved=True)
        
        # Check that historical data cache contains the boosted value
        approval_key = f"approval:{selector}"
        assert approval_key in scorer._historical_data
        cached_value = scorer._historical_data[approval_key]
        assert cached_value > scorer.STRATEGY_DEFAULTS[strategy]
    
    def test_strategy_boost_in_confidence_calculation(self, scorer):
        """Test that strategy boosts are applied in full confidence calculation."""
        selector = ".tested-class"
        strategy = StrategyType.CSS
        
        # Record approval to create boost
        scorer.record_positive_feedback(selector, strategy, approved=True)
        
        # Calculate full confidence score
        alt_selector = AlternativeSelector(
            selector_string=selector,
            strategy_type=strategy,
            confidence_score=0.5,
            element_description="test",
        )
        
        result = scorer.calculate_confidence(alt_selector)
        
        # Historical stability should be boosted
        assert result.historical_stability > scorer.STRATEGY_DEFAULTS[strategy]
        
        # Final score should reflect the boost (but may be affected by specificity)
        assert result.confidence_score > 0.65  # Should be above baseline considering all factors
    
    def test_related_strategy_relationships(self, scorer):
        """Test all strategy relationships work correctly."""
        # Test CSS relationships
        scorer.record_positive_feedback("#test", StrategyType.CSS, approved=True)
        
        # CSS should boost XPath and Attribute Match
        assert scorer.get_strategy_boost(StrategyType.XPATH) > 0
        assert scorer.get_strategy_boost(StrategyType.ATTRIBUTE_MATCH) > 0
        
        # Test TEXT_ANCHOR relationships  
        scorer.record_positive_feedback("text='Test'", StrategyType.TEXT_ANCHOR, approved=True)
        
        # TEXT_ANCHOR should boost DOM_RELATIONSHIP and ROLE_BASED
        assert scorer.get_strategy_boost(StrategyType.DOM_RELATIONSHIP) > 0
        assert scorer.get_strategy_boost(StrategyType.ROLE_BASED) > 0
    
    def test_approval_with_confidence_at_time(self, scorer):
        """Test approval recording with confidence at approval time."""
        selector = "#with-confidence"
        strategy = StrategyType.CSS
        confidence_at_approval = 0.6
        
        scorer.record_positive_feedback(
            selector, 
            strategy, 
            approved=True, 
            confidence_at_approval=confidence_at_approval
        )
        
        # Check the approval was recorded with the confidence
        approval_key = f"approval:{selector}"
        assert approval_key in scorer._historical_data
        
        # The cached value should be boosted from the original confidence
        cached_value = scorer._historical_data[approval_key]
        assert cached_value > confidence_at_approval
    
    def test_no_boost_without_approval(self, scorer):
        """Test that no boost is applied without approval."""
        selector = "#no-approval"
        strategy = StrategyType.CSS
        
        # Don't record any approval
        
        # Check confidence is still default
        confidence = scorer._get_historical_stability(selector, strategy)
        assert confidence == scorer.STRATEGY_DEFAULTS[strategy]
        
        # Check strategy boost is zero
        boost = scorer.get_strategy_boost(strategy)
        assert boost == 0.0


class TestRejectionLearning:
    """Tests for rejection learning functionality (Story 5.2)."""
    
    @pytest.fixture
    def scorer(self):
        """Create a ConfidenceScorer instance for testing."""
        return ConfidenceScorer()
    
    def test_record_negative_feedback_basic(self, scorer):
        """Test basic negative feedback recording."""
        selector = ".bad-selector"
        strategy = StrategyType.CSS
        reason = "too_specific"
        
        # Record rejection
        scorer.record_negative_feedback(selector, strategy, rejection_reason=reason)
        
        # Check rejection weights were updated
        weights = scorer.get_rejection_weights()
        assert strategy.value in weights
        assert weights[strategy.value]['count'] == 1
        assert weights[strategy.value]['total_penalty'] > 0
    
    def test_rejection_applies_penalty(self, scorer):
        """Test that rejection feedback actually penalizes confidence scores."""
        selector = ".penalized-class"
        strategy = StrategyType.CSS
        
        # Get baseline confidence
        baseline = scorer._get_historical_stability(selector, strategy)
        
        # Record rejection
        scorer.record_negative_feedback(selector, strategy, rejection_reason="too_specific")
        
        # Check confidence is now penalized
        penalized = scorer._get_historical_stability(selector, strategy)
        assert penalized < baseline
        assert penalized >= scorer.MIN_CONFIDENCE_FLOOR
    
    def test_strategy_penalty_calculation(self, scorer):
        """Test strategy penalty calculation."""
        strategy = StrategyType.CSS
        
        # Record multiple rejections
        for i in range(5):
            scorer.record_negative_feedback(f".bad-{i}", strategy, rejection_reason="wrong_element")
        
        # Check penalty is calculated correctly
        penalty = scorer.get_strategy_penalty(strategy)
        assert penalty > 0
        assert penalty <= scorer.MAX_REJECTION_PENALTY
    
    def test_calculate_confidence_different_strategies(self, scorer):
        """Test confidence calculation for different strategy types."""
        strategies = [
            ("#id", StrategyType.CSS),
            (".class", StrategyType.CSS),
            ("//div", StrategyType.XPATH),
            ("//*[text()='test']", StrategyType.TEXT_ANCHOR),
            ("[data-testid]", StrategyType.ATTRIBUTE_MATCH),
            ("parent > child", StrategyType.DOM_RELATIONSHIP),
            ("[role='button']", StrategyType.ROLE_BASED),
        ]
        
        for selector_str, strategy in strategies:
            selector = AlternativeSelector(
                selector_string=selector_str,
                strategy_type=strategy,
                confidence_score=0.5,
                element_description="test",
            )
            result = scorer.calculate_confidence(selector)
            
            assert 0.0 <= result.confidence_score <= 1.0
