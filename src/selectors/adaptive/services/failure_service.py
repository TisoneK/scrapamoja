"""
Failure Service for managing selector failures and proposed alternatives.

This service provides business logic for the failures API endpoints,
including fetching failure details with alternatives, confidence scores,
and blast radius calculations.

Story: 4.1 - View Proposed Selectors with Visual Preview
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import logging

from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository
from src.selectors.adaptive.db.repositories.recipe_repository import RecipeRepository
from src.selectors.adaptive.db.repositories.audit_event_repository import AuditEventRepository
from src.selectors.adaptive.services.confidence_scorer import ConfidenceScorer
from src.selectors.adaptive.services.blast_radius import (
    BlastRadiusCalculator, 
    BlastRadiusResult,
    SeverityLevel,
)
from src.selectors.adaptive.services.dom_analyzer import AlternativeSelector, StrategyType

from src.observability.logger import get_logger


class FailureService:
    """
    Service for managing selector failures and alternative proposals.
    
    This service:
    - Fetches failure events with their details
    - Provides proposed alternative selectors
    - Calculates confidence scores for alternatives
    - Calculates blast radius for impact assessment
    """
    
    def __init__(
        self,
        failure_repository: Optional[FailureEventRepository] = None,
        confidence_scorer: Optional[ConfidenceScorer] = None,
        blast_radius_calculator: Optional[BlastRadiusCalculator] = None,
        recipe_repository: Optional[RecipeRepository] = None,
        audit_repository: Optional[AuditEventRepository] = None,
    ):
        """
        Initialize the failure service.
        
        Args:
            failure_repository: Repository for failure events (creates default if None)
            confidence_scorer: Service for confidence scoring
            blast_radius_calculator: Service for blast radius calculation
            recipe_repository: Repository for recipe CRUD operations
            audit_repository: Repository for audit logging (Story 4.2 implementation)
        """
        self._logger = get_logger("failure_service")
        
        # Use provided or create default repository
        self.failure_repository = failure_repository or FailureEventRepository()
        
        # Use provided or create default services
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.blast_radius_calculator = blast_radius_calculator or BlastRadiusCalculator()
        
        # Recipe repository for selector updates
        self.recipe_repository = recipe_repository or RecipeRepository()
        
        # Audit repository for proper database logging (Story 4.2)
        self.audit_repository = audit_repository or AuditEventRepository()
        
        # TODO(Story 4.2): Replace with database table for persistence
        # Currently in-memory only - data lost on restart
        # Requires: Epic 7 (Escalation UI) database models
        self._alternatives: Dict[int, List[AlternativeSelector]] = {}
        
        # Storage for snapshot references (in-memory for MVP)
        # TODO(Story 4.2): Replace with database table for persistence
        # Currently in-memory only - data lost on restart
        self._snapshot_references: Dict[int, int] = {}
        
        # Storage for flagged failures (database-backed for Story 4.3)
        # Replaces in-memory storage with proper database persistence
        self._flagged_failures_cache: Dict[int, Dict[str, Any]] = {}
    
    def register_alternative(
        self,
        failure_id: int,
        selector: str,
        strategy: StrategyType,
        snapshot_id: Optional[int] = None,
    ) -> AlternativeSelector:
        """
        Register an alternative selector for a failure.
        
        Args:
            failure_id: The failure event ID
            selector: The alternative selector string
            strategy: The strategy type used
            snapshot_id: Optional snapshot ID for DOM analysis
            
        Returns:
            The registered alternative with confidence score
        """
        # Create alternative selector with initial confidence
        alt_selector = AlternativeSelector(
            selector_string=selector,
            strategy_type=strategy,
            confidence_score=0.5,  # Placeholder, will be calculated
            element_description=f"Alternative selector: {selector[:50]}...",
        )
        
        # Calculate refined confidence score
        scored_selector = self.confidence_scorer.calculate_confidence(
            selector=alt_selector,
            snapshot_id=snapshot_id,
        )
        
        # Store the alternative
        if failure_id not in self._alternatives:
            self._alternatives[failure_id] = []
        self._alternatives[failure_id].append(scored_selector)
        
        # Store snapshot reference if provided
        if snapshot_id:
            self._snapshot_references[failure_id] = snapshot_id
        
        self._logger.info(
            "alternative_registered",
            failure_id=failure_id,
            selector=selector[:50],
            confidence=scored_selector.confidence_score,
        )
        
        return scored_selector
    
    def get_failure_detail(
        self,
        failure_id: int,
        include_alternatives: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a failure event.
        
        Args:
            failure_id: The failure event ID
            include_alternatives: Whether to include proposed alternatives
            
        Returns:
            Dictionary with failure details or None if not found
        """
        # Fetch failure event from repository
        failure = self.failure_repository.get_by_id(failure_id)
        
        if not failure:
            self._logger.warning("failure_not_found", failure_id=failure_id)
            return None
        
        # Build base response from failure event
        result = {
            "failure_id": failure.id,
            "selector_id": failure.selector_id,
            "failed_selector": failure.selector_id,  # Use selector_id as the failed selector
            "recipe_id": failure.recipe_id,
            "sport": failure.sport,
            "site": failure.site,
            "timestamp": failure.timestamp.isoformat() if failure.timestamp else None,
            "error_type": failure.error_type,
            "failure_reason": failure.failure_reason,
            "severity": failure.severity or "minor",
            "snapshot_id": self._snapshot_references.get(failure_id),
            "alternatives": [],
            "flagged": False,
            "flag_note": None,
            "flagged_at": None,
        }
        
        # Add flag info if present
        flag_info = self._load_flagged_failure(failure_id)
        if flag_info:
            result["flagged"] = flag_info.get("flagged", False)
            result["flag_note"] = flag_info.get("note")
            result["flagged_at"] = flag_info.get("flagged_at")
        
        # Add alternatives if requested and available
        if include_alternatives and failure_id in self._alternatives:
            alternatives = self._alternatives[failure_id]
            
            # Get HTML content for blast radius calculation if snapshot exists
            snapshot_id = self._snapshot_references.get(failure_id)
            html_content = None
            if snapshot_id:
                # Try to get HTML from snapshot repository (if available)
                # For now, we'll calculate blast radius without it
                pass
            
            for alt in alternatives:
                # Calculate blast radius if we have HTML
                blast_radius = None
                if html_content:
                    # This would be async in production
                    pass
                
                alt_dict = {
                    "selector": alt.selector_string,
                    "strategy": alt.strategy_type.value if hasattr(alt.strategy_type, 'value') else str(alt.strategy_type),
                    "confidence_score": alt.confidence_score,
                    "blast_radius": blast_radius,
                    "highlight_css": self._generate_highlight_css(alt.selector_string),
                    # Custom selector fields (Story 4.4)
                    "is_custom": getattr(alt, 'is_custom', False),
                    "custom_notes": getattr(alt, 'custom_notes', None),
                }
                result["alternatives"].append(alt_dict)
        
        return result
    
    def list_failures(
        self,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        error_type: Optional[str] = None,
        severity: Optional[str] = None,
        flagged: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List failure events with filtering and pagination.
        
        Args:
            sport: Optional sport filter
            site: Optional site filter
            error_type: Optional error type filter
            severity: Optional severity filter
            flagged: Optional flagged status filter
            date_from: Optional start date filter
            date_to: Optional end date filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Tuple of (list of failure summaries, total count)
        """
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Fetch failures from repository
        failures = self.failure_repository.find_with_filters(
            sport=sport,
            date_from=date_from,
            date_to=date_to,
            error_type=error_type,
            site=site,
            limit=page_size,
            offset=offset,
        )
        
        # Build summary list
        results = []
        for failure in failures:
            failure_id = failure.id
            has_alternatives = failure_id in self._alternatives and len(self._alternatives[failure_id]) > 0
            
            # Get flag info if present
            flag_info = self._load_flagged_failure(failure_id)
            
            # Apply flagged filter if specified
            if flagged is not None and flag_info.get("flagged", False) != flagged:
                continue
            
            results.append({
                "failure_id": failure.id,
                "selector_id": failure.selector_id,
                "failed_selector": failure.selector_id,
                "sport": failure.sport,
                "site": failure.site,
                "timestamp": failure.timestamp.isoformat() if failure.timestamp else None,
                "error_type": failure.error_type,
                "severity": failure.severity or "minor",
                "has_alternatives": has_alternatives,
                "alternative_count": len(self._alternatives.get(failure_id, [])),
                "flagged": flag_info.get("flagged", False),
                "flag_note": flag_info.get("note"),
            })
        
        # Get total count (simplified - in production would be a proper count query)
        total = len(results)  # This is approximate for MVP
        
        return results, total
    
    def approve_alternative(
        self,
        failure_id: int,
        selector: str,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Approve an alternative selector.
        
        Args:
            failure_id: The failure event ID
            selector: The selector to approve
            notes: Optional approval notes
            user_id: Optional user ID for audit logging
            
        Returns:
            Result dictionary
        """
        # Verify the alternative exists
        alternatives = self._alternatives.get(failure_id, [])
        matching = [a for a in alternatives if a.selector_string == selector]
        
        if not matching:
            return {
                "success": False,
                "message": f"No alternative found with selector: {selector}",
                "selector": selector,
                "failure_id": failure_id,
            }
        
        alternative = matching[0]
        
        # Get the failure event to find recipe_id
        failure_event = self.failure_repository.get_by_id(failure_id)
        recipe_id = failure_event.recipe_id if failure_event else None
        before_selector = failure_event.selector_id if failure_event else None
        
        # Get current recipe for version tracking
        current_recipe = None
        new_version = 1
        if recipe_id:
            current_recipe = self.recipe_repository.get_latest_version(recipe_id)
            if current_recipe:
                new_version = current_recipe.version + 1
        
        # TASK 1.1 & 1.2: Update recipe with new selector and increment version
        updated_selectors = {}
        if current_recipe and current_recipe.selectors:
            updated_selectors = dict(current_recipe.selectors)
            # Find the selector key to update (simplified - in production would be more sophisticated)
            selector_key = self._find_selector_key(updated_selectors, before_selector or "")
            
            if selector_key:
                # Update the selector with approved alternative
                updated_selectors[selector_key] = {
                    "css": selector,
                    "strategy": alternative.strategy_type.value,
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                }
                self._logger.info(
                    "recipe_selector_updated",
                    recipe_id=recipe_id,
                    selector_key=selector_key,
                    old_selector=before_selector[:50] if before_selector else None,
                    new_selector=selector[:50],
                )
            else:
                # Selector key not found - log warning but continue with best effort
                self._logger.warning(
                    "selector_key_not_found",
                    recipe_id=recipe_id,
                    failure_id=failure_id,
                    before_selector=before_selector[:50] if before_selector else None,
                    available_keys=list(updated_selectors.keys()),
                    action="adding_new_selector_key",
                )
                # Add new selector key as fallback
                new_key = f"selector_{len(updated_selectors) + 1}"
                updated_selectors[new_key] = {
                    "css": selector,
                    "strategy": alternative.strategy_type.value,
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                    "auto_added": True,  # Flag that this was auto-added
                }
        else:
            # No existing selectors or recipe - create new entry
            self._logger.warning(
                "no_existing_selectors_found",
                recipe_id=recipe_id,
                failure_id=failure_id,
                action="creating_new_selector_entry",
            )
            updated_selectors = {
                "selector_1": {
                    "css": selector,
                    "strategy": alternative.strategy_type.value,
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                    "auto_added": True,
                }
            }
        
        # Create new recipe version with updated selectors
        if recipe_id and updated_selectors:
            self.recipe_repository.create_new_version(
                recipe_id=recipe_id,
                selectors=updated_selectors,
                parent_recipe_id=recipe_id,
                generation=(current_recipe.generation or 0) + 1 if current_recipe else 1,
            )
        
        # TASK 2: Record approval in audit log
        self._record_audit_event(
            action_type="selector_approved",
            failure_id=failure_id,
            selector=selector,
            user_id=user_id,
            before_state=before_selector,
            after_state=selector,
            confidence_at_time=alternative.confidence_score,
            notes=notes,
        )
        
        # TASK 3: Update confidence scorer with positive feedback
        self._record_positive_feedback(
            selector=selector,
            strategy=alternative.strategy_type,
        )
        
        self._logger.info(
            "alternative_approved",
            failure_id=failure_id,
            selector=selector[:50],
            notes=notes,
            recipe_id=recipe_id,
            new_version=new_version,
        )
        
        return {
            "success": True,
            "message": "Selector approved successfully",
            "selector": selector,
            "failure_id": failure_id,
            "recipe_id": recipe_id,
            "new_version": new_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def reject_alternative(
        self,
        failure_id: int,
        selector: str,
        reason: str,
        suggested_alternative: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reject an alternative selector.
        
        Args:
            failure_id: The failure event ID
            selector: The selector to reject
            reason: Reason for rejection
            suggested_alternative: Optional suggested alternative
            user_id: Optional user ID for audit logging
            
        Returns:
            Result dictionary
        """
        # Verify the alternative exists
        alternatives = self._alternatives.get(failure_id, [])
        matching = [a for a in alternatives if a.selector_string == selector]
        
        if not matching:
            return {
                "success": False,
                "message": f"No alternative found with selector: {selector}",
                "selector": selector,
                "failure_id": failure_id,
            }
        
        alternative = matching[0]
        
        # Get the failure event
        failure_event = self.failure_repository.get_by_id(failure_id)
        
        # TASK 2: Record rejection in audit log
        self._record_audit_event(
            action_type="selector_rejected",
            failure_id=failure_id,
            selector=selector,
            user_id=user_id,
            reason=reason,
            suggested_alternative=suggested_alternative,
            confidence_at_time=alternative.confidence_score,
        )
        
        # TASK 3: Update confidence scorer with negative feedback
        self._record_negative_feedback(
            selector=selector,
            strategy=alternative.strategy_type,
            reason=reason,
        )
        
        self._logger.info(
            "alternative_rejected",
            failure_id=failure_id,
            selector=selector[:50],
            reason=reason,
            suggested_alternative=suggested_alternative,
        )
        
        return {
            "success": True,
            "message": "Selector rejected",
            "selector": selector,
            "failure_id": failure_id,
            "reason": reason,
            "suggested_alternative": suggested_alternative,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def flag_failure(
        self,
        failure_id: int,
        note: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flag a failure for developer review.
        
        Args:
            failure_id: The failure event ID
            note: Note explaining why this needs developer review
            user_id: Optional user ID for audit logging
            
        Returns:
            Result dictionary
        """
        # Input validation
        if not note or not note.strip():
            return {
                "success": False,
                "message": "Flag note is required and cannot be empty",
                "failure_id": failure_id,
            }
        
        if len(note) > 1000:
            return {
                "success": False,
                "message": "Flag note must be less than 1000 characters",
                "failure_id": failure_id,
            }
        
        # Verify failure exists
        failure = self.failure_repository.get_by_id(failure_id)
        if not failure:
            return {
                "success": False,
                "message": f"Failure with ID {failure_id} not found",
                "failure_id": failure_id,
            }
        
        # Check if already flagged (allow updating the note)
        existing_flag = self._load_flagged_failure(failure_id)
        if existing_flag and existing_flag.get("flagged", False):
            # Update existing flag with new note
            flag_info = {
                "flagged": True,
                "note": note,
                "flagged_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
            }
            
            # Save to database
            if self._save_flagged_failure(failure_id, flag_info):
                # Update cache
                self._flagged_failures_cache[failure_id] = flag_info
            
            self._logger.info(
                "failure_flag_updated",
                failure_id=failure_id,
                note=note[:100],  # Truncate for logging
                user_id=user_id,
            )
            
            return {
                "success": True,
                "message": "Flag note updated successfully",
                "failure_id": failure_id,
                "flagged": True,
                "flag_note": note,
                "flagged_at": flag_info["flagged_at"],
            }
        
        flagged_at = datetime.now(timezone.utc)
        flag_info = {
            "flagged": True,
            "note": note,
            "flagged_at": flagged_at.isoformat(),
            "user_id": user_id,
        }
        
        # Save to database
        if self._save_flagged_failure(failure_id, flag_info):
            # Update cache
            self._flagged_failures_cache[failure_id] = flag_info
        else:
            # Fallback to in-memory if database fails
            self._flagged_failures_cache[failure_id] = flag_info
            self._logger.warning("flag_fallback_to_memory", failure_id=failure_id)
        
        # Record audit event
        self._record_audit_event(
            action_type="selector_flagged",
            failure_id=failure_id,
            selector=failure.selector_id,
            user_id=user_id,
            notes=note,
        )
        
        self._logger.info(
            "failure_flagged",
            failure_id=failure_id,
            note=note[:100],  # Truncate for logging
            user_id=user_id,
        )
        
        return {
            "success": True,
            "message": "Failure flagged for developer review",
            "failure_id": failure_id,
            "flagged": True,
            "flag_note": note,
            "flagged_at": flagged_at.isoformat(),
        }
    
    def unflag_failure(
        self,
        failure_id: int,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Remove flag from a failure.
        
        Args:
            failure_id: The failure event ID
            user_id: Optional user ID for audit logging
            
        Returns:
            Result dictionary
        """
        # Verify the failure exists
        failure = self.failure_repository.get_by_id(failure_id)
        if not failure:
            return {
                "success": False,
                "message": f"Failure with ID {failure_id} not found",
                "failure_id": failure_id,
            }
        
        # Check if it was flagged
        flag_info = self._load_flagged_failure(failure_id)
        if not flag_info or not flag_info.get("flagged", False):
            return {
                "success": False,
                "message": f"Failure with ID {failure_id} is not flagged",
                "failure_id": failure_id,
            }
        
        # Store unflag info (keep original note for audit)
        unflag_info = {
            "flagged": False,
            "note": flag_info.get("note"),  # Keep original note
            "flagged_at": flag_info.get("flagged_at"),  # Keep original flag time
            "unflagged_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
        }
        
        # Save to database
        if self._save_flagged_failure(failure_id, unflag_info):
            # Update cache
            self._flagged_failures_cache[failure_id] = unflag_info
        else:
            self._logger.warning("unflag_fallback_to_memory", failure_id=failure_id)
        
        # Record audit event
        self._record_audit_event(
            action_type="selector_unflagged",
            failure_id=failure_id,
            selector=failure.selector_id,
            user_id=user_id,
        )
        
        self._logger.info(
            "failure_unflagged",
            failure_id=failure_id,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "message": "Flag removed from failure",
            "failure_id": failure_id,
            "flagged": False,
        }
    
    def create_custom_selector(
        self,
        failure_id: int,
        selector_string: str,
        strategy_type: str,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a custom selector for a failure.
        
        This allows users to manually create alternative selectors when the
        auto-proposal system cannot handle specific edge cases.
        
        Args:
            failure_id: The failure event ID
            selector_string: The custom selector string
            strategy_type: The strategy type (css, xpath, text_anchor, etc.)
            notes: Optional notes about the approach
            user_id: Optional user ID for tracking
            
        Returns:
            Result dictionary with the created selector
        """
        # Verify the failure exists
        failure = self.failure_repository.get_by_id(failure_id)
        if not failure:
            return {
                "success": False,
                "message": f"Failure with ID {failure_id} not found",
                "failure_id": failure_id,
            }
        
        # Validate strategy type
        try:
            strategy = StrategyType(strategy_type.lower())
        except ValueError:
            return {
                "success": False,
                "message": f"Invalid strategy type: {strategy_type}. Valid types: {[s.value for s in StrategyType]}",
                "failure_id": failure_id,
            }
        
        # Create alternative selector with initial confidence
        alt_selector = AlternativeSelector(
            selector_string=selector_string,
            strategy_type=strategy,
            confidence_score=0.5,  # Custom selectors start with medium confidence
            element_description=f"Custom selector: {selector_string[:50]}...",
            # Custom selector specific fields
            is_custom=True,
            custom_notes=notes,
            created_by=user_id,
        )
        
        # Calculate refined confidence score using custom selector scoring (with boost)
        snapshot_id = self._snapshot_references.get(failure_id)
        scored_selector = self.confidence_scorer.score_custom_selector(
            selector=alt_selector,
            notes=notes,
        )
        
        # Override the strategy with the user-provided one
        scored_selector.strategy_type = strategy
        scored_selector.created_by = user_id
        
        # Store the alternative
        if failure_id not in self._alternatives:
            self._alternatives[failure_id] = []
        self._alternatives[failure_id].append(scored_selector)
        
        # Record audit event for custom selector creation
        self._record_audit_event(
            action_type="custom_selector_created",
            failure_id=failure_id,
            selector=selector_string,
            user_id=user_id,
            notes=notes,
        )
        
        # Record custom selector for learning (Story 4.4 - Task 4)
        self._record_custom_selector_for_learning(
            selector=selector_string,
            strategy=strategy,
            notes=notes,
        )
        
        created_at = datetime.now(timezone.utc)
        
        self._logger.info(
            "custom_selector_created",
            failure_id=failure_id,
            selector=selector_string[:50],
            strategy=strategy_type,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "message": "Custom selector created successfully",
            "failure_id": failure_id,
            "selector": selector_string,
            "strategy_type": strategy_type,
            "created_at": created_at.isoformat(),
        }
    
    def _record_custom_selector_for_learning(
        self,
        selector: str,
        strategy: StrategyType,
        notes: Optional[str] = None,
    ) -> None:
        """
        Record custom selector for future learning.
        
        This feeds into Epic 5 (Learning & Weight Adjustment) by tracking
        which custom strategies are being used.
        
        Args:
            selector: The custom selector string
            strategy: The strategy type used
            notes: Optional notes about the approach
        """
        # TODO(Epic 5): Integrate with the learning system
        # For now, store in memory for future processing
        if not hasattr(self, '_custom_selectors_for_learning'):
            self._custom_selectors_for_learning = []
        
        self._custom_selectors_for_learning.append({
            "selector": selector,
            "strategy": strategy.value,
            "notes": notes,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        
        # Also record in ConfidenceScorer for historical tracking
        self.confidence_scorer.record_custom_selector_feedback(
            selector=selector,
            strategy=strategy,
            approved=True,  # Created but not yet evaluated
            confidence_at_approval=None,
        )
        
        self._logger.info(
            "custom_selector_recorded_for_learning",
            strategy=strategy.value,
            selector_length=len(selector),
        )
    
    def _find_selector_key(self, selectors: Dict[str, Any], selector_value: str) -> Optional[str]:
        """
        Find the key in selectors dict that matches the given selector value.
        
        Args:
            selectors: Dictionary of selector configurations
            selector_value: The selector value to find
            
        Returns:
            The key if found, None otherwise
        """
        if not selectors:
            return None
        
        # Search through selectors to find matching value
        selector_str = str(selector_value) if selector_value else ""
        for key, value in selectors.items():
            if isinstance(value, dict):
                # Check if any value in the dict matches
                for v in value.values():
                    if selector_str in str(v):
                        return key
            elif selector_str in str(value):
                return key
        
        # Return first key if no match found (fallback)
        return list(selectors.keys())[0] if selectors else None
    
    def _load_flagged_failure(self, failure_id: int) -> Optional[Dict[str, Any]]:
        """
        Load flag information from database with caching.
        
        Args:
            failure_id: The failure event ID
            
        Returns:
            Flag info dict or None if not flagged
        """
        # Check cache first
        if failure_id in self._flagged_failures_cache:
            return self._flagged_failures_cache[failure_id]
        
        # Try to load from database (assuming flag columns exist)
        try:
            failure = self.failure_repository.get_by_id(failure_id)
            if failure and hasattr(failure, 'flagged') and failure.flagged:
                flag_info = {
                    "flagged": True,
                    "note": getattr(failure, 'flag_note', None),
                    "flagged_at": getattr(failure, 'flagged_at', None),
                }
                # Cache the result
                self._flagged_failures_cache[failure_id] = flag_info
                return flag_info
        except Exception as e:
            self._logger.warning("failed_to_load_flag_from_db", failure_id=failure_id, error=str(e))
        
        return None
    
    def _save_flagged_failure(self, failure_id: int, flag_info: Dict[str, Any]) -> bool:
        """
        Save flag information to database.
        
        Args:
            failure_id: The failure event ID
            flag_info: Flag information to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Update failure record with flag info
            success = self.failure_repository.update_flag_info(
                failure_id=failure_id,
                flagged=flag_info.get("flagged", False),
                flag_note=flag_info.get("note"),
                flagged_at=flag_info.get("flagged_at"),
            )
            
            if success:
                # Update cache
                self._flagged_failures_cache[failure_id] = flag_info
                self._logger.info("flag_saved_to_db", failure_id=failure_id)
            
            return success
        except Exception as e:
            self._logger.error("failed_to_save_flag_to_db", failure_id=failure_id, error=str(e))
            return False

    def _record_audit_event(
        self,
        action_type: str,
        failure_id: int,
        selector: str,
        user_id: Optional[str] = None,
        before_state: Optional[str] = None,
        after_state: Optional[str] = None,
        confidence_at_time: Optional[float] = None,
        reason: Optional[str] = None,
        suggested_alternative: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        """
        Record an audit event for selector approval or rejection.
        
        This implements Story 4.2 requirement for proper audit logging
        to the database table instead of just logger output.
        
        Args:
            action_type: Type of action (selector_approved, selector_rejected)
            failure_id: The failure event ID
            selector: The selector involved
            user_id: User who performed the action
            before_state: State before change
            after_state: State after change
            confidence_at_time: Confidence score at time of action
            reason: Reason for rejection
            suggested_alternative: Suggested alternative selector
            notes: Optional notes
        """
        try:
            # Create audit event in database (Story 4.2 implementation)
            audit_event = self.audit_repository.create_audit_event(
                action_type=action_type,
                failure_id=failure_id,
                selector=selector,
                user_id=user_id,
                before_state=before_state,
                after_state=after_state,
                confidence_at_time=confidence_at_time,
                reason=reason,
                suggested_alternative=suggested_alternative,
                notes=notes,
            )
            
            self._logger.info(
                "audit_event_recorded",
                audit_event_id=audit_event.id,
                action_type=action_type,
                failure_id=failure_id,
                selector=selector[:50],  # Truncate for logging
                user_id=user_id,
            )
            
        except Exception as e:
            # Fallback to logger if database fails
            self._logger.error(
                "audit_event_database_failed",
                action_type=action_type,
                failure_id=failure_id,
                selector=selector[:50],
                error=str(e),
                fallback="logger_only"
            )
            
            # Build audit event data for logger fallback
            audit_data = {
                "action_type": action_type,
                "failure_id": failure_id,
                "selector": selector,
                "user_id": user_id or "system",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            if before_state:
                audit_data["before_state"] = before_state
            if after_state:
                audit_data["after_state"] = after_state
            if confidence_at_time is not None:
                audit_data["confidence_at_time"] = confidence_at_time
            if reason:
                audit_data["reason"] = reason
            if suggested_alternative:
                audit_data["suggested_alternative"] = suggested_alternative
            if notes:
                audit_data["notes"] = notes
            
            # Log the event as fallback
            self._logger.info("audit_event_fallback", **audit_data)
    
    def _record_positive_feedback(
        self,
        selector: str,
        strategy: StrategyType,
    ):
        """
        Record positive feedback to the confidence scorer for learning.
        
        This implements Epic 5 (Learning & Weight Adjustment) by:
        - Tracking approval count per strategy type
        - Applying boost to approved strategy's base confidence
        - Applying slight boost to related strategies
        - Persisting learned weights for future confidence calculations
        
        Args:
            selector: The approved selector
            strategy: The strategy type used
        """
        # Call the confidence scorer's record_positive_feedback method
        # which implements the full learning logic from Story 5.1
        self.confidence_scorer.record_positive_feedback(
            selector=selector,
            strategy=strategy,
            approved=True,
            confidence_at_approval=None,  # Will use strategy default
        )
        
        self._logger.info(
            "positive_feedback_recorded_for_learning",
            selector=selector[:30],
            strategy=strategy.value,
        )
    
    def _record_negative_feedback(
        self,
        selector: str,
        strategy: StrategyType,
        reason: str,
    ):
        """
        Record negative feedback to the confidence scorer for learning.
        
        This implements Epic 5 Story 5.2 (Learn from Rejections) by:
        1. Calling the confidence scorer's record_negative_feedback method
        2. Passing the rejection reason for pattern analysis
        3. Storing rejection history in the database
        
        Args:
            selector: The rejected selector
            strategy: The strategy type used
            reason: Reason for rejection
        """
        # Get historical confidence if available
        historical_key = f"approval:{selector}"
        rejection_key = f"rejection:{selector}"
        
        raw_confidence = self.confidence_scorer._historical_data.get(historical_key)
        if raw_confidence is None:
            raw_confidence = self.confidence_scorer._historical_data.get(rejection_key)
        
        # Ensure we have a float
        if isinstance(raw_confidence, float):
            confidence_at_rejection = raw_confidence
        else:
            confidence_at_rejection = self.confidence_scorer.STRATEGY_DEFAULTS.get(strategy, 0.5)
        
        # Call the confidence scorer's record_negative_feedback method
        self.confidence_scorer.record_negative_feedback(
            selector=selector,
            strategy=strategy,
            rejection_reason=reason,
            confidence_at_rejection=confidence_at_rejection,
        )
        
        # Also save rejection history to database
        reason_pattern = self._parse_rejection_reason(reason)
        try:
            if self.weight_repository is None:
                from src.selectors.adaptive.db.repositories.weight_repository import get_weight_repository
                self.weight_repository = get_weight_repository()
            
            # Calculate penalized confidence
            penalty = self.confidence_scorer.get_strategy_penalty(strategy)
            penalized_conf = max(
                self.confidence_scorer.MIN_CONFIDENCE_FLOOR,
                confidence_at_rejection - penalty
            )
            
            self.weight_repository.save_rejection_history(
                selector_string=selector,
                strategy_type=strategy.value,
                confidence_at_rejection=confidence_at_rejection,
                penalized_confidence=penalized_conf,
                rejection_reason=reason,
                reason_pattern=reason_pattern,
            )
        except Exception as e:
            self._logger.warning(
                "failed_to_save_rejection_history",
                error=str(e)
            )
        
        self._logger.info(
            "negative_feedback_recorded_for_learning",
            selector=selector[:30],
            strategy=strategy.value,
            reason_pattern=reason_pattern,
        )
    
    def _parse_rejection_reason(self, reason: str) -> Optional[str]:
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
    
    def _generate_highlight_css(self, selector: str) -> str:
        """
        Generate CSS for highlighting elements matching a selector.
        
        Args:
            selector: The selector string
            
        Returns:
            CSS string for highlighting
        """
        # Simple highlight - in production would be more sophisticated
        return f"background-color: rgba(255, 235, 59, 0.5); border: 2px solid #ffc107;"


# Module-level instance for convenience
_failure_service: Optional[FailureService] = None


def get_failure_service() -> FailureService:
    """Get the global failure service instance."""
    global _failure_service
    if _failure_service is None:
        _failure_service = FailureService()
    return _failure_service
