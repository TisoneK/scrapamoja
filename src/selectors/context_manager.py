"""
Selector Context Manager for hierarchical selector organization.

This module provides context-aware selector loading and management
for complex multi-layer navigation patterns like flashscore workflow.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

from src.observability.logger import get_logger
from ..models.selector_models import (
    SemanticSelector, 
    TabContext, 
    TabType, 
    TabState, 
    TabVisibility
)


logger = get_logger(__name__)


class NavigationLevel(Enum):
    """Navigation levels in hierarchical structure."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class DOMState(Enum):
    """DOM states for different match types."""
    LIVE = "live"
    SCHEDULED = "scheduled"
    FINISHED = "finished"
    UNKNOWN = "unknown"


@dataclass
class SelectorContext:
    """Context information for selector loading."""
    primary_context: str  # authentication, navigation, extraction, filtering
    secondary_context: Optional[str] = None  # match_list, match_summary, etc.
    tertiary_context: Optional[str] = None  # inc_ot, ft, q1, q2, etc.
    dom_state: Optional[DOMState] = None
    tab_context: Optional[TabContext] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_context_path(self) -> str:
        """Get the full context path as a string."""
        parts = [self.primary_context]
        if self.secondary_context:
            parts.append(self.secondary_context)
        if self.tertiary_context:
            parts.append(self.tertiary_context)
        return "/".join(parts)
    
    def get_selector_file_path(self, selectors_root: Path, filename: str) -> Path:
        """Get the full file path for a selector in this context."""
        parts = [self.primary_context]
        if self.secondary_context:
            parts.append(self.secondary_context)
        if self.tertiary_context:
            parts.append(self.tertiary_context)
        
        return selectors_root / "/".join(parts) / filename


