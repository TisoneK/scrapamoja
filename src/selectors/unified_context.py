"""
Unified Context Model for Selector Engine.

This module provides a unified context model that combines SelectorContext
(Flashscore hierarchical context) and DOMContext (Engine DOM resolution)
into a single cohesive interface.

Design Goals:
- Backward Compatibility: All existing SelectorContext usage continues to work
- Forward Compatibility: All DOMContext capabilities are available
- Single Source of Truth: One context object for all operations
- No Breaking Changes: Existing selectors work without modification
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

from playwright.async_api import Page

from src.models.selector_models import TabContext
from src.utils.exceptions import SelectorEngineError

# Import existing context classes for conversion
from src.selectors.context_manager import (
    SelectorContext,
    DOMState,
    SelectorContextManager
)
from src.selectors.context import DOMContext


# Custom exceptions for unified context
class UnifiedContextError(SelectorEngineError):
    """Base exception for unified context operations."""
    pass


class ContextConversionError(UnifiedContextError):
    """Raised when context conversion fails."""
    pass


class ContextValidationError(UnifiedContextError):
    """Raised when unified context validation fails."""
    pass


# Type alias for context source
ContextSource = str  # "selector", "dom", "unified"


@dataclass
class UnifiedContext:
    """
    Unified context model combining SelectorContext and DOMContext.

    This class provides a single interface for both Flashscore hierarchical
    context (authentication, navigation, extraction) and Engine DOM resolution
    (page, URL, timestamp).

    Mapping from SelectorContext:
        - primary_context → primary_context (kept as-is)
        - secondary_context → secondary_context (kept as-is)
        - tertiary_context → tertiary_context (kept as-is)
        - dom_state → dom_state (kept as-is)
        - tab_context → tab_context (kept as-is, converted to string)

    Mapping from DOMContext:
        - page → page (Playwright page object)
        - url → url (current page URL)
        - timestamp → timestamp (creation time)
        - tab_context → tab_context (string identifier)
        - metadata → metadata (combined with selector context metadata)
    """

    # Core identity (from DOMContext)
    page: Optional[Page] = None  # Playwright page - Optional for backward compat
    url: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Hierarchical context (from SelectorContext)
    primary_context: str = "extraction"  # authentication, navigation, extraction, filtering
    secondary_context: Optional[str] = None  # match_list, match_summary, etc.
    tertiary_context: Optional[str] = None  # inc_ot, ft, q1, q2, etc.

    # State information (from SelectorContext)
    dom_state: Optional[DOMState] = None
    tab_context: Optional[str] = None  # String identifier for tab

    # Metadata (combined from both)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Legacy support - keep references to original contexts
    selector_context: Optional[SelectorContext] = None  # For backward compat
    dom_context: Optional[DOMContext] = None  # For engine calls

    # Tracking
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context_source: ContextSource = "unified"

    def __post_init__(self) -> None:
        """Validate unified context after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate context fields."""
        # Validate primary context
        valid_primary_contexts = {"authentication", "navigation", "extraction", "filtering"}
        if self.primary_context not in valid_primary_contexts:
            raise ContextValidationError(
                f"Invalid primary_context: {self.primary_context}. "
                f"Must be one of: {valid_primary_contexts}"
            )

        # Update timestamp on validation
        self.updated_at = datetime.now(timezone.utc)

    def get_context_path(self) -> str:
        """
        Get the full context path as a string.

        Returns:
            str: Context path like "extraction/match_list" or "authentication"
        """
        parts = [self.primary_context]
        if self.secondary_context:
            parts.append(self.secondary_context)
        if self.tertiary_context:
            parts.append(self.tertiary_context)
        return "/".join(parts)

    def get_hierarchical_context(self) -> Dict[str, Any]:
        """
        Get hierarchical context as a dictionary.

        Returns:
            Dict containing primary, secondary, tertiary contexts and DOM state
        """
        return {
            "primary": self.primary_context,
            "secondary": self.secondary_context,
            "tertiary": self.tertiary_context,
            "dom_state": self.dom_state.value if self.dom_state else None,
            "tab_context": self.tab_context,
            "is_active": self.is_active
        }

    def get_dom_context_info(self) -> Dict[str, Any]:
        """
        Get DOM context info as a dictionary.

        Returns:
            Dict containing page URL, timestamp, and metadata
        """
        return {
            "url": self.url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "has_page": self.page is not None,
            "metadata": self.metadata
        }

    def to_selector_context(self) -> SelectorContext:
        """
        Convert to SelectorContext for backward compatibility.

        Returns:
            SelectorContext: Equivalent SelectorContext instance
        """
        # Convert string tab_context back to TabContext if needed
        tab_ctx: Optional[TabContext] = None
        if self.tab_context:
            tab_ctx = TabContext(
                name=self.tab_context,
                container_selector="",
                activation_selector="",
                is_available=True
            )

        return SelectorContext(
            primary_context=self.primary_context,
            secondary_context=self.secondary_context,
            tertiary_context=self.tertiary_context,
            dom_state=self.dom_state,
            tab_context=tab_ctx,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    def to_dom_context(self) -> DOMContext:
        """
        Convert to DOMContext for engine calls.

        Returns:
            DOMContext: Equivalent DOMContext instance

        Raises:
            ContextConversionError: If required fields are missing
        """
        if self.page is None:
            raise ContextConversionError(
                "Cannot convert to DOMContext without a page object"
            )

        if not self.tab_context:
            raise ContextConversionError(
                "Cannot convert to DOMContext without a tab_context"
            )

        # Combine metadata from unified context
        combined_metadata = dict(self.metadata)
        if self.selector_context:
            combined_metadata["selector_context"] = {
                "primary": self.primary_context,
                "secondary": self.secondary_context,
                "tertiary": self.tertiary_context,
                "dom_state": self.dom_state.value if self.dom_state else None
            }

        return DOMContext(
            page=self.page,
            tab_context=self.tab_context,
            url=self.url or "unknown",
            timestamp=self.timestamp,
            metadata=combined_metadata
        )

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to context."""
        self.metadata[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)

    def update_timestamp(self) -> None:
        """Update the timestamp to current time."""
        self.timestamp = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


