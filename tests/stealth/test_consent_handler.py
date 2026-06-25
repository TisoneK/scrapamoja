"""
Tests for consent dialog handling subsystem.

Validates that ConsentHandler can detect and accept various consent
dialog patterns reliably.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.stealth.consent_handler import (
    ConsentHandler,
    ConsentPattern,
    DialogType,
    STANDARD_PATTERNS,
)


class TestConsentPatternInitialization:
    """Tests for ConsentPattern initialization."""

    def test_pattern_init_basic(self):
        """ConsentPattern initializes with required fields."""
        pattern = ConsentPattern(
            name="test_pattern",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
        )
        assert pattern.name == "test_pattern"
        assert pattern.dialog_selector == ".dialog"
        assert pattern.accept_button_selector == ".accept"
        assert pattern.text_heuristics == []

    def test_pattern_init_with_heuristics(self):
        """ConsentPattern initializes with text heuristics."""
        heuristics = ["cookie", "consent"]
        pattern = ConsentPattern(
            name="test_pattern",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
            text_heuristics=heuristics,
        )
        assert pattern.text_heuristics == heuristics


class TestConsentHandlerInitialization:
    """Tests for ConsentHandler initialization."""

    def test_handler_init_defaults(self):
        """ConsentHandler initializes with default timeout."""
        handler = ConsentHandler()
        assert handler.timeout_seconds == 5.0
        assert handler.event_builder is None
        assert handler.custom_patterns == []

    def test_handler_init_custom_timeout(self):
        """ConsentHandler accepts custom timeout."""
        handler = ConsentHandler(timeout_seconds=10.0)
        assert handler.timeout_seconds == 10.0

    def test_handler_init_with_event_builder(self):
        """ConsentHandler accepts event builder."""
        mock_builder = MagicMock()
        handler = ConsentHandler(event_builder=mock_builder)
        assert handler.event_builder is mock_builder


class TestStandardPatterns:
    """Tests for standard consent patterns."""

    def test_standard_patterns_defined(self):
        """Standard patterns are defined."""
        assert len(STANDARD_PATTERNS) >= 3
        pattern_names = [p.name for p in STANDARD_PATTERNS]
        assert "cookie_banner_standard" in pattern_names
        assert "gdpr_modal_standard" in pattern_names

    def test_all_patterns_have_required_fields(self):
        """All standard patterns have required fields."""
        for pattern in STANDARD_PATTERNS:
            assert pattern.name
            assert pattern.dialog_selector
            assert pattern.accept_button_selector


class TestConsentPatternMatching:
    """Tests for pattern matching logic."""

    @pytest.mark.asyncio
    async def test_pattern_matches_dialog_exists(self):
        """Pattern matches when dialog element exists."""
        pattern = ConsentPattern(
            name="test",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
        )
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=MagicMock())  # Element found
        
        matches = await pattern.matches(page)
        assert matches is True

    @pytest.mark.asyncio
    async def test_pattern_no_match_dialog_missing(self):
        """Pattern doesn't match when dialog element missing."""
        pattern = ConsentPattern(
            name="test",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
        )
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        
        matches = await pattern.matches(page)
        assert matches is False

    @pytest.mark.asyncio
    async def test_pattern_matches_with_text_heuristics(self):
        """Pattern uses text heuristics for matching."""
        pattern = ConsentPattern(
            name="test",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
            text_heuristics=["cookie", "consent"],
        )
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=MagicMock())
        page.content = AsyncMock(return_value="<html>Please accept our cookies</html>")
        
        matches = await pattern.matches(page)
        assert matches is True

    @pytest.mark.asyncio
    async def test_pattern_no_match_wrong_text(self):
        """Pattern doesn't match when text heuristics fail."""
        pattern = ConsentPattern(
            name="test",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
            text_heuristics=["cookie", "consent"],
        )
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=MagicMock())
        page.content = AsyncMock(return_value="<html>No relevant keywords here</html>")
        
        matches = await pattern.matches(page)
        assert matches is False


class TestConsentDetection:
    """Tests for consent dialog detection."""

    @pytest.mark.asyncio
    async def test_detect_dialog_found(self):
        """detect_dialog finds dialog when present."""
        handler = ConsentHandler()
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=MagicMock())
        page.content = AsyncMock(return_value="<html>Accept cookies</html>")
        
        found, dialog_type, pattern_name = await handler.detect_dialog(page)
        assert found is True
        assert dialog_type is not None
        assert pattern_name is not None

    @pytest.mark.asyncio
    async def test_detect_dialog_not_found(self):
        """detect_dialog returns false when no dialog."""
        handler = ConsentHandler()
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        
        found, dialog_type, pattern_name = await handler.detect_dialog(page)
        assert found is False
        assert dialog_type is None
        assert pattern_name is None

    @pytest.mark.asyncio
    async def test_detect_dialog_custom_pattern(self):
        """detect_dialog uses custom patterns."""
        handler = ConsentHandler()
        custom_pattern = ConsentPattern(
            name="custom_test",
            dialog_selector=".custom-dialog",
            accept_button_selector=".custom-accept",
        )
        handler.register_pattern(custom_pattern)
        
        page = AsyncMock()
        
        # Mock query_selector to return element for custom pattern selector
        def query_selector_side_effect(selector):
            if ".custom-dialog" in selector:
                return MagicMock()
            return None
        
        page.query_selector = AsyncMock(side_effect=query_selector_side_effect)
        
        found, dialog_type, pattern_name = await handler.detect_dialog(page)
        assert found is True
        assert pattern_name == "custom_test"


