"""
Stability Scoring Service for recipe selector stability tracking.

This service calculates and updates stability scores based on selector
resolution successes and failures over time.
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime


class FailureSeverity(str, Enum):
    """Enumeration for failure severity levels."""
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is a valid severity level."""
        return value in (cls.MINOR.value, cls.MODERATE.value, cls.CRITICAL.value)


class StabilityScoringService:
    """
    Service for calculating and updating recipe stability scores.
    
    The stability scoring algorithm uses the following formula:
    
    stability_score = base_score + (success_count * success_weight) 
                      - (failure_count * failure_weight) * severity_multiplier
                      + (generations_survived * generation_bonus)
    
    Where:
    - base_score: 0.5 (neutral starting point)
    - success_weight: 0.05 (each success adds 5%)
    - failure_weight: 0.10 (each failure subtracts 10%)
    - severity_multiplier: 1.0 (minor), 1.5 (moderate), 2.0 (critical)
    - generation_bonus: 0.1 per generation survived
    
    Score bounds: 0.0 (minimum) to 1.0 (maximum)
    """
    
    # Default weights (can be configured)
    DEFAULT_SUCCESS_WEIGHT = 0.05
    DEFAULT_FAILURE_WEIGHT = 0.10
    DEFAULT_BASE_SCORE = 0.5
    DEFAULT_GENERATION_BONUS = 0.1
    
    # Severity multipliers
    SEVERITY_MULTIPLIERS = {
        FailureSeverity.MINOR: 1.0,
        FailureSeverity.MODERATE: 1.5,
        FailureSeverity.CRITICAL: 2.0,
    }
    
    # Failure impact values
    FAILURE_IMPACT = {
        FailureSeverity.MINOR: 0.05,
        FailureSeverity.MODERATE: 0.10,
        FailureSeverity.CRITICAL: 0.20,
    }
    
    def __init__(
        self,
        recipe_repository,
        success_weight: float = DEFAULT_SUCCESS_WEIGHT,
        failure_weight: float = DEFAULT_FAILURE_WEIGHT,
        base_score: float = DEFAULT_BASE_SCORE,
        generation_bonus: float = DEFAULT_GENERATION_BONUS,
    ):
        """
        Initialize the stability scoring service.
        
        Args:
            recipe_repository: RecipeRepository instance for database operations
            success_weight: Weight for each successful resolution (default 0.05)
            failure_weight: Weight for each failure (default 0.10)
            base_score: Starting score for new recipes (default 0.5)
            generation_bonus: Bonus per generation survived (default 0.1)
        """
        self.repository = recipe_repository
        self.success_weight = success_weight
        self.failure_weight = failure_weight
        self.base_score = base_score
        self.generation_bonus = generation_bonus
    
    def calculate_stability_score(
        self,
        success_count: int,
        failure_count: int,
        generations_survived: int = 0,
        consecutive_failures: int = 0,
    ) -> float:
        """
        Calculate stability score based on tracking metrics.
        
        Args:
            success_count: Number of successful resolutions
            failure_count: Number of failed resolutions
            generations_survived: Number of layout generations survived
            consecutive_failures: Number of consecutive failures
            
        Returns:
            Stability score between 0.0 and 1.0
        """
        # Ensure non-negative values
        success_count = max(0, success_count)
        failure_count = max(0, failure_count)
        generations_survived = max(0, generations_survived)
        consecutive_failures = max(0, consecutive_failures)
        
        # Start with base score
        score = self.base_score
        
        # Add success contribution
        score += success_count * self.success_weight
        
        # Subtract failure contribution
        failure_penalty = failure_count * self.failure_weight
        score -= failure_penalty
        
        # Add generation survival bonus
        score += generations_survived * self.generation_bonus
        
        # Apply consecutive failure multiplier (additional penalty)
        if consecutive_failures > 2:
            consecutive_penalty = (consecutive_failures - 2) * 0.02
            score -= consecutive_penalty
        
        # Clamp score to bounds [0.0, 1.0]
        return max(0.0, min(1.0, score))
    
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
        # Update tracking metrics in repository
        recipe = self.repository.update_stability_on_success(
            recipe_id=recipe_id,
            version=version,
        )
        
        if recipe:
            # Recalculate stability score
            new_score = self.calculate_stability_score(
                success_count=recipe.success_count or 0,
                failure_count=recipe.failure_count or 0,
                generations_survived=recipe.generations_survived or 0,
                consecutive_failures=recipe.consecutive_failures or 0,
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
            # Recalculate stability score
            new_score = self.calculate_stability_score(
                success_count=recipe.success_count or 0,
                failure_count=recipe.failure_count or 0,
                generations_survived=recipe.generations_survived or 0,
                consecutive_failures=recipe.consecutive_failures or 0,
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
