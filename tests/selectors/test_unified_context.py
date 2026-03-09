"""
Unit tests for UnifiedContext module.

These tests verify:
- UnifiedContext creation and validation
- Conversion from SelectorContext
- Conversion from DOMContext
- Conversion to SelectorContext (backward compatibility)
- Conversion to DOMContext (engine calls)
- Metadata preservation
- Context path generation
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from src.selectors.unified_context import (
    UnifiedContext,
    from_selector_context,
    from_dom_context,
    create_unified_context,
    ContextConversionError,
    ContextValidationError,
    DOMState,
)


class TestUnifiedContextCreation:
    """Tests for UnifiedContext creation."""

    def test_create_minimal_context(self):
        """Test creating a minimal unified context."""
        ctx = UnifiedContext(primary_context="extraction")

        assert ctx.primary_context == "extraction"
        assert ctx.url == ""
        assert ctx.is_active is True
        assert ctx.context_source == "unified"

    def test_create_full_context(self):
        """Test creating a full unified context with all fields."""
        page = Mock()
        now = datetime.now(timezone.utc)

        ctx = UnifiedContext(
            page=page,
            url="https://example.com",
            timestamp=now,
            primary_context="extraction",
            secondary_context="match_list",
            tertiary_context="live",
            dom_state=DOMState.LIVE,
            tab_context="main",
            metadata={"key": "value"}
        )

        assert ctx.page is page
        assert ctx.url == "https://example.com"
        assert ctx.timestamp == now
        assert ctx.primary_context == "extraction"
        assert ctx.secondary_context == "match_list"
        assert ctx.tertiary_context == "live"
        assert ctx.dom_state == DOMState.LIVE
        assert ctx.tab_context == "main"
        assert ctx.metadata["key"] == "value"

    def test_invalid_primary_context_raises_error(self):
        """Test that invalid primary context raises validation error."""
        with pytest.raises(ContextValidationError):
            UnifiedContext(primary_context="invalid_context")

    def test_default_primary_context(self):
        """Test default primary context value."""
        ctx = UnifiedContext()
        assert ctx.primary_context == "extraction"


class TestContextPath:
    """Tests for context path generation."""

    def test_context_path_primary_only(self):
        """Test context path with only primary context."""
        ctx = UnifiedContext(primary_context="navigation")
        assert ctx.get_context_path() == "navigation"

    def test_context_path_with_secondary(self):
        """Test context path with secondary context."""
        ctx = UnifiedContext(
            primary_context="extraction",
            secondary_context="match_list"
        )
        assert ctx.get_context_path() == "extraction/match_list"

    def test_context_path_with_tertiary(self):
        """Test context path with all levels."""
        ctx = UnifiedContext(
            primary_context="extraction",
            secondary_context="match_summary",
            tertiary_context="ft"
        )
        assert ctx.get_context_path() == "extraction/match_summary/ft"


class TestHierarchicalContext:
    """Tests for hierarchical context methods."""

    def test_get_hierarchical_context(self):
        """Test getting hierarchical context as dict."""
        ctx = UnifiedContext(
            primary_context="extraction",
            secondary_context="match_list",
            tertiary_context="live",
            dom_state=DOMState.LIVE,
            tab_context="main",
            is_active=True
        )

        result = ctx.get_hierarchical_context()

        assert result["primary"] == "extraction"
        assert result["secondary"] == "match_list"
        assert result["tertiary"] == "live"
        assert result["dom_state"] == "live"
        assert result["tab_context"] == "main"
        assert result["is_active"] is True


class TestDOMContextInfo:
    """Tests for DOM context info methods."""

    def test_get_dom_context_info(self):
        """Test getting DOM context info as dict."""
        now = datetime.now(timezone.utc)
        page = Mock()

        ctx = UnifiedContext(
            page=page,
            url="https://example.com",
            timestamp=now,
            metadata={"key": "value"}
        )

        result = ctx.get_dom_context_info()

        assert result["url"] == "https://example.com"
        assert result["timestamp"] == now.isoformat()
        assert result["has_page"] is True
        assert result["metadata"]["key"] == "value"


class TestMetadataOperations:
    """Tests for metadata operations."""

    def test_add_metadata(self):
        """Test adding metadata to context."""
        ctx = UnifiedContext(primary_context="extraction")
        ctx.add_metadata("test_key", "test_value")

        assert ctx.get_metadata("test_key") == "test_value"

    def test_get_metadata_default(self):
        """Test getting metadata with default value."""
        ctx = UnifiedContext(primary_context="extraction")

        assert ctx.get_metadata("nonexistent", "default") == "default"


class TestSelectorContextConversion:
    """Tests for conversion to SelectorContext."""

    def test_to_selector_context(self):
        """Test converting to SelectorContext."""
        now = datetime.now(timezone.utc)
        ctx = UnifiedContext(
            primary_context="extraction",
            secondary_context="match_list",
            tertiary_context="live",
            dom_state=DOMState.LIVE,
            is_active=True,
            created_at=now,
            updated_at=now
        )

        sc = ctx.to_selector_context()

        assert sc.primary_context == "extraction"
        assert sc.secondary_context == "match_list"
        assert sc.tertiary_context == "live"
        assert sc.dom_state == DOMState.LIVE
        assert sc.is_active is True


class TestDOMContextConversion:
    """Tests for conversion to DOMContext."""

    def test_to_dom_context_with_page(self):
        """Test converting to DOMContext with page."""
        page = Mock()
        now = datetime.now(timezone.utc)

        ctx = UnifiedContext(
            page=page,
            url="https://example.com",
            timestamp=now,
            tab_context="main",
            primary_context="extraction"
        )

        dc = ctx.to_dom_context()

        assert dc.page is page
        assert dc.tab_context == "main"
        assert dc.url == "https://example.com"
        assert dc.timestamp == now

    def test_to_dom_context_without_page_raises_error(self):
        """Test that converting without page raises error."""
        ctx = UnifiedContext(
            primary_context="extraction",
            tab_context="main"
        )

        with pytest.raises(ContextConversionError, match="without a page object"):
            ctx.to_dom_context()

    def test_to_dom_context_without_tab_context_raises_error(self):
        """Test that converting without tab_context raises error."""
        page = Mock()
        ctx = UnifiedContext(
            page=page,
            primary_context="extraction"
        )

        with pytest.raises(ContextConversionError, match="without a tab_context"):
            ctx.to_dom_context()

    def test_to_dom_context_preserves_metadata(self):
        """Test that metadata is preserved in conversion."""
        page = Mock()
        now = datetime.now(timezone.utc)

        ctx = UnifiedContext(
            page=page,
            url="https://example.com",
            timestamp=now,
            tab_context="main",
            primary_context="extraction",
            secondary_context="match_list",
            selector_context=Mock(),  # Add selector_context to trigger metadata inclusion
            metadata={"custom": "data"}
        )

        dc = ctx.to_dom_context()

        assert dc.metadata["custom"] == "data"
        assert "selector_context" in dc.metadata


class TestFromSelectorContext:
    """Tests for from_selector_context conversion."""

    def test_from_selector_context_basic(self):
        """Test basic conversion from SelectorContext."""
        from src.selectors.context_manager import SelectorContext

        sc = SelectorContext(
            primary_context="extraction",
            secondary_context="match_list",
            tertiary_context="live",
            dom_state=DOMState.LIVE
        )

        uc = from_selector_context(sc)

        assert uc.primary_context == "extraction"
        assert uc.secondary_context == "match_list"
        assert uc.tertiary_context == "live"
        assert uc.dom_state == DOMState.LIVE
        assert uc.context_source == "selector"
        assert uc.selector_context is sc
        assert uc.metadata["converted_from"] == "selector_context"

    def test_from_selector_context_with_page(self):
        """Test conversion from SelectorContext with page."""
        from src.selectors.context_manager import SelectorContext

        page = Mock()
        sc = SelectorContext(
            primary_context="navigation",
            secondary_context="main_menu"
        )

        uc = from_selector_context(sc, page=page, url="https://example.com")

        assert uc.page is page
        assert uc.url == "https://example.com"
        assert uc.primary_context == "navigation"
        assert uc.secondary_context == "main_menu"


class TestFromDOMContext:
    """Tests for from_dom_context conversion."""

    def test_from_dom_context_basic(self):
        """Test basic conversion from DOMContext."""
        from src.selectors.context import DOMContext

        page = Mock()
        now = datetime.now(timezone.utc)
        dc = DOMContext(
            page=page,
            tab_context="main",
            url="https://example.com",
            timestamp=now,
            metadata={"key": "value"}
        )

        uc = from_dom_context(dc)

        assert uc.page is page
        assert uc.tab_context == "main"
        assert uc.url == "https://example.com"
        assert uc.timestamp == now
        assert uc.metadata["key"] == "value"
        assert uc.context_source == "dom"
        assert uc.dom_context is dc

    def test_from_dom_context_extracts_selector_metadata(self):
        """Test that selector metadata is extracted from DOMContext."""
        from src.selectors.context import DOMContext

        page = Mock()
        now = datetime.now(timezone.utc)
        dc = DOMContext(
            page=page,
            tab_context="main",
            url="https://example.com",
            timestamp=now,
            metadata={
                "selector_context": {
                    "primary": "extraction",
                    "secondary": "match_list",
                    "dom_state": "live"
                }
            }
        )

        uc = from_dom_context(dc)

        assert uc.primary_context == "extraction"
        assert uc.secondary_context == "match_list"
        assert uc.dom_state == DOMState.LIVE


class TestCreateUnifiedContext:
    """Tests for create_unified_context factory function."""

    def test_create_with_all_params(self):
        """Test creating with all parameters."""
        page = Mock()

        uc = create_unified_context(
            primary_context="extraction",
            page=page,
            url="https://example.com",
            secondary_context="match_list",
            tertiary_context="live",
            dom_state=DOMState.LIVE,
            tab_context="main",
            metadata={"custom": "value"}
        )

        assert uc.primary_context == "extraction"
        assert uc.page is page
        assert uc.url == "https://example.com"
        assert uc.secondary_context == "match_list"
        assert uc.tertiary_context == "live"
        assert uc.dom_state == DOMState.LIVE
        assert uc.tab_context == "main"
        assert uc.metadata["custom"] == "value"

    def test_create_with_minimal_params(self):
        """Test creating with minimal parameters."""
        uc = create_unified_context(primary_context="navigation")

        assert uc.primary_context == "navigation"
        assert uc.url == ""
        assert uc.page is None
        assert uc.secondary_context is None


class TestTimestampUpdate:
    """Tests for timestamp update functionality."""

    def test_update_timestamp(self):
        """Test timestamp update method."""
        ctx = UnifiedContext(primary_context="extraction")
        original_timestamp = ctx.timestamp

        # Small delay to ensure different timestamp
        import time
        time.sleep(0.01)

        ctx.update_timestamp()

        assert ctx.timestamp > original_timestamp
        assert ctx.updated_at >= ctx.timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
