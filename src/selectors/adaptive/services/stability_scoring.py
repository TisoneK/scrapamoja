"""
Stability Scoring Service for recipe selector stability tracking.

This service uses the existing ConfidenceScorer via composition to calculate 
stability scores based on selector resolution successes and failures over time.

REFACTORED: Now uses ConfidenceScorer via composition per Sprint Change Proposal (2026-03-03)
to avoid duplicating scoring functionality while avoiding import issues with the 
confidence package shadowing the confidence.py module.
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime

from src.observability.logger import get_logger


class FailureSeverity(str, Enum):
    """Enumeration for failure severity levels."""
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is a valid severity level."""
        return value in (cls.MINOR.value, cls.MODERATE.value, cls.CRITICAL.value)


class AdaptiveWeights:
    """
    Extended weights for recipe stability scoring.
    
    Works alongside ConfidenceWeights from the confidence system.
    """
    
    # Stability-specific weight factors
    GENERATION_BONUS_WEIGHT = 0.1  # Per generation survived
    PARENT_INHERITANCE_WEIGHT = 0.15  # Inheritance factor from parent recipe
    CONSECUTIVE_FAILURE_PENALTY = 0.02  # Per consecutive failure beyond 2
    
    def __init__(
        self,
        generation_bonus: float = GENERATION_BONUS_WEIGHT,
        parent_inheritance: float = PARENT_INHERITANCE_WEIGHT,
        consecutive_penalty: float = CONSECUTIVE_FAILURE_PENALTY,
    ):
        self.generation_bonus = generation_bonus
        self.parent_inheritance = parent_inheritance
        self.consecutive_penalty = consecutive_penalty