@dataclass
class ContextTransition:
    """Represents a transition between contexts."""
    from_context: Optional[SelectorContext]
    to_context: SelectorContext
    transition_time: datetime = field(default_factory=datetime.utcnow)
    transition_type: str = "navigation"  # navigation, tab_switch, dom_change
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelectorContextManager:
    """
    Manages selector contexts for hierarchical selector organization.
    
    This class tracks navigation states, manages context transitions,
    and provides context-aware selector loading capabilities.
    """
    
    # Valid primary contexts
    PRIMARY_CONTEXTS = {
        'authentication', 'navigation', 'extraction', 'filtering'
    }
    
    # Valid secondary contexts within extraction
    EXTRACTION_SECONDARY_CONTEXTS = {
        'match_list', 'match_summary', 'match_h2h', 'match_odds', 'match_stats'
    }
    
    # Valid tertiary contexts within match_stats
    MATCH_STATS_TERTIARY_CONTEXTS = {
        'inc_ot', 'ft', 'q1', 'q2', 'q3', 'q4'
    }
    
    def __init__(self, selectors_root: Path):
        """
        Initialize context manager.
        
        Args:
            selectors_root: Root directory of hierarchical selectors
        """
        self.selectors_root = Path(selectors_root)
        
        # Context state
        self.current_context: Optional[SelectorContext] = None
        self.context_history: List[ContextTransition] = []
        self.active_contexts: Dict[str, SelectorContext] = {}
        
        # Context validation
        self._validate_selectors_structure()
        
        # Performance tracking
        self.context_load_times: Dict[str, float] = {}
        self.context_switch_count: int = 0
        
        # Cache for loaded selectors
        self.selector_cache: Dict[str, List[SemanticSelector]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Configuration
        self.cache_ttl_seconds = 300  # 5 minutes
        self.max_history_size = 100
        
        logger.info(f"SelectorContextManager initialized for {selectors_root}")
    
    def _validate_selectors_structure(self) -> None:
        """Validate that the selectors directory has required structure."""
        if not self.selectors_root.exists():
            raise ValueError(f"Selectors directory does not exist: {self.selectors_root}")
        
        # Check primary folders
        missing_primary = self.PRIMARY_CONTEXTS - {
            f.name for f in self.selectors_root.iterdir() if f.is_dir()
        }
        if missing_primary:
            logger.warning(f"Missing primary context folders: {missing_primary}")
    
    async def set_context(
        self,
        primary_context: str,
        secondary_context: Optional[str] = None,
        tertiary_context: Optional[str] = None,
        dom_state: Optional[DOMState] = None,
        tab_context: Optional[TabContext] = None
    ) -> bool:
        """
        Set the current selector context.
        
        Args:
            primary_context: Primary navigation context
            secondary_context: Secondary navigation context (optional)
            tertiary_context: Tertiary navigation context (optional)
            dom_state: Current DOM state (optional)
            tab_context: Tab context information (optional)
            
        Returns:
            bool: True if context was set successfully
        """
        try:
            # Validate context
            if not self._validate_context(primary_context, secondary_context, tertiary_context):
                return False
            
            # Create new context
            new_context = SelectorContext(
                primary_context=primary_context,
                secondary_context=secondary_context,
                tertiary_context=tertiary_context,
                dom_state=dom_state,
                tab_context=tab_context,
                is_active=True
            )
            
            # Record transition
            transition = ContextTransition(
                from_context=self.current_context,
                to_context=new_context,
                transition_type="navigation"
            )
            
            # Update current context
            old_context = self.current_context
            self.current_context = new_context
            self.active_contexts[new_context.get_context_path()] = new_context
            
            # Add to history
            self.context_history.append(transition)
            if len(self.context_history) > self.max_history_size:
                self.context_history = self.context_history[-self.max_history_size:]
            
            # Invalidate cache if context changed significantly
            if old_context and self._should_invalidate_cache(old_context, new_context):
                self._invalidate_relevant_cache(old_context, new_context)
            
            self.context_switch_count += 1
            
            logger.info(
                f"Context set to: {new_context.get_context_path()}",
                primary=primary_context,
                secondary=secondary_context,
                tertiary=tertiary_context,
                dom_state=dom_state.value if dom_state else None
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set context: {e}")
            return False
    
    def _validate_context(
        self,
        primary_context: str,
        secondary_context: Optional[str],
        tertiary_context: Optional[str]
    ) -> bool:
        """Validate context parameters."""
        # Validate primary context
        if primary_context not in self.PRIMARY_CONTEXTS:
            logger.error(f"Invalid primary context: {primary_context}")
            return False
        
        # Validate secondary context
        if secondary_context:
            if primary_context == 'extraction':
                if secondary_context not in self.EXTRACTION_SECONDARY_CONTEXTS:
                    logger.error(f"Invalid extraction secondary context: {secondary_context}")
                    return False
            else:
                logger.warning(f"Secondary context not typically used with {primary_context}")
        
        # Validate tertiary context
        if tertiary_context:
            if secondary_context == 'match_stats':
                if tertiary_context not in self.MATCH_STATS_TERTIARY_CONTEXTS:
                    logger.error(f"Invalid match_stats tertiary context: {tertiary_context}")
                    return False
            else:
                logger.warning(f"Tertiary context only valid with match_stats secondary context")
        
        return True
    
    def _should_invalidate_cache(
        self, 
        old_context: SelectorContext, 
        new_context: SelectorContext
    ) -> bool:
        """Determine if cache should be invalidated."""
        # Invalidate if primary context changed
        if old_context.primary_context != new_context.primary_context:
            return True
        
        # Invalidate if secondary context changed
        if old_context.secondary_context != new_context.secondary_context:
            return True
        
        # Invalidate if DOM state changed significantly
        if (old_context.dom_state != new_context.dom_state and 
            old_context.dom_state and new_context.dom_state):
            return True
        
        return False
    
    def _invalidate_relevant_cache(
        self, 
        old_context: SelectorContext, 
        new_context: SelectorContext
    ) -> None:
        """Invalidate relevant cache entries."""
        # Clear cache for contexts that are no longer relevant
        keys_to_remove = []
        
        for cache_key in self.selector_cache.keys():
            # Invalidate if cache key contains old context path
            if old_context.get_context_path() in cache_key:
                keys_to_remove.append(cache_key)
        
        for key in keys_to_remove:
            del self.selector_cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]
        
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries")
    
    async def get_context_selectors(
        self,
        context: Optional[SelectorContext] = None,
        force_reload: bool = False
    ) -> List[SemanticSelector]:
        """
        Get selectors for the current or specified context.
        
        Args:
            context: Context to get selectors for (uses current if None)
            force_reload: Force reload from disk instead of cache
            
        Returns:
            List[SemanticSelector]: Selectors for the context
        """
        target_context = context or self.current_context
        if not target_context:
            logger.warning("No context specified and no current context set")
            return []
        
        context_path = target_context.get_context_path()
        cache_key = f"{context_path}_{target_context.dom_state or 'unknown'}"
        
        # Check cache first
        if not force_reload and self._is_cache_valid(cache_key):
            start_time = datetime.utcnow()
            selectors = self.selector_cache.get(cache_key, [])
            load_time = (datetime.utcnow() - start_time).total_seconds()
            self.context_load_times[context_path] = load_time
            
            logger.debug(f"Loaded {len(selectors)} selectors from cache for {context_path}")
            return selectors
        
        # Load from disk
        try:
            start_time = datetime.utcnow()
            selectors = await self._load_selectors_from_disk(target_context)
            load_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Cache the results
            self.selector_cache[cache_key] = selectors
            self.cache_timestamps[cache_key] = datetime.utcnow()
            self.context_load_times[context_path] = load_time
            
            logger.info(f"Loaded {len(selectors)} selectors from disk for {context_path} in {load_time:.3f}s")
            return selectors
            
        except Exception as e:
            logger.error(f"Failed to load selectors for context {context_path}: {e}")
            return []
    
    async def _load_selectors_from_disk(self, context: SelectorContext) -> List[SemanticSelector]:
        """Load selectors from disk for the given context."""
        selectors = []
        
        # Get the directory for this context
        context_dir = self.selectors_root / context.primary_context
        if context.secondary_context:
            context_dir = context_dir / context.secondary_context
        if context.tertiary_context:
            context_dir = context_dir / context.tertiary_context
        
        if not context_dir.exists():
            logger.warning(f"Context directory does not exist: {context_dir}")
            return []
        
        # Load all YAML files in the context directory
        yaml_files = list(context_dir.glob("*.yaml")) + list(context_dir.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                selector = await self._load_selector_file(yaml_file, context)
                if selector:
                    selectors.append(selector)
            except Exception as e:
                logger.error(f"Failed to load selector from {yaml_file}: {e}")
        
        return selectors
    
    async def _load_selector_file(
        self, 
        file_path: Path, 
        context: SelectorContext
    ) -> Optional[SemanticSelector]:
        """Load a single selector file."""
        import yaml
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            # Create SemanticSelector from YAML data
            selector = SemanticSelector(
                name=data.get('name', file_path.stem),
                description=data.get('description', ''),
                context=context.get_context_path(),
                strategies=data.get('strategies', []),
                validation_rules=data.get('validation_rules', []),
                confidence_threshold=data.get('confidence_threshold', 0.8),
                metadata={
                    'file_path': str(file_path),
                    'context': context.get_context_path(),
                    'dom_state': context.dom_state.value if context.dom_state else None,
                    **data.get('metadata', {})
                }
            )
            
            return selector
            
        except Exception as e:
            logger.error(f"Error loading selector file {file_path}: {e}")
            return None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.cache_timestamps:
            return False
        
        age = datetime.utcnow() - self.cache_timestamps[cache_key]
        return age.total_seconds() < self.cache_ttl_seconds
    
    async def detect_dom_state(self, page_content: str) -> DOMState:
        """
        Detect DOM state based on page content.
        
        Args:
            page_content: HTML content of the page
            
        Returns:
            DOMState: Detected DOM state
        """
        content_lower = page_content.lower()
        
        # Look for indicators of live matches
        live_indicators = ['live', 'in progress', 'playing', 'minute']
        scheduled_indicators = ['scheduled', 'upcoming', 'kick-off', 'starts']
        finished_indicators = ['finished', 'final', 'full time', 'ft', 'ended']
        
        live_score = sum(1 for indicator in live_indicators if indicator in content_lower)
        scheduled_score = sum(1 for indicator in scheduled_indicators if indicator in content_lower)
        finished_score = sum(1 for indicator in finished_indicators if indicator in content_lower)
        
        # Determine state based on scores
        if live_score > scheduled_score and live_score > finished_score:
            return DOMState.LIVE
        elif scheduled_score > live_score and scheduled_score > finished_score:
            return DOMState.SCHEDULED
        elif finished_score > live_score and finished_score > scheduled_score:
            return DOMState.FINISHED
        else:
            return DOMState.UNKNOWN
    
    async def update_tab_context(self, tab_context: TabContext) -> None:
        """
        Update tab context information.
        
        Args:
            tab_context: Current tab context
        """
        if self.current_context:
            self.current_context.tab_context = tab_context
            self.current_context.updated_at = datetime.utcnow()
            
            logger.debug(f"Updated tab context: {tab_context.tab_id}")
    
    def get_context_history(self, limit: int = 10) -> List[ContextTransition]:
        """
        Get recent context transitions.
        
        Args:
            limit: Maximum number of transitions to return
            
        Returns:
            List[ContextTransition]: Recent transitions
        """
        return self.context_history[-limit:] if self.context_history else []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the context manager.
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        return {
            "context_switches": self.context_switch_count,
            "active_contexts": len(self.active_contexts),
            "cached_contexts": len(self.selector_cache),
            "average_load_time": (
                sum(self.context_load_times.values()) / len(self.context_load_times)
                if self.context_load_times else 0.0
            ),
            "cache_hit_ratio": self._calculate_cache_hit_ratio(),
            "current_context": (
                self.current_context.get_context_path() 
                if self.current_context else None
            )
        }
    
    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio (placeholder for now)."""
        # This would need actual hit/miss tracking to be accurate
        return 0.8  # Placeholder
    
    async def clear_cache(self, context_path: Optional[str] = None) -> None:
        """
        Clear selector cache.
        
        Args:
            context_path: Specific context path to clear (clears all if None)
        """
        if context_path:
            # Clear specific context
            keys_to_remove = [
                key for key in self.selector_cache.keys() 
                if context_path in key
            ]
            for key in keys_to_remove:
                del self.selector_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
            
            logger.info(f"Cleared cache for context: {context_path}")
        else:
            # Clear all cache
            self.selector_cache.clear()
            self.cache_timestamps.clear()
            logger.info("Cleared all selector cache")
    
    def get_available_contexts(self) -> Dict[str, List[str]]:
        """
        Get available contexts based on directory structure.
        
        Returns:
            Dict[str, List[str]]: Available contexts by level
        """
        contexts = {
            "primary": [],
            "secondary": {},
            "tertiary": {}
        }
        
        # Find primary contexts
        for item in self.selectors_root.iterdir():
            if item.is_dir() and item.name in self.PRIMARY_CONTEXTS:
                contexts["primary"].append(item.name)
                
                # Find secondary contexts
                if item.name == 'extraction':
                    secondary_dir = item
                    contexts["secondary"][item.name] = []
                    
                    for sec_item in secondary_dir.iterdir():
                        if sec_item.is_dir() and sec_item.name in self.EXTRACTION_SECONDARY_CONTEXTS:
                            contexts["secondary"][item.name].append(sec_item.name)
                            
                            # Find tertiary contexts
                            if sec_item.name == 'match_stats':
                                tertiary_dir = sec_item
                                contexts["tertiary"][sec_item.name] = []
                                
                                for tert_item in tertiary_dir.iterdir():
                                    if (tert_item.is_dir() and 
                                        tert_item.name in self.MATCH_STATS_TERTIARY_CONTEXTS):
                                        contexts["tertiary"][sec_item.name].append(tert_item.name)
        
        return contexts


# Global context manager instance
_context_manager: Optional[SelectorContextManager] = None


def get_context_manager(selectors_root: Optional[Path] = None) -> SelectorContextManager:
    """
    Get or create the global context manager.
    
    Args:
        selectors_root: Root directory for selectors (required for first call)
        
    Returns:
        SelectorContextManager: Global context manager instance
    """
    global _context_manager
    
    if _context_manager is None:
        if selectors_root is None:
            raise ValueError("selectors_root required for first initialization")
        _context_manager = SelectorContextManager(selectors_root)
    
    return _context_manager
