"""
Failure Context Service for capturing and enriching failure event context.

This service extracts and stores comprehensive context information when
a selector failure occurs, including page state, tab type, and confidence scores.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from ..db.models.failure_event import FailureEvent
from ..db.repositories.failure_event_repository import FailureEventRepository


class FailureContextService:
    """
    Service for capturing and enriching failure context.
    
    This service extracts comprehensive context information at the time of
    selector failure to enable better analysis and pattern detection.
    """
    
    # Maximum size for page_state JSON to prevent large payloads
    MAX_PAGE_STATE_SIZE = 10000
    
    def __init__(self, repository: FailureEventRepository):
        """
        Initialize the failure context service.
        
        Args:
            repository: FailureEventRepository instance for database operations
        """
        self.repository = repository
    
    def create_enriched_failure(
        self,
        selector_id: str,
        error_type: str,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        recipe_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        strategy_used: Optional[str] = None,
        resolution_time: Optional[float] = None,
        severity: str = "minor",
        correlation_id: Optional[str] = None,
        # Context fields
        previous_strategy_used: Optional[str] = None,
        confidence_score_at_failure: Optional[float] = None,
        tab_type: Optional[str] = None,
        page_state: Optional[Dict[str, Any]] = None,
    ) -> FailureEvent:
        """
        Create a failure event with comprehensive context.
        
        Args:
            selector_id: Name/ID of the failed selector
            error_type: Classification: empty_result, exception, timeout, validation
            sport: Sport context (from page context)
            site: Site identifier
            recipe_id: Associated recipe (if known)
            failure_reason: Detailed error message
            strategy: Strategy that was attempted
            resolution_time: Time taken before failure (ms)
            severity: Severity level: minor, moderate, critical
            correlation_id: For tracing related events
            previous_strategy_used: Strategy used before this failure
            confidence_score_at_failure: Confidence score at time of failure
            tab_type: Type of tab being extracted (odds, results, schedule)
            page_state: Page state at time of failure
            
        Returns:
            Created FailureEvent instance with context
        """
        # Truncate page_state if too large
        if page_state:
            page_state = self._truncate_page_state(page_state)
        
        return self.repository.create(
            selector_id=selector_id,
            error_type=error_type,
            recipe_id=recipe_id,
            sport=sport,
            site=site,
            failure_reason=failure_reason,
            strategy_used=strategy_used,
            resolution_time=resolution_time,
            severity=severity,
            correlation_id=correlation_id,
            previous_strategy_used=previous_strategy_used,
            confidence_score_at_failure=confidence_score_at_failure,
            tab_type=tab_type,
            page_state=page_state,
        )
    
    def enrich_existing_failure(
        self,
        failure_id: int,
        previous_strategy_used: Optional[str] = None,
        confidence_score_at_failure: Optional[float] = None,
        tab_type: Optional[str] = None,
        page_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[FailureEvent]:
        """
        Enrich an existing failure event with context data.
        
        This method can be called after the initial failure is recorded
        to add additional context information.
        
        Args:
            failure_id: ID of the failure event to enrich
            previous_strategy_used: Strategy used before this failure
            confidence_score_at_failure: Confidence score at time of failure
            tab_type: Type of tab being extracted
            page_state: Page state at time of failure
            
        Returns:
            Updated FailureEvent or None if not found
        """
        # Truncate page_state if too large
        if page_state:
            page_state = self._truncate_page_state(page_state)
        
        # Get existing failure event
        failure = self.repository.get_by_id(failure_id)
        if not failure:
            return None
        
        # Update context fields
        if previous_strategy_used is not None:
            failure.previous_strategy_used = previous_strategy_used
        if confidence_score_at_failure is not None:
            failure.confidence_score_at_failure = confidence_score_at_failure
        if tab_type is not None:
            failure.tab_type = tab_type
        if page_state is not None:
            failure.page_state = page_state
        
        # Save changes
        with self.repository._get_session() as session:
            session.add(failure)
            session.commit()
            session.refresh(failure)
        
        return failure
    
    def capture_page_context(
        self,
        page,
        current_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Capture relevant page context at time of failure.
        
        Args:
            page: Playwright page object
            current_url: Optional URL override
            
        Returns:
            Dictionary containing page context
        """
        context = {}
        
        try:
            # Get viewport size
            viewport = page.viewport_size
            if viewport:
                context["viewport"] = {
                    "width": viewport.get("width"),
                    "height": viewport.get("height"),
                }
            
            # Get URL
            context["url"] = current_url or page.url
            
            # Get scroll position (if available)
            # This is a best-effort capture
            try:
                scroll_position = page.evaluate("""
                    () => ({
                        x: window.scrollX,
                        y: window.scrollY,
                        documentHeight: document.documentElement.scrollHeight,
                        windowHeight: window.innerHeight
                    })
                """)
                context["scroll_position"] = scroll_position
            except Exception:
                pass
            
            # Get loaded resources count
            try:
                resources = page.evaluate("""
                    () => ({
                        images: document.images.length,
                        scripts: document.scripts.length,
                        links: document.getElementsByTagName('a').length
                    })
                """)
                context["page_elements"] = resources
            except Exception:
                pass
            
        except Exception as e:
            # Gracefully handle any errors during context capture
            context["capture_error"] = str(e)
        
        return context
    
    def _truncate_page_state(
        self,
        page_state: Dict[str, Any],
        max_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Truncate page state to prevent large payloads.
        
        Args:
            page_state: Page state dictionary
            max_size: Maximum character size (default: MAX_PAGE_STATE_SIZE)
            
        Returns:
            Truncated page state dictionary
        """
        import json
        
        max_size = max_size or self.MAX_PAGE_STATE_SIZE
        
        # Convert to JSON string to check size
        state_json = json.dumps(page_state)
        
        if len(state_json) <= max_size:
            return page_state
        
        # Truncate by removing less critical keys
        truncated = page_state.copy()
        
        # Priority keys to keep (in order of importance)
        priority_keys = ["url", "viewport", "scroll_position", "page_elements"]
        
        # Remove non-priority keys first
        keys_to_remove = [k for k in truncated.keys() if k not in priority_keys]
        for key in keys_to_remove:
            del truncated[key]
        
        # Check size again
        state_json = json.dumps(truncated)
        if len(state_json) <= max_size:
            return truncated
        
        # If still too large, truncate each remaining value
        for key in priority_keys:
            if key in truncated and isinstance(truncated[key], str):
                truncated[key] = truncated[key][:max_size // 2]
        
        return truncated
    
    def get_context_summary(
        self,
        failure_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a summary of context for a failure event.
        
        Args:
            failure_id: ID of the failure event
            
        Returns:
            Dictionary with context summary or None if not found
        """
        failure = self.repository.get_by_id(failure_id)
        if not failure:
            return None
        
        return {
            "failure_id": failure.id,
            "selector_id": failure.selector_id,
            "sport": failure.sport,
            "site": failure.site,
            "tab_type": failure.tab_type,
            "previous_strategy": failure.previous_strategy_used,
            "confidence_score": failure.confidence_score_at_failure,
            "has_page_state": failure.page_state is not None,
            "page_state_keys": list(failure.page_state.keys()) if failure.page_state else [],
            "timestamp": failure.timestamp.isoformat() if failure.timestamp else None,
        }