class StabilityScoringService:
    """
    Service for calculating and updating recipe stability scores.
    
    REENGINEERED using Composition with ConfidenceScorer per Sprint Change Proposal (2026-03-03):
    - Uses internal ConfidenceScorer instance for base scoring
    - Adds recipe-specific stability logic (generation tracking, parent-child inheritance)
    - Avoids inheritance issues with package shadowing
    
    The stability scoring algorithm uses the following formula:
    
    stability_score = base_confidence + generation_bonus + parent_inheritance - consecutive_failure_penalty
    
    Where:
    - base_confidence: From internal ConfidenceScorer (strategy history based)
    - generation_bonus: 0.1 per generation survived (tracked via failure events)
    - parent_inheritance: 0.15 from parent recipe stability (if parent exists)
    - consecutive_failure_penalty: 0.02 per failure beyond 2
    
    Score bounds: 0.0 (minimum) to 1.0 (maximum)
    
    Note: This class maintains backward compatibility with the original
    StabilityScoringService API while leveraging ConfidenceScorer functionality.
    """
    
    # Default weights (for backward compatibility)
    DEFAULT_SUCCESS_WEIGHT = 0.05
    DEFAULT_FAILURE_WEIGHT = 0.10
    DEFAULT_BASE_SCORE = 0.5
    DEFAULT_GENERATION_BONUS = 0.1
    
    # Severity multipliers (kept for backward compatibility)
    SEVERITY_MULTIPLIERS = {
        FailureSeverity.MINOR: 1.0,
        FailureSeverity.MODERATE: 1.5,
        FailureSeverity.CRITICAL: 2.0,
    }
    
    # Failure impact values (kept for backward compatibility)
    FAILURE_IMPACT = {
        FailureSeverity.MINOR: 0.05,
        FailureSeverity.MODERATE: 0.10,
        FailureSeverity.CRITICAL: 0.20,
    }
    
    def __init__(
        self,
        recipe_repository=None,
        success_weight: float = DEFAULT_SUCCESS_WEIGHT,
        failure_weight: float = DEFAULT_FAILURE_WEIGHT,
        base_score: float = DEFAULT_BASE_SCORE,
        generation_bonus: float = DEFAULT_GENERATION_BONUS,
    ):
        """
        Initialize the stability scoring service.
        
        Args:
            recipe_repository: RecipeRepository instance for database operations
            success_weight: Weight for each successful resolution (default 0.05) - kept for BC
            failure_weight: Weight for each failure (default 0.10) - kept for BC
            base_score: Starting score for new recipes (default 0.5) - kept for BC
            generation_bonus: Bonus per generation survived (default 0.1)
        """
        # Lazy import to avoid circular import issues
        # The confidence.py module is shadowed by confidence/ package
        self._confidence_scorer = None
        
        # Store repository reference
        self.repository = recipe_repository
        
        # Store configuration for backward compatibility
        self.success_weight = success_weight
        self.failure_weight = failure_weight
        self.base_score = base_score
        self.generation_bonus = generation_bonus
        
        # Initialize adaptive-specific weights
        self._adaptive_weights = AdaptiveWeights()
        
        # Get logger
        self._logger = get_logger("stability_scoring")
        
        # Track strategy metrics for confidence scoring
        self._strategy_metrics: dict = {}
    
    @property
    def confidence_scorer(self):
        """Lazy-load the ConfidenceScorer to avoid circular imports."""
        if self._confidence_scorer is None:
            # Import from adaptive services where Story 3.2 created it
            from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
            self._confidence_scorer = ConfidenceScorer()
        return self._confidence_scorer
    
    def calculate_recipe_stability(
        self,
        recipe_id: str,
        success_count: int = 0,
        failure_count: int = 0,
        generations_survived: int = 0,
        consecutive_failures: int = 0,
        parent_recipe_id: Optional[str] = None,
    ) -> float:
        """
        Calculate stability score for a recipe using ConfidenceScorer + adaptive extensions.
        
        This is the PRIMARY method for recipe stability calculation.
        Uses ConfidenceScorer for base scoring and adds adaptive-specific factors.
        
        Args:
            recipe_id: Unique identifier for the recipe
            success_count: Number of successful resolutions
            failure_count: Number of failed resolutions
            generations_survived: Number of layout generations survived
            consecutive_failures: Number of consecutive failures
            parent_recipe_id: Optional parent recipe for inheritance
            
        Returns:
            Stability score between 0.0 and 1.0
        """
        # Ensure non-negative values
        success_count = max(0, success_count)
        failure_count = max(0, failure_count)
        generations_survived = max(0, generations_survived)
        consecutive_failures = max(0, consecutive_failures)
        
        # Get base confidence from internal ConfidenceScorer
        base_confidence = self._calculate_base_confidence(
            success_count, 
            failure_count,
            generations_survived
        )
        
        # Add generation survival bonus
        generation_bonus = generations_survived * self._adaptive_weights.generation_bonus
        
        # Add parent inheritance if parent exists
        parent_inheritance = 0.0
        if parent_recipe_id:
            parent_inheritance = self._get_parent_inheritance(parent_recipe_id)
        
        # Apply consecutive failure penalty
        consecutive_penalty = 0.0
        if consecutive_failures > 2:
            consecutive_penalty = (consecutive_failures - 2) * self._adaptive_weights.consecutive_penalty
        
        # Calculate final stability score
        stability_score = (
            base_confidence + 
            generation_bonus + 
            parent_inheritance - 
            consecutive_penalty
        )
        
        # Clamp to bounds [0.0, 1.0]
        return max(0.0, min(1.0, stability_score))
    
    def _calculate_base_confidence(
        self,
        success_count: int,
        failure_count: int,
        generations_survived: int,
    ) -> float:
        """
        Calculate base confidence from success/failure counts.
        
        This aligns with ConfidenceScorer patterns while avoiding duplicate logic.
        """
        if success_count == 0 and failure_count == 0:
            return self.base_score
        
        # Calculate success rate
        total_attempts = success_count + failure_count
        if total_attempts == 0:
            return self.base_score
        
        success_rate = success_count / total_attempts
        
        # Apply success/failure weights (matching ConfidenceScorer patterns)
        score = (
            self.base_score +
            (success_count * self.success_weight) -
            (failure_count * self.failure_weight)
        )
        
        # Factor in generations survived
        score += generations_survived * self.generation_bonus
        
        return max(0.0, min(1.0, score))
    
    def _get_parent_inheritance(self, parent_recipe_id: str) -> float:
        """
        Get stability inheritance from parent recipe.
        
        Args:
            parent_recipe_id: The parent recipe ID
            
        Returns:
            Inheritance factor (0.0 to 0.15)
        """
        if not self.repository:
            return 0.0
        
        try:
            # Get parent recipe stability
            parent = self.repository.get_by_id(parent_recipe_id)
            if parent and parent.stability_score:
                # Inherit a portion of parent's stability
                return parent.stability_score * self._adaptive_weights.parent_inheritance
        except Exception as e:
            self._logger.warning(
                "parent_inheritance_failed",
                parent_recipe_id=parent_recipe_id,
                error=str(e)
            )
        
        return 0.0
    
    # Keep for backward compatibility - delegates to new method
    def calculate_stability_score(
        self,
        success_count: int,
        failure_count: int,
        generations_survived: int = 0,
        consecutive_failures: int = 0,
    ) -> float:
        """
        Calculate stability score based on tracking metrics.
        
        DEPRECATED: Use calculate_recipe_stability() instead.
        This method is kept for backward compatibility.
        
        Args:
            success_count: Number of successful resolutions
            failure_count: Number of failed resolutions
            generations_survived: Number of layout generations survived
            consecutive_failures: Number of consecutive failures
            
        Returns:
            Stability score between 0.0 and 1.0
        """
        return self.calculate_recipe_stability(
            recipe_id="unknown",  # Legacy compatibility
            success_count=success_count,
            failure_count=failure_count,
            generations_survived=generations_survived,
            consecutive_failures=consecutive_failures,
        )
    
    async def on_selector_success(
        self,
        recipe_id: str,
        selector_id: Optional[str] = None,
        version: Optional[int] = None,
    ):
        """
        Handle successful selector resolution.
        
        Increments success_count, resets consecutive_failures,
        updates timestamp, and recalculates stability score.
        
        Args:
            recipe_id: Unique identifier for the recipe
            selector_id: Optional selector that succeeded
            version: Optional specific version to update
        """
        if not self.repository:
            self._logger.warning("on_selector_success called without repository")
            return
        
        # Update tracking metrics in repository
        recipe = self.repository.update_stability_on_success(
            recipe_id=recipe_id,
            version=version,
        )
        
        if recipe:
            # Recalculate stability score using new method
            new_score = self.calculate_recipe_stability(
                recipe_id=recipe_id,
                success_count=recipe.success_count or 0,
                failure_count=recipe.failure_count or 0,
                generations_survived=recipe.generations_survived or 0,
                consecutive_failures=recipe.consecutive_failures or 0,
                parent_recipe_id=recipe.parent_recipe_id,
            )
            
            # Update the score in database
            self.repository.update_stability_score(
                recipe_id=recipe_id,
                stability_score=new_score,
                version=version,
            )
    
    async def on_selector_failure(
        self,
        recipe_id: str,
        selector_id: Optional[str] = None,
        severity: str = FailureSeverity.MINOR,
        version: Optional[int] = None,
    ):
        """
        Handle failed selector resolution.
        
        Increments failure_count and consecutive_failures,
        updates timestamps and severity, then recalculates score.
        
        Args:
            recipe_id: Unique identifier for the recipe
            selector_id: Optional selector that failed
            severity: Failure severity level ("minor", "moderate", "critical")
            version: Optional specific version to update
        """
        if not self.repository:
            self._logger.warning("on_selector_failure called without repository")
            return
        
        # Validate severity
        if not FailureSeverity.is_valid(severity):
            severity = FailureSeverity.MINOR
        
        # Update tracking metrics in repository
        recipe = self.repository.update_stability_on_failure(
            recipe_id=recipe_id,
            severity=severity,
            version=version,
        )
        
        if recipe:
            # Recalculate stability score using new method
            new_score = self.calculate_recipe_stability(
                recipe_id=recipe_id,
                success_count=recipe.success_count or 0,
                failure_count=recipe.failure_count or 0,
                generations_survived=recipe.generations_survived or 0,
                consecutive_failures=recipe.consecutive_failures or 0,
                parent_recipe_id=recipe.parent_recipe_id,
            )
            
            # Update the score in database
            self.repository.update_stability_score(
                recipe_id=recipe_id,
                stability_score=new_score,
                version=version,
            )
    
    def calculate_failure_impact(self, severity: str) -> float:
        """
        Calculate the score impact for a given failure severity.
        
        Args:
            severity: Failure severity level
            
        Returns:
            Score impact (negative value)
        """
        severity_enum = FailureSeverity(severity) if FailureSeverity.is_valid(severity) else FailureSeverity.MINOR
        return -self.FAILURE_IMPACT[severity_enum]
    
    async def get_stability_rankings(
        self,
        recipe_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List:
        """
        Get recipes ranked by stability score.
        
        Args:
            recipe_id: Optional filter for specific recipe
            limit: Optional limit on number of results
            
        Returns:
            List of Recipe instances ordered by stability_score descending
        """
        if not self.repository:
            return []
        
        return self.repository.get_stability_rankings(
            recipe_id=recipe_id,
            limit=limit,
        )
    
    async def get_recipe_stability(
        self,
        recipe_id: str,
        version: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get detailed stability information for a recipe.
        
        Args:
            recipe_id: Unique identifier for the recipe
            version: Optional specific version
            
        Returns:
            Dictionary with stability metrics, or None if not found
        """
        if not self.repository:
            return None
        
        recipe = self.repository.get_by_id(recipe_id=recipe_id, version=version)
        
        if not recipe:
            return None
        
        return {
            "recipe_id": recipe.recipe_id,
            "version": recipe.version,
            "stability_score": recipe.stability_score,
            "success_count": recipe.success_count or 0,
            "failure_count": recipe.failure_count or 0,
            "consecutive_failures": recipe.consecutive_failures or 0,
            "generations_survived": recipe.generations_survived or 0,
            "last_successful_resolution": recipe.last_successful_resolution,
            "last_failure_timestamp": recipe.last_failure_timestamp,
            "failure_severity": recipe.failure_severity,
            "parent_recipe_id": getattr(recipe, 'parent_recipe_id', None),
        }
    
    def get_severity_multiplier(self, severity: str) -> float:
        """
        Get the penalty multiplier for a given failure severity.
        
        Args:
            severity: Failure severity level
            
        Returns:
            Severity multiplier (1.0, 1.5, or 2.0)
        """
        severity_enum = FailureSeverity(severity) if FailureSeverity.is_valid(severity) else FailureSeverity.MINOR
        return self.SEVERITY_MULTIPLIERS[severity_enum]
    
    # Delegate methods to ConfidenceScorer for integration
    def get_strategy_confidence(self, strategy_id: str) -> float:
        """
        Get confidence for a specific strategy.
        
        Delegates to internal ConfidenceScorer instance.
        
        Args:
            strategy_id: The strategy identifier
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        metrics = self._strategy_metrics.get(strategy_id)
        if metrics:
            return metrics.reliability_score
        return 0.5  # Default for unknown strategies
    
    def update_strategy_metrics(self, selector_name: str, strategy_id: str, metrics) -> None:
        """
        Update strategy performance metrics.
        
        Delegates to internal ConfidenceScorer instance.
        
        Args:
            selector_name: The selector name
            strategy_id: The strategy identifier
            metrics: ConfidenceMetrics instance
        """
        key = f"{selector_name}.{strategy_id}"
        self._strategy_metrics[key] = metrics
        
        # Also update the internal confidence scorer if available
        if self._confidence_scorer:
            self._confidence_scorer.update_strategy_metrics(selector_name, strategy_id, metrics)