class TestConsentAcceptance:
    """Tests for dialog acceptance."""

    @pytest.mark.asyncio
    async def test_accept_consent_success(self):
        """accept_consent successfully clicks and validates."""
        handler = ConsentHandler()
        pattern = ConsentPattern(
            name="test",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
        )
        
        mock_button = AsyncMock()
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)  # Dialog dismissed
        
        # Mock find_accept_button to return button
        pattern.find_accept_button = AsyncMock(return_value=mock_button)
        
        success = await handler.accept_consent(page, pattern=pattern, verify_dismissed=True)
        assert success is True
        mock_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_accept_consent_button_not_found(self):
        """accept_consent fails if button not found."""
        handler = ConsentHandler()
        pattern = ConsentPattern(
            name="test",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
        )
        
        page = AsyncMock()
        pattern.find_accept_button = AsyncMock(return_value=None)
        
        success = await handler.accept_consent(page, pattern=pattern)
        assert success is False

    @pytest.mark.asyncio
    async def test_accept_consent_dialog_not_dismissed(self):
        """accept_consent fails if dialog still visible."""
        handler = ConsentHandler()
        pattern = ConsentPattern(
            name="test",
            dialog_selector=".dialog",
            accept_button_selector=".accept",
        )
        
        mock_button = AsyncMock()
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=MagicMock())  # Dialog still visible
        
        pattern.find_accept_button = AsyncMock(return_value=mock_button)
        
        success = await handler.accept_consent(page, pattern=pattern, verify_dismissed=True)
        assert success is False


class TestDetectAndAccept:
    """Tests for detect_and_accept convenience method."""

    @pytest.mark.asyncio
    async def test_detect_and_accept_success(self):
        """detect_and_accept successfully detects and accepts dialog."""
        handler = ConsentHandler()
        
        mock_button = AsyncMock()
        page = AsyncMock()
        page.query_selector = AsyncMock(side_effect=[MagicMock(), None])  # Found, then dismissed
        page.content = AsyncMock(return_value="<html>Accept cookies</html>")
        
        success = await handler.detect_and_accept(page)
        assert success is True

    @pytest.mark.asyncio
    async def test_detect_and_accept_no_dialog(self):
        """detect_and_accept returns False if no dialog found."""
        handler = ConsentHandler()
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        
        success = await handler.detect_and_accept(page)
        assert success is False

    @pytest.mark.asyncio
    async def test_detect_and_accept_timeout(self):
        """detect_and_accept respects timeout."""
        handler = ConsentHandler(timeout_seconds=0.1)
        
        async def slow_detect(*args, **kwargs):
            await asyncio.sleep(1)  # Longer than timeout
            return False
        
        page = AsyncMock()
        handler.detect_dialog = slow_detect
        
        success = await handler.detect_and_accept(page)
        assert success is False


class TestPatternRegistration:
    """Tests for custom pattern registration."""

    def test_register_pattern(self):
        """register_pattern adds pattern to list."""
        handler = ConsentHandler()
        pattern = ConsentPattern(
            name="custom",
            dialog_selector=".custom",
            accept_button_selector=".custom-accept",
        )
        
        handler.register_pattern(pattern)
        assert pattern in handler.custom_patterns

    def test_register_multiple_patterns(self):
        """register_pattern allows multiple registrations."""
        handler = ConsentHandler()
        pattern1 = ConsentPattern("p1", ".d1", ".a1")
        pattern2 = ConsentPattern("p2", ".d2", ".a2")
        
        handler.register_pattern(pattern1)
        handler.register_pattern(pattern2)
        
        assert len(handler.custom_patterns) == 2

    def test_get_available_patterns(self):
        """get_available_patterns returns all pattern names."""
        handler = ConsentHandler()
        custom = ConsentPattern("custom", ".d", ".a")
        handler.register_pattern(custom)
        
        patterns = handler.get_available_patterns()
        assert "custom" in patterns
        assert len(patterns) >= 3  # At least 3 standard + 1 custom


class TestDialogTypeInference:
    """Tests for dialog type inference."""

    def test_infer_cookie_banner_type(self):
        """Infers COOKIE_BANNER from pattern name."""
        handler = ConsentHandler()
        dialog_type = handler._infer_dialog_type("cookie_banner_standard")
        assert dialog_type == DialogType.COOKIE_BANNER

    def test_infer_gdpr_modal_type(self):
        """Infers GDPR_MODAL from pattern name."""
        handler = ConsentHandler()
        dialog_type = handler._infer_dialog_type("gdpr_modal_standard")
        assert dialog_type == DialogType.GDPR_MODAL

    def test_infer_generic_modal_type(self):
        """Infers GENERIC_MODAL for unknown pattern."""
        handler = ConsentHandler()
        dialog_type = handler._infer_dialog_type("unknown_pattern")
        assert dialog_type == DialogType.GENERIC_MODAL


class TestValidateNoDialog:
    """Tests for post-acceptance validation."""

    @pytest.mark.asyncio
    async def test_validate_no_dialog_success(self):
        """validate_no_dialog returns true when no dialog."""
        handler = ConsentHandler()
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        
        result = await handler.validate_no_dialog(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_no_dialog_still_present(self):
        """validate_no_dialog returns false when dialog present."""
        handler = ConsentHandler()
        
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=MagicMock())
        page.content = AsyncMock(return_value="<html>Cookie banner</html>")
        
        result = await handler.validate_no_dialog(page)
        assert result is False