# Conversion functions
def from_selector_context(
    sc: SelectorContext,
    page: Optional[Page] = None,
    url: str = ""
) -> UnifiedContext:
    """
    Convert SelectorContext to UnifiedContext.

    Args:
        sc: SelectorContext to convert
        page: Optional Playwright page object
        url: Optional URL string

    Returns:
        UnifiedContext: Converted unified context
    """
    # Extract tab_context string from TabContext if present
    tab_ctx_str: Optional[str] = None
    if sc.tab_context:
        if hasattr(sc.tab_context, 'name'):
            tab_ctx_str = sc.tab_context.name
        elif isinstance(sc.tab_context, str):
            tab_ctx_str = sc.tab_context

    # Build metadata from selector context
    metadata: Dict[str, Any] = {
        "converted_from": "selector_context",
        "original_context_path": sc.get_context_path()
    }

    return UnifiedContext(
        page=page,
        url=url or "",
        timestamp=sc.updated_at,
        primary_context=sc.primary_context,
        secondary_context=sc.secondary_context,
        tertiary_context=sc.tertiary_context,
        dom_state=sc.dom_state,
        tab_context=tab_ctx_str,
        metadata=metadata,
        selector_context=sc,
        is_active=sc.is_active,
        created_at=sc.created_at,
        updated_at=sc.updated_at,
        context_source="selector"
    )


def from_dom_context(dc: DOMContext) -> UnifiedContext:
    """
    Convert DOMContext to UnifiedContext.

    Args:
        dc: DOMContext to convert

    Returns:
        UnifiedContext: Converted unified context
    """
    # Extract hierarchical context from metadata if present
    selector_meta = dc.metadata.get("selector_context", {})
    primary = selector_meta.get("primary", "extraction")
    secondary = selector_meta.get("secondary")
    tertiary = selector_meta.get("tertiary")

    # Parse DOM state from metadata if present
    dom_state: Optional[DOMState] = None
    dom_state_str = selector_meta.get("dom_state")
    if dom_state_str:
        try:
            dom_state = DOMState(dom_state_str)
        except ValueError:
            pass

    # Build comprehensive metadata
    metadata = dict(dc.metadata)
    metadata["converted_from"] = "dom_context"

    return UnifiedContext(
        page=dc.page,
        url=dc.url,
        timestamp=dc.timestamp,
        primary_context=primary,
        secondary_context=secondary,
        tertiary_context=tertiary,
        dom_state=dom_state,
        tab_context=dc.tab_context,
        metadata=metadata,
        dom_context=dc,
        context_source="dom"
    )


def create_unified_context(
    primary_context: str,
    page: Optional[Page] = None,
    url: str = "",
    secondary_context: Optional[str] = None,
    tertiary_context: Optional[str] = None,
    dom_state: Optional[DOMState] = None,
    tab_context: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> UnifiedContext:
    """
    Create a new UnifiedContext from scratch.

    Args:
        primary_context: Primary context (authentication, navigation, extraction, filtering)
        page: Optional Playwright page object
        url: Optional URL string
        secondary_context: Optional secondary context
        tertiary_context: Optional tertiary context
        dom_state: Optional DOM state
        tab_context: Optional tab context string
        metadata: Optional metadata dictionary

    Returns:
        UnifiedContext: New unified context instance
    """
    return UnifiedContext(
        page=page,
        url=url or "",
        timestamp=datetime.now(timezone.utc),
        primary_context=primary_context,
        secondary_context=secondary_context,
        tertiary_context=tertiary_context,
        dom_state=dom_state,
        tab_context=tab_context,
        metadata=metadata or {},
        context_source="unified"
    )


# Backward compatibility - keep original class names accessible
SelectorContext = SelectorContext  # noqa: F811
DOMContext = DOMContext  # noqa: F811
DOMState = DOMState  # noqa: F811


__all__ = [
    # Main class
    "UnifiedContext",

    # Custom exceptions
    "UnifiedContextError",
    "ContextConversionError",
    "ContextValidationError",

    # Conversion functions
    "from_selector_context",
    "from_dom_context",
    "create_unified_context",

    # Type alias
    "ContextSource",

    # Re-export for backward compatibility
    "SelectorContext",
    "DOMContext",
    "DOMState",
]
