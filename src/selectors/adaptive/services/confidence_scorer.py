"""
Confidence Scoring Service for refining selector confidence scores.

This service calculates refined confidence scores for alternative selectors
based on historical stability, selector specificity, and DOM structure similarity.

Story: 3.2 - Generate Confidence Scores
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import logging

from src.selectors.adaptive.services.dom_analyzer import AlternativeSelector, StrategyType
from src.selectors.adaptive.db.repositories.weight_repository import get_weight_repository
from src.observability.logger import get_logger


class ConfidenceTier(Enum):
    """Enumeration for confidence tier levels.
    
    Tiers categorize confidence scores for easier interpretation:
    - HIGH: 0.7-1.0 (green) - Highly reliable selectors
    - MEDIUM: 0.4-0.69 (yellow) - Moderately reliable
    - LOW: 0.0-0.39 (red) - Less reliable selectors
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    @classmethod
    def from_score(cls, score: float) -> "ConfidenceTier":
        """Convert a numeric score to a confidence tier.
        
        Args:
            score: Confidence score between 0.0 and 1.0
            
        Returns:
            ConfidenceTier corresponding to the score range
        """
        if score >= 0.7:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        else:
            return cls.LOW


@dataclass
class ScoringBreakdown:
    """Detailed breakdown of confidence score components.
    
    Attributes:
        historical_stability: Score from 0.0 to 1.0 based on selector history
        specificity_score: Score from 0.0 to 1.0 based on selector specificity
        dom_similarity: Score from 0.0 to 1.0 based on DOM structure similarity
        final_score: Weighted combination of all factors (0.0 to 1.0)
    """
    historical_stability: float
    specificity_score: float
    dom_similarity: float
    final_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "historical_stability": round(self.historical_stability, 3),
            "specificity_score": round(self.specificity_score, 3),
            "dom_similarity": round(self.dom_similarity, 3),
            "final_score": round(self.final_score, 3),
        }


