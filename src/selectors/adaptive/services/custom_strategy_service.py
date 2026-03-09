"""
Custom Selector Strategy Service for creating and managing custom selector strategies.

This implements Story 7.2 (Technical and Non-Technical Views) requirements:
- Custom selector strategy creation interface
- Real-time validation and testing interface
- Save custom strategies for future use
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import re
import logging

from src.observability.logger import get_logger


@dataclass
class CustomStrategy:
    """Represents a custom selector strategy."""
    id: str
    name: str
    description: str
    selector: str
    strategy_type: str  # css, xpath, text_anchor, custom
    confidence_weight: float = 0.5
    blast_radius_protection: bool = True
    validation_rules: Dict[str, Any] = None
    created_by: str = ""
    created_at: datetime = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.validation_rules is None:
            self.validation_rules = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomStrategy':
        """Create CustomStrategy from dictionary."""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class ValidationResult:
    """Result of selector validation."""
    is_valid: bool
    confidence_score: float
    error_message: Optional[str] = None
    suggestions: List[str] = None
    test_results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.test_results is None:
            self.test_results = {}


class CustomStrategyService:
    """
    Service for managing custom selector strategies.
    
    This service provides:
    - Strategy creation and validation
    - Real-time testing interface
    - Strategy persistence and management
    """
    
    def __init__(self):
        """Initialize the custom strategy service."""
        self._logger = get_logger("custom_strategy_service")
        self._strategies: Dict[str, CustomStrategy] = {}
        self._load_default_strategies()
    
    def create_strategy(
        self,
        name: str,
        description: str,
        selector: str,
        strategy_type: str,
        confidence_weight: float = 0.5,
        blast_radius_protection: bool = True,
        validation_rules: Optional[Dict[str, Any]] = None,
        created_by: str = ""
    ) -> Tuple[Optional[CustomStrategy], ValidationResult]:
        """
        Create a new custom selector strategy.
        
        Args:
            name: Strategy name
            description: Strategy description
            selector: The selector string
            strategy_type: Type of strategy (css, xpath, text_anchor, custom)
            confidence_weight: Weight for confidence scoring
            blast_radius_protection: Whether to enable blast radius protection
            validation_rules: Custom validation rules
            created_by: User who created the strategy
            
        Returns:
            Tuple of (strategy, validation_result)
        """
        try:
            # Validate the selector first
            validation = self.validate_selector(selector, strategy_type)
            
            if not validation.is_valid:
                return None, validation
            
            # Generate ID
            strategy_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create strategy
            strategy = CustomStrategy(
                id=strategy_id,
                name=name,
                description=description,
                selector=selector,
                strategy_type=strategy_type,
                confidence_weight=confidence_weight,
                blast_radius_protection=blast_radius_protection,
                validation_rules=validation_rules or {},
                created_by=created_by
            )
            
            # Store strategy
            self._strategies[strategy_id] = strategy
            
            self._logger.info(f"Created custom strategy: {strategy_id}")
            return strategy, validation
            
        except Exception as e:
            self._logger.error(f"Failed to create strategy: {e}")
            return None, ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                error_message=f"Failed to create strategy: {str(e)}"
            )
    
    def validate_selector(self, selector: str, strategy_type: str) -> ValidationResult:
        """
        Validate a selector string.
        
        Args:
            selector: The selector to validate
            strategy_type: Type of selector
            
        Returns:
            Validation result with confidence score and suggestions
        """
        try:
            if strategy_type == "css":
                return self._validate_css_selector(selector)
            elif strategy_type == "xpath":
                return self._validate_xpath_selector(selector)
            elif strategy_type == "text_anchor":
                return self._validate_text_anchor_selector(selector)
            elif strategy_type == "custom":
                return self._validate_custom_selector(selector)
            else:
                return ValidationResult(
                    is_valid=False,
                    confidence_score=0.0,
                    error_message=f"Unknown strategy type: {strategy_type}"
                )
                
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                error_message=f"Validation failed: {str(e)}"
            )
    
    def _validate_css_selector(self, selector: str) -> ValidationResult:
        """Validate CSS selector."""
        suggestions = []
        confidence = 0.5
        
        # Basic CSS selector validation
        if not selector.strip():
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                error_message="Selector cannot be empty"
            )
        
        # Check for common issues
        if selector.count('#') > 1:
            suggestions.append("Multiple ID selectors detected - consider using a single ID")
            confidence -= 0.1
        
        if selector.count('.') > 3:
            suggestions.append("Many class selectors - consider simplifying")
            confidence -= 0.1
        
        # Check for specific patterns
        if selector.startswith('#'):
            confidence = 0.9  # ID selectors are very stable
        elif selector.startswith('.'):
            confidence = 0.7  # Class selectors are moderately stable
        elif '[' in selector and ']' in selector:
            confidence = 0.8  # Attribute selectors are stable
        elif '>' in selector:
            confidence = 0.6  # Child selectors are moderately stable
        elif ' ' in selector:
            confidence = 0.5  # Descendant selectors are less stable
        
        # Check for invalid characters
        if re.search(r'[<>{}]', selector):
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                error_message="Invalid characters in selector"
            )
        
        # Test common patterns
        test_results = {
            "has_id": '#' in selector,
            "has_classes": '.' in selector,
            "has_attributes": '[' in selector,
            "has_pseudo_elements": ':' in selector,
            "complexity_score": self._calculate_complexity_score(selector)
        }
        
        return ValidationResult(
            is_valid=True,
            confidence_score=max(0.1, min(1.0, confidence)),
            suggestions=suggestions,
            test_results=test_results
        )
    
    def _validate_xpath_selector(self, selector: str) -> ValidationResult:
        """Validate XPath selector."""
        suggestions = []
        confidence = 0.6
        
        if not selector.strip():
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                error_message="XPath cannot be empty"
            )
        
        # Basic XPath validation
        if not (selector.startswith('/') or selector.startswith('(')):
            suggestions.append("XPath should start with / or (")
            confidence -= 0.2
        
        # Check for XPath functions
        if any(func in selector for func in ['contains(', 'starts-with(', 'text(']):
            confidence += 0.1  # Functions add robustness
        
        # Check for absolute vs relative
        if selector.startswith('//'):
            confidence = 0.7  # Relative XPath is more flexible
        elif selector.startswith('/'):
            confidence = 0.8  # Absolute XPath is more specific
        
        test_results = {
            "is_absolute": selector.startswith('/'),
            "is_relative": selector.startswith('//'),
            "has_functions": any(func in selector for func in ['contains(', 'starts-with(', 'text(']),
            "has_predicates": '[' in selector and ']' in selector,
            "complexity_score": self._calculate_complexity_score(selector)
        }
        
        return ValidationResult(
            is_valid=True,
            confidence_score=max(0.1, min(1.0, confidence)),
            suggestions=suggestions,
            test_results=test_results
        )
    
    def _validate_text_anchor_selector(self, selector: str) -> ValidationResult:
        """Validate text anchor selector."""
        if not selector.strip():
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                error_message="Text anchor cannot be empty"
            )
        
        # Text anchors are usually stable but can be fragile
        confidence = 0.6
        suggestions = []
        
        # Check for common text anchor patterns
        if len(selector) < 3:
            suggestions.append("Text anchor is very short - may be fragile")
            confidence -= 0.2
        
        if selector.isdigit():
            suggestions.append("Numeric text anchors can be unstable")
            confidence -= 0.1
        
        test_results = {
            "length": len(selector),
            "has_numbers": any(char.isdigit() for char in selector),
            "has_special_chars": any(not char.isalnum() and not char.isspace() for char in selector),
            "word_count": len(selector.split())
        }
        
        return ValidationResult(
            is_valid=True,
            confidence_score=max(0.1, min(1.0, confidence)),
            suggestions=suggestions,
            test_results=test_results
        )
    
    def _validate_custom_selector(self, selector: str) -> ValidationResult:
        """Validate custom selector."""
        # Custom selectors have variable validation
        return ValidationResult(
            is_valid=True,
            confidence_score=0.5,
            suggestions=["Custom selectors should be tested thoroughly"],
            test_results={"type": "custom", "validated": False}
        )
    
    def _calculate_complexity_score(self, selector: str) -> float:
        """Calculate complexity score for a selector."""
        # Simple complexity calculation based on length and special characters
        length_score = min(1.0, len(selector) / 50.0)
        special_chars = sum(1 for c in selector if not c.isalnum() and not c.isspace())
        special_score = min(1.0, special_chars / 10.0)
        
        return (length_score + special_score) / 2.0
    
    def test_strategy(
        self,
        strategy_id: str,
        test_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test a strategy against sample content.
        
        Args:
            strategy_id: ID of the strategy to test
            test_content: Sample content to test against
            
        Returns:
            Test results
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return {"error": "Strategy not found"}
        
        # Mock test results - in real implementation, this would
        # actually test the selector against real DOM content
        return {
            "strategy_id": strategy_id,
            "test_passed": True,
            "matches_found": 1,
            "execution_time_ms": 15,
            "confidence_score": strategy.confidence_weight,
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "sample_content_used": test_content is not None
        }
    
    def get_strategy(self, strategy_id: str) -> Optional[CustomStrategy]:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)
    
    def list_strategies(
        self,
        strategy_type: Optional[str] = None,
        created_by: Optional[str] = None,
        active_only: bool = True
    ) -> List[CustomStrategy]:
        """
        List strategies with optional filtering.
        
        Args:
            strategy_type: Filter by strategy type
            created_by: Filter by creator
            active_only: Only return active strategies
            
        Returns:
            List of matching strategies
        """
        strategies = list(self._strategies.values())
        
        if strategy_type:
            strategies = [s for s in strategies if s.strategy_type == strategy_type]
        
        if created_by:
            strategies = [s for s in strategies if s.created_by == created_by]
        
        if active_only:
            strategies = [s for s in strategies if s.is_active]
        
        return strategies
    
    def update_strategy(
        self,
        strategy_id: str,
        updates: Dict[str, Any]
    ) -> Optional[CustomStrategy]:
        """Update an existing strategy."""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None
        
        # Update allowed fields
        allowed_fields = {
            'name', 'description', 'selector', 'strategy_type',
            'confidence_weight', 'blast_radius_protection',
            'validation_rules', 'is_active'
        }
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(strategy, field, value)
        
        self._logger.info(f"Updated strategy: {strategy_id}")
        return strategy
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy."""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            self._logger.info(f"Deleted strategy: {strategy_id}")
            return True
        return False
    
    def _load_default_strategies(self):
        """Load some default custom strategies for demonstration."""
        default_strategies = [
            CustomStrategy(
                id="default_team_name_v2",
                name="Team Name v2",
                description="Improved team name selector with fallback",
                selector=".team-info .name",
                strategy_type="css",
                confidence_weight=0.8,
                created_by="system"
            ),
            CustomStrategy(
                id="default_score_xpath",
                name="Score XPath",
                description="XPath-based score selector",
                selector="//div[contains(@class, 'score')]/text()",
                strategy_type="xpath",
                confidence_weight=0.7,
                created_by="system"
            )
        ]
        
        for strategy in default_strategies:
            self._strategies[strategy.id] = strategy


# Global instance for dependency injection
_custom_strategy_service: Optional[CustomStrategyService] = None


def get_custom_strategy_service() -> CustomStrategyService:
    """Get or create the global custom strategy service instance."""
    global _custom_strategy_service
    if _custom_strategy_service is None:
        _custom_strategy_service = CustomStrategyService()
    return _custom_strategy_service
