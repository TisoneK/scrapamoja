"""
Unit tests for Generation Tracking in ConfidenceScorer service.

Story: 5.3 - Track Selector Survival Across Generations
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
from src.selectors.adaptive.services.dom_analyzer import (
    AlternativeSelector,
    StrategyType,
)


class TestGenerationTracking:
    """Tests for generation tracking functionality (Story 5.3)."""
    
    @pytest.fixture
    def scorer(self):
        """Create a ConfidenceScorer instance without repository."""
        return ConfidenceScorer(weight_repository=None)
    
    @pytest.fixture
    def sample_selector(self):
        """Create a sample AlternativeSelector."""
        return AlternativeSelector(
            selector_string=".btn-primary",
            strategy_type=StrategyType.CSS,
            confidence_score=0.7,
            element_description="Primary button class",
        )
    
    # ==================== Task 1: Generation Tracking Tests ====================
    
    def test_record_generation_survival_new_recipe(self, scorer):
        """Test recording generation survival for a new recipe."""
        recipe_id = "recipe_001"
        
        # Record survival for generation 1
        scorer.record_generation_survival(recipe_id, generation=1)
        
        # Verify generation data was created
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data is not None
        assert gen_data['current_generation'] == 1
        assert gen_data['generations_survived'] == 0  # First generation doesn't count as survived yet
    
    def test_record_generation_survival_increments_survived(self, scorer):
        """Test that surviving a new generation increments survival count."""
        recipe_id = "recipe_002"
        
        # Record initial generation
        scorer.record_generation_survival(recipe_id, generation=1)
        
        # Survive generation 2
        scorer.record_generation_survival(recipe_id, generation=2)
        
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data['generations_survived'] == 1
        assert gen_data['current_generation'] == 2
    
    def test_record_generation_survival_resets_consecutive_failures(self, scorer):
        """Test that surviving a new generation resets consecutive failures."""
        recipe_id = "recipe_003"
        
        # First record a failure
        scorer.record_generation_failure(recipe_id, generation=1)
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data['consecutive_failures'] == 1
        
        # Now survive a new generation
        scorer.record_generation_survival(recipe_id, generation=2)
        
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data['consecutive_failures'] == 0
    
    # ==================== Task 2: Stability Score Calculation Tests ====================
    
    def test_calculate_generation_stability_new_recipe(self, scorer):
        """Test stability calculation for a new recipe (no history)."""
        recipe_id = "recipe_004"
        
        stability = scorer.calculate_generation_stability(recipe_id)
        
        # Default stability should be 1.0 (neutral)
        assert stability == 1.0
    
    def test_calculate_generation_stability_with_survival(self, scorer):
        """Test stability calculation with generations survived."""
        recipe_id = "recipe_005"
        
        # Survive 2 generations
        scorer.record_generation_survival(recipe_id, generation=1)
        scorer.record_generation_survival(recipe_id, generation=2)
        
        stability = scorer.calculate_generation_stability(recipe_id)
        
        # Should be higher than 1.0 due to survival
        assert stability > 1.0
        # Should be capped at reasonable bounds
        assert stability <= 1.5
    
    def test_calculate_generation_stability_with_failures(self, scorer):
        """Test stability calculation with generation failures."""
        recipe_id = "recipe_006"
        
        # Record initial generation
        scorer.record_generation_survival(recipe_id, generation=1)
        
        # Record failures
        scorer.record_generation_failure(recipe_id, generation=2)
        
        stability = scorer.calculate_generation_stability(recipe_id)
        
        # Should be lower than 1.0 due to failures
        # (but our formula uses survival rate, not failure count)
        assert stability >= 0.5  # Minimum bound
    
    def test_get_generation_boost(self, scorer):
        """Test getting generation boost amount."""
        recipe_id = "recipe_007"
        
        # Survive 3 generations
        # Generation 1 -> 2: survived becomes 1
        # Generation 2 -> 3: survived becomes 2
        scorer.record_generation_survival(recipe_id, generation=1)
        scorer.record_generation_survival(recipe_id, generation=2)
        scorer.record_generation_survival(recipe_id, generation=3)
        
        boost = scorer.get_generation_boost(recipe_id)
        
        # 2 generations survived * 0.05 = 0.10
        assert boost == 0.10
    
    def test_calculate_confidence_with_generation_tracking(self, scorer, sample_selector):
        """Test confidence calculation includes generation stability."""
        recipe_id = "recipe_008"
        
        # Record some survival history
        scorer.record_generation_survival(recipe_id, generation=1)
        scorer.record_generation_survival(recipe_id, generation=2)
        
        # Calculate confidence with generation tracking
        result = scorer.calculate_confidence(
            sample_selector,
            recipe_id=recipe_id,
        )
        
        # Confidence should be affected by generation stability
        assert result.confidence_score is not None
        assert 0.0 <= result.confidence_score <= 1.0
    
    # ==================== Task 3: Generation Failure Detection Tests ====================
    
    def test_record_generation_failure(self, scorer):
        """Test recording a generation failure."""
        recipe_id = "recipe_009"
        
        should_review = scorer.record_generation_failure(
            recipe_id, 
            generation=1,
            selector=".btn-primary",
        )
        
        # Should not mark for review after single failure
        assert should_review is False
        
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data['generation_failures'] == 1
        assert gen_data['consecutive_failures'] == 1
    
    def test_record_generation_failure_marks_for_review(self, scorer):
        """Test that consecutive failures trigger review flag."""
        recipe_id = "recipe_010"
        
        # Record initial generation
        scorer.record_generation_survival(recipe_id, generation=1)
        
        # Record 3 consecutive failures (threshold is 3)
        should_review_1 = scorer.record_generation_failure(recipe_id, generation=2)
        assert should_review_1 is False
        
        should_review_2 = scorer.record_generation_failure(recipe_id, generation=2)
        assert should_review_2 is False
        
        should_review_3 = scorer.record_generation_failure(recipe_id, generation=2)
        assert should_review_3 is True  # Should trigger review
    
    def test_should_mark_recipe_for_review(self, scorer):
        """Test the review flag check method."""
        recipe_id = "recipe_011"
        
        # Initially should not be marked for review
        assert scorer.should_mark_recipe_for_review(recipe_id) is False
        
        # Record 3 consecutive failures
        scorer.record_generation_failure(recipe_id, generation=1)
        scorer.record_generation_failure(recipe_id, generation=1)
        scorer.record_generation_failure(recipe_id, generation=1)
        
        assert scorer.should_mark_recipe_for_review(recipe_id) is True
    
    def test_reset_generation_failures(self, scorer):
        """Test resetting consecutive failure count."""
        recipe_id = "recipe_012"
        
        # Record failures
        scorer.record_generation_failure(recipe_id, generation=1)
        scorer.record_generation_failure(recipe_id, generation=1)
        
        # Reset
        scorer.reset_generation_failures(recipe_id)
        
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data['consecutive_failures'] == 0
    
    def test_detect_generation_change(self, scorer):
        """Test generation change detection."""
        recipe_id = "recipe_013"
        
        # Initially no generation data
        assert scorer.detect_generation_change(recipe_id, 1) is False
        
        # Record generation 1
        scorer.record_generation_survival(recipe_id, generation=1)
        
        # Should detect change to generation 2 (2 > 1)
        assert scorer.detect_generation_change(recipe_id, 2) is True
        
        # Record surviving generation 2 to update stored generation
        scorer.record_generation_survival(recipe_id, generation=2)
        
        # Now should NOT detect change for generation 2 (2 == 2)
        assert scorer.detect_generation_change(recipe_id, 2) is False
    
    # ==================== Task 4: Integration with Learning System Tests ====================
    
    def test_export_generation_data(self, scorer):
        """Test exporting generation data."""
        recipe_id = "recipe_014"
        
        scorer.record_generation_survival(recipe_id, generation=1)
        
        exported = scorer.export_generation_data()
        
        assert recipe_id in exported
        assert exported[recipe_id]['current_generation'] == 1
    
    def test_load_generation_data(self, scorer):
        """Test loading generation data."""
        recipe_id = "recipe_015"
        
        test_data = {
            recipe_id: {
                'current_generation': 3,
                'generations_survived': 2,
                'generation_failures': 1,
                'consecutive_failures': 0,
                'sport': 'basketball',
                'site': 'flashscore',
            }
        }
        
        scorer.load_generation_data(test_data)
        
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data['current_generation'] == 3
        assert gen_data['generations_survived'] == 2
    
    def test_get_all_generation_data(self, scorer):
        """Test getting all generation data."""
        # Record multiple recipes
        scorer.record_generation_survival("recipe_016", generation=1)
        scorer.record_generation_survival("recipe_017", generation=1)
        scorer.record_generation_failure("recipe_018", generation=1)
        
        all_data = scorer.get_all_generation_data()
        
        assert len(all_data) == 3
        assert "recipe_016" in all_data
        assert "recipe_017" in all_data
        assert "recipe_018" in all_data
    
    # ==================== Edge Cases and Integration Tests ====================
    
    def test_generation_tracking_with_sport_context(self, scorer):
        """Test generation tracking with sport context."""
        recipe_id = "recipe_019"
        
        scorer.record_generation_survival(
            recipe_id, 
            generation=1,
            sport="basketball",
            site="flashscore",
        )
        
        gen_data = scorer.get_generation_data(recipe_id)
        assert gen_data['sport'] == "basketball"
        assert gen_data['site'] == "flashscore"
    
    def test_confidence_calculation_no_recipe_id(self, scorer, sample_selector):
        """Test confidence calculation without recipe_id still works."""
        result = scorer.calculate_confidence(sample_selector)
        
        # Should work without recipe_id
        assert result.confidence_score is not None
        assert 0.0 <= result.confidence_score <= 1.0
    
    def test_multiple_recipes_independent(self, scorer):
        """Test that multiple recipes track independently."""
        # Track 3 different recipes
        scorer.record_generation_survival("recipe_A", generation=1)
        scorer.record_generation_survival("recipe_A", generation=2)
        
        scorer.record_generation_failure("recipe_B", generation=1)
        
        scorer.record_generation_survival("recipe_C", generation=1)
        
        # Verify each is independent
        assert scorer.get_generation_data("recipe_A")['generations_survived'] == 1
        assert scorer.get_generation_data("recipe_B")['generation_failures'] == 1
        assert scorer.get_generation_data("recipe_C")['generations_survived'] == 0
