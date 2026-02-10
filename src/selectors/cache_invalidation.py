"""
Cache invalidation logic for DOM state changes.

This module provides intelligent cache invalidation strategies based on
DOM state changes, navigation events, and context transitions.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .context_manager import SelectorContext, DOMState
from .navigation_tracker import NavigationEvent, NavigationEventType
from .lru_cache import get_context_cache


logger = logging.getLogger(__name__)


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    IMMEDIATE = "immediate"  # Invalidate immediately
    DELAYED = "delayed"     # Wait before invalidating
    SELECTIVE = "selective"   # Only invalidate specific entries
    PREDICTIVE = "predictive"   # Predict future invalidations


@dataclass
class InvalidationRule:
    """Rule for cache invalidation."""
    name: str
    strategy: InvalidationStrategy
    conditions: Dict[str, Any]
    delay_seconds: float = 0.0
    priority: int = 1  # Lower number = higher priority
    patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvalidationEvent:
    """Represents a cache invalidation event."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    rule_name: str
    strategy: InvalidationStrategy
    keys_invalidated: List[str] = field(default_factory=list)
    keys_affected: int = 0
    reason: str = ""
    context_path: Optional[str] = None
    dom_state: Optional[DOMState] = None
    execution_time_ms: float = 0.0


class CacheInvalidationManager:
    """
    Manages cache invalidation based on various triggers.
    """
    
    def __init__(self, cache_id: str = "default"):
        """
        Initialize cache invalidation manager.
        
        Args:
            cache_id: ID of the cache to manage
        """
        self.cache_id = cache_id
        self.cache = get_context_cache(cache_id)
        
        # Invalidation rules
        self.rules: List[InvalidationRule] = []
        self.rule_handlers: Dict[str, Callable] = {}
        
        # Invalidation history
        self.invalidation_history: List[InvalidationEvent] = []
        self.max_history_size = 1000
        
        # Performance tracking
        self.stats = {
            "total_invalidations": 0,
            "invalidations_by_strategy": {},
            "invalidations_by_rule": {},
            "average_execution_time_ms": 0.0
        }
        
        # Background invalidation processor
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Initialize default rules
        self._setup_default_rules()
        
        logger.info(f"CacheInvalidationManager initialized for cache: {cache_id}")
    
    def _setup_default_rules(self) -> None:
        """Setup default invalidation rules."""
        # Rule: DOM state changes
        self.add_rule(InvalidationRule(
            name="dom_state_change",
            strategy=InvalidationStrategy.IMMEDIATE,
            conditions={
                "trigger": "dom_state_change",
                "from_states": ["live", "scheduled", "finished"],
                "to_states": ["live", "scheduled", "finished"]
            },
            priority=1
        ))
        
        # Rule: Navigation context changes
        self.add_rule(InvalidationRule(
            name="context_change",
            strategy=InvalidationStrategy.IMMEDIATE,
            conditions={
                "trigger": "context_change",
                "primary_changes": True,
                "secondary_changes": True,
                "tertiary_changes": True
            },
            priority=2
        ))
        
        # Rule: Tab switches
        self.add_rule(InvalidationRule(
            name="tab_switch",
            strategy=InvalidationStrategy.SELECTIVE,
            conditions={
                "trigger": "tab_switch",
                "invalidate_current": True,
                "invalidate_previous": False,
                "pattern": r"context:.*:tab_.*"
            },
            priority=3
        ))
        
        # Rule: Time-based expiration
        self.add_rule(InvalidationRule(
            name="time_based",
            strategy=InvalidationStrategy.DELAYED,
            conditions={
                "trigger": "time_based",
                "max_age_seconds": 300,  # 5 minutes
                "context_patterns": [r"context:extraction.*"]
            },
            delay_seconds=60.0,
            priority=4
        ))
        
        # Rule: Content change detection
        self.add_rule(InvalidationRule(
            name="content_change",
            strategy=InvalidationStrategy.PREDICTIVE,
            conditions={
                "trigger": "content_change",
                "content_patterns": [
                    r"live.*score",
                    r"match.*started",
                    r"match.*finished"
                ]
            },
            priority=5
        ))
    
    def add_rule(self, rule: InvalidationRule) -> None:
        """
        Add an invalidation rule.
        
        Args:
            rule: Rule to add
        """
        self.rules.append(rule)
        
        # Create handler for the rule
        handler = self._create_rule_handler(rule)
        self.rule_handlers[rule.name] = handler
        
        logger.info(f"Added invalidation rule: {rule.name} ({rule.strategy.value})")
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove an invalidation rule.
        
        Args:
            rule_name: Name of rule to remove
            
        Returns:
            bool: True if rule was removed
        """
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                if rule_name in self.rule_handlers:
                    del self.rule_handlers[rule_name]
                
                logger.info(f"Removed invalidation rule: {rule_name}")
                return True
        
        return False
    
    async def invalidate_on_navigation_event(
        self,
        event: NavigationEvent
    ) -> List[InvalidationEvent]:
        """
        Invalidate cache based on navigation event.
        
        Args:
            event: Navigation event that triggered invalidation
            
        Returns:
            List[InvalidationEvent]: List of invalidation events
        """
        invalidation_events = []
        
        for rule in self.rules:
            if await self._rule_matches_event(rule, event):
                try:
                    start_time = datetime.utcnow()
                    
                    # Apply rule-specific invalidation logic
                    keys_invalidated = await self.rule_handlers[rule.name](event, rule)
                    
                    execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    # Create invalidation event
                    invalidation_event = InvalidationEvent(
                        rule_name=rule.name,
                        strategy=rule.strategy,
                        keys_invalidated=keys_invalidated,
                        keys_affected=len(keys_invalidated),
                        reason=f"Navigation event: {event.event_type.value}",
                        context_path=getattr(event, 'target_context', None),
                        execution_time_ms=execution_time
                    )
                    
                    invalidation_events.append(invalidation_event)
                    
                    # Update statistics
                    self._update_stats(rule.name, rule.strategy, execution_time)
                    
                    logger.debug(
                        f"Invalidated {len(keys_invalidated)} entries for rule {rule.name} "
                        f"in {execution_time:.2f}ms"
                    )
                    
                except Exception as e:
                    logger.error(f"Error applying rule {rule.name}: {e}")
        
        return invalidation_events
    
    async def invalidate_on_dom_state_change(
        self,
        old_state: Optional[DOMState],
        new_state: DOMState,
        context_path: Optional[str] = None
    ) -> List[InvalidationEvent]:
        """
        Invalidate cache based on DOM state change.
        
        Args:
            old_state: Previous DOM state
            new_state: New DOM state
            context_path: Current context path
            
        Returns:
            List[InvalidationEvent]: List of invalidation events
        """
        invalidation_events = []
        
        # Create mock navigation event for DOM state change
        mock_event = NavigationEvent(
            event_type=NavigationEventType.DOM_UPDATE,
            source_context=old_state.value if old_state else None,
            target_context=new_state.value,
            metadata={
                "context_path": context_path,
                "old_state": old_state.value if old_state else None,
                "new_state": new_state.value
            }
        )
        
        return await self.invalidate_on_navigation_event(mock_event)
    
    async def invalidate_on_context_change(
        self,
        old_context: Optional[SelectorContext],
        new_context: SelectorContext
    ) -> List[InvalidationEvent]:
        """
        Invalidate cache based on context change.
        
        Args:
            old_context: Previous context
            new_context: New context
            
        Returns:
            List[InvalidationEvent]: List of invalidation events
        """
        invalidation_events = []
        
        # Create mock navigation event for context change
        mock_event = NavigationEvent(
            event_type=NavigationEventType.CONTEXT_CHANGE,
            source_context=old_context.get_context_path() if old_context else None,
            target_context=new_context.get_context_path(),
            metadata={
                "old_primary": old_context.primary_context if old_context else None,
                "old_secondary": old_context.secondary_context,
                "old_tertiary": old_context.tertiary_context,
                "new_primary": new_context.primary_context,
                "new_secondary": new_context.secondary_context,
                "new_tertiary": new_context.tertiary_context
            }
        )
        
        return await self.invalidate_on_navigation_event(mock_event)
    
    async def invalidate_by_pattern(
        self,
        pattern: str,
        reason: str = "Pattern-based invalidation"
    ) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Regex pattern to match keys
            reason: Reason for invalidation
            
        Returns:
            int: Number of entries invalidated
        """
        start_time = datetime.utcnow()
        
        try:
            # Get all cache keys
            cache_info = self.cache.get_cache_info()
            all_entries = cache_info.get("top_entries", [])
            all_keys = [entry["key"] for entry in all_entries]
            
            # Find matching keys
            import re
            regex_pattern = re.compile(pattern, re.IGNORECASE)
            matching_keys = [
                key for key in all_keys
                if regex_pattern.search(key)
            ]
            
            # Invalidate matching keys
            keys_invalidated = 0
            for key in matching_keys:
                if await self.cache.remove(key):
                    keys_invalidated += 1
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create invalidation event
            invalidation_event = InvalidationEvent(
                rule_name="pattern_based",
                strategy=InvalidationStrategy.IMMEDIATE,
                keys_invalidated=matching_keys,
                keys_affected=keys_invalidated,
                reason=reason,
                execution_time_ms=execution_time
            )
            
            self.invalidation_history.append(invalidation_event)
            self._update_stats("pattern_based", InvalidationStrategy.IMMEDIATE, execution_time)
            
            logger.info(
                f"Pattern-based invalidation: {keys_invalidated} entries matching '{pattern}' "
                f"in {execution_time:.2f}ms"
            )
            
            return keys_invalidated
            
        except Exception as e:
            logger.error(f"Pattern-based invalidation failed: {e}")
            return 0
    
    async def invalidate_context(
        self,
        context_path: str,
        dom_state: Optional[DOMState] = None
    ) -> int:
        """
        Invalidate all entries for a specific context.
        
        Args:
            context_path: Context path to invalidate
            dom_state: DOM state to invalidate
            
        Returns:
            int: Number of entries invalidated
        """
        pattern = f"context:{context_path}"
        if dom_state:
            pattern += f":{dom_state.value}"
        
        return await self.invalidate_by_pattern(pattern, f"Context invalidation: {context_path}")
    
    async def start_background_processor(self) -> None:
        """Start the background invalidation processor."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._processing_loop())
        logger.info("Background invalidation processor started")
    
    async def stop_background_processor(self) -> None:
        """Stop the background invalidation processor."""
        if not self._running:
            return
        
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Background invalidation processor stopped")
    
    async def _processing_loop(self) -> None:
        """Background processing loop for delayed invalidations."""
        while self._running:
            try:
                # Process any queued invalidations
                while not self._processing_queue.empty():
                    invalidation_data = await self._processing_queue.get()
                    await self._process_delayed_invalidation(invalidation_data)
                
                # Check for time-based invalidations
                await self._check_time_based_invalidations()
                
                # Sleep before next iteration
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                logger.debug("Processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                await asyncio.sleep(5.0)
    
    async def _process_delayed_invalidation(self, invalidation_data: Dict[str, Any]) -> None:
        """Process a delayed invalidation."""
        try:
            rule_name = invalidation_data.get("rule_name")
            delay_seconds = invalidation_data.get("delay_seconds", 0.0)
            
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            
            # Execute the invalidation
            keys_invalidated = invalidation_data.get("keys_to_invalidate", [])
            for key in keys_invalidated:
                await self.cache.remove(key)
            
            execution_time = invalidation_data.get("execution_time_ms", 0.0)
            
            # Create invalidation event
            invalidation_event = InvalidationEvent(
                rule_name=rule_name,
                strategy=InvalidationStrategy.DELAYED,
                keys_invalidated=keys_invalidated,
                keys_affected=len(keys_invalidated),
                reason=f"Delayed invalidation: {rule_name}",
                execution_time_ms=execution_time
            )
            
            self.invalidation_history.append(invalidation_event)
            self._update_stats(rule_name, InvalidationStrategy.DELAYED, execution_time)
            
            logger.info(
                f"Delayed invalidation completed: {len(keys_invalidated)} entries for rule {rule_name}"
            )
            
        except Exception as e:
            logger.error(f"Error processing delayed invalidation: {e}")
    
    async def _check_time_based_invalidations(self) -> None:
        """Check for time-based invalidations."""
        current_time = datetime.utcnow()
        
        for rule in self.rules:
            if (rule.strategy == InvalidationStrategy.DELAYED and 
                "max_age_seconds" in rule.conditions):
                
                max_age = rule.conditions["max_age_seconds"]
                context_patterns = rule.conditions.get("context_patterns", [])
                
                # Check each context pattern
                for pattern in context_patterns:
                    cache_key = f"context:{pattern}"
                    entry = await self.cache.get(cache_key)
                    
                    if entry and not entry.is_expired:
                        age = current_time - entry.created_at
                        
                        if age.total_seconds() > max_age:
                            # Queue for delayed invalidation
                            await self._processing_queue.put({
                                "rule_name": rule.name,
                                "delay_seconds": rule.delay_seconds,
                                "keys_to_invalidate": [cache_key],
                                "execution_time_ms": 0.0  # Will be set when processed
                            })
                            
                            logger.debug(
                                f"Queued time-based invalidation for {pattern} "
                                f"(age: {age.total_seconds():.1f}s)"
                            )
    
    def _rule_matches_event(self, rule: InvalidationRule, event: NavigationEvent) -> bool:
        """Check if a rule matches a navigation event."""
        conditions = rule.conditions
        trigger = conditions.get("trigger")
        
        if trigger == "dom_state_change":
            return (event.source_context and event.target_context and
                    event.source_context != event.target_context)
        
        elif trigger == "context_change":
            # Check for context changes
            if conditions.get("primary_changes"):
                old_primary = event.metadata.get("old_primary")
                new_primary = event.metadata.get("new_primary")
                if old_primary != new_primary:
                    return True
            
            if conditions.get("secondary_changes"):
                old_secondary = event.metadata.get("old_secondary")
                new_secondary = event.metadata.get("new_secondary")
                if old_secondary != new_secondary:
                    return True
            
            if conditions.get("tertiary_changes"):
                old_tertiary = event.metadata.get("old_tertiary")
                new_tertiary = event.metadata.get("new_tertiary")
                if old_tertiary != new_tertiary:
                    return True
        
        elif trigger == "tab_switch":
            return event.event_type == NavigationEventType.TAB_SWITCH
        
        elif trigger == "content_change":
            content = event.metadata.get("content", "")
            for pattern in conditions.get("content_patterns", []):
                if re.search(pattern, content, re.IGNORECASE):
                    return True
        
        return False
    
    def _create_rule_handler(self, rule: InvalidationRule) -> Callable:
        """Create a handler function for a rule."""
        strategy = rule.strategy
        
        if strategy == InvalidationStrategy.IMMEDIATE:
            return self._create_immediate_handler(rule)
        elif strategy == InvalidationStrategy.DELAYED:
            return self._create_delayed_handler(rule)
        elif strategy == InvalidationStrategy.SELECTIVE:
            return self._create_selective_handler(rule)
        elif strategy == InvalidationStrategy.PREDICTIVE:
            return self._create_predictive_handler(rule)
        else:
            return self._create_default_handler(rule)
    
    async def _create_immediate_handler(self, rule: InvalidationRule) -> Callable:
        """Create immediate invalidation handler."""
        async def handler(event: NavigationEvent, rule: InvalidationRule) -> List[str]:
            keys_invalidated = []
            
            # Determine keys to invalidate based on event
            if rule.name == "dom_state_change":
                # Invalidate all context entries for old DOM state
                old_state = event.source_context
                if old_state:
                    await self.invalidate_context(context_path=event.target_context, dom_state=old_state)
            
            elif rule.name == "context_change":
                # Invalidate old context entries
                old_context = event.source_context
                if old_context:
                    await self.invalidate_context(context_path=old_context)
            
            elif rule.name == "tab_switch":
                # Invalidate previous tab context
                if rule.conditions.get("invalidate_previous"):
                    # This would need access to previous tab context
                    # For now, invalidate all tab contexts
                    await self.invalidate_by_pattern(rule.conditions["pattern"])
            
            return keys_invalidated
        
        return handler
    
    async def _create_delayed_handler(self, rule: InvalidationRule) -> Callable:
        """Create delayed invalidation handler."""
        async def handler(event: NavigationEvent, rule: InvalidationRule) -> List[str]:
            # Queue for delayed processing
            keys_to_invalidate = []
            
            # Determine keys to invalidate based on event
            if rule.name == "dom_state_change":
                old_state = event.source_context
                if old_state:
                    await self.invalidate_context(context_path=event.target_context, dom_state=old_state)
                    keys_to_invalidate.append(f"context:{event.target_context}:{old_state}")
            
            elif rule.name == "context_change":
                old_context = event.source_context
                if old_context:
                    await self.invalidate_context(context_path=old_context)
                    keys_to_invalidate.append(f"context:{old_context}")
            
            # Queue for delayed processing
            await self._processing_queue.put({
                "rule_name": rule.name,
                "delay_seconds": rule.delay_seconds,
                "keys_to_invalidate": keys_to_invalidate,
                "execution_time_ms": 0.0
            })
            
            return keys_to_invalidate
        
        return handler
    
    async def _create_selective_handler(self, rule: InvalidationRule) -> Callable:
        """Create selective invalidation handler."""
        async def handler(event: NavigationEvent, rule: InvalidationRule) -> List[str]:
            keys_invalidated = []
            
            # Tab switch selective invalidation
            if rule.name == "tab_switch" and event.event_type == NavigationEventType.TAB_SWITCH:
                if rule.conditions.get("invalidate_current"):
                    # Invalidate current tab context
                    current_tab = event.target_context
                    if current_tab:
                        await self.invalidate_context(context_path=current_tab)
                        keys_invalidated.append(f"context:{current_tab}")
            
            return keys_invalidated
        
        return handler
    
    async def _create_predictive_handler(self, rule: InvalidationRule) -> Callable:
        """Create predictive invalidation handler."""
        async def handler(event: NavigationEvent, rule: InvalidationRule) -> List[str]:
            keys_invalidated = []
            
            # Content change predictive invalidation
            if rule.name == "content_change":
                content = event.metadata.get("content", "")
                for pattern in rule.conditions.get("content_patterns", []):
                    if re.search(pattern, content, re.IGNORECASE):
                        # Predict related contexts that might be affected
                        related_patterns = self._get_related_context_patterns(pattern)
                        
                        for related_pattern in related_patterns:
                            await self.invalidate_by_pattern(
                                f"context:{related_pattern}",
                                f"Predictive invalidation for content pattern: {pattern}"
                            )
            
            return keys_invalidated
        
        return handler
    
    def _create_default_handler(self, rule: InvalidationRule) -> Callable:
        """Create default invalidation handler."""
        async def handler(event: NavigationEvent, rule: InvalidationRule) -> List[str]:
            # Default: invalidate based on context change
            return await self._create_immediate_handler(rule)(event, rule)
        
        return handler
    
    def _get_related_context_patterns(self, content_pattern: str) -> List[str]:
        """Get context patterns related to a content pattern."""
        # Simple mapping of content patterns to related contexts
        pattern_mappings = {
            r"live.*score": ["context:extraction/match_list", "context:extraction/match_summary"],
            r"match.*started": ["context:extraction/match_list"],
            r"match.*finished": ["context:extraction/match_summary", "context:extraction/match_h2h"]
        }
        
        return pattern_mappings.get(content_pattern, [])
    
    def _update_stats(self, rule_name: str, strategy: InvalidationStrategy, execution_time: float) -> None:
        """Update invalidation statistics."""
        self.stats["total_invalidations"] += 1
        
        # Update strategy stats
        if strategy.value not in self.stats["invalidations_by_strategy"]:
            self.stats["invalidations_by_strategy"][strategy.value] = 0
        self.stats["invalidations_by_strategy"][strategy.value] += 1
        
        # Update rule stats
        if rule_name not in self.stats["invalidations_by_rule"]:
            self.stats["invalidations_by_rule"][rule_name] = 0
        self.stats["invalidations_by_rule"][rule_name] += 1
        
        # Update average execution time
        total_invalidations = self.stats["total_invalidations"]
        current_avg = self.stats["average_execution_time_ms"]
        new_avg = ((current_avg * (total_invalidations - 1)) + execution_time) / total_invalidations
        self.stats["average_execution_time_ms"] = new_avg
    
    def get_invalidation_stats(self) -> Dict[str, Any]:
        """Get invalidation statistics."""
        return {
            **self.stats,
            "rules_count": len(self.rules),
            "history_size": len(self.invalidation_history),
            "processor_running": self._running
        }
    
    def get_invalidation_history(self, limit: int = 50) -> List[InvalidationEvent]:
        """Get recent invalidation history."""
        return sorted(
            self.invalidation_history[-limit:],
            key=lambda event: event.timestamp,
            reverse=True
        )


# Global invalidation manager instances
_invalidation_managers: Dict[str, CacheInvalidationManager] = {}


def get_invalidation_manager(cache_id: str = "default") -> CacheInvalidationManager:
    """
    Get or create a cache invalidation manager.
    
    Args:
        cache_id: ID of the cache to manage
        
    Returns:
        CacheInvalidationManager: Manager instance
    """
    global _invalidation_managers
    
    if cache_id not in _invalidation_managers:
        _invalidation_managers[cache_id] = CacheInvalidationManager(cache_id)
        logger.info(f"Created invalidation manager for cache: {cache_id}")
    
    return _invalidation_managers[cache_id]
