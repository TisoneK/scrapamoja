"""
Failing unit tests for confidence scoring system.

These tests are written first (Test-First Validation) and must fail
before implementation. They will pass once the confidence scoring system
is properly implemented according to the specification.
"""

import pytest
from datetime import datetime

from src.models.selector_models import (
    SelectorResult, ElementInfo, ValidationResult, ValidationType,
    StrategyPattern, StrategyType
)
from src.selectors import ConfidenceScorer
from src.utils.exceptions import ValidationError


class TestConfidenceScorer:
    """Test cases for confidence scoring algorithms."""
    
    def test_calculate_confidence_perfect_match(self):
        """Test confidence calculation for a perfect match."""
        scorer = ConfidenceScorer()
        
        # Create perfect result
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name home"},
            css_classes=["team-name", "home"],
            dom_path="body.div.match-header.span.team-name",
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,  # Will be calculated
            resolution_time=50.0,
            validation_results=[
                ValidationResult(
                    rule_type="regex",
                    passed=True,
                    score=1.0,
                    message="Text matches expected pattern"
                ),
                ValidationResult(
                    rule_type="semantic",
                    passed=True,
                    score=1.0,
                    message="Content has semantic meaning"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should have high confidence for perfect match
        assert confidence > 0.9
        assert confidence <= 1.0
    
    def test_calculate_confidence_partial_match(self):
        """Test confidence calculation for a partial match."""
        scorer = ConfidenceScorer()
        
        # Create partial result with some issues
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester",  # Incomplete team name
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.div.match-header.span.team-name",
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=75.0,
            validation_results=[
                ValidationResult(
                    rule_type="regex",
                    passed=False,
                    score=0.6,
                    message="Text incomplete"
                ),
                ValidationResult(
                    rule_type="semantic",
                    passed=True,
                    score=0.8,
                    message="Partial semantic meaning"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should have medium confidence for partial match
        assert 0.6 < confidence < 0.8
    
    def test_calculate_confidence_poor_match(self):
        """Test confidence calculation for a poor match."""
        scorer = ConfidenceScorer()
        
        # Create poor result with many issues
        element_info = ElementInfo(
            tag_name="div",
            text_content="???",
            attributes={"class": "unknown"},
            css_classes=["unknown"],
            dom_path="body.div.unknown",
            visibility=False,  # Hidden element
            interactable=False
        )
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=200.0,  # Slow resolution
            validation_results=[
                ValidationResult(
                    rule_type="regex",
                    passed=False,
                    score=0.1,
                    message="Text doesn't match pattern"
                ),
                ValidationResult(
                    rule_type="semantic",
                    passed=False,
                    score=0.2,
                    message="No semantic meaning"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should have low confidence for poor match
        assert confidence < 0.5
    
    def test_calculate_confidence_failed_result(self):
        """Test confidence calculation for failed result."""
        scorer = ConfidenceScorer()
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=None,
            confidence_score=0.0,
            resolution_time=100.0,
            validation_results=[],
            success=False,
            timestamp=datetime.utcnow(),
            failure_reason="Element not found"
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Failed results should have zero confidence
        assert confidence == 0.0
    
    def test_calculate_confidence_with_strategy_history(self):
        """Test confidence calculation considering strategy success history."""
        scorer = ConfidenceScorer()
        
        # Create result with strategy that has good history
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.div.match-header.span.team-name",
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=45.0,
            validation_results=[
                ValidationResult(
                    rule_type="regex",
                    passed=True,
                    score=0.9,
                    message="Text matches pattern"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        # Mock strategy with high success rate (this would come from metrics)
        # This will need to be implemented in the actual scorer
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should consider strategy history in confidence calculation
        assert confidence > 0.8
    
    def test_validate_content_regex_success(self):
        """Test content validation with regex rule success."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.span.team-name",
            visibility=True,
            interactable=True
        )
        
        rule = {
            "type": "regex",
            "pattern": r"^[A-Za-z\s]+$",
            "required": True,
            "weight": 0.4
        }
        
        validations = scorer.validate_content(element_info, [rule])
        
        assert len(validations) == 1
        assert validations[0].passed is True
        assert validations[0].score > 0.8
        assert "matches pattern" in validations[0].message.lower()
    
    def test_validate_content_regex_failure(self):
        """Test content validation with regex rule failure."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="12345",  # Numbers only, not letters
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.span.team-name",
            visibility=True,
            interactable=True
        )
        
        rule = {
            "type": "regex",
            "pattern": r"^[A-Za-z\s]+$",
            "required": True,
            "weight": 0.4
        }
        
        validations = scorer.validate_content(element_info, [rule])
        
        assert len(validations) == 1
        assert validations[0].passed is False
        assert validations[0].score < 0.5
        assert "pattern" in validations[0].message.lower()
    
    def test_validate_content_data_type_success(self):
        """Test content validation with data type rule success."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="2.10",  # Valid odds format
            attributes={"class": "odds"},
            css_classes=["odds"],
            dom_path="body.span.odds",
            visibility=True,
            interactable=True
        )
        
        rule = {
            "type": "data_type",
            "pattern": "float",
            "required": True,
            "weight": 0.3
        }
        
        validations = scorer.validate_content(element_info, [rule])
        
        assert len(validations) == 1
        assert validations[0].passed is True
        assert validations[0].score > 0.8
    
    def test_validate_content_semantic_success(self):
        """Test content validation with semantic rule success."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name", "data-team": "home"},
            css_classes=["team-name"],
            dom_path="body.span.team-name",
            visibility=True,
            interactable=True
        )
        
        rule = {
            "type": "semantic",
            "pattern": "team_name",
            "required": True,
            "weight": 0.3
        }
        
        validations = scorer.validate_content(element_info, [rule])
        
        assert len(validations) == 1
        assert validations[0].passed is True
        assert validations[0].score > 0.7
    
    def test_validate_content_multiple_rules(self):
        """Test content validation with multiple rules."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.span.team-name",
            visibility=True,
            interactable=True
        )
        
        rules = [
            {
                "type": "regex",
                "pattern": r"^[A-Za-z\s]+$",
                "required": True,
                "weight": 0.4
            },
            {
                "type": "semantic",
                "pattern": "team_name",
                "required": True,
                "weight": 0.3
            },
            {
                "type": "custom",
                "pattern": "length_check",
                "required": False,
                "weight": 0.2
            }
        ]
        
        validations = scorer.validate_content(element_info, rules)
        
        assert len(validations) == 3
        # All should pass for good content
        assert all(v.passed for v in validations)
        # All should have reasonable scores
        assert all(v.score > 0.5 for v in validations)
    
    def test_get_threshold_by_context(self):
        """Test getting confidence threshold by context."""
        scorer = ConfidenceScorer()
        
        # Test different contexts
        production_threshold = scorer.get_threshold("production")
        development_threshold = scorer.get_threshold("development")
        research_threshold = scorer.get_threshold("research")
        
        # Production should have highest threshold
        assert production_threshold >= 0.8
        # Development should have medium threshold
        assert 0.6 <= development_threshold < 0.8
        # Research should have lowest threshold
        assert research_threshold <= 0.6
    
    def test_calculate_confidence_weighted_validation(self):
        """Test confidence calculation with weighted validation rules."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.span.team-name",
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=50.0,
            validation_results=[
                # High weight, high score
                ValidationResult(
                    rule_type="regex",
                    passed=True,
                    score=0.9,
                    message="Text matches pattern"
                ),
                # Low weight, low score
                ValidationResult(
                    rule_type="custom",
                    passed=False,
                    score=0.3,
                    message="Custom rule failed"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should still have good confidence due to high-weight rule passing
        assert confidence > 0.7
    
    def test_calculate_confidence_position_stability(self):
        """Test confidence calculation considering DOM position stability."""
        scorer = ConfidenceScorer()
        
        # Create result with stable DOM path
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.div.match-header.span.team-name",  # Stable path
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=50.0,
            validation_results=[
                ValidationResult(
                    rule_type="regex",
                    passed=True,
                    score=0.8,
                    message="Text matches pattern"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should have good confidence for stable position
        assert confidence > 0.8
    
    def test_calculate_confidence_performance_penalty(self):
        """Test confidence calculation with performance penalty for slow resolution."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="Manchester United",
            attributes={"class": "team-name"},
            css_classes=["team-name"],
            dom_path="body.span.team-name",
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="home_team_name",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=500.0,  # Slow resolution time
            validation_results=[
                ValidationResult(
                    rule_type="regex",
                    passed=True,
                    score=0.9,
                    message="Text matches pattern"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should have reduced confidence due to slow performance
        assert confidence < 0.8
        assert confidence > 0.5  # But still reasonable since content is good


class TestConfidenceScorerEdgeCases:
    """Test edge cases for confidence scoring."""
    
    def test_empty_validation_results(self):
        """Test confidence calculation with no validation results."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="Test",
            attributes={"class": "test"},
            css_classes=["test"],
            dom_path="body.span.test",
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="test_selector",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=50.0,
            validation_results=[],  # No validation results
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should still calculate confidence based on other factors
        assert 0.0 <= confidence <= 1.0
    
    def test_invalid_validation_rule(self):
        """Test validation with invalid rule type."""
        scorer = ConfidenceScorer()
        
        element_info = ElementInfo(
            tag_name="span",
            text_content="Test",
            attributes={"class": "test"},
            css_classes=["test"],
            dom_path="body.span.test",
            visibility=True,
            interactable=True
        )
        
        rule = {
            "type": "invalid_type",
            "pattern": "test",
            "required": True,
            "weight": 0.5
        }
        
        validations = scorer.validate_content(element_info, [rule])
        
        assert len(validations) == 1
        assert validations[0].passed is False
        assert "invalid" in validations[0].message.lower()
    
    def test_null_element_info(self):
        """Test validation with null element info."""
        scorer = ConfidenceScorer()
        
        rule = {
            "type": "regex",
            "pattern": r"test",
            "required": True,
            "weight": 0.5
        }
        
        validations = scorer.validate_content(None, [rule])
        
        assert len(validations) == 1
        assert validations[0].passed is False
        assert "element" in validations[0].message.lower() or "null" in validations[0].message.lower()
    
    def test_confidence_bounds(self):
        """Test confidence calculation stays within bounds."""
        scorer = ConfidenceScorer()
        
        # Test with perfect conditions
        element_info = ElementInfo(
            tag_name="span",
            text_content="Perfect Match",
            attributes={"class": "perfect"},
            css_classes=["perfect"],
            dom_path="body.span.perfect",
            visibility=True,
            interactable=True
        )
        
        result = SelectorResult(
            selector_name="perfect_selector",
            strategy_used="text_anchor",
            element_info=element_info,
            confidence_score=0.0,
            resolution_time=1.0,  # Very fast
            validation_results=[
                ValidationResult(
                    rule_type="regex",
                    passed=True,
                    score=1.0,
                    message="Perfect match"
                )
            ],
            success=True,
            timestamp=datetime.utcnow()
        )
        
        confidence = scorer.calculate_confidence(result, result.validation_results)
        
        # Should never exceed 1.0
        assert confidence <= 1.0
        assert confidence >= 0.0