class ConfidenceScorer:
    """Service for calculating refined confidence scores for selectors.
    
    This service refines the initial confidence scores from DOM Analysis (Story 3.1)
    by considering multiple scoring factors:
    
    1. Historical Stability (40% weight): Based on selector's past performance
    2. Specificity (35% weight): How specific the selector is (ID > class > tag)
    3. DOM Similarity (25% weight): How similar to the failed selector
    
    The weighted combination produces a final confidence score between 0.0 and 1.0.
    
    Integration:
    - Input: AlternativeSelector with placeholder confidence (from Story 3.1)
    - Output: Enhanced AlternativeSelector with detailed scoring breakdown
    - Uses: Snapshot repository for DOM analysis (Story 2.2)
    - Prepares for: Blast radius calculation (Story 3.3)
    """
    
    # Default weights for scoring factors (adjustable)
    WEIGHTS = {
        'historical_stability': 0.4,
        'specificity': 0.35,
        'dom_similarity': 0.25,
    }
    
    # Default confidence scores by strategy type (when no history exists)
    STRATEGY_DEFAULTS = {
        StrategyType.CSS: 0.7,
        StrategyType.XPATH: 0.65,
        StrategyType.TEXT_ANCHOR: 0.6,
        StrategyType.ATTRIBUTE_MATCH: 0.55,
        StrategyType.DOM_RELATIONSHIP: 0.5,
        StrategyType.ROLE_BASED: 0.5,
    }
    
    # Boost for custom selectors (human-created, likely more reliable)
    CUSTOM_SELECTOR_BOOST = 0.15
    
    # Penalty for custom selectors that get rejected (for learning)
    CUSTOM_SELECTOR_REJECTION_PENALTY = 0.2
    
    # Learning boost amounts
    APPROVAL_BOOST_AMOUNT = 0.05  # 5% boost per approval
    RELATED_STRATEGY_BOOST_AMOUNT = 0.03  # 3% boost for related strategies
    MAX_APPROVAL_BOOST = 0.25  # Cap at 25% total boost
    
    # Rejection penalty amounts (Story 5.2)
    REJECTION_PENALTY_AMOUNT = 0.05  # 5% penalty per rejection
    RELATED_STRATEGY_PENALTY_AMOUNT = 0.03  # 3% penalty for related strategies
    MAX_REJECTION_PENALTY = 0.25  # Cap at 25% total penalty
    MIN_CONFIDENCE_FLOOR = 0.1  # Minimum confidence floor for heavily rejected strategies
    
    # Rejection reason patterns for learning
    REJECTION_PATTERNS = {
        'too_specific': {'weight_adjustment': -0.05, 'description': 'Selector is too specific'},
        'too_generic': {'weight_adjustment': -0.03, 'description': 'Selector is too generic'},
        'wrong_element': {'weight_adjustment': -0.08, 'description': 'Wrong element selected'},
        'fragile': {'weight_adjustment': -0.06, 'description': 'Selector is fragile/unstable'},
        'not_stable': {'weight_adjustment': -0.05, 'description': 'Selector is not stable'},
        'custom': {'weight_adjustment': 0.0, 'description': 'Custom rejection reason'},
    }
    
    # Strategy relationship matrix for similar strategy boost
    # Maps each strategy to its related strategies and boost factor
    STRATEGY_RELATIONSHIPS = {
        StrategyType.CSS: {StrategyType.XPATH: 0.03, StrategyType.ATTRIBUTE_MATCH: 0.03},
        StrategyType.XPATH: {StrategyType.CSS: 0.03, StrategyType.DOM_RELATIONSHIP: 0.03},
        StrategyType.TEXT_ANCHOR: {StrategyType.DOM_RELATIONSHIP: 0.03, StrategyType.ROLE_BASED: 0.03},
        StrategyType.ATTRIBUTE_MATCH: {StrategyType.CSS: 0.03, StrategyType.XPATH: 0.03},
        StrategyType.DOM_RELATIONSHIP: {StrategyType.XPATH: 0.03, StrategyType.TEXT_ANCHOR: 0.03},
        StrategyType.ROLE_BASED: {StrategyType.TEXT_ANCHOR: 0.03},
    }
    
    # ==================== GENERATION TRACKING (STORY 5.3) ====================
    
    # Generation tracking constants
    GENERATION_WEIGHT = 0.15  # Weight for generation survival in confidence calculation
    GENERATION_SURVIVAL_BOOST = 0.05  # 5% boost per generation survived
    MAX_GENERATION_BOOST = 0.25  # Cap at 25% total generation boost
    CONSECUTIVE_FAILURES_FOR_REVIEW = 3  # Mark recipe for review after this many failures
    
    # Generation data structure:
    # {
    #     recipe_id: {
    #         'current_generation': int,
    #         'generations_survived': int,
    #         'generation_failures': int,
    #         'consecutive_failures': int,
    #         'last_generation_change': str (ISO datetime),
    #         'first_generation': str (ISO datetime),
    #     }
    # }
    
    def __init__(
        self,
        snapshot_repository=None,
        weight: float = WEIGHTS['historical_stability'],
        specificity_weight: float = WEIGHTS['specificity'],
        dom_similarity_weight: float = WEIGHTS['dom_similarity'],
        weight_repository=None,
    ):
        """Initialize the confidence scorer service.
        
        Args:
            snapshot_repository: Repository for accessing DOM snapshots
            weight: Weight for historical stability factor (default 0.4)
            specificity_weight: Weight for specificity factor (default 0.35)
            dom_similarity_weight: Weight for DOM similarity factor (default 0.25)
            weight_repository: Repository for persisting learned weights
        """
        self._logger = get_logger("confidence_scorer")
        
        # Repository for snapshot access
        self.snapshot_repository = snapshot_repository
        
        # Weight repository for persistence
        self.weight_repository = weight_repository
        
        # Custom weights (must sum to 1.0)
        self.WEIGHTS = {
            'historical_stability': weight,
            'specificity': specificity_weight,
            'dom_similarity': dom_similarity_weight,
        }
        
        # Validate weights sum to 1.0
        total = sum(self.WEIGHTS.values())
        if abs(total - 1.0) > 0.01:
            self._logger.warning(
                "weights_sum_warning",
                total=total,
                warning="Weights should sum to 1.0, normalizing"
            )
            # Normalize weights
            for key in self.WEIGHTS:
                self.WEIGHTS[key] = self.WEIGHTS[key] / total
        
        # Track historical data (in-memory for MVP, would be DB in production)
        # Stores either float scores or dict metrics depending on key prefix
        self._historical_data: Dict[str, float | Dict[str, Any]] = {}
        
        # Approval learning: Track approvals per strategy type
        # Structure: {StrategyType: {'count': int, 'last_approval': datetime, 'total_boost': float}}
        self._approval_weights: Dict[str, Dict[str, Any]] = {}
        
        # Rejection learning: Track rejections per strategy type (Story 5.2)
        # Structure: {StrategyType: {'count': int, 'last_rejection': datetime, 'total_penalty': float}}
        self._rejection_weights: Dict[str, Dict[str, Any]] = {}
        
        # Generation tracking: Track selector survival across generations (Story 5.3)
        # Structure: {recipe_id: {'current_generation': int, 'generations_survived': int, ...}}
        self._generation_data: Dict[str, Dict[str, Any]] = {}
        
        # Related strategy boost cache
        self._related_strategy_boosts: Dict[str, float] = {}
        
        # Load persisted weights on initialization
        self._load_persisted_weights()
        self._load_persisted_rejection_weights()
        self._load_persisted_generation_data()
    
    def calculate_confidence(
        self,
        selector: AlternativeSelector,
        snapshot_id: Optional[int] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        recipe_id: Optional[str] = None,
    ) -> AlternativeSelector:
        """Calculate refined confidence score for a selector.
        
        This is the main entry point for confidence scoring. It takes an AlternativeSelector
        with placeholder confidence and returns an enhanced version with detailed scoring.
        
        Args:
            selector: AlternativeSelector with initial confidence from DOM analysis
            snapshot_id: Optional snapshot ID for DOM similarity calculation
            sport: Optional sport context for historical lookup
            site: Optional site context for historical lookup
            recipe_id: Optional recipe ID for generation tracking (Story 5.3)
            
        Returns:
            Enhanced AlternativeSelector with scoring_breakdown and confidence_tier
        """
        # 1. Historical stability score (40% weight)
        historical = self._get_historical_stability(
            selector.selector_string,
            selector.strategy_type,
            sport,
        )
        
        # 2. Specificity score (35% weight)
        specificity = self._calculate_specificity(selector.selector_string)
        
        # 3. DOM similarity (25% weight) - optional, depends on snapshot availability
        dom_sim = 0.5  # Default neutral score
        if snapshot_id and self.snapshot_repository:
            dom_sim = self._calculate_dom_similarity(
                selector.selector_string,
                snapshot_id,
            )
        
        # 4. Generation stability (Story 5.3) - apply generation boost/penalty
        generation_stability = 1.0  # Default neutral
        if recipe_id:
            generation_stability = self.calculate_generation_stability(recipe_id)
        
        # Calculate weighted final score
        # Base score from original three factors
        base_score = (
            historical * self.WEIGHTS['historical_stability'] +
            specificity * self.WEIGHTS['specificity'] +
            dom_sim * self.WEIGHTS['dom_similarity']
        )
        
        # Apply generation stability factor
        # generation_stability > 1.0 means good survival, < 1.0 means poor survival
        final_score = base_score * generation_stability
        
        # Clamp to valid range [0.0, 1.0]
        final_score = max(0.0, min(1.0, final_score))
        
        # Build scoring breakdown
        breakdown = ScoringBreakdown(
            historical_stability=historical,
            specificity_score=specificity,
            dom_similarity=dom_sim,
            final_score=final_score,
        )
        
        # Determine confidence tier
        tier = ConfidenceTier.from_score(final_score)
        
        self._logger.info(
            "confidence_calculated",
            selector=selector.selector_string[:50],
            final_score=round(final_score, 3),
            tier=tier.value,
            historical=round(historical, 3),
            specificity=round(specificity, 3),
            dom_sim=round(dom_sim, 3),
            generation_stability=round(generation_stability, 3),
            recipe_id=recipe_id,
        )
        
        # Return enhanced AlternativeSelector with extended fields
        return AlternativeSelector(
            selector_string=selector.selector_string,
            strategy_type=selector.strategy_type,
            confidence_score=final_score,
            element_description=selector.element_description,
            scoring_breakdown=breakdown,
            confidence_tier=tier,
            historical_stability=historical,
            specificity_score=specificity,
            dom_similarity=dom_sim,
        )
    
    def _get_historical_stability(
        self,
        selector_string: str,
        strategy_type: StrategyType,
        sport: Optional[str] = None,
    ) -> float:
        """Look up historical stability for a selector.
        
        In production, this would query a database of selector performance history.
        For MVP, we use strategy-based defaults with in-memory caching.
        
        Args:
            selector_string: The selector string to look up
            strategy_type: The strategy type for default fallback
            sport: Optional sport context
            
        Returns:
            Historical stability score between 0.0 and 1.0
        """
        # Check in-memory cache first
        cache_key = f"{sport}:{selector_string}" if sport else selector_string
        
        # Also check approval and rejection cache keys
        approval_key = f"approval:{selector_string}"
        rejection_key = f"rejection:{selector_string}"
        strategy_key = f"strategy:{strategy_type.value}"
        
        # Check various cache keys in order of specificity
        for key in [cache_key, approval_key, rejection_key, strategy_key]:
            if key in self._historical_data:
                cached_value = self._historical_data[key]
                if isinstance(cached_value, float):
                    return cached_value
        
        # Check if there's any penalty from rejections for this strategy
        strategy_penalty = self.get_strategy_penalty(strategy_type)
        if strategy_penalty > 0:
            # Apply penalty to base confidence
            base_confidence = self.STRATEGY_DEFAULTS.get(strategy_type, 0.5)
            penalized = max(self.MIN_CONFIDENCE_FLOOR, base_confidence - strategy_penalty)
            # Store in cache for future lookups
            self._historical_data[cache_key] = penalized
            return penalized
        
        # Use strategy-based default
        default_score = self.STRATEGY_DEFAULTS.get(strategy_type, 0.5)
        
        # Store in cache for future lookups
        self._historical_data[cache_key] = default_score
        
        return default_score
    
    def _calculate_specificity(self, selector: str) -> float:
        """Calculate selector specificity score.
        
        More specific selectors (ID-based) are generally more reliable than
        less specific ones (tag-only).
        
        Scoring:
        - ID-based: 0.8-0.9 (single ID is very specific)
        - Class-based: 0.6-0.8 (classes are moderately specific)
        - Attribute selectors: 0.6
        - Tag + class combinations: 0.5
        - Tag only: 0.3
        
        Args:
            selector: The selector string to analyze
            
        Returns:
            Specificity score between 0.0 and 1.0
        """
        if not selector:
            return 0.3
        
        selector = selector.strip()
        
        # ID selector (highest specificity)
        # e.g., #main-content, #nav-header
        if '#' in selector and selector.count('#') == 1:
            return 0.9
        
        # Multiple IDs - very specific
        if selector.count('#') > 1:
            return 0.95
        
        # Tag + class combinations (check BEFORE class-only)
        # e.g., div.container, span.highlight
        if len(selector.split()) > 1:
            return 0.5
        
        # Class-based selectors (checked AFTER tag+class)
        # e.g., .btn-primary, .nav-item.active
        if '.' in selector:
            class_count = selector.count('.')
            # More classes = slightly more specific but also more fragile
            score = 0.6 + (class_count * 0.05)
            return min(0.8, score)
        
        # Attribute selectors
        # e.g., [data-testid="..."], [name="..."]
        if '[' in selector:
            return 0.6
        
        # Tag only (lowest specificity)
        # e.g., div, span, a
        return 0.3
    
    def _calculate_dom_similarity(
        self,
        selector: str,
        snapshot_id: int,
    ) -> float:
        """Calculate DOM similarity between proposed and failed selector.
        
        This analyzes how similar the proposed selector is to the original
        failed selector in terms of DOM structure. More similar selectors
        are more likely to work in similar contexts.
        
        Args:
            selector: The proposed selector string
            snapshot_id: ID of the DOM snapshot to analyze
            
        Returns:
            DOM similarity score between 0.0 and 1.0
        """
        if not self.snapshot_repository:
            return 0.5  # Neutral score if no repository
        
        try:
            # Get snapshot from repository
            snapshot = self.snapshot_repository.get_by_id(snapshot_id)
            if not snapshot:
                return 0.5
            
            html = snapshot.html_content
            
            # For now, return a simple heuristic based on selector type
            # In production, this would do proper DOM path comparison
            
            # If we can find the element, it's similar
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            element = soup.select_one(selector)
            
            if element:
                # Found the element - moderate similarity
                return 0.7
            else:
                # Element not found - lower similarity
                return 0.4
                
        except Exception as e:
            self._logger.warning(
                "dom_similarity_error",
                selector=selector[:30],
                error=str(e)
            )
            return 0.5  # Neutral on error
    
    def rank_selectors(
        self,
        selectors: List[AlternativeSelector],
    ) -> List[AlternativeSelector]:
        """Sort selectors by confidence score (highest first).
        
        Args:
            selectors: List of AlternativeSelector objects to sort
            
        Returns:
            Sorted list with highest confidence first
        """
        return sorted(
            selectors,
            key=lambda s: s.confidence_score,
            reverse=True,
        )
    
    def add_historical_data(
        self,
        selector_string: str,
        stability_score: float,
        sport: Optional[str] = None,
    ):
        """Add historical stability data for a selector.
        
        This allows the system to learn from selector performance over time.
        
        Args:
            selector_string: The selector string
            stability_score: Historical stability score (0.0 to 1.0)
            sport: Optional sport context
        """
        cache_key = f"{sport}:{selector_string}" if sport else selector_string
        self._historical_data[cache_key] = max(0.0, min(1.0, stability_score))
        
        self._logger.info(
            "historical_data_added",
            selector=selector_string[:30],
            score=stability_score,
            sport=sport,
        )
    
    def update_strategy_metrics(
        self,
        selector_name: str,
        strategy_id: str,
        metrics: Dict[str, Any],
    ):
        """Update historical metrics for a selector strategy.
        
        This method is called by StabilityScoringService to record selector performance.
        
        Args:
            selector_name: Name of the selector
            strategy_id: ID of the strategy being used
            metrics: Dictionary containing performance metrics
        """
        # Store strategy-level metrics for historical lookup
        # Uses a composite key to avoid collisions with simple selector keys
        strategy_key = f"__strategy:{strategy_id}"
        self._historical_data[strategy_key] = metrics
        
        self._logger.info(
            "strategy_metrics_updated",
            selector=selector_name[:30],
            strategy=strategy_id,
            metrics=metrics,
        )
    
    def score_custom_selector(
        self,
        selector: AlternativeSelector,
        notes: Optional[str] = None,
    ) -> AlternativeSelector:
        """
        Score a custom (user-created) selector with special considerations.
        
        Custom selectors get a boost because they're created by humans who
        understand the specific context, but we also track them for learning.
        
        Args:
            selector: AlternativeSelector with initial confidence
            notes: Optional notes from the custom selector creator
            
        Returns:
            Enhanced AlternativeSelector with boosted confidence score
        """
        # First calculate base confidence using the standard method
        scored = self.calculate_confidence(selector)
        
        # Apply custom selector boost (human-created selectors tend to be more reliable)
        boosted_score = min(1.0, scored.confidence_score + self.CUSTOM_SELECTOR_BOOST)
        
        # Update the score
        scored.confidence_score = boosted_score
        
        # Recalculate tier if needed
        scored.confidence_tier = ConfidenceTier.from_score(boosted_score)
        
        # Update scoring breakdown if it exists
        if scored.scoring_breakdown:
            scored.scoring_breakdown.final_score = boosted_score
        
        # Mark as custom selector
        scored.is_custom = True
        if notes:
            scored.custom_notes = notes
        
        self._logger.info(
            "custom_selector_scored",
            original_score=scored.confidence_score - self.CUSTOM_SELECTOR_BOOST,
            boosted_score=boosted_score,
            boost_applied=self.CUSTOM_SELECTOR_BOOST,
        )
        
        return scored
    
    def record_custom_selector_feedback(
        self,
        selector: str,
        strategy: StrategyType,
        approved: bool,
        confidence_at_approval: Optional[float] = None,
    ):
        """
        Record feedback from custom selector approval/rejection for learning.
        
        This feeds into Epic 5 (Learning & Weight Adjustment) by tracking
        which custom strategies work and which don't.
        
        Args:
            selector: The custom selector string
            strategy: The strategy type used
            approved: Whether the custom selector was approved
            confidence_at_approval: Confidence score when approved (if approved)
        """
        cache_key = f"custom:{selector}"
        
        if not hasattr(self, '_custom_selector_history'):
            self._custom_selector_history = []
        
        entry = {
            "selector": selector,
            "strategy": strategy.value,
            "approved": approved,
            "recorded_at": datetime.now().isoformat(),
        }
        
        if approved and confidence_at_approval:
            # Store as positive historical data
            self._historical_data[cache_key] = confidence_at_approval
            entry["confidence_score"] = confidence_at_approval
        else:
            # Penalize rejected custom selectors
            self._historical_data[cache_key] = max(
                0.1, 
                (confidence_at_approval or 0.5) - self.CUSTOM_SELECTOR_REJECTION_PENALTY
            )
        
        self._custom_selector_history.append(entry)
        
        self._logger.info(
            "custom_selector_feedback_recorded",
            strategy=strategy.value,
            approved=approved,
            selector_length=len(selector),
        )
    
    def record_positive_feedback(
        self,
        selector: str,
        strategy: StrategyType,
        approved: bool = True,
        confidence_at_approval: Optional[float] = None,
    ) -> None:
        """
        Record positive feedback from selector approval for learning.
        
        This implements Epic 5 (Learning & Weight Adjustment) by:
        1. Tracking approval count per strategy type
        2. Applying boost to the approved strategy's base confidence
        3. Applying slight boost to related strategies (CSS→XPath, etc.)
        4. Persisting learned weights for future confidence calculations
        
        Args:
            selector: The approved selector string
            strategy: The strategy type used
            approved: Whether the selector was approved (True for approvals)
            confidence_at_approval: Confidence score at time of approval
        """
        strategy_key = strategy.value
        
        # Initialize or update approval weights for this strategy
        if strategy_key not in self._approval_weights:
            self._approval_weights[strategy_key] = {
                'count': 0,
                'last_approval': None,
                'total_boost': 0.0,
            }
        
        approval_data = self._approval_weights[strategy_key]
        approval_data['count'] += 1
        approval_data['last_approval'] = datetime.now().isoformat()
        
        # Calculate and apply boost for this strategy
        # Boost scales with approval count, capped at MAX_APPROVAL_BOOST
        new_boost = min(
            self.MAX_APPROVAL_BOOST,
            approval_data['count'] * self.APPROVAL_BOOST_AMOUNT
        )
        approval_data['total_boost'] = new_boost
        
        # Update historical data with boosted confidence
        cache_key = f"approval:{selector}"
        base_confidence = confidence_at_approval or self.STRATEGY_DEFAULTS.get(strategy, 0.5)
        boosted_confidence = min(1.0, base_confidence + new_boost)
        self._historical_data[cache_key] = boosted_confidence
        
        # Also update strategy-specific historical lookup
        strategy_cache_key = f"strategy:{strategy_key}"
        self._historical_data[strategy_cache_key] = boosted_confidence
        
        # Apply boost to related strategies (Task 3: Similar Strategy Boost)
        related_boosts = self.STRATEGY_RELATIONSHIPS.get(strategy, {})
        for related_strategy, boost_amount in related_boosts.items():
            related_key = related_strategy.value
            
            # Initialize related strategy if not exists
            if related_key not in self._approval_weights:
                self._approval_weights[related_key] = {
                    'count': 0,
                    'last_approval': None,
                    'total_boost': 0.0,
                    'related_boost': 0.0,
                }
            
            # Add related strategy boost to the RELATED strategy's related_boost field
            # This represents boost COMING FROM related strategies
            current_related_boost = self._approval_weights[related_key].get('related_boost', 0.0)
            self._approval_weights[related_key]['related_boost'] = min(
                self.MAX_APPROVAL_BOOST,
                current_related_boost + boost_amount
            )
            
            # Update related strategy historical data
            related_cache_key = f"strategy:{related_key}"
            base_related = self.STRATEGY_DEFAULTS.get(related_strategy, 0.5)
            related_boost_total = self._approval_weights[related_key].get('total_boost', 0.0) + \
                                  self._approval_weights[related_key].get('related_boost', 0.0)
            boosted_related = min(1.0, base_related + related_boost_total)
            self._historical_data[related_cache_key] = boosted_related
        
        self._logger.info(
            "positive_feedback_recorded",
            selector=selector[:30],
            strategy=strategy_key,
            approval_count=approval_data['count'],
            boost_applied=new_boost,
            related_strategies=[s.value for s in related_boosts.keys()],
        )
        
        # Persist the updated weights to database
        self._persist_weights(strategy_key, approval_data)
        
        # Also persist related strategy weights
        for related_key in self._approval_weights:
            if related_key != strategy_key and 'related_boost' in self._approval_weights[related_key]:
                self._persist_weights(related_key, self._approval_weights[related_key])
    
    def get_approval_weights(self) -> Dict[str, Any]:
        """
        Get current approval weights for all strategies.
        
        Returns:
            Dictionary mapping strategy names to their approval data
        """
        return dict(self._approval_weights)
    
    def get_strategy_boost(self, strategy: StrategyType) -> float:
        """
        Get the total boost for a specific strategy from approvals.
        
        Args:
            strategy: The strategy type to get boost for
            
        Returns:
            Total boost (direct + related) for the strategy
        """
        strategy_key = strategy.value
        if strategy_key not in self._approval_weights:
            return 0.0
        
        weights = self._approval_weights[strategy_key]
        direct_boost = weights.get('total_boost', 0.0)
        related_boost = weights.get('related_boost', 0.0)
        
        return direct_boost + related_boost
    
    def load_weights(self, weights_data: Dict[str, Any]):
        """
        Load approval weights from persisted storage.
        
        Args:
            weights_data: Dictionary containing approval weights
        """
        if not weights_data:
            return
        
        self._approval_weights = weights_data
        
        # Rebuild related strategy boosts from loaded data
        for strategy_key, data in weights_data.items():
            try:
                strategy = StrategyType(strategy_key)
                related_boosts = self.STRATEGY_RELATIONSHIPS.get(strategy, {})
                
                for related_strategy in related_boosts.keys():
                    related_key = related_strategy.value
                    if related_key not in self._approval_weights:
                        continue
                    
                    # Recalculate related boost based on relationships
                    related_base = self._approval_weights[related_key].get('total_boost', 0.0)
                    self._approval_weights[related_key]['related_boost'] = related_base * 0.5
            except ValueError:
                # Unknown strategy, skip
                pass
        
        self._logger.info("weights_loaded", strategy_count=len(weights_data))
    
    def export_weights(self) -> Dict[str, Any]:
        """
        Export approval weights for persistence.
        
        Returns:
            Dictionary containing all approval weights
        """
        return dict(self._approval_weights)
    
    def _load_persisted_weights(self):
        """
        Load persisted weights from the database on initialization.
        Only loads if weight_repository is explicitly provided.
        """
        # Only attempt to load if repository was explicitly provided
        if self.weight_repository is None:
            # Skip loading - will use in-memory weights only
            return
        
        try:
            persisted_weights = self.weight_repository.load_weights_for_scorer()
            
            if persisted_weights:
                self._approval_weights = persisted_weights
                self._logger.info(
                    "persisted_weights_loaded",
                    strategy_count=len(persisted_weights)
                )
        except Exception as e:
            self._logger.warning(
                "failed_to_load_persisted_weights",
                error=str(e)
            )
    
    def _persist_weights(self, strategy_key: str, approval_data: Dict[str, Any]):
        """
        Persist weights to the database.
        
        Args:
            strategy_key: The strategy type key
            approval_data: The approval weight data
        """
        try:
            if self.weight_repository is None:
                self.weight_repository = get_weight_repository()
            
            self.weight_repository.upsert_approval_weight(
                strategy_type=strategy_key,
                approval_count=approval_data.get('count', 0),
                total_boost=approval_data.get('total_boost', 0.0),
                related_boost=approval_data.get('related_boost', 0.0),
            )
            
            self._logger.debug(
                "weights_persisted",
                strategy=strategy_key,
                count=approval_data.get('count', 0),
            )
        except Exception as e:
            self._logger.warning(
                "failed_to_persist_weights",
                strategy=strategy_key,
                error=str(e)
            )
    
    # ==================== REJECTION LEARNING (STORY 5.2) ====================
    
    def record_negative_feedback(
        self,
        selector: str,
        strategy: StrategyType,
        rejection_reason: Optional[str] = None,
        confidence_at_rejection: Optional[float] = None,
    ):
        """
        Record negative feedback from selector rejection for learning.
        
        This implements Epic 5 (Learning & Weight Adjustment) for negative feedback:
        1. Tracking rejection count per strategy type
        2. Applying penalty to the rejected strategy's base confidence
        3. Applying slight penalty to related strategies (CSS→XPath, etc.)
        4. Parsing rejection reason for pattern extraction
        5. Persisting learned rejection weights for future confidence calculations
        
        Args:
            selector: The rejected selector string
            strategy: The strategy type used
            rejection_reason: Reason for rejection (optional, for pattern analysis)
            confidence_at_rejection: Confidence score at time of rejection
        """
        strategy_key = strategy.value
        
        # Initialize or update rejection weights for this strategy
        if strategy_key not in self._rejection_weights:
            self._rejection_weights[strategy_key] = {
                'count': 0,
                'last_rejection': None,
                'total_penalty': 0.0,
            }
        
        rejection_data = self._rejection_weights[strategy_key]
        rejection_data['count'] += 1
        rejection_data['last_rejection'] = datetime.now().isoformat()
        
        # Calculate and apply penalty for this strategy
        # Penalty scales with rejection count, capped at MAX_REJECTION_PENALTY
        new_penalty = min(
            self.MAX_REJECTION_PENALTY,
            rejection_data['count'] * self.REJECTION_PENALTY_AMOUNT
        )
        rejection_data['total_penalty'] = new_penalty
        
        # Update historical data with penalized confidence
        cache_key = f"rejection:{selector}"
        base_confidence = confidence_at_rejection or self.STRATEGY_DEFAULTS.get(strategy, 0.5)
        penalized_confidence = max(self.MIN_CONFIDENCE_FLOOR, base_confidence - new_penalty)
        self._historical_data[cache_key] = penalized_confidence
        
        # Also update strategy-specific historical lookup
        strategy_cache_key = f"strategy:{strategy_key}"
        self._historical_data[strategy_cache_key] = penalized_confidence
        
        # Parse rejection reason for pattern extraction (Task 3)
        reason_pattern = self._parse_rejection_reason(rejection_reason)
        
        # Apply penalty to related strategies (Task 3: Similar Strategy Penalty)
        related_penalties = self.STRATEGY_RELATIONSHIPS.get(strategy, {})
        for related_strategy, penalty_amount in related_penalties.items():
            related_key = related_strategy.value
            
            # Initialize related strategy if not exists
            if related_key not in self._rejection_weights:
                self._rejection_weights[related_key] = {
                    'count': 0,
                    'last_rejection': None,
                    'total_penalty': 0.0,
                    'related_penalty': 0.0,
                }
            
            # Add related strategy penalty to the RELATED strategy's related_penalty field
            current_related_penalty = self._rejection_weights[related_key].get('related_penalty', 0.0)
            self._rejection_weights[related_key]['related_penalty'] = min(
                self.MAX_REJECTION_PENALTY,
                current_related_penalty + penalty_amount
            )
            
            # Update related strategy historical data
            related_cache_key = f"strategy:{related_key}"
            base_related = self.STRATEGY_DEFAULTS.get(related_strategy, 0.5)
            related_penalty_total = self._rejection_weights[related_key].get('total_penalty', 0.0) + \
                                  self._rejection_weights[related_key].get('related_penalty', 0.0)
            penalized_related = max(self.MIN_CONFIDENCE_FLOOR, base_related - related_penalty_total)
            self._historical_data[related_cache_key] = penalized_related
        
        self._logger.info(
            "negative_feedback_recorded",
            selector=selector[:30],
            strategy=strategy_key,
            rejection_count=rejection_data['count'],
            penalty_applied=new_penalty,
            reason_pattern=reason_pattern,
            related_strategies=[s.value for s in related_penalties.keys()],
        )
        
        # Persist the updated rejection weights to database
        self._persist_rejection_weights(strategy_key, rejection_data)
        
        # Also persist related strategy rejection weights
        for related_key in self._rejection_weights:
            if related_key != strategy_key and 'related_penalty' in self._rejection_weights[related_key]:
                self._persist_rejection_weights(related_key, self._rejection_weights[related_key])
    
    def _parse_rejection_reason(self, reason: Optional[str]) -> Optional[str]:
        """
        Parse rejection reason to extract pattern for learning.
        
        Args:
            reason: The raw rejection reason string
            
        Returns:
            Parsed pattern key or None
        """
        if not reason:
            return None
        
        reason_lower = reason.lower().strip()
        
        # Match against known patterns
        if 'too specific' in reason_lower or 'overly specific' in reason_lower:
            return 'too_specific'
        elif 'too generic' in reason_lower or 'not specific enough' in reason_lower:
            return 'too_generic'
        elif 'wrong element' in reason_lower or 'incorrect element' in reason_lower:
            return 'wrong_element'
        elif 'fragile' in reason_lower:
            return 'fragile'
        elif 'not stable' in reason_lower or 'unstable' in reason_lower:
            return 'not_stable'
        else:
            return 'custom'
    
    def get_rejection_weights(self) -> Dict[str, Any]:
        """
        Get current rejection weights for all strategies.
        
        Returns:
            Dictionary mapping strategy names to their rejection data
        """
        return dict(self._rejection_weights)
    
    def get_strategy_penalty(self, strategy: StrategyType) -> float:
        """
        Get the total penalty for a specific strategy from rejections.
        
        Args:
            strategy: The strategy type to get penalty for
            
        Returns:
            Total penalty (direct + related) for the strategy
        """
        strategy_key = strategy.value
        if strategy_key not in self._rejection_weights:
            return 0.0
        
        weights = self._rejection_weights[strategy_key]
        direct_penalty = weights.get('total_penalty', 0.0)
        related_penalty = weights.get('related_penalty', 0.0)
        
        return direct_penalty + related_penalty
    
    def load_rejection_weights(self, weights_data: Dict[str, Any]):
        """
        Load rejection weights from persisted storage.
        
        Args:
            weights_data: Dictionary containing rejection weights
        """
        if not weights_data:
            return
        
        self._rejection_weights = weights_data
        
        self._logger.info("rejection_weights_loaded", strategy_count=len(weights_data))
    
    def export_rejection_weights(self) -> Dict[str, Any]:
        """
        Export rejection weights for persistence.
        
        Returns:
            Dictionary containing all rejection weights
        """
        return dict(self._rejection_weights)
    
    def _load_persisted_rejection_weights(self):
        """
        Load persisted rejection weights from the database on initialization.
        Only loads if weight_repository is explicitly provided.
        """
        if self.weight_repository is None:
            return
        
        try:
            persisted_weights = self.weight_repository.load_rejection_weights_for_scorer()
            
            if persisted_weights:
                self._rejection_weights = persisted_weights
                self._logger.info(
                    "persisted_rejection_weights_loaded",
                    strategy_count=len(persisted_weights)
                )
        except Exception as e:
            self._logger.warning(
                "failed_to_load_persisted_rejection_weights",
                error=str(e)
            )
    
    def _persist_rejection_weights(self, strategy_key: str, rejection_data: Dict[str, Any]):
        """
        Persist rejection weights to the database.
        
        Args:
            strategy_key: The strategy type key
            rejection_data: The rejection weight data
        """
        try:
            if self.weight_repository is None:
                self.weight_repository = get_weight_repository()
            
            self.weight_repository.upsert_rejection_weight(
                strategy_type=strategy_key,
                rejection_count=rejection_data.get('count', 0),
                total_penalty=rejection_data.get('total_penalty', 0.0),
                related_penalty=rejection_data.get('related_penalty', 0.0),
            )
            
            self._logger.debug(
                "rejection_weights_persisted",
                strategy=strategy_key,
                count=rejection_data.get('count', 0),
            )
        except Exception as e:
            self._logger.warning(
                "failed_to_persist_rejection_weights",
                strategy=strategy_key,
                error=str(e)
            )
    
    # ==================== GENERATION TRACKING METHODS (STORY 5.3) ====================
    
    def record_generation_survival(
        self,
        recipe_id: str,
        generation: int,
        sport: Optional[str] = None,
        site: Optional[str] = None,
    ):
        """
        Record that a selector survived a generation change.
        
        This implements AC #1: When selectors survive a layout generation change,
        the generation_survived count should increment.
        
        Args:
            recipe_id: The recipe identifier
            generation: The generation number that was survived
            sport: Optional sport context
            site: Optional site context
        """
        # Initialize generation data for this recipe if not exists
        if recipe_id not in self._generation_data:
            self._generation_data[recipe_id] = {
                'current_generation': generation,
                'generations_survived': 0,
                'generation_failures': 0,
                'consecutive_failures': 0,
                'last_generation_change': datetime.now().isoformat(),
                'first_generation': datetime.now().isoformat(),
                'sport': sport,
                'site': site,
            }
        
        gen_data = self._generation_data[recipe_id]
        
        # If this is a new generation, increment survival count
        if generation > gen_data.get('current_generation', 0):
            gen_data['generations_survived'] = gen_data.get('generations_survived', 0) + 1
            gen_data['current_generation'] = generation
            gen_data['last_generation_change'] = datetime.now().isoformat()
            # Reset consecutive failures on survival
            gen_data['consecutive_failures'] = 0
        
        self._logger.info(
            "generation_survival_recorded",
            recipe_id=recipe_id,
            generation=generation,
            generations_survived=gen_data.get('generations_survived', 0),
        )
        
        # Persist the updated generation data
        self._persist_generation_data(recipe_id, gen_data)
    
    def record_generation_failure(
        self,
        recipe_id: str,
        generation: int,
        selector: Optional[str] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
    ) -> bool:
        """
        Record that a selector failed during a generation.
        
        This implements AC #2: When failure is detected, it should be recorded
        as a generation failure and the recipe should be marked for review after
        consecutive failures threshold.
        
        Args:
            recipe_id: The recipe identifier
            generation: The generation number where failure occurred
            selector: The selector that failed (optional)
            sport: Optional sport context
            site: Optional site context
            
        Returns:
            True if recipe should be marked for review, False otherwise
        """
        # Initialize generation data for this recipe if not exists
        if recipe_id not in self._generation_data:
            self._generation_data[recipe_id] = {
                'current_generation': generation,
                'generations_survived': 0,
                'generation_failures': 0,
                'consecutive_failures': 0,
                'last_generation_change': datetime.now().isoformat(),
                'first_generation': datetime.now().isoformat(),
                'sport': sport,
                'site': site,
            }
        
        gen_data = self._generation_data[recipe_id]
        
        # Increment failure counts
        gen_data['generation_failures'] = gen_data.get('generation_failures', 0) + 1
        gen_data['consecutive_failures'] = gen_data.get('consecutive_failures', 0) + 1
        
        self._logger.info(
            "generation_failure_recorded",
            recipe_id=recipe_id,
            generation=generation,
            consecutive_failures=gen_data['consecutive_failures'],
            total_failures=gen_data['generation_failures'],
        )
        
        # Persist the updated generation data
        self._persist_generation_data(recipe_id, gen_data)
        
        # Check if recipe should be marked for review
        should_mark_review = (
            gen_data['consecutive_failures'] >= self.CONSECUTIVE_FAILURES_FOR_REVIEW
        )
        
        if should_mark_review:
            self._logger.warning(
                "recipe_marked_for_review",
                recipe_id=recipe_id,
                consecutive_failures=gen_data['consecutive_failures'],
                threshold=self.CONSECUTIVE_FAILURES_FOR_REVIEW,
            )
        
        return should_mark_review
    
    def detect_generation_change(
        self,
        recipe_id: str,
        current_generation: int,
    ) -> bool:
        """
        Detect if a generation change has occurred for a recipe.
        
        Args:
            recipe_id: The recipe identifier
            current_generation: The current generation number from the recipe
            
        Returns:
            True if a new generation was detected, False otherwise
        """
        if recipe_id not in self._generation_data:
            return False  # First time seeing this recipe
        
        stored_generation = self._generation_data[recipe_id].get('current_generation', 0)
        return current_generation > stored_generation
    
    def calculate_generation_stability(
        self,
        recipe_id: str,
    ) -> float:
        """
        Calculate stability score based on generation survival.
        
        This implements AC #1: The stability score should reflect the survival rate.
        
        Formula: survival_rate = generations_survived / total_generations
        Stability = 1.0 + (GENERATION_WEIGHT * survival_rate)
        
        Args:
            recipe_id: The recipe identifier
            
        Returns:
            Stability score (typically 0.85 to 1.25 based on survival)
        """
        if recipe_id not in self._generation_data:
            return 1.0  # Default neutral stability
        
        gen_data = self._generation_data[recipe_id]
        generations_survived = gen_data.get('generations_survived', 0)
        current_generation = gen_data.get('current_generation', 1)
        
        # Calculate survival rate
        if current_generation == 0:
            return 1.0
        
        survival_rate = generations_survived / max(1, current_generation)
        
        # Calculate stability with generation weight
        # Higher survival = higher stability
        stability = 1.0 + (self.GENERATION_WEIGHT * survival_rate)
        
        # Cap at reasonable bounds
        stability = max(0.5, min(1.5, stability))
        
        return stability
    
    def get_generation_data(
        self,
        recipe_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get generation tracking data for a recipe.
        
        Args:
            recipe_id: The recipe identifier
            
        Returns:
            Dictionary with generation data or None if not found
        """
        return self._generation_data.get(recipe_id)
    
    def get_all_generation_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all generation tracking data.
        
        Returns:
            Dictionary mapping recipe IDs to their generation data
        """
        return dict(self._generation_data)
    
    def should_mark_recipe_for_review(
        self,
        recipe_id: str,
    ) -> bool:
        """
        Check if a recipe should be marked for review based on failures.
        
        Args:
            recipe_id: The recipe identifier
            
        Returns:
            True if recipe should be marked for review
        """
        if recipe_id not in self._generation_data:
            return False
        
        gen_data = self._generation_data[recipe_id]
        return gen_data.get('consecutive_failures', 0) >= self.CONSECUTIVE_FAILURES_FOR_REVIEW
    
    def reset_generation_failures(
        self,
        recipe_id: str,
    ):
        """
        Reset consecutive failure count after successful recovery.
        
        Args:
            recipe_id: The recipe identifier
        """
        if recipe_id in self._generation_data:
            self._generation_data[recipe_id]['consecutive_failures'] = 0
            self._persist_generation_data(recipe_id, self._generation_data[recipe_id])
    
    def get_generation_boost(self, recipe_id: str) -> float:
        """
        Get the confidence boost from generation survival for a recipe.
        
        Args:
            recipe_id: The recipe identifier
            
        Returns:
            Confidence boost from generation survival (0.0 to MAX_GENERATION_BOOST)
        """
        if recipe_id not in self._generation_data:
            return 0.0
        
        gen_data = self._generation_data[recipe_id]
        generations_survived = gen_data.get('generations_survived', 0)
        
        # Calculate boost based on generations survived
        boost = generations_survived * self.GENERATION_SURVIVAL_BOOST
        
        return min(self.MAX_GENERATION_BOOST, boost)
    
    def export_generation_data(self) -> Dict[str, Any]:
        """
        Export generation tracking data for persistence.
        
        Returns:
            Dictionary containing all generation tracking data
        """
        return dict(self._generation_data)
    
    def load_generation_data(self, generation_data: Dict[str, Dict[str, Any]]):
        """
        Load generation tracking data from persisted storage.
        
        Args:
            generation_data: Dictionary containing generation tracking data
        """
        if not generation_data:
            return
        
        self._generation_data = generation_data
        self._logger.info("generation_data_loaded", recipe_count=len(generation_data))
    
    def _load_persisted_generation_data(self):
        """
        Load persisted generation data from the database on initialization.
        """
        if self.weight_repository is None:
            return
        
        try:
            persisted_data = self.weight_repository.load_generation_data_for_scorer()
            
            if persisted_data:
                self._generation_data = persisted_data
                self._logger.info(
                    "persisted_generation_data_loaded",
                    recipe_count=len(persisted_data)
                )
        except Exception as e:
            self._logger.warning(
                "failed_to_load_persisted_generation_data",
                error=str(e)
            )
    
    def _persist_generation_data(self, recipe_id: str, gen_data: Dict[str, Any]):
        """
        Persist generation data to the database.
        
        Args:
            recipe_id: The recipe identifier
            gen_data: The generation data dictionary
        """
        try:
            if self.weight_repository is None:
                self.weight_repository = get_weight_repository()
            
            self.weight_repository.upsert_generation_data(
                recipe_id=recipe_id,
                current_generation=gen_data.get('current_generation', 1),
                generations_survived=gen_data.get('generations_survived', 0),
                generation_failures=gen_data.get('generation_failures', 0),
                consecutive_failures=gen_data.get('consecutive_failures', 0),
                sport=gen_data.get('sport'),
                site=gen_data.get('site'),
            )
            
            self._logger.debug(
                "generation_data_persisted",
                recipe_id=recipe_id,
                generation=gen_data.get('current_generation', 1),
            )
        except Exception as e:
            self._logger.warning(
                "failed_to_persist_generation_data",
                recipe_id=recipe_id,
                error=str(e)
            )
