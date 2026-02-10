"""
Tab-scoped selector activation system.

This module provides tab-specific selector activation with context isolation,
ensuring only the appropriate selectors are active for each tab context.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import weakref

from .context_manager import SelectorContext, get_context_manager
from .navigation_tracker import NavigationStateTracker, NavigationEvent, NavigationEventType
from .lru_cache import get_context_cache


logger = logging.getLogger(__name__)


class TabType(Enum):
    """Types of tabs for selector scoping."""
    CONTENT = "content"
    NAVIGATION = "navigation"
    SETTINGS = "settings"
    MODAL = "modal"
    FILTER = "filter"


@dataclass
class TabContext:
    """Context information for a specific tab."""
    tab_id: str
    tab_type: TabType
    is_active: bool = False
    is_visible: bool = False
    is_loaded: bool = False
    context_path: Optional[str] = None
    dom_state: Optional[str] = None
    selectors: List[Any] = field(default_factory=list)
    activated_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivationEvent:
    """Event representing a tab activation or deactivation."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tab_id: str
    event_type: str  # "activate", "deactivate", "selector_load", "context_change"
    details: Dict[str, Any] = field(default_factory=dict)
    performance_ms: float = 0.0


class TabScopedSelectorManager:
    """
    Manages tab-scoped selector activation with context isolation.
    """
    
    def __init__(self, cache_id: str = "default"):
        """
        Initialize tab-scoped selector manager.
        
        Args:
            cache_id: ID of the cache to use
        """
        self.cache_id = cache_id
        self.cache = get_context_cache(cache_id)
        self.navigation_tracker = NavigationStateTracker()
        
        # Tab management
        self.tabs: Dict[str, TabContext] = {}
        self.active_tab: Optional[str] = None
        self.tab_history: List[ActivationEvent] = []
        self.max_history_size = 1000
        
        # Activation rules and policies
        self.activation_rules: Dict[str, Dict[str, Any]] = {}
        self.isolation_policies: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.stats = {
            "total_activations": 0,
            "total_deactivations": 0,
            "selector_loads": 0,
            "context_switches": 0,
            "average_activation_time_ms": 0.0,
            "active_tabs": 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Event listeners
        self.event_listeners: List[Callable[[ActivationEvent], None]] = []
        
        # Initialize default rules and policies
        self._setup_default_rules()
        self._setup_default_policies()
        
        logger.info(f"TabScopedSelectorManager initialized with cache: {cache_id}")
    
    def _setup_default_rules(self) -> None:
        """Setup default tab activation rules."""
        # Rule: Match tabs get match_list selectors
        self.add_activation_rule("match_tab", {
            "tab_patterns": [r"match", r"fixture", r"live"],
            "required_context": "extraction/match_list",
            "selector_patterns": [r"match.*list", r"fixture.*list", r"live.*match"]
        })
        
        # Rule: Summary tabs get match_summary selectors
        self.add_activation_rule("summary_tab", {
            "tab_patterns": [r"summary", r"overview", r"details"],
            "required_context": "extraction/match_summary",
            "selector_patterns": [r"summary.*selector", r"overview.*selector", r"details.*selector"]
        })
        
        # Rule: H2H tabs get match_h2h selectors
        self.add_activation_rule("h2h_tab", {
            "tab_patterns": [r"h2h", r"head.to.head", r"history"],
            "required_context": "extraction/match_h2h",
            "selector_patterns": [r"h2h.*selector", r"history.*selector", r"versus.*selector"]
        })
        
        # Rule: Odds tabs get match_odds selectors
        self.add_activation_rule("odds_tab", {
            "tab_patterns": [r"odds", r"betting", r"price"],
            "required_context": "extraction/match_odds",
            "selector_patterns": [r"odds.*selector", r"betting.*selector", r"price.*selector"]
        })
        
        # Rule: Stats tabs get match_stats selectors
        self.add_activation_rule("stats_tab", {
            "tab_patterns": [r"stats", r"statistics", r"performance"],
            "required_context": "extraction/match_stats",
            "selector_patterns": [r"stats.*selector", r"statistics.*selector", r"performance.*selector"]
        })
        
        # Rule: Navigation tabs get navigation selectors
        self.add_activation_rule("navigation_tab", {
            "tab_patterns": [r"nav", r"menu", r"sport"],
            "required_context": "navigation",
            "selector_patterns": [r"nav.*selector", r"menu.*selector", r"sport.*selector"]
        })
        
        # Rule: Authentication tabs get authentication selectors
        self.add_activation_rule("auth_tab", {
            "tab_patterns": [r"login", r"signin", r"auth", r"consent"],
            "required_context": "authentication",
            "selector_patterns": [r"login.*selector", r"signin.*selector", r"auth.*selector", r"consent.*selector"]
        })
        
        # Rule: Filtering tabs get filtering selectors
        self.add_activation_rule("filter_tab", {
            "tab_patterns": [r"filter", r"search", r"date"],
            "required_context": "filtering",
            "selector_patterns": [r"filter.*selector", r"search.*selector", r"date.*selector"]
        })
    
    def _setup_default_policies(self) -> None:
        """Setup default isolation policies."""
        # Policy: Only one tab of each type can be active
        self.add_isolation_policy("single_active_tab_per_type", {
            "description": "Only one tab of each type can be active",
            "enforcement": "strict"
        })
        
        # Policy: Context switching requires deactivation of previous context
        self.add_isolation_policy("context_switch_requires_deactivation", {
            "description": "Must deactivate previous context before activating new one",
            "grace_period_ms": 500
        })
        
        # Policy: Memory management for inactive tabs
        self.add_isolation_policy("inactive_tab_memory_cleanup", {
            "description": "Clean up selectors for inactive tabs after timeout",
            "timeout_minutes": 10,
            "max_inactive_tabs": 5
        })
        
        # Policy: Tab activation logging
        self.add_isolation_policy("activation_logging", {
            "description": "Log all activation events for debugging",
            "log_level": "info"
        })
    
    def add_activation_rule(self, rule_name: str, rule_config: Dict[str, Any]) -> None:
        """
        Add an activation rule.
        
        Args:
            rule_name: Name of the rule
            rule_config: Configuration for the rule
        """
        self.activation_rules[rule_name] = rule_config
        logger.info(f"Added activation rule: {rule_name}")
    
    def add_isolation_policy(self, policy_name: str, policy_config: Dict[str, Any]) -> None:
        """
        Add an isolation policy.
        
        Args:
            policy_name: Name of the policy
            policy_config: Configuration for the policy
        """
        self.isolation_policies[policy_name] = policy_config
        logger.info(f"Added isolation policy: {policy_name}")
    
    def add_event_listener(self, listener: Callable[[ActivationEvent], None]) -> None:
        """
        Add an event listener.
        
        Args:
            listener: Function to call on events
        """
        self.event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[ActivationEvent], None]) -> bool:
        """
        Remove an event listener.
        
        Args:
            listener: Function to remove
            
        Returns:
            bool: True if listener was removed
        """
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)
            return True
        return False
    
    async def register_tab(
        self,
        tab_id: str,
        tab_type: TabType,
        initial_context_path: Optional[str] = None,
        initial_dom_state: Optional[str] = None
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a new tab.
        
        Args:
            tab_id: Unique identifier for the tab
            tab_type: Type of the tab
            initial_context_path: Initial context path
            initial_dom_state: Initial DOM state
            metadata: Additional metadata
            
        Returns:
            bool: True if registration successful
        """
        with self._lock:
            if tab_id in self.tabs:
                logger.warning(f"Tab {tab_id} already registered")
                return False
            
            # Create tab context
            tab_context = TabContext(
                tab_id=tab_id,
                tab_type=tab_type,
                is_active=False,
                is_visible=False,
                is_loaded=False,
                context_path=initial_context_path,
                dom_state=initial_dom_state,
                metadata=metadata or {}
            )
            
            self.tabs[tab_id] = tab_context
            self.stats["active_tabs"] += 1
            
            logger.info(f"Registered tab: {tab_id} ({tab_type.value})")
            
            # Notify listeners
            await self._notify_event(ActivationEvent(
                timestamp=datetime.utcnow(),
                tab_id=tab_id,
                event_type="register",
                details={"tab_type": tab_type.value}
            ))
            
            return True
    
    async def activate_tab(
        self,
        tab_id: str,
        context_path: Optional[str] = None,
        dom_state: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Activate a tab and load its selectors.
        
        Args:
            tab_id: ID of tab to activate
            context_path: Context path for activation
            dom_state: DOM state for activation
            force: Force activation even if rules don't match
            
        Returns:
            bool: True if activation successful
        """
        start_time = datetime.utcnow()
        
        with self._lock:
            if tab_id not in self.tabs:
                logger.error(f"Tab {tab_id} not registered")
                return False
            
            tab_context = self.tabs[tab_id]
            
            # Check if activation is allowed by rules
            if not force and not await self._check_activation_rules(tab_context, context_path, dom_state):
                logger.warning(f"Activation blocked by rules for tab {tab_id}")
                return False
            
            # Check isolation policies
            if not await self._check_isolation_policies(tab_context):
                logger.warning(f"Activation blocked by isolation policies for tab {tab_id}")
                return False
            
            # Deactivate current active tab of same type if policy requires
            current_active = self._get_active_tab_of_type(tab_context.tab_type)
            if current_active and current_active != tab_id:
                policy = self.isolation_policies.get("single_active_tab_per_type")
                if policy and policy.get("enforcement") == "strict":
                    await self.deactivate_tab(current_active)
                    logger.info(f"Deactivated {current_active} due to single active tab policy")
            
            # Update tab context
            old_context_path = tab_context.context_path
            old_dom_state = tab_context.dom_state
            
            tab_context.is_active = True
            tab_context.is_visible = True
            tab_context.is_loaded = True
            tab_context.context_path = context_path or old_context_path
            tab_context.dom_state = dom_state or old_dom_state
            tab_context.last_activity = datetime.utcnow()
            
            # Update active tab tracking
            self.active_tab = tab_id
            
            # Load selectors for the new context
            selectors = await self._load_selectors_for_context(tab_context)
            tab_context.selectors = selectors
            
            # Update cache with new selectors
            if selectors:
                await self.cache.put_context_selectors(
                    context_path=tab_context.context_path,
                    selectors=selectors,
                    dom_state=tab_context.dom_state
                )
            
            # Update statistics
            activation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats["total_activations"] += 1
            self.stats["selector_loads"] += len(selectors)
            self._update_average_activation_time(activation_time)
            
            # Create activation event
            await self._notify_event(ActivationEvent(
                timestamp=datetime.utcnow(),
                tab_id=tab_id,
                event_type="activate",
                details={
                    "context_path": tab_context.context_path,
                    "dom_state": tab_context.dom_state,
                    "selectors_loaded": len(selectors),
                    "activation_time_ms": activation_time,
                    "previous_context": old_context_path
                }
            ))
            
            logger.info(
                f"Activated tab {tab_id} with {len(selectors)} selectors "
                f"(context: {tab_context.context_path}) in {activation_time:.2f}ms"
            )
            
            return True
    
    async def deactivate_tab(
        self,
        tab_id: str,
        reason: str = "manual_deactivation"
    ) -> bool:
        """
        Deactivate a tab.
        
        Args:
            tab_id: ID of tab to deactivate
            reason: Reason for deactivation
            
        Returns:
            bool: True if deactivation successful
        """
        start_time = datetime.utcnow()
        
        with self._lock:
            if tab_id not in self.tabs:
                logger.error(f"Tab {tab_id} not registered")
                return False
            
            tab_context = self.tabs[tab_id]
            
            if not tab_context.is_active:
                logger.warning(f"Tab {tab_id} is not active")
                return True
            
            # Update tab context
            tab_context.is_active = False
            tab_context.last_activity = datetime.utcnow()
            
            # Update active tab tracking
            if self.active_tab == tab_id:
                self.active_tab = None
            
            # Clear selectors from cache
            if tab_context.context_path:
                await self.cache.invalidate_context(tab_context.context_path, tab_context.dom_state)
            
            # Update statistics
            deactivation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats["total_deactivations"] += 1
            self._update_average_activation_time(deactivation_time)
            
            # Create deactivation event
            await self._notify_event(ActivationEvent(
                timestamp=datetime.utcnow(),
                tab_id=tab_id,
                event_type="deactivate",
                details={
                    "reason": reason,
                    "deactivation_time_ms": deactivation_time
                }
            ))
            
            logger.info(f"Deactivated tab {tab_id} in {deactivation_time:.2f}ms")
            return True
    
    async def switch_context(
        self,
        tab_id: str,
        new_context_path: str,
        new_dom_state: Optional[str] = None
    ) -> bool:
        """
        Switch context for an active tab.
        
        Args:
            tab_id: ID of tab to switch context for
            new_context_path: New context path
            new_dom_state: New DOM state
            
        Returns:
            bool: True if switch successful
        """
        return await self.activate_tab(
            tab_id=tab_id,
            context_path=new_context_path,
            dom_state=new_dom_state
        )
    
    def get_active_tab(self) -> Optional[TabContext]:
        """Get the currently active tab."""
        with self._lock:
            return self.tabs.get(self.active_tab) if self.active_tab else None
    
    def get_tab_context(self, tab_id: str) -> Optional[TabContext]:
        """Get context for a specific tab."""
        with self._lock:
            return self.tabs.get(tab_id)
    
    def get_active_selectors(self) -> List[Any]:
        """Get selectors for the currently active tab."""
        active_tab = self.get_active_tab()
        
        if active_tab and active_tab.selectors:
            return active_tab.selectors
        
        return []
    
    async def _check_activation_rules(
        self,
        tab_context: TabContext,
        context_path: Optional[str],
        dom_state: Optional[str]
    ) -> bool:
        """Check if activation is allowed by rules."""
        for rule_name, rule_config in self.activation_rules.items():
            if await self._evaluate_activation_rule(rule_name, rule_config, tab_context, context_path, dom_state):
                logger.debug(f"Activation allowed by rule: {rule_name}")
                return True
        
        logger.debug(f"Activation blocked by rule: {rule_name}")
        return False
    
    async def _evaluate_activation_rule(
        self,
        rule_name: str,
        rule_config: Dict[str, Any],
        tab_context: TabContext,
        context_path: Optional[str],
        dom_state: Optional[str]
    ) -> bool:
        """Evaluate a specific activation rule."""
        tab_patterns = rule_config.get("tab_patterns", [])
        required_context = rule_config.get("required_context")
        selector_patterns = rule_config.get("selector_patterns", [])
        
        # Check tab type patterns
        for pattern in tab_patterns:
            import re
            if re.search(pattern, tab_context.tab_id, re.IGNORECASE):
                logger.debug(f"Tab ID matches pattern {pattern} for rule {rule_name}")
                break
        
        # Check required context
        if required_context and context_path != required_context:
            logger.debug(f"Context path {context_path} doesn't match required {required_context} for rule {rule_name}")
            return False
        
        # Check selector patterns (would need access to tab selectors)
        # This is a simplified check - in practice, you'd load selectors and check patterns
        
        return True
    
    async def _check_isolation_policies(self, tab_context: TabContext) -> bool:
        """Check if activation is allowed by isolation policies."""
        for policy_name, policy_config in self.isolation_policies.items():
            if not await self._evaluate_isolation_policy(policy_name, policy_config, tab_context):
                logger.debug(f"Isolation policy {policy_name} allows activation")
                return False
        
        return True
    
    async def _evaluate_isolation_policy(
        self,
        policy_name: str,
        policy_config: Dict[str, Any],
        tab_context: TabContext
    ) -> bool:
        """Evaluate a specific isolation policy."""
        # Policy: single_active_tab_per_type
        if policy_name == "single_active_tab_per_type":
            if policy_config.get("enforcement") == "strict":
                current_active = self._get_active_tab_of_type(tab_context.tab_type)
                return current_active is None or current_active.tab_id == tab_context.tab_id
        
        # Policy: context_switch_requires_deactivation
        if policy_name == "context_switch_requires_deactivation":
            # Check if there's an active tab that needs deactivation
            if self.active_tab and self.active_tab != tab_context.tab_id:
                return False  # Would need to deactivate first
        
        return True
    
    def _get_active_tab_of_type(self, tab_type: TabType) -> Optional[str]:
        """Get the active tab ID of a specific type."""
        for tab_id, tab_context in self.tabs.items():
            if tab_context.is_active and tab_context.tab_type == tab_type:
                return tab_id
        return None
    
    async def _load_selectors_for_context(self, tab_context: TabContext) -> List[Any]:
        """Load selectors appropriate for the tab context."""
        if not tab_context.context_path:
            return []
        
        try:
            # Get selectors from cache
            selectors = await self.cache.get_context_selectors(
                context_path=tab_context.context_path,
                dom_state=tab_context.dom_state
            )
            
            # Apply activation rule modifications
            rule_name = await self._get_matching_rule(tab_context)
            if rule_name:
                rule_config = self.activation_rules.get(rule_name, {})
                await self._apply_rule_modifications(selectors, rule_config)
            
            return selectors
            
        except Exception as e:
            logger.error(f"Error loading selectors for {tab_context.context_path}: {e}")
            return []
    
    async def _get_matching_rule(self, tab_context: TabContext) -> Optional[str]:
        """Find the activation rule that matches this tab."""
        for rule_name, rule_config in self.activation_rules.items():
            tab_patterns = rule_config.get("tab_patterns", [])
            
            for pattern in tab_patterns:
                import re
                if re.search(pattern, tab_context.tab_id, re.IGNORECASE):
                    return rule_name
        
        return None
    
    async def _apply_rule_modifications(
        self,
        selectors: List[Any],
        rule_config: Dict[str, Any]
    ) -> List[Any]:
        """Apply rule modifications to selectors."""
        # This is a placeholder for rule-based modifications
        # In practice, you would modify selectors based on rule requirements
        return selectors
    
    def _update_average_activation_time(self, activation_time: float) -> None:
        """Update running average of activation times."""
        total_activations = self.stats["total_activations"]
        if total_activations == 1:
            self.stats["average_activation_time_ms"] = activation_time
        else:
            # Exponential moving average with alpha = 0.1
            alpha = 0.1
            current_avg = self.stats["average_activation_time_ms"]
            new_avg = (alpha * activation_time) + ((1 - alpha) * current_avg)
            self.stats["average_activation_time_ms"] = new_avg
    
    async def _notify_event(self, event: ActivationEvent) -> None:
        """Notify all event listeners."""
        for listener in self.event_listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
        
        # Add to history
        self.tab_history.append(event)
        
        # Limit history size
        if len(self.tab_history) > self.max_history_size:
            self.tab_history = self.tab_history[-self.max_history_size:]
    
    def get_tab_statistics(self) -> Dict[str, Any]:
        """Get tab management statistics."""
        with self._lock:
            active_tabs = sum(1 for tab in self.tabs.values() if tab.is_active)
            
            return {
                **self.stats,
                "registered_tabs": len(self.tabs),
                "active_tabs": active_tabs,
                "tab_types": {
                    tab_type.value: sum(1 for tab in self.tabs.values() if tab.tab_type == tab_type)
                    for tab_type in TabType
                },
                "active_tab_id": self.active_tab,
                "history_size": len(self.tab_history)
            }
    
    def get_tab_history(self, limit: int = 50) -> List[ActivationEvent]:
        """Get recent tab activation history."""
        with self._lock:
            return sorted(
                self.tab_history[-limit:],
                key=lambda event: event.timestamp,
                reverse=True
            )
    
    async def cleanup_inactive_tabs(self) -> int:
        """Clean up resources for inactive tabs."""
        cleanup_count = 0
        current_time = datetime.utcnow()
        
        with self._lock:
            policy = self.isolation_policies.get("inactive_tab_memory_cleanup", {})
            timeout_minutes = policy.get("timeout_minutes", 10)
            max_inactive_tabs = policy.get("max_inactive_tabs", 5)
            
            inactive_tabs = []
            
            for tab_id, tab_context in self.tabs.items():
                if not tab_context.is_active:
                    age_minutes = (current_time - tab_context.last_activity).total_seconds() / 60
                    
                    if age_minutes > timeout_minutes:
                        # Clean up selectors and mark for cleanup
                        if tab_context.context_path:
                            await self.cache.invalidate_context(tab_context.context_path)
                        
                        tab_context.selectors = []
                        cleanup_count += 1
                        
                        logger.info(f"Cleaned up inactive tab: {tab_id}")
            
                    elif len(inactive_tabs) < max_inactive_tabs:
                        inactive_tabs.append(tab_id)
            
            # Remove oldest inactive tabs if over limit
            if len(inactive_tabs) > max_inactive_tabs:
                # Sort by last activity and remove oldest
                inactive_tabs.sort(key=lambda tid: self.tabs[tid].last_activity)
                excess_tabs = inactive_tabs[max_inactive_tabs:]
                
                for tab_id in excess_tabs:
                    del self.tabs[tab_id]
                    logger.info(f"Removed inactive tab: {tab_id}")
                    cleanup_count += 1
        
        return cleanup_count


# Global tab manager instance
_tab_manager: Optional[TabScopedSelectorManager] = None


def get_tab_manager(cache_id: str = "default") -> TabScopedSelectorManager:
    """
    Get or create the global tab manager.
    
    Args:
        cache_id: ID of the cache to use
        
    Returns:
        TabScopedSelectorManager: Manager instance
    """
    global _tab_manager
    
    if _tab_manager is None:
        _tab_manager = TabScopedSelectorManager(cache_id)
        logger.info(f"Created tab manager for cache: {cache_id}")
    
    return _tab_manager
